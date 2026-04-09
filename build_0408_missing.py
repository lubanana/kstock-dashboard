#!/usr/bin/env python3
"""
4/8 데이터 추가 구축 (누락분)
"""

import sys
sys.path.insert(0, '/root/.openclaw/workspace/strg')

import sqlite3
import pandas as pd
from datetime import datetime
from concurrent.futures import ProcessPoolExecutor, as_completed
import FinanceDataReader as fdr

DB_PATH = '/root/.openclaw/workspace/strg/data/level1_prices.db'
TARGET_DATE = '2026-04-08'

def get_missing_symbols():
    """누락된 종목 리스트"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # 4/7에는 있지만 4/8에는 없는 종목
    cursor.execute('''
        SELECT DISTINCT code FROM price_data WHERE date = '2026-04-07'
        EXCEPT
        SELECT DISTINCT code FROM price_data WHERE date = '2026-04-08'
    ''')
    missing = [row[0] for row in cursor.fetchall()]
    
    conn.close()
    return missing

def process_stock(code):
    """개별 종목 처리"""
    try:
        df = fdr.DataReader(code, TARGET_DATE, TARGET_DATE)
        if df is not None and len(df) > 0:
            row = df.iloc[0]
            return ('success', code, {
                'date': TARGET_DATE,
                'open': float(row['Open']),
                'high': float(row['High']),
                'low': float(row['Low']),
                'close': float(row['Close']),
                'volume': int(row['Volume']),
                'change_pct': float(row['Change']) if 'Change' in row else 0.0
            })
        return ('empty', code, None)
    except Exception as e:
        return ('error', code, str(e))

def build_missing():
    """누락 데이터 구축"""
    print("=" * 60)
    print(f"🚀 {TARGET_DATE} 누락 데이터 구축")
    print("=" * 60)
    
    # 누락 종목 확인
    missing = get_missing_symbols()
    print(f"누락 종목: {len(missing)}개\n")
    
    if not missing:
        print("누락된 종목이 없습니다.")
        return
    
    # DB 연결
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # 병렬 처리
    success = 0
    failed = 0
    
    print(f"🔧 병렬 구축 시작 (workers: 8)\n")
    
    with ProcessPoolExecutor(max_workers=8) as executor:
        futures = {executor.submit(process_stock, code): code for code in missing}
        
        for i, future in enumerate(as_completed(futures)):
            result = future.result()
            status, code, data = result
            
            if status == 'success' and data:
                # stock_info에서 종목명 조회
                cursor.execute("SELECT name, market FROM stock_info WHERE code = ?", (code,))
                row = cursor.fetchone()
                name = row[0] if row else 'Unknown'
                market = row[1] if row else 'Unknown'
                
                # 저장
                cursor.execute('''
                    INSERT OR REPLACE INTO price_data 
                    (code, name, market, date, open, high, low, close, volume, change_pct, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, datetime('now'))
                ''', (code, name, market, data['date'], data['open'], data['high'], 
                     data['low'], data['close'], data['volume'], data['change_pct']))
                
                success += 1
                if success % 100 == 0:
                    conn.commit()
                    print(f"   진행: {success}/{len(missing)} ({success/len(missing)*100:.1f}%)")
            else:
                failed += 1
    
    conn.commit()
    conn.close()
    
    print("\n" + "=" * 60)
    print(f"✅ 완료: 성공 {success}개, 실패 {failed}개")
    print("=" * 60)

if __name__ == '__main__':
    build_missing()
