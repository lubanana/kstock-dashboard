#!/usr/bin/env python3
"""
Gap-Up Momentum Scanner (갭상승 모멘텀 스캐너)
============================================
조건:
- 전일대비 18% 이상 상승
- 거래대금 500억원 이상  
- 양봉 (시가 < 종가)
- 전일 종가 2,000원 이상

백테스트 포함
"""

import sqlite3
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import List, Dict, Tuple, Optional
import json
import os


class GapUpMomentumScanner:
    """갭상승 모멘텀 스캐너"""
    
    def __init__(self, db_path: str = 'data/level1_prices.db'):
        self.db_path = db_path
        self.signals: List[Dict] = []
        
    def get_data_for_date(self, date: str) -> pd.DataFrame:
        """특정 날짜의 모든 종목 데이터 조회"""
        conn = sqlite3.connect(self.db_path)
        
        # 해당 날짜와 전일 데이터 조회
        query = """
        SELECT 
            p1.code, p1.name, p1.date, 
            p1.open as today_open, p1.high as today_high, 
            p1.low as today_low, p1.close as today_close,
            p1.volume, p1.close * p1.volume as trading_value,
            p2.close as prev_close
        FROM price_data p1
        LEFT JOIN price_data p2 ON p1.code = p2.code 
            AND p2.date = date(?, '-1 day')
        WHERE p1.date = ?
            AND p2.close IS NOT NULL  -- 전일 데이터 필수
        """
        
        df = pd.read_sql(query, conn, params=(date, date))
        conn.close()
        
        return df
    
    def scan(self, date: str) -> List[Dict]:
        """
        특정 날짜 스캔
        
        조건:
        1. 전일대비 18% 이상 상승
        2. 거래대금 500억원 이상
        3. 양봉 (시가 < 종가)
        4. 전일 종가 2,000원 이상
        """
        print(f"🔍 스캔 중: {date}")
        
        df = self.get_data_for_date(date)
        
        if df.empty:
            print(f"  ⚠️ 데이터 없음: {date}")
            return []
        
        # 수익률 계산
        df['change_pct'] = (df['today_close'] - df['prev_close']) / df['prev_close'] * 100
        
        # 필터 적용
        conditions = (
            (df['change_pct'] >= 18) &           # 18% 이상 상승
            (df['trading_value'] >= 5e9) &      # 500억 이상 거래대금
            (df['today_open'] < df['today_close']) &  # 양봉
            (df['prev_close'] >= 2000)          # 전일 종가 2,000원 이상
        )
        
        signals = df[conditions].copy()
        signals = signals.sort_values('change_pct', ascending=False)
        
        print(f"  📊 대상: {len(df)} 종목")
        print(f"  ✅ 신호: {len(signals)} 종목")
        
        # 결과 포맷팅
        results = []
        for _, row in signals.iterrows():
            results.append({
                'code': row['code'],
                'name': row['name'],
                'date': row['date'],
                'prev_close': float(row['prev_close']),
                'today_open': float(row['today_open']),
                'today_high': float(row['today_high']),
                'today_low': float(row['today_low']),
                'today_close': float(row['today_close']),
                'change_pct': float(row['change_pct']),
                'volume': int(row['volume']),
                'trading_value': float(row['trading_value']),
            })
        
        return results
    
    def scan_range(self, start_date: str, end_date: str) -> List[Dict]:
        """기간 스캔"""
        all_signals = []
        
        # 거래일 목록 생성
        conn = sqlite3.connect(self.db_path)
        cursor = conn.execute("""
            SELECT DISTINCT date FROM price_data 
            WHERE date BETWEEN ? AND ?
            ORDER BY date
        """, (start_date, end_date))
        dates = [row[0] for row in cursor.fetchall()]
        conn.close()
        
        print(f"\n📅 스캔 기간: {start_date} ~ {end_date} ({len(dates)} 거래일)")
        print("=" * 60)
        
        for date in dates:
            signals = self.scan(date)
            all_signals.extend(signals)
        
        print("\n" + "=" * 60)
        print(f"📊 총 신호: {len(all_signals)} 개")
        
        return all_signals


