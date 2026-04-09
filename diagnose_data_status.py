#!/usr/bin/env python3
"""
데이터 구축 진단 도구
===================
주가 데이터 구축 상태를 확인하고 문제점을 진단

Usage:
    python3 diagnose_data_status.py
"""

import sqlite3
import pandas as pd
from datetime import datetime, timedelta
import sys
sys.path.insert(0, '.')

DB_PATH = 'data/level1_prices.db'

def check_db_status():
    """DB 상태 확인"""
    print("=" * 60)
    print("📊 데이터 구축 진단 보고서")
    print("=" * 60)
    
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        # 1. 전체 데이터 수
        cursor.execute("SELECT COUNT(*) FROM price_data")
        total_rows = cursor.fetchone()[0]
        print(f"\n1️⃣ 총 데이터 레코드: {total_rows:,}개")
        
        # 2. 고유 종목 수
        cursor.execute("SELECT COUNT(DISTINCT code) FROM price_data")
        unique_stocks = cursor.fetchone()[0]
        print(f"2️⃣ 고유 종목 수: {unique_stocks:,}개")
        
        # 3. 날짜 범위
        cursor.execute("SELECT MIN(date), MAX(date) FROM price_data")
        min_date, max_date = cursor.fetchone()
        print(f"3️⃣ 데이터 기간: {min_date} ~ {max_date}")
        
        # 4. 최근 5일간 데이터 수
        print(f"\n4️⃣ 최근 5일간 데이터 현황:")
        for i in range(5):
            date_str = (datetime.now() - timedelta(days=i)).strftime('%Y-%m-%d')
            cursor.execute("SELECT COUNT(*) FROM price_data WHERE date = ?", (date_str,))
            count = cursor.fetchone()[0]
            status = "✅" if count > 3000 else "⚠️" if count > 0 else "❌"
            print(f"   {date_str}: {count:,}개 {status}")
        
        # 5. 종목별 최신 데이터
        print(f"\n5️⃣ 종목별 최신 데이터 날짜 (샘플 10개):")
        cursor.execute("""
            SELECT code, name, MAX(date) as latest_date, close
            FROM price_data 
            GROUP BY code 
            ORDER BY latest_date DESC
            LIMIT 10
        """)
        for row in cursor.fetchall():
            print(f"   {row[0]} {row[1]}: {row[2]} ({row[3]:,.0f}원)")
        
        # 6. 누락된 최근 데이터 확인
        today = datetime.now().strftime('%Y-%m-%d')
        yesterday = (datetime.now() - timedelta(days=1)).strftime('%Y-%m-%d')
        
        cursor.execute("SELECT COUNT(*) FROM price_data WHERE date = ?", (yesterday,))
        yesterday_count = cursor.fetchone()[0]
        
        print(f"\n6️⃣ 어제({yesterday}) 데이터: {yesterday_count:,}개")
        
        if yesterday_count < 3500:
            print(f"   ⚠️ 어제 데이터가 부족합니다. {3500 - yesterday_count}개 누락")
            print(f"   💡 unified_daily_updater.py를 실행하세요:")
            print(f"      python3 unified_daily_updater.py --date {yesterday}")
        else:
            print(f"   ✅ 어제 데이터 정상")
        
        conn.close()
        
    except Exception as e:
        print(f"❌ 오류 발생: {e}")
        return False
    
    print("\n" + "=" * 60)
    return True

def main():
    check_db_status()

if __name__ == '__main__':
    main()
