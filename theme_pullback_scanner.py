#!/usr/bin/env python3
"""
Theme Momentum Pullback Scanner (테마 모멘텀 눌림목 스캐너)
==========================================================
전략 개념:
1. 특정 테마/종목에 관심 집중 (거래대금 급증)
2. 다음날 하락 (숏커버링/이익실현 매물)
3. 눌림목에서 매수 (반등 노리기)

조건:
- 당일 거래대금 / 20일 평균 거래대금 > N배 (기본 5배)
- 당일 상승률 > 10% (강한 모멘텀 확인)
- 다음날 하락 (-1% 이하 또는 시가 < 전일 종가)
- 전일 종가 2,000원 이상
"""

import sqlite3
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Tuple
import json
import os


class ThemeMomentumScanner:
    """테마 모멘텀 스캐너"""
    
    def __init__(self, db_path: str = 'data/level1_prices.db'):
        self.db_path = db_path
        
    def get_stock_data_with_volume_avg(self, code: str, date: str, days: int = 25) -> pd.DataFrame:
        """종목의 과거 데이터 + 20일 평균 거래대금 조회"""
        conn = sqlite3.connect(self.db_path)
        
        # 해당 날짜 기준 과거 N일 데이터
        query = """
        SELECT date, open, high, low, close, volume, (close * volume) as value
        FROM price_data
        WHERE code = ? AND date <= ?
        ORDER BY date DESC
        LIMIT ?
        """
        
        df = pd.read_sql(query, conn, params=(code, date, days))
        conn.close()
        
        if len(df) < 21:
            return pd.DataFrame()
        
        # 20일 평균 거래대금 계산 (당일 제외)
        df = df.sort_values('date')  # 과거 -> 최근
        df['value_ma20'] = df['value'].shift(1).rolling(window=20).mean()
        df['value_ratio'] = df['value'] / df['value_ma20']
        
        # 당일 데이터만 반환
        return df[df['date'] == date]
    
    def scan_surge_stocks(self, date: str, 
                          min_value_ratio: float = 5.0,
                          min_change_pct: float = 10.0) -> List[Dict]:
        """
        관심 집중 종목 스캔 (거래대금 급증)
        
        조건:
        - 거래대금 / 20일 평균 >= min_value_ratio
        - 당일 상승률 >= min_change_pct
        - 종가 >= 2,000원
        """
        conn = sqlite3.connect(self.db_path)
        
        # 해당 날짜의 모든 종목 조회
        query = """
        SELECT code, name, date, open, high, low, close, volume,
               (close * volume) as trading_value,
               ((close - open) / open * 100) as change_pct
        FROM price_data
        WHERE date = ? AND close >= 2000
        """
        
        df = pd.read_sql(query, conn, params=(date,))
        conn.close()
        
        if df.empty:
            return []
        
        # 각 종목별 20일 평균 대비 거래대금 비율 계산
        results = []
        for _, row in df.iterrows():
            code = row['code']
            
            # 20일 평균 대비 계산
            avg_df = self.get_stock_data_with_volume_avg(code, date)
            if avg_df.empty:
                continue
            
            value_ratio = avg_df['value_ratio'].iloc[0]
            
            # 조건 체크
            if (value_ratio >= min_value_ratio and 
                row['change_pct'] >= min_change_pct):
                
                results.append({
                    'code': code,
                    'name': row['name'],
                    'date': row['date'],
                    'open': float(row['open']),
                    'high': float(row['high']),
                    'low': float(row['low']),
                    'close': float(row['close']),
                    'change_pct': float(row['change_pct']),
                    'volume': int(row['volume']),
                    'trading_value': float(row['trading_value']),
                    'value_ratio': float(value_ratio),
                })
        
        # 거래대금 비율 높은 순 정렬
        results = sorted(results, key=lambda x: x['value_ratio'], reverse=True)
        return results
    
    def check_next_day_drop(self, code: str, scan_date: str,
                           min_drop_pct: float = -1.0) -> Optional[Dict]:
        """
        다음날 하락 여부 확인
        
        반환:
        - 하락 시: {'next_date', 'next_open', 'next_close', 'drop_pct', ...}
        - 미하락 시: None
        """
        conn = sqlite3.connect(self.db_path)
        
        query = """
        SELECT date, open, high, low, close, volume
        FROM price_data
        WHERE code = ? AND date > ?
        ORDER BY date
        LIMIT 1
        """
        
        df = pd.read_sql(query, conn, params=(code, scan_date))
        conn.close()
        
        if df.empty:
            return None
        
        next_row = df.iloc[0]
        next_open = float(next_row['open'])
        next_close = float(next_row['close'])
        next_high = float(next_row['high'])
        next_low = float(next_row['low'])
        
        # 스캔일 종가 조회
        conn = sqlite3.connect(self.db_path)
        cursor = conn.execute(
            "SELECT close FROM price_data WHERE code = ? AND date = ?",
            (code, scan_date)
        )
        scan_close = cursor.fetchone()
        conn.close()
        
        if not scan_close:
            return None
        
        scan_close = float(scan_close[0])
        
        # 하락률 계산 (시가 기준 또는 종가 기준)
        open_drop_pct = (next_open - scan_close) / scan_close * 100
        close_drop_pct = (next_close - scan_close) / scan_close * 100
        
        # 하락 조건: 시가 또는 종가가 1% 이상 하락
        if open_drop_pct <= min_drop_pct or close_drop_pct <= min_drop_pct:
            return {
                'next_date': next_row['date'],
                'next_open': next_open,
                'next_high': next_high,
                'next_low': next_low,
                'next_close': next_close,
                'scan_close': scan_close,
                'open_drop_pct': open_drop_pct,
                'close_drop_pct': close_drop_pct,
            }
        
        return None
    
    def scan_pullback_entries(self, date: str,
                              min_value_ratio: float = 5.0,
                              min_change_pct: float = 10.0,
                              min_drop_pct: float = -1.0) -> List[Dict]:
        """
        테마 눌림목 진입 포인트 스캔
        
        Day 1: 거래대금 급증 + 상승
        Day 2: 하락 (진입일)
        """
        print(f"🔍 스캔 중: {date}")
        
        # Day 1: 관심 집중 종목
        surge_stocks = self.scan_surge_stocks(date, min_value_ratio, min_change_pct)
        print(f"  📈 관심집중: {len(surge_stocks)} 종목")
        
        if not surge_stocks:
            return []
        
        # Day 2: 하락 확인
        entries = []
        for stock in surge_stocks:
            drop_info = self.check_next_day_drop(
                stock['code'], date, min_drop_pct
            )
            
            if drop_info:
                entries.append({
                    **stock,
                    **drop_info,
                    'entry_price': drop_info['next_open'],  # 다음날 시가 진입
                })
        
        print(f"  ✅ 눌림목 진입: {len(entries)} 종목")
        return entries


