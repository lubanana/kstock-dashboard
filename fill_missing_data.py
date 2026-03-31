#!/usr/bin/env python3
"""
누락된 주식 데이터 구축 스크립트
"""

import sqlite3
import pandas as pd
from datetime import datetime, timedelta
import FinanceDataReader as fdr
import sys

sys.path.insert(0, '/root/.openclaw/workspace/strg')

def get_missing_dates():
    """누락된 실제 거래일 확인"""
    db_path = '/root/.openclaw/workspace/strg/data/pivot_strategy.db'
    conn = sqlite3.connect(db_path)
    
    # 모든 날짜 확인
    all_dates = conn.execute('SELECT DISTINCT date FROM stock_prices ORDER BY date').fetchall()
    all_dates = set(d[0] for d in all_dates)
    
    date_range = conn.execute('SELECT MIN(date), MAX(date) FROM stock_prices').fetchone()
    start_date = datetime.strptime(date_range[0], '%Y-%m-%d')
    end_date = datetime.strptime(date_range[1], '%Y-%m-%d')
    
    # 한국 공휴일 (2025-2026)
    holidays = {
        '2025-01-01', '2025-01-28', '2025-01-29', '2025-01-30',
        '2025-03-01', '2025-05-01', '2025-05-05', '2025-05-06',
        '2025-06-03', '2025-06-06', '2025-08-15',
        '2025-10-01', '2025-10-03', '2025-10-06', '2025-10-07', '2025-10-08', '2025-10-09',
        '2025-12-25', '2025-12-31',
        '2026-01-01', '2026-02-16', '2026-02-17'
    }
    
    # 실제 거래일 중 누락된 날짜
    expected = []
    current = start_date
    while current <= end_date:
        if current.weekday() < 5:
            date_str = current.strftime('%Y-%m-%d')
            if date_str not in holidays and date_str not in all_dates:
                expected.append(date_str)
        current += timedelta(days=1)
    
    conn.close()
    return expected


def fetch_and_save_missing_data(missing_dates):
    """누락된 날짜 데이터 구축"""
    db_path = '/root/.openclaw/workspace/strg/data/pivot_strategy.db'
    conn = sqlite3.connect(db_path)
    
    # 종목 목록 가져오기
    symbols = conn.execute('SELECT symbol FROM stock_info').fetchall()
    symbols = [s[0] for s in symbols]
    
    print(f"총 {len(symbols)}개 종목, {len(missing_dates)}일 데이터 구축")
    
    for target_date in missing_dates:
        print(f"\n📅 {target_date} 데이터 구축 중...")
        
        # 해당 날짜 포함한 범위로 데이터 조회
        start = (datetime.strptime(target_date, '%Y-%m-%d') - timedelta(days=5)).strftime('%Y-%m-%d')
        end = (datetime.strptime(target_date, '%Y-%m-%d') + timedelta(days=5)).strftime('%Y-%m-%d')
        
        records_added = 0
        
        for i, symbol in enumerate(symbols):
            if i % 500 == 0:
                print(f"  [{i}/{len(symbols)}] {symbol}...", end='\r')
            
            try:
                df = fdr.DataReader(symbol, start, end)
                if df is None or len(df) == 0:
                    continue
                
                # 해당 날짜 데이터만 필터
                df = df[df.index.strftime('%Y-%m-%d') == target_date]
                if len(df) == 0:
                    continue
                
                row = df.iloc[0]
                conn.execute('''
                    INSERT OR REPLACE INTO stock_prices 
                    (symbol, date, open, high, low, close, volume, change_rate)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    symbol, target_date,
                    float(row['Open']), float(row['High']), float(row['Low']),
                    float(row['Close']), int(row['Volume']),
                    float(row.get('Change', 0)) if 'Change' in row else None
                ))
                records_added += 1
                
            except Exception as e:
                continue
        
        conn.commit()
        print(f"  ✓ {target_date}: {records_added}건 추가")
    
    conn.close()
    print("\n✅ 데이터 구축 완료!")


def verify_data_completeness():
    """데이터 완전성 검증"""
    db_path = '/root/.openclaw/workspace/strg/data/pivot_strategy.db'
    conn = sqlite3.connect(db_path)
    
    print("\n=== 데이터 완전성 검증 ===")
    
    # 총 건수
    total = conn.execute('SELECT COUNT(*) FROM stock_prices').fetchone()[0]
    print(f"총 데이터: {total:,}건")
    
    # 날짜별 건수 (최근 10일)
    recent = conn.execute('''
        SELECT date, COUNT(*) as cnt 
        FROM stock_prices 
        GROUP BY date 
        ORDER BY date DESC 
        LIMIT 10
    ''').fetchall()
    
    print("\n최근 10일 데이터 현황:")
    for d, c in recent:
        print(f"  {d}: {c:,}건")
    
    conn.close()


if __name__ == '__main__':
    print("="*60)
    print("📊 누락된 주식 데이터 구축")
    print("="*60)
    
    missing = get_missing_dates()
    
    if missing:
        print(f"\n누락된 거래일: {len(missing)}일")
        for d in missing:
            print(f"  - {d}")
        
        fetch_and_save_missing_data(missing)
        verify_data_completeness()
    else:
        print("\n✅ 누락된 데이터 없음!")
        verify_data_completeness()
