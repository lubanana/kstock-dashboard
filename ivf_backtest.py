#!/usr/bin/env python3
"""
IVF (ICT + Volume + Fibonacci + 수급) 백테스트
"""

import sys
sys.path.insert(0, '/root/.openclaw/workspace/strg')

import json
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from fdr_wrapper import get_price
from ivf_scanner_simple import calculate_signal


class IVFBacktest:
    """IVF 백테스트"""
    
    def __init__(self, initial_capital=100_000_000):
        self.initial_capital = initial_capital
        self.trades = []
    
    def simulate_trade(self, symbol, entry_date, signal_data, hold_days=10):
        """거래 시뮬레이션"""
        try:
            entry_price = signal_data['price']
            
            # 손절/목표 설정
            stop_loss = entry_price * 0.95  # -5%
            target_price = entry_price * 1.15  # +15%
            
            # 보유 기간 데이터
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
                
                # 손절
                if row['Low'] <= stop_loss:
                    exit_price = stop_loss
                    exit_reason = '손절'
                    break
                
                # 익절
                if row['High'] >= target_price:
                    exit_price = target_price
                    exit_reason = '목표도달'
                    break
            
            # 보유 만료
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
                'confluence': signal_data.get('confluence', [])
            }
            
        except Exception as e:
            return None
    
    def run_backtest(self, symbols, dates):
        """백테스트 실행"""
        print("=" * 70)
        print("🔥 IVF (ICT + Volume + Fibonacci + 수급) 백테스트")
        print("=" * 70)
        
        all_signals = []
        
        for symbol in symbols:
            print(f"\n📊 {symbol}")
            for date in dates:
                signal = calculate_signal(symbol, date)
                if signal and signal['score'] >= 50:
                    all_signals.append((symbol, date, signal))
                    print(f"   {date}: {signal['signal']} ({signal['score']}점) - {signal['confluence']}")
        
        if not all_signals:
            print("\n⚠️ 신호가 없습니다.")
            return []
        
        print(f"\n\n📈 총 {len(all_signals)}개 신호 발견 - 시뮬레이션 시작")
        print("=" * 70)
        
        # 시뮬레이션
        for symbol, date, signal in all_signals:
            trade = self.simulate_trade(symbol, date, signal)
            if trade:
                self.trades.append(trade)
                emoji = '📈' if trade['return_pct'] > 0 else '📉'
                print(f"{emoji} {trade['symbol']}: {trade['return_pct']:+.2f}% ({trade['exit_reason']})")
        
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
        win_rate = len(wins) / total * 100
        avg_return = np.mean(returns)
        total_return = sum(returns)
        
        print(f"\n총 거래: {total}회")
        print(f"승률: {win_rate:.1f}% ({len(wins)}승 {len(losses)}패)")
        print(f"평균 수익률: {avg_return:+.2f}%")
        print(f"총 수익률: {total_return:+.2f}%")
        print(f"평균 수익: {np.mean(wins) if wins else 0:+.2f}%")
        print(f"평균 손실: {np.mean(losses) if losses else 0:.2f}%")
        
        # 점수별 분석
        print("\n📊 점수별 성과")
        score_70 = [t for t in self.trades if t['signal_score'] >= 70]
        score_50_69 = [t for t in self.trades if 50 <= t['signal_score'] < 70]
        
        if score_70:
            r = [t['return_pct'] for t in score_70]
            wr = len([x for x in r if x > 0]) / len(r) * 100
            print(f"70점+: {len(score_70)}회, 승률 {wr:.1f}%, 평균 {np.mean(r):+.2f}%")
        
        if score_50_69:
            r = [t['return_pct'] for t in score_50_69]
            wr = len([x for x in r if x > 0]) / len(r) * 100
            print(f"50~69점: {len(score_50_69)}회, 승률 {wr:.1f}%, 평균 {np.mean(r):+.2f}%")
        
        # 합치 분석
        print("\n🔗 합치 요소별 성과")
        cf_stats = {}
        for t in self.trades:
            for cf in t.get('confluence', []):
                if cf not in cf_stats:
                    cf_stats[cf] = []
                cf_stats[cf].append(t['return_pct'])
        
        for cf, rets in sorted(cf_stats.items(), key=lambda x: np.mean(x[1]), reverse=True):
            print(f"{cf}: {len(rets)}회, 평균 {np.mean(rets):+.2f}%")
        
        # TOP 수익
        print("\n🏆 TOP 3 수익")
        for t in sorted(self.trades, key=lambda x: x['return_pct'], reverse=True)[:3]:
            print(f"   {t['symbol']} ({t['entry_date']}): {t['return_pct']:+.2f}%")
        
        return {
            'trades': self.trades,
            'summary': {
                'total': total,
                'win_rate': win_rate,
                'avg_return': avg_return,
                'total_return': total_return
            }
        }


if __name__ == '__main__':
    bt = IVFBacktest()
    
    symbols = ['033100', '140860', '348210', '006730', '009620', '012210', '025980', '042700']
    dates = ['2026-02-10', '2026-02-17', '2026-02-24', '2026-03-03', '2026-03-10', '2026-03-17']
    
    results = bt.run_backtest(symbols, dates)
    
    if results:
        with open('docs/ivf_backtest_results.json', 'w', encoding='utf-8') as f:
            json.dump(results, f, ensure_ascii=False, indent=2, default=str)
        print("\n✅ 저장: docs/ivf_backtest_results.json")
