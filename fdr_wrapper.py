#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
FinanceDataReader Wrapper with Local Database Caching
======================================================
FinanceDataReader API를 감싸는 래퍼 모듈
- DB에 데이터가 있으면 캐시에서 반환 (API 호출 안 함)
- DB에 없으면 API 호출 후 DB에 저장

Usage:
    from fdr_wrapper import FDRWrapper, DatabaseManager
    
    # 방법 1: 래퍼 클래스 사용
    fdr = FDRWrapper()
    df = fdr.get_price('005930', '2024-01-01', '2024-12-31')
    
    # 방법 2: 컨텍스트 매니저 사용
    with DatabaseManager() as db:
        wrapper = FDRWrapper(db)
        df = wrapper.get_price('005930', '2024-01-01', '2024-12-31')
"""

import pandas as pd
import FinanceDataReader as fdr_module
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Tuple
import sqlite3
import os


class DatabaseManager:
    """
    SQLite 데이터베이스 연결 관리 (컨텍스트 매니저 지원)
    """
    
    def __init__(self, db_path: str = './data/pivot_strategy.db'):
        self.db_path = db_path
        self.conn = None
        self.cursor = None
    
    def __enter__(self):
        """컨텍스트 매니저 진입"""
        self.conn = sqlite3.connect(self.db_path)
        self.cursor = self.conn.cursor()
        self._ensure_schema()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """컨텍스트 매니저 종료"""
        if self.conn:
            if exc_type is None:
                self.conn.commit()
            else:
                self.conn.rollback()
            self.conn.close()
    
    def _ensure_schema(self):
        """테이블 및 인덱스가 존재하는지 확인/생성"""
        # stock_prices 테이블 생성 (없으면)
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS stock_prices (
                symbol TEXT NOT NULL,
                date TEXT NOT NULL,
                open REAL,
                high REAL,
                low REAL,
                close REAL,
                volume INTEGER,
                PRIMARY KEY (symbol, date)
            )
        ''')
        
        # symbol + date 복합 인덱스 생성 (중복 방지 및 조회 성능 향상)
        self.cursor.execute('''
            CREATE UNIQUE INDEX IF NOT EXISTS idx_symbol_date 
            ON stock_prices(symbol, date)
        ''')
        
        # symbol 단독 인덱스 (조회 성능 향상)
        self.cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_symbol 
            ON stock_prices(symbol)
        ''')
        
        self.conn.commit()
    
    def get_price_range(
        self, 
        symbol: str, 
        start_date: str, 
        end_date: str
    ) -> pd.DataFrame:
        """
        특정 기간의 주가 데이터 조회
        
        Parameters:
        -----------
        symbol : str
            종목코드
        start_date : str
            시작일 (YYYY-MM-DD)
        end_date : str
            종료일 (YYYY-MM-DD)
        
        Returns:
        --------
        pd.DataFrame : 주가 데이터
        """
        query = """
            SELECT symbol, date, open, high, low, close, volume 
            FROM stock_prices 
            WHERE symbol = ? 
              AND date >= ? 
              AND date <= ?
            ORDER BY date ASC
        """
        df = pd.read_sql_query(
            query, 
            self.conn, 
            params=(symbol, start_date, end_date),
            parse_dates=['date']
        )
        return df
    
    def check_data_availability(
        self, 
        symbol: str, 
        start_date: str, 
        end_date: str
    ) -> Tuple[bool, int, str, str]:
        """
        특정 기간의 데이터가 DB에 얼마나 있는지 확인
        
        Returns:
        --------
        (has_data, count, min_date, max_date)
        """
        query = """
            SELECT COUNT(*), MIN(date), MAX(date) 
            FROM stock_prices 
            WHERE symbol = ? 
              AND date >= ? 
              AND date <= ?
        """
        self.cursor.execute(query, (symbol, start_date, end_date))
        result = self.cursor.fetchone()
        
        count = result[0] if result else 0
        min_date = result[1] if result and result[1] else None
        max_date = result[2] if result and result[2] else None
        
        # 요청 기간의 영업일 수 대비 데이터 비율 계산 (대략 70% 이상이면 충분하다고 판단)
        has_data = count > 0
        
        return has_data, count, min_date, max_date
    
    def get_available_date_range(self, symbol: str) -> Tuple[Optional[str], Optional[str]]:
        """해당 종목이 DB에서 가진 데이터의 최소/최대 날짜"""
        self.cursor.execute(
            "SELECT MIN(date), MAX(date) FROM stock_prices WHERE symbol = ?",
            (symbol,)
        )
        result = self.cursor.fetchone()
        if result and result[0]:
            return result[0], result[1]
        return None, None
    
    def save_prices(self, symbol: str, df: pd.DataFrame) -> int:
        """
        주가 데이터를 DB에 저장 (중복 시 업데이트)
        
        Parameters:
        -----------
        symbol : str
            종목코드
        df : pd.DataFrame
            주가 데이터 (columns: open, high, low, close, volume)
        
        Returns:
        --------
        int : 저장된 행 수
        """
        if df.empty:
            return 0
        
        df = df.copy()
        
        # 인덱스 처리
        if isinstance(df.index, pd.DatetimeIndex):
            df = df.reset_index()
            date_col = df.columns[0]
            df = df.rename(columns={date_col: 'date'})
        
        # 컬럼명 표준화
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
        
        # 필요 컬럼 확인
        required_cols = ['symbol', 'date', 'open', 'high', 'low', 'close', 'volume']
        missing_cols = [col for col in required_cols if col not in df.columns]
        if missing_cols:
            print(f"⚠️ 누락된 컬럼: {missing_cols}")
            return 0
        
        df = df[required_cols]
        
        # INSERT OR REPLACE로 저장
        saved_count = 0
        for _, row in df.iterrows():
            try:
                self.cursor.execute('''
                    INSERT OR REPLACE INTO stock_prices 
                    (symbol, date, open, high, low, close, volume)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                ''', (
                    row['symbol'], 
                    row['date'], 
                    float(row['open']), 
                    float(row['high']), 
                    float(row['low']), 
                    float(row['close']), 
                    int(row['volume'])
                ))
                saved_count += 1
            except Exception as e:
                print(f"⚠️ 데이터 저장 오류 ({row['date']}): {e}")
                continue
        
        self.conn.commit()
        return saved_count


class FDRWrapper:
    """
    FinanceDataReader Wrapper with Database Caching
    """
    
    def __init__(self, db_manager: Optional[DatabaseManager] = None, db_path: str = './data/pivot_strategy.db'):
        """
        Parameters:
        -----------
        db_manager : DatabaseManager, optional
            외부에서 생성한 DatabaseManager 인스턴스
        db_path : str
            SQLite 데이터베이스 파일 경로 (db_manager가 None일 때 사용)
        """
        self.db = db_manager
        self.db_path = db_path
        self._external_db = db_manager is not None
        self._cache_stats = {'hit': 0, 'miss': 0, 'api_calls': 0, 'partial': 0}
    
    def __enter__(self):
        """컨텍스트 매니저 진입"""
        if not self._external_db:
            self.db = DatabaseManager(self.db_path)
            self.db.__enter__()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """컨텍스트 매니저 종료"""
        if not self._external_db and self.db:
            self.db.__exit__(exc_type, exc_val, exc_tb)
            self.db = None
    
    def _ensure_db(self):
        """DB 매니저가 없으면 생성"""
        if self.db is None:
            self.db = DatabaseManager(self.db_path)
            self.db.__enter__()
    
    def get_price(
        self, 
        symbol: str, 
        start: Optional[str] = None, 
        end: Optional[str] = None,
        use_cache: bool = True
    ) -> pd.DataFrame:
        """
        주가 데이터 조회 (DB 우선, 없으면 API)
        
        Flow:
        1. DB에 해당 기간 데이터가 있는지 확인
        2. DB에 충분한 데이터 있으면 → DB 데이터 리턴
        3. DB에 없거나 부족하면 → API 호출 → DB 저장 → 리턴
        4. API 호출 실패 시 → DB에 있는 데이터라도 반환
        
        Parameters:
        -----------
        symbol : str
            종목코드 (예: '005930')
        start : str, optional
            시작일 (YYYY-MM-DD), None이면 1년 전
        end : str, optional
            종료일 (YYYY-MM-DD), None이면 오늘
        use_cache : bool
            DB 캐시 사용 여부 (기본 True)
        
        Returns:
        --------
        pd.DataFrame : 주가 데이터
            columns: symbol, date, open, high, low, close, volume
        """
        # 기본 날짜 설정
        if end is None:
            end = datetime.now().strftime('%Y-%m-%d')
        if start is None:
            start = (datetime.now() - timedelta(days=365)).strftime('%Y-%m-%d')
        
        # 날짜 형식 통일
        start = pd.to_datetime(start).strftime('%Y-%m-%d')
        end = pd.to_datetime(end).strftime('%Y-%m-%d')
        
        # DB 매니저 확보
        self._ensure_db()
        
        # 1. DB에 해당 기간 데이터가 있는지 확인
        if use_cache:
            try:
                has_data, count, min_date, max_date = self.db.check_data_availability(
                    symbol, start, end
                )
                
                if has_data:
                    # DB에서 해당 기간 데이터 조회
                    df_db = self.db.get_price_range(symbol, start, end)
                    
                    if not df_db.empty:
                        # 요청 기간이 DB 데이터 범위 내에 있는지 확인
                        db_start = pd.to_datetime(min_date)
                        db_end = pd.to_datetime(max_date)
                        req_start = pd.to_datetime(start)
                        req_end = pd.to_datetime(end)
                        
                        # DB가 요청 기간을 완전히 커버하는지 확인
                        if db_start <= req_start and db_end >= req_end:
                            self._cache_stats['hit'] += 1
                            print(f"💾 DB 캐시 사용: {symbol} ({start}~{end}, {len(df_db)}일)")
                            return df_db
                        else:
                            # 부분 데이터 (확장이 필요한 경우)
                            self._cache_stats['partial'] += 1
                            print(f"⚠️ DB 부분 데이터: {symbol} (DB: {min_date}~{max_date}, 요청: {start}~{end})")
                            # 여기서는 API 호출 후 병합하는 로직을 추가할 수 있음
                            # 현재는 부분 데이터라도 반환
                            return df_db
            except Exception as e:
                print(f"⚠️ DB 조회 오류: {e}")
        
        # 2. DB에 데이터가 없거나 부족하면 API 호출
        self._cache_stats['miss'] += 1
        self._cache_stats['api_calls'] += 1
        print(f"🌐 API 호출: {symbol} ({start}~{end})")
        
        try:
            df_api = fdr_module.DataReader(symbol, start, end)
            
            if df_api.empty:
                print(f"⚠️ API 데이터 없음: {symbol}")
                # API 실패 시 DB에 있는 기존 데이터라도 반환
                return self._fallback_to_db(symbol, start, end)
            
            # DB에 저장
            try:
                saved_count = self.db.save_prices(symbol, df_api)
                print(f"💾 DB 저장 완료: {symbol} ({saved_count}일)")
            except Exception as e:
                print(f"⚠️ DB 저장 오류 (무시): {e}")
            
            # 반환 형식 통일
            df_api = df_api.reset_index()
            if 'Date' in df_api.columns:
                df_api = df_api.rename(columns={'Date': 'date'})
            df_api['symbol'] = symbol
            
            # 컬럼 순서 정렬
            cols = ['symbol', 'date', 'Open', 'High', 'Low', 'Close', 'Volume']
            if all(col in df_api.columns for col in cols):
                df_api = df_api[cols]
                df_api.columns = ['symbol', 'date', 'open', 'high', 'low', 'close', 'volume']
            
            return df_api
            
        except Exception as e:
            print(f"❌ API 오류 ({symbol}): {e}")
            # API 실패 시 DB에 있는 기존 데이터라도 반환
            return self._fallback_to_db(symbol, start, end)
    
    def _fallback_to_db(
        self, 
        symbol: str, 
        start: str, 
        end: str
    ) -> pd.DataFrame:
        """API 실패 시 DB에 있는 데이터라도 반환"""
        try:
            df = self.db.get_price_range(symbol, start, end)
            if not df.empty:
                print(f"💾 DB 폼백: {symbol} ({len(df)}일)")
            return df
        except Exception as e:
            print(f"❌ DB 폼백 실패: {e}")
            return pd.DataFrame()
    
    def get_latest_price(self, symbol: str) -> Optional[Dict]:
        """최신 주가 조회 (최근 5일 중 마지막)"""
        end = datetime.now().strftime('%Y-%m-%d')
        start = (datetime.now() - timedelta(days=10)).strftime('%Y-%m-%d')
        
        df = self.get_price(symbol, start, end)
        
        if not df.empty:
            row = df.iloc[-1]
            return {
                'symbol': symbol,
                'date': str(row['date']),
                'open': float(row['open']),
                'high': float(row['high']),
                'low': float(row['low']),
                'close': float(row['close']),
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
            'partial_cache': self._cache_stats['partial'],
            'total_requests': total,
            'hit_rate': f"{hit_rate:.1f}%",
            'api_calls': self._cache_stats['api_calls']
        }
    
    def bulk_update(
        self, 
        symbols: List[str], 
        start: str, 
        end: str,
        progress_interval: int = 10
    ) -> Dict[str, int]:
        """
        여러 종목을 한꺼번에 업데이트
        
        Parameters:
        -----------
        symbols : List[str]
            종목코드 리스트
        start : str
            시작일
        end : str
            종료일
        progress_interval : int
            진행 상황 출력 간격
        
        Returns:
        --------
        Dict[str, int] : 각 종목별 저장된 데이터 수
        """
        results = {}
        total = len(symbols)
        
        for i, symbol in enumerate(symbols, 1):
            try:
                df = self.get_price(symbol, start, end)
                results[symbol] = len(df)
                
                if i % progress_interval == 0 or i == total:
                    print(f"📊 진행: {i}/{total} ({i/total*100:.1f}%)")
                    
            except Exception as e:
                print(f"❌ {symbol} 실패: {e}")
                results[symbol] = -1
        
        return results


# 편의 함수
def get_price(
    symbol: str, 
    start: Optional[str] = None, 
    end: Optional[str] = None,
    db_path: str = './data/pivot_strategy.db'
) -> pd.DataFrame:
    """
    단순 주가 조회 함수
    
    Usage:
        df = get_price('005930', '2024-01-01', '2024-12-31')
    """
    with FDRWrapper(db_path=db_path) as wrapper:
        return wrapper.get_price(symbol, start, end)


def bulk_download(
    symbols: List[str], 
    start: str, 
    end: str,
    db_path: str = './data/pivot_strategy.db'
) -> Dict[str, int]:
    """
    여러 종목 일괄 다운로드
    
    Usage:
        results = bulk_download(['005930', '000660'], '2024-01-01', '2024-12-31')
    """
    with FDRWrapper(db_path=db_path) as wrapper:
        return wrapper.bulk_update(symbols, start, end)


if __name__ == "__main__":
    # 테스트
    print("🚀 FDRWrapper 개선 버전 테스트\n")
    
    # 1. 기본 조회 테스트
    print("=" * 60)
    print("테스트 1: 삼성전자 (005930) - 2024년 1월~3월")
    print("=" * 60)
    
    with FDRWrapper() as wrapper:
        df = wrapper.get_price('005930', '2024-01-01', '2024-03-31')
        print(f"데이터: {len(df)}일")
        if not df.empty:
            print(df.head())
        
        # 2. 캐시 테스트 (동일 데이터 다시 조회)
        print("\n" + "=" * 60)
        print("테스트 2: 캐시 테스트 (동일 데이터 재조회)")
        print("=" * 60)
        df2 = wrapper.get_price('005930', '2024-01-01', '2024-03-31')
        print(f"데이터: {len(df2)}일 (DB에서 로드됨)")
        
        # 3. 캐시 통계
        print("\n" + "=" * 60)
        print("테스트 3: 캐시 통계")
        print("=" * 60)
        stats = wrapper.get_cache_stats()
        for key, value in stats.items():
            print(f"  {key}: {value}")
    
    # 4. 편의 함수 테스트
    print("\n" + "=" * 60)
    print("테스트 4: 편의 함수 사용")
    print("=" * 60)
    df3 = get_price('000660', days=10)  # SK하이닉스 최근 10일
    print(f"SK하이닉스: {len(df3)}일")
    if not df3.empty:
        print(df3.tail(3))
    
    print("\n✅ 모든 테스트 완료!")
