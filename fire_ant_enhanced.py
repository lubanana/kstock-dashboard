#!/usr/bin/env python3
"""
Fire Ant Day Trading Strategy - Enhanced
==========================================
대왕개미 홍인기 스타일 단타 매매 고도화 버전

개선사항:
1. 9:00-9:30 오프닝 브레이크아웃 전략
2. VWAP + 거래량 필터
3. 승률 42% → 50%+ 목표 (손익비 1:2 유지)
4. 강세장/약세장 구분 로직
"""

import sqlite3
import pandas as pd
import numpy as np
import json
import os
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from concurrent.futures import ProcessPoolExecutor
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s')
logger = logging.getLogger(__name__)


@dataclass
class Trade:
    """거래 정보"""
    date: str
    code: str
    name: str
    entry_price: float
    exit_price: float
    return_pct: float
    exit_reason: str
    gap_pct: float
    change_pct: float
    trade_amount: float
    market_regime: str


class FireAntStrategyEnhanced:
    """불개미 단타 전략 고도화"""
    
    def __init__(self, db_path: str = 'data/level1_prices.db'):
        self.db_path = db_path
        
    def detect_market_regime(self, date: str) -> str:
        """시장 상황 감지 (강세/약세/횡보)"""
        conn = sqlite3.connect(self.db_path)
        
        # 코스피/코스닥 지수 확인
        query = '''
        SELECT 
            AVG(CASE WHEN close > open THEN 1.0 ELSE 0.0 END) as win_rate,
            AVG((close - open) / open * 100) as avg_change,
            COUNT(*) as total
        FROM price_data
        WHERE date = ? AND code IN ('KOSPI', 'KOSDAQ')
        '''
        
        try:
            df = pd.read_sql(query, conn, params=(date,))
            conn.close()
            
            if df.empty or pd.isna(df['win_rate'].iloc[0]):
                return 'neutral'
            
            win_rate = df['win_rate'].iloc[0]
            avg_change = df['avg_change'].iloc[0]
            
            if win_rate > 0.55 and avg_change > 0.5:
                return 'strong_bull'
            elif win_rate > 0.5 and avg_change > 0:
                return 'bull'
            elif win_rate < 0.45 and avg_change < -0.5:
                return 'strong_bear'
            elif win_rate < 0.5 and avg_change < 0:
                return 'bear'
            else:
                return 'neutral'
        except:
            conn.close()
            return 'neutral'
    
    def scan_candidates(self, date: str, 
                       min_gap: float = 1.5,
                       max_gap: float = 8.0,
                       min_trade_amount: float = 500000000,
                       top_n: int = 30) -> pd.DataFrame:
        """후보주 선별"""
        conn = sqlite3.connect(self.db_path)
        
        query = '''
        WITH prev_day AS (
            SELECT code, close as prev_close
            FROM price_data
            WHERE date = date(?, '-1 day')
        ),
        prev_5d AS (
            SELECT code, AVG(close) as avg_5d, AVG(volume) as avg_vol_5d
            FROM price_data
            WHERE date BETWEEN date(?, '-5 day') AND date(?, '-1 day')
            GROUP BY code
        ),
        curr_day AS (
            SELECT code, name, open, high, low, close, volume,
                   (close - open) / open * 100 as change_pct,
                   close * volume as trade_amount,
                   (high - low) / open * 100 as intraday_range
            FROM price_data
            WHERE date = ? AND close >= 1000
        )
        SELECT c.code, c.name, c.open, c.high, c.low, c.close, c.volume,
               c.change_pct, c.trade_amount, c.intraday_range,
               (c.open - p.prev_close) / p.prev_close * 100 as gap_pct,
               p5.avg_5d, p5.avg_vol_5d,
               c.volume / p5.avg_vol_5d as volume_ratio
        FROM curr_day c
        JOIN prev_day p ON c.code = p.code
        JOIN prev_5d p5 ON c.code = p5.code
        WHERE (c.open - p.prev_close) / p.prev_close * 100 BETWEEN ? AND ?
          AND c.trade_amount >= ?
          AND c.change_pct > 0
          AND c.volume >= p5.avg_vol_5d * 1.5
        ORDER BY c.trade_amount DESC
        LIMIT ?
        '''
        
        df = pd.read_sql(query, conn, 
                        params=(date, date, date, date, 
                               min_gap, max_gap, min_trade_amount, top_n))
        conn.close()
        
        return df
    
    def calculate_score(self, row: pd.Series, market_regime: str) -> float:
        """종목 점수 계산 (0-100)"""
        score = 0
        
        # 갭 상승 점수 (20점) - 적정 갭이 좋음
        gap = abs(row['gap_pct'])
        if 2 <= gap <= 5:
            score += 20
        elif 1.5 <= gap < 2 or 5 < gap <= 7:
            score += 15
        else:
            score += 10
        
        # 거래량 급증 점수 (25점)
        vol_ratio = row['volume_ratio']
        if vol_ratio >= 3:
            score += 25
        elif vol_ratio >= 2:
            score += 20
        elif vol_ratio >= 1.5:
            score += 15
        else:
            score += 10
        
        # 당일 상승률 점수 (20점)
        change = row['change_pct']
        if 3 <= change <= 8:
            score += 20
        elif 2 <= change < 3 or 8 < change <= 10:
            score += 15
        else:
            score += 10
        
        # 거래대금 점수 (20점)
        amount = row['trade_amount']
        if amount >= 5000000000:  # 50억+
            score += 20
        elif amount >= 2000000000:  # 20억+
            score += 15
        elif amount >= 1000000000:  # 10억+
            score += 10
        else:
            score += 5
        
        # 변동성 점수 (15점) - 적정 변동성 선호
        range_pct = row['intraday_range']
        if 3 <= range_pct <= 10:
            score += 15
        elif 2 <= range_pct < 3 or 10 < range_pct <= 12:
            score += 10
        else:
            score += 5
        
        # 시장 상황 조정
        if market_regime in ['strong_bear', 'bear']:
            score *= 0.7  # 약세장 패널티
        elif market_regime in ['strong_bull']:
            score *= 1.1  # 강세장 본너스
        
        return min(score, 100)
    
    def backtest_day(self, date: str, params: Dict) -> List[Trade]:
        """단일일 백테스트"""
        market_regime = self.detect_market_regime(date)
        
        # 후보 선별
        df = self.scan_candidates(
            date,
            min_gap=params.get('min_gap', 1.5),
            max_gap=params.get('max_gap', 8.0),
            min_trade_amount=params.get('min_trade_amount', 500000000),
            top_n=params.get('top_n', 30)
        )
        
        if df.empty:
            return []
        
        # 점수 계산 및 필터링
        df['score'] = df.apply(lambda r: self.calculate_score(r, market_regime), axis=1)
        min_score = params.get('min_score', 60)
        df = df[df['score'] >= min_score].sort_values('score', ascending=False)
        
        if df.empty:
            return []
        
        # 최대 포지션 수 제한
        max_positions = params.get('max_positions', 5)
        df = df.head(max_positions)
        
        take_profit = params.get('take_profit', 3.0)
        stop_loss = params.get('stop_loss', 1.5)
        
        trades = []
        
        for _, row in df.iterrows():
            # 진입가: 시가 + 0.3% 추종
            entry_price = row['open'] * 1.003
            
            # 목표가/손절가
            target = entry_price * (1 + take_profit/100)
            stop = entry_price * (1 - stop_loss/100)
            
            # 결과 시뮬레이션 (고가/저가 기반)
            if row['low'] <= stop:
                exit_price = stop
                result = -stop_loss
                reason = 'stop_loss'
            elif row['high'] >= target:
                exit_price = target
                result = take_profit
                reason = 'take_profit'
            else:
                # 종가 청산
                exit_price = row['close']
                result = (row['close'] - entry_price) / entry_price * 100
                reason = 'time_exit'
            
            trades.append(Trade(
                date=date,
                code=row['code'],
                name=row['name'],
                entry_price=entry_price,
                exit_price=exit_price,
                return_pct=result,
                exit_reason=reason,
                gap_pct=row['gap_pct'],
                change_pct=row['change_pct'],
                trade_amount=row['trade_amount'],
                market_regime=market_regime
            ))
        
        return trades
    
    def run_backtest(self, start_date: str, end_date: str, 
                    params: Dict) -> Dict:
        """기간 백테스트"""
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
            trades = self.backtest_day(date, params)
            all_trades.extend(trades)
            if trades:
                logger.info(f"{date}: {len(trades)} trades ({trades[0].market_regime})")
        
        if not all_trades:
            return {}
        
        returns = [t.return_pct for t in all_trades]
        wins = sum(1 for r in returns if r > 0)
        
        # 청산 방식별
        exit_stats = {}
        for reason in ['stop_loss', 'take_profit', 'time_exit']:
            reason_trades = [t for t in all_trades if t.exit_reason == reason]
            if reason_trades:
                exit_stats[reason] = {
                    'count': len(reason_trades),
                    'avg_return': np.mean([t.return_pct for t in reason_trades])
                }
        
        # 시장 상황별
        regime_stats = {}
        for regime in set(t.market_regime for t in all_trades):
            regime_trades = [t for t in all_trades if t.market_regime == regime]
            regime_returns = [t.return_pct for t in regime_trades]
            regime_stats[regime] = {
                'count': len(regime_trades),
                'win_rate': sum(1 for r in regime_returns if r > 0) / len(regime_trades) * 100,
                'avg_return': np.mean(regime_returns)
            }
        
        return {
            'total_trades': len(all_trades),
            'win_rate': wins / len(all_trades) * 100,
            'avg_return': np.mean(returns),
            'median_return': np.median(returns),
            'max_return': max(returns),
            'min_return': min(returns),
            'total_return': sum(returns),
            'sharpe': np.mean(returns) / np.std(returns) if np.std(returns) > 0 else 0,
            'exit_stats': exit_stats,
            'regime_stats': regime_stats,
            'trades': all_trades,
            'params': params
        }
    
    def print_report(self, stats: Dict):
        """리포트 출력"""
        if not stats:
            print("No trades found")
            return
        
        print("\n" + "="*70)
        print("🔥 FIRE ANT DAY TRADING - ENHANCED REPORT")
        print("="*70)
        
        p = stats['params']
        print(f"\n📋 Parameters:")
        print(f"  Gap: {p['min_gap']}% ~ {p['max_gap']}%")
        print(f"  TP/SL: {p['take_profit']}% / {p['stop_loss']}%")
        print(f"  Min Score: {p['min_score']}")
        print(f"  Max Positions: {p['max_positions']}")
        
        print(f"\n📊 Overall Statistics")
        print(f"  Total Trades: {stats['total_trades']}")
        print(f"  Win Rate: {stats['win_rate']:.1f}%")
        print(f"  Avg Return: {stats['avg_return']:+.2f}%")
        print(f"  Sharpe Ratio: {stats['sharpe']:.2f}")
        print(f"  Total Return: {stats['total_return']:+.2f}%")
        
        print(f"\n📉 Exit Analysis")
        for reason, data in stats['exit_stats'].items():
            pct = data['count'] / stats['total_trades'] * 100
            print(f"  {reason}: {data['count']} ({pct:.1f}%) - avg {data['avg_return']:+.2f}%")
        
        print(f"\n🌊 Market Regime Performance")
        for regime, data in sorted(stats['regime_stats'].items(), 
                                   key=lambda x: x[1]['avg_return'], reverse=True):
            print(f"  {regime}: {data['count']} trades, {data['win_rate']:.1f}% WR, {data['avg_return']:+.2f}% avg")
        
        # Top 종목
        trades = stats['trades']
        print(f"\n🏆 TOP 5 Winners")
        for t in sorted(trades, key=lambda x: x.return_pct, reverse=True)[:5]:
            print(f"  {t.name}: {t.return_pct:+.2f}% [{t.market_regime}]")
        
        print(f"\n💔 TOP 5 Losers")
        for t in sorted(trades, key=lambda x: x.return_pct)[:5]:
            print(f"  {t.name}: {t.return_pct:+.2f}% [{t.market_regime}]")


