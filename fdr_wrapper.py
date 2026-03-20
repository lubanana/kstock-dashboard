#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
FinanceDataReader Wrapper with Local Database Caching
======================================================
FinanceDataReader API를 감싸는 래퍼 모듈
- DB에 데이터가 있으면 캐시에서 반환
- 없으면 API 호출 후 DB에 저장

Usage:
    from fdr_wrapper import FDRWrapper
    
    fdr = FDRWrapper()
    df = fdr.get_price('005930', '2024-01-01', '2024-12-31')
"""

import pandas as pd
import sqlite3
import FinanceDataReader as fdr_module
from datetime import datetime, timedelta
from typing import Optional, List, Dict
from pathlib import Path


class LocalDB:
    """간소화된 로컬 DB 클래스"""
    
    def __init__(self, db_path: str = './data/pivot_strategy.db'):
        self.db_path = db_path
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        self.conn = sqlite3.connect(db_path)
        self.conn.row_factory = sqlite3.Row
        self._init_tables()
    
    def _init_tables(self):
        """테이블 초기화"""
        cursor = self.conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS stock_prices (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                symbol TEXT NOT NULL,
                date TEXT NOT NULL,
                open REAL,
                high REAL,
                low REAL,
                close REAL,
                volume INTEGER,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(symbol, date)
            )
        ''')
        self.conn.commit()
    
    def get_prices(self, symbol: str, start_date: str, end_date: str) -> pd.DataFrame:
        """주가 데이터 조회"""
        query = '''
            SELECT date, open, high, low, close, volume
            FROM stock_prices
            WHERE symbol = ? AND date >= ? AND date <= ?
            ORDER BY date
        '''
        df = pd.read_sql_query(query, self.conn, params=(symbol, start_date, end_date))
        if not df.empty:
            df['date'] = pd.to_datetime(df['date'])
            df.set_index('date', inplace=True)
            # 컬럼명 대문자로 변환 (FinanceDataReader 호환)
            df.columns = [col.capitalize() for col in df.columns]
        return df
    
    def save_prices(self, df: pd.DataFrame, symbol: str):
        """주가 데이터 저장"""
        if df.empty:
            return
        
        cursor = self.conn.cursor()
        
        # DataFrame 복사 및 처리
        df_copy = df.copy()
        
        # 인덱스가 날짜인 경우 처리
        if isinstance(df_copy.index, pd.DatetimeIndex):
            df_copy = df_copy.reset_index()
            date_col = df_copy.columns[0]
        else:
            date_col = 'Date' if 'Date' in df_copy.columns else 'date'
        
        # 컬럼명 소문자로 통일
        col_map = {}
        for col in df_copy.columns:
            col_lower = col.lower()
            if col_lower in ['date', 'open', 'high', 'low', 'close', 'volume']:
                col_map[col] = col_lower
        df_copy.rename(columns=col_map, inplace=True)
        
        # 필요한 컬럼 확인
        required_cols = ['date', 'open', 'high', 'low', 'close', 'volume']
        for col in required_cols:
            if col not in df_copy.columns:
                print(f"⚠️ 누락된 컬럼: {col}")
                return
        
        # 데이터 삽입
        for _, row in df_copy.iterrows():
            try:
                date_val = row['date']
                if hasattr(date_val, 'strftime'):
                    date_str = date_val.strftime('%Y-%m-%d')
                else:
                    date_str = str(date_val)[:10]
                
                cursor.execute('''
                    INSERT OR REPLACE INTO stock_prices 
                    (symbol, date, open, high, low, close, volume)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                ''', (
                    symbol,
                    date_str,
                    float(row['open']),
                    float(row['high']),
                    float(row['low']),
                    float(row['close']),
                    int(row['volume'])
                ))
            except Exception as e:
                print(f"⚠️ 저장 오류 ({symbol}): {e}")
                continue
        
        self.conn.commit()
    
    def get_last_update(self, symbol: str) -> Optional[str]:
        """마지막 업데이트 날짜 조회"""
        cursor = self.conn.cursor()
        cursor.execute(
            "SELECT MAX(date) FROM stock_prices WHERE symbol = ?",
            (symbol,)
        )
        result = cursor.fetchone()
        return result[0] if result and result[0] else None
    
    def close(self):
        """DB 연결 종료"""
        self.conn.close()


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
        self.db = LocalDB(db_path)
        self._cache_stats = {'hit': 0, 'miss': 0, 'api_calls': 0}
    
    def get_price(
        self, 
        symbol: str, 
        start_date: str = None, 
        end_date: str = None,
        force_update: bool = False
    ) -> pd.DataFrame:
        """
        주가 데이터 조회 (캐시 우선)
        
        Parameters:
        -----------
        symbol : str
            종목코드 (예: '005930')
        start_date : str
            시작일 (YYYY-MM-DD), None이면 1년 전
        end_date : str
            종료일 (YYYY-MM-DD), None이면 오늘
        force_update : bool
            True면 캐시 무시하고 API 강제 호출
        
        Returns:
        --------
        pd.DataFrame : 주가 데이터 (Open, High, Low, Close, Volume)
        """
        # 기본 날짜 설정
        if end_date is None:
            end_date = datetime.now().strftime('%Y-%m-%d')
        if start_date is None:
            start_date = (datetime.now() - timedelta(days=365)).strftime('%Y-%m-%d')
        
        # 1. DB에서 데이터 조회 (force_update가 아닐 때)
        if not force_update:
            cached_data = self.db.get_prices(symbol, start_date, end_date)
            if not cached_data.empty:
                # 요청한 기간의 데이터가 충분한지 확인
                expected_days = self._estimate_trading_days(start_date, end_date)
                if len(cached_data) >= expected_days * 0.8:  # 80% 이상 있으면 캐시 사용
                    self._cache_stats['hit'] += 1
                    return cached_data
                else:
                    # 부분 데이터 - API로 보충 필요
                    pass
        
        # 2. API 호출
        self._cache_stats['miss'] += 1
        self._cache_stats['api_calls'] += 1
        
        try:
            df = fdr_module.DataReader(symbol, start_date, end_date)
            
            if df.empty:
                # API 실패 시 캐시된 데이터라도 반환
                if not force_update:
                    cached_data = self.db.get_prices(symbol, start_date, end_date)
                    if not cached_data.empty:
                        return cached_data
                return pd.DataFrame()
            
            # 컬럼명 대문자로 통일
            df.columns = [col.capitalize() if col.lower() in ['open', 'high', 'low', 'close', 'volume'] else col for col in df.columns]
            
            # 3. DB에 저장
            self.db.save_prices(df, symbol)
            
            return df
            
        except Exception as e:
            # API 오류 시 캐시된 데이터 반환
            if not force_update:
                cached_data = self.db.get_prices(symbol, start_date, end_date)
                if not cached_data.empty:
                    return cached_data
            return pd.DataFrame()
    
    def get_latest_price(self, symbol: str) -> Optional[Dict]:
        """
        최신 주가 조회
        
        Returns:
        --------
        Dict : 최신 주가 정보 또는 None
        """
        # 먼저 DB에서 최신 데이터 확인
        last_update = self.db.get_last_update(symbol)
        today = datetime.now().strftime('%Y-%m-%d')
        
        if last_update == today:
            # 오늘 데이터가 있으면 캐시에서 반환
            df = self.db.get_prices(symbol, today, today)
            if not df.empty:
                row = df.iloc[-1]
                return {
                    'symbol': symbol,
                    'date': today,
                    'open': row['Open'],
                    'high': row['High'],
                    'low': row['Low'],
                    'close': row['Close'],
                    'volume': int(row['Volume'])
                }
        
        # 없으면 API 호출 (최근 5일)
        start = (datetime.now() - timedelta(days=5)).strftime('%Y-%m-%d')
        df = self.get_price(symbol, start, today)
        
        if not df.empty:
            row = df.iloc[-1]
            date_str = row.name.strftime('%Y-%m-%d') if hasattr(row.name, 'strftime') else str(row.name)
            return {
                'symbol': symbol,
                'date': date_str,
                'open': row['Open'],
                'high': row['High'],
                'low': row['Low'],
                'close': row['Close'],
                'volume': int(row['Volume'])
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
    
    def _estimate_trading_days(self, start_date: str, end_date: str) -> int:
        """영업일 수 추정 (주말 제외)"""
        start = datetime.strptime(start_date, '%Y-%m-%d')
        end = datetime.strptime(end_date, '%Y-%m-%d')
        days = (end - start).days + 1
        # 주말 제외 (약 71%가 영업일)
        return int(days * 0.71)
    
    def close(self):
        """DB 연결 종료"""
        self.db.close()
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()


# 편의 함수들
def get_price(symbol: str, start_date: str = None, end_date: str = None) -> pd.DataFrame:
    """
    단순 주가 조회 함수 (컨텍스트 매니저 없이 사용)
    """
    wrapper = FDRWrapper()
    df = wrapper.get_price(symbol, start_date, end_date)
    wrapper.close()
    return df


def get_latest(symbol: str) -> Optional[Dict]:
    """
    최신 주가 조회 함수
    """
    wrapper = FDRWrapper()
    result = wrapper.get_latest_price(symbol)
    wrapper.close()
    return result


if __name__ == "__main__":
    # 테스트
    print("🚀 FDRWrapper 테스트\n")
    
    # 1. 단일 종목 조회
    print("테스트 1: 삼성전자 조회")
    df = get_price('005930', '2024-01-01', '2024-01-31')
    print(f"데이터: {len(df)}일")
    print(df.head(3))
    
    # 2. 최신 주가 조회
    print("\n테스트 2: 최신 주가 조회")
    latest = get_latest('005930')
    print(latest)
    
    print("\n✅ 테스트 완료!")
