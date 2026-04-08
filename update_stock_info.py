#!/usr/bin/env python3
"""
Stock Info Updater - 종목명 매핑 테이블 생성 및 업데이트
"""

import sys
sys.path.insert(0, '/root/.openclaw/workspace/strg')

import sqlite3
import pandas as pd
import FinanceDataReader as fdr
from datetime import datetime


def create_stock_info_table():
    """stock_info 테이블 생성"""
    conn = sqlite3.connect('data/level1_prices.db')
    cursor = conn.cursor()
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS stock_info (
            code TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            market TEXT,
            sector TEXT,
            industry TEXT,
            listing_date TEXT,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    conn.commit()
    conn.close()
    print("✅ stock_info 테이블 생성 완료")


def fetch_stock_listings():
    """KOSPI/KOSDAQ 종목 목록 수집"""
    print("📥 KOSPI 종목 수집 중...")
    kospi = fdr.StockListing('KOSPI')
    kospi['market'] = 'KOSPI'
    
    print("📥 KOSDAQ 종목 수집 중...")
    kosdaq = fdr.StockListing('KOSDAQ')
    kosdaq['market'] = 'KOSDAQ'
    
    # 컬럼명 통일
    kospi = kospi.rename(columns={
        'Code': 'code',
        'Name': 'name',
        'Sector': 'sector',
        'Industry': 'industry',
        'ListingDate': 'listing_date'
    })
    
    kosdaq = kosdaq.rename(columns={
        'Code': 'code',
        'Name': 'name',
        'Sector': 'sector',
        'Industry': 'industry',
        'ListingDate': 'listing_date'
    })
    
    # 필요한 컬럼만 선택
    cols = ['code', 'name', 'market', 'sector', 'industry', 'listing_date']
    kospi = kospi[[c for c in cols if c in kospi.columns]]
    kosdaq = kosdaq[[c for c in cols if c in kosdaq.columns]]
    
    all_stocks = pd.concat([kospi, kosdaq], ignore_index=True)
    print(f"   KOSPI: {len(kospi)}개, KOSDAQ: {len(kosdaq)}개, 총 {len(all_stocks)}개")
    
    return all_stocks


def update_stock_info():
    """stock_info 테이블 업데이트"""
    print("=" * 70)
    print("🔄 Stock Info 업데이트 시작")
    print("=" * 70)
    
    # 테이블 생성
    create_stock_info_table()
    
    # 종목 목록 수집
    stocks_df = fetch_stock_listings()
    
    # DB 연결
    conn = sqlite3.connect('data/level1_prices.db')
    cursor = conn.cursor()
    
    # 기존 데이터 확인
    cursor.execute('SELECT COUNT(*) FROM stock_info')
    existing_count = cursor.fetchone()[0]
    print(f"\n📊 기존 데이터: {existing_count}개")
    
    # UPSERT (INSERT OR REPLACE)
    inserted = 0
    for _, row in stocks_df.iterrows():
        cursor.execute('''
            INSERT OR REPLACE INTO stock_info 
            (code, name, market, sector, industry, listing_date, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (
            row.get('code'),
            row.get('name'),
            row.get('market'),
            row.get('sector'),
            row.get('industry'),
            row.get('listing_date'),
            datetime.now().isoformat()
        ))
        inserted += 1
        
        if inserted % 500 == 0:
            print(f"   진행: {inserted}/{len(stocks_df)}개")
    
    conn.commit()
    
    # 최종 확인
    cursor.execute('SELECT COUNT(*) FROM stock_info')
    final_count = cursor.fetchone()[0]
    conn.close()
    
    print(f"\n✅ 업데이트 완료: {inserted}개 종목")
    print(f"📊 최종 stock_info: {final_count}개")
    print("=" * 70)


def update_price_data_names():
    """price_data 테이블의 종목명 업데이트"""
    print("\n" + "=" * 70)
    print("🔄 price_data 종목명 업데이트")
    print("=" * 70)
    
    conn = sqlite3.connect('data/level1_prices.db')
    cursor = conn.cursor()
    
    # stock_info에서 종목명 가져오기
    stock_info = pd.read_sql_query('SELECT code, name FROM stock_info', conn)
    name_map = dict(zip(stock_info['code'], stock_info['name']))
    
    print(f"   매핑 테이블: {len(name_map)}개 종목")
    
    # price_data에서 잘못된 종목명 확인
    cursor.execute('''
        SELECT DISTINCT code, name FROM price_data 
        WHERE name IS NULL OR name = '' OR name = 'Stock' OR name = 'Unknown'
    ''')
    invalid_names = cursor.fetchall()
    
    print(f"   잘못된 종목명: {len(invalid_names)}개")
    
    # 업데이트
    updated = 0
    for code, old_name in invalid_names:
        if code in name_map:
            correct_name = name_map[code]
            cursor.execute(
                'UPDATE price_data SET name = ? WHERE code = ?',
                (correct_name, code)
            )
            updated += cursor.rowcount
            if updated <= 5:  # 샘플 출력
                print(f"   {code}: '{old_name}' → '{correct_name}'")
    
    conn.commit()
    conn.close()
    
    print(f"\n✅ 업데이트 완료: {updated}개 행")
    print("=" * 70)


def verify_updates():
    """업데이트 결과 검증"""
    print("\n" + "=" * 70)
    print("📊 업데이트 검증")
    print("=" * 70)
    
    conn = sqlite3.connect('data/level1_prices.db')
    
    # 문제 종목 확인
    df = pd.read_sql_query('''
        SELECT DISTINCT code, name FROM price_data 
        WHERE code IN ('131890', '272910', '038880')
    ''', conn)
    
    print("\n검증 대상 종목:")
    for _, row in df.iterrows():
        code = row['code']
        name = row['name']
        
        # stock_info에서 정확한 이름
        info_df = pd.read_sql_query(
            f"SELECT name FROM stock_info WHERE code = '{code}'",
            conn
        )
        correct_name = info_df['name'].iloc[0] if len(info_df) > 0 else 'N/A'
        
        status = "✅" if name == correct_name else "❌"
        print(f"   {status} {code}: '{name}' (정확한 이름: '{correct_name}')")
    
    # 전체 통계
    total = pd.read_sql_query('SELECT COUNT(DISTINCT code) FROM price_data', conn).iloc[0, 0]
    valid = pd.read_sql_query('''
        SELECT COUNT(DISTINCT code) FROM price_data 
        WHERE name IS NOT NULL AND name != '' AND name != 'Stock' AND name != 'Unknown'
    ''', conn).iloc[0, 0]
    
    print(f"\n📈 전체 현황:")
    print(f"   총 종목: {total}개")
    print(f"   정상 종목명: {valid}개 ({valid/total*100:.1f}%)")
    print(f"   수정 필요: {total-valid}개")
    
    conn.close()
    print("=" * 70)


def main():
    """메인 실행"""
    # stock_info 업데이트
    update_stock_info()
    
    # price_data 종목명 업데이트
    update_price_data_names()
    
    # 검증
    verify_updates()
    
    print("\n✅ 모든 작업 완료!")


if __name__ == '__main__':
    main()
