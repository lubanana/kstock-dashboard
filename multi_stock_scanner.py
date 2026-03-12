#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Multi-Stock Pivot Point Scanner
===============================
KOSPI/KOSDAQ 종목들을 스캔하여 피벗 포인트 돌파 신호를 포착하는 프로그램

기능:
1. KOSPI/KOSDAQ 전 종목 스캔
2. 피벗 포인트 돌파 + 거래량 급증 필터
3. 결과를 CSV/Excel로 저장
4. 텔레그램/이메일 알림 (선택)
"""

import pandas as pd
import numpy as np
import FinanceDataReader as fdr
from datetime import datetime, timedelta
from typing import List, Dict, Optional
import concurrent.futures
from tqdm import tqdm
import warnings
warnings.filterwarnings('ignore')


class MultiStockScanner:
    """
    다중 종목 스캐너
    """
    
    def __init__(
        self,
        pivot_period: int = 20,
        volume_threshold: float = 1.5,
        min_price: float = 1000,  # 최소 주가 (원)
        min_volume: int = 100000,  # 최소 일평균 거래량
        max_stocks: Optional[int] = None,  # 최대 스캔 종목 수 (테스트용)
    ):
        self.pivot_period = pivot_period
        self.volume_threshold = volume_threshold
        self.min_price = min_price
        self.min_volume = min_volume
        self.max_stocks = max_stocks
        
        self.kospi_codes: List[str] = []
        self.kosdaq_codes: List[str] = []
        self.results: List[Dict] = []
    
    def fetch_stock_list(self) -> pd.DataFrame:
        """
        KOSPI/KOSDAQ 종목 리스트 수집
        """
        print("📋 종목 리스트 수집 중...")
        
        # KOSPI
        kospi = fdr.StockListing('KOSPI')
        kospi['market'] = 'KOSPI'
        
        # KOSDAQ
        kosdaq = fdr.StockListing('KOSDAQ')
        kosdaq['market'] = 'KOSDAQ'
        
        # 합치기
        all_stocks = pd.concat([kospi, kosdaq], ignore_index=True)
        
        # 필터링
        all_stocks = all_stocks[
            (all_stocks['Code'].notna()) & 
            (all_stocks['Name'].notna())
        ].copy()
        
        # 테스트용 제한
        if self.max_stocks:
            all_stocks = all_stocks.head(self.max_stocks)
        
        self.kospi_codes = all_stocks[all_stocks['market'] == 'KOSPI']['Code'].tolist()
        self.kosdaq_codes = all_stocks[all_stocks['market'] == 'KOSDAQ']['Code'].tolist()
        
        print(f"✅ KOSPI: {len(self.kospi_codes)}개, KOSDAQ: {len(self.kosdaq_codes)}개 종목")
        
        return all_stocks
    
    def scan_stock(self, symbol: str, name: str = '', market: str = '') -> Optional[Dict]:
        """
        개별 종목 스캔
        
        Returns:
        --------
        dict : 신호가 감지되면 신호 정보, 아니면 None
        """
        try:
            # 최근 N일 데이터 수집 (분석용 + 계산용 여유분)
            end_date = datetime.now()
            start_date = end_date - timedelta(days=self.pivot_period * 3)
            
            df = fdr.DataReader(symbol, start_date.strftime('%Y-%m-%d'), 
                               end_date.strftime('%Y-%m-%d'))
            
            if len(df) < self.pivot_period + 5:
                return None
            
            # 컬럼명 소문자로
            df.columns = [col.lower() for col in df.columns]
            
            # 최신 데이터
            latest = df.iloc[-1]
            prev = df.iloc[-2]
            
            # 최소 가격 필터
            if latest['close'] < self.min_price:
                return None
            
            # 평균 거래량 필터
            avg_volume = df['volume'].tail(20).mean()
            if avg_volume < self.min_volume:
                return None
            
            # 피벗 고가 계산
            df[f'high_{self.pivot_period}'] = df['high'].rolling(window=self.pivot_period).max()
            
            # 거래량 이동평균
            df['volume_ma20'] = df['volume'].rolling(window=20).mean()
            
            # 피벗 돌파 확인
            pivot_high = df[f'high_{self.pivot_period}'].iloc[-2]  # 전일 기준 N일 고가
            
            # 조건 체크
            price_break = latest['close'] > pivot_high  # 종가가 피벗 고가 돌파
            volume_spike = latest['volume'] > (df['volume_ma20'].iloc[-2] * self.volume_threshold)
            
            if price_break and volume_spike:
                # 신호 감지!
                signal = {
                    'symbol': symbol,
                    'name': name,
                    'market': market,
                    'date': latest.name.strftime('%Y-%m-%d'),
                    'close': latest['close'],
                    'open': latest['open'],
                    'high': latest['high'],
                    'low': latest['low'],
                    'volume': int(latest['volume']),
                    'pivot_high': pivot_high,
                    'volume_ma20': int(df['volume_ma20'].iloc[-2]),
                    'volume_ratio': latest['volume'] / df['volume_ma20'].iloc[-2],
                    'price_change_pct': ((latest['close'] - prev['close']) / prev['close']) * 100,
                    'days_since_pivot': self._count_days_since_pivot(df),
                }
                return signal
            
            return None
            
        except Exception as e:
            return None
    
    def _count_days_since_pivot(self, df: pd.DataFrame) -> int:
        """
        마지막 피벇 고가 갱신 후 경과일 수 계산
        """
        pivot_col = f'high_{self.pivot_period}'
        if pivot_col not in df.columns:
            return 0
        
        latest_pivot = df[pivot_col].iloc[-1]
        
        for i in range(2, min(len(df), self.pivot_period + 1)):
            if df[pivot_col].iloc[-i] != latest_pivot:
                return i - 1
        
        return 0
    
    def scan_all(self, max_workers: int = 4, progress: bool = True) -> pd.DataFrame:
        """
        전 종목 스캔
        
        Parameters:
        -----------
        max_workers : int
            병렬 처리 스레드 수
        progress : bool
            진행바 표시 여부
        """
        # 종목 리스트 수집
        stock_list = self.fetch_stock_list()
        
        symbols = stock_list['Code'].tolist()
        names = stock_list['Name'].tolist()
        markets = stock_list['market'].tolist()
        
        print(f"\n🔍 {len(symbols)}개 종목 스캔 시작...")
        
        self.results = []
        
        # 병렬 스캔
        with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = {
                executor.submit(self.scan_stock, sym, name, market): (sym, name, market)
                for sym, name, market in zip(symbols, names, markets)
            }
            
            iterator = concurrent.futures.as_completed(futures)
            if progress:
                iterator = tqdm(iterator, total=len(futures), desc="Scanning")
            
            for future in iterator:
                result = future.result()
                if result:
                    self.results.append(result)
        
        # DataFrame 변환
        if self.results:
            df = pd.DataFrame(self.results)
            df = df.sort_values('volume_ratio', ascending=False).reset_index(drop=True)
            print(f"\n✅ 신호 감지: {len(df)}개 종목")
            return df
        else:
            print("\n⚠️ 신호 감지된 종목 없음")
            return pd.DataFrame()
    
    def save_results(self, df: pd.DataFrame, output_dir: str = './scans') -> str:
        """
        결과 저장
        """
        import os
        os.makedirs(output_dir, exist_ok=True)
        
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        
        # CSV 저장
        csv_path = os.path.join(output_dir, f'scan_results_{timestamp}.csv')
        df.to_csv(csv_path, index=False, encoding='utf-8-sig')
        
        # Excel 저장
        excel_path = os.path.join(output_dir, f'scan_results_{timestamp}.xlsx')
        df.to_excel(excel_path, index=False, sheet_name='Scan Results')
        
        print(f"📁 결과 저장 완료:")
        print(f"   CSV: {csv_path}")
        print(f"   Excel: {excel_path}")
        
        return csv_path
    
    def get_top_picks(self, df: pd.DataFrame, n: int = 10) -> pd.DataFrame:
        """
        상위 종목 선정 (거래량 비율 + 가격 변동률 기준)
        """
        if df.empty:
            return df
        
        # 종합 점수 계산
        df['score'] = (
            (df['volume_ratio'] - 1) * 50 +  # 거래량 비율 가중치
            df['price_change_pct'].clip(0, 20) * 2  # 가격 상승률 (음수는 0 처리)
        )
        
        return df.nlargest(n, 'score')[['symbol', 'name', 'market', 'close', 
                                        'volume_ratio', 'price_change_pct', 'score']]


def main():
    """
    메인 실행 함수
    """
    # 스캐너 초기화
    scanner = MultiStockScanner(
        pivot_period=20,
        volume_threshold=1.5,
        min_price=1000,
        min_volume=100000,
        # max_stocks=100,  # 테스트용: 100개만 스캔
    )
    
    # 전 종목 스캔
    results = scanner.scan_all(max_workers=8)
    
    if not results.empty:
        # 결과 저장
        scanner.save_results(results)
        
        # 상위 10개 출력
        print("\n🏆 TOP 10 픽:")
        top_picks = scanner.get_top_picks(results, 10)
        print(top_picks.to_string(index=False))
    
    return results


if __name__ == "__main__":
    results = main()
