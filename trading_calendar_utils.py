#!/usr/bin/env python3
"""
Trading Calendar Utilities for Scanners
=========================================
스캐너용 거래일 유틸리티

스캐너에서 사용 예시:
    from trading_calendar_utils import get_trading_calendar_manager, adjust_to_trading_day
    
    # 거래일 조정
    adjusted_date = adjust_to_trading_day('2026-04-13', direction='previous')
"""

from datetime import datetime
from typing import Optional
from trading_calendar import TradingCalendarManager

# 전역 인스턴스 (lazy initialization)
_manager: Optional[TradingCalendarManager] = None


def get_trading_calendar_manager(db_path: str = 'data/level1_prices.db') -> TradingCalendarManager:
    """
    TradingCalendarManager 싱글톤 인스턴스 반환
    
    Args:
        db_path: 데이터베이스 경로
    
    Returns:
        TradingCalendarManager 인스턴스
    """
    global _manager
    if _manager is None:
        _manager = TradingCalendarManager(db_path=db_path)
        _manager.connect()
    return _manager


def adjust_to_trading_day(date: str, direction: str = 'previous', 
                          db_path: str = 'data/level1_prices.db') -> Optional[str]:
    """
    특정일을 거래일로 조정 (스캐너용 간편 함수)
    
    Args:
        date: 기준일 (YYYY-MM-DD)
        direction: 'previous' (이전 거래일) 또는 'next' (다음 거래일)
        db_path: 데이터베이스 경로
    
    Returns:
        조정된 거래일 (YYYY-MM-DD) 또는 None
    
    Example:
        >>> adjust_to_trading_day('2026-04-13', 'previous')
        '2026-04-13'  # 일요일이 아니므로 그대로 반환
        
        >>> adjust_to_trading_day('2026-04-12', 'previous')
        '2026-04-10'  # 일요일 → 금요일
    """
    try:
        manager = get_trading_calendar_manager(db_path)
        return manager.adjust_to_trading_day(date, direction)
    except Exception as e:
        # DB 오류 시 기본 로직 사용 (주말만 체크)
        dt = datetime.strptime(date, '%Y-%m-%d')
        weekday = dt.weekday()
        
        if weekday < 5:  # 월~금
            return date
        
        # 주말이면 조정
        if direction == 'previous':
            # 이전 금요일
            days_back = weekday - 4  # 토(5)→1, 일(6)→2
            adjusted = dt - __import__('datetime').timedelta(days=days_back)
            return adjusted.strftime('%Y-%m-%d')
        else:
            # 다음 월요일
            days_forward = 7 - weekday  # 토(5)→2, 일(6)→1
            adjusted = dt + __import__('datetime').timedelta(days=days_forward)
            return adjusted.strftime('%Y-%m-%d')


def is_trading_day(date: str, db_path: str = 'data/level1_prices.db') -> bool:
    """
    특정일이 거래일인지 확인
    
    Args:
        date: 확인할 날짜 (YYYY-MM-DD)
        db_path: 데이터베이스 경로
    
    Returns:
        True if 거래일, False if 휴장일
    """
    try:
        manager = get_trading_calendar_manager(db_path)
        is_valid, _ = manager.validate_date(date)
        return is_valid
    except Exception:
        # DB 오류 시 주말만 체크
        dt = datetime.strptime(date, '%Y-%m-%d')
        return dt.weekday() < 5


def get_previous_trading_day(date: str, db_path: str = 'data/level1_prices.db') -> Optional[str]:
    """
    이전 거래일 반환
    
    Args:
        date: 기준일 (YYYY-MM-DD)
        db_path: 데이터베이스 경로
    
    Returns:
        이전 거래일 (YYYY-MM-DD)
    """
    manager = get_trading_calendar_manager(db_path)
    return manager.get_previous_trading_day(date)


def get_next_trading_day(date: str, db_path: str = 'data/level1_prices.db') -> Optional[str]:
    """
    다음 거래일 반환
    
    Args:
        date: 기준일 (YYYY-MM-DD)
        db_path: 데이터베이스 경로
    
    Returns:
        다음 거래일 (YYYY-MM-DD)
    """
    manager = get_trading_calendar_manager(db_path)
    return manager.get_next_trading_day(date)


