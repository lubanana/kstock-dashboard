#!/usr/bin/env python3
"""
Stock Database Manager
======================
한국주식 종목정보 & 공시 데이터 통합 관리 시스템

기능:
1. KRX 종목정보 업데이트
2. DART 공시 종목 매핑
3. 코드 변환 (KRX ↔ DART)
4. 주기적 동기화
"""

import sqlite3
import pandas as pd
import FinanceDataReader as fdr
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
import logging
import os

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class StockDatabaseManager:
    """종목 데이터베이스 통합 관리자"""
    
    def __init__(self):
        self.level1_db = 'data/level1_prices.db'
        self.pivot_db = 'data/pivot_strategy.db'
        self.dart_cache = 'data/dart_cache.db'
        
        self._init_databases()
    
    def _init_databases(self):
        """데이터베이스 초기화"""
        # level1_prices.db
        conn1 = sqlite3.connect(self.level1_db)
        cursor1 = conn1.cursor()
        cursor1.execute('''
            CREATE TABLE IF NOT EXISTS stock_info (
                code TEXT PRIMARY KEY,
                name TEXT,
                market TEXT,
                sector TEXT,
                industry TEXT,
                listing_date TEXT,
                updated_at TEXT
            )
        ''')
        conn1.commit()
        conn1.close()
        
        # pivot_strategy.db
        conn2 = sqlite3.connect(self.pivot_db)
        cursor2 = conn2.cursor()
        
        # 종목 기본정보
        cursor2.execute('''
            CREATE TABLE IF NOT EXISTS stock_info (
                symbol TEXT PRIMARY KEY,
                name TEXT,
                market TEXT,
                sector TEXT,
                industry TEXT,
                updated_at TEXT
            )
        ''')
        
        # 코드 매핑
        cursor2.execute('''
            CREATE TABLE IF NOT EXISTS stock_code_mapping (
                krx_code TEXT PRIMARY KEY,
                dart_code TEXT,
                naver_code TEXT,
                name TEXT,
                code_type TEXT DEFAULT 'normal',
                created_at TEXT,
                updated_at TEXT
            )
        ''')
        
        # 매핑 로그
        cursor2.execute('''
            CREATE TABLE IF NOT EXISTS mapping_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                action TEXT,
                krx_code TEXT,
                dart_code TEXT,
                message TEXT,
                created_at TEXT
            )
        ''')
        
        conn2.commit()
        conn2.close()
        logger.info("Database initialization completed")
    
    def update_krx_stock_list(self) -> pd.DataFrame:
        """KRX 종목 목록 업데이트"""
        logger.info("Fetching KRX stock list from FinanceDataReader...")
        
        try:
            # KOSPI
            kospi = fdr.StockListing('KOSPI')
            kospi['market'] = 'KOSPI'
            
            # KOSDAQ
            kosdaq = fdr.StockListing('KOSDAQ')
            kosdaq['market'] = 'KOSDAQ'
            
            # 병합
            all_stocks = pd.concat([kospi, kosdaq], ignore_index=True)
            all_stocks['updated_at'] = datetime.now().isoformat()
            
            # 필요한 컬럼만 선택
            if 'Sector' in all_stocks.columns:
                all_stocks = all_stocks.rename(columns={'Sector': 'sector'})
            if 'Industry' in all_stocks.columns:
                all_stocks = all_stocks.rename(columns={'Industry': 'industry'})
            
            # 컬럼 매핑
            column_map = {
                'Code': 'code',
                'Name': 'name',
                'ListingDate': 'listing_date'
            }
            all_stocks = all_stocks.rename(columns=column_map)
            
            logger.info(f"Fetched {len(all_stocks)} stocks from KRX")
            return all_stocks
            
        except Exception as e:
            logger.error(f"Failed to fetch KRX list: {e}")
            return pd.DataFrame()
    
    def update_level1_stock_info(self, stocks_df: pd.DataFrame):
        """level1_prices.db 종목정보 업데이트"""
        if stocks_df.empty:
            return
        
        conn = sqlite3.connect(self.level1_db)
        
        # 필요한 컬럼 선택
        required_cols = ['code', 'name', 'market', 'sector', 'industry', 'listing_date', 'updated_at']
        for col in required_cols:
            if col not in stocks_df.columns:
                stocks_df[col] = None
        
        stocks_df = stocks_df[required_cols]
        
        # UPSERT
        cursor = conn.cursor()
        for _, row in stocks_df.iterrows():
            cursor.execute('''
                INSERT INTO stock_info (code, name, market, sector, industry, listing_date, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(code) DO UPDATE SET
                    name=excluded.name,
                    market=excluded.market,
                    sector=excluded.sector,
                    industry=excluded.industry,
                    listing_date=excluded.listing_date,
                    updated_at=excluded.updated_at
            ''', (row['code'], row['name'], row['market'], row['sector'], 
                  row['industry'], row['listing_date'], row['updated_at']))
        
        conn.commit()
        conn.close()
        logger.info(f"Updated {len(stocks_df)} stocks in level1_prices.db")
    
    def update_pivot_stock_info(self, stocks_df: pd.DataFrame):
        """pivot_strategy.db 종목정보 업데이트"""
        if stocks_df.empty:
            return
        
        conn = sqlite3.connect(self.pivot_db)
        
        # 컬럼 매핑
        df = stocks_df.copy()
        if 'code' in df.columns:
            df = df.rename(columns={'code': 'symbol'})
        
        required_cols = ['symbol', 'name', 'market', 'sector', 'industry', 'updated_at']
        for col in required_cols:
            if col not in df.columns:
                df[col] = None
        
        df = df[required_cols]
        
        # UPSERT
        cursor = conn.cursor()
        for _, row in df.iterrows():
            cursor.execute('''
                INSERT INTO stock_info (symbol, name, market, sector, industry, updated_at)
                VALUES (?, ?, ?, ?, ?, ?)
                ON CONFLICT(symbol) DO UPDATE SET
                    name=excluded.name,
                    market=excluded.market,
                    sector=excluded.sector,
                    industry=excluded.industry,
                    updated_at=excluded.updated_at
            ''', (row['symbol'], row['name'], row['market'], row['sector'],
                  row['industry'], row['updated_at']))
        
        conn.commit()
        conn.close()
        logger.info(f"Updated {len(df)} stocks in pivot_strategy.db")
    
    def update_code_mapping(self, stocks_df: pd.DataFrame):
        """종목 코드 매핑 업데이트"""
        if stocks_df.empty:
            return
        
        conn = sqlite3.connect(self.pivot_db)
        cursor = conn.cursor()
        
        now = datetime.now().isoformat()
        updated = 0
        inserted = 0
        
        for _, row in stocks_df.iterrows():
            krx_code = row.get('code') or row.get('symbol')
            name = row.get('name')
            
            # DART 코드는 일반적으로 KRX 코드와 동일
            # 단, ETF/ETN/선물 등은 다를 수 있음
            dart_code = krx_code
            naver_code = krx_code
            
            # 코드 타입 판별
            code_type = self._detect_code_type(krx_code, name)
            
            # 매핑 업데이트
            cursor.execute('''
                SELECT krx_code FROM stock_code_mapping WHERE krx_code = ?
            ''', (krx_code,))
            
            if cursor.fetchone():
                try:
                    cursor.execute('''
                        UPDATE stock_code_mapping
                        SET dart_code = ?, naver_code = ?, name = ?, code_type = ?, updated_at = ?
                        WHERE krx_code = ?
                    ''', (dart_code, naver_code, name, code_type, now, krx_code))
                except sqlite3.OperationalError:
                    cursor.execute('''
                        UPDATE stock_code_mapping
                        SET dart_code = ?, naver_code = ?, name = ?, code_type = ?
                        WHERE krx_code = ?
                    ''', (dart_code, naver_code, name, code_type, krx_code))
                updated += 1
            else:
                try:
                    cursor.execute('''
                        INSERT INTO stock_code_mapping (krx_code, dart_code, naver_code, name, code_type, created_at, updated_at)
                        VALUES (?, ?, ?, ?, ?, ?, ?)
                    ''', (krx_code, dart_code, naver_code, name, code_type, now, now))
                except sqlite3.OperationalError:
                    cursor.execute('''
                        INSERT OR REPLACE INTO stock_code_mapping (krx_code, dart_code, naver_code, name, code_type)
                        VALUES (?, ?, ?, ?, ?)
                    ''', (krx_code, dart_code, naver_code, name, code_type))
                inserted += 1
        
        conn.commit()
        conn.close()
        logger.info(f"Code mapping: {inserted} inserted, {updated} updated")
    
    def _detect_code_type(self, code: str, name: str) -> str:
        """종목 타입 감지"""
        name = str(name) if name else ''
        
        # ETF/ETN
        if any(x in name for x in ['ETF', 'ETN', 'TIGER', 'KODEX', 'KBSTAR', 'SOL', 'ARIRANG', 'HANARO', 'KOSEF']):
            return 'etf'
        
        # 선물/옵션
        if any(x in name for x in ['선물', '옵션', 'Futures', 'Options']):
            return 'futures'
        
        # ETF는 코드 패턴으로도 확인
        if code.startswith('5') or code.startswith('4') or code.startswith('2'):
            if any(x in name for x in ['ETF', '인덱스', '레버리지', '인버스']):
                return 'etf'
        
        # 우선주
        if '우' in name or name.endswith('(우)'):
            return 'preferred'
        
        # 스팩
        if '스팩' in name or 'SPAC' in name:
            return 'spac'
        
        return 'normal'
    
    def get_dart_corp_codes(self) -> pd.DataFrame:
        """DART 기업 코드 가져오기"""
        conn = sqlite3.connect(self.pivot_db)
        
        try:
            df = pd.read_sql('''
                SELECT DISTINCT corp_code, stock_code, corp_name
                FROM dart_disclosures
                WHERE stock_code IS NOT NULL AND stock_code != ''
            ''', conn)
            
            logger.info(f"Found {len(df)} DART corp codes with stock mapping")
            return df
            
        except Exception as e:
            logger.error(f"Failed to get DART codes: {e}")
            return pd.DataFrame()
        finally:
            conn.close()
    
    def verify_code_mapping(self) -> Dict:
        """코드 매핑 검증"""
        conn = sqlite3.connect(self.pivot_db)
        
        results = {}
        
        # 총 매핑 수
        df = pd.read_sql('SELECT COUNT(*) as cnt FROM stock_code_mapping', conn)
        results['total_mapping'] = df['cnt'].iloc[0]
        
        # 타입별 분포
        df = pd.read_sql('''
            SELECT code_type, COUNT(*) as cnt
            FROM stock_code_mapping
            GROUP BY code_type
        ''', conn)
        results['type_distribution'] = df.set_index('code_type')['cnt'].to_dict()
        
        # DART 매핑 확인
        df = pd.read_sql('''
            SELECT COUNT(*) as cnt
            FROM stock_code_mapping scm
            JOIN dart_disclosures dd ON scm.krx_code = dd.stock_code
        ''', conn)
        results['dart_linked'] = df['cnt'].iloc[0]
        
        conn.close()
        
        return results
    
    def sync_databases(self):
        """전체 데이터베이스 동기화"""
        logger.info("=" * 60)
        logger.info("Starting database synchronization...")
        logger.info("=" * 60)
        
        # 1. KRX 종목 목록 가져오기
        stocks_df = self.update_krx_stock_list()
        
        if stocks_df.empty:
            logger.error("Failed to fetch stock list")
            return False
        
        # 2. 각 DB 업데이트
        self.update_level1_stock_info(stocks_df)
        self.update_pivot_stock_info(stocks_df)
        self.update_code_mapping(stocks_df)
        
        # 3. 검증
        verify = self.verify_code_mapping()
        logger.info("\n" + "=" * 60)
        logger.info("Verification Results:")
        logger.info(f"  Total mappings: {verify['total_mapping']}")
        logger.info(f"  Type distribution: {verify['type_distribution']}")
        logger.info(f"  DART linked: {verify['dart_linked']}")
        logger.info("=" * 60)
        
        return True
    
    def get_stock_info(self, code: str = None, name: str = None) -> Optional[Dict]:
        """종목 정보 조회"""
        conn = sqlite3.connect(self.pivot_db)
        
        try:
            if code:
                df = pd.read_sql('''
                    SELECT scm.*, si.sector, si.industry
                    FROM stock_code_mapping scm
                    LEFT JOIN stock_info si ON scm.krx_code = si.symbol
                    WHERE scm.krx_code = ?
                ''', conn, params=(code,))
            elif name:
                df = pd.read_sql('''
                    SELECT scm.*, si.sector, si.industry
                    FROM stock_code_mapping scm
                    LEFT JOIN stock_info si ON scm.krx_code = si.symbol
                    WHERE scm.name LIKE ?
                ''', conn, params=(f'%{name}%',))
            else:
                return None
            
            if df.empty:
                return None
            
            return df.iloc[0].to_dict()
            
        finally:
            conn.close()
    
    def convert_code(self, code: str, from_type: str, to_type: str) -> Optional[str]:
        """코드 변환"""
        conn = sqlite3.connect(self.pivot_db)
        
        try:
            cursor = conn.cursor()
            
            type_map = {
                'krx': 'krx_code',
                'dart': 'dart_code',
                'naver': 'naver_code'
            }
            
            from_col = type_map.get(from_type)
            to_col = type_map.get(to_type)
            
            if not from_col or not to_col:
                return None
            
            cursor.execute(f'''
                SELECT {to_col} FROM stock_code_mapping WHERE {from_col} = ?
            ''', (code,))
            
            result = cursor.fetchone()
            return result[0] if result else None
            
        finally:
            conn.close()


def main():
    """메인 실행"""
    manager = StockDatabaseManager()
    
    # 전체 동기화
    success = manager.sync_databases()
    
    if success:
        print("\n✅ Database synchronization completed successfully!")
        
        # 샘플 조회
        print("\n📊 Sample stock info:")
        info = manager.get_stock_info(code='005930')
        if info:
            print(f"  삼성전자: {info}")
    else:
        print("\n❌ Database synchronization failed!")


if __name__ == '__main__':
    main()
