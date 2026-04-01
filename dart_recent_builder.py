#!/usr/bin/env python3
"""
DART 최근 공시 데이터 구축 스크립트
OpenDartReader API 활용
"""

import sys
sys.path.insert(0, '/root/.openclaw/workspace/strg')

import sqlite3
import pandas as pd
from datetime import datetime, timedelta
import time
import os

# OpenDartReader import 시도
try:
    import OpenDartReader
    from dotenv import load_dotenv
    
    # .env 파일 로드
    load_dotenv('/root/.openclaw/workspace/strg/.env')
    
    DART_API_KEY = os.environ.get('OPENDART_API_KEY') or os.environ.get('DART_API_KEY')
    if not DART_API_KEY:
        print("⚠️ .env 파일에서 API 키를 찾을 수 없습니다")
        dart = None
    else:
        dart = OpenDartReader(DART_API_KEY)
        print("✅ OpenDartReader 초기화 완료")
except Exception as e:
    print(f"⚠️ OpenDartReader 초기화 실패: {e}")
    dart = None


def create_table():
    """DART 공시 테이블 생성"""
    conn = sqlite3.connect('/root/.openclaw/workspace/strg/data/pivot_strategy.db')
    cursor = conn.cursor()
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS dart_disclosures (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            corp_code TEXT,
            corp_name TEXT,
            stock_code TEXT,
            receipt_no TEXT UNIQUE,
            receipt_date TEXT,
            disclosure_type TEXT,
            disclosure_title TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # 인덱스 생성
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_dart_date ON dart_disclosures(receipt_date)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_dart_stock ON dart_disclosures(stock_code)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_dart_type ON dart_disclosures(disclosure_type)')
    
    conn.commit()
    conn.close()
    print("✅ 테이블 생성 완료")


def collect_recent_disclosures(days=30):
    """최근 공시 수집"""
    if dart is None:
        print("⚠️ DART API 사용 불가")
        return 0
    
    conn = sqlite3.connect('/root/.openclaw/workspace/strg/data/pivot_strategy.db')
    cursor = conn.cursor()
    
    # 종목 목록 로드 (corp_code는 symbol로 대체하여 조회)
    cursor.execute('SELECT symbol, name FROM stock_info')
    stocks = cursor.fetchall()
    
    end_date = datetime.now()
    start_date = end_date - timedelta(days=days)
    
    print(f"\n📊 수집 기간: {start_date.strftime('%Y-%m-%d')} ~ {end_date.strftime('%Y-%m-%d')}")
    print(f"📋 대상 종목: {len(stocks)}개\n")
    
    total_inserted = 0
    errors = 0
    
    for i, (stock_code, name) in enumerate(stocks, 1):
        try:
            # OpenDartReader로 공시 목록 조회 (종목코드 사용)
            df = dart.list(stock_code, start=start_date.strftime('%Y-%m-%d'), 
                          end=end_date.strftime('%Y-%m-%d'))
            
            if df is not None and len(df) > 0:
                for _, row in df.iterrows():
                    try:
                        cursor.execute('''
                            INSERT OR IGNORE INTO dart_disclosures 
                            (corp_code, corp_name, stock_code, receipt_no, receipt_date, 
                             disclosure_type, disclosure_title)
                            VALUES (?, ?, ?, ?, ?, ?, ?)
                        ''', (
                            stock_code,  # corp_code 대신 stock_code 사용
                            row.get('corp_name', name),
                            stock_code,
                            row.get('rcept_no', ''),
                            row.get('rcept_dt', ''),
                            row.get('report_nm', ''),
                            row.get('report_nm', '')
                        ))
                        if cursor.rowcount > 0:
                            total_inserted += 1
                    except:
                        pass
            
            if i % 100 == 0:
                conn.commit()
                print(f"   [{i}/{len(stocks)}] 진행중... (수집: {total_inserted}건)", end='\r')
            
            time.sleep(0.05)  # API 속도 제한
            
        except Exception as e:
            errors += 1
            if errors < 10:
                print(f"\n   ⚠️ {stock_code} 오류: {e}")
            time.sleep(0.5)
    
    conn.commit()
    conn.close()
    
    print(f"\n\n✅ 수집 완료: {total_inserted}건")
    return total_inserted


def show_stats():
    """통계 출력"""
    conn = sqlite3.connect('/root/.openclaw/workspace/strg/data/pivot_strategy.db')
    cursor = conn.cursor()
    
    print("\n" + "="*70)
    print("📊 DART 공시 데이터 통계")
    print("="*70)
    
    total = cursor.execute('SELECT COUNT(*) FROM dart_disclosures').fetchone()[0]
    print(f"\n총 공시 수: {total:,}건")
    
    latest = cursor.execute('SELECT MAX(receipt_date) FROM dart_disclosures').fetchone()[0]
    earliest = cursor.execute('SELECT MIN(receipt_date) FROM dart_disclosures').fetchone()[0]
    print(f"기간: {earliest} ~ {latest}")
    
    # 최근 7일
    recent_7d = cursor.execute('''
        SELECT COUNT(*) FROM dart_disclosures 
        WHERE receipt_date >= date('now', '-7 days')
    ''').fetchone()[0]
    print(f"최근 7일: {recent_7d}건")
    
    # 최근 30일
    recent_30d = cursor.execute('''
        SELECT COUNT(*) FROM dart_disclosures 
        WHERE receipt_date >= date('now', '-30 days')
    ''').fetchone()[0]
    print(f"최근 30일: {recent_30d}건")
    
    # 상위 종목
    print("\n📈 공시 많은 종목 TOP 10:")
    top_stocks = cursor.execute('''
        SELECT stock_code, COUNT(*) as cnt 
        FROM dart_disclosures 
        GROUP BY stock_code 
        ORDER BY cnt DESC 
        LIMIT 10
    ''').fetchall()
    for s in top_stocks:
        print(f"   {s[0]}: {s[1]}건")
    
    conn.close()


def main():
    print("="*70)
    print("🚀 DART 최근 공시 데이터 구축")
    print("="*70)
    
    # 테이블 생성
    create_table()
    
    # 최근 30일 데이터 수집
    if dart:
        count = collect_recent_disclosures(days=30)
    else:
        print("\n⚠️ DART API 키 설정 필요")
        print("   export DART_API_KEY='your_api_key'")
    
    # 통계 출력
    show_stats()
    
    print("\n✅ 완료!")


if __name__ == '__main__':
    main()
