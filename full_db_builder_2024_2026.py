#!/usr/bin/env python3
"""
Full DB Builder - 2024~2026 Complete Data Build
===============================================
- 코스피/코스닥 전체 종목 대상
- 2024-01-01 ~ 2026-03-20 기간 데이터 구축
- 공휴일/주말 자동 필터링
- 진행 상황 10분마다 보고
"""

import sqlite3
import pandas as pd
import FinanceDataReader as fdr
from datetime import datetime, timedelta
from typing import List, Set
import time
import sys
import os

# 2024년 ~ 2026년 한국 공휴일 (거래소 휴장일)
KRX_HOLIDAYS = {
    # 2024년
    '2024-01-01', '2024-02-09', '2024-02-12', '2024-03-01', '2024-04-10',
    '2024-05-01', '2024-05-06', '2024-05-15', '2024-06-06', '2024-08-15',
    '2024-09-16', '2024-09-17', '2024-09-18', '2024-10-01', '2024-10-03',
    '2024-10-09', '2024-12-25', '2024-12-31',
    # 2025년
    '2025-01-01', '2025-01-28', '2025-01-29', '2025-01-30', '2025-03-01',
    '2025-03-03', '2025-05-01', '2025-05-05', '2025-05-06', '2025-06-06',
    '2025-08-15', '2025-10-03', '2025-10-06', '2025-10-07', '2025-10-08',
    '2025-10-09', '2025-12-25',
    # 2026년
    '2026-01-01', '2026-02-16', '2026-02-17', '2026-02-18', '2026-03-01',
}

# 버퍼링 없는 출력
sys.stdout = os.fdopen(sys.stdout.fileno(), 'w', buffering=1)


