#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Build 1-Year Price Data - Direct API Version
=============================================
FinanceDataReader 직접 호출로 1년치 주가 데이터 구축

Features:
- DB의 stock_info 테이블에서 종목코드 조회
- FinanceDataReader 직접 호출 (래퍼 우회)
- SQLite에 직접 저장
- 진행상황 표시 및 에러 로깅
"""

import pandas as pd
import sqlite3
import FinanceDataReader as fdr
from datetime import datetime, timedelta
from pathlib import Path
import time


class DataBuilderDirect:
    """직접 API 호출로 데이터 구축"""
    
    def __init__(self, db_path: str = './data/pivot_strategy.db'):
        self.db_path = db_path
        self.conn = sqlite3.connect(db_path)
        
        # 날짜 설정 (1년치)
        self.end_date = datetime.now().strftime('%Y-%m-%d')
        self.start_date = (datetime.now() - timedelta(days=365)).strftime('%Y-%m-%d')
        
        print(f"📅 데이터 수집 기간: {self.start_date} ~ {self.end_date}")
        
        # 통계
        self.stats = {
            'total': 0,
            'success': 0,
            'failed': 0,
            'skipped': 0,
            'api_calls': 0
        }
    
    def get_stock_list(self, market: str = 'ALL'):
        """DB에서 종목 리스트 조회"""
        cursor = self.conn.cursor()
        
        if market == 'ALL':
            cursor.execute('SELECT symbol, name, market FROM stock_info ORDER BY symbol')
        else:
            cursor.execute(
                'SELECT symbol, name, market FROM stock_info WHERE market = ? ORDER BY symbol',
                (market,)
            )
        
        return cursor.fetchall()
    
    def check_existing_data(self, symbol: str, min_days: int = 200) -> bool:
        """이미 충분한 데이터가 있는지 확인"""
        cursor = self.conn.cursor()
        cursor.execute('''
            SELECT COUNT(*) FROM stock_prices 
            WHERE symbol = ? AND date >= ? AND date <= ?
        ''', (symbol, self.start_date, self.end_date))
        
        count = cursor.fetchone()[0]
        return count >= min_days
    
    def save_to_db(self, symbol: str, df: pd.DataFrame):
        """데이터프레임을 DB에 저장 (INSERT OR REPLACE)"""
        if df.empty:
            return False
        
        # 컬럼명 표준화
        df = df.copy()
        df.columns = [c.lower() for c in df.columns]
        
        # 인덱스가 날짜인 경우 처리
        if df.index.name == 'date' or isinstance(df.index, pd.DatetimeIndex):
            df = df.reset_index()
        
        # 필요한 컬럼만 선택
        required_cols = ['date', 'open', 'high', 'low', 'close', 'volume']
        
        # 컬럼명 매핑 (대소문자 처리)
        col_map = {}
        for col in df.columns:
            col_lower = col.lower()
            if col_lower in ['date', 'datetime']:
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
        
        # date 컬럼 문자열로 변환
        if 'date' in df.columns:
            df['date'] = pd.to_datetime(df['date']).dt.strftime('%Y-%m-%d')
        
        # 심볼 추가
        df['symbol'] = symbol
        
        # 필요 컬럼만 선택
        for col in required_cols:
            if col not in df.columns:
                print(f"  ⚠️ 누락된 컬럼: {col}")
                return False
        
        df = df[['symbol', 'date'] + required_cols[1:]]
        
        # INSERT OR REPLACE로 저장 (중복 시 업데이트)
        try:
            cursor = self.conn.cursor()
            for _, row in df.iterrows():
                cursor.execute('''
                    INSERT OR REPLACE INTO stock_prices 
                    (symbol, date, open, high, low, close, volume)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                ''', (
                    row['symbol'], row['date'], row['open'], row['high'],
                    row['low'], row['close'], int(row['volume'])
                ))
            self.conn.commit()
            return True
        except Exception as e:
            print(f"  ⚠️ DB 저장 오류: {e}")
            return False
    
    def fetch_single(self, symbol: str, retries: int = 3, delay: float = 0.5):
        """단일 종목 데이터 가져오기"""
        for attempt in range(retries):
            try:
                df = fdr.DataReader(symbol, self.start_date, self.end_date)
                
                if df.empty:
                    return None, "empty"
                
                self.stats['api_calls'] += 1
                return df, "success"
                
            except Exception as e:
                if attempt < retries - 1:
                    time.sleep(delay * (attempt + 1))
                else:
                    return None, str(e)
        
        return None, "failed"
    
    def build_all(self, market: str = 'ALL', skip_existing: bool = True):
        """전 종목 데이터 구축"""
        stocks = self.get_stock_list(market)
        self.stats['total'] = len(stocks)
        
        print(f"\n🔍 총 {len(stocks)}개 종목 데이터 구축 시작...")
        print("=" * 60)
        
        for i, (symbol, name, mkt) in enumerate(stocks, 1):
            print(f"\n[{i}/{len(stocks)}] {symbol} - {name} ({mkt})")
            
            # 기존 데이터 확인
            if skip_existing and self.check_existing_data(symbol):
                print(f"  ⏭️  캐시됨 (스킵)")
                self.stats['skipped'] += 1
                continue
            
            # 데이터 가져오기
            df, status = self.fetch_single(symbol)
            
            if status == "success" and df is not None:
                # DB 저장
                if self.save_to_db(symbol, df):
                    print(f"  ✅ 성공 ({len(df)}일)")
                    self.stats['success'] += 1
                else:
                    print(f"  ❌ DB 저장 실패")
                    self.stats['failed'] += 1
            elif status == "empty":
                print(f"  ⚠️ 데이터 없음")
                self.stats['failed'] += 1
            else:
                print(f"  ❌ API 실패: {status}")
                self.stats['failed'] += 1
            
            # 진행상황 출력 (10개마다)
            if i % 10 == 0:
                self.print_progress()
            
            # API 부하 방지
            time.sleep(0.15)
        
        print("\n" + "=" * 60)
        print("✅ 데이터 구축 완료!")
        self.print_stats()
    
    def build_missing_only(self, market: str = 'ALL'):
        """부족한 데이터만 보충"""
        stocks = self.get_stock_list(market)
        
        # 부족한 종목만 필터링
        missing_stocks = []
        for symbol, name, mkt in stocks:
            if not self.check_existing_data(symbol):
                missing_stocks.append((symbol, name, mkt))
        
        print(f"\n🔍 캐시 부족 종목: {len(missing_stocks)}개 / 전체 {len(stocks)}개")
        
        if not missing_stocks:
            print("✅ 모든 종목에 충분한 데이터가 있습니다!")
            return
        
        self.stats['total'] = len(missing_stocks)
        
        for i, (symbol, name, mkt) in enumerate(missing_stocks, 1):
            print(f"\n[{i}/{len(missing_stocks)}] {symbol} - {name}")
            
            df, status = self.fetch_single(symbol)
            
            if status == "success" and df is not None:
                if self.save_to_db(symbol, df):
                    print(f"  ✅ 성공 ({len(df)}일)")
                    self.stats['success'] += 1
                else:
                    print(f"  ❌ DB 저장 실패")
                    self.stats['failed'] += 1
            else:
                print(f"  ❌ 실패: {status}")
                self.stats['failed'] += 1
            
            if i % 10 == 0:
                self.print_progress()
            
            time.sleep(0.15)
        
        print("\n" + "=" * 60)
        print("✅ 보충 완료!")
        self.print_stats()
    
    def print_progress(self):
        """진행상황 출력"""
        total = self.stats['total']
        processed = self.stats['success'] + self.stats['failed'] + self.stats['skipped']
        pct = (processed / total * 100) if total > 0 else 0
        
        print(f"\n📊 진행: {processed}/{total} ({pct:.1f}%)")
        print(f"   ✅ 성공: {self.stats['success']} | ⏭️  스킵: {self.stats['skipped']} | ❌ 실패: {self.stats['failed']}")
    
    def print_stats(self):
        """최종 통계 출력"""
        print("\n📈 최종 통계")
        print("-" * 40)
        print(f"  총 종목: {self.stats['total']}")
        print(f"  ✅ 성공: {self.stats['success']}")
        print(f"  ⏭️  스킵: {self.stats['skipped']}")
        print(f"  ❌ 실패: {self.stats['failed']}")
        print(f"  🌐 API 호출: {self.stats['api_calls']}")
        
        success_rate = (self.stats['success'] / self.stats['total'] * 100) if self.stats['total'] > 0 else 0
        print(f"  📉 성공률: {success_rate:.1f}%")
    
    def verify_data(self, sample_size: int = 10):
        """데이터 검증"""
        print("\n🔍 데이터 검증 (샘플링)")
        print("=" * 60)
        
        cursor = self.conn.cursor()
        cursor.execute('SELECT symbol, name FROM stock_info ORDER BY RANDOM() LIMIT ?', (sample_size,))
        samples = cursor.fetchall()
        
        for symbol, name in samples:
            cursor.execute('''
                SELECT COUNT(*), MIN(date), MAX(date) 
                FROM stock_prices 
                WHERE symbol = ? AND date >= ? AND date <= ?
            ''', (symbol, self.start_date, self.end_date))
            
            count, start, end = cursor.fetchone()
            
            if count == 0:
                print(f"  ❌ {symbol} ({name}): 데이터 없음")
            elif count < 200:
                print(f"  ⚠️  {symbol} ({name}): {count}일 ({start} ~ {end}) - 부족")
            else:
                print(f"  ✅ {symbol} ({name}): {count}일 ({start} ~ {end})")
    
    def close(self):
        """DB 연결 종료"""
        self.conn.close()


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='1년치 주가 데이터 구축 (직접 API)')
    parser.add_argument('--market', default='ALL', choices=['ALL', 'KOSPI', 'KOSDAQ'])
    parser.add_argument('--mode', default='missing', choices=['all', 'missing'])
    parser.add_argument('--verify', action='store_true')
    
    args = parser.parse_args()
    
    print("🚀 1년치 주가 데이터 구축 시작 (직접 API)")
    print("=" * 60)
    
    builder = DataBuilderDirect()
    
    try:
        if args.mode == 'all':
            builder.build_all(market=args.market, skip_existing=True)
        else:
            builder.build_missing_only(market=args.market)
        
        if args.verify:
            builder.verify_data()
    finally:
        builder.close()
    
    print("\n✅ 완료!")
