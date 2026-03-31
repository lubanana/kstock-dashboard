#!/usr/bin/env python3
"""
DART Quality Oversold Scanner 백테스터 (최적화版)
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import json
import sqlite3
import sys
import pickle
import warnings
warnings.filterwarnings('ignore')

sys.path.insert(0, '/root/.openclaw/workspace/strg')

class DARTBacktesterFast:
    def __init__(self, start_date='2024-01-01', end_date='2025-03-31'):
        self.start_date = start_date
        self.end_date = end_date
        self.price_conn = sqlite3.connect('/root/.openclaw/workspace/strg/data/pivot_strategy.db')
        self.dart_conn = sqlite3.connect('/root/.openclaw/workspace/strg/data/dart_financial.db')
        self.fundamental_cache = {}
        self.load_fundamentals()
        
    def load_fundamentals(self):
        print("📊 재무 데이터 로드 중...")
        cursor = self.dart_conn.cursor()
        results = cursor.execute('''
            SELECT stock_code, year, revenue, operating_profit, net_income, 
                   total_assets, total_liabilities, total_equity
            FROM financial_data WHERE reprt_code = '11011'
            ORDER BY stock_code, year DESC
        ''').fetchall()
        
        for row in results:
            code = row[0]
            if code not in self.fundamental_cache:
                self.fundamental_cache[code] = []
            self.fundamental_cache[code].append(row[1:])
        print(f"  ✓ {len(self.fundamental_cache)}개 종목")
    
    def get_fundamental_score(self, symbol, check_date):
        if symbol not in self.fundamental_cache:
            return None
        
        data = self.fundamental_cache[symbol]
        if len(data) < 1:
            return None
        
        year = int(check_date[:4])
        available_years = [int(d[0]) for d in data]
        
        use_year = None
        for y in sorted(available_years, reverse=True):
            if y <= year:
                use_year = y
                break
        
        if use_year is None:
            return None
        
        latest = None
        for d in data:
            if int(d[0]) == use_year:
                latest = d
                break
        
        if not latest:
            return None
        
        revenue, op_profit, net_income, assets, liabilities, equity = latest[1:]
        
        if equity <= 0 or revenue <= 0:
            return None
        
        roe = (net_income / equity) * 100
        debt_ratio = (liabilities / equity) * 100
        op_margin = (op_profit / revenue) * 100
        
        # 퀄리티 점수
        score = 0
        if roe >= 20: score += 30
        elif roe >= 15: score += 25
        elif roe >= 10: score += 20
        elif roe >= 5: score += 10
        
        if debt_ratio <= 50: score += 25
        elif debt_ratio <= 100: score += 20
        elif debt_ratio <= 200: score += 15
        elif debt_ratio <= 300: score += 10
        
        if op_margin >= 20: score += 25
        elif op_margin >= 15: score += 20
        elif op_margin >= 10: score += 15
        elif op_margin >= 5: score += 10
        
        return {'quality_score': score, 'roe': roe, 'debt_ratio': debt_ratio, 'op_margin': op_margin, 'year': use_year}
    
    def run_backtest(self, symbols, trading_dates):
        print(f"\\n📈 백테스트 시작: {len(symbols)}개 종목, {len(trading_dates)}일")
        
        signals = []
        cursor = self.price_conn.cursor()
        
        for i, date in enumerate(trading_dates):
            if i % 5 == 0:
                print(f"  [{i+1}/{len(trading_dates)}] {date}...", end='\\r')
            
            for symbol in symbols:
                # 재무 데이터 확인 (원래 기준: 60점+)
                fund = self.get_fundamental_score(symbol, date)
                if not fund or fund['quality_score'] < 60:
                    continue
                
                # 가격 데이터 조회 (과거 100일)
                start = (datetime.strptime(date, '%Y-%m-%d') - timedelta(days=100)).strftime('%Y-%m-%d')
                rows = cursor.execute('''
                    SELECT date, close, high, low, volume FROM stock_prices
                    WHERE symbol = ? AND date >= ? AND date <= ? ORDER BY date ASC
                ''', (symbol, start, date)).fetchall()
                
                if len(rows) < 50:
                    continue
                
                df = pd.DataFrame(rows, columns=['date', 'close', 'high', 'low', 'volume'])
                latest = df.iloc[-1]
                
                if latest['close'] < 1000:
                    continue
                
                # 52주 고점 대비
                high_52w = df['high'].tail(252).max()
                vs_high = (latest['close'] - high_52w) / high_52w * 100
                
                if vs_high > -10:  # -10% 이상 하락 (원래 기준)
                    continue
                
                # RSI
                prices = df['close']
                delta = prices.diff()
                gain = delta.where(delta > 0, 0).rolling(14).mean()
                loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
                rs = gain / loss
                rsi = 100 - (100 / (1 + rs))
                rsi_val = rsi.iloc[-1]
                
                if rsi_val > 40:  # RSI 40 이하
                    continue
                
                # 신호 발생!
                signal = {
                    'symbol': symbol,
                    'date': date,
                    'entry_price': latest['close'],
                    'quality_score': fund['quality_score'],
                    'roe': fund['roe'],
                    'debt_ratio': fund['debt_ratio'],
                    'op_margin': fund['op_margin'],
                    'rsi': rsi_val,
                    'vs_52w_high': vs_high
                }
                
                # 향후 수익률 계산
                exit_rows = cursor.execute('''
                    SELECT close FROM stock_prices
                    WHERE symbol = ? AND date > ? ORDER BY date ASC LIMIT 60
                ''', (symbol, date)).fetchall()
                
                if exit_rows:
                    closes = [r[0] for r in exit_rows]
                    for days in [5, 10, 20, 40, 60]:
                        if len(closes) >= days:
                            ret = (closes[days-1] - latest['close']) / latest['close'] * 100
                            signal[f'return_{days}d'] = ret
                
                signals.append(signal)
        
        print(f"\\n✅ 총 신호: {len(signals)}개")
        return signals
    
    def analyze(self, signals):
        if not signals:
            print("신호 없음")
            return
        
        df = pd.DataFrame(signals)
        
        print("\\n" + "="*70)
        print("📊 백테스트 결과")
        print("="*70)
        print(f"총 신호: {len(df)}개")
        print(f"기간: {df['date'].min()[:10]} ~ {df['date'].max()[:10]}")
        print(f"\\n평균 재무점수: {df['quality_score'].mean():.1f}점")
        print(f"평균 RSI: {df['rsi'].mean():.1f}")
        print(f"평균 52주대비: {df['vs_52w_high'].mean():.1f}%")
        
        print("\\n" + "-"*70)
        print(f"{'보유기간':<10} {'평균수익':<12} {'승률':<10} {'최대수익':<12} {'최대손실':<12}")
        print("-"*70)
        
        for period in [5, 10, 20, 40, 60]:
            col = f'return_{period}d'
            if col in df.columns:
                valid = df[col].dropna()
                if len(valid) > 0:
                    avg = valid.mean()
                    win = (valid > 0).mean() * 100
                    print(f"{period}일{'':<8} {avg:>+8.2f}% {win:>8.1f}% {valid.max():>+10.1f}% {valid.min():>+10.1f}%")
        
        # 저장
        output = f'/root/.openclaw/workspace/strg/docs/dart_backtest_result.json'
        df.to_json(output, orient='records', force_ascii=False, indent=2)
        print(f"\\n📄 저장: {output}")
        
        return df


def main():
    # 종목 로드
    conn = sqlite3.connect('/root/.openclaw/workspace/strg/data/pivot_strategy.db')
    symbols = [r[0] for r in conn.execute('SELECT symbol FROM stock_info').fetchall()]
    
    # 거래일 (월 1-5일) - 2026년 포함 확장
    dates = [r[0] for r in conn.execute('''
        SELECT DISTINCT date FROM stock_prices
        WHERE date >= '2024-01-01' AND date <= '2026-03-31'
        AND CAST(strftime('%d', date) AS INTEGER) <= 5
        ORDER BY date ASC
    ''').fetchall()]
    conn.close()
    
    print(f"대상: {len(symbols)}개 종목, {len(dates)}개 스캔일")
    
    # 백테스트
    bt = DARTBacktesterFast(start_date='2024-01-01', end_date='2026-03-31')
    signals = bt.run_backtest(symbols, dates)
    bt.analyze(signals)


if __name__ == '__main__':
    main()