def count_trading_days(start_date: str, end_date: str, 
                       db_path: str = 'data/level1_prices.db') -> int:
    """
    특정 기간의 거래일 수 계산
    
    Args:
        start_date: 시작일 (YYYY-MM-DD)
        end_date: 종료일 (YYYY-MM-DD)
        db_path: 데이터베이스 경로
    
    Returns:
        거래일 수
    """
    manager = get_trading_calendar_manager(db_path)
    return manager.count_trading_days(start_date, end_date)


def add_trading_days(date: str, days: int, db_path: str = 'data/level1_prices.db') -> Optional[str]:
    """
    n거래일 후/전 날짜 계산
    
    Args:
        date: 기준일 (YYYY-MM-DD)
        days: +n (n거래일 후), -n (n거래일 전)
        db_path: 데이터베이스 경로
    
    Returns:
        계산된 거래일
    """
    manager = get_trading_calendar_manager(db_path)
    return manager.add_trading_days(date, days)


def ensure_trading_day_in_db(date: str, db_path: str = 'data/level1_prices.db') -> str:
    """
    스캐너용: 입력된 날짜가 거래일이 아니면 DB에서 찾아 조정
    
    이 함수는 스캐너의 --date 인자 처리에 사용됩니다.
    
    Args:
        date: 입력된 날짜 (YYYY-MM-DD)
        db_path: 데이터베이스 경로
    
    Returns:
        조정된 거래일 (YYYY-MM-DD)
    
    Example:
        # 스캐너에서 사용
        scan_date = ensure_trading_day_in_db(args.date)
    """
    manager = get_trading_calendar_manager(db_path)
    
    # DB에 해당 날짜가 있는지 확인
    query = "SELECT is_trading_day FROM trading_calendar WHERE date = ?"
    import pandas as pd
    df = pd.read_sql_query(query, manager._conn, params=(date,))
    
    if df.empty:
        # DB에 없으면 거래일 테이블이 구축되지 않은 것
        # 기본 로직으로 처리
        adjusted = adjust_to_trading_day(date, 'previous', db_path)
        print(f"⚠️  {date}은(는) 캘린더에 없습니다. {adjusted}로 조정합니다.")
        return adjusted or date
    
    if df['is_trading_day'].iloc[0] == 1:
        return date
    
    # 거래일이 아니면 이전 거래일 찾기
    previous = manager.get_previous_trading_day(date)
    if previous:
        # 휴장일 정보 가져오기
        query = "SELECT holiday_name FROM trading_calendar WHERE date = ?"
        holiday_df = pd.read_sql_query(query, manager._conn, params=(date,))
        holiday_name = holiday_df['holiday_name'].iloc[0] if not holiday_df.empty else None
        
        if holiday_name:
            print(f"⚠️  {date}은(는) 휴장일입니다: {holiday_name}")
        else:
            print(f"⚠️  {date}은(는) 거래일이 아닙니다.")
        print(f"📅 가장 가까운 이전 거래일({previous})로 스캔을 진행합니다.")
        return previous
    
    # 이전 거래일이 없으면 다음 거래일
    next_day = manager.get_next_trading_day(date)
    if next_day:
        print(f"⚠️  {date}은(는) 거래일이 아닙니다.")
        print(f"📅 가장 가까운 다음 거래일({next_day})로 스캔을 진행합니다.")
        return next_day
    
    return date


# 테스트
if __name__ == '__main__':
    import sys
    
    # 테스트 실행
    print("📅 Trading Calendar Utils Test")
    print("=" * 50)
    
    test_dates = [
        '2026-04-11',  # 토요일
        '2026-04-12',  # 일요일
        '2026-04-13',  # 월요일 (거래일)
        '2026-05-05',  # 어린이날
    ]
    
    for date in test_dates:
        adjusted = adjust_to_trading_day(date, 'previous')
        valid = is_trading_day(date)
        status = "✅ 거래일" if valid else "❌ 휴장일"
        print(f"{date}: {status} → 조정: {adjusted}")
    
    print("\n" + "=" * 50)
    
    # ensure_trading_day_in_db 테스트
    print("\nensure_trading_day_in_db 테스트:")
    result = ensure_trading_day_in_db('2026-04-13')
    print(f"   입력: 2026-04-13 → 결과: {result}")
    
    result = ensure_trading_day_in_db('2026-04-12')
    print(f"   입력: 2026-04-12 → 결과: {result}")
