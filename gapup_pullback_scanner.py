#!/usr/bin/env python3
"""
Gap-Up Pullback Scanner (갭상승 눌림목 스캐너)
============================================
원본 조건:
- 전일대비 18% 이상 상승
- 거래대금 500억원 이상  
- 양봉 (시가 < 종가)
- 전일 종가 2,000원 이상

개선안: 눌림목 대기 (2-3일 후 반등)
- 스캔 후 1~3일 대기
- 조정폭 -3% ~ -10% 확인
- 반등 신호 (RSI 상승, 양봉) 확인 시 진입
"""

import sqlite3
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import List, Dict, Tuple, Optional
import json
import os


class GapUpPullbackScanner:
    """갭상승 눌림목 스캐너"""
    
    def __init__(self, db_path: str = 'data/level1_prices.db'):
        self.db_path = db_path
        
    def get_price_data(self, code: str, start_date: str, days: int = 20) -> pd.DataFrame:
        """특정 종목의 가격 데이터 조회"""
        conn = sqlite3.connect(self.db_path)
        
        query = """
        SELECT date, open, high, low, close, volume
        FROM price_data
        WHERE code = ? AND date >= ?
        ORDER BY date
        LIMIT ?
        """
        
        df = pd.read_sql(query, conn, params=(code, start_date, days))
        conn.close()
        
        return df
    
    def calculate_rsi(self, prices: pd.Series, period: int = 14) -> pd.Series:
        """RSI 계산"""
        delta = prices.diff()
        gain = delta.where(delta > 0, 0).rolling(window=period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
        rs = gain / loss
        return 100 - (100 / (1 + rs))
    
    def find_pullback_entries(self, date: str, 
                              pullback_days: int = 3,
                              min_pullback_pct: float = -3,
                              max_pullback_pct: float = -10) -> List[Dict]:
        """
        눌림목 진입 포인트 탐색
        
        로직:
        1. N일전 18%+ 상승 종목 탐색
        2. 그 이후 눌림목 확인 (-3% ~ -10%)
        3. 반등 신호 확인 (RSI 상승, 양봉)
        """
        conn = sqlite3.connect(self.db_path)
        
        # N일간 데이터 조회
        query = """
        WITH gap_up AS (
            -- N일간 18%+ 상승 종목
            SELECT DISTINCT p1.code, p1.name, p1.date as gap_date, p1.close as gap_close,
                   ((p1.close - p2.close) / p2.close * 100) as gap_pct,
                   (p1.close * p1.volume) as gap_value
            FROM price_data p1
            JOIN price_data p2 ON p1.code = p2.code 
                AND p2.date = date(p1.date, '-1 day')
            WHERE p1.date BETWEEN date(?, ?) AND ?
                AND ((p1.close - p2.close) / p2.close * 100) >= 18
                AND (p1.close * p1.volume) >= 5e9
                AND p1.open < p1.close
                AND p2.close >= 2000
        )
        SELECT * FROM gap_up
        ORDER BY gap_date DESC
        """
        
        df_gap = pd.read_sql(query, conn, 
                            params=(date, f'-{pullback_days} days', date))
        conn.close()
        
        if df_gap.empty:
            return []
        
        entries = []
        for _, row in df_gap.iterrows():
            code = row['code']
            gap_date = row['gap_date']
            gap_close = row['gap_close']
            
            # 갭상승 이후 데이터 조회
            df_prices = self.get_price_data(code, gap_date, 10)
            
            if len(df_prices) < 2:
                continue
            
            gap_idx = df_prices[df_prices['date'] == gap_date].index
            if len(gap_idx) == 0:
                continue
            gap_idx = gap_idx[0]
            
            # 눌림목 확인 (갭상승일 다음날부터 오늘까지)
            for i in range(gap_idx + 1, len(df_prices)):
                current = df_prices.iloc[i]
                
                # 갭종가 대비 조정폭
                pullback_pct = (current['low'] - gap_close) / gap_close * 100
                close_pct = (current['close'] - gap_close) / gap_close * 100
                
                # 눌림목 범위 확인
                if min_pullback_pct >= pullback_pct >= max_pullback_pct:
                    # 반등 조건 확인
                    is_bullish = current['close'] > current['open']
                    
                    # RSI 계산 (최소 5일 필요)
                    if i >= 5:
                        rsi_values = self.calculate_rsi(df_prices['close'][:i+1])
                        current_rsi = rsi_values.iloc[-1]
                        prev_rsi = rsi_values.iloc[-2]
                        rsi_rising = current_rsi > prev_rsi and current_rsi < 50
                    else:
                        current_rsi = None
                        rsi_rising = False
                    
                    # 진입 조건: 양봉 또는 RSI 상승
                    if is_bullish or rsi_rising:
                        entries.append({
                            'code': code,
                            'name': row['name'],
                            'entry_date': current['date'],
                            'gap_date': gap_date,
                            'gap_close': float(gap_close),
                            'gap_pct': float(row['gap_pct']),
                            'entry_open': float(current['open']),
                            'entry_close': float(current['close']),
                            'entry_low': float(current['low']),
                            'pullback_pct': float(pullback_pct),
                            'close_pct': float(close_pct),
                            'is_bullish': is_bullish,
                            'rsi': float(current_rsi) if current_rsi else None,
                            'rsi_rising': rsi_rising,
                            'days_after_gap': i - gap_idx,
                        })
                        break  # 첫 진입 포인트만
        
        return entries
    
    def scan(self, date: str) -> List[Dict]:
        """특정 날짜 스캔"""
        print(f"🔍 스캔 중: {date}")
        
        entries = self.find_pullback_entries(date)
        
        print(f"  ✅ 눌림목 진입: {len(entries)} 종목")
        return entries


class PullbackBacktester:
    """눌림목 전략 백테스터"""
    
    def __init__(self, db_path: str = 'data/level1_prices.db'):
        self.db_path = db_path
    
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
    
    def backtest_entry(self, entry: Dict,
                       holding_days: int = 7,
                       stop_loss_pct: float = -5,
                       take_profit_pct: float = 15) -> Optional[Dict]:
        """단일 진입 백테스트"""
        code = entry['code']
        entry_date = entry['entry_date']
        entry_price = entry['entry_close']
        
        df = self.get_future_data(code, entry_date, holding_days)
        
        if len(df) < 2:
            return None
        
        max_profit = 0
        max_loss = 0
        exit_price = entry_price
        exit_day = 0
        exit_reason = 'hold'
        final_return = 0
        
        for day_idx, (_, row) in enumerate(df.iloc[1:].iterrows(), 1):
            day_return = (row['close'] - entry_price) / entry_price * 100
            day_high_return = (row['high'] - entry_price) / entry_price * 100
            day_low_return = (row['low'] - entry_price) / entry_price * 100
            
            max_profit = max(max_profit, day_high_return)
            max_loss = min(max_loss, day_low_return)
            
            if day_low_return <= stop_loss_pct:
                exit_price = entry_price * (1 + stop_loss_pct / 100)
                exit_day = day_idx
                exit_reason = 'stop_loss'
                final_return = stop_loss_pct
                break
            
            if day_high_return >= take_profit_pct:
                exit_price = entry_price * (1 + take_profit_pct / 100)
                exit_day = day_idx
                exit_reason = 'take_profit'
                final_return = take_profit_pct
                break
            
            if day_idx >= holding_days:
                exit_price = row['close']
                exit_day = day_idx
                exit_reason = 'time_exit'
                final_return = day_return
                break
        
        if exit_reason == 'hold' and len(df) > 1:
            last_row = df.iloc[-1]
            exit_price = last_row['close']
            exit_day = len(df) - 1
            exit_reason = 'data_end'
            final_return = (last_row['close'] - entry_price) / entry_price * 100
        
        return {
            'code': code,
            'name': entry['name'],
            'entry_date': entry_date,
            'gap_date': entry['gap_date'],
            'entry_price': entry_price,
            'pullback_pct': entry['pullback_pct'],
            'exit_price': exit_price,
            'exit_day': exit_day,
            'final_return': final_return,
            'max_profit': max_profit,
            'max_loss': max_loss,
            'exit_reason': exit_reason,
        }
    
    def run_backtest(self, entries: List[Dict],
                     holding_days: int = 7,
                     stop_loss_pct: float = -5,
                     take_profit_pct: float = 15) -> Dict:
        """전체 백테스트"""
        print(f"\n🧪 눌림목 백테스트 (보유: {holding_days}일)")
        print("=" * 60)
        
        results = []
        for entry in entries:
            result = self.backtest_entry(entry, holding_days, stop_loss_pct, take_profit_pct)
            if result:
                results.append(result)
        
        if not results:
            return {}
        
        returns = [r['final_return'] for r in results]
        wins = len([r for r in results if r['final_return'] > 0])
        
        exit_reasons = {}
        for r in results:
            reason = r['exit_reason']
            exit_reasons[reason] = exit_reasons.get(reason, 0) + 1
        
        return {
            'total_entries': len(results),
            'win_rate': wins / len(results) * 100,
            'avg_return': np.mean(returns),
            'median_return': np.median(returns),
            'max_return': max(returns),
            'min_return': min(returns),
            'exit_reasons': exit_reasons,
            'results': results,
        }
    
    def print_report(self, stats: Dict):
        """리포트 출력"""
        print("\n" + "=" * 60)
        print("📊 눌림목 전략 백테스트 결과")
        print("=" * 60)
        
        print(f"\n📈 전체 통계")
        print(f"  총 진입: {stats['total_entries']} 개")
        print(f"  승률: {stats['win_rate']:.1f}%")
        print(f"  평균 수익률: {stats['avg_return']:+.2f}%")
        print(f"  중간값: {stats['median_return']:+.2f}%")
        print(f"  최대 수익: {stats['max_return']:+.2f}%")
        print(f"  최대 손실: {stats['min_return']:+.2f}%")
        
        print(f"\n📉 청산 방식")
        for reason, count in stats['exit_reasons'].items():
            pct = count / stats['total_entries'] * 100
            label = {'stop_loss': '손절', 'take_profit': '익절', 'time_exit': '기간종료', 'data_end': '데이터종료'}.get(reason, reason)
            print(f"  {label}: {count} ({pct:.1f}%)")
        
        print(f"\n🏆 TOP 5 수익")
        top_gainers = sorted(stats['results'], key=lambda x: x['final_return'], reverse=True)[:5]
        for r in top_gainers:
            print(f"  {r['name']}: {r['final_return']:+.1f}% (갭{r['pullback_pct']:.1f}%)")
        
        print(f"\n💔 TOP 5 손실")
        top_losers = sorted(stats['results'], key=lambda x: x['final_return'])[:5]
        for r in top_losers:
            print(f"  {r['name']}: {r['final_return']:+.1f}% (갭{r['pullback_pct']:.1f}%)")


def main():
    scanner = GapUpPullbackScanner()
    
    # 최근 3개월 스캔
    end_date = '2026-04-09'
    start_date = '2026-01-01'
    
    # 거래일 목록
    conn = sqlite3.connect(scanner.db_path)
    cursor = conn.execute("""
        SELECT DISTINCT date FROM price_data 
        WHERE date BETWEEN ? AND ?
        ORDER BY date
    """, (start_date, end_date))
    dates = [row[0] for row in cursor.fetchall()]
    conn.close()
    
    print(f"\n📅 스캔 기간: {start_date} ~ {end_date} ({len(dates)} 거래일)")
    print("=" * 60)
    
    all_entries = []
    for date in dates:
        entries = scanner.scan(date)
        all_entries.extend(entries)
    
    print("\n" + "=" * 60)
    print(f"📊 총 눌림목 진입: {len(all_entries)} 개")
    
    if all_entries:
        backtester = PullbackBacktester()
        stats = backtester.run_backtest(all_entries)
        backtester.print_report(stats)
        
        # 결과 저장
        os.makedirs('reports', exist_ok=True)
        output_file = f'reports/pullback_backtest_{start_date}_{end_date}.json'
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump({
                'strategy': 'gapup_pullback',
                'scan_conditions': {
                    'min_gap_pct': 18,
                    'min_trading_value': 5000000000,
                    'pullback_days': 3,
                    'min_pullback_pct': -3,
                    'max_pullback_pct': -10,
                },
                'backtest_params': {
                    'holding_days': 7,
                    'stop_loss_pct': -5,
                    'take_profit_pct': 15,
                },
                'statistics': {k: v for k, v in stats.items() if k != 'results'},
                'results': stats.get('results', []),
            }, f, ensure_ascii=False, indent=2)
        
        print(f"\n💾 결과 저장: {output_file}")
    else:
        print("\n❌ 진입 포인트 없음")


if __name__ == '__main__':
    main()