class FullDBBuilder:
    """전체 DB 구축기"""
    
    def __init__(self, db_path: str = './data/pivot_strategy.db'):
        self.db_path = db_path
        self.holidays = KRX_HOLIDAYS
        self.conn = sqlite3.connect(db_path)
        self.conn.row_factory = sqlite3.Row
        
        # 통계
        self.stats = {
            'success': 0,
            'failed': 0,
            'skipped': 0,
            'updated': 0
        }
    
    def is_trading_day(self, date_str: str) -> bool:
        """거래일 여부 확인 (공휴일 + 주말 제외)"""
        if date_str in self.holidays:
            return False
        date = datetime.strptime(date_str, '%Y-%m-%d')
        return date.weekday() < 5  # 0-4: 월-금
    
    def get_all_symbols(self) -> List[str]:
        """전체 종목 리스트 조회 (stock_info 테이블 우선)"""
        cursor = self.conn.cursor()
        
        # stock_info에서 먼저 조회
        try:
            cursor.execute('SELECT DISTINCT symbol FROM stock_info ORDER BY symbol')
            symbols = [row[0] for row in cursor.fetchall()]
            if len(symbols) > 1000:  # 충분한 종목이 있으면 사용
                print(f"stock_info에서 {len(symbols)}개 종목 로드")
                return symbols
        except:
            pass
        
        # 현재 DB에 있는 종목들
        cursor.execute('SELECT DISTINCT symbol FROM stock_prices ORDER BY symbol')
        symbols = [row[0] for row in cursor.fetchall()]
        print(f"stock_prices에서 {len(symbols)}개 종목 로드")
        return symbols
    
    def get_existing_data_range(self, symbol: str) -> tuple:
        """해당 종목의 기존 데이터 기간 조회"""
        cursor = self.conn.cursor()
        cursor.execute('''
            SELECT MIN(date), MAX(date), COUNT(*) 
            FROM stock_prices 
            WHERE symbol = ? AND date >= '2024-01-01'
        ''', (symbol,))
        row = cursor.fetchone()
        return (row[0], row[1], row[2]) if row else (None, None, 0)
    
    def fetch_and_save(self, symbol: str, start_date: str, end_date: str) -> bool:
        """FDR로 데이터 가져와서 저장"""
        try:
            # FDR 데이터 요청
            df = fdr.DataReader(symbol, start_date, end_date)
            
            if df.empty:
                return False
            
            # 데이터 전처리
            df = df.reset_index()
            
            # 컬럼명 확인
            date_col = 'Date' if 'Date' in df.columns else df.columns[0]
            df.rename(columns={date_col: 'date'}, inplace=True)
            
            # 필요한 컬럼만
            col_map = {}
            for col in df.columns:
                col_lower = col.lower()
                if col_lower in ['date', 'open', 'high', 'low', 'close', 'volume']:
                    col_map[col] = col_lower
            
            df = df.rename(columns=col_map)
            required = ['date', 'open', 'high', 'low', 'close', 'volume']
            if not all(c in df.columns for c in required):
                return False
            
            df = df[required]
            
            # 거래량 0인 날짜 필터링 (공휴일 등)
            df = df[df['volume'] > 0]
            
            if df.empty:
                return False
            
            # DB 저장
            cursor = self.conn.cursor()
            inserted = 0
            
            for _, row in df.iterrows():
                try:
                    date_val = row['date']
                    if hasattr(date_val, 'strftime'):
                        date_str = date_val.strftime('%Y-%m-%d')
                    else:
                        date_str = str(date_val)[:10]
                    
                    # 공휴일 체크 - 스킵
                    if not self.is_trading_day(date_str):
                        continue
                    
                    cursor.execute('''
                        INSERT OR REPLACE INTO stock_prices 
                        (symbol, date, open, high, low, close, volume)
                        VALUES (?, ?, ?, ?, ?, ?, ?)
                    ''', (symbol, date_str,
                          float(row['open']), float(row['high']), 
                          float(row['low']), float(row['close']), 
                          int(row['volume'])))
                    inserted += 1
                    
                except Exception as e:
                    continue
            
            self.conn.commit()
            
            if inserted > 0:
                self.stats['updated'] += 1
                return True
            return False
            
        except Exception as e:
            return False
    
    def build_all(self, start_date: str = '2024-01-01', 
                  end_date: str = '2026-03-20'):
        """전체 종목 구축"""
        print("=" * 70)
        print("🔧 전체 DB 구축 시작")
        print("=" * 70)
        print(f"대상 기간: {start_date} ~ {end_date}")
        print()
        
        # 전체 종목 로드
        symbols = self.get_all_symbols()
        total = len(symbols)
        print(f"총 종목 수: {total}개")
        print()
        
        # 진행
        start_time = datetime.now()
        last_report = start_time
        
        for i, symbol in enumerate(symbols, 1):
            # 진행률 표시
            if i % 10 == 0 or i == 1:
                elapsed = (datetime.now() - start_time).total_seconds()
                rate = i / total
                eta = (elapsed / rate - elapsed) / 60 if rate > 0 else 0
                print(f"[{i:5d}/{total}] {rate*100:5.1f}% | ETA: {eta:.0f}분 | {symbol}")
            
            # 10분마다 상세 보고
            now = datetime.now()
            if (now - last_report).total_seconds() >= 600:
                self.print_progress(i, total, start_time)
                last_report = now
            
            # 기존 데이터 확인
            first_date, last_date, count = self.get_existing_data_range(symbol)
            
            # 이미 완전한 데이터가 있으면 스킵
            if first_date and last_date:
                if first_date <= start_date and last_date >= end_date:
                    self.stats['skipped'] += 1
                    continue
            
            # 데이터 가져오기
            time.sleep(0.1)
            if self.fetch_and_save(symbol, start_date, end_date):
                self.stats['success'] += 1
            else:
                self.stats['failed'] += 1
        
        # 최종 보고
        self.print_final_report(start_time)
    
    def print_progress(self, current: int, total: int, start_time: datetime):
        """진행 상황 출력"""
        elapsed = (datetime.now() - start_time).total_seconds()
        rate = current / total
        eta = (elapsed / rate - elapsed) / 60 if rate > 0 else 0
        
        print()
        print("=" * 70)
        print(f"📊 진행 보고 ({elapsed/60:.0f}분 경과)")
        print("=" * 70)
        print(f"진행: {current}/{total} ({rate*100:.1f}%)")
        print(f"성공: {self.stats['success']} | 실패: {self.stats['failed']} | "
              f"스킵: {self.stats['skipped']} | 업데이트: {self.stats['updated']}")
        print(f"예상 남은 시간: {eta:.0f}분")
        print("=" * 70)
        print()
    
    def print_final_report(self, start_time: datetime):
        """최종 보고"""
        elapsed = datetime.now() - start_time
        
        print()
        print("=" * 70)
        print("✅ 전체 DB 구축 완료")
        print("=" * 70)
        print(f"총 소요 시간: {elapsed}")
        print(f"✅ 성공: {self.stats['success']}개")
        print(f"⏭️ 스킵: {self.stats['skipped']}개 (이미 완료)")
        print(f"❌ 실패: {self.stats['failed']}개")
        print(f"📝 업데이트: {self.stats['updated']}개 종목")
        print("=" * 70)
        
        # 데이터 완성도 재확인
        self.verify_completeness()
    
    def verify_completeness(self):
        """완성도 검증"""
        print()
        print("🔍 데이터 완성도 검증...")
        
        cursor = self.conn.cursor()
        
        # 예상 거래일 수 (2024-01-01 ~ 2026-03-20)
        trading_days = sum(1 for d in pd.date_range('2024-01-01', '2026-03-20')
                          if d.weekday() < 5 and d.strftime('%Y-%m-%d') not in self.holidays)
        
        # 전체 종목
        cursor.execute('SELECT COUNT(DISTINCT symbol) FROM stock_prices')
        total = cursor.fetchone()[0]
        
        # 95% 이상 완료된 종목
        cursor.execute('''
            SELECT COUNT(*) FROM (
                SELECT symbol, COUNT(*) as cnt
                FROM stock_prices
                WHERE date >= '2024-01-01' AND date <= '2026-03-20'
                GROUP BY symbol
                HAVING cnt >= ?
            )
        ''', (int(trading_days * 0.95),))
        complete = cursor.fetchone()[0]
        
        # 평균 일수
        cursor.execute('''
            SELECT AVG(cnt) FROM (
                SELECT COUNT(*) as cnt
                FROM stock_prices
                WHERE date >= '2024-01-01' AND date <= '2026-03-20'
                GROUP BY symbol
            )
        ''')
        avg_days = cursor.fetchone()[0] or 0
        
        print(f"  전체 종목: {total}개")
        print(f"  예상 거래일: {trading_days}일")
        print(f"  완전한 데이터: {complete}개 ({complete/total*100:.1f}%)")
        print(f"  평균 보유일: {avg_days:.0f}일 ({avg_days/trading_days*100:.1f}%)")
    
    def close(self):
        """연결 종료"""
        self.conn.close()


def main():
    builder = FullDBBuilder()
    try:
        builder.build_all('2024-01-01', '2026-03-20')
    except KeyboardInterrupt:
        print("\n\n⚠️ 사용자 중단")
    finally:
        builder.close()


if __name__ == '__main__':
    main()