class GapUpBacktester:
    """갭상승 전략 백테스터"""
    
    def __init__(self, db_path: str = 'data/level1_prices.db'):
        self.db_path = db_path
        
    def get_future_data(self, code: str, entry_date: str, days: int = 20) -> pd.DataFrame:
        """진입 후 미래 데이터 조회"""
        conn = sqlite3.connect(self.db_path)
        
        query = """
        SELECT date, open, high, low, close, volume
        FROM price_data
        WHERE code = ? AND date > ?
        ORDER BY date
        LIMIT ?
        """
        
        df = pd.read_sql(query, conn, params=(code, entry_date, days))
        conn.close()
        
        return df
    
    def backtest_signal(self, signal: Dict, 
                        holding_days: int = 10,
                        stop_loss_pct: float = -7,
                        take_profit_pct: float = 20) -> Dict:
        """
        단일 신호 백테스트
        
        전략:
        - 진입: 다음날 시가 (스캔 당일은 이미 상승했으므로)
        - 보유: holding_days 또는 손절/익절
        """
        code = signal['code']
        entry_date = signal['date']
        scan_high = signal['today_high']
        scan_close = signal['today_close']
        
        # 다음날 데이터 조회
        df = self.get_future_data(code, entry_date, holding_days + 2)
        
        if len(df) < 2:
            return None
        
        # 다음날 시가에 진입
        entry_price = df.iloc[0]['open']
        
        # 보유 기간 동안 수익률 계산
        max_profit = 0
        max_loss = 0
        exit_price = entry_price
        exit_day = 0
        exit_reason = 'hold'
        final_return = 0  # 초기화
        
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
        
        # 루프가 break 없이 종료된 경우 (데이터 부족)
        if exit_reason == 'hold' and len(df) > 1:
            last_row = df.iloc[-1]
            exit_price = last_row['close']
            exit_day = len(df) - 1
            exit_reason = 'data_end'
            final_return = (last_row['close'] - entry_price) / entry_price * 100
        
        return {
            'code': code,
            'name': signal['name'],
            'entry_date': entry_date,
            'scan_close': scan_close,
            'scan_change_pct': signal['change_pct'],
            'entry_price': entry_price,
            'exit_price': exit_price,
            'exit_day': exit_day,
            'final_return': final_return,
            'max_profit': max_profit,
            'max_loss': max_loss,
            'exit_reason': exit_reason,
            'trading_value': signal['trading_value'],
        }
    
    def run_backtest(self, signals: List[Dict], 
                     holding_days: int = 10,
                     stop_loss_pct: float = -7,
                     take_profit_pct: float = 20) -> Dict:
        """전체 백테스트 실행"""
        print(f"\n🧪 백테스트 시작 (보유기간: {holding_days}일)")
        print("=" * 60)
        
        results = []
        for signal in signals:
            result = self.backtest_signal(
                signal, holding_days, stop_loss_pct, take_profit_pct
            )
            if result:
                results.append(result)
        
        if not results:
            print("❌ 백테스트 결과 없음")
            return {}
        
        # 결과 분석
        returns = [r['final_return'] for r in results]
        wins = len([r for r in results if r['final_return'] > 0])
        losses = len([r for r in results if r['final_return'] <= 0])
        
        exit_reasons = {}
        for r in results:
            reason = r['exit_reason']
            exit_reasons[reason] = exit_reasons.get(reason, 0) + 1
        
        stats = {
            'total_signals': len(results),
            'win_rate': wins / len(results) * 100,
            'avg_return': np.mean(returns),
            'median_return': np.median(returns),
            'max_return': max(returns),
            'min_return': min(returns),
            'wins': wins,
            'losses': losses,
            'exit_reasons': exit_reasons,
            'results': results,
        }
        
        return stats
    
    def print_report(self, stats: Dict):
        """백테스트 리포트 출력"""
        print("\n" + "=" * 60)
        print("📊 백테스트 결과")
        print("=" * 60)
        
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
            label = {'stop_loss': '손절', 'take_profit': '익절', 'time_exit': '기간종료'}.get(reason, reason)
            print(f"  {label}: {count} ({pct:.1f}%)")
        
        # TOP 수익/손실
        print(f"\n🏆 TOP 5 수익")
        top_gainers = sorted(stats['results'], key=lambda x: x['final_return'], reverse=True)[:5]
        for r in top_gainers:
            print(f"  {r['name']} ({r['code']}): {r['final_return']:+.1f}% ({r['exit_reason']})")
        
        print(f"\n💔 TOP 5 손실")
        top_losers = sorted(stats['results'], key=lambda x: x['final_return'])[:5]
        for r in top_losers:
            print(f"  {r['name']} ({r['code']}): {r['final_return']:+.1f}% ({r['exit_reason']})")


def main():
    # 스캐너 생성
    scanner = GapUpMomentumScanner()
    
    # 최근 3개월 백테스트
    end_date = '2026-04-09'
    start_date = '2026-01-01'
    
    # 스캔 실행
    signals = scanner.scan_range(start_date, end_date)
    
    if signals:
        # 백테스트 실행
        backtester = GapUpBacktester()
        stats = backtester.run_backtest(
            signals, 
            holding_days=10,
            stop_loss_pct=-7,
            take_profit_pct=20
        )
        
        backtester.print_report(stats)
        
        # 결과 저장
        os.makedirs('reports', exist_ok=True)
        output_file = f'reports/gapup_backtest_{start_date}_{end_date}.json'
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump({
                'scan_conditions': {
                    'min_change_pct': 18,
                    'min_trading_value': 5000000000,
                    'require_bullish': True,
                    'min_prev_close': 2000,
                },
                'backtest_params': {
                    'holding_days': 10,
                    'stop_loss_pct': -7,
                    'take_profit_pct': 20,
                },
                'statistics': {k: v for k, v in stats.items() if k != 'results'},
                'results': stats.get('results', []),
            }, f, ensure_ascii=False, indent=2)
        
        print(f"\n💾 결과 저장: {output_file}")
    else:
        print("\n❌ 스캔 결과 없음")


if __name__ == '__main__':
    main()