class ThemePullbackBacktester:
    """테마 눌림목 백테스터"""
    
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
                       holding_days: int = 5,
                       stop_loss_pct: float = -5,
                       take_profit_pct: float = 10) -> Optional[Dict]:
        """단일 진입 백테스트"""
        code = entry['code']
        entry_date = entry['next_date']  # 다음날 (하락일)
        entry_price = entry['entry_price']  # 시가 진입
        
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
        if exit_reason == 'hold' and len(df) > 1:
            last_row = df.iloc[-1]
            exit_price = last_row['close']
            exit_day = len(df) - 1
            exit_reason = 'data_end'
            final_return = (last_row['close'] - entry_price) / entry_price * 100
        
        return {
            'code': code,
            'name': entry['name'],
            'scan_date': entry['date'],
            'entry_date': entry_date,
            'scan_close': entry['scan_close'],
            'entry_price': entry_price,
            'scan_change_pct': entry['change_pct'],
            'value_ratio': entry['value_ratio'],
            'open_drop_pct': entry['open_drop_pct'],
            'exit_price': exit_price,
            'exit_day': exit_day,
            'final_return': final_return,
            'max_profit': max_profit,
            'max_loss': max_loss,
            'exit_reason': exit_reason,
        }
    
    def run_backtest(self, entries: List[Dict],
                     holding_days: int = 5,
                     stop_loss_pct: float = -5,
                     take_profit_pct: float = 10) -> Dict:
        """전체 백테스트"""
        print(f"\n🧪 백테스트 시작 (보유: {holding_days}일)")
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
        print("📊 테마 눌림목 백테스트 결과")
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
            label = {'stop_loss': '손절', 'take_profit': '익절', 
                    'time_exit': '기간종료', 'data_end': '데이터종료'}.get(reason, reason)
            print(f"  {label}: {count} ({pct:.1f}%)")
        
        print(f"\n🏆 TOP 10 수익")
        top_gainers = sorted(stats['results'], key=lambda x: x['final_return'], reverse=True)[:10]
        for r in top_gainers:
            print(f"  {r['name']}: {r['final_return']:+.1f}% "
                  f"(거래대금 {r['value_ratio']:.1f}배, 하락 {r['open_drop_pct']:.1f}%)")
        
        print(f"\n💔 TOP 10 손실")
        top_losers = sorted(stats['results'], key=lambda x: x['final_return'])[:10]
        for r in top_losers:
            print(f"  {r['name']}: {r['final_return']:+.1f}% "
                  f"(거래대금 {r['value_ratio']:.1f}배, 하락 {r['open_drop_pct']:.1f}%)")


