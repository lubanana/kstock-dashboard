#!/usr/bin/env python3
"""
Japanese Pattern Backtester (일본 고전 기법 백테스터)
=====================================================

전략:
1. 사카타 5법 + 일목균형표 신호 발생
2. 다음날 시가 진입
3. 보유 후 수익 실현
"""

import sqlite3
import pandas as pd
import numpy as np
from datetime import datetime
from typing import List, Dict, Optional
import json
import os
from japanese_pattern_scanner import JapanesePatternScanner, SakataFiveMethods, IchimokuCloud


class JapanesePatternBacktester:
    """일본 패턴 백테스터"""
    
    def __init__(self, db_path: str = 'data/level1_prices.db'):
        self.db_path = db_path
        self.scanner = JapanesePatternScanner(db_path)
    
    def get_future_data(self, code: str, entry_date: str, days: int = 10) -> pd.DataFrame:
        """진입 후 데이터 조회"""
        conn = sqlite3.connect(self.db_path)
        
        query = """
        SELECT date, open, high, low, close, volume
        FROM price_data
        WHERE code = ? AND date >= ?
        ORDER BY date
        LIMIT ?
        """
        
        df = pd.read_sql(query, conn, params=(code, entry_date, days + 1))
        conn.close()
        
        return df
    
    def backtest_signal(self, signal: Dict,
                       holding_days: int = 5,
                       stop_loss_pct: float = -5,
                       take_profit_pct: float = 10) -> Optional[Dict]:
        """단일 신호 백테스트"""
        code = signal['code']
        scan_date = signal['date']
        
        # 다음날 데이터 조회
        df = self.get_future_data(code, scan_date, holding_days + 2)
        
        if len(df) < 2:
            return None
        
        # 다음날 시가 진입
        entry_price = df.iloc[1]['open'] if len(df) > 1 else df.iloc[0]['open']
        entry_date = df.iloc[1]['date'] if len(df) > 1 else df.iloc[0]['date']
        
        # 보유 기간 시뮬레이션
        max_profit = 0
        max_loss = 0
        exit_price = entry_price
        exit_day = 0
        exit_reason = 'hold'
        final_return = 0
        
        for day_idx, (_, row) in enumerate(df.iloc[2:].iterrows(), 1):
            day_return = (row['close'] - entry_price) / entry_price * 100
            day_high_return = (row['high'] - entry_price) / entry_price * 100
            day_low_return = (row['low'] - entry_price) / entry_price * 100
            
            max_profit = max(max_profit, day_high_return)
            max_loss = min(max_loss, day_low_return)
            
            # 손절 체크
            if day_low_return <= stop_loss_pct:
                exit_price = entry_price * (1 + stop_loss_pct / 100)
                exit_day = day_idx
                exit_reason = 'stop_loss'
                final_return = stop_loss_pct
                break
            
            # 익절 체크
            if day_high_return >= take_profit_pct:
                exit_price = entry_price * (1 + take_profit_pct / 100)
                exit_day = day_idx
                exit_reason = 'take_profit'
                final_return = take_profit_pct
                break
            
            # 보유 기간 종료
            if day_idx >= holding_days:
                exit_price = row['close']
                exit_day = day_idx
                exit_reason = 'time_exit'
                final_return = day_return
                break
        
        # 루프 종료 후
        if exit_reason == 'hold' and len(df) > 2:
            last_row = df.iloc[-1]
            exit_price = last_row['close']
            exit_day = len(df) - 2
            exit_reason = 'data_end'
            final_return = (last_row['close'] - entry_price) / entry_price * 100
        
        # 신호 분류
        bullish_signals = [s for s in signal['signals'] if 'BULLISH' in s or 'TK_CROSS_BULLISH' in s or 'TRIPLE_BOTTOM' in s]
        bearish_signals = [s for s in signal['signals'] if 'BEARISH' in s or 'TK_CROSS_BEARISH' in s or 'TRIPLE_TOP' in s]
        
        return {
            'code': code,
            'name': signal['name'],
            'scan_date': scan_date,
            'entry_date': entry_date,
            'entry_price': entry_price,
            'scan_close': signal['close'],
            'signals': signal['signals'],
            'signal_count': signal['signal_count'],
            'bullish_signals': len(bullish_signals),
            'bearish_signals': len(bearish_signals),
            'exit_price': exit_price,
            'exit_day': exit_day,
            'final_return': final_return,
            'max_profit': max_profit,
            'max_loss': max_loss,
            'exit_reason': exit_reason,
        }
    
    def run_backtest(self, signals: List[Dict],
                    holding_days: int = 5,
                    stop_loss_pct: float = -5,
                    take_profit_pct: float = 10) -> Dict:
        """전체 백테스트"""
        print(f"\n🧪 백테스트 (보유: {holding_days}일, 손절: {stop_loss_pct}%, 익절: {take_profit_pct}%)")
        print("=" * 70)
        
        results = []
        for signal in signals:
            result = self.backtest_signal(signal, holding_days, stop_loss_pct, take_profit_pct)
            if result:
                results.append(result)
        
        if not results:
            return {}
        
        returns = [r['final_return'] for r in results]
        wins = len([r for r in results if r['final_return'] > 0])
        
        # 신호별 분석
        signal_performance = {}
        for r in results:
            for sig in r['signals']:
                if sig not in signal_performance:
                    signal_performance[sig] = {'count': 0, 'wins': 0, 'returns': []}
                signal_performance[sig]['count'] += 1
                signal_performance[sig]['returns'].append(r['final_return'])
                if r['final_return'] > 0:
                    signal_performance[sig]['wins'] += 1
        
        # 신호별 승률 계산
        for sig in signal_performance:
            count = signal_performance[sig]['count']
            signal_performance[sig]['win_rate'] = signal_performance[sig]['wins'] / count * 100 if count > 0 else 0
            signal_performance[sig]['avg_return'] = np.mean(signal_performance[sig]['returns'])
        
        exit_reasons = {}
        for r in results:
            reason = r['exit_reason']
            exit_reasons[reason] = exit_reasons.get(reason, 0) + 1
        
        return {
            'total_signals': len(results),
            'win_rate': wins / len(results) * 100,
            'avg_return': np.mean(returns),
            'median_return': np.median(returns),
            'max_return': max(returns),
            'min_return': min(returns),
            'exit_reasons': exit_reasons,
            'signal_performance': signal_performance,
            'results': results,
        }
    
    def print_report(self, stats: Dict):
        """리포트 출력"""
        print("\n" + "=" * 70)
        print("📊 일본 고전 기법 백테스트 결과")
        print("=" * 70)
        
        print(f"\n📈 전체 통계")
        print(f"  총 신호: {stats['total_signals']} 개")
        print(f"  승률: {stats['win_rate']:.1f}%")
        print(f"  평균 수익률: {stats['avg_return']:+.2f}%")
        print(f"  중간값: {stats['median_return']:+.2f}%")
        print(f"  최대 수익: {stats['max_return']:+.2f}%")
        print(f"  최대 손실: {stats['min_return']:+.2f}%")
        
        print(f"\n📉 청산 방식")
        for reason, count in stats['exit_reasons'].items():
            pct = count / stats['total_signals'] * 100
            label = {'stop_loss': '손절', 'take_profit': '익절', 
                    'time_exit': '기간종료', 'data_end': '데이터종료'}.get(reason, reason)
            print(f"  {label}: {count} ({pct:.1f}%)")
        
        print(f"\n🔔 신호별 성과")
        signal_perf = stats['signal_performance']
        sorted_signals = sorted(signal_perf.items(), key=lambda x: x[1]['win_rate'], reverse=True)
        
        for sig, perf in sorted_signals[:10]:
            if perf['count'] >= 5:  # 5회 이상 발생한 신호만
                print(f"  {sig}: 승률 {perf['win_rate']:.1f}% (n={perf['count']}), 평균 {perf['avg_return']:+.2f}%")
        
        print(f"\n🏆 TOP 10 수익")
        top_gainers = sorted(stats['results'], key=lambda x: x['final_return'], reverse=True)[:10]
        for r in top_gainers:
            print(f"  {r['name']}: {r['final_return']:+.1f}% (신호: {len(r['signals'])}개)")
        
        print(f"\n💔 TOP 10 손실")
        top_losers = sorted(stats['results'], key=lambda x: x['final_return'])[:10]
        for r in top_losers:
            print(f"  {r['name']}: {r['final_return']:+.1f}% (신호: {len(r['signals'])}개)")


