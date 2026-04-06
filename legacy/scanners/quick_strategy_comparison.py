#!/usr/bin/env python3
"""
다중 전략 백테스트 - 기존 스캔 결과 기반
"""

import sys
sys.path.insert(0, '/root/.openclaw/workspace/strg')

import json
import numpy as np
from datetime import datetime, timedelta
from fdr_wrapper import get_price


class QuickMultiStrategyTest:
    """빠른 다중 전략 테스트"""
    
    def __init__(self):
        self.initial_capital = 100_000_000
    
    def simulate_strategy(self, name, trades_data, hold_days=7, stop_pct=0.05, target_rr=3.0):
        """전략별 시뮬레이션"""
        results = []
        
        for trade_info in trades_data:
            symbol = trade_info['symbol']
            entry_date = trade_info['entry_date']
            entry_price = trade_info['entry_price']
            
            # 손절/목표 설정
            stop_loss = entry_price * (1 - stop_pct)
            risk = entry_price - stop_loss
            target = entry_price + (risk * target_rr)
            
            # 시뮬레이션
            entry_dt = datetime.strptime(entry_date, '%Y-%m-%d')
            exit_start = entry_dt + timedelta(days=hold_days - 2)
            exit_end = entry_dt + timedelta(days=hold_days + 3)
            
            try:
                df = get_price(symbol,
                              exit_start.strftime('%Y-%m-%d'),
                              exit_end.strftime('%Y-%m-%d'))
                
                if df is None or df.empty:
                    continue
                
                # 결과 계산 (7거래일 후)
                exit_price = df['Close'].iloc[min(hold_days-1, len(df)-1)]
                
                # 중간 체크
                for idx in range(min(hold_days, len(df))):
                    if idx == 0:
                        continue
                    low = df['Low'].iloc[idx]
                    high = df['High'].iloc[idx]
                    
                    if low <= stop_loss:
                        exit_price = stop_loss
                        break
                    if high >= target:
                        exit_price = target
                        break
                
                return_pct = ((exit_price - entry_price) / entry_price) * 100
                
                results.append({
                    'symbol': symbol,
                    'return': round(return_pct, 2),
                    'entry': entry_price,
                    'exit': round(exit_price, 0)
                })
                
            except:
                continue
        
        return results
    
    def run_comparison(self):
        """전략 비교 실행"""
        print("=" * 70)
        print("🔥 다중 전략 수익률 비교 (기존 스캔 종목 기반)")
        print("=" * 70)
        
        # 기존 65점 종목 8개
        test_stocks = [
            {'symbol': '033100', 'name': '제룡전기', 'entry_date': '2026-03-03', 'entry_price': 51100},
            {'symbol': '140860', 'name': '파크시스템스', 'entry_date': '2026-03-03', 'entry_price': 279500},
            {'symbol': '348210', 'name': '넥스틴', 'entry_date': '2026-03-03', 'entry_price': 82000},
            {'symbol': '006730', 'name': '서부T&D', 'entry_date': '2026-03-03', 'entry_price': 15320},
            {'symbol': '009620', 'name': '삼보산업', 'entry_date': '2026-03-03', 'entry_price': 1642},
            {'symbol': '012210', 'name': '삼미금속', 'entry_date': '2026-03-03', 'entry_price': 15480},
            {'symbol': '025980', 'name': '아난티', 'entry_date': '2026-03-03', 'entry_price': 8210},
            {'symbol': '042700', 'name': '한미반도체', 'entry_date': '2026-03-03', 'entry_price': 282000},
        ]
        
        # 전략별 설정
        strategies = [
            {
                'name': '전략1: 보수적 높은R:R',
                'desc': '7일 보유, -5% 손절, 1:4 목표',
                'hold_days': 7,
                'stop_pct': 0.05,
                'target_rr': 4.0,
                'max_pos': 3
            },
            {
                'name': '전략2: 추세 추종',
                'desc': '10일 보유, -6% 손절, 1:3.5 목표',
                'hold_days': 10,
                'stop_pct': 0.06,
                'target_rr': 3.5,
                'max_pos': 5
            },
            {
                'name': '전략3: 단기 짧게',
                'desc': '5일 보유, -4% 손절, 1:2.5 목표',
                'hold_days': 5,
                'stop_pct': 0.04,
                'target_rr': 2.5,
                'max_pos': 4
            },
            {
                'name': '전략4: 고승률',
                'desc': '5일 보유, -3% 손절, 1:1.5 목표',
                'hold_days': 5,
                'stop_pct': 0.03,
                'target_rr': 1.5,
                'max_pos': 5
            },
            {
                'name': '전략5: 극단적R:R',
                'desc': '15일 보유, -7% 손절, 1:5 목표',
                'hold_days': 15,
                'stop_pct': 0.07,
                'target_rr': 5.0,
                'max_pos': 2
            },
        ]
        
        all_results = []
        
        for strategy in strategies:
            print(f"\n📊 {strategy['name']}")
            print(f"   {strategy['desc']}")
            print("-" * 50)
            
            # 상위 종목만 선택
            selected = test_stocks[:strategy['max_pos']]
            
            results = self.simulate_strategy(
                strategy['name'],
                selected,
                strategy['hold_days'],
                strategy['stop_pct'],
                strategy['target_rr']
            )
            
            if results:
                returns = [r['return'] for r in results]
                wins = [r for r in returns if r > 0]
                
                win_rate = len(wins) / len(returns) * 100
                avg_return = np.mean(returns)
                total_return = np.sum(returns)
                
                avg_win = np.mean(wins) if wins else 0
                avg_loss = abs(np.mean([r for r in returns if r <= 0])) if len(returns) > len(wins) else 0
                rr = avg_win / avg_loss if avg_loss > 0 else 0
                
                print(f"   거래: {len(results)}회 | 승률: {win_rate:.1f}%")
                print(f"   평균: {avg_return:+.2f}% | 총수익: {total_return:+.2f}%")
                print(f"   R:R: 1:{rr:.2f}")
                
                for r in results:
                    emoji = '📈' if r['return'] > 0 else '📉'
                    print(f"      {emoji} {r['symbol']}: {r['return']:+.2f}%")
                
                all_results.append({
                    'name': strategy['name'],
                    'trades': len(results),
                    'win_rate': win_rate,
                    'total_return': total_return,
                    'avg_return': avg_return,
                    'rr_ratio': rr,
                    'details': results
                })
        
        # 최종 비교
        print("\n" + "=" * 70)
        print("📊 전략별 최종 비교")
        print("=" * 70)
        
        all_results.sort(key=lambda x: x['total_return'], reverse=True)
        
        print(f"\n{'순위':<4} {'전략명':<20} {'거래':<6} {'승률':<8} {'평균':<10} {'총수익':<10} {'R:R':<6}")
        print("-" * 70)
        
        for i, r in enumerate(all_results, 1):
            medal = '🥇' if i == 1 else '🥈' if i == 2 else '🥉' if i == 3 else '  '
            print(f"{medal} {i:<2} {r['name']:<20} {r['trades']:<6} {r['win_rate']:<8.1f} {r['avg_return']:<10.2f} {r['total_return']:<10.2f} 1:{r['rr_ratio']:.2f}")
        
        # 최적 전략 분석
        if all_results:
            best = all_results[0]
            print(f"\n🏆 최적 전략: {best['name']}")
            print(f"   - 총 수익률: {best['total_return']:+.2f}%")
            print(f"   - 승률: {best['win_rate']:.1f}%")
            print(f"   - R:R 비율: 1:{best['rr_ratio']:.2f}")
            print(f"   - 거래 횟수: {best['trades']}회")
        
        return all_results


if __name__ == '__main__':
    tester = QuickMultiStrategyTest()
    results = tester.run_comparison()
    
    # 저장
    with open('docs/strategy_comparison_results.json', 'w', encoding='utf-8') as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    
    print("\n✅ 결과 저장: docs/strategy_comparison_results.json")
