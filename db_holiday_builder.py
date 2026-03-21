#!/usr/bin/env python3
"""
KRX Holiday Checker & DB Builder
================================
- 2024년 ~ 2026년 한국 공휴일 정보 관리
- 코스피/코스닥 전체 종목 데이터 구축
- 공휴일 예외 처리
"""

import sqlite3
import pandas as pd
import FinanceDataReader as fdr
from datetime import datetime, timedelta
from typing import List, Set
import time
import sys

# 2024년 ~ 2026년 한국 공휴일 (거래소 휴장일)
KRX_HOLIDAYS_2024_2026 = {
    # 2024년
    '2024-01-01',  # 신정
    '2024-02-09', '2024-02-12',  # 설연휴
    '2024-03-01',  # 삼일절
    '2024-04-10',  # 총선
    '2024-05-01',  # 근로자의 날
    '2024-05-06',  # 어린이날 대체
    '2024-05-15',  # 부처님 오신 날
    '2024-06-06',  # 현충일
    '2024-08-15',  # 광복절
    '2024-09-16', '2024-09-17', '2024-09-18',  # 추석연휴
    '2024-10-01',  # 국군의 날
    '2024-10-03',  # 개천절
    '2024-10-09',  # 한글날
    '2024-12-25',  # 성탄절
    '2024-12-31',  # 연말
    
    # 2025년
    '2025-01-01',  # 신정
    '2025-01-28', '2025-01-29', '2025-01-30',  # 설연휴
    '2025-03-01',  # 삼일절
    '2025-03-03',  # 삼일절 대체
    '2025-05-01',  # 근로자의 날
    '2025-05-05',  # 어린이날
    '2025-05-06',  # 부처님 오신 날
    '2025-06-06',  # 현충일
    '2025-08-15',  # 광복절
    '2025-10-03',  # 개천절
    '2025-10-06', '2025-10-07', '2025-10-08', '2025-10-09',  # 추석연휴
    '2025-12-25',  # 성탄절
    
    # 2026년 (3월까지)
    '2026-01-01',  # 신정
    '2026-02-16', '2026-02-17', '2026-02-18',  # 설연휴
    '2026-03-01',  # 삼일절
}

# 매년 반복되는 공휴일 (고정)
RECURRING_HOLIDAYS = [
    (1, 1),   # 신정
    (3, 1),   # 삼일절
    (5, 1),   # 근로자의 날
    (6, 6),   # 현충일
    (8, 15),  # 광복절
    (10, 3),  # 개천절
    (10, 9),  # 한글날
    (12, 25), # 성탄절
]


class HolidayChecker:
    """공휴일 체커"""
    
    def __init__(self):
        self.holidays = set(KRX_HOLIDAYS_2024_2026)
    
    def is_holiday(self, date_str: str) -> bool:
        """공휴일 여부 확인"""
        return date_str in self.holidays
    
    def is_weekend(self, date_str: str) -> bool:
        """주말 여부 확인"""
        date = datetime.strptime(date_str, '%Y-%m-%d')
        return date.weekday() >= 5  # 5=토요일, 6=일요일
    
    def is_trading_day(self, date_str: str) -> bool:
        """거래일 여부 확인"""
        return not (self.is_holiday(date_str) or self.is_weekend(date_str))
    
    def get_trading_days(self, start_date: str, end_date: str) -> List[str]:
        """거래일 목록 반환"""
        trading_days = []
        current = datetime.strptime(start_date, '%Y-%m-%d')
        end = datetime.strptime(end_date, '%Y-%m-%d')
        
        while current <= end:
            date_str = current.strftime('%Y-%m-%d')
            if self.is_trading_day(date_str):
                trading_days.append(date_str)
            current += timedelta(days=1)
        
        return trading_days


