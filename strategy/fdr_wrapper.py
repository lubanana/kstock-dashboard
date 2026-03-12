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
import FinanceDataReader as fdr_module
from datetime import datetime, timedelta
from typing import Optional, List, Dict
from local_db import LocalDB


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
    
    def _get_cache_key(self, symbol: str, start_date: str, end_date: str) -> str:
        """캐시 키 생성"""
        return f"{symbol}_{start_date}_{end_date}"
    
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
        pd.DataFrame : 주가 데이터 (open, high, low, close, volume)
        """
        # 기본 날짜 설정
        if end_date is None:
            end_date = datetime.now().strftime('%Y-%m-%d')
        if start_date is None:
            start_date = (datetime.now() - timedelta(days=365)).strftime('%Y-%m-%d')
        
        # 캐시 확인 (force_update가 아닐 때)
        if not force_update:
            cached_data = self.db.get_prices(symbol, start_date, end_date)
            if not cached_data.empty:
                # 요청한 기간 전체가 캐시되어 있는지 확인
                if len(cached_data) >= self._estimate_trading_days(start_date, end_date) * 0.9:
                    self._cache_stats['hit'] += 1
                    print(f"💾 캐시 히트: {symbol} ({len(cached_data)}일)")
                    return cached_data
        
        # API 호출
        self._cache_stats['miss'] += 1
        self._cache_stats['api_calls'] += 1
        print(f"🌐 API 호출: {symbol} ({start_date} ~ {end_date})")
        
        try:
            df = fdr_module.DataReader(symbol, start_date, end_date)
            
            if df.empty:
                print(f"⚠️ 데이터 없음: {symbol}")
                return pd.DataFrame()
            
            # DB에 저장
            self.db.save_prices(df, symbol)
            print(f"💾 DB 저장 완료: {symbol} ({len(df)}일)")
            
            return df
            
        except Exception as e:
            print(f"❌ API 오류 ({symbol}): {e}")
            # 부분 캐시라도 있으면 반환
            cached_data = self.db.get_prices(symbol, start_date, end_date)
            if not cached_data.empty:
                print(f"⚠️ 부분 캐시 반환: {symbol} ({len(cached_data)}일)")
                return cached_data
            return pd.DataFrame()
    
    def get_prices_batch(
        self, 
        symbols: List[str], 
        start_date: str = None, 
        end_date: str = None,
        show_progress: bool = True
    ) -> Dict[str, pd.DataFrame]:
        """
        여러 종목 주가 데이터 일괄 조회
        
        Parameters:
        -----------
        symbols : List[str]
            종목코드 리스트
        start_date : str
            시작일
        end_date : str
            종료일
        show_progress : bool
            진행상황 출력 여부
        
        Returns:
        --------
        Dict[str, pd.DataFrame] : {symbol: DataFrame}
        """
        results = {}
        total = len(symbols)
        
        for i, symbol in enumerate(symbols):
            if show_progress:
                print(f"\n[{i+1}/{total}] {symbol} 조회 중...")
            
            df = self.get_price(symbol, start_date, end_date)
            if not df.empty:
                results[symbol] = df
        
        if show_progress:
            print(f"\n✅ 완료: {len(results)}/{total} 종목 조회")
        
        return results
    
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
                # 컬럼명이 소문자일 수도 있고 대문자일 수도 있음
                col_map = {col.lower(): col for col in df.columns}
                return {
                    'symbol': symbol,
                    'date': today,
                    'open': row[col_map.get('open', 'Open')],
                    'high': row[col_map.get('high', 'High')],
                    'low': row[col_map.get('low', 'Low')],
                    'close': row[col_map.get('close', 'Close')],
                    'volume': int(row[col_map.get('volume', 'Volume')])
                }
        
        # 없으면 API 호출 (최근 5일)
        start = (datetime.now() - timedelta(days=5)).strftime('%Y-%m-%d')
        df = self.get_price(symbol, start, today)
        
        if not df.empty:
            row = df.iloc[-1]
            # 컬럼명이 소문자일 수도 있고 대문자일 수도 있음
            col_map = {col.lower(): col for col in df.columns}
            return {
                'symbol': symbol,
                'date': row.name.strftime('%Y-%m-%d') if hasattr(row.name, 'strftime') else str(row.name),
                'open': row[col_map.get('open', 'Open')],
                'high': row[col_map.get('high', 'High')],
                'low': row[col_map.get('low', 'Low')],
                'close': row[col_map.get('close', 'Close')],
                'volume': int(row[col_map.get('volume', 'Volume')])
            }
        
        return None
    
    def update_cache(self, symbol: str, days: int = 30) -> bool:
        """
        특정 종목 캐시 업데이트
        
        Parameters:
        -----------
        symbol : str
            종목코드
        days : int
            업데이트할 일수 (최근 N일)
        
        Returns:
        --------
        bool : 성공 여부
        """
        end_date = datetime.now().strftime('%Y-%m-%d')
        start_date = (datetime.now() - timedelta(days=days)).strftime('%Y-%m-%d')
        
        try:
            df = fdr_module.DataReader(symbol, start_date, end_date)
            if not df.empty:
                self.db.save_prices(df, symbol)
                return True
        except Exception as e:
            print(f"❌ 업데이트 실패 ({symbol}): {e}")
        
        return False
    
    def get_cache_stats(self) -> Dict:
        """
        캐시 통계 조회
        """
        total = self._cache_stats['hit'] + self._cache_stats['miss']
        hit_rate = (self._cache_stats['hit'] / total * 100) if total > 0 else 0
        
        return {
            'cache_hit': self._cache_stats['hit'],
            'cache_miss': self._cache_stats['miss'],
            'total_requests': total,
            'hit_rate': f"{hit_rate:.1f}%",
            'api_calls': self._cache_stats['api_calls']
        }
    
    def reset_cache_stats(self):
        """캐시 통계 초기화"""
        self._cache_stats = {'hit': 0, 'miss': 0, 'api_calls': 0}
    
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
    with FDRWrapper() as wrapper:
        return wrapper.get_price(symbol, start_date, end_date)


def get_latest(symbol: str) -> Optional[Dict]:
    """
    최신 주가 조회 함수
    """
    with FDRWrapper() as wrapper:
        return wrapper.get_latest_price(symbol)


if __name__ == "__main__":
    # 테스트
    print("🚀 FDRWrapper 테스트\n")
    
    with FDRWrapper() as fdr:
        # 1. 단일 종목 조회 (API 호출 + 캐시)
        print("=" * 50)
        print("테스트 1: 삼성전자 조회 (첫 호출 - API)")
        print("=" * 50)
        df1 = fdr.get_price('005930', '2024-01-01', '2024-01-31')
        print(f"데이터: {len(df1)}일")
        print(df1.head(3))
        
        # 2. 캐시된 데이터 조회
        print("\n" + "=" * 50)
        print("테스트 2: 삼성전자 재조회 (캐시 히트)")
        print("=" * 50)
        df2 = fdr.get_price('005930', '2024-01-01', '2024-01-31')
        print(f"데이터: {len(df2)}일")
        
        # 3. 최신 주가 조회
        print("\n" + "=" * 50)
        print("테스트 3: 최신 주가 조회")
        print("=" * 50)
        latest = fdr.get_latest_price('005930')
        print(latest)
        
        # 4. 캐시 통계
        print("\n" + "=" * 50)
        print("캐시 통계")
        print("=" * 50)
        stats = fdr.get_cache_stats()
        for key, value in stats.items():
            print(f"  {key}: {value}")
    
    print("\n✅ 테스트 완료!")
