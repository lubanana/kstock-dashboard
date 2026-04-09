#!/usr/bin/env python3
"""
통합 데이터 구축 시스템 (Unified Data Builder)
================================================
모든 스캐너가 사용하는 level1_prices.db 중심의 통합 데이터 관리

주요 기능:
1. 일일 가격 데이터 자동 수집 (KRX + FinanceDataReader)
2. 기술적 지표 자동 계산 (MA, RSI, MACD, 볼린저밴드)
3. 누락 데이터 백필
4. 데이터 품질 검증

Usage:
    python3 unified_data_builder.py --mode daily        # 일일 업데이트
    python3 unified_data_builder.py --mode backfill --days 30  # 백필
    python3 unified_data_builder.py --mode verify       # 품질 검증
    python3 unified_data_builder.py --mode full         # 전체 재구축
"""

import sys
sys.path.insert(0, '.')

import sqlite3
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Tuple
import argparse
import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
import time
import FinanceDataReader as fdr

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('data_builder.log')
    ]
)
logger = logging.getLogger(__name__)

DB_PATH = 'data/level1_prices.db'
BATCH_SIZE = 100  # 병렬 처리 배치 크기
MAX_WORKERS = 8   # 병렬 worker 수


class UnifiedDataBuilder:
    """통합 데이터 구축 엔진"""
    
    def __init__(self):
        self.conn = None
        self._connect_db()
        self._ensure_tables()
    
    def _connect_db(self):
        """DB 연결"""
        import os
        os.makedirs('data', exist_ok=True)
        self.conn = sqlite3.connect(DB_PATH, check_same_thread=False)
        self.conn.execute('PRAGMA journal_mode=WAL')
        logger.info(f"DB 연결: {DB_PATH}")
    
    def _ensure_tables(self):
        """필수 테이블 생성"""
        # 가격 데이터 테이블
        self.conn.execute('''
            CREATE TABLE IF NOT EXISTS price_data (
                date TEXT,
                code TEXT,
                name TEXT,
                open REAL,
                high REAL,
                low REAL,
                close REAL,
                volume INTEGER,
                change_pct REAL,
                ma5 REAL,
                ma20 REAL,
                ma60 REAL,
                rsi REAL,
                macd REAL,
                macd_signal REAL,
                bb_upper REAL,
                bb_lower REAL,
                PRIMARY KEY (date, code)
            )
        ''')
        
        # 종목 정보 테이블
        self.conn.execute('''
            CREATE TABLE IF NOT EXISTS stock_info (
                code TEXT PRIMARY KEY,
                name TEXT,
                market TEXT,
                sector TEXT,
                last_updated TEXT
            )
        ''')
        
        # 데이터 구축 로그
        self.conn.execute('''
            CREATE TABLE IF NOT EXISTS build_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT,
                mode TEXT,
                records_processed INTEGER,
                records_inserted INTEGER,
                errors INTEGER,
                duration_seconds REAL
            )
        ''')
        
        self.conn.commit()
        logger.info("테이블 확인 완료")
    
    def get_stock_list(self) -> pd.DataFrame:
        """KRX 종목 리스트 조회"""
        try:
            stocks = fdr.StockListing('KOSPI')
            kosdaq = fdr.StockListing('KOSDAQ')
            
            if kosdaq is not None and not kosdaq.empty:
                stocks = pd.concat([stocks, kosdaq], ignore_index=True)
            
            # 컬럼명 통일
            if 'Code' in stocks.columns:
                stocks = stocks.rename(columns={'Code': 'code', 'Name': 'name'})
            
            logger.info(f"종목 리스트 로드: {len(stocks)}개")
            return stocks[['code', 'name']].drop_duplicates()
        except Exception as e:
            logger.error(f"종목 리스트 로드 실패: {e}")
            return pd.DataFrame(columns=['code', 'name'])
    
    def fetch_stock_data(self, code: str, name: str, days: int = 100) -> Optional[pd.DataFrame]:
        """개별 종목 데이터 수집"""
        try:
            end_date = datetime.now()
            start_date = end_date - timedelta(days=days + 30)  # 버퍼 추가
            
            df = fdr.DataReader(code, start=start_date.strftime('%Y-%m-%d'))
            
            if df is None or df.empty:
                return None
            
            # 최근 N일만 필터
            df = df.tail(days)
            
            # 컬럼명 통일
            df = df.rename(columns={
                'Open': 'open',
                'High': 'high',
                'Low': 'low',
                'Close': 'close',
                'Volume': 'volume',
                'Change': 'change_pct'
            })
            
            df['code'] = code
            df['name'] = name
            df.index.name = 'date'
            df = df.reset_index()
            
            return df
        except Exception as e:
            logger.warning(f"{code} 데이터 수집 실패: {e}")
            return None
    
    def calculate_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        """기술적 지표 계산"""
        if df.empty or len(df) < 20:
            return df
        
        # 이동평균
        df['ma5'] = df['close'].rolling(5).mean()
        df['ma20'] = df['close'].rolling(20).mean()
        df['ma60'] = df['close'].rolling(60).mean()
        
        # RSI
        delta = df['close'].diff()
        gain = delta.where(delta > 0, 0)
        loss = -delta.where(delta < 0, 0)
        avg_gain = gain.rolling(14).mean()
        avg_loss = loss.rolling(14).mean()
        rs = avg_gain / avg_loss.replace(0, np.nan)
        df['rsi'] = 100 - (100 / (1 + rs))
        df['rsi'] = df['rsi'].fillna(50)
        
        # MACD
        exp1 = df['close'].ewm(span=12, adjust=False).mean()
        exp2 = df['close'].ewm(span=26, adjust=False).mean()
        df['macd'] = exp1 - exp2
        df['macd_signal'] = df['macd'].ewm(span=9, adjust=False).mean()
        
        # 볼린저 밴드
        df['bb_upper'] = df['ma20'] + (df['close'].rolling(20).std() * 2)
        df['bb_lower'] = df['ma20'] - (df['close'].rolling(20).std() * 2)
        
        return df
    
    def insert_data(self, df: pd.DataFrame) -> int:
        """데이터 삽입"""
        if df.empty:
            return 0
        
        try:
            # 필요한 컬럼만 선택
            columns = ['date', 'code', 'name', 'open', 'high', 'low', 'close', 
                      'volume', 'change_pct', 'ma5', 'ma20', 'ma60', 'rsi',
                      'macd', 'macd_signal', 'bb_upper', 'bb_lower']
            
            df_insert = df[columns].copy()
            df_insert['date'] = pd.to_datetime(df_insert['date']).dt.strftime('%Y-%m-%d')
            
            # NaN 처리
            df_insert = df_insert.replace([np.inf, -np.inf], np.nan)
            df_insert = df_insert.where(pd.notnull(df_insert), None)
            
            # UPSERT 수행
            records = df_insert.to_records(index=False).tolist()
            
            self.conn.executemany('''
                INSERT OR REPLACE INTO price_data 
                (date, code, name, open, high, low, close, volume, change_pct,
                 ma5, ma20, ma60, rsi, macd, macd_signal, bb_upper, bb_lower)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', records)
            
            self.conn.commit()
            return len(records)
        except Exception as e:
            logger.error(f"데이터 삽입 실패: {e}")
            return 0
    
    def update_stock_info(self, stocks_df: pd.DataFrame):
        """종목 정보 업데이트"""
        try:
            for _, row in stocks_df.iterrows():
                self.conn.execute('''
                    INSERT OR REPLACE INTO stock_info (code, name, last_updated)
                    VALUES (?, ?, ?)
                ''', (row['code'], row['name'], datetime.now().isoformat()))
            self.conn.commit()
            logger.info(f"종목 정보 업데이트: {len(stocks_df)}개")
        except Exception as e:
            logger.error(f"종목 정보 업데이트 실패: {e}")
    
    def daily_update(self, days: int = 5):
        """일일 업데이트"""
        logger.info(f"일일 업데이트 시작 (최근 {days}일)")
        start_time = time.time()
        
        # 종목 리스트 로드
        stocks = self.get_stock_list()
        if stocks.empty:
            logger.error("종목 리스트를 가져올 수 없음")
            return
        
        # 이미 최신 데이터가 있는 종목 확인
        cursor = self.conn.execute('''
            SELECT DISTINCT code FROM price_data 
            WHERE date >= date('now', '-1 day')
        ''')
        existing_codes = {r[0] for r in cursor.fetchall()}
        
        # 업데이트 필요한 종목만 필터
        stocks_to_update = stocks[~stocks['code'].isin(existing_codes)]
        logger.info(f"업데이트 필요 종목: {len(stocks_to_update)}개 (이미 최신: {len(existing_codes)}개)")
        
        if stocks_to_update.empty:
            logger.info("모든 종목이 최신 상태입니다")
            return
        
        # 병렬 처리
        total_inserted = 0
        errors = 0
        processed = 0
        
        with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
            future_to_stock = {
                executor.submit(self.fetch_stock_data, row['code'], row['name'], days): (row['code'], row['name'])
                for _, row in stocks_to_update.iterrows()
            }
            
            for future in as_completed(future_to_stock):
                code, name = future_to_stock[future]
                processed += 1
                
                try:
                    df = future.result(timeout=30)
                    if df is not None and not df.empty:
                        df = self.calculate_indicators(df)
                        inserted = self.insert_data(df)
                        total_inserted += inserted
                        
                        if processed % 100 == 0:
                            logger.info(f"진행: {processed}/{len(stocks_to_update)} (삽입: {total_inserted}건)")
                except Exception as e:
                    errors += 1
                    logger.warning(f"{code} 처리 실패: {e}")
        
        # 종목 정보 업데이트
        self.update_stock_info(stocks)
        
        # 로그 기록
        duration = time.time() - start_time
        self.conn.execute('''
            INSERT INTO build_log (timestamp, mode, records_processed, records_inserted, errors, duration_seconds)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (datetime.now().isoformat(), 'daily', processed, total_inserted, errors, duration))
        self.conn.commit()
        
        logger.info(f"일일 업데이트 완료: 처리 {processed}건, 삽입 {total_inserted}건, 오류 {errors}건, 소요 {duration:.1f}초")
    
    def backfill_missing(self, lookback_days: int = 30):
        """누락 데이터 백필"""
        logger.info(f"누락 데이터 백필 시작 (최근 {lookback_days}일)")
        start_time = time.time()
        
        # 특정 기간 데이터가 없는 종목 확인
        start_date = (datetime.now() - timedelta(days=lookback_days)).strftime('%Y-%m-%d')
        
        cursor = self.conn.execute('''
            SELECT code, name FROM stock_info
            WHERE code NOT IN (
                SELECT DISTINCT code FROM price_data WHERE date >= ?
            )
        ''', (start_date,))
        
        missing_stocks = [(r[0], r[1]) for r in cursor.fetchall()]
        logger.info(f"누락 종목: {len(missing_stocks)}개")
        
        if not missing_stocks:
            logger.info("누락된 데이터 없음")
            return
        
        # 백필 실행
        total_inserted = 0
        errors = 0
        
        for i, (code, name) in enumerate(missing_stocks):
            try:
                df = self.fetch_stock_data(code, name, lookback_days + 10)
                if df is not None and not df.empty:
                    df = self.calculate_indicators(df)
                    inserted = self.insert_data(df)
                    total_inserted += inserted
                    
                    if (i + 1) % 50 == 0:
                        logger.info(f"백필 진행: {i+1}/{len(missing_stocks)}")
                
                time.sleep(0.1)  # API 부하 방지
            except Exception as e:
                errors += 1
                logger.warning(f"{code} 백필 실패: {e}")
        
        duration = time.time() - start_time
        logger.info(f"백필 완료: 삽입 {total_inserted}건, 오류 {errors}건, 소요 {duration:.1f}초")
    
    def verify_data_quality(self) -> Dict:
        """데이터 품질 검증"""
        logger.info("데이터 품질 검증 시작")
        
        results = {}
        
        # 1. 총 레코드 수
        cursor = self.conn.execute('SELECT COUNT(*) FROM price_data')
        results['total_records'] = cursor.fetchone()[0]
        
        # 2. 종목 수
        cursor = self.conn.execute('SELECT COUNT(DISTINCT code) FROM price_data')
        results['total_stocks'] = cursor.fetchone()[0]
        
        # 3. 날짜 범위
        cursor = self.conn.execute('SELECT MIN(date), MAX(date) FROM price_data')
        min_date, max_date = cursor.fetchone()
        results['date_range'] = f"{min_date} ~ {max_date}"
        
        # 4. NULL 값 확인
        cursor = self.conn.execute('SELECT COUNT(*) FROM price_data WHERE close IS NULL')
        results['null_close'] = cursor.fetchone()[0]
        
        # 5. 최근 데이터 현황
        cursor = self.conn.execute('''
            SELECT date, COUNT(DISTINCT code) 
            FROM price_data 
            WHERE date >= date('now', '-5 days')
            GROUP BY date ORDER BY date DESC
        ''')
        results['recent_days'] = cursor.fetchall()
        
        # 6. 중복 데이터 확인
        cursor = self.conn.execute('''
            SELECT date, code, COUNT(*) as cnt
            FROM price_data
            GROUP BY date, code
            HAVING cnt > 1
        ''')
        duplicates = cursor.fetchall()
        results['duplicates'] = len(duplicates)
        
        # 결과 출력
        print("\n" + "="*70)
        print("📊 데이터 품질 검증 결과")
        print("="*70)
        print(f"총 레코드: {results['total_records']:,}건")
        print(f"종목 수: {results['total_stocks']:,}개")
        print(f"날짜 범위: {results['date_range']}")
        print(f"NULL 종가: {results['null_close']}건")
        print(f"중복 데이터: {results['duplicates']}건")
        print("\n최근 5일 데이터 현황:")
        for date, count in results['recent_days']:
            status = "✅" if count > 3000 else "⚠️"
            print(f"  {status} {date}: {count:,}종목")
        print("="*70)
        
        return results
    
    def full_rebuild(self):
        """전체 데이터 재구축"""
        logger.warning("전체 재구축 시작 - 기존 데이터 삭제됩니다")
        
        # 백업
        import shutil
        backup_path = f"{DB_PATH}.backup.{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        shutil.copy(DB_PATH, backup_path)
        logger.info(f"백업 생성: {backup_path}")
        
        # 테이블 초기화
        self.conn.execute('DELETE FROM price_data')
        self.conn.commit()
        
        # 전체 재구축
        stocks = self.get_stock_list()
        logger.info(f"전체 재구축: {len(stocks)}개 종목")
        
        total_inserted = 0
        for i, (_, row) in enumerate(stocks.iterrows()):
            try:
                df = self.fetch_stock_data(row['code'], row['name'], 1000)
                if df is not None and not df.empty:
                    df = self.calculate_indicators(df)
                    inserted = self.insert_data(df)
                    total_inserted += inserted
                    
                    if (i + 1) % 100 == 0:
                        logger.info(f"재구축 진행: {i+1}/{len(stocks)} (누적 {total_inserted}건)")
                
                time.sleep(0.05)
            except Exception as e:
                logger.warning(f"{row['code']} 재구축 실패: {e}")
        
        logger.info(f"전체 재구축 완료: 총 {total_inserted}건")
    
    def close(self):
        """DB 연결 종료"""
        if self.conn:
            self.conn.close()
            logger.info("DB 연결 종료")


def main():
    """메인 실행"""
    parser = argparse.ArgumentParser(description='통합 데이터 구축 시스템')
    parser.add_argument('--mode', choices=['daily', 'backfill', 'verify', 'full'],
                       default='daily', help='실행 모드')
    parser.add_argument('--days', type=int, default=5,
                       help='수집 일수 (daily/backfill 모드)')
    
    args = parser.parse_args()
    
    builder = UnifiedDataBuilder()
    
    try:
        if args.mode == 'daily':
            builder.daily_update(args.days)
        elif args.mode == 'backfill':
            builder.backfill_missing(args.days)
        elif args.mode == 'verify':
            builder.verify_data_quality()
        elif args.mode == 'full':
            confirm = input("전체 재구축 시 기존 데이터가 삭제됩니다. 계속하시겠습니까? (yes/no): ")
            if confirm.lower() == 'yes':
                builder.full_rebuild()
            else:
                print("취소되었습니다")
    finally:
        builder.close()


if __name__ == '__main__':
    main()
