#!/usr/bin/env python3
"""
Japanese Strategy Full Market Backtest
======================================
일본 전략 전체 종목 대상 종합 백테스트

전략:
- Ichimoku: 5/10/20 (단기)
- Entry: 다음날 저가
- SL/TP: -5%/+10%
- Holding: 5일
"""

import sqlite3
import pandas as pd
import numpy as np
from typing import List, Dict, Optional
import json
from datetime import datetime
import os


class FullMarketBacktester:
    """전체 시장 백테스터"""
    
    def __init__(self, db_path: str = 'data/level1_prices.db'):
        self.db_path = db_path
    
    def get_all_stocks(self, date: str, min_price: int = 1000) -> List[Dict]:
        """전체 종목 조회"""
        conn = sqlite3.connect(self.db_path)
        
        query = """
        SELECT code, name, close, volume
        FROM price_data
        WHERE date = ? AND close >= ?
        ORDER BY code
        """
        
        df = pd.read_sql(query, conn, params=(date, min_price))
        conn.close()
        
        return df.to_dict('records')
    
    def get_stock_data(self, code: str, end_date: str, days: int = 80) -> pd.DataFrame:
        """종목 데이터 조회"""
        conn = sqlite3.connect(self.db_path)
        
        query = """
        SELECT date, open, high, low, close, volume
        FROM price_data
        WHERE code = ? AND date <= ?
        ORDER BY date DESC
        LIMIT ?
        """
        
        df = pd.read_sql(query, conn, params=(code, end_date, days))
        conn.close()
        
        return df.sort_values('date').reset_index(drop=True)
    
    def get_future_data(self, code: str, start_date: str, days: int = 10) -> pd.DataFrame:
        """진입 후 데이터 조회"""
        conn = sqlite3.connect(self.db_path)
        
        query = """
        SELECT date, open, high, low, close, volume
        FROM price_data
        WHERE code = ? AND date > ?
        ORDER BY date
        LIMIT ?
        """
        
        df = pd.read_sql(query, conn, params=(code, start_date, days))
        conn.close()
        
        return df
    
    def calculate_ichimoku(self, df: pd.DataFrame, tenkan: int = 5, kijun: int = 10) -> pd.DataFrame:
        """일목균형표 계산"""
        df = df.copy()
        df['tenkan'] = (df['high'].rolling(window=tenkan).max() + 
                        df['low'].rolling(window=tenkan).min()) / 2
        df['kijun'] = (df['high'].rolling(window=kijun).max() + 
                       df['low'].rolling(window=kijun).min()) / 2
        return df
    
    def detect_signal(self, df: pd.DataFrame) -> bool:
        """TK_CROSS 골든크로스 감지"""
        if len(df) < 15:
            return False
        
        df = self.calculate_ichimoku(df)
        
        if len(df) < 2:
            return False
        
        prev = df.iloc[-2]
        curr = df.iloc[-1]
        
        # 골든크로스: 전환선이 기준선을 상향 돌파
        return prev['tenkan'] <= prev['kijun'] and curr['tenkan'] > curr['kijun']
    
    def backtest_single(self, code: str, name: str, signal_date: str,
                       scan_close: float, scan_high: float, scan_low: float,
                       holding_days: int = 5) -> Optional[Dict]:
        """단일 백테스트"""
        
        # 다음날 데이터 조회
        df = self.get_future_data(code, signal_date, holding_days + 2)
        
        if len(df) < 2:
            return None
        
        # 진입가: 다음날 저가
        next_day = df.iloc[1]
        entry_price = next_day['low']
        entry_date = next_day['date']
        
        # 손절/익절가
        stop_loss = entry_price * 0.95
        take_profit = entry_price * 1.10
        
        # 시뮬레이션
        for day_idx, (_, row) in enumerate(df.iloc[2:].iterrows(), 1):
            day_high = row['high']
            day_low = row['low']
            day_close = row['close']
            
            # 손절 체크
            if day_low <= stop_loss:
                return {
                    'code': code,
                    'name': name,
                    'signal_date': signal_date,
                    'entry_date': entry_date,
                    'entry_price': entry_price,
                    'exit_price': stop_loss,
                    'return': -5.0,
                    'days': day_idx,
                    'reason': 'stop_loss',
                    'scan_close': scan_close,
                }
            
            # 익절 체크
            if day_high >= take_profit:
                return {
                    'code': code,
                    'name': name,
                    'signal_date': signal_date,
                    'entry_date': entry_date,
                    'entry_price': entry_price,
                    'exit_price': take_profit,
                    'return': 10.0,
                    'days': day_idx,
                    'reason': 'take_profit',
                    'scan_close': scan_close,
                }
            
            # 기간 종료
            if day_idx >= holding_days:
                final_return = (day_close - entry_price) / entry_price * 100
                return {
                    'code': code,
                    'name': name,
                    'signal_date': signal_date,
                    'entry_date': entry_date,
                    'entry_price': entry_price,
                    'exit_price': day_close,
                    'return': final_return,
                    'days': day_idx,
                    'reason': 'time_exit',
                    'scan_close': scan_close,
                }
        
        return None
    
    def scan_and_backtest_date(self, date: str) -> List[Dict]:
        """특정 날짜 스캔 및 백테스트"""
        print(f"\n📅 {date} - 전체 종목 스캔 중...")
        
        stocks = self.get_all_stocks(date)
        print(f"  대상 종목: {len(stocks)}개")
        
        signals = []
        backtests = []
        
        for i, stock in enumerate(stocks):
            if i % 500 == 0:
                print(f"  진행: {i}/{len(stocks)} ({len(signals)} 신호)")
            
            # 데이터 조회
            df = self.get_stock_data(stock['code'], date, days=80)
            
            if len(df) < 20:
                continue
            
            # 신호 감지
            df_up_to = df[df['date'] <= date]
            if len(df_up_to) < 15:
                continue
            
            if self.detect_signal(df_up_to):
                latest = df_up_to.iloc[-1]
                signals.append({
                    'code': stock['code'],
                    'name': stock['name'],
                    'date': date,
                    'close': latest['close'],
                    'high': latest['high'],
                    'low': latest['low'],
                })
        
        print(f"  ✅ 신호 발견: {len(signals)}개")
        
        # 백테스트
        print(f"  🧪 백테스트 진행...")
        for sig in signals:
            result = self.backtest_single(
                sig['code'], sig['name'], sig['date'],
                sig['close'], sig['high'], sig['low']
            )
            if result:
                backtests.append(result)
        
        print(f"  📊 완료: {len(backtests)}건")
        return backtests
    
    def run_full_backtest(self, dates: List[str]) -> Dict:
        """전체 백테스트 실행"""
        print("=" * 70)
        print("📊 일본 전략 - 전체 종목 대상 백테스트")
        print("=" * 70)
        print(f"\n전략: TK_CROSS(5/10/20) + 다음날 저가 진입 + -5%/+10%")
        print(f"테스트 기간: {dates[0]} ~ {dates[-1]}")
        
        all_results = []
        for date in dates:
            results = self.scan_and_backtest_date(date)
            all_results.extend(results)
        
        # 통계 계산
        if not all_results:
            return {}
        
        returns = [r['return'] for r in all_results]
        wins = len([r for r in all_results if r['return'] > 0])
        
        # 청산 방식별
        reasons = {}
        for r in all_results:
            reason = r['reason']
            reasons[reason] = reasons.get(reason, 0) + 1
        
        # 일별 통계
        daily_stats = {}
        for r in all_results:
            date = r['signal_date']
            if date not in daily_stats:
                daily_stats[date] = {'count': 0, 'wins': 0, 'returns': []}
            daily_stats[date]['count'] += 1
            daily_stats[date]['returns'].append(r['return'])
            if r['return'] > 0:
                daily_stats[date]['wins'] += 1
        
        return {
            'total_signals': len(all_results),
            'win_rate': wins / len(all_results) * 100,
            'avg_return': np.mean(returns),
            'median_return': np.median(returns),
            'max_return': max(returns),
            'min_return': min(returns),
            'std_return': np.std(returns),
            'exit_reasons': reasons,
            'daily_stats': daily_stats,
            'results': all_results,
        }
    
    def print_report(self, stats: Dict):
        """리포트 출력"""
        print("\n" + "=" * 70)
        print("📊 백테스트 결과 리포트")
        print("=" * 70)
        
        print(f"\n📈 전체 통계")
        print(f"  총 거래: {stats['total_signals']}건")
        print(f"  승률: {stats['win_rate']:.2f}%")
        print(f"  평균 수익률: {stats['avg_return']:+.2f}%")
        print(f"  중간값: {stats['median_return']:+.2f}%")
        print(f"  표준편차: {stats['std_return']:.2f}%")
        print(f"  최대 수익: {stats['max_return']:+.2f}%")
        print(f"  최대 손실: {stats['min_return']:+.2f}%")
        
        # 샤프 비율 (간략)
        sharpe = stats['avg_return'] / stats['std_return'] if stats['std_return'] > 0 else 0
        print(f"  샤프 비율: {sharpe:.2f}")
        
        print(f"\n📉 청산 방식")
        for reason, count in stats['exit_reasons'].items():
            pct = count / stats['total_signals'] * 100
            label = {'stop_loss': '손절', 'take_profit': '익절', 
                    'time_exit': '기간종료'}.get(reason, reason)
            avg_return = np.mean([r['return'] for r in stats['results'] if r['reason'] == reason])
            print(f"  {label}: {count}건 ({pct:.1f}%) - 평균 {avg_return:+.2f}%")
        
        print(f"\n📅 일별 통계")
        for date, s in sorted(stats['daily_stats'].items()):
            win_rate = s['wins'] / s['count'] * 100 if s['count'] > 0 else 0
            avg = np.mean(s['returns'])
            print(f"  {date}: {s['count']}건, 승률 {win_rate:.0f}%, 평균 {avg:+.2f}%")
        
        print(f"\n🏆 TOP 20 수익")
        top_gainers = sorted(stats['results'], key=lambda x: x['return'], reverse=True)[:20]
        for i, r in enumerate(top_gainers, 1):
            print(f"  {i}. {r['name']}: {r['return']:+.1f}% ({r['reason']})")
        
        print(f"\n💔 TOP 20 손실")
        top_losers = sorted(stats['results'], key=lambda x: x['return'])[:20]
        for i, r in enumerate(top_losers, 1):
            print(f"  {i}. {r['name']}: {r['return']:+.1f}% ({r['reason']})")


