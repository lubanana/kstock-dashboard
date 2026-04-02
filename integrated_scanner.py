#!/usr/bin/env python3
"""
통합 복합 스캐너 (Integrated Multi-Strategy Scanner)
이번 주 생성된 모든 스캐너 조합
"""

import sys
sys.path.insert(0, '/root/.openclaw/workspace/strg')

import json
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from dataclasses import dataclass
from typing import List, Dict, Optional
from fdr_wrapper import get_price
from advanced_candle_detector import AdvancedCandleDetector


@dataclass
class ScanResult:
    """통합 스캔 결과"""
    symbol: str
    name: str
    market: str
    price: float
    
    # 전략별 점수
    ivf_score: int = 0
    ivf_signal: str = 'NEUTRAL'
    ivf_pattern: str = ''
    
    candle_score: int = 0
    candle_pattern: str = ''
    
    trend_score: int = 0
    fib_score: int = 0
    volume_score: int = 0
    
    # 종합
    total_score: int = 0
    final_signal: str = 'NEUTRAL'
    
    # 리스크 관리
    stop_loss: float = 0
    target_price: float = 0
    rr_ratio: float = 0
    
    # 메타데이터
    confluence: List[str] = None
    date: str = ''


class IntegratedScanner:
    """통합 복합 스캐너"""
    
    def __init__(self):
        self.results = []
        
    def scan_ivf_v2(self, symbol: str, date: str) -> Dict:
        """IVF v2.0 스캔 (핵심 전략)"""
        try:
            df = get_price(symbol, 
                          (datetime.strptime(date, '%Y-%m-%d') - timedelta(days=90)).strftime('%Y-%m-%d'),
                          date)
            if df is None or len(df) < 30:
                return None
            
            df = df.reset_index()
            closes = df['Close'].values
            highs = df['High'].values
            lows = df['Low'].values
            volumes = df['Volume'].values
            current_price = closes[-1]
            
            score = 0
            confluence = []
            
            # 1. 피볼나치 (30~70% 확장)
            recent_high = np.max(highs[-20:])
            recent_low = np.min(lows[-20:])
            if recent_high <= recent_low:
                return None
            
            retracement = ((recent_high - current_price) / (recent_high - recent_low)) * 100
            if 30 <= retracement <= 70:
                score += 20
                confluence.append(f'Fib_{retracement:.0f}')
            else:
                return None
            
            # 2. 거래량 (1.0x+)
            avg_vol = np.mean(volumes[-20:])
            rvol = volumes[-1] / avg_vol if avg_vol > 0 else 0
            if rvol >= 2.0:
                score += 15
                confluence.append('RVol_2.0')
            elif rvol >= 1.5:
                score += 10
                confluence.append('RVol_1.5')
            elif rvol >= 1.0:
                score += 5
                confluence.append('RVol_Up')
            else:
                return None
            
            # 3. 캔들 패턴 (고급)
            detector = AdvancedCandleDetector(df)
            all_patterns = detector.detect_all_patterns(min_reliability=3)
            
            pattern_score = 0
            best_pattern = None
            
            for p in all_patterns:
                if p['pattern'] == 'morning_star':
                    pattern_score = 25
                    best_pattern = 'morning_star'
                    break
                elif p['pattern'] == 'bullish_engulfing' and pattern_score < 20:
                    pattern_score = 20
                    best_pattern = 'bullish_engulfing'
                elif p['pattern'] == 'bullish_pinbar' and pattern_score < 15:
                    pattern_score = 15
                    best_pattern = 'bullish_pinbar'
                elif p['pattern'] == 'hammer' and pattern_score < 12:
                    pattern_score = 12
                    best_pattern = 'hammer'
            
            if pattern_score > 0:
                score += pattern_score
                confluence.append(best_pattern.upper())
            else:
                return None  # 패턴 필수
            
            # 4. 추세 확인
            ma5 = np.mean(closes[-5:])
            ma20 = np.mean(closes[-20:])
            if current_price > ma5 > ma20:
                score += 10
                confluence.append('Bullish_Trend')
            elif current_price > ma20:
                score += 5
                confluence.append('Above_MA20')
            
            # 신호 결정
            if score >= 60:
                signal = 'STRONG_BUY'
            elif score >= 50:
                signal = 'BUY'
            elif score >= 45:
                signal = 'WATCH'
            else:
                return None
            
            # 리스크 계산
            atr = np.mean([highs[-i] - lows[-i] for i in range(1, 15)])
            
            if score >= 60:
                stop = current_price - (atr * 1.5)
                target = current_price + (atr * 3.5)
            elif score >= 55:
                stop = current_price - (atr * 1.5)
                target = current_price + (atr * 3.0)
            else:
                stop = current_price - (atr * 1.3)
                target = current_price + (atr * 2.5)
            
            rr = (target - current_price) / (current_price - stop) if (current_price - stop) > 0 else 0
            
            return {
                'score': score,
                'signal': signal,
                'pattern': best_pattern,
                'retracement': retracement,
                'rvol': rvol,
                'confluence': confluence,
                'stop_loss': stop,
                'target_price': target,
                'rr_ratio': rr
            }
            
        except Exception as e:
            return None
    
    def run_integrated_scan(self, symbols: List[str], date: str) -> List[ScanResult]:
        """통합 스캔 실행"""
        print("=" * 80)
        print("🔥 통합 복합 스캐너 실행")
        print("=" * 80)
        print(f"대상 종목: {len(symbols)}개")
        print(f"기준일: {date}")
        print("=" * 80)
        
        results = []
        
        for symbol in symbols:
            result = self.scan_ivf_v2(symbol, date)
            if result:
                scan_result = ScanResult(
                    symbol=symbol,
                    name='',
                    market='',
                    price=0,
                    ivf_score=result['score'],
                    ivf_signal=result['signal'],
                    ivf_pattern=result['pattern'],
                    candle_score=result['score'] - 20,  # 추정
                    candle_pattern=result['pattern'],
                    total_score=result['score'],
                    final_signal=result['signal'],
                    stop_loss=result['stop_loss'],
                    target_price=result['target_price'],
                    rr_ratio=result['rr_ratio'],
                    confluence=result['confluence'],
                    date=date
                )
                
                # 가격 정보 조회
                try:
                    df = get_price(symbol, date, date)
                    if df is not None and not df.empty:
                        scan_result.price = df['Close'].iloc[-1]
                except:
                    pass
                
                results.append(scan_result)
                
                emoji = '📈' if result['signal'] in ['BUY', 'STRONG_BUY'] else '➖'
                print(f"{emoji} {symbol}: {result['signal']} ({result['score']}점, {result['pattern']}, R:R 1:{result['rr_ratio']:.1f})")
        
        print(f"\n✅ 스캔 완료: {len(results)}개 신호 감지")
        return results
    
    def generate_report(self, results: List[ScanResult], date: str) -> str:
        """HTML 리포트 생성"""
        
        # 정렬
        results.sort(key=lambda x: x.total_score, reverse=True)
        
        # HTML 생성
        html = f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>통합 복합 스캐너 리포트 - {date}</title>
    <style>
        body {{ font-family: 'Segoe UI', sans-serif; margin: 20px; background: #f5f5f5; }}
        .header {{ background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 30px; border-radius: 10px; margin-bottom: 20px; }}
        .header h1 {{ margin: 0; font-size: 2em; }}
        .summary {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 15px; margin-bottom: 20px; }}
        .card {{ background: white; padding: 20px; border-radius: 10px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }}
        .card h3 {{ margin-top: 0; color: #333; }}
        .metric {{ font-size: 2em; font-weight: bold; color: #667eea; }}
        .stock-grid {{ display: grid; grid-template-columns: repeat(auto-fill, minmax(350px, 1fr)); gap: 15px; }}
        .stock-card {{ background: white; padding: 20px; border-radius: 10px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); border-left: 5px solid #ddd; }}
        .stock-card.strong_buy {{ border-left-color: #28a745; }}
        .stock-card.buy {{ border-left-color: #17a2b8; }}
        .stock-card.watch {{ border-left-color: #ffc107; }}
        .badge {{ display: inline-block; padding: 4px 12px; border-radius: 20px; font-size: 0.85em; font-weight: bold; }}
        .badge-strong {{ background: #28a745; color: white; }}
        .badge-buy {{ background: #17a2b8; color: white; }}
        .badge-watch {{ background: #ffc107; color: #333; }}
        .score {{ font-size: 1.5em; font-weight: bold; color: #333; }}
        .confluence {{ margin-top: 10px; }}
        .confluence-tag {{ display: inline-block; padding: 2px 8px; margin: 2px; background: #e9ecef; border-radius: 4px; font-size: 0.8em; }}
        .risk {{ margin-top: 15px; padding: 10px; background: #f8f9fa; border-radius: 5px; }}
        .risk-row {{ display: flex; justify-content: space-between; }}
        .footer {{ text-align: center; margin-top: 30px; padding: 20px; color: #666; }}
    </style>
</head>
<body>
    <div class="header">
        <h1>🔥 통합 복합 스캐너 리포트</h1>
        <p>생성일: {datetime.now().strftime('%Y-%m-%d %H:%M')}</p>
    </div>
"""
        
        # 요약 통계
        strong_buy = len([r for r in results if r.final_signal == 'STRONG_BUY'])
        buy = len([r for r in results if r.final_signal == 'BUY'])
        watch = len([r for r in results if r.final_signal == 'WATCH'])
        
        html += f"""
    <div class="summary">
        <div class="card">
            <h3>총 신호</h3>
            <div class="metric">{len(results)}</div>
        </div>
        <div class="card">
            <h3>STRONG BUY</h3>
            <div class="metric" style="color: #28a745;">{strong_buy}</div>
        </div>
        <div class="card">
            <h3>BUY</h3>
            <div class="metric" style="color: #17a2b8;">{buy}</div>
        </div>
        <div class="card">
            <h3>WATCH</h3>
            <div class="metric" style="color: #ffc107;">{watch}</div>
        </div>
    </div>
"""
        
        # 종목 상세
        html += '    <div class="stock-grid">\n'
        
        for r in results:
            signal_class = r.final_signal.lower().replace('_', '-')
            badge_class = f"badge-{r.final_signal.lower().split('_')[0]}"
            
            html += f"""
        <div class="stock-card {signal_class}">
            <div style="display: flex; justify-content: space-between; align-items: center;">
                <div>
                    <h3 style="margin: 0;">{r.symbol}</h3>
                    <div class="score">{r.total_score}점</div>
                </div>
                <span class="badge {badge_class}">{r.final_signal}</span>
            </div>
            <div style="margin-top: 10px;">
                <strong>현재가:</strong> {r.price:,.0f}원 | 
                <strong>패턴:</strong> {r.candle_pattern}
            </div>
            <div class="confluence">
                {''.join([f'<span class="confluence-tag">{c}</span>' for c in r.confluence[:6]])}
            </div>
            <div class="risk">
                <div class="risk-row">
                    <span>🛑 손절: {r.stop_loss:,.0f}</span>
                    <span>🎯 목표: {r.target_price:,.0f}</span>
                </div>
                <div style="margin-top: 5px;">
                    <strong>R:R = 1:{r.rr_ratio:.2f}</strong>
                </div>
            </div>
        </div>
"""
        
        html += """    </div>
    <div class="footer">
        <p>통합 복합 스캐너 | IVF v2.0 + 고급 캔들 패턴 + 피볼나치</p>
    </div>
</body>
</html>"""
        
        return html


def main():
    """메인 실행"""
    scanner = IntegratedScanner()
    
    # 대상 종목
    symbols = [
        '005930', '000660', '035720', '005380', '051910',
        '042700', '348210', '140860', '033100', '012210',
        '055550', '086790', '032640', '033780', '035900',
        '263750', '251270', '194480', '293490', '225570',
        '009150', '006400', '028260', '032830', '010140',
        '316140', '024110', '161890', '271560', '267250'
    ]
    
    # 실행일 (현재 날짜)
    today = datetime.now().strftime('%Y-%m-%d')
    
    # 스캔 실행
    results = scanner.run_integrated_scan(symbols, today)
    
    if not results:
        print("\n⚠️ 신호가 없습니다.")
        return
    
    # 리포트 생성
    html = scanner.generate_report(results, today)
    
    # 저장
    report_file = f'INTEGRATED_SCAN_REPORT_{today.replace("-", "")}.html'
    with open(report_file, 'w', encoding='utf-8') as f:
        f.write(html)
    
    print(f"\n✅ 리포트 저장: {report_file}")
    
    # JSON 저장
    json_data = [{
        'symbol': r.symbol,
        'price': r.price,
        'score': r.total_score,
        'signal': r.final_signal,
        'pattern': r.candle_pattern,
        'stop_loss': r.stop_loss,
        'target_price': r.target_price,
        'rr_ratio': r.rr_ratio,
        'confluence': r.confluence
    } for r in results]
    
    json_file = f'docs/integrated_scan_{today.replace("-", "")}.json'
    with open(json_file, 'w', encoding='utf-8') as f:
        json.dump(json_data, f, ensure_ascii=False, indent=2)
    
    print(f"✅ 데이터 저장: {json_file}")
    
    # TOP 5 출력
    print("\n" + "=" * 80)
    print("🏆 TOP 5 추천 종목")
    print("=" * 80)
    for i, r in enumerate(results[:5], 1):
        print(f"{i}. {r.symbol}: {r.final_signal} ({r.total_score}점)")
        print(f"   가격: {r.price:,.0f}원 | 패턴: {r.candle_pattern}")
        print(f"   손절: {r.stop_loss:,.0f} | 목표: {r.target_price:,.0f} | R:R 1:{r.rr_ratio:.1f}")


if __name__ == '__main__':
    main()
