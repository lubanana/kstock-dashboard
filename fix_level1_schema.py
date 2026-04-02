#!/usr/bin/env python3
"""
level1_prices.db 테이블 구조 수정
잘못된 PRIMARY KEY (code만) → 올바른 복합키 (code, date)
"""

import sqlite3
from datetime import datetime


def fix_table_structure():
    """테이블 구조 수정"""
    print("=" * 70)
    print("🔧 level1_prices.db 테이블 구조 수정")
    print("=" * 70)
    
    conn = sqlite3.connect('data/level1_prices.db')
    cursor = conn.cursor()
    
    # 1. 기존 테이블 백업
    print("\n1. 기존 테이블 백업...")
    cursor.execute("ALTER TABLE price_data RENAME TO price_data_backup")
    conn.commit()
    print("   ✓ price_data → price_data_backup")
    
    # 2. 새 테이블 생성 (올바른 구조)
    print("\n2. 새 테이블 생성...")
    cursor.execute('''
        CREATE TABLE price_data (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            code TEXT NOT NULL,
            name TEXT,
            market TEXT,
            date TEXT NOT NULL,
            open REAL,
            high REAL,
            low REAL,
            close REAL,
            volume INTEGER,
            change_pct REAL,
            ma5 REAL,
            ma20 REAL,
            ma60 REAL,
            rsi REAL,
            macd REAL,
            score REAL,
            recommendation TEXT,
            status TEXT,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(code, date)
        )
    ''')
    conn.commit()
    print("   ✓ 새 테이블 생성 (code, date 복합 유니크)")
    
    # 3. 인덱스 생성
    print("\n3. 인덱스 생성...")
    cursor.execute("CREATE INDEX idx_price_code ON price_data(code)")
    cursor.execute("CREATE INDEX idx_price_date ON price_data(date)")
    cursor.execute("CREATE INDEX idx_price_code_date ON price_data(code, date)")
    conn.commit()
    print("   ✓ 인덱스 3개 생성")
    
    # 4. 데이터 마이그레이션
    print("\n4. 데이터 마이그레이션...")
    cursor.execute('''
        INSERT INTO price_data 
        (code, name, market, date, open, high, low, close, volume, 
         change_pct, ma5, ma20, ma60, rsi, macd, score, recommendation, status, updated_at)
        SELECT * FROM price_data_backup
    ''')
    conn.commit()
    
    cursor.execute("SELECT COUNT(*) FROM price_data")
    count = cursor.fetchone()[0]
    print(f"   ✓ {count:,} rows 마이그레이션 완료")
    
    # 5. 백업 테이블 삭제
    print("\n5. 백업 테이블 삭제...")
    cursor.execute("DROP TABLE price_data_backup")
    conn.commit()
    print("   ✓ price_data_backup 삭제")
    
    # 6. 결과 확인
    print("\n6. 결과 확인...")
    cursor.execute("SELECT COUNT(*) as rows, COUNT(DISTINCT code) as symbols, MIN(date), MAX(date) FROM price_data")
    row = cursor.fetchone()
    print(f"   총 데이터: {row[0]:,} rows")
    print(f"   종목수: {row[1]:,}")
    print(f"   기간: {row[2]} ~ {row[3]}")
    
    conn.close()
    print("\n" + "=" * 70)
    print("✅ 테이블 구조 수정 완료!")
    print("=" * 70)


if __name__ == '__main__':
    fix_table_structure()
