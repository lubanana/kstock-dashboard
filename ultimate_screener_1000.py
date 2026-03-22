#!/usr/bin/env python3
"""
Ultimate Stock Screener - 1000 Point Scale
==========================================
종합 분석 시스템
"""

import sqlite3
import pandas as pd
import numpy as np
from datetime import datetime
import json
import sys
import os

sys.stdout = os.fdopen(sys.stdout.fileno(), 'w', buffering=1)


class UltimateScreener:
    def __init__(self, db_path='./data/pivot_strategy.db'):
        self.db_path = db_path
        self.conn = sqlite3.connect(db_path)
        self.stock_names = self._load_names()
    
    def _load_names(self):
        names = {}
        cursor = self.conn.cursor()
        try:
            cursor.execute('SELECT symbol, name FROM stock_info')
            for row in cursor.fetchall():
                names[row[0]] = row[1]
        except:
            pass
        
        # 기본 매핑 추가
        defaults = {
            '000440': '중앙에너비스', 'BYC': 'BYC', '000250': '삼천당제약',
            '000490': '대동공업', '003350': '기산텔레콤', '001750': '한양증권',
            '001515': 'SK증권우', '154030': '아이윈', '139480': '이마트',
            '049720': '고려신용정보', '002870': '신풍', '005930': '삼성전자'
        }
        names.update(defaults)
        return names
    
    def get_price(self, symbol, days=120):
        query = '''SELECT date, open, high, low, close, volume 
                   FROM stock_prices WHERE symbol = ? 
                   AND date >= date('now', '-{} days') ORDER BY date'''.format(days)
        df = pd.read_sql_query(query, self.conn, params=(symbol,))
        if df.empty:
            return None
        df['date'] = pd.to_datetime(df['date'])
        df.set_index('date', inplace=True)
        return df
    
    def calc_indicators(self, df):
        if len(df) < 60:
            return None
        
        # EMA
        df['ema20'] = df['close'].ewm(span=20).mean()
        df['ema60'] = df['close'].ewm(span=60).mean()
        df['ema120'] = df['close'].ewm(span=120).mean()
        
        # RSI
        delta = df['close'].diff()
        gain = delta.where(delta > 0, 0).rolling(14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
        df['rsi'] = 100 - (100 / (1 + gain / loss))
        
        # MACD
        ema12 = df['close'].ewm(span=12).mean()
        ema26 = df['close'].ewm(span=26).mean()
        df['macd'] = ema12 - ema26
        df['macd_sig'] = df['macd'].ewm(span=9).mean()
        df['macd_hist'] = df['macd'] - df['macd_sig']
        
        # 볼린저
        df['ma20'] = df['close'].rolling(20).mean()
        df['std20'] = df['close'].rolling(20).std()
        df['bb_up'] = df['ma20'] + df['std20'] * 2
        df['bb_low'] = df['ma20'] - df['std20'] * 2
        
        # ATR
        df['tr'] = np.maximum(df['high'] - df['low'],
            np.maximum(abs(df['high'] - df['close'].shift(1)),
                      abs(df['low'] - df['close'].shift(1))))
        df['atr14'] = df['tr'].rolling(14).mean()
        
        # 거래량
        df['vol_ma20'] = df['volume'].rolling(20).mean()
        df['vol_ratio'] = df['volume'] / df['vol_ma20']
        
        return df
    
    def score_stock(self, symbol):
        df = self.get_price(symbol)
        if df is None or len(df) < 60:
            return None
        
        df = self.calc_indicators(df)
        if df is None:
            return None
        
        latest = df.iloc[-1]
        price = latest['close']
        
        scores = {'total': 0}
        reasons = []
        
        # 1. 추세 점수 (0-250)
        trend_score = 0
        if price > latest['ema20']:
            trend_score += 60
            reasons.append('주가>EMA20')
        if latest['ema20'] > latest['ema60']:
            trend_score += 60
            reasons.append('정배열20>60')
        if latest['ema60'] > latest['ema120']:
            trend_score += 50
            reasons.append('정배열60>120')
        
        high_52w = df['high'].tail(252).max() if len(df) >= 252 else df['high'].max()
        if high_52w > 0:
            from_high = (high_52w - price) / high_52w
            if from_high < 0.10:
                trend_score += 50
                reasons.append('52주고가-10%')
            elif from_high < 0.20:
                trend_score += 30
                reasons.append('52주고가-20%')
        
        if len(df) >= 60:
            ret60 = (price - df['close'].iloc[-60]) / df['close'].iloc[-60] * 100
            if ret60 > 20:
                trend_score += 30
                reasons.append(f'60일+{ret60:.0f}%')
        
        scores['trend'] = min(trend_score, 250)
        scores['total'] += scores['trend']
        
        # 2. 모멘텀 점수 (0-200)
        mom_score = 0
        rsi = latest['rsi']
        if 45 <= rsi <= 65:
            mom_score += 60
            reasons.append(f'RSI{rsi:.0f}')
        elif 40 <= rsi <= 70:
            mom_score += 30
        
        if latest['macd_hist'] > 0:
            mom_score += 40
            reasons.append('MACD+')
        
        if len(df) >= 3 and df['macd_hist'].iloc[-1] > df['macd_hist'].iloc[-2] > df['macd_hist'].iloc[-3]:
            mom_score += 30
            reasons.append('MACD증가')
        
        if len(df) >= 20:
            ret20 = (price - df['close'].iloc[-20]) / df['close'].iloc[-20] * 100
            if 5 <= ret20 <= 30:
                mom_score += 50
                reasons.append(f'20일+{ret20:.0f}%')
            elif ret20 > 0:
                mom_score += 20
        
        scores['momentum'] = min(mom_score, 200)
        scores['total'] += scores['momentum']
        
        # 3. 거래량 점수 (0-200)
        vol_score = 0
        vol_ratio = latest['vol_ratio']
        if vol_ratio >= 2.5:
            vol_score += 80
            reasons.append(f'거래량{vol_ratio:.1f}배')
        elif vol_ratio >= 2.0:
            vol_score += 60
            reasons.append(f'거래량{vol_ratio:.1f}배')
        elif vol_ratio >= 1.5:
            vol_score += 40
        elif vol_ratio >= 1.0:
            vol_score += 20
        
        if len(df) >= 20:
            amount = (df['close'].tail(20) * df['volume'].tail(20)).mean() / 100000000
            if amount >= 100:
                vol_score += 60
                reasons.append(f'대금{amount:.0f}억')
            elif amount >= 50:
                vol_score += 40
            elif amount >= 10:
                vol_score += 20
        
        if df['volume'].tail(5).mean() > df['volume'].tail(20).mean():
            vol_score += 20
            reasons.append('거래량증가')
        
        scores['volume'] = min(vol_score, 200)
        scores['total'] += scores['volume']
        
        # 4. 변동성/리스크 점수 (0-150)
        vola_score = 0
        if latest['atr14'] > 0:
            atr_pct = latest['atr14'] / price * 100
            if 2 <= atr_pct <= 5:
                vola_score += 60
                reasons.append(f'ATR{atr_pct:.1f}%')
        
        bb_range = latest['bb_up'] - latest['bb_low']
        if bb_range > 0:
            bb_pos = (price - latest['bb_low']) / bb_range
            if 0.4 <= bb_pos <= 0.7:
                vola_score += 50
                reasons.append(f'BB상단{bb_pos*100:.0f}%')
        
        scores['volatility'] = min(vola_score, 150)
        scores['total'] += scores['volatility']
        
        # 5. 피봇/브레이크아웃 점수 (0-200)
        pivot_score = 0
        if len(df) >= 30:
            recent_high = df['high'].tail(20).max()
            recent_low = df['low'].tail(20).min()
            
            if recent_high > 0:
                proximity = (recent_high - price) / recent_high * 100
                if proximity <= 3:
                    pivot_score += 80
                    reasons.append(f'고가근접{proximity:.1f}%')
                elif proximity <= 7:
                    pivot_score += 40
                    reasons.append(f'눌림목{proximity:.1f}%')
            
            # 박스권 상단 돌파 시도
            if recent_high > recent_low:
                box_range = (recent_high - recent_low) / recent_low * 100
                if box_range < 15:  # 좁은 박스권
                    pivot_score += 40
                    reasons.append('박스권수렴')
        
        scores['pivot'] = min(pivot_score, 200)
        scores['total'] += scores['pivot']
        
        # 목표가/손절가 계산 - 동적 계산 (항상 2.0이 나오지 않도록)
        if latest['atr14'] > 0 and len(df) >= 20:
            # ATR 기반 기본값
            atr = latest['atr14']
            
            # 1. 최근 20일 고가/저가 기반 피봇 레벨 계산
            recent_high = df['high'].tail(20).max()
            recent_low = df['low'].tail(20).min()
            
            # 2. 목표가 계산 - 여러 방법 중 최대값 사용
            targets = []
            
            # ATR 기반 확장 (3~6배 변동)
            targets.append(price + atr * 3)  # 보수적
            targets.append(price + atr * 4.5)  # 중립
            
            # 최근 고가 돌파 목표
            if recent_high > price:
                # 고가 돌파 후 상승 목표 (고가 + 고가-저가의 50~100%)
                box_range = recent_high - recent_low
                targets.append(recent_high + box_range * 0.5)
                targets.append(recent_high + box_range * 0.8)
            
            # 피본나치 확장 (상승추세 가정)
            if len(df) >= 10:
                last_low = df['low'].tail(10).min()
                if price > last_low:
                    move = price - last_low
                    targets.append(price + move * 1.272)  # 피본나치 127.2%
                    targets.append(price + move * 1.618)  # 피본나치 161.8%
            
            # 3. 손절가 계산 - 여러 방법 중 최소값 사용 (더 타이트하게)
            stop_losses = []
            
            # ATR 기반 (1.5~2.5배)
            stop_losses.append(price - atr * 1.5)
            stop_losses.append(price - atr * 2.0)
            stop_losses.append(price - atr * 2.5)
            
            # EMA20 기반 (추세 이탈 기준)
            stop_losses.append(latest['ema20'] * 0.98)
            stop_losses.append(latest['ema20'] * 0.95)
            
            # 최근 저가 기반
            recent_low_5d = df['low'].tail(5).min()
            stop_losses.append(recent_low_5d * 0.99)
            
            # 최종 목표가/손절가 선택
            target = max([t for t in targets if t > price] or [price * 1.10])
            stop_loss = min([s for s in stop_losses if s < price] or [price * 0.93])
            
            # 손익비 계산
            potential_gain = target - price
            potential_loss = price - stop_loss
            rr = potential_gain / potential_loss if potential_loss > 0 else 0
            
        else:
            # 데이터 부족시 기본값
            stop_loss = price * 0.93
            target = price * 1.15
            rr = (target - price) / (price - stop_loss)
        
        return {
            'symbol': symbol,
            'name': self.stock_names.get(symbol, symbol),
            'price': round(price, 0),
            'score': scores['total'],
            'scores': scores,
            'rsi': round(latest['rsi'], 1),
            'vol_ratio': round(latest['vol_ratio'], 2),
            'stop_loss': round(stop_loss, 0),
            'target': round(target, 0),
            'rr_ratio': round(rr, 2),
            'reasons': reasons[:8]  # 상위 8개 이유만
        }
    
    def scan_all(self):
        cursor = self.conn.cursor()
        cursor.execute('SELECT DISTINCT symbol FROM stock_prices WHERE date >= "2025-01-01"')
        symbols = [row[0] for row in cursor.fetchall()]
        
        print(f"총 {len(symbols)}개 종목 분석 시작...")
        results = []
        
        for i, symbol in enumerate(symbols, 1):
            if i % 100 == 0:
                print(f"  진행: {i}/{len(symbols)} ({i/len(symbols)*100:.1f}%)")
            
            result = self.score_stock(symbol)
            if result and result['score'] >= 500:  # 500점 이상만
                results.append(result)
        
        # 점수 순 정렬
        results.sort(key=lambda x: x['score'], reverse=True)
        return results
    
    def generate_report(self, results):
        now = datetime.now().strftime('%Y%m%d_%H%M')
        
        # TOP 10
        top10 = results[:10]
        
        # 참조용 11-50위
        reference = results[10:50]
        
        # HTML 리포트
        html = f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>Ultimate Stock Screener - Top Picks</title>
    <style>
        body {{ font-family: 'Segoe UI', sans-serif; margin: 20px; background: #f5f5f5; }}
        .header {{ background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 30px; border-radius: 10px; margin-bottom: 20px; }}
        .header h1 {{ margin: 0; font-size: 28px; }}
        .header p {{ margin: 10px 0 0 0; opacity: 0.9; }}
        .section {{ background: white; padding: 20px; border-radius: 10px; margin-bottom: 20px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }}
        .section h2 {{ color: #333; border-bottom: 2px solid #667eea; padding-bottom: 10px; }}
        table {{ width: 100%; border-collapse: collapse; }}
        th {{ background: #667eea; color: white; padding: 12px; text-align: left; }}
        td {{ padding: 10px; border-bottom: 1px solid #eee; }}
        tr:hover {{ background: #f8f9ff; }}
        .rank {{ font-weight: bold; font-size: 18px; width: 50px; text-align: center; }}
        .score {{ font-weight: bold; color: #667eea; font-size: 20px; }}
        .price {{ font-weight: bold; color: #333; }}
        .target {{ color: #28a745; font-weight: bold; }}
        .stop {{ color: #dc3545; }}
        .rr {{ color: #666; }}
        .badge {{ display: inline-block; padding: 3px 8px; border-radius: 12px; font-size: 11px; margin: 2px; }}
        .badge-blue {{ background: #e3f2fd; color: #1976d2; }}
        .badge-green {{ background: #e8f5e9; color: #388e3c; }}
        .badge-orange {{ background: #fff3e0; color: #f57c00; }}
        .badge-red {{ background: #ffebee; color: #d32f2f; }}
        .reasons {{ font-size: 12px; color: #666; }}
        .top3 {{ background: linear-gradient(135deg, #ffd700 0%, #ffb700 100%); color: #333; }}
        .methodology {{ background: #f8f9fa; padding: 15px; border-radius: 5px; font-size: 13px; line-height: 1.6; }}
    </style>
</head>
<body>
    <div class="header">
        <h1>🚀 Ultimate Stock Screener</h1>
        <p>내일 급등 가능성 높은 종목 TOP 10 (1000점 체계) | 생성일: {datetime.now().strftime('%Y-%m-%d %H:%M')}</p>
    </div>
    
    <div class="section">
        <h2>🏆 TOP 10 급등 예상 종목</h2>
        <table>
            <tr>
                <th>순위</th>
                <th>종목</th>
                <th>현재가</th>
                <th>종합점수</th>
                <th>목표가</th>
                <th>손절가</th>
                <th>손익비</th>
                <th>선정근거</th>
            </tr>
"""
        
        for i, r in enumerate(top10, 1):
            row_class = 'top3' if i <= 3 else ''
            badge_class = 'badge-red' if i <= 3 else ('badge-orange' if i <= 6 else 'badge-blue')
            
            reasons_html = ' '.join([f'<span class="badge {badge_class}">{reason}</span>' for reason in r['reasons'][:5]])
            
            html += f"""
            <tr class="{row_class}">
                <td class="rank">#{i}</td>
                <td><strong>{r['name']}</strong><br><small>{r['symbol']}</small></td>
                <td class="price">{r['price']:,.0f}원</td>
                <td class="score">{r['score']}점</td>
                <td class="target">{r['target']:,.0f}원</td>
                <td class="stop">{r['stop_loss']:,.0f}원</td>
                <td class="rr">1:{r['rr_ratio']:.1f}</td>
                <td class="reasons">{reasons_html}</td>
            </tr>
"""
        
        html += """
        </table>
    </div>
    
    <div class="section">
        <h2>📊 점수 세부 내역 (TOP 10)</h2>
        <table>
            <tr>
                <th>순위</th>
                <th>종목</th>
                <th>추세<br>(250)</th>
                <th>모멘텀<br>(200)</th>
                <th>거래량<br>(200)</th>
                <th>리스크<br>(150)</th>
                <th>피봇<br>(200)</th>
                <th>총점</th>
            </tr>
"""
        
        for i, r in enumerate(top10, 1):
            s = r['scores']
            html += f"""
            <tr>
                <td>#{i}</td>
                <td><strong>{r['name']}</strong></td>
                <td>{s['trend']}</td>
                <td>{s['momentum']}</td>
                <td>{s['volume']}</td>
                <td>{s['volatility']}</td>
                <td>{s['pivot']}</td>
                <td class="score">{r['score']}</td>
            </tr>
"""
        
        html += """
        </table>
    </div>
    
    <div class="section">
        <h2>🔍 참조용 종목 (11-50위)</h2>
        <table>
            <tr>
                <th>순위</th>
                <th>종목</th>
                <th>현재가</th>
                <th>점수</th>
                <th>RSI</th>
                <th>거래량비율</th>
                <th>주요 특징</th>
            </tr>
"""
        
        for i, r in enumerate(reference, 11):
            reasons_short = ', '.join(r['reasons'][:3])
            html += f"""
            <tr>
                <td>#{i}</td>
                <td><strong>{r['name']}</strong><br><small>{r['symbol']}</small></td>
                <td>{r['price']:,.0f}원</td>
                <td>{r['score']}점</td>
                <td>{r['rsi']}</td>
                <td>{r['vol_ratio']:.1f}x</td>
                <td class="reasons">{reasons_short}</td>
            </tr>
"""
        
        html += """
        </table>
    </div>
    
    <div class="section">
        <h2>📈 채점 방법론 (1000점 체계)</h2>
        <div class="methodology">
            <strong>1. 추세 점수 (250점)</strong><br>
            • 주가 > EMA20 (60점) | EMA20 > EMA60 (60점) | EMA60 > EMA120 (50점)<br>
            • 52주 고가 근접 10% 이내 (50점) | 20% 이내 (30점)<br>
            • 60일 수익률 +20% 이상 (30점)<br><br>
            
            <strong>2. 모멘텀 점수 (200점)</strong><br>
            • RSI 45-65 (60점) | MACD > 0 (40점) | MACD 3일 연속 증가 (30점)<br>
            • 20일 수익률 +5~30% (50점)<br><br>
            
            <strong>3. 거래량 점수 (200점)</strong><br>
            • 거래량 2.5배 이상 (80점) | 2배 (60점) | 1.5배 (40점)<br>
            • 거래대금 100억 이상 (60점) | 50억 (40점)<br>
            • 거래량 증가 추세 (20점)<br><br>
            
            <strong>4. 변동성/리스크 점수 (150점)</strong><br>
            • ATR 2-5% 적정 변동성 (60점) | BB 중상단 위치 (50점)<br><br>
            
            <strong>5. 피봇/브레이크아웃 점수 (200점)</strong><br>
            • 20일 고가 3% 이내 근접 (80점) | 7% 이내 눌림목 (40점)<br>
            • 좁은 박스권 수렴 (40점)<br><br>
            
            <strong>목표가/손절가:</strong> ATR 기반 (목표=현재가+ATR×4, 손절=현재가-ATR×2)
        </div>
    </div>
    
    <div class="section" style="text-align: center; color: #666; font-size: 12px;">
        <p>⚠️ 본 분석은 기술적 분석 기반 예측이며, 투자 결정은 본인의 판단과 책임하에 신중히 이루어져야 합니다.</p>
        <p>Generated by Ultimate Stock Screener | Data: FinanceDataReader | DB: pivot_strategy.db</p>
    </div>
</body>
</html>
"""
        
        # 저장
        filename = f'Ultimate_Screener_TOP10_{now}.html'
        with open(f'./reports/{filename}', 'w', encoding='utf-8') as f:
            f.write(html)
        with open(f'./docs/{filename}', 'w', encoding='utf-8') as f:
            f.write(html)
        
        # JSON 저장
        json_data = {
            'generated_at': datetime.now().isoformat(),
            'top10': top10,
            'reference_11_50': reference
        }
        with open(f'./reports/Ultimate_Screener_{now}.json', 'w', encoding='utf-8') as f:
            json.dump(json_data, f, ensure_ascii=False, indent=2)
        
        return filename


def main():
    screener = UltimateScreener()
    
    print("="*70)
    print("🚀 Ultimate Stock Screener - 1000 Point Scale")
    print("="*70)
    print()
    
    results = screener.scan_all()
    
    print(f"\n✅ 분석 완료: {len(results)}개 종목 500점 이상")
    
    if len(results) >= 10:
        # TOP 10 출력
        print("\n" + "="*70)
        print("🏆 TOP 10 급등 예상 종목")
        print("="*70)
        
        for i, r in enumerate(results[:10], 1):
            print(f"\n#{i} {r['name']} ({r['symbol']})")
            print(f"   현재가: {r['price']:,.0f}원 | 점수: {r['score']}/1000점")
            print(f"   목표가: {r['target']:,.0f}원 (+{((r['target']/r['price']-1)*100):.1f}%)")
            print(f"   손절가: {r['stop_loss']:,.0f}원 (-{((1-r['stop_loss']/r['price'])*100):.1f}%)")
            print(f"   손익비: 1:{r['rr_ratio']:.2f}")
            print(f"   근거: {', '.join(r['reasons'][:5])}")
        
        # 리포트 생성
        filename = screener.generate_report(results)
        print(f"\n📄 리포트 저장: reports/{filename}")
        print(f"   docs/{filename}")
    
    screener.conn.close()


if __name__ == '__main__':
    main()
