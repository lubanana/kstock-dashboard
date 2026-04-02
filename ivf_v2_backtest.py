#!/usr/bin/env python3
"""
IVF v2.0 백테스트
"""

import sys
sys.path.insert(0, '/root/.openclaw/workspace/strg')

import json
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from fdr_wrapper import get_price
from ivf_scanner_v2 import calculate_ivf_v2_score


class IVFV2Backtest:
    """IVF v2.0 백테스트"""
    
    def __init__(self, initial_capital=100_000_000):
        self.initial_capital = initial_capital
        self.trades = []
    
    def simulate_trade(self, symbol, entry_date, signal_data):
        """거래 시뮬레이션"""
        try:
            entry_price = signal_data['price']
            stop_loss = signal_data['stop_loss']
            target_price = signal_data['target_price']
            score = signal_data['score']
            
            # 점수별 보유 기간
            if score >= 85:
                hold_days = 15
            elif score >= 70:
                hold_days = 10
            else:
                hold_days = 7
            
            entry_dt = datetime.strptime(entry_date, '%Y-%m-%d')
            end_dt = entry_dt + timedelta(days=hold_days + 5)
            
            df = get_price(symbol,
                          (entry_dt + timedelta(days=1)).strftime('%Y-%m-%d'),
                          end_dt.strftime('%Y-%m-%d'))
            
            if df is None or len(df) < 3:
                return None
            
            # 시뮬레이션
            exit_price = None
            exit_reason = None
            actual_hold = 0
            
            for idx in range(min(hold_days, len(df))):
                row = df.iloc[idx]
                actual_hold = idx + 1
                
                if row['Low'] <= stop_loss:
                    exit_price = stop_loss
                    exit_reason = '손절'
                    break
                
                if row['High'] >= target_price:
                    exit_price = target_price
                    exit_reason = '목표도달'
                    break
            
            if exit_price is None:
                exit_price = df['Close'].iloc[min(hold_days-1, len(df)-1)]
                exit_reason = '보유만기'
            
            return_pct = ((exit_price - entry_price) / entry_price) * 100
            
            return {
                'symbol': symbol,
                'entry_date': entry_date,
                'exit_date': (entry_dt + timedelta(days=actual_hold)).strftime('%Y-%m-%d'),
                'entry_price': round(entry_price, 0),
                'exit_price': round(exit_price, 0),
                'return_pct': round(return_pct, 2),
                'hold_days': actual_hold,
                'exit_reason': exit_reason,
                'signal_score': signal_data['score'],
                'confluence': signal_data.get('confluence', []),
                'rsi': signal_data.get('rsi'),
                'patterns': signal_data.get('patterns', []),
                'rr_ratio': signal_data.get('rr_ratio', 0)
            }
            
        except Exception as e:
            return None
    
    def run(self, symbols, dates):
        """백테스트 실행"""
        print("=" * 70)
        print("🔥 IVF v2.0 백테스트 (승률 향상 버전)")
        print("=" * 70)
        
        all_signals = []
        
        print("\n📊 신호 스캐닝...")
        for symbol in symbols:
            for date in dates:
                signal = calculate_ivf_v2_score(symbol, date)
                if signal and signal['score'] >= 50:  # 50점 이상만
                    all_signals.append((symbol, date, signal))
        
        print(f"   50점+ 신호: {len(all_signals)}개")
        
        if not all_signals:
            print("\n⚠️ 신호가 없습니다.")
            return None
        
        # 정렬 및 상위 선택
        all_signals.sort(key=lambda x: x[2]['score'], reverse=True)
        
        # 70점+ 우선, 부족시 55점+ 추가
        high_quality = [s for s in all_signals if s[2]['score'] >= 70]
        medium_quality = [s for s in all_signals if 55 <= s[2]['score'] < 70]
        
        test_signals = high_quality[:15] + medium_quality[:10]
        
        print(f"   → 70점+: {len(high_quality)}개")
        print(f"   → 55~69점: {len(medium_quality)}개")
        print(f"   → 테스트: {len(test_signals)}개")
        
        if not test_signals:
            return None
        
        print("\n" + "-" * 70)
        
        # 시뮬레이션
        for symbol, date, signal in test_signals:
            trade = self.simulate_trade(symbol, date, signal)
            if trade:
                self.trades.append(trade)
                emoji = '📈' if trade['return_pct'] > 0 else '📉'
                print(f"{emoji} {trade['symbol']} ({trade['entry_date'][:10]}): "
                      f"{trade['return_pct']:+.2f}% ({trade['signal_score']}점, {trade['exit_reason']})")
        
        return self.analyze()
    
    def analyze(self):
        """결과 분석"""
        print("\n" + "=" * 70)
        print("📊 백테스트 결과")
        print("=" * 70)
        
        if not self.trades:
            print("\n⚠️ 유효한 거래가 없습니다.")
            return None
        
        returns = [t['return_pct'] for t in self.trades]
        wins = [r for r in returns if r > 0]
        losses = [r for r in returns if r <= 0]
        
        total = len(self.trades)
        win_rate = len(wins) / total * 100 if total > 0 else 0
        avg_return = np.mean(returns)
        total_return = sum(returns)
        
        gross_profit = sum([r for r in returns if r > 0])
        gross_loss = abs(sum([r for r in returns if r <= 0]))
        pf = gross_profit / gross_loss if gross_loss > 0 else 0
        
        avg_rr = np.mean([t['rr_ratio'] for t in self.trades if t['rr_ratio'] > 0])
        
        print(f"\n📈 종합 성과")
        print(f"   총 거래: {total}회")
        print(f"   승률: {win_rate:.1f}% ({len(wins)}승 {len(losses)}패)")
        print(f"   평균 수익률: {avg_return:+.2f}%")
        print(f"   총 수익률: {total_return:+.2f}%")
        print(f"   Profit Factor: {pf:.2f}")
        print(f"   평균 R:R = 1:{avg_rr:.2f}")
        
        print(f"\n📊 세부 통계")
        print(f"   평균 수익: {np.mean(wins) if wins else 0:+.2f}%")
        print(f"   평균 손실: {np.mean(losses) if losses else 0:.2f}%")
        print(f"   최고 수익: {max(returns):+.2f}%")
        print(f"   최저 손실: {min(returns):.2f}%")
        
        # 점수별
        print(f"\n🎯 점수별 성과")
        for threshold, name in [(85, '85+'), (70, '70~84'), (55, '55~69')]:
            subset = [t for t in self.trades if t['signal_score'] >= threshold 
                     and t['signal_score'] < (threshold + 15 if threshold < 85 else 100)]
            if subset:
                r = [t['return_pct'] for t in subset]
                wr = len([x for x in r if x > 0]) / len(r) * 100
                print(f"   {name}점: {len(subset)}회, 승률 {wr:.1f}%, 평균 {np.mean(r):+.2f}%")
        
        # 합치 분석
        print(f"\n🔗 합치 요소별 성과")
        cf_stats = {}
        for t in self.trades:
            for cf in t.get('confluence', []):
                if cf not in cf_stats:
                    cf_stats[cf] = []
                cf_stats[cf].append(t['return_pct'])
        
        for cf, rets in sorted(cf_stats.items(), key=lambda x: np.mean(x[1]), reverse=True)[:10]:
            wr = len([r for r in rets if r > 0]) / len(rets) * 100
            print(f"   {cf}: {len(rets)}회, 승률 {wr:.1f}%, 평균 {np.mean(rets):+.2f}%")
        
        # TOP/WORST
        print(f"\n🏆 TOP 5 수익")
        for t in sorted(self.trades, key=lambda x: x['return_pct'], reverse=True)[:5]:
            print(f"   {t['symbol']} ({t['entry_date']}): {t['return_pct']:+.2f}% (R:R 1:{t['rr_ratio']})")
        
        print(f"\n⚠️ TOP 5 손실")
        for t in sorted(self.trades, key=lambda x: x['return_pct'])[:5]:
            print(f"   {t['symbol']} ({t['entry_date']}): {t['return_pct']:.2f}%")
        
        return {
            'trades': self.trades,
            'summary': {
                'total': total,
                'win_rate': win_rate,
                'avg_return': avg_return,
                'total_return': total_return,
                'profit_factor': pf,
                'avg_rr': avg_rr
            }
        }


if __name__ == '__main__':
    bt = IVFV2Backtest()
    
    symbols = ['033100', '140860', '348210', '006730', '009620', '012210', '025980', '042700',
               '005930', '000660', '035720', '051910', '028260', '086790', '055550']
    dates = ['2026-01-13', '2026-01-20', '2026-01-27',
             '2026-02-03', '2026-02-10', '2026-02-17', '2026-02-24', 
             '2026-03-03', '2026-03-10', '2026-03-17', '2026-03-24', '2026-03-31']
    
    results = bt.run(symbols, dates)
    
    if results:
        with open('docs/ivf_v2_backtest_results.json', 'w', encoding='utf-8') as f:
            json.dump(results, f, ensure_ascii=False, indent=2, default=str)
        print("\n✅ 저장: docs/ivf_v2_backtest_results.json")
