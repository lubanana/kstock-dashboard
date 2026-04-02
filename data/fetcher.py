#!/usr/bin/env python3
"""
KStock Analyzer - Data Fetcher Module
FinanceDataReader를 활용한 한국 주식 데이터 수집
"""

import FinanceDataReader as fdr
import pandas as pd
from datetime import datetime, timedelta
from typing import Optional, List, Dict


class StockDataFetcher:
    """한국 주식 데이터 수집기"""
    
    def __init__(self):
        self.krx_stocks = None
        self._load_stock_list()
    
    def _load_stock_list(self):
        """KRX 전체 종목 리스트 로드"""
        try:
            self.krx_stocks = fdr.StockListing('KRX')
            print(f"📋 KRX 종목 로드 완료: {len(self.krx_stocks)}개")
        except Exception as e:
            print(f"⚠️ 종목 리스트 로드 실패: {e}")
            self.krx_stocks = pd.DataFrame()
    
    def get_stock_list(self, market: str = 'KRX') -> pd.DataFrame:
        """시장별 종목 리스트 조회"""
        return fdr.StockListing(market)
    
    def get_price(self, 
                  symbol: str, 
                  start: Optional[str] = None, 
                  end: Optional[str] = None,
                  period: int = 252) -> pd.DataFrame:
        """특정 종목 가격 데이터 조회"""
        if start is None:
            start = (datetime.now() - timedelta(days=period)).strftime('%Y-%m-%d')
        if end is None:
            end = datetime.now().strftime('%Y-%m-%d')
        
        df = fdr.DataReader(symbol, start, end)
        df['Symbol'] = symbol
        df['Name'] = self._get_name(symbol)
        return df
    
    def get_index(self, 
                  index_name: str = 'KS11', 
                  period: int = 252) -> pd.DataFrame:
        """지수 데이터 조회"""
        start = (datetime.now() - timedelta(days=period)).strftime('%Y-%m-%d')
        end = datetime.now().strftime('%Y-%m-%d')
        return fdr.DataReader(index_name, start, end)
    
    def _get_name(self, symbol: str) -> str:
        """종목코드로 종목명 조회"""
        if self.krx_stocks is not None and not self.krx_stocks.empty:
            match = self.krx_stocks[self.krx_stocks['Code'] == symbol]
            if not match.empty:
                return match.iloc[0]['Name']
        return symbol
    
    def search_stock(self, keyword: str) -> pd.DataFrame:
        """키워드로 종목 검색"""
        if self.krx_stocks is None or self.krx_stocks.empty:
            return pd.DataFrame()
        
        mask = (
            self.krx_stocks['Name'].str.contains(keyword, na=False, case=False) |
            self.krx_stocks['Code'].str.contains(keyword, na=False)
        )
        return self.krx_stocks[mask]


if __name__ == "__main__":
    fetcher = StockDataFetcher()
    
    # 테스트
    print("\n🔍 삼성전자 검색:")
    results = fetcher.search_stock('삼성')
    print(results[['Code', 'Name', 'Market']].head())
    
    print("\n📊 삼성전자 최근 5일:")
    df = fetcher.get_price('005930', period=5)
    print(df)
