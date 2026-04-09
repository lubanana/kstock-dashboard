#!/usr/bin/env python3
"""
DART 최근 공시 빠른 업데이트
=======================
최근 N일 공시만 빠르게 업데이트

Usage:
    python3 fast_dart_update.py --days 10
"""

import sys
sys.path.insert(0, '/root/.openclaw/workspace/strg')

import sqlite3
import pandas as pd
from datetime import datetime, timedelta
import time
import os

# OpenDartReader import
try:
    import OpenDartReader
    from dotenv import load_dotenv
    load_dotenv('/root/.openclaw/workspace/strg/.env')
    
    DART_API_KEY = os.environ.get('OPENDART_API_KEY') or os.environ.get('DART_API_KEY')
    if DART_API_KEY:
        dart = OpenDartReader(DART_API_KEY)
        print("✅ OpenDartReader 초기화 완료")
    else:
        dart = None
        print("⚠️ API 키 없음")
except Exception as e:
    print(f"⚠️ 초기화 실패: {e}")
    dart = None


def update_disclosures(days=10):
    """최근 공시 업데이트"""
    if not dart:
        return
    
    # 종목 목록은 level1_prices.db에서 읽기
    conn_prices = sqlite3.connect('/root/.openclaw/workspace/strg/data/level1_prices.db')
    cursor_prices = conn_prices.execute('SELECT code, name FROM stock_info')
    stocks = cursor_prices.fetchall()
    conn_prices.close()
    
    # 공시 저장은 pivot_strategy.db
    conn = sqlite3.connect('/root/.openclaw/workspace/strg/data/pivot_strategy.db')
    cursor = conn.cursor()
    
    end_date = datetime.now()
    start_date = end_date - timedelta(days=days)
    
    print(f"\n📊 수집 기간: {start_date.strftime('%Y-%m-%d')} ~ {end_date.strftime('%Y-%m-%d')}")
    print(f"📋 대상 종목: {len(stocks)}개\n")
    
    total_inserted = 0
    errors = 0
    
    for i, (code, name) in enumerate(stocks, 1):
        try:
            df = dart.list(code, start=start_date.strftime('%Y-%m-%d'),
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
                            code, name, code,
                            row.get('rcept_no', ''),
                            row.get('rcept_dt', ''),
                            row.get('report_nm', ''),
                            row.get('report_nm', '')
                        ))
                        if cursor.rowcount > 0:
                            total_inserted += 1
                    except:
                        pass
            
            if i % 50 == 0:
                conn.commit()
                print(f"   [{i}/{len(stocks)}] 수집: {total_inserted}건")
            
            time.sleep(0.03)
            
        except Exception as e:
            errors += 1
            time.sleep(0.3)
    
    conn.commit()
    conn.close()
    
    print(f"\n✅ 완료: {total_inserted}건 추가, 오류: {errors}건")
    return total_inserted


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--days', type=int, default=10)
    args = parser.parse_args()
    
    print("="*70)
    print("🚀 DART 공시 빠른 업데이트")
    print("="*70)
    
    update_disclosures(args.days)
    
    print("\n✅ 완료!")