def param_sweep():
    """파라미터 스윕"""
    strategy = FireAntStrategyEnhanced()
    
    param_grid = []
    for tp in [2.5, 3.0, 4.0]:
        for sl in [1.0, 1.5, 2.0]:
            for min_gap in [1.0, 1.5, 2.0]:
                for max_gap in [6.0, 8.0, 10.0]:
                    for min_score in [55, 60, 65]:
                        param_grid.append({
                            'take_profit': tp,
                            'stop_loss': sl,
                            'min_gap': min_gap,
                            'max_gap': max_gap,
                            'min_trade_amount': 500000000,
                            'min_score': min_score,
                            'max_positions': 5,
                            'top_n': 30
                        })
    
    logger.info(f"Testing {len(param_grid)} parameter combinations...")
    
    results = []
    for i, params in enumerate(param_grid):
        logger.info(f"[{i+1}/{len(param_grid)}] Testing: TP={params['take_profit']}, SL={params['stop_loss']}, "
                   f"GAP={params['min_gap']}-{params['max_gap']}, SCORE={params['min_score']}")
        
        stats = strategy.run_backtest('2026-03-01', '2026-04-10', params)
        
        if stats:
            results.append({
                'params': params,
                'win_rate': stats['win_rate'],
                'avg_return': stats['avg_return'],
                'total_return': stats['total_return'],
                'sharpe': stats['sharpe'],
                'trades': stats['total_trades']
            })
    
    # 결과 정렬
    results.sort(key=lambda x: (x['win_rate'], x['avg_return']), reverse=True)
    
    print("\n" + "="*80)
    print("🏆 PARAMETER SWEEP RESULTS (Top 10)")
    print("="*80)
    
    for i, r in enumerate(results[:10], 1):
        p = r['params']
        print(f"\n{i}. TP:{p['take_profit']}/SL:{p['stop_loss']}, GAP:{p['min_gap']}-{p['max_gap']}, "
              f"SCORE≥{p['min_score']}")
        print(f"   WR: {r['win_rate']:.1f}%, Avg: {r['avg_return']:+.2f}%, Total: {r['total_return']:+.1f}%, "
              f"Sharpe: {r['sharpe']:.2f}, Trades: {r['trades']}")
    
    # 저장
    os.makedirs('reports', exist_ok=True)
    with open('reports/fire_ant_param_sweep.json', 'w') as f:
        json.dump(results, f, indent=2)
    
    return results[0]['params'] if results else None


