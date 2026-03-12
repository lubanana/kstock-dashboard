#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Stock Repository Module
=======================
날짜 디비에서 주식 종목 정보를 관리하는 클래스

Features:
- 전체 종목 조회 (KOSPI/KOSDAQ)
- 개별 종목 정보 조회
- 종목 검색 (이름/코드)
- 시장별 필터링
"""

import sqlite3
import pandas as pd
from typing import List, Dict, Optional, Tuple
from pathlib import Path


class StockRepository:
    """
    주식 종목 정보 저장소 클래스
    """
    
    def __init__(self, db_path: str = './data/pivot_strategy.db'):
        """
        Parameters:
        -----------
        db_path : str
            SQLite 데이터베이스 파일 경로
        """
        self.db_path = db_path
        self.conn = sqlite3.connect(db_path)
        self.conn.row_factory = sqlite3.Row
    
    def get_all_stocks(self, market: str = None) -> pd.DataFrame:
        """
        전체 종목 조회
        
        Parameters:
        -----------
        market : str
            'KOSPI', 'KOSDAQ' 또는 None(전체)
        
        Returns:
        --------
        pd.DataFrame : 종목 정보
        """
        query = "SELECT * FROM stock_info"
        params = []
        
        if market:
            query += " WHERE market = ?"
            params.append(market)
        
        query += " ORDER BY symbol"
        
        return pd.read_sql_query(query, self.conn, params=params)
    
    def get_stock_by_symbol(self, symbol: str) -> Optional[Dict]:
        """
        종목 코드로 조회
        
        Parameters:
        -----------
        symbol : str
            종목코드 (예: '005930')
        
        Returns:
        --------
        dict : 종목 정보 또는 None
        """
        cursor = self.conn.cursor()
        cursor.execute(
            "SELECT * FROM stock_info WHERE symbol = ?",
            (symbol,)
        )
        row = cursor.fetchone()
        
        if row:
            return dict(row)
        return None
    
    def search_stocks(self, keyword: str) -> pd.DataFrame:
        """
        종목명 또는 코드로 검색
        
        Parameters:
        -----------
        keyword : str
            검색 키워드
        
        Returns:
        --------
        pd.DataFrame : 검색 결과
        """
        query = """
            SELECT * FROM stock_info 
            WHERE name LIKE ? OR symbol LIKE ?
            ORDER BY 
                CASE WHEN symbol = ? THEN 0 ELSE 1 END,
                name
        """
        params = [f'%{keyword}%', f'%{keyword}%', keyword]
        
        return pd.read_sql_query(query, self.conn, params=params)
    
    def get_market_summary(self) -> pd.DataFrame:
        """
        시장별 종목 수 요약
        
        Returns:
        --------
        pd.DataFrame : 시장별 통계
        """
        query = """
            SELECT 
                market,
                COUNT(*) as total_count,
                MIN(updated_at) as oldest_update,
                MAX(updated_at) as latest_update
            FROM stock_info
            GROUP BY market
            ORDER BY market
        """
        return pd.read_sql_query(query, self.conn)
    
    def get_stocks_by_market(self, market: str, limit: int = None) -> List[Dict]:
        """
        특정 시장의 종목 리스트 조회
        
        Parameters:
        -----------
        market : str
            'KOSPI' 또는 'KOSDAQ'
        limit : int
            최대 조회 개수
        
        Returns:
        --------
        List[Dict] : 종목 정보 리스트
        """
        query = "SELECT * FROM stock_info WHERE market = ? ORDER BY symbol"
        params = [market]
        
        if limit:
            query += f" LIMIT {limit}"
        
        df = pd.read_sql_query(query, self.conn, params=params)
        return df.to_dict('records')
    
    def get_sample_stocks(self, n: int = 10, market: str = None) -> List[Dict]:
        """
        샘플 종목 조회 (테스트용)
        
        Parameters:
        -----------
        n : int
            샘플 개수
        market : str
            특정 시장 필터
        
        Returns:
        --------
        List[Dict] : 종목 정보 리스트
        """
        query = "SELECT * FROM stock_info"
        params = []
        
        if market:
            query += " WHERE market = ?"
            params.append(market)
        
        query += f" ORDER BY RANDOM() LIMIT {n}"
        
        df = pd.read_sql_query(query, self.conn, params=params)
        return df.to_dict('records')
    
    def get_stock_count(self, market: str = None) -> int:
        """
        종목 수 조회
        
        Parameters:
        -----------
        market : str
            특정 시장 필터
        
        Returns:
        --------
        int : 종목 수
        """
        query = "SELECT COUNT(*) FROM stock_info"
        params = []
        
        if market:
            query += " WHERE market = ?"
            params.append(market)
        
        cursor = self.conn.cursor()
        cursor.execute(query, params)
        return cursor.fetchone()[0]
    
    def stock_exists(self, symbol: str) -> bool:
        """
        종목 존재 여부 확인
        
        Parameters:
        -----------
        symbol : str
            종목코드
        
        Returns:
        --------
        bool : 존재 여부
        """
        cursor = self.conn.cursor()
        cursor.execute(
            "SELECT 1 FROM stock_info WHERE symbol = ?",
            (symbol,)
        )
        return cursor.fetchone() is not None
    
    def close(self):
        """DB 연결 종료"""
        self.conn.close()
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()


def main():
    """테스트 실행"""
    print("🚀 StockRepository 테스트\n")
    
    with StockRepository() as repo:
        # 1. 전체 종목 수
        print("📊 전체 종목 수:")
        kospi_count = repo.get_stock_count('KOSPI')
        kosdaq_count = repo.get_stock_count('KOSDAQ')
        print(f"  KOSPI: {kospi_count}개")
        print(f"  KOSDAQ: {kosdaq_count}개")
        print(f"  총계: {kospi_count + kosdaq_count}개\n")
        
        # 2. 개별 종목 조회
        print("📋 개별 종목 조회 (005930):")
        stock = repo.get_stock_by_symbol('005930')
        if stock:
            print(f"  코드: {stock['symbol']}")
            print(f"  이름: {stock['name']}")
            print(f"  시장: {stock['market']}\n")
        
        # 3. 종목 검색
        print("🔍 '삼성' 검색:")
        results = repo.search_stocks('삼성')
        print(results[['symbol', 'name', 'market']].head().to_string(index=False))
        print()
        
        # 4. 샘플 종목
        print("🎲 샘플 종목 (5개):")
        samples = repo.get_sample_stocks(5)
        for s in samples:
            print(f"  - {s['symbol']}: {s['name']} ({s['market']})")
    
    print("\n✅ 테스트 완료!")


if __name__ == "__main__":
    main()
