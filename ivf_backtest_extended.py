#!/usr/bin/env python3
"""
IVF 백테스트 - 확장 버전 (낮은 임계값)
"""

import sys
sys.path.insert(0, '/root/.openclaw/workspace/strg')

import json
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from fdr_wrapper import get_price
from ivf_scanner_simple import calculate_signal


class IVFBacktestExtended:
    """확장 IVF 백테스트"""
    
    def __init__(self, initial_capital=100_000_000, min_score=35):
        self.initial_capital = initial_capital
        self.min_score = min_score
        self.trades = []
    
    def simulate_trade(self, symbol, entry_date, signal_data):
        """거래 시뮬레이션"""
        try:
            entry_price = signal_data['price']
            score = signal_data['score']
            
            # 점수별 리스크 조정
            if score >= 70:
                stop_pct = 0.04  # -4%
                target_pct = 0.20  # +20%
            elif score >= 55:
                stop_pct = 0.05  # -5%
                target_pct = 0.15  # +15%
            else:
                stop_pct = 0.06  # -6%
                target_pct = 0.12  # +12%
            
            stop_loss = entry_price * (1 - stop_pct)
            target_price = entry_price * (1 + target_pct)
            
            # 보유 기간
            hold_days = 10 if score >= 55 else 7
            
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
                'rr_ratio': round(target_pct / stop_pct, 2)
            }
            
        except Exception as e:
            return None
    
    def run(self, symbols, dates):
        """백테스트 실행"""
        print("=" * 70)
        print("🔥 IVF (ICT + Volume + Fibonacci + 수급) 확장 백테스트")
        print(f"   최소 점수: {self.min_score}점")
        print("=" * 70)
        
        all_signals = []
        
        for symbol in symbols:
            for date in dates:
                signal = calculate_signal(symbol, date)
                if signal and signal['score'] >= self.min_score:
                    all_signals.append((symbol, date, signal))
        
        print(f"\n📊 총 {len(all_signals)}개 신호 발견")
        
        if not all_signals:
            return None
        
        # 상위 신호만 선택 (최대 20개)
        all_signals.sort(key=lambda x: x[2]['score'], reverse=True)
        selected = all_signals[:20]
        
        print(f"   → 상위 {len(selected)}개 시뮬레이션")
        print("\n" + "-" * 70)
        
        for symbol, date, signal in selected:
            print(f"{symbol} ({date}): {signal['signal']} ({signal['score']}점) - {signal['confluence']}")
        
        print("-" * 70)
        
        # 시뮬레이션
        for symbol, date, signal in selected:
            trade = self.simulate_trade(symbol, date, signal)
            if trade:
                self.trades.append(trade)
        
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
        
        # Profit Factor
        gross_profit = sum([r for r in returns if r > 0])
        gross_loss = abs(sum([r for r in returns if r <= 0]))
        pf = gross_profit / gross_loss if gross_loss > 0 else 0
        
        # 평균 R:R
        avg_rr = np.mean([t['rr_ratio'] for t in self.trades])
        
        print(f"\n📈 종합 성과")
        print(f"   총 거래: {total}회")
        print(f"   승률: {win_rate:.1f}% ({len(wins)}승 {len(losses)}패)")
        print(f"   평균 수익률: {avg_return:+.2f}%")
        print(f"   총 수익률: {total_return:+.2f}%")
        print(f"   Profit Factor: {pf:.2f}")
        print(f"   평균 손익비: 1:{avg_rr:.2f}")
        
        print(f"\n📊 세부 통계")
        print(f"   평균 수익: {np.mean(wins) if wins else 0:+.2f}%")
        print(f"   평균 손실: {np.mean(losses) if losses else 0:.2f}%")
        print(f"   최고 수익: {max(returns):+.2f}%")
        print(f"   최저 손실: {min(returns):.2f}%")
        
        # 점수별
        print(f"\n🎯 점수별 성과")
        for threshold, name in [(70, '70+'), (55, '55~69'), (40, '40~54')]:
            subset = [t for t in self.trades if t['signal_score'] >= threshold and t['signal_score'] < (threshold + 15 if threshold < 70 else 100)]
            if subset:
                r = [t['return_pct'] for t in subset]
                wr = len([x for x in r if x > 0]) / len(r) * 100
                print(f"   {name}점: {len(subset)}회, 승률 {wr:.1f}%, 평균 {np.mean(r):+.2f}%")
        
        # 합치
        print(f"\n🔗 합치 요소별 성과")
        cf_stats = {}
        for t in self.trades:
            for cf in t.get('confluence', []):
                if cf not in cf_stats:
                    cf_stats[cf] = []
                cf_stats[cf].append(t['return_pct'])
        
        for cf, rets in sorted(cf_stats.items(), key=lambda x: np.mean(x[1]), reverse=True):
            wr = len([r for r in rets if r > 0]) / len(rets) * 100
            print(f"   {cf}: {len(rets)}회, 승률 {wr:.1f}%, 평균 {np.mean(rets):+.2f}%")
        
        # TOP
        print(f"\n🏆 TOP 5 수익")
        for t in sorted(self.trades, key=lambda x: x['return_pct'], reverse=True)[:5]:
            print(f"   {t['symbol']} ({t['entry_date']}): {t['return_pct']:+.2f}% (진입: {t['entry_price']:,.0f})")
        
        # WORST
        print(f"\n⚠️ TOP 5 손실")
        for t in sorted(self.trades, key=lambda x: x['return_pct'])[:5]:
            print(f"   {t['symbol']} ({t['entry_date']}): {t['return_pct']:.2f}% (진입: {t['entry_price']:,.0f})")
        
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
    bt = IVFBacktestExtended(min_score=35)
    
    symbols = ['033100', '140860', '348210', '006730', '009620', '012210', '025980', '042700']
    dates = ['2026-02-03', '2026-02-10', '2026-02-17', '2026-02-24', '2026-03-03', '2026-03-10', '2026-03-17', '2026-03-24']
    
    results = bt.run(symbols, dates)
    
    if results:
        with open('docs/ivf_backtest_results.json', 'w', encoding='utf-8') as f:
            json.dump(results, f, ensure_ascii=False, indent=2, default=str)
        print("\n✅ 저장: docs/ivf_backtest_results.json")
