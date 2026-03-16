#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
버핏 3전략 백테스터
2024년 1월 ~ 2026년 3월 (약 2년 3개월)
"""

import sqlite3
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import json
import os
from typing import List, Dict, Tuple
import warnings
warnings.filterwarnings('ignore')

class BuffettBacktester:
    """
    버핏 전략 백테스터
    """
    
    def __init__(self, db_path='./data/pivot_strategy.db'):
        self.db_path = db_path
        self.initial_capital = 100000000  # 1억원
        self.results = {}
        
    def get_price_data(self, symbol: str, start_date: str, end_date: str) -> pd.DataFrame:
        """특정 기간 주가 데이터 조회"""
        conn = sqlite3.connect(self.db_path)
        query = """
            SELECT date, open, high, low, close, volume 
            FROM stock_prices 
            WHERE symbol = ? AND date BETWEEN ? AND ?
            ORDER BY date
        """
        df = pd.read_sql_query(query, conn, params=(symbol, start_date, end_date))
        conn.close()
        
        if len(df) < 60:
            return None
            
        df['date'] = pd.to_datetime(df['date'])
        return df
    
    def calculate_signals(self, df: pd.DataFrame, strategy: str, check_date: str) -> bool:
        """
        특정 날짜의 진입 신호 계산
        """
        if df is None or len(df) < 120:
            return False
        
        # check_date 이전 데이터만 사용
        df_hist = df[df['date'] <= check_date]
        if len(df_hist) < 60:
            return False
        
        current_price = df_hist['close'].iloc[-1]
        
        # 기술적 지표
        df_hist['ma20'] = df_hist['close'].rolling(20).mean()
        df_hist['ma60'] = df_hist['close'].rolling(60).mean()
        
        # RSI
        delta = df_hist['close'].diff()
        gain = delta.where(delta > 0, 0).rolling(14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
        rs = gain / loss
        rsi = (100 - (100 / (1 + rs))).iloc[-1]
        
        if strategy == 'graham':
            # 전략1: 저평가 + 거래량
            low_52w = df_hist['close'].tail(252).min() if len(df_hist) >= 252 else df_hist['close'].min()
            pb_proxy = current_price / low_52w if low_52w > 0 else 999
            
            avg_volume = df_hist['volume'].tail(20).mean()
            recent_volume = df_hist['volume'].tail(5).mean()
            volume_ratio = recent_volume / avg_volume if avg_volume > 0 else 1
            
            returns_3m = (current_price / df_hist['close'].iloc[-60] - 1) * 100 if len(df_hist) >= 60 else 0
            ma_aligned = (current_price > df_hist['ma20'].iloc[-1] > df_hist['ma60'].iloc[-1]) if not pd.isna(df_hist['ma60'].iloc[-1]) else False
            
            score = 0
            if pb_proxy < 1.3: score += 30
            elif pb_proxy < 1.5: score += 20
            if volume_ratio > 1.5: score += 20
            elif volume_ratio > 1.0: score += 10
            if returns_3m > 0: score += 20
            elif returns_3m > -5: score += 10
            if 30 <= rsi <= 60: score += 15
            if ma_aligned: score += 15
            
            return score >= 60
            
        elif strategy == 'quality':
            # 전략2: 퀄리티
            returns_6m = (current_price / df_hist['close'].iloc[-120] - 1) * 100 if len(df_hist) >= 120 else 0
            
            monthly_returns = []
            for i in range(1, min(7, len(df_hist)//20)):
                if len(df_hist) >= i*20:
                    ret = (current_price / df_hist['close'].iloc[-i*20] - 1) * 100
                    monthly_returns.append(ret)
            return_std = np.std(monthly_returns) if len(monthly_returns) > 1 else 10
            
            high_52w = df_hist['close'].tail(252).max() if len(df_hist) >= 252 else df_hist['close'].max()
            from_52w_high = (current_price / high_52w - 1) * 100 if high_52w > 0 else 0
            
            score = 0
            if returns_6m > 15: score += 25
            elif returns_6m > 5: score += 18
            if return_std < 8: score += 15
            elif return_std < 12: score += 10
            if -20 <= from_52w_high <= -5: score += 20
            elif -30 <= from_52w_high < -20: score += 15
            if rsi > 50: score += 20
            elif rsi > 45: score += 12
            
            return score >= 70
            
        elif strategy == 'dividend':
            # 전략3: 배당성장 (안정성)
            returns = df_hist['close'].pct_change().dropna()
            volatility = returns.tail(60).std() * np.sqrt(252) * 100
            
            returns_6m = (current_price / df_hist['close'].iloc[-120] - 1) * 100 if len(df_hist) >= 120 else 0
            consistent = returns_6m > 0
            
            max_dd = ((df_hist['close'] / df_hist['close'].cummax()) - 1).min() * 100
            
            score = 0
            if volatility < 30: score += 25
            elif volatility < 40: score += 18
            if consistent and returns_6m > 5: score += 25
            elif consistent: score += 15
            if max_dd > -20: score += 20
            elif max_dd > -30: score += 12
            if 40 <= rsi <= 60: score += 15
            
            return score >= 60
        
        return False
    
    def run_backtest(self, strategy: str, start_date: str, end_date: str) -> Dict:
        """
        단일 전략 백테스트
        """
        print(f"\n🔍 전략 백테스트: {strategy}")
        print(f"   기간: {start_date} ~ {end_date}")
        
        # 종목 리스트
        conn = sqlite3.connect(self.db_path)
        stocks_df = pd.read_sql_query(
            "SELECT symbol, name, market FROM stock_info", 
            conn
        )
        conn.close()
        
        # 리밸런싱 일정 (월 1회)
        rebalance_dates = pd.date_range(start=start_date, end=end_date, freq='MS')
        
        portfolio = {}  # {symbol: {'shares': n, 'entry_price': p, 'entry_date': d}}
        cash = self.initial_capital
        portfolio_value_history = []
        trades = []
        
        for i, rebalance_date in enumerate(rebalance_dates):
            date_str = rebalance_date.strftime('%Y-%m-%d')
            
            if i % 3 == 0:
                print(f"   진행: {date_str} ({i}/{len(rebalance_dates)})")
            
            # 기존 포지션 평가
            current_value = cash
            for symbol, pos in list(portfolio.items()):
                df = self.get_price_data(symbol, start_date, date_str)
                if df is not None and len(df) > 0:
                    current_price = df['close'].iloc[-1]
                    current_value += pos['shares'] * current_price
            
            portfolio_value_history.append({
                'date': date_str,
                'value': current_value
            })
            
            # 신규 종목 스크리닝 (상위 10개)
            candidates = []
            for _, row in stocks_df.iterrows():
                symbol = row['symbol']
                name = row['name']
                
                df = self.get_price_data(symbol, start_date, date_str)
                if df is None:
                    continue
                
                if self.calculate_signals(df, strategy, date_str):
                    # 점수 계산 (간략화)
                    returns_6m = 0
                    if len(df) >= 120:
                        returns_6m = (df['close'].iloc[-1] / df['close'].iloc[-120] - 1) * 100
                    
                    candidates.append({
                        'symbol': symbol,
                        'name': name,
                        'score': returns_6m,
                        'price': df['close'].iloc[-1]
                    })
            
            # 상위 10개 선택
            candidates.sort(key=lambda x: x['score'], reverse=True)
            selected = candidates[:10]
            
            if not selected:
                continue
            
            # 포트폴리오 리밸런싱
            # 기존 포지션 정리
            for symbol, pos in list(portfolio.items()):
                df = self.get_price_data(symbol, start_date, date_str)
                if df is not None and len(df) > 0:
                    sell_price = df['close'].iloc[-1]
                    proceeds = pos['shares'] * sell_price
                    
                    # 수익 계산
                    buy_value = pos['shares'] * pos['entry_price']
                    profit = proceeds - buy_value
                    
                    trades.append({
                        'symbol': symbol,
                        'entry_date': pos['entry_date'],
                        'exit_date': date_str,
                        'entry_price': pos['entry_price'],
                        'exit_price': sell_price,
                        'shares': pos['shares'],
                        'profit': profit,
                        'return_pct': (sell_price / pos['entry_price'] - 1) * 100
                    })
                    
                    cash += proceeds
            
            portfolio = {}
            
            # 신규 매수
            if selected and cash > 0:
                per_stock = cash / len(selected)
                
                for stock in selected:
                    shares = int(per_stock / stock['price'])
                    if shares > 0:
                        cost = shares * stock['price']
                        if cost <= cash:
                            portfolio[stock['symbol']] = {
                                'shares': shares,
                                'entry_price': stock['price'],
                                'entry_date': date_str,
                                'name': stock['name']
                            }
                            cash -= cost
        
        # 최종 평가
        final_value = cash
        for symbol, pos in portfolio.items():
            df = self.get_price_data(symbol, start_date, end_date)
            if df is not None and len(df) > 0:
                final_value += pos['shares'] * df['close'].iloc[-1]
        
        # 성과 지표 계산
        values = [v['value'] for v in portfolio_value_history]
        returns = [(values[i] / values[i-1] - 1) * 100 for i in range(1, len(values))] if len(values) > 1 else [0]
        
        total_return = (final_value / self.initial_capital - 1) * 100
        cagr = ((final_value / self.initial_capital) ** (1 / 2.25) - 1) * 100  # 2.25년
        
        # MDD 계산
        peak = self.initial_capital
        mdd = 0
        for v in values:
            if v > peak:
                peak = v
            dd = (v / peak - 1) * 100
            if dd < mdd:
                mdd = dd
        
        # 승률
        winning_trades = [t for t in trades if t['profit'] > 0]
        win_rate = len(winning_trades) / len(trades) * 100 if trades else 0
        
        avg_return = np.mean([t['return_pct'] for t in trades]) if trades else 0
        
        result = {
            'strategy': strategy,
            'start_date': start_date,
            'end_date': end_date,
            'initial_capital': self.initial_capital,
            'final_value': final_value,
            'total_return_pct': round(total_return, 2),
            'cagr_pct': round(cagr, 2),
            'mdd_pct': round(mdd, 2),
            'total_trades': len(trades),
            'win_rate_pct': round(win_rate, 2),
            'avg_trade_return_pct': round(avg_return, 2),
            'portfolio_history': portfolio_value_history,
            'trades': trades
        }
        
        print(f"\n   ✅ 백테스트 완료")
        print(f"      총 수익률: {total_return:.2f}%")
        print(f"      CAGR: {cagr:.2f}%")
        print(f"      MDD: {mdd:.2f}%")
        print(f"      승률: {win_rate:.1f}%")
        print(f"      거래 횟수: {len(trades)}")
        
        return result
    
    def run_all_backtests(self) -> Dict:
        """
        3전략 모두 백테스트
        """
        start_date = '2024-01-01'
        end_date = '2026-03-13'
        
        print("=" * 60)
        print("📊 버핏 3전략 백테스트 시작")
        print("=" * 60)
        print(f"기간: {start_date} ~ {end_date}")
        print(f"초기 자본: {self.initial_capital:,.0f}원")
        
        strategies = ['graham', 'quality', 'dividend']
        results = {}
        
        for strategy in strategies:
            results[strategy] = self.run_backtest(strategy, start_date, end_date)
        
        # 종합 비교
        print("\n" + "=" * 60)
        print("📈 3전략 종합 비교")
        print("=" * 60)
        print(f"{'전략':<15} {'총수익':<10} {'CAGR':<10} {'MDD':<10} {'승률':<10} {'거래':<10}")
        print("-" * 60)
        
        for strategy in strategies:
            r = results[strategy]
            strategy_name = {
                'graham': '순유동자산',
                'quality': '퀄리티',
                'dividend': '배당성장'
            }[strategy]
            print(f"{strategy_name:<15} {r['total_return_pct']:>7.1f}% {r['cagr_pct']:>7.1f}% {r['mdd_pct']:>7.1f}% {r['win_rate_pct']:>7.1f}% {r['total_trades']:>7}회")
        
        return results
    
    def save_results(self, results: Dict, timestamp: str = None):
        """결과 저장"""
        if timestamp is None:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M')
        
        os.makedirs('./reports/buffett_backtest', exist_ok=True)
        
        # JSON 저장
        json_path = f'./reports/buffett_backtest/backtest_results_{timestamp}.json'
        with open(json_path, 'w', encoding='utf-8') as f:
            json.dump(results, f, ensure_ascii=False, indent=2, default=str)
        
        # CSV 저장
        for strategy, result in results.items():
            if 'trades' in result and result['trades']:
                trades_df = pd.DataFrame(result['trades'])
                csv_path = f'./reports/buffett_backtest/trades_{strategy}_{timestamp}.csv'
                trades_df.to_csv(csv_path, index=False, encoding='utf-8-sig')
            
            if 'portfolio_history' in result:
                history_df = pd.DataFrame(result['portfolio_history'])
                csv_path = f'./reports/buffett_backtest/history_{strategy}_{timestamp}.csv'
                history_df.to_csv(csv_path, index=False, encoding='utf-8-sig')
        
        print(f"\n💾 백테스트 결과 저장 완료:")
        print(f"   {json_path}")
        
        return timestamp


def main():
    """메인 실행"""
    backtester = BuffettBacktester()
    results = backtester.run_all_backtests()
    timestamp = backtester.save_results(results)
    
    return timestamp


if __name__ == '__main__':
    main()
