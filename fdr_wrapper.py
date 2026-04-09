#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
FinanceDataReader Wrapper with Local Database Caching
======================================================
스캐너와 통합된 주가 데이터 래퍼
- level1_prices.db 사용 (스캐너와 동일 DB)

Usage:
    from fdr_wrapper import get_price
    
    df = get_price('005930', start_date='2024-01-01', end_date='2024-12-31')
"""

import pandas as pd
import sqlite3
import FinanceDataReader as fdr_module
from datetime import datetime, timedelta
from typing import Optional, List, Dict
from pathlib import Path

DB_PATH = './data/level1_prices.db'


def get_price(symbol: str, start_date: str = None, end_date: str = None, 
              days: int = None) -> Optional[pd.DataFrame]:
    """
    주가 데이터 조회 (level1_prices.db 우선, 없으면 API 호출)
    
    Parameters:
    -----------
    symbol : str
        종목코드 (예: '005930')
    start_date : str
        시작일 (YYYY-MM-DD)
    end_date : str
        종료일 (YYYY-MM-DD)
    days : int
        최근 N일 조회 (start_date/end_date 대체)
    
    Returns:
    --------
    pd.DataFrame : 주가 데이터 (Open, High, Low, Close, Volume)
    """
    # 날짜 설정
    if end_date is None:
        end_date = datetime.now().strftime('%Y-%m-%d')
    
    if start_date is None:
        if days:
            start_date = (datetime.strptime(end_date, '%Y-%m-%d') - timedelta(days=days)).strftime('%Y-%m-%d')
        else:
            start_date = (datetime.strptime(end_date, '%Y-%m-%d') - timedelta(days=365)).strftime('%Y-%m-%d')
    
    # 1. DB에서 먼저 조회
    df = _get_from_db(symbol, start_date, end_date)
    
    if df is not None and len(df) >= 10:
        return df
    
    # 2. DB에 없으면 API 호출
    try:
        df = fdr_module.DataReader(symbol, start=start_date, end=end_date)
        if df is not None and not df.empty:
            # 컬럼명 표준화
            df = df.rename(columns={
                'Open': 'Open',
                'High': 'High',
                'Low': 'Low',
                'Close': 'Close',
                'Volume': 'Volume'
            })
            return df
    except Exception as e:
        print(f"⚠️ API 호출 실패 ({symbol}): {e}")
    
    return df


def _get_from_db(symbol: str, start_date: str, end_date: str) -> Optional[pd.DataFrame]:
    """DB에서 데이터 조회"""
    try:
        if not Path(DB_PATH).exists():
            return None
            
        conn = sqlite3.connect(DB_PATH)
        
        query = '''
            SELECT date, open as Open, high as High, low as Low, 
                   close as Close, volume as Volume
            FROM price_data 
            WHERE code = ? AND date >= ? AND date <= ?
            ORDER BY date
        '''
        
        df = pd.read_sql_query(query, conn, params=(symbol, start_date, end_date))
        conn.close()
        
        if not df.empty:
            df['date'] = pd.to_datetime(df['date'])
            df.set_index('date', inplace=True)
            return df
            
    except Exception as e:
        print(f"⚠️ DB 조회 오류: {e}")
    
    return None


def save_to_db(symbol: str, name: str, df: pd.DataFrame):
    """DB에 데이터 저장"""
    if df is None or df.empty:
        return
    
    try:
        Path(DB_PATH).parent.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        # 테이블 생성
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS price_data (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                code TEXT NOT NULL,
                name TEXT,
                date TEXT NOT NULL,
                open REAL,
                high REAL,
                low REAL,
                close REAL,
                volume INTEGER,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(code, date)
            )
        ''')
        
        # 데이터 삽입
        for idx, row in df.iterrows():
            date_str = idx.strftime('%Y-%m-%d') if hasattr(idx, 'strftime') else str(idx)[:10]
            
            cursor.execute('''
                INSERT OR REPLACE INTO price_data 
                (code, name, date, open, high, low, close, volume, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, datetime('now'))
            ''', (
                symbol, name, date_str,
                float(row.get('Open', row.get('open', 0))),
                float(row.get('High', row.get('high', 0))),
                float(row.get('Low', row.get('low', 0))),
                float(row.get('Close', row.get('close', 0))),
                int(row.get('Volume', row.get('volume', 0)))
            ))
        
        conn.commit()
        conn.close()
        
    except Exception as e:
        print(f"⚠️ DB 저장 오류 ({symbol}): {e}")


# 하위 호환성을 위한 클래스
class FDRWrapper:
    """하위 호환성용 래퍼 클래스"""
    
    def __init__(self, db_path: str = None):
        self.db_path = db_path or DB_PATH
    
    def get_price(self, symbol: str, start_date: str = None, end_date: str = None) -> pd.DataFrame:
        return get_price(symbol, start_date, end_date)


if __name__ == '__main__':
    # 테스트
    print("fdr_wrapper 테스트")
    df = get_price('005930', days=30)
    if df is not None:
        print(f"✅ 삼성전자 데이터: {len(df)}일")
        print(df.tail())
    else:
        print("❌ 데이터 없음")
