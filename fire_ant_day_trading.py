#!/usr/bin/env python3
"""
Fire Ant Day Trading Strategy (불개미 단타 전략)
===============================================
대왕개미 홍인기 스타일 단타 매매 전략

핵심 원리:
1. 장 시작 후 30분이 승부처 (9:00-9:30)
2. 주도주(대장주) 선별 - 거래대금 + 상승률 상위
3. 오프닝 갭 후 눌림목 매수
4. VWAP 기준 선회 + 거래량 급증 시 진입
5. 당일 청산 (스캘핑)

진입 조건:
- 전일 대비 +2% 이상 갭상승
- 9:00-9:30 사이 거래대금 상위 10위 이내
- VWAP 상회 및 재돌파
- 5분봉 양봉 + 거래량 2배 이상

청산 조건:
- +3% 익절 / -1.5% 손절
- 11:30 미청산 시 강제 청산
- VWAP 하회 시 즉시 청산
"""

import sqlite3
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class FireAntDayTradingStrategy:
    """불개미 단타 전략"""
    
    def __init__(self, db_path: str = 'data/level1_prices.db'):
        self.db_path = db_path
        
    def get_intraday_data(self, code: str, date: str) -> pd.DataFrame:
        """분봉 데이터 조회 (실제로는 분봉 DB 필요)"""
        # 현재는 일봉 기준으로 시뮬레이션
        conn = sqlite3.connect(self.db_path)
        
        query = '''
        SELECT date, open, high, low, close, volume
        FROM price_data
        WHERE code = ? AND date <= ?
        ORDER BY date DESC
        LIMIT 30
        '''
        
        df = pd.read_sql(query, conn, params=(code, date))
        conn.close()
        
        return df.sort_values('date').reset_index(drop=True)
    
    def scan_leading_stocks(self, date: str, top_n: int = 20) -> pd.DataFrame:
        """주도주 선별 (전일 대비 상승률 + 거래대금)"""
        conn = sqlite3.connect(self.db_path)
        
        # 전일 데이터와 비교
        query = '''
        WITH prev_day AS (
            SELECT code, close as prev_close
            FROM price_data
            WHERE date = date(?, '-1 day')
        ),
        curr_day AS (
            SELECT code, name, open, high, low, close, volume,
                   (close - open) / open * 100 as change_pct,
                   close * volume as trade_amount
            FROM price_data
            WHERE date = ? AND close >= 1000
        )
        SELECT c.code, c.name, c.open, c.high, c.low, c.close, c.volume,
               c.change_pct, c.trade_amount,
               (c.open - p.prev_close) / p.prev_close * 100 as gap_pct
        FROM curr_day c
        JOIN prev_day p ON c.code = p.code
        WHERE c.change_pct > 2
          AND c.trade_amount > 1000000000
        ORDER BY c.trade_amount DESC
        LIMIT ?
        '''
        
        df = pd.read_sql(query, conn, params=(date, date, top_n))
        conn.close()
        
        return df
    
    def check_entry_signal(self, df: pd.DataFrame, code: str, 
                          min_gap: float = 2.0,
                          vwap_bounce: bool = True) -> bool:
        """진입 신호 확인"""
        if len(df) < 2:
            return False
        
        latest = df.iloc[-1]
        prev = df.iloc[-2]
        
        # 1. 갭상승 확인
        gap_up = latest['open'] > prev['close'] * (1 + min_gap/100)
        
        # 2. 양봉 확인
        bullish = latest['close'] > latest['open']
        
        # 3. 거래량 급증 (2배 이상)
        avg_volume = df['volume'].rolling(5).mean().iloc[-1]
        volume_spike = latest['volume'] > avg_volume * 2
        
        # 4. VWAP 상회 (일봉 기준 근사치)
        typical_price = (latest['high'] + latest['low'] + latest['close']) / 3
        vwap_condition = latest['close'] > typical_price * 0.995
        
        # 5. 전일 대비 상승률
        change_pct = (latest['close'] - prev['close']) / prev['close'] * 100
        momentum = change_pct > 2
        
        signals = {
            'gap_up': gap_up,
            'bullish': bullish,
            'volume_spike': volume_spike,
            'vwap_condition': vwap_condition,
            'momentum': momentum
        }
        
        # 최소 4개 조건 충족
        score = sum(signals.values())
        return score >= 4, signals
    
    def backtest_day(self, date: str, 
                    take_profit: float = 3.0,
                    stop_loss: float = 1.5,
                    max_hold_hours: int = 3) -> List[Dict]:
        """단일일 백테스트"""
        
        # 주도주 선별
        leaders = self.scan_leading_stocks(date)
        
        if leaders.empty:
            return []
        
        trades = []
        
        for _, stock in leaders.iterrows():
            code = stock['code']
            name = stock['name']
            
            # 데이터 조회
            df = self.get_intraday_data(code, date)
            
            if len(df) < 5:
                continue
            
            # 진입 신호 확인
            entry_signal, signals = self.check_entry_signal(df, code)
            
            if not entry_signal:
                continue
            
            # 진입가 설정 (시가 근처)
            entry_price = stock['open'] * 1.005  # 0.5% 추종 진입
            
            # 목표가/손절가
            target_price = entry_price * (1 + take_profit/100)
            stop_price = entry_price * (1 - stop_loss/100)
            
            # 당일 고가/저가로 결과 시뮬레이션
            day_high = stock['high']
            day_low = stock['low']
            day_close = stock['close']
            
            # 결과 계산
            if day_low <= stop_price:
                # 손절
                exit_price = stop_price
                result = -stop_loss
                exit_reason = 'stop_loss'
            elif day_high >= target_price:
                # 익절
                exit_price = target_price
                result = take_profit
                exit_reason = 'take_profit'
            else:
                # 미청산 시 종가 청산
                exit_price = day_close
                result = (day_close - entry_price) / entry_price * 100
                exit_reason = 'time_exit'
            
            trades.append({
                'date': date,
                'code': code,
                'name': name,
                'entry_price': entry_price,
                'exit_price': exit_price,
                'return': result,
                'exit_reason': exit_reason,
                'signals': signals,
                'gap_pct': stock['gap_pct'],
                'change_pct': stock['change_pct'],
                'trade_amount': stock['trade_amount']
            })
        
        return trades
    
    def run_backtest(self, start_date: str, end_date: str,
                    take_profit: float = 3.0,
                    stop_loss: float = 1.5) -> Dict:
        """기간 백테스트"""
        
        logger.info(f"Fire Ant Day Trading Backtest: {start_date} ~ {end_date}")
        
        # 거래일 리스트
        conn = sqlite3.connect(self.db_path)
        query = '''
        SELECT DISTINCT date FROM price_data 
        WHERE date BETWEEN ? AND ?
        ORDER BY date
        '''
        dates = pd.read_sql(query, conn, params=(start_date, end_date))['date'].tolist()
        conn.close()
        
        all_trades = []
        
        for date in dates:
            trades = self.backtest_day(date, take_profit, stop_loss)
            all_trades.extend(trades)
            
            if trades:
                logger.info(f"{date}: {len(trades)} trades")
        
        if not all_trades:
            return {}
        
        # 통계 계산
        returns = [t['return'] for t in all_trades]
        wins = len([r for r in returns if r > 0])
        
        # 청산 방식별
        exit_reasons = {}
        for t in all_trades:
            reason = t['exit_reason']
            exit_reasons[reason] = exit_reasons.get(reason, 0) + 1
        
        return {
            'total_trades': len(all_trades),
            'win_rate': wins / len(all_trades) * 100,
            'avg_return': np.mean(returns),
            'median_return': np.median(returns),
            'max_return': max(returns),
            'min_return': min(returns),
            'total_return': sum(returns),
            'exit_reasons': exit_reasons,
            'trades': all_trades
        }
    
    def print_report(self, stats: Dict):
        """리포트 출력"""
        if not stats:
            print("No trades found")
            return
        
        print("\n" + "="*70)
        print("🔥 FIRE ANT DAY TRADING STRATEGY REPORT")
        print("="*70)
        
        print(f"\n📊 Overall Statistics")
        print(f"  Total Trades: {stats['total_trades']}")
        print(f"  Win Rate: {stats['win_rate']:.1f}%")
        print(f"  Avg Return: {stats['avg_return']:+.2f}%")
        print(f"  Median Return: {stats['median_return']:+.2f}%")
        print(f"  Max Return: {stats['max_return']:+.2f}%")
        print(f"  Min Return: {stats['min_return']:+.2f}%")
        print(f"  Total Return: {stats['total_return']:+.2f}%")
        
        print(f"\n📉 Exit Distribution")
        for reason, count in stats['exit_reasons'].items():
            pct = count / stats['total_trades'] * 100
            avg = np.mean([t['return'] for t in stats['trades'] if t['exit_reason'] == reason])
            print(f"  {reason}: {count} ({pct:.1f}%) - avg {avg:+.2f}%")
        
        # TOP 수익
        print(f"\n🏆 TOP 10 Winners")
        top_gainers = sorted(stats['trades'], key=lambda x: x['return'], reverse=True)[:10]
        for i, t in enumerate(top_gainers, 1):
            print(f"  {i}. {t['name']}: {t['return']:+.2f}% ({t['exit_reason']})")
        
        # TOP 손실
        print(f"\n💔 TOP 10 Losers")
        top_losers = sorted(stats['trades'], key=lambda x: x['return'])[:10]
        for i, t in enumerate(top_losers, 1):
            print(f"  {i}. {t['name']}: {t['return']:+.2f}% ({t['exit_reason']})")


def main():
    """메인 실행"""
    strategy = FireAntDayTradingStrategy()
    
    # 백테스트 기간
    stats = strategy.run_backtest(
        start_date='2026-03-01',
        end_date='2026-04-10',
        take_profit=3.0,
        stop_loss=1.5
    )
    
    strategy.print_report(stats)
    
    # 결과 저장
    if stats.get('trades'):
        import json
        import os
        
        os.makedirs('reports', exist_ok=True)
        
        output = {
            'strategy': 'fire_ant_day_trading',
            'parameters': {
                'take_profit': 3.0,
                'stop_loss': 1.5,
                'entry_time': '09:00-09:30',
                'exit_time': '11:30 or TP/SL'
            },
            'summary': {k: v for k, v in stats.items() if k != 'trades'},
        }
        
        with open('reports/fire_ant_backtest.json', 'w', encoding='utf-8') as f:
            json.dump(output, f, ensure_ascii=False, indent=2)
        
        df = pd.DataFrame(stats['trades'])
        df.to_csv('reports/fire_ant_backtest.csv', index=False, encoding='utf-8-sig')
        
        print(f"\n💾 Results saved to reports/fire_ant_backtest.*")


if __name__ == '__main__':
    main()
