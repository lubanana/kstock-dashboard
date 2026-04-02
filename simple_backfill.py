#!/usr/bin/env python3
"""
간소화된 level1_prices.db 역사 데이터 백필
pivot_strategy.db에서 직접 데이터 마이그레이션
"""

import sys
sys.path.insert(0, '/root/.openclaw/workspace/strg')

import sqlite3
import pandas as pd
from datetime import datetime


def simple_migrate():
    """간단한 마이그레이션"""
    print("=" * 70)
    print("🔄 level1_prices.db 간단 마이그레이션")
    print("=" * 70)
    
    src = sqlite3.connect('data/pivot_strategy.db')
    dst = sqlite3.connect('data/level1_prices.db')
    
    # 대상 테이블 비우기
    print("\n1. 기존 데이터 정리...")
    dst.execute("DELETE FROM price_data")
    dst.commit()
    
    # 소스 데이터 배치 조회 및 삽입
    print("2. 데이터 마이그레이션...")
    
    cursor = src.cursor()
    cursor.execute("SELECT COUNT(*) FROM stock_prices")
    total_rows = cursor.fetchone()[0]
    print(f"   소스 데이터: {total_rows:,} rows")
    
    # 배치 처리
    batch_size = 100000
    offset = 0
    inserted = 0
    
    while offset < total_rows:
        query = f"""
            SELECT 
                symbol as code,
                date,
                Open as open,
                High as high,
                Low as low,
                Close as close,
                Volume as volume
            FROM stock_prices
            LIMIT {batch_size} OFFSET {offset}
        """
        
        df = pd.read_sql_query(query, src)
        
        if df.empty:
            break
        
        # 추가 컬럼
        df['name'] = 'Stock'
        df['market'] = 'KOSPI'
        df['change_pct'] = None
        df['ma5'] = None
        df['ma20'] = None
        df['ma60'] = None
        df['rsi'] = None
        df['macd'] = None
        df['score'] = 50
        df['recommendation'] = 'HOLD'
        df['status'] = 'active'
        df['updated_at'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        # 저장
        df.to_sql('price_data', dst, if_exists='append', index=False)
        inserted += len(df)
        
        print(f"   {inserted:,} / {total_rows:,} rows ({inserted/total_rows*100:.1f}%)")
        
        offset += batch_size
    
    # 인덱스 생성
    print("3. 인덱스 생성...")
    dst.execute("CREATE INDEX IF NOT EXISTS idx_price_code ON price_data(code)")
    dst.execute("CREATE INDEX IF NOT EXISTS idx_price_date ON price_data(date)")
    dst.execute("CREATE INDEX IF NOT EXISTS idx_price_code_date ON price_data(code, date)")
    dst.commit()
    
    # 결과 확인
    print("\n4. 결과 확인...")
    df_check = pd.read_sql_query(
        "SELECT COUNT(*) as rows, COUNT(DISTINCT code) as symbols, MIN(date) as start, MAX(date) as end FROM price_data",
        dst
    )
    print(df_check.to_string(index=False))
    
    src.close()
    dst.close()
    
    print(f"\n✅ 마이그레이션 완료: {inserted:,} rows")


if __name__ == '__main__':
    simple_migrate()