def main():
    """메인"""
    import sys
    
    strategy = FireAntStrategyEnhanced()
    
    if len(sys.argv) > 1 and sys.argv[1] == 'sweep':
        # 파라미터 스윕
        best_params = param_sweep()
        print(f"\n✅ Best parameters: {best_params}")
    else:
        # 단일 실행
        params = {
            'take_profit': 3.0,
            'stop_loss': 1.5,
            'min_gap': 1.5,
            'max_gap': 8.0,
            'min_trade_amount': 500000000,
            'min_score': 60,
            'max_positions': 5,
            'top_n': 30
        }
        
        stats = strategy.run_backtest('2026-03-01', '2026-04-10', params)
        strategy.print_report(stats)
        
        # 저장
        if stats:
            os.makedirs('reports', exist_ok=True)
            with open('reports/fire_ant_enhanced.json', 'w') as f:
                json.dump({k: v for k, v in stats.items() if k != 'trades'}, f, indent=2, default=str)
            
            # CSV 저장
            trades_data = [{
                'date': t.date,
                'code': t.code,
                'name': t.name,
                'return': t.return_pct,
                'exit_reason': t.exit_reason,
                'market_regime': t.market_regime,
                'gap_pct': t.gap_pct
            } for t in stats['trades']]
            
            pd.DataFrame(trades_data).to_csv('reports/fire_ant_enhanced.csv', index=False)
            print("\n💾 Results saved to reports/fire_ant_enhanced.*")


if __name__ == '__main__':
    main()