def main():
    backtester = JapanesePatternBacktester()
    
    # 거래일 목록
    end_date = '2026-04-08'
    start_date = '2026-01-01'
    
    conn = sqlite3.connect(backtester.db_path)
    cursor = conn.execute("""
        SELECT DISTINCT date FROM price_data 
        WHERE date BETWEEN ? AND ?
        ORDER BY date
    """, (start_date, end_date))
    dates = [row[0] for row in cursor.fetchall()]
    conn.close()
    
    print(f"\n📅 스캔 기간: {start_date} ~ {end_date} ({len(dates)} 거래일)")
    print("=" * 70)
    
    all_signals = []
    for date in dates:
        signals = backtester.scanner.scan_market(date, min_signals=1)
        all_signals.extend(signals)
    
    print("\n" + "=" * 70)
    print(f"📊 총 신호: {len(all_signals)} 개")
    
    if all_signals:
        # 시나리오 1: 보수적
        print("\n" + "=" * 70)
        print("📊 시나리오 1: 보수적")
        stats1 = backtester.run_backtest(all_signals, holding_days=5, 
                                         stop_loss_pct=-5, take_profit_pct=10)
        backtester.print_report(stats1)
        
        # 시나리오 2: 공격적
        print("\n" + "=" * 70)
        print("📊 시나리오 2: 공격적")
        stats2 = backtester.run_backtest(all_signals, holding_days=10,
                                         stop_loss_pct=-7, take_profit_pct=15)
        backtester.print_report(stats2)
        
        # 결과 저장
        os.makedirs('reports', exist_ok=True)
        output_file = f'reports/japanese_pattern_backtest_{start_date}_{end_date}.json'
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump({
                'strategy': 'japanese_classic_patterns',
                'methods': ['sakata_5_methods', 'ichimoku_cloud'],
                'scenario1': {k: v for k, v in stats1.items() if k != 'results'},
                'scenario2': {k: v for k, v in stats2.items() if k != 'results'},
            }, f, ensure_ascii=False, indent=2)
        
        print(f"\n💾 결과 저장: {output_file}")
    else:
        print("\n❌ 신호 없음")


if __name__ == '__main__':
    main()
