#!/usr/bin/env python3
"""
S-Series Sequential Scanner
S1: 거래대금 TOP 20
S2: 턴어라운드  
S3: 신규 모멘텀

순차 실행 및 결과 저장
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Tuple
import json
import sys
sys.path.insert(0, '/root/.openclaw/workspace/strg')

from fdr_wrapper import FDRWrapper
from local_db import LocalDB


class SSeriesScanner:
    """S시리즈 순차 스캐너"""
    
    def __init__(self, db_path: str = './data/pivot_strategy.db'):
        self.db = LocalDB(db_path)
        self.fdr = FDRWrapper(db_path=db_path)
        self.today = datetime.now().strftime('%Y-%m-%d')
        self.timestamp = datetime.now().strftime('%Y%m%d_%H%M')
        
    def get_all_stocks(self) -> pd.DataFrame:
        """전체 종목 로드"""
        query = "SELECT symbol, name, market FROM stock_info ORDER BY market, symbol"
        df = pd.read_sql_query(query, self.db.conn)
        print(f"📊 총 {len(df)}개 종목 로드 (KOSPI {len(df[df['market']=='KOSPI'])}, KOSDAQ {len(df[df['market']=='KOSDAQ'])})\n")
        return df
    
    def load_price_data(self, symbol: str, days: int = 60) -> pd.DataFrame:
        """가격 데이터 로드"""
        try:
            end = self.today
            start = (datetime.now() - timedelta(days=days)).strftime('%Y-%m-%d')
            df = self.fdr.get_price(symbol, start=start, end=end)
            return df
        except Exception as e:
            print(f"⚠️ {symbol} 데이터 로드 실패: {e}")
            return pd.DataFrame()
    
    def run_s1_top20(self, all_data: Dict[str, pd.DataFrame]) -> pd.DataFrame:
        """
        S1: 거래대금 TOP 20
        - 20일 평균 거래대금 10억원 이상
        - 거래대금 기준 상위 20개
        """
        print("=" * 60)
        print("📊 S1: 거래대금 TOP 20 스캔 시작")
        print("=" * 60)
        
        results = []
        for symbol, df in all_data.items():
            if df.empty or len(df) < 20:
                continue
            
            # 20일 평균 거래대금 계산
            df['amount'] = df['close'] * df['volume']
            avg_amount = df['amount'].tail(20).mean()
            
            if avg_amount >= 1e9:  # 10억원 이상
                results.append({
                    'symbol': symbol,
                    'name': df.get('name', symbol),
                    'avg_amount': avg_amount,
                    'latest_price': df['close'].iloc[-1],
                    'latest_volume': df['volume'].iloc[-1]
                })
        
        # 정렬
        df_result = pd.DataFrame(results)
        if not df_result.empty:
            df_result = df_result.sort_values('avg_amount', ascending=False).head(20)
            df_result['rank'] = range(1, len(df_result) + 1)
        
        print(f"✅ S1 완료: {len(df_result)}개 종목 선정\n")
        return df_result
    
    def run_s2_turnaround(self, all_data: Dict[str, pd.DataFrame]) -> pd.DataFrame:
        """
        S2: 턴어라운드
        - 60일 저점 대비 10% 이상 반등
        - RSI 40~60 (중립 구간)
        """
        print("=" * 60)
        print("📊 S2: 턴어라운드 스캔 시작")
        print("=" * 60)
        
        results = []
        for symbol, df in all_data.items():
            if df.empty or len(df) < 60:
                continue
            
            # 60일 저점 및 현재가
            low_60d = df['low'].tail(60).min()
            current = df['close'].iloc[-1]
            rebound_pct = (current - low_60d) / low_60d * 100
            
            # RSI 계산 (14일)
            if len(df) >= 14:
                delta = df['close'].diff()
                gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
                loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
                rs = gain / loss
                rsi = 100 - (100 / (1 + rs))
                current_rsi = rsi.iloc[-1]
            else:
                continue
            
            # 조건: 60일 저점 대비 10% 이상 반등 + RSI 40~60
            if rebound_pct >= 10 and 40 <= current_rsi <= 60:
                results.append({
                    'symbol': symbol,
                    'name': df.get('name', symbol),
                    'current_price': current,
                    'low_60d': low_60d,
                    'rebound_pct': rebound_pct,
                    'rsi': current_rsi
                })
        
        df_result = pd.DataFrame(results)
        if not df_result.empty:
            df_result = df_result.sort_values('rebound_pct', ascending=False)
        
        print(f"✅ S2 완료: {len(df_result)}개 종목 선정\n")
        return df_result
    
    def run_s3_momentum(self, all_data: Dict[str, pd.DataFrame]) -> pd.DataFrame:
        """
        S3: 신규 모멘텀
        - MACD > 0
        - RSI > 50
        """
        print("=" * 60)
        print("📊 S3: 신규 모멘텀 스캔 시작")
        print("=" * 60)
        
        results = []
        for symbol, df in all_data.items():
            if df.empty or len(df) < 26:
                continue
            
            # MACD 계산
            ema12 = df['close'].ewm(span=12).mean()
            ema26 = df['close'].ewm(span=26).mean()
            macd = ema12 - ema26
            signal = macd.ewm(span=9).mean()
            macd_hist = macd - signal
            
            # RSI 계산
            delta = df['close'].diff()
            gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
            loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
            rs = gain / loss
            rsi = 100 - (100 / (1 + rs))
            
            current_macd = macd.iloc[-1]
            current_rsi = rsi.iloc[-1]
            
            # 조건: MACD > 0 + RSI > 50
            if current_macd > 0 and current_rsi > 50:
                results.append({
                    'symbol': symbol,
                    'name': df.get('name', symbol),
                    'current_price': df['close'].iloc[-1],
                    'macd': current_macd,
                    'rsi': current_rsi
                })
        
        df_result = pd.DataFrame(results)
        if not df_result.empty:
            df_result = df_result.sort_values('macd', ascending=False)
        
        print(f"✅ S3 완료: {len(df_result)}개 종목 선정\n")
        return df_result
    
    def save_results(self, s1_df: pd.DataFrame, s2_df: pd.DataFrame, s3_df: pd.DataFrame):
        """결과 저장"""
        output_dir = f'./reports/strategy_sequential'
        import os
        os.makedirs(output_dir, exist_ok=True)
        
        # S1 저장
        s1_csv = f'{output_dir}/s1_top20_{self.timestamp}.csv'
        s1_json = f'{output_dir}/s1_top20_{self.timestamp}.json'
        s1_df.to_csv(s1_csv, index=False, encoding='utf-8-sig')
        s1_df.to_json(s1_json, orient='records', force_ascii=False, indent=2)
        print(f"💾 S1 저장: {s1_csv}")
        
        # S2 저장
        s2_csv = f'{output_dir}/s2_turnaround_{self.timestamp}.csv'
        s2_json = f'{output_dir}/s2_turnaround_{self.timestamp}.json'
        s2_df.to_csv(s2_csv, index=False, encoding='utf-8-sig')
        s2_df.to_json(s2_json, orient='records', force_ascii=False, indent=2)
        print(f"💾 S2 저장: {s2_csv}")
        
        # S3 저장
        s3_csv = f'{output_dir}/s3_momentum_{self.timestamp}.csv'
        s3_json = f'{output_dir}/s3_momentum_{self.timestamp}.json'
        s3_df.to_csv(s3_csv, index=False, encoding='utf-8-sig')
        s3_df.to_json(s3_json, orient='records', force_ascii=False, indent=2)
        print(f"💾 S3 저장: {s3_csv}")
    
    def run_all(self):
        """전체 실행"""
        print("\n🚀 S-Series 스캐너 순차 실행")
        print(f"시작 시간: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        
        start_time = datetime.now()
        
        # 종목 로드
        stocks_df = self.get_all_stocks()
        
        # 가격 데이터 로드
        print("📥 가격 데이터 로드 중...")
        all_data = {}
        for idx, row in stocks_df.iterrows():
            symbol = row['symbol']
            df = self.load_price_data(symbol)
            if not df.empty:
                df['name'] = row['name']
                all_data[symbol] = df
            
            if (idx + 1) % 500 == 0:
                print(f"  진행: {idx + 1}/{len(stocks_df)} 종목")
        
        print(f"✅ 데이터 로드 완료: {len(all_data)}개 종목\n")
        
        # S1 실행
        s1_start = datetime.now()
        s1_df = self.run_s1_top20(all_data)
        s1_time = (datetime.now() - s1_start).total_seconds()
        
        # S2 실행
        s2_start = datetime.now()
        s2_df = self.run_s2_turnaround(all_data)
        s2_time = (datetime.now() - s2_start).total_seconds()
        
        # S3 실행
        s3_start = datetime.now()
        s3_df = self.run_s3_momentum(all_data)
        s3_time = (datetime.now() - s3_start).total_seconds()
        
        # 결과 저장
        self.save_results(s1_df, s2_df, s3_df)
        
        # 종합 결과 출력
        total_time = (datetime.now() - start_time).total_seconds()
        
        print("\n" + "=" * 60)
        print("📊 S-Series 스캔 결과 종합")
        print("=" * 60)
        print(f"S1 (거래대금 TOP 20): {len(s1_df)}개 종목 - {s1_time:.1f}초")
        print(f"S2 (턴어라운드):      {len(s2_df)}개 종목 - {s2_time:.1f}초")
        print(f"S3 (신규 모멘텀):     {len(s3_df)}개 종목 - {s3_time:.1f}초")
        print(f"총 실행 시간: {total_time:.1f}초")
        print("=" * 60)
        
        # TOP 5 표시
        if not s1_df.empty:
            print("\n🏆 S1 TOP 5 (거래대금 기준):")
            for i, row in s1_df.head(5).iterrows():
                print(f"  {row['rank']:2d}. {row['symbol']} ({row.get('name', 'N/A')[:8]:8s}): {row['avg_amount']/1e8:6.1f}억원")
        
        if not s2_df.empty:
            print("\n🏆 S2 TOP 5 (반등률 기준):")
            for i, row in s2_df.head(5).iterrows():
                print(f"  {i+1:2d}. {row['symbol']} ({row.get('name', 'N/A')[:8]:8s}): {row['rebound_pct']:+6.1f}% (RSI: {row['rsi']:.1f})")
        
        if not s3_df.empty:
            print("\n🏆 S3 TOP 5 (MACD 기준):")
            for i, row in s3_df.head(5).iterrows():
                print(f"  {i+1:2d}. {row['symbol']} ({row.get('name', 'N/A')[:8]:8s}): MACD {row['macd']:8.0f} (RSI: {row['rsi']:.1f})")


if __name__ == '__main__':
    scanner = SSeriesScanner()
    scanner.run_all()
