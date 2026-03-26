#!/usr/bin/env python3
"""
오늘 종가 데이터 DB 업데이트
"""

import FinanceDataReader as fdr
import pandas as pd
import sqlite3
from datetime import datetime
import time

def update_today_prices():
    today = '2026-03-26'
    
    print(f'📊 {today} 종목 가격정보 DB 구축')
    print('=' * 70)
    
    # 종목 리스트
    print('\\n1. 종목 리스트 로드...')
    ks = fdr.StockListing('KOSPI')
    q = fdr.StockListing('KOSDAQ')
    
    # 심볼 리스트
    kospi_codes = ks['Code'].tolist() if 'Code' in ks.columns else ks['Symbol'].tolist()
    kosdaq_codes = q['Code'].tolist() if 'Code' in q.columns else q['Symbol'].tolist()
    
    all_codes = kospi_codes + kosdaq_codes
    print(f'   KOSPI: {len(kospi_codes)}개')
    print(f'   KOSDAQ: {len(kosdaq_codes)}개')
    print(f'   총: {len(all_codes)}개')
    
    # DB 연결
    conn = sqlite3.connect('data/pivot_strategy.db')
    cursor = conn.cursor()
    
    # 데이터 수집
    print(f'\\n2. {today} 가격 데이터 수집 중...')
    print('   (약 10~15분 소요)')
    print('-' * 70)
    
    success_count = 0
    fail_count = 0
    inserted_count = 0
    
    for i, code in enumerate(all_codes, 1):
        try:
            # 데이터 수집
            df = fdr.DataReader(code, today, today)
            
            if len(df) == 0:
                fail_count += 1
                continue
            
            # DB 저장
            row = df.iloc[0]
            cursor.execute('''
                INSERT OR REPLACE INTO stock_prices 
                (symbol, date, open, high, low, close, volume)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (
                code,
                today,
                float(row['Open']),
                float(row['High']),
                float(row['Low']),
                float(row['Close']),
                int(row['Volume'])
            ))
            
            success_count += 1
            inserted_count += 1
            
            if i % 100 == 0:
                print(f'   진행: {i}/{len(all_codes)} (성공: {success_count}, 실패: {fail_count})')
                conn.commit()
            
            time.sleep(0.05)  # API rate limit
            
        except Exception as e:
            fail_count += 1
            if i % 100 == 0:
                print(f'   진행: {i}/{len(all_codes)} (성공: {success_count}, 실패: {fail_count})')
    
    conn.commit()
    conn.close()
    
    print('-' * 70)
    print(f'\\n✅ 완료!')
    print(f'   성공: {success_count}개')
    print(f'   실패: {fail_count}개')
    print(f'   DB 저장: {inserted_count}개')
    
    return success_count

if __name__ == '__main__':
    update_today_prices()
