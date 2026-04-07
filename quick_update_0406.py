#!/usr/bin/env python3
"""
Quick daily update - 2026-04-06
"""
import sqlite3
import FinanceDataReader as fdr
import pandas as pd
from datetime import datetime
import sys

DB_PATH = 'data/level1_prices.db'
DATE = '2026-04-06'

def get_all_codes():
    """KOSPI/KOSDAQ 종목 코드"""
    try:
        kospi = fdr.StockListing('KOSPI')
        kosdaq = fdr.StockListing('KOSDAQ')
        codes = list(kospi['Code']) + list(kosdaq['Code'])
        return [c for c in codes if str(c).isdigit()]
    except Exception as e:
        print(f"종목 목록 로드 실패: {e}")
        return []

def update_daily():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    codes = get_all_codes()
    print(f"총 {len(codes)}개 종목 처리 중...")
    
    updated = 0
    failed = 0
    
    for i, code in enumerate(codes, 1):
        try:
            # 이미 있는지 확인
            cursor.execute("SELECT 1 FROM price_data WHERE code=? AND date=?", (code, DATE))
            if cursor.fetchone():
                continue
            
            # 데이터 가져오기
            df = fdr.DataReader(code, DATE, DATE)
            if df.empty:
                failed += 1
                continue
            
            row = df.iloc[0]
            name = code  # 이름은 나중에 업데이트
            
            cursor.execute("""
                INSERT INTO price_data 
                (code, name, date, open, high, low, close, volume, change)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                code, name, DATE,
                float(row['Open']), float(row['High']), float(row['Low']),
                float(row['Close']), int(row['Volume']), float(row.get('Change', 0))
            ))
            
            updated += 1
            
            if i % 100 == 0:
                print(f"  {i}/{len(codes)} - 업데이트: {updated}, 실패: {failed}")
                conn.commit()
                
        except Exception as e:
            failed += 1
            if i % 100 == 0:
                print(f"  {i}/{len(codes)} - 에러: {e}")
    
    conn.commit()
    conn.close()
    
    print(f"\n=== 완료 ===")
    print(f"업데이트: {updated}개")
    print(f"실패: {failed}개")

if __name__ == '__main__':
    update_daily()
