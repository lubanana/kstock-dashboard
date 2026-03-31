#!/usr/bin/env python3
"""
단기 급등 예측 스캐너 (Short-term Momentum Scanner)
기간: 1~5일 내 급등 가능성
"""

import sys
sys.path.insert(0, '/root/.openclaw/workspace/strg')

import pandas as pd
import json
import numpy as np
from datetime import datetime, timedelta
import sqlite3
from fdr_wrapper import get_price


class ShortTermMomentumScanner:
    """단기 급등 가능성 스캐너"""
    
    def __init__(self):
        self.price_conn = sqlite3.connect('/root/.openclaw/workspace/strg/data/pivot_strategy.db')
        
    def calculate_indicators(self, df):
        """기술적 지표 계산"""
        if df is None or len(df) < 20:
            return None
            
        indicators = {}
        
        # 1. RSI (14일)
        delta = df['Close'].diff()
        gain = delta.where(delta > 0, 0).rolling(14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
        rs = gain / loss
        rsi = 100 - (100 / (1 + rs))
        indicators['rsi'] = rsi.iloc[-1]
        indicators['rsi_prev'] = rsi.iloc[-2] if len(rsi) > 1 else None
        
        # 2. 볼린저 밴드 (20일, 2σ)
        sma20 = df['Close'].rolling(20).mean()
        std20 = df['Close'].rolling(20).std()
        indicators['bb_upper'] = (sma20 + 2 * std20).iloc[-1]
        indicators['bb_lower'] = (sma20 - 2 * std20).iloc[-1]
        indicators['bb_middle'] = sma20.iloc[-1]
        indicators['bb_position'] = (df['Close'].iloc[-1] - indicators['bb_lower']) / (indicators['bb_upper'] - indicators['bb_lower'])
        
        # 3. 거래량 분석
        vol_sma20 = df['Volume'].rolling(20).mean()
        indicators['volume_ratio'] = df['Volume'].iloc[-1] / vol_sma20.iloc[-1]
        indicators['volume_prev_ratio'] = df['Volume'].iloc[-2] / vol_sma20.iloc[-2] if len(df) > 1 else 1
        
        # 4. 이평선
        indicators['ema5'] = df['Close'].ewm(span=5).mean().iloc[-1]
        indicators['ema10'] = df['Close'].ewm(span=10).mean().iloc[-1]
        indicators['ema20'] = df['Close'].ewm(span=20).mean().iloc[-1]
        
        # 5. 캔들스틱 패턴
        latest = df.iloc[-1]
        prev = df.iloc[-2] if len(df) > 1 else latest
        
        # 핸머 (Hammer)
        body = abs(latest['Close'] - latest['Open'])
        lower_shadow = min(latest['Close'], latest['Open']) - latest['Low']
        upper_shadow = latest['High'] - max(latest['Close'], latest['Open'])
        indicators['is_hammer'] = (lower_shadow > 2 * body) and (upper_shadow < body)
        
        # 도지 (Doji)
        indicators['is_doji'] = body < (latest['High'] - latest['Low']) * 0.1
        
        # 양봉/음봉
        indicators['is_bullish'] = latest['Close'] > latest['Open']
        
        # 6. 변동성
        indicators['atr'] = (df['High'] - df['Low']).rolling(14).mean().iloc[-1]
        indicators['daily_return'] = (latest['Close'] - prev['Close']) / prev['Close'] * 100
        
        # 7. 가격 위치
        high_20 = df['High'].tail(20).max()
        low_20 = df['Low'].tail(20).min()
        indicators['price_position'] = (latest['Close'] - low_20) / (high_20 - low_20)
        
        # 8. OBV (On Balance Volume)
        obv = [0]
        for i in range(1, len(df)):
            if df['Close'].iloc[i] > df['Close'].iloc[i-1]:
                obv.append(obv[-1] + df['Volume'].iloc[i])
            elif df['Close'].iloc[i] < df['Close'].iloc[i-1]:
                obv.append(obv[-1] - df['Volume'].iloc[i])
            else:
                obv.append(obv[-1])
        indicators['obv'] = obv[-1]
        indicators['obv_slope'] = (obv[-1] - obv[-5]) / 5 if len(obv) >= 5 else 0
        
        return indicators
    
    def calculate_momentum_score(self, indicators):
        """단기 급등 점수 계산 (100점 만점)"""
        if indicators is None:
            return 0
            
        score = 0
        signals = []
        
        # 1. RSI 과매도 후 반등 (20점)
        if indicators['rsi'] < 30:
            score += 20
            signals.append("RSI 과매도 (<30)")
        elif indicators['rsi'] < 40:
            score += 15
            signals.append("RSI 과열근접 (<40)")
        
        # RSI 상승 반전 (10점)
        if indicators['rsi_prev'] and indicators['rsi'] > indicators['rsi_prev']:
            score += 10
            signals.append("RSI 상승 반전")
        
        # 2. 볼린저 밴드 하단 돌파 (15점)
        if indicators['bb_position'] < 0.1:
            score += 15
            signals.append("BB 하단 근접")
        elif indicators['bb_position'] < 0.2:
            score += 10
            signals.append("BB 하단 접근")
        
        # 3. 거래량 급증 (20점)
        if indicators['volume_ratio'] > 3:
            score += 20
            signals.append("거래량 폭발 (>300%)")
        elif indicators['volume_ratio'] > 2:
            score += 15
            signals.append("거래량 급증 (>200%)")
        elif indicators['volume_ratio'] > 1.5:
            score += 10
            signals.append("거래량 증가 (>150%)")
        
        # 4. 캔들스틱 패턴 (15점)
        if indicators['is_hammer']:
            score += 15
            signals.append("핸머 패턴 (반전신호)")
        elif indicators['is_doji']:
            score += 10
            signals.append("도지 패턴 (망치형)")
        
        if indicators['is_bullish']:
            score += 5
            signals.append("양봉")
        
        # 5. 이평선 정배열 (10점)
        if indicators['ema5'] > indicators['ema10'] > indicators['ema20']:
            score += 10
            signals.append("정배열 (단기~중기)")
        elif indicators['ema5'] > indicators['ema10']:
            score += 5
            signals.append("단기 정배열")
        
        # 6. 가격 위치 (10점)
        if indicators['price_position'] < 0.2:
            score += 10
            signals.append("20일 저점 근접")
        elif indicators['price_position'] < 0.3:
            score += 5
            signals.append("20일 하단권")
        
        # 7. OBV 상승 (10점)
        if indicators['obv_slope'] > 0:
            score += 10
            signals.append("OBV 상승 (매수세)")
        
        return min(score, 100), signals
    
    def scan_stock(self, symbol, min_score=60):
        """개별 종목 스캔"""
        try:
            end_date = datetime.now()
            start_date = end_date - timedelta(days=60)
            df = get_price(symbol, start_date.strftime('%Y-%m-%d'), end_date.strftime('%Y-%m-%d'))
            
            if df is None or len(df) < 30:
                return None
            
            latest = df.iloc[-1]
            if latest['Close'] < 1000:  # 저가주 제외
                return None
            
            # 거래대금 필터 (10억 이상)
            if latest['Close'] * latest['Volume'] < 1000000000:
                return None
            
            indicators = self.calculate_indicators(df)
            if indicators is None:
                return None
            
            score, signals = self.calculate_momentum_score(indicators)
            
            if score < min_score:
                return None
            
            # 종목명 조회
            name = self.price_conn.execute(
                'SELECT name FROM stock_info WHERE symbol = ?', (symbol,)
            ).fetchone()
            name = name[0] if name else 'Unknown'
            
            return {
                'symbol': symbol,
                'name': name,
                'price': latest['Close'],
                'volume': latest['Volume'],
                'amount': latest['Close'] * latest['Volume'],
                'score': score,
                'signals': signals,
                'rsi': indicators['rsi'],
                'volume_ratio': indicators['volume_ratio'],
                'bb_position': indicators['bb_position'],
                'daily_return': indicators['daily_return'],
                'is_bullish': indicators['is_bullish']
            }
            
        except Exception as e:
            return None
    
    def run(self, max_results=30):
        """전체 스캔 실행"""
        print("="*70)
        print("🚀 단기 급등 예측 스캐너 (1~5일 타겟)")
        print("="*70)
        print("\n📋 스캔 기준:")
        print("   • RSI 과매도 후 반등 (+20점)")
        print("   • 볼린저 밴드 하단 근접 (+15점)")
        print("   • 거래량 급증 (+20점)")
        print("   • 캔들스틱 반전 패턴 (+15점)")
        print("   • 이평선 정배열 (+10점)")
        print("   • 20일 저점 근접 (+10점)")
        print("   • OBV 상승 (+10점)")
        print("\n   총점 60점 이상 선정\n")
        
        symbols = [r[0] for r in self.price_conn.execute('SELECT symbol FROM stock_info').fetchall()]
        print(f"📊 대상: {len(symbols)}개 종목 스캔 중...\n")
        
        results = []
        for i, symbol in enumerate(symbols, 1):
            if i % 500 == 0:
                print(f"   [{i}/{len(symbols)}] 진행중... (선정: {len(results)}개)", end='\r')
            
            result = self.scan_stock(symbol)
            if result:
                results.append(result)
        
        print(f"\n✅ 스캔 완료: {len(results)}개 종목 선정\n")
        
        # 점수순 정렬
        results = sorted(results, key=lambda x: x['score'], reverse=True)[:max_results]
        
        return results
    
    def generate_report(self, results, date_str):
        """HTML 리포트 생성"""
        
        cards_html = ""
        for i, r in enumerate(results, 1):
            # 점수에 따른 색상
            if r['score'] >= 80:
                color = '#00ff88'
                grade = '강력매수'
            elif r['score'] >= 70:
                color = '#4dabf7'
                grade = '매수'
            else:
                color = '#fcc419'
                grade = '관심'
            
            # 시그널 HTML
            signals_html = ""
            for sig in r['signals'][:5]:
                signals_html += f'<div style="color: {color}; font-size: 12px; margin: 2px 0;">✓ {sig}</div>'
            
            cards_html += f"""
            <div style="background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%); 
                 border-radius: 12px; padding: 20px; margin: 15px 0; border-left: 4px solid {color};"
            >
                <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 15px;">
                    <div>
                        <span style="font-size: 24px; font-weight: bold; color: {color};">{i}.</span>
                        <span style="font-size: 20px; font-weight: bold; color: #fff; margin-left: 10px;">{r['name']}</span>
                        <span style="color: #adb5bd; margin-left: 10px;">({r['symbol']})</span>
                    </div>
                    <div style="background: {color}; color: #000; padding: 5px 15px; 
                         border-radius: 20px; font-weight: bold;">
                        {r['score']}점 · {grade}
                    </div>
                </div>
                
                <div style="display: grid; grid-template-columns: repeat(4, 1fr); gap: 10px; margin-bottom: 15px;">
                    <div style="background: rgba(255,255,255,0.05); padding: 10px; border-radius: 8px;">
                        <div style="color: #868e96; font-size: 11px;">현재가</div>
                        <div style="color: #fff; font-size: 16px; font-weight: bold;">{r['price']:,.0f}원</div>
                    </div>
                    <div style="background: rgba(255,255,255,0.05); padding: 10px; border-radius: 8px;">
                        <div style="color: #868e96; font-size: 11px;">RSI</div>
                        <div style="color: {'#ff6b6b' if r['rsi'] < 30 else '#fff'}; font-size: 16px; font-weight: bold;">{r['rsi']:.1f}</div>
                    </div>
                    <div style="background: rgba(255,255,255,0.05); padding: 10px; border-radius: 8px;">
                        <div style="color: #868e96; font-size: 11px;">거래량비율</div>
                        <div style="color: {'#00ff88' if r['volume_ratio'] > 2 else '#fff'}; font-size: 16px; font-weight: bold;">{r['volume_ratio']:.1f}x</div>
                    </div>
                    <div style="background: rgba(255,255,255,0.05); padding: 10px; border-radius: 8px;">
                        <div style="color: #868e96; font-size: 11px;">당일수익률</div>
                        <div style="color: {'#00ff88' if r['daily_return'] > 0 else '#ff6b6b'}; font-size: 16px; font-weight: bold;">{r['daily_return']:+.1f}%</div>
                    </div>
                </div>
                
                <div style="background: rgba(255,255,255,0.03); padding: 12px; border-radius: 8px;">
                    <div style="color: #868e96; font-size: 12px; margin-bottom: 8px;">📊 급등 시그널</div>
                    {signals_html}
                </div>
            </div>
            """
        
        html = f"""<!DOCTYPE html>
<html lang="ko">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>단기 급등 예측 리포트 - {date_str}</title>
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{ 
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', 'Noto Sans KR', sans-serif;
            background: linear-gradient(135deg, #0f0f23 0%, #1a1a2e 50%, #16213e 100%);
            color: #fff;
            min-height: 100vh;
            padding: 20px;
        }}
        .container {{ max-width: 1200px; margin: 0 auto; }}
        .header {{ 
            text-align: center; padding: 40px 20px; 
            background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%);
            border-radius: 20px; margin-bottom: 30px;
        }}
        .header h1 {{ font-size: 32px; margin-bottom: 10px; }}
        .header p {{ opacity: 0.9; }}
        .section {{ margin-bottom: 40px; }}
        .section-title {{ 
            font-size: 24px; margin-bottom: 20px; padding-bottom: 10px;
            border-bottom: 2px solid #f5576c;
        }}
        .footer {{ 
            text-align: center; padding: 30px; color: #868e96; 
            border-top: 1px solid #333; margin-top: 40px;
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🚀 단기 급등 예측 리포트</h1>
            <p>RSI 과매도 + 거래량 급증 + 반전 패턴 기반 선별</p>
            <p style="margin-top: 10px; font-size: 14px;">{date_str} · 1~5일 타겟</p>
        </div>
        
        <div class="section">
            <h2 class="section-title">🏆 TOP {len(results)} 급등 예상 종목</h2>
            {cards_html}
        </div>
        
        <div class="footer">
            <p>⚠️ 본 리포트는 기술적 분석 기반 참고 자료입니다.</p>
            <p>단기 트레이딩은 높은 리스크를 동반하므로 신중한 판단이 필요합니다.</p>
        </div>
    </div>
</body>
</html>"""
        
        return html


def main():
    scanner = ShortTermMomentumScanner()
    results = scanner.run(max_results=30)
    
    # 결과 출력
    print("="*70)
    print("📋 최종 결과")
    print("="*70)
    
    for i, r in enumerate(results[:10], 1):
        print(f"\n{i}. [{r['score']}점] {r['name']} ({r['symbol']})")
        print(f"   현재가: {r['price']:,.0f}원 | RSI: {r['rsi']:.1f} | 거래량: {r['volume_ratio']:.1f}x")
        print(f"   시그널: {', '.join(r['signals'][:3])}")
    
    # HTML 리포트 생성
    date_str = datetime.now().strftime('%Y%m%d')
    html = scanner.generate_report(results, date_str)
    
    output_path = f'/root/.openclaw/workspace/strg/docs/SHORT_TERM_MOMENTUM_{date_str}.html'
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(html)
    
    print(f"\n📄 HTML 리포트: {output_path}")
    
    # JSON 저장
    json_path = f'/root/.openclaw/workspace/strg/docs/short_term_momentum_{date_str}.json'
    with open(json_path, 'w', encoding='utf-8') as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    print(f"📄 JSON: {json_path}")


if __name__ == '__main__':
    main()
