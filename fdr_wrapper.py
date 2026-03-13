#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
FinanceDataReader Wrapper with Local Database Caching
======================================================
FinanceDataReader API를 감싸는 래퍼 모듈
- DB에 데이터가 있으면 캐시에서 반환 (API 호출 안 함)
- DB에 없으면 API 호출 후 DB에 저장

Usage:
    from fdr_wrapper import FDRWrapper
    
    fdr = FDRWrapper()
    df = fdr.get_price('005930', '2024-01-01', '2024-12-31')
"""

import pandas as pd
import FinanceDataReader as fdr_module
from datetime import datetime, timedelta
from typing import Optional, List, Dict
import sqlite3


class FDRWrapper:
    """
    FinanceDataReader Wrapper with Database Caching
    """
    
    def __init__(self, db_path: str = './data/pivot_strategy.db'):
        """
        Parameters:
        -----------
        db_path : str
            SQLite 데이터베이스 파일 경로
        """
        self.db_path = db_path
        self._cache_stats = {'hit': 0, 'miss': 0, 'api_calls': 0}
    
    def _get_db_data(self, symbol: str, start_date: str, end_date: str) -> pd.DataFrame:
        """DB에서 데이터 조회"""
        try:
            conn = sqlite3.connect(self.db_path)
            query = """
                SELECT * FROM stock_prices 
                WHERE symbol = ? AND date >= ? AND date <= ?
                ORDER BY date
            """
            df = pd.read_sql_query(query, conn, params=(symbol, start_date, end_date))
            conn.close()
            return df
        except Exception as e:
            print(f"⚠️ DB 조회 오류: {e}")
            return pd.DataFrame()
    
    def _get_db_total_count(self, symbol: str) -> int:
        """DB에 저장된 해당 종목의 전체 데이터 개수 확인"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute(
                "SELECT COUNT(*) FROM stock_prices WHERE symbol = ?",
                (symbol,)
            )
            count = cursor.fetchone()[0]
            conn.close()
            return count
        except:
            return 0
    
    def _save_to_db(self, symbol: str, df: pd.DataFrame) -> bool:
        """데이터프레임을 DB에 저장"""
        if df.empty:
            return False
        
        try:
            # 컬럼명 표준화
            df = df.copy()
            df = df.reset_index()
            
            # 컬럼명 매핑
            col_map = {}
            for col in df.columns:
                col_lower = col.lower()
                if col_lower in ['date', 'datetime', 'index']:
                    col_map[col] = 'date'
                elif col_lower in ['open', '시가']:
                    col_map[col] = 'open'
                elif col_lower in ['high', '고가']:
                    col_map[col] = 'high'
                elif col_lower in ['low', '저가']:
                    col_map[col] = 'low'
                elif col_lower in ['close', '종가', 'closing_price']:
                    col_map[col] = 'close'
                elif col_lower in ['volume', '거래량', 'vol']:
                    col_map[col] = 'volume'
            
            df = df.rename(columns=col_map)
            
            # date 컬럼 처리
            if 'date' in df.columns:
                df['date'] = pd.to_datetime(df['date']).dt.strftime('%Y-%m-%d')
            
            # symbol 추가
            df['symbol'] = symbol
            
            # 필요 컬럼 선택
            required_cols = ['symbol', 'date', 'open', 'high', 'low', 'close', 'volume']
            for col in required_cols:
                if col not in df.columns:
                    print(f"⚠️ 누락된 컬럼: {col}")
                    return False
            
            df = df[required_cols]
            
            # DB 저장 (INSERT OR REPLACE)
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            for _, row in df.iterrows():
                cursor.execute('''
                    INSERT OR REPLACE INTO stock_prices 
                    (symbol, date, open, high, low, close, volume)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                ''', (
                    row['symbol'], row['date'], 
                    float(row['open']), float(row['high']), float(row['low']), 
                    float(row['close']), int(row['volume'])
                ))
            conn.commit()
            conn.close()
            return True
            
        except Exception as e:
            print(f"⚠️ DB 저장 오류: {e}")
            return False
    
    def get_price(
        self, 
        symbol: str, 
        start_date: str = None, 
        end_date: str = None,
        min_days: int = 200
    ) -> pd.DataFrame:
        """
        주가 데이터 조회 (DB 우선, 없으면 API)
        
        Flow:
        1. DB에 해당 종목 데이터 있는지 확인 (전체 개수)
        2. DB에 충분한 데이터 있으면 → DB 데이터 리턴 (API 호출 안 함)
        3. DB에 없거나 부족하면 → API 호출 → DB 저장 → 리턴
        
        Parameters:
        -----------
        symbol : str
            종목코드 (예: '005930')
        start_date : str
            시작일 (YYYY-MM-DD), None이면 1년 전
        end_date : str
            종료일 (YYYY-MM-DD), None이면 오늘
        min_days : int
            최소 필요 데이터 일수 (기본 200일)
        
        Returns:
        --------
        pd.DataFrame : 주가 데이터
        """
        # 기본 날짜 설정
        if end_date is None:
            end_date = datetime.now().strftime('%Y-%m-%d')
        if start_date is None:
            start_date = (datetime.now() - timedelta(days=365)).strftime('%Y-%m-%d')
        
        # 1. DB에 해당 종목 데이터가 충분한지 확인
        db_total_count = self._get_db_total_count(symbol)
        
        if db_total_count >= min_days:
            # DB에 충분한 데이터가 있으면 API 호출 없이 DB 데이터 리턴
            df = self._get_db_data(symbol, start_date, end_date)
            if not df.empty:
                self._cache_stats['hit'] += 1
                print(f"💾 DB 캐시 사용: {symbol} (전체: {db_total_count}일, 반환: {len(df)}일)")
                return df
        
        # 2. DB에 데이터가 없거나 부족하면 API 호출
        self._cache_stats['miss'] += 1
        self._cache_stats['api_calls'] += 1
        print(f"🌐 API 호출: {symbol} (DB: {db_total_count}일, 필요: {min_days}일)")
        
        try:
            df = fdr_module.DataReader(symbol, start_date, end_date)
            
            if df.empty:
                print(f"⚠️ API 데이터 없음: {symbol}")
                # API 실패 시 DB에 있는 데이터라도 반환
                df = self._get_db_data(symbol, start_date, end_date)
                if not df.empty:
                    print(f"💾 DB 폼백: {symbol} ({len(df)}일)")
                return df
            
            # DB에 저장
            if self._save_to_db(symbol, df):
                print(f"💾 DB 저장 완료: {symbol} ({len(df)}일)")
            
            return df
            
        except Exception as e:
            print(f"❌ API 오류 ({symbol}): {e}")
            # API 실패 시 DB에 있는 데이터 반환
            df = self._get_db_data(symbol, start_date, end_date)
            if not df.empty:
                print(f"💾 DB 폼백: {symbol} ({len(df)}일)")
            return df
    
    def get_latest_price(self, symbol: str) -> Optional[Dict]:
        """최신 주가 조회"""
        df = self.get_price(symbol, days=5)
        
        if not df.empty:
            row = df.iloc[-1]
            return {
                'symbol': symbol,
                'date': row['date'] if 'date' in row else str(row.name),
                'open': row['open'],
                'high': row['high'],
                'low': row['low'],
                'close': row['close'],
                'volume': int(row['volume'])
            }
        return None
    
    def get_cache_stats(self) -> Dict:
        """캐시 통계 조회"""
        total = self._cache_stats['hit'] + self._cache_stats['miss']
        hit_rate = (self._cache_stats['hit'] / total * 100) if total > 0 else 0
        
        return {
            'cache_hit': self._cache_stats['hit'],
            'cache_miss': self._cache_stats['miss'],
            'total_requests': total,
            'hit_rate': f"{hit_rate:.1f}%",
            'api_calls': self._cache_stats['api_calls']
        }


# 편의 함수
def get_price(symbol: str, start_date: str = None, end_date: str = None, min_days: int = 200) -> pd.DataFrame:
    """단순 주가 조회 함수"""
    wrapper = FDRWrapper()
    return wrapper.get_price(symbol, start_date, end_date, min_days)


if __name__ == "__main__":
    # 테스트
    print("🚀 FDRWrapper 테스트\n")
    
    wrapper = FDRWrapper()
    
    # 1. DB에 있는 종목 테스트 (캐시 사용)
    print("=" * 50)
    print("테스트 1: 삼성전자 (005930)")
    print("=" * 50)
    df = wrapper.get_price('005930')
    print(f"데이터: {len(df)}일")
    if not df.empty:
        print(df.head(3))
    
    # 2. 캐시 통계
    print("\n" + "=" * 50)
    print("캐시 통계")
    print("=" * 50)
    stats = wrapper.get_cache_stats()
    for key, value in stats.items():
        print(f"  {key}: {value}")
    
    print("\n✅ 테스트 완료!")