def main():
    backtester = FullMarketBacktester()
    
    # 테스트 기간 (3개월)
    test_dates = [
        # 3월
        '2026-03-03', '2026-03-06', '2026-03-10', '2026-03-13',
        '2026-03-17', '2026-03-20', '2026-03-24', '2026-03-27',
        # 4월
        '2026-04-03', '2026-04-07', '2026-04-10',
    ]
    
    stats = backtester.run_full_backtest(test_dates)
    backtester.print_report(stats)
    
    # 저장
    os.makedirs('reports', exist_ok=True)
    
    # JSON 저장 (결과만)
    output = {
        'strategy': 'japanese_full_market',
        'parameters': {
            'tenkan': 5,
            'kijun': 10,
            'entry': 'next_low',
            'stop_loss': -5,
            'take_profit': 10,
            'holding_days': 5,
        },
        'summary': {k: v for k, v in stats.items() if k != 'results' and k != 'daily_stats'},
        'daily_stats': stats.get('daily_stats', {}),
    }
    
    with open('reports/japanese_full_backtest.json', 'w', encoding='utf-8') as f:
        json.dump(output, f, ensure_ascii=False, indent=2)
    
    # CSV 저장 (상세 결과)
    if stats.get('results'):
        df = pd.DataFrame(stats['results'])
        df.to_csv('reports/japanese_full_backtest.csv', index=False, encoding='utf-8-sig')
        print(f"\n💾 저장 완료:")
        print(f"  - reports/japanese_full_backtest.json")
        print(f"  - reports/japanese_full_backtest.csv")


if __name__ == '__main__':
    main()
