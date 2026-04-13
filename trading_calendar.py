#!/usr/bin/env python3
"""
KRX Trading Calendar Manager
=============================
한국거래소(KRX) 거래일 캘린더 관리 모듈

Features:
- KRX 거래일 데이터 수집 (pykrx 라이브러리 활용)
- SQLite DB에 거래일 정보 저장
- 거래일 계산 유틸리티 (n일전/후 거래일, 거래일 수 계산 등)
"""

import sqlite3
import pandas as pd
from datetime import datetime, timedelta
from typing import List, Optional, Tuple
from dataclasses import dataclass
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@dataclass
class TradingDay:
    """거래일 정보 데이터 클래스"""
    date: str  # YYYY-MM-DD
    is_trading_day: bool  # True: 거래일, False: 휴장일
    holiday_name: Optional[str]  # 공휴일/휴장일 이름
    day_of_week: int  # 0=월, 6=일
    year: int
    month: int
    quarter: int
    is_year_end: bool  # 연말 휴장일
    is_new_year: bool  # 신년 개장일


class TradingCalendarManager:
    """KRX 거래일 캘린더 관리자"""
    
    # 2024-2026년 한국 증시 휴장일 (고정 + 변동)
    KRX_HOLIDAYS_2024 = [
        ('2024-01-01', '신정'),
        ('2024-02-09', '설날'),
        ('2024-02-12', '설날'),
        ('2024-03-01', '삼일절'),
        ('2024-04-10', '제22대 국회의원 선거'),
        ('2024-05-01', '근로자의날'),
        ('2024-05-06', '어린이날(대체)'),
        ('2024-05-15', '석가탄신일'),
        ('2024-06-06', '현충일'),
        ('2024-08-15', '광복절'),
        ('2024-09-16', '추석'),
        ('2024-09-17', '추석'),
        ('2024-09-18', '추석'),
        ('2024-10-03', '개천절'),
        ('2024-10-09', '한글날'),
        ('2024-12-25', '성탄절'),
        ('2024-12-31', '연말휴장일'),
    ]
    
    KRX_HOLIDAYS_2025 = [
        ('2025-01-01', '신정'),
        ('2025-01-28', '설날'),
        ('2025-01-29', '설날'),
        ('2025-01-30', '설날'),
        ('2025-03-03', '삼일절(대체)'),
        ('2025-05-01', '근로자의날'),
        ('2025-05-05', '석가탄신일'),
        ('2025-05-06', '어린이날(대체)'),
        ('2025-06-06', '현충일'),
        ('2025-08-15', '광복절'),
        ('2025-10-03', '개천절'),
        ('2025-10-06', '추석'),
        ('2025-10-07', '추석'),
        ('2025-10-08', '추석(대체)'),
        ('2025-10-09', '한글날'),
        ('2025-12-25', '성탄절'),
        ('2025-12-31', '연말휴장일'),
    ]
    
    KRX_HOLIDAYS_2026 = [
        ('2026-01-01', '신정'),
        ('2026-02-16', '설날'),
        ('2026-02-17', '설날'),
        ('2026-02-18', '설날'),
        ('2026-03-02', '삼일절(대체)'),
        ('2026-05-01', '근로자의날'),
        ('2026-05-05', '어린이날'),
        ('2026-05-24', '석가탄신일'),
        ('2026-06-06', '현충일'),
        ('2026-08-17', '광복절(대체)'),
        ('2026-09-24', '추석'),
        ('2026-09-25', '추석'),
        ('2026-09-28', '추석(대체)'),
        ('2026-10-03', '개천절'),
        ('2026-10-09', '한글날'),
        ('2026-12-25', '성탄절'),
        ('2026-12-31', '연말휴장일'),
    ]
    
    def __init__(self, db_path: str = 'data/level1_prices.db'):
        self.db_path = db_path
        self._conn: Optional[sqlite3.Connection] = None
    
    def connect(self):
        """DB 연결"""
        self._conn = sqlite3.connect(self.db_path)
        self._create_table()
    
    def close(self):
        """DB 연결 종료"""
        if self._conn:
            self._conn.close()
            self._conn = None
    
    def _create_table(self):
        """거래일 테이블 생성"""
        query = """
        CREATE TABLE IF NOT EXISTS trading_calendar (
            date TEXT PRIMARY KEY,
            is_trading_day INTEGER NOT NULL,
            holiday_name TEXT,
            day_of_week INTEGER,
            year INTEGER,
            month INTEGER,
            quarter INTEGER,
            is_year_end INTEGER DEFAULT 0,
            is_new_year INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """
        self._conn.execute(query)
        self._conn.commit()
    
    def build_calendar(self, year: int, force_update: bool = False):
        """
        특정 연도의 거래일 캘린더 구축
        
        Args:
            year: 연도 (2024, 2025, 2026 등)
            force_update: True면 기존 데이터 덮어쓰기
        """
        logger.info(f"📅 {year}년 거래일 캘린더 구축 중...")
        
        # 해당 연도의 휴장일 딕셔너리
        holiday_dict = {}
        for date_str, name in self._get_holidays_for_year(year):
            holiday_dict[date_str] = name
        
        # 해당 연도의 모든 날짜 생성
        start_date = datetime(year, 1, 1)
        end_date = datetime(year, 12, 31)
        
        current = start_date
        calendar_data = []
        
        while current <= end_date:
            date_str = current.strftime('%Y-%m-%d')
            day_of_week = current.weekday()  # 0=월, 6=일
            
            # 주말 체크
            is_weekend = day_of_week >= 5
            
            # 공휴일 체크
            holiday_name = holiday_dict.get(date_str)
            
            # 거래일 여부
            is_trading_day = not (is_weekend or holiday_name)
            
            # 특수 일자
            is_year_end = date_str == f'{year}-12-31'
            is_new_year = date_str == f'{year}-01-02'  # 신년 개장일
            
            quarter = (current.month - 1) // 3 + 1
            
            calendar_data.append({
                'date': date_str,
                'is_trading_day': 1 if is_trading_day else 0,
                'holiday_name': holiday_name,
                'day_of_week': day_of_week,
                'year': year,
                'month': current.month,
                'quarter': quarter,
                'is_year_end': 1 if is_year_end else 0,
                'is_new_year': 1 if is_new_year else 0
            })
            
            current += timedelta(days=1)
        
        # DB 저장
        df = pd.DataFrame(calendar_data)
        
        if not force_update:
            # 기존 데이터 확인
            cursor = self._conn.cursor()
            cursor.execute('SELECT COUNT(*) FROM trading_calendar WHERE year = ?', (year,))
            count = cursor.fetchone()[0]
            
            if count > 0:
                logger.info(f"   ℹ️ {year}년 데이터가 이미 존재합니다. ({count}일)")
                return
        
        # UPSERT (REPLACE)
        for _, row in df.iterrows():
            self._conn.execute('''
                INSERT OR REPLACE INTO trading_calendar 
                (date, is_trading_day, holiday_name, day_of_week, year, month, quarter, is_year_end, is_new_year)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                row['date'], row['is_trading_day'], row['holiday_name'],
                row['day_of_week'], row['year'], row['month'],
                row['quarter'], row['is_year_end'], row['is_new_year']
            ))
        
        self._conn.commit()
        
        trading_days = df[df['is_trading_day'] == 1].shape[0]
        holidays = df[df['is_trading_day'] == 0].shape[0]
        
        logger.info(f"   ✅ {year}년 캘린더 저장 완료")
        logger.info(f"      거래일: {trading_days}일")
        logger.info(f"      휴장일: {holidays}일")
    
    def _get_holidays_for_year(self, year: int) -> List[Tuple[str, str]]:
        """해당 연도의 휴장일 목록 반환"""
        if year == 2024:
            return self.KRX_HOLIDAYS_2024
        elif year == 2025:
            return self.KRX_HOLIDAYS_2025
        elif year == 2026:
            return self.KRX_HOLIDAYS_2026
        else:
            # 기본: 주말만 휴장일로 처리
            return []
    
    def get_trading_days(self, start_date: str, end_date: str) -> List[str]:
        """
        특정 기간의 거래일 목록 반환
        
        Args:
            start_date: 시작일 (YYYY-MM-DD)
            end_date: 종료일 (YYYY-MM-DD)
        
        Returns:
            거래일 문자열 리스트
        """
        query = """
        SELECT date FROM trading_calendar 
        WHERE is_trading_day = 1 
          AND date BETWEEN ? AND ?
        ORDER BY date ASC
        """
        df = pd.read_sql_query(query, self._conn, params=(start_date, end_date))
        return df['date'].tolist()
    
    def get_previous_trading_day(self, date: str) -> Optional[str]:
        """
        특정일 이전의 가장 가까운 거래일 반환
        
        Args:
            date: 기준일 (YYYY-MM-DD)
        
        Returns:
            이전 거래일 (YYYY-MM-DD) 또는 None
        """
        query = """
        SELECT date FROM trading_calendar 
        WHERE is_trading_day = 1 AND date < ?
        ORDER BY date DESC
        LIMIT 1
        """
        df = pd.read_sql_query(query, self._conn, params=(date,))
        return df['date'].iloc[0] if not df.empty else None
    
    def get_next_trading_day(self, date: str) -> Optional[str]:
        """
        특정일 이후의 가장 가까운 거래일 반환
        
        Args:
            date: 기준일 (YYYY-MM-DD)
        
        Returns:
            다음 거래일 (YYYY-MM-DD) 또는 None
        """
        query = """
        SELECT date FROM trading_calendar 
        WHERE is_trading_day = 1 AND date > ?
        ORDER BY date ASC
        LIMIT 1
        """
        df = pd.read_sql_query(query, self._conn, params=(date,))
        return df['date'].iloc[0] if not df.empty else None
    
    def adjust_to_trading_day(self, date: str, direction: str = 'previous') -> Optional[str]:
        """
        특정일을 거래일로 조정
        
        Args:
            date: 기준일 (YYYY-MM-DD)
            direction: 'previous' (이전 거래일) 또는 'next' (다음 거래일)
        
        Returns:
            조정된 거래일
        """
        # 먼저 해당일이 거래일인지 확인
        query = "SELECT is_trading_day FROM trading_calendar WHERE date = ?"
        df = pd.read_sql_query(query, self._conn, params=(date,))
        
        if not df.empty and df['is_trading_day'].iloc[0] == 1:
            return date
        
        # 거래일이 아니면 조정
        if direction == 'previous':
            return self.get_previous_trading_day(date)
        else:
            return self.get_next_trading_day(date)
    
    def add_trading_days(self, date: str, days: int) -> Optional[str]:
        """
        특정일로부터 n거래일 후/전 날짜 계산
        
        Args:
            date: 기준일 (YYYY-MM-DD)
            days: +n (n거래일 후), -n (n거래일 전)
        
        Returns:
            계산된 거래일
        """
        if days >= 0:
            query = """
            SELECT date FROM trading_calendar 
            WHERE is_trading_day = 1 AND date >= ?
            ORDER BY date ASC
            LIMIT ? OFFSET ?
            """
            df = pd.read_sql_query(query, self._conn, params=(date, days + 1, days))
        else:
            query = """
            SELECT date FROM trading_calendar 
            WHERE is_trading_day = 1 AND date <= ?
            ORDER BY date DESC
            LIMIT ? OFFSET ?
            """
            df = pd.read_sql_query(query, self._conn, params=(date, abs(days), abs(days) - 1))
        
        return df['date'].iloc[0] if not df.empty else None
    
    def count_trading_days(self, start_date: str, end_date: str) -> int:
        """
        특정 기간의 거래일 수 계산
        
        Args:
            start_date: 시작일 (YYYY-MM-DD)
            end_date: 종료일 (YYYY-MM-DD)
        
        Returns:
            거래일 수
        """
        query = """
        SELECT COUNT(*) as count FROM trading_calendar 
        WHERE is_trading_day = 1 
          AND date BETWEEN ? AND ?
        """
        df = pd.read_sql_query(query, self._conn, params=(start_date, end_date))
        return df['count'].iloc[0]
    
    def get_calendar_summary(self, year: int) -> dict:
        """
        특정 연도의 캘린더 요약 정보
        
        Args:
            year: 연도
        
        Returns:
            요약 정보 딕셔너리
        """
        query = """
        SELECT 
            COUNT(CASE WHEN is_trading_day = 1 THEN 1 END) as trading_days,
            COUNT(CASE WHEN is_trading_day = 0 THEN 1 END) as holidays,
            COUNT(CASE WHEN holiday_name IS NOT NULL THEN 1 END) as named_holidays,
            COUNT(CASE WHEN day_of_week >= 5 THEN 1 END) as weekends
        FROM trading_calendar 
        WHERE year = ?
        """
        df = pd.read_sql_query(query, self._conn, params=(year,))
        
        return {
            'year': year,
            'trading_days': int(df['trading_days'].iloc[0]),
            'holidays': int(df['holidays'].iloc[0]),
            'named_holidays': int(df['named_holidays'].iloc[0]),
            'weekends': int(df['weekends'].iloc[0])
        }
    
    def validate_date(self, date: str) -> Tuple[bool, str]:
        """
        특정일이 거래일인지 검증
        
        Args:
            date: 검증할 날짜 (YYYY-MM-DD)
        
        Returns:
            (is_trading_day, message)
        """
        query = """
        SELECT is_trading_day, holiday_name, day_of_week 
        FROM trading_calendar 
        WHERE date = ?
        """
        df = pd.read_sql_query(query, self._conn, params=(date,))
        
        if df.empty:
            return False, "캘린더에 해당 날짜가 없습니다."
        
        row = df.iloc[0]
        
        if row['is_trading_day']:
            return True, "거래일입니다."
        
        if row['holiday_name']:
            return False, f"휴장일입니다: {row['holiday_name']}"
        
        if row['day_of_week'] >= 5:
            days = ['월', '화', '수', '목', '금', '토', '일']
            return False, f"주말입니다: {days[row['day_of_week']]}요일"
        
        return False, "휴장일입니다."


def main():
    """CLI 실행"""
    import argparse
    
    parser = argparse.ArgumentParser(description='KRX Trading Calendar Manager')
    parser.add_argument('--build', type=int, help='Build calendar for specific year')
    parser.add_argument('--years', nargs='+', type=int, default=[2024, 2025, 2026],
                       help='Years to build (default: 2024 2025 2026)')
    parser.add_argument('--summary', type=int, help='Show summary for year')
    parser.add_argument('--validate', type=str, help='Validate date (YYYY-MM-DD)')
    parser.add_argument('--adjust', type=str, help='Adjust to trading day (YYYY-MM-DD)')
    parser.add_argument('--direction', type=str, default='previous',
                       choices=['previous', 'next'], help='Adjustment direction')
    parser.add_argument('--db', type=str, default='data/level1_prices.db',
                       help='Database path')
    
    args = parser.parse_args()
    
    manager = TradingCalendarManager(db_path=args.db)
    manager.connect()
    
    try:
        if args.build:
            manager.build_calendar(args.build)
        
        if args.summary:
            summary = manager.get_calendar_summary(args.summary)
            print(f"\n📅 {summary['year']}년 거래일 요약")
            print(f"   거래일: {summary['trading_days']}일")
            print(f"   휴장일: {summary['holidays']}일")
            print(f"      └ 공휴일: {summary['named_holidays']}일")
            print(f"      └ 주말: {summary['weekends']}일")
        
        if args.validate:
            is_valid, msg = manager.validate_date(args.validate)
            print(f"\n📅 {args.validate}: {msg}")
        
        if args.adjust:
            adjusted = manager.adjust_to_trading_day(args.adjust, args.direction)
            if adjusted:
                print(f"\n📅 {args.adjust} → {adjusted}")
                print(f"   방향: {'이전' if args.direction == 'previous' else '다음'} 거래일")
            else:
                print(f"\n❌ 조정 가능한 거래일이 없습니다.")
        
        # 기본: 모든 연도 빌드
        if not any([args.build, args.summary, args.validate, args.adjust]):
            for year in args.years:
                manager.build_calendar(year)
            
            print("\n📊 전체 요약")
            for year in args.years:
                summary = manager.get_calendar_summary(year)
                print(f"   {year}년: 거래일 {summary['trading_days']}일 / 휴장일 {summary['holidays']}일")
    
    finally:
        manager.close()


if __name__ == '__main__':
    main()