class DBBuilder:
    """DB 구축기"""
    
    def __init__(self, db_path: str = './data/pivot_strategy.db'):
        self.db_path = db_path
        self.holiday_checker = HolidayChecker()
        self.conn = sqlite3.connect(db_path)
        self.conn.row_factory = sqlite3.Row
    
    def get_all_symbols(self) -> List[str]:
        """전체 종목 리스트 조회"""
        cursor = self.conn.cursor()
        
        # stock_info 테이블에서 조회
        try:
            cursor.execute('SELECT DISTINCT symbol FROM stock_info ORDER BY symbol')
            symbols = [row[0] for row in cursor.fetchall()]
            if symbols:
                return symbols
        except:
            pass
        
        # stock_prices 테이블에서 조회
        cursor.execute('SELECT DISTINCT symbol FROM stock_prices ORDER BY symbol')
        symbols = [row[0] for row in cursor.fetchall()]
        return symbols
    
    def get_missing_data_symbols(self, start_date: str = '2024-01-01', 
                                  end_date: str = '2026-03-20',
                                  min_days: int = 100) -> List[dict]:
        """데이터가 부족한 종목 조회"""
        cursor = self.conn.cursor()
        
        # 예상 거래일 수 계산
        expected_days = len(self.holiday_checker.get_trading_days(start_date, end_date))
        
        query = '''
            SELECT 
                symbol,
                COUNT(*) as data_count,
                MIN(date) as first_date,
                MAX(date) as last_date
            FROM stock_prices
            WHERE date >= ? AND date <= ?
            GROUP BY symbol
            HAVING data_count < ? OR last_date < ?
            ORDER BY data_count ASC
        '''
        
        cursor.execute(query, (start_date, end_date, min_days, end_date))
        results = []
        for row in cursor.fetchall():
            results.append({
                'symbol': row[0],
                'data_count': row[1],
                'first_date': row[2],
                'last_date': row[3],
                'expected_days': expected_days,
                'missing_ratio': (expected_days - row[1]) / expected_days if expected_days > 0 else 0
            })
        
        return results
    
    def check_symbol_data_gaps(self, symbol: str, start_date: str, end_date: str) -> List[str]:
        """특정 종목의 누락된 거래일 확인"""
        cursor = self.conn.cursor()
        
        # DB에 있는 날짜들
        cursor.execute('''
            SELECT date FROM stock_prices 
            WHERE symbol = ? AND date >= ? AND date <= ?
            ORDER BY date
        ''', (symbol, start_date, end_date))
        
        existing_dates = set(row[0] for row in cursor.fetchall())
        
        # 예상 거래일
        expected_dates = set(self.holiday_checker.get_trading_days(start_date, end_date))
        
        # 누락된 날짜
        missing_dates = sorted(expected_dates - existing_dates)
        
        return missing_dates
    
    def fetch_and_save_symbol(self, symbol: str, start_date: str, end_date: str) -> bool:
        """특정 종목 데이터 fetch 및 저장"""
        try:
            # FDR로 데이터 가져오기
            df = fdr.DataReader(symbol, start_date, end_date)
            
            if df.empty:
                print(f"  ⚠️ {symbol}: 데이터 없음")
                return False
            
            # 컬럼명 표준화
            df = df.reset_index()
            if 'Date' in df.columns:
                df.rename(columns={'Date': 'date'}, inplace=True)
            
            # 필요한 컬럼만 선택
            required_cols = ['date', 'Open', 'High', 'Low', 'Close', 'Volume']
            if not all(col in df.columns for col in required_cols):
                print(f"  ⚠️ {symbol}: 컬럼 부족 - {df.columns.tolist()}")
                return False
            
            df = df[required_cols]
            df.columns = ['date', 'open', 'high', 'low', 'close', 'volume']
            
            # 공휴일 데이터 필터링 (거래량 0인 날짜 제외)
            df = df[df['volume'] > 0]
            
            if df.empty:
                print(f"  ⚠️ {symbol}: 유효한 거래일 없음")
                return False
            
            # DB 저장
            cursor = self.conn.cursor()
            for _, row in df.iterrows():
                try:
                    cursor.execute('''
                        INSERT OR REPLACE INTO stock_prices 
                        (symbol, date, open, high, low, close, volume)
                        VALUES (?, ?, ?, ?, ?, ?, ?)
                    ''', (symbol, row['date'].strftime('%Y-%m-%d') if hasattr(row['date'], 'strftime') else str(row['date']),
                          float(row['open']), float(row['high']), float(row['low']), 
                          float(row['close']), int(row['volume'])))
                except Exception as e:
                    print(f"    저장 오류 {symbol} {row['date']}: {e}")
            
            self.conn.commit()
            print(f"  ✅ {symbol}: {len(df)}건 저장 ({df['date'].min()} ~ {df['date'].max()})")
            return True
            
        except Exception as e:
            print(f"  ❌ {symbol}: {e}")
            return False
    
    def build_missing_data(self, start_date: str = '2024-01-01',
                          end_date: str = '2026-03-20',
                          batch_size: int = 10):
        """누락된 데이터 구축"""
        print("=" * 70)
        print("🔧 DB 구축 시작")
        print("=" * 70)
        print(f"기간: {start_date} ~ {end_date}")
        print()
        
        # 데이터 부족 종목 조회
        print("📊 데이터 부족 종목 분석 중...")
        missing_symbols = self.get_missing_data_symbols(start_date, end_date)
        
        if not missing_symbols:
            print("✅ 모든 종목이 완벽합니다!")
            return
        
        print(f"총 {len(missing_symbols)}개 종목 데이터 보충 필요")
        print()
        
        # 진행 상황 추적
        total = len(missing_symbols)
        success_count = 0
        fail_count = 0
        skip_count = 0
        
        start_time = datetime.now()
        last_report_time = start_time
        
        for i, info in enumerate(missing_symbols, 1):
            symbol = info['symbol']
            
            # 진행률 표시
            if i % 10 == 0:
                print(f"\n   진행: {i}/{total} ({i/total*100:.1f}%)")
            
            # 10분마다 보고
            current_time = datetime.now()
            if (current_time - last_report_time).total_seconds() >= 600:
                elapsed = current_time - start_time
                print(f"\n   [진행 보고] {elapsed.total_seconds()/60:.0f}분 경과")
                print(f"   성공: {success_count}, 실패: {fail_count}, 스킵: {skip_count}")
                last_report_time = current_time
            
            # 데이터 가져오기
            time.sleep(0.1)  # Rate limit
            
            # 해당 종목의 누락된 기간 파악
            gaps = self.check_symbol_data_gaps(symbol, start_date, end_date)
            
            if not gaps:
                skip_count += 1
                continue
            
            # 데이터 fetch
            if self.fetch_and_save_symbol(symbol, start_date, end_date):
                success_count += 1
            else:
                fail_count += 1
        
        # 최종 보고
        elapsed = datetime.now() - start_time
        print("\n" + "=" * 70)
        print("📊 구축 완료 요약")
        print("=" * 70)
        print(f"총 소요: {elapsed}")
        print(f"✅ 성공: {success_count}개")
        print(f"❌ 실패: {fail_count}개")
        print(f"⏭️ 스킵: {skip_count}개")
        print("=" * 70)
    
    def verify_data_completeness(self, start_date: str = '2024-01-01',
                                  end_date: str = '2026-03-20') -> dict:
        """데이터 완성도 검증"""
        print("\n🔍 데이터 완성도 검증...")
        
        cursor = self.conn.cursor()
        
        # 전체 종목 수
        cursor.execute('SELECT COUNT(DISTINCT symbol) FROM stock_prices')
        total_symbols = cursor.fetchone()[0]
        
        # 예상 거래일
        expected_days = len(self.holiday_checker.get_trading_days(start_date, end_date))
        
        # 완전한 데이터를 가진 종목
        cursor.execute('''
            SELECT COUNT(*) FROM (
                SELECT symbol, COUNT(*) as cnt
                FROM stock_prices
                WHERE date >= ? AND date <= ?
                GROUP BY symbol
                HAVING cnt >= ? * 0.95
            )
        ''', (start_date, end_date, expected_days))
        complete_symbols = cursor.fetchone()[0]
        
        # 평균 데이터 보유일
        cursor.execute('''
            SELECT AVG(cnt) FROM (
                SELECT COUNT(*) as cnt
                FROM stock_prices
                WHERE date >= ? AND date <= ?
                GROUP BY symbol
            )
        ''', (start_date, end_date))
        avg_days = cursor.fetchone()[0] or 0
        
        result = {
            'total_symbols': total_symbols,
            'expected_days': expected_days,
            'complete_symbols': complete_symbols,
            'complete_ratio': complete_symbols / total_symbols if total_symbols > 0 else 0,
            'avg_days': avg_days,
            'coverage': avg_days / expected_days if expected_days > 0 else 0
        }
        
        print(f"  전체 종목: {total_symbols}개")
        print(f"  완전한 데이터: {complete_symbols}개 ({result['complete_ratio']*100:.1f}%)")
        print(f"  평균 보유일: {avg_days:.0f}일 / {expected_days}일 ({result['coverage']*100:.1f}%)")
        
        return result
    
    def close(self):
        """연결 종료"""
        self.conn.close()


def main():
    """메인 실행"""
    builder = DBBuilder()
    
    try:
        # 데이터 완성도 먼저 확인
        builder.verify_data_completeness('2024-01-01', '2026-03-20')
        
        # 누락된 데이터 구축
        builder.build_missing_data('2024-01-01', '2026-03-20')
        
        # 다시 완성도 확인
        print("\n")
        builder.verify_data_completeness('2024-01-01', '2026-03-20')
        
    except KeyboardInterrupt:
        print("\n\n⚠️ 사용자가 중단했습니다.")
    finally:
        builder.close()


if __name__ == '__main__':
    main()
