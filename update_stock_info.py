#!/usr/bin/env python3
"""
Stock Info Updater - FDR 최신 종목 리스트로 DB 업데이트
증권 종목코드 기준 (6자리 숫자)
"""

import sqlite3
import FinanceDataReader as fdr
import pandas as pd
from datetime import datetime


def update_stock_info():
    """stock_info 테이블을 FDR 최신 데이터로 업데이트"""
    
    print('='*70)
    print('🔄 Stock Info 업데이트 시작')
    print('='*70)
    
    # 1. FDR에서 최신 종목 리스트 가져오기
    print('\n📥 최신 종목 리스트 다운로드...')
    kospi = fdr.StockListing('KOSPI')
    kosdaq = fdr.StockListing('KOSDAQ')
    
    # 필요한 컬럼만 선택
    kospi_df = kospi[['Code', 'Name', 'Market']].copy()
    kospi_df['Market'] = 'KOSPI'
    
    kosdaq_df = kosdaq[['Code', 'Name', 'Market']].copy()
    kosdaq_df['Market'] = 'KOSDAQ'
    
    # 합치기
    latest_df = pd.concat([kospi_df, kosdaq_df], ignore_index=True)
    latest_df.columns = ['symbol', 'name', 'market']
    
    print(f'   KOSPI: {len(kospi_df)}개')
    print(f'   KOSDAQ: {len(kosdaq_df)}개')
    print(f'   총: {len(latest_df)}개')
    
    # 2. DB 연결
    conn = sqlite3.connect('data/pivot_strategy.db')
    cursor = conn.cursor()
    
    # 3. 기존 데이터 백업
    print('\n💾 기존 데이터 백업...')
    cursor.execute('CREATE TABLE IF NOT EXISTS stock_info_backup AS SELECT * FROM stock_info')
    cursor.execute('SELECT COUNT(*) FROM stock_info_backup')
    backup_count = cursor.fetchone()[0]
    print(f'   백업 완료: {backup_count}개')
    
    # 4. 새로운 테이블 구조 생성
    print('\n🔧 테이블 재생성...')
    cursor.execute('DROP TABLE IF EXISTS stock_info_new')
    cursor.execute('''
        CREATE TABLE stock_info_new (
            symbol TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            market TEXT,
            sector TEXT,
            industry TEXT,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # 5. 새 데이터 삽입
    print('\n📊 새 데이터 삽입...')
    inserted = 0
    for _, row in latest_df.iterrows():
        try:
            cursor.execute('''
                INSERT INTO stock_info_new (symbol, name, market)
                VALUES (?, ?, ?)
            ''', (row['symbol'], row['name'], row['market']))
            inserted += 1
        except Exception as e:
            print(f'   ⚠️ 삽입 오류 {row["symbol"]}: {e}')
    
    conn.commit()
    print(f'   삽입 완료: {inserted}개')
    
    # 6. 기존 테이블 교체
    print('\n🔄 테이블 교체...')
    cursor.execute('DROP TABLE IF EXISTS stock_info')
    cursor.execute('ALTER TABLE stock_info_new RENAME TO stock_info')
    conn.commit()
    
    # 7. 검증
    print('\n✅ 검증:')
    cursor.execute('SELECT COUNT(*) FROM stock_info')
    new_count = cursor.fetchone()[0]
    cursor.execute('SELECT market, COUNT(*) FROM stock_info GROUP BY market')
    market_dist = cursor.fetchall()
    
    print(f'   새 종목 수: {new_count}개')
    print('   시장별 분포:')
    for market, count in market_dist:
        print(f'     - {market}: {count}개')
    
    # 8. 한국알콜 확인
    print('\n📋 한국알콜 확인:')
    cursor.execute("SELECT symbol, name, market FROM stock_info WHERE name = '한국알콜'")
    rows = cursor.fetchall()
    if rows:
        for r in rows:
            print(f'   {r[0]} - {r[1]} ({r[2]})')
    else:
        print('   ⚠️ 한국알콜 없음')
    
    conn.close()
    print('\n' + '='*70)
    print('✅ 업데이트 완료!')
    print('='*70)
    
    return new_count


if __name__ == '__main__':
    count = update_stock_info()