def main():
    scanner = ThemeMomentumScanner()
    
    # 최근 3개월 백테스트
    end_date = '2026-04-08'  # 04-09까지 하면 다음날 데이터 없음
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
        entries = scanner.scan_pullback_entries(
            date,
            min_value_ratio=5.0,    # 거래대금 5배 이상
            min_change_pct=10.0,    # 10% 이상 상승
            min_drop_pct=-1.0       # 1% 이상 하락
        )
        all_entries.extend(entries)
    
    print("\n" + "=" * 60)
    print(f"📊 총 눌림목 진입: {len(all_entries)} 개")
    
    if all_entries:
        backtester = ThemePullbackBacktester()
        
        # 시나리오 1: 보수적 (손절 -5%, 익절 10%)
        print("\n" + "=" * 60)
        print("📊 시나리오 1: 보수적 (보유 5일, 손절 -5%, 익절 10%)")
        stats1 = backtester.run_backtest(all_entries, holding_days=5, 
                                         stop_loss_pct=-5, take_profit_pct=10)
        backtester.print_report(stats1)
        
        # 시나리오 2: 공격적 (손절 -7%, 익절 20%)
        print("\n" + "=" * 60)
        print("📊 시나리오 2: 공격적 (보유 7일, 손절 -7%, 익절 20%)")
        stats2 = backtester.run_backtest(all_entries, holding_days=7,
                                         stop_loss_pct=-7, take_profit_pct=20)
        backtester.print_report(stats2)
        
        # 결과 저장
        os.makedirs('reports', exist_ok=True)
        output_file = f'reports/theme_pullback_backtest_{start_date}_{end_date}.json'
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump({
                'strategy': 'theme_momentum_pullback',
                'scan_conditions': {
                    'min_value_ratio': 5.0,
                    'min_change_pct': 10.0,
                    'min_drop_pct': -1.0,
                },
                'scenario1': {k: v for k, v in stats1.items() if k != 'results'},
                'scenario2': {k: v for k, v in stats2.items() if k != 'results'},
                'entries': all_entries,
            }, f, ensure_ascii=False, indent=2)
        
        print(f"\n💾 결과 저장: {output_file}")
    else:
        print("\n❌ 진입 포인트 없음")


if __name__ == '__main__':
    main()
