#!/usr/bin/env python3
"""
DART Quality Oversold Scanner 백테스터
전체 코스피/코스닥 종목 대상 백테스트

백테스트 기간: 2024-01-01 ~ 2025-03-31
신호 발생일 기준 수익률 계산
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import json
import sqlite3
import sys
import warnings
warnings.filterwarnings('ignore')

sys.path.insert(0, '/root/.openclaw/workspace/strg')

class DARTBacktester:
    """
    DART 재무 데이터 기반 백테스터
    """
    
    def __init__(self, start_date='2024-01-01', end_date='2025-03-31'):
        self.start_date = start_date
        self.end_date = end_date
        self.trades = []
        
        # DB 연결
        self.price_conn = sqlite3.connect('/root/.openclaw/workspace/strg/data/pivot_strategy.db')
        self.dart_conn = sqlite3.connect('/root/.openclaw/workspace/strg/data/dart_financial.db')
        
        # 재무 데이터 캐시
        self.fundamental_cache = {}
        self.load_all_fundamentals()
    
    def load_all_fundamentals(self):
        """모든 종목의 재무 데이터 로드"""
        print("📊 재무 데이터 로드 중...")
        cursor = self.dart_conn.cursor()
        
        results = cursor.execute('''
            SELECT stock_code, year, revenue, operating_profit, net_income, 
                   total_assets, total_liabilities, total_equity
            FROM financial_data 
            WHERE reprt_code = '11011'
            ORDER BY stock_code, year DESC
        ''').fetchall()
        
        for row in results:
            code = row[0]
            if code not in self.fundamental_cache:
                self.fundamental_cache[code] = []
            self.fundamental_cache[code].append(row[1:])  # year 이후 데이터
        
        print(f"  ✓ {len(self.fundamental_cache)}개 종목 재무 데이터 로드 완료")
    
    def get_fundamental_score(self, symbol, check_date):
        """특정 시점 기준 재무 점수 계산"""
        if symbol not in self.fundamental_cache:
            return None
        
        data = self.fundamental_cache[symbol]
        if len(data) < 2:
            return None
        
        # check_date 이전의 최신 데이터 사용
        year = int(check_date[:4])
        available_years = [int(d[0]) for d in data]
        
        # 사용 가능한 최신 연도 선택
        use_year = None
        for y in sorted(available_years, reverse=True):
            if y <= year:
                use_year = y
                break
        
        if use_year is None:
            return None
        
        # 해당 연도 데이터 찾기
        latest = None
        prev = None
        for d in data:
            if int(d[0]) == use_year:
                latest = d
            elif int(d[0]) == use_year - 1:
                prev = d
        
        if not latest:
            return None
        
        # 지표 계산
        revenue = latest[1]
        operating_profit = latest[2]
        net_income = latest[3]
        total_equity = latest[6]
        total_liabilities = latest[5]
        
        if total_equity <= 0 or revenue <= 0:
            return None
        
        roe = (net_income / total_equity) * 100
        debt_ratio = (total_liabilities / total_equity) * 100
        op_margin = (operating_profit / revenue) * 100
        
        # 성장성
        revenue_growth = 0
        profit_growth = 0
        if prev and prev[1] > 0 and prev[3] > 0:
            revenue_growth = ((latest[1] - prev[1]) / prev[1]) * 100
            profit_growth = ((latest[3] - prev[3]) / prev[3]) * 100
        
        # 퀄리티 점수
        quality_score = 0
        
        if roe >= 20: quality_score += 30
        elif roe >= 15: quality_score += 25
        elif roe >= 10: quality_score += 20
        elif roe >= 5: quality_score += 10
        
        if debt_ratio <= 50: quality_score += 25
        elif debt_ratio <= 100: quality_score += 20
        elif debt_ratio <= 200: quality_score += 15
        elif debt_ratio <= 300: quality_score += 10
        
        if op_margin >= 20: quality_score += 25
        elif op_margin >= 15: quality_score += 20
        elif op_margin >= 10: quality_score += 15
        elif op_margin >= 5: quality_score += 10
        
        if revenue_growth >= 20: quality_score += 10
        elif revenue_growth >= 10: quality_score += 7
        elif revenue_growth >= 0: quality_score += 5
        
        if profit_growth >= 30: quality_score += 10
        elif profit_growth >= 10: quality_score += 7
        elif profit_growth >= 0: quality_score += 5
        
        return {
            'roe': roe,
            'debt_ratio': debt_ratio,
            'op_margin': op_margin,
            'revenue_growth': revenue_growth,
            'profit_growth': profit_growth,
            'quality_score': quality_score,
            'year': use_year
        }
    
    def get_stock_data(self, symbol, date):
        """특정 날짜의 주식 데이터 조회"""
        try:
            # 과거 400일 데이터 조회
            start = (datetime.strptime(date, '%Y-%m-%d') - timedelta(days=400)).strftime('%Y-%m-%d')
            
            cursor = self.price_conn.cursor()
            data = cursor.execute('''
                SELECT date, open, high, low, close, volume
                FROM stock_prices
                WHERE symbol = ? AND date >= ? AND date <= ?
                ORDER BY date ASC
            ''', (symbol, start, date)).fetchall()
            
            if len(data) < 100:
                return None
            
            df = pd.DataFrame(data, columns=['date', 'open', 'high', 'low', 'close', 'volume'])
            df['date'] = pd.to_datetime(df['date'])
            df = df.set_index('date')
            df = df.sort_index()
            
            return df
            
        except Exception as e:
            return None
    
    def calculate_rsi(self, prices, period=14):
        delta = prices.diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
        rs = gain / loss
        return 100 - (100 / (1 + rs))
    
    def check_signal(self, symbol, date):
        """특정 날짜의 매수 신호 체크"""
        try:
            # 재무 데이터 확인
            fundamentals = self.get_fundamental_score(symbol, date)
            if not fundamentals or fundamentals['quality_score'] < 50:  # 50점 이상
                return None
            
            # 가격 데이터 확인
            df = self.get_stock_data(symbol, date)
            if df is None or len(df) < 100:
                return None
            
            # 기술적 지표 계산
            df['RSI'] = self.calculate_rsi(df['close'])
            df['EMA20'] = df['close'].ewm(span=20, adjust=False).mean()
            df['Volume_MA20'] = df['volume'].rolling(window=20).mean()
            
            # 볼린저밴드
            df['BB_Middle'] = df['close'].rolling(window=20).mean()
            df['BB_Std'] = df['close'].rolling(window=20).std()
            df['BB_Lower'] = df['BB_Middle'] - (df['BB_Std'] * 2)
            df['BB_Position'] = (df['close'] - df['BB_Lower']) / (df['BB_Middle'] - df['BB_Lower'])
            
            # 최신 데이터
            latest = df.iloc[-1]
            
            # 52주 고점
            high_52w = df['high'].tail(252).max()
            price_vs_high = (latest['close'] - high_52w) / high_52w * 100
            
            # RSI
            rsi = df['RSI'].iloc[-1]
            bb_position = df['BB_Position'].iloc[-1]
            
            # 과매도 점수
            oversold_score = 0
            if rsi < 30: oversold_score += 40
            elif rsi < 40: oversold_score += 30
            elif rsi < 50: oversold_score += 15
            
            if bb_position < 0.1: oversold_score += 30
            elif bb_position < 0.2: oversold_score += 20
            elif bb_position < 0.3: oversold_score += 10
            
            # 매수 조건 (완화)
            if (fundamentals['quality_score'] >= 40 and  # 50→40
                oversold_score >= 30 and  # 40→30
                price_vs_high <= -5 and  # -10→-5
                latest['close'] >= 1000):
                
                return {
                    'symbol': symbol,
                    'date': date,
                    'entry_price': latest['close'],
                    'quality_score': fundamentals['quality_score'],
                    'oversold_score': oversold_score,
                    'rsi': rsi,
                    'vs_52w_high': price_vs_high,
                    'roe': fundamentals['roe'],
                    'debt_ratio': fundamentals['debt_ratio'],
                    'op_margin': fundamentals['op_margin']
                }
            
            return None
            
        except Exception as e:
            return None
    
    def calculate_exit_returns(self, symbol, entry_date, entry_price):
        """보유 기간별 수익률 계산"""
        returns = {}
        
        try:
            cursor = self.price_conn.cursor()
            
            # 향후 60일 데이터 조회
            for days in [5, 10, 20, 40, 60]:
                exit_date = (datetime.strptime(entry_date, '%Y-%m-%d') + timedelta(days=days)).strftime('%Y-%m-%d')
                
                data = cursor.execute('''
                    SELECT close FROM stock_prices
                    WHERE symbol = ? AND date > ? AND date <= ?
                    ORDER BY date ASC
                    LIMIT 1
                ''', (symbol, entry_date, exit_date)).fetchone()
                
                if data:
                    exit_price = data[0]
                    returns[f'return_{days}d'] = (exit_price - entry_price) / entry_price * 100
                else:
                    returns[f'return_{days}d'] = None
        
        except Exception as e:
            pass
        
        return returns
    
    def run_backtest(self, symbols):
        """백테스트 실행"""
        print("="*70)
        print(f"📊 DART Quality Oversold 백테스트")
        print("="*70)
        print(f"기간: {self.start_date} ~ {self.end_date}")
        print(f"대상: {len(symbols)}개 종목")
        print()
        
        # 거래일 리스트 생성 (월 1회 첫 영업일)
        cursor = self.price_conn.cursor()
        trading_dates = cursor.execute('''
            SELECT DISTINCT date FROM stock_prices
            WHERE date >= ? AND date <= ?
            AND strftime('%d', date) <= '05'
            ORDER BY date ASC
        ''', (self.start_date, self.end_date)).fetchall()
        
        trading_dates = [d[0] for d in trading_dates]
        print(f"스캔일: {len(trading_dates)}회")
        print()
        
        all_signals = []
        
        for i, date in enumerate(trading_dates):
            print(f"  [{i+1}/{len(trading_dates)}] {date} 스캔 중...", end='\r')
            
            for symbol in symbols:
                signal = self.check_signal(symbol, date)
                if signal:
                    # 수익률 계산
                    returns = self.calculate_exit_returns(symbol, date, signal['entry_price'])
                    signal.update(returns)
                    all_signals.append(signal)
                    print(f"  ✓ {date} - {symbol} - 재무:{signal['quality_score']:.0f}")
        
        print(f"\n\n✅ 총 신호: {len(all_signals)}개")
        return all_signals
    
    def analyze_results(self, signals):
        """결과 분석"""
        if not signals:
            print("신호 없음")
            return
        
        df = pd.DataFrame(signals)
        
        print("\n" + "="*70)
        print("📈 백테스트 결과 분석")
        print("="*70)
        
        # 기본 통계
        print(f"\n총 신호 수: {len(df)}개")
        print(f"평균 진입가: {df['entry_price'].mean():,.0f}원")
        print(f"평균 재무점수: {df['quality_score'].mean():.1f}점")
        print(f"평균 RSI: {df['rsi'].mean():.1f}")
        
        # 수익률 분석
        periods = [5, 10, 20, 40, 60]
        
        print("\n" + "-"*70)
        print(f"{'보유기간':<10} {'평균수익':<12} {'승률':<10} {'최대수익':<12} {'최대손실':<12}")
        print("-"*70)
        
        for period in periods:
            col = f'return_{period}d'
            if col in df.columns:
                valid = df[col].dropna()
                if len(valid) > 0:
                    avg_return = valid.mean()
                    win_rate = (valid > 0).mean() * 100
                    max_return = valid.max()
                    min_return = valid.min()
                    
                    print(f"{period}일{'':<8} {avg_return:>+8.2f}% {win_rate:>8.1f}% {max_return:>+10.1f}% {min_return:>+10.1f}%")
        
        # 월별 신호 수
        print("\n" + "-"*70)
        print("월별 신호 수:")
        df['year_month'] = pd.to_datetime(df['date']).dt.to_period('M')
        monthly = df.groupby('year_month').size()
        for ym, cnt in monthly.items():
            print(f"  {ym}: {cnt}개")
        
        # TOP 종목
        print("\n" + "-"*70)
        print("📊 TOP 수익 종목 (20일 보유 기준)")
        if 'return_20d' in df.columns:
            top = df.nlargest(10, 'return_20d')[['symbol', 'date', 'entry_price', 'return_20d', 'quality_score']]
            for _, row in top.iterrows():
                print(f"  {row['symbol']} ({row['date'][:10]}): {row['return_20d']:+.1f}% (재무:{row['quality_score']:.0f})")
        
        return df
    
    def save_results(self, df):
        """결과 저장"""
        output_file = f'/root/.openclaw/workspace/strg/docs/dart_backtest_{self.start_date}_{self.end_date}.json'
        df.to_json(output_file, orient='records', force_ascii=False, indent=2)
        print(f"\n📄 결과 저장: {output_file}")


def main():
    # 종목 리스트 로드
    conn = sqlite3.connect('/root/.openclaw/workspace/strg/data/pivot_strategy.db')
    symbols = [row[0] for row in conn.execute('SELECT symbol FROM stock_info').fetchall()]
    conn.close()
    
    # 백테스트 실행
    backtester = DARTBacktester()
    signals = backtester.run_backtest(symbols)
    
    if signals:
        df = backtester.analyze_results(signals)
        backtester.save_results(df)
    else:
        print("\n⚠️ 신호가 없습니다.")


if __name__ == '__main__':
    main()
