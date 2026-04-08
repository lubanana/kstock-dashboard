#!/usr/bin/env python3
"""
4/8 데이터 level1_prices.db에 직접 구축
"""

import sys
sys.path.insert(0, '/root/.openclaw/workspace/strg')

import sqlite3
import pandas as pd
from datetime import datetime
from concurrent.futures import ProcessPoolExecutor, as_completed
import FinanceDataReader as fdr

DB_PATH = '/root/.openclaw/workspace/strg/data/level1_prices.db'

def get_all_symbols():
    """전체 종목 리스트"""
    symbols = []
    
    try:
        kospi = fdr.StockListing('KOSPI')
        symbols.extend(kospi['Code'].tolist())
        print(f"KOSPI: {len(kospi)}개")
    except Exception as e:
        print(f"KOSPI 로드 실패: {e}")
    
    try:
        kosdaq = fdr.StockListing('KOSDAQ')
        symbols.extend(kosdaq['Code'].tolist())
        print(f"KOSDAQ: {len(kosdaq)}개")
    except Exception as e:
        print(f"KOSDAQ 로드 실패: {e}")
    
    # ETF/ETN 필터링
    exclude = ['K', 'Q', 'V', 'W', 'T']
    filtered = [s for s in symbols if not any(s.startswith(p) for p in exclude) and len(s) == 6]
    
    return list(set(filtered))

def process_stock(args):
    """개별 종목 처리"""
    code, target_date = args
    try:
        df = fdr.DataReader(code, target_date, target_date)
        if df is not None and len(df) > 0:
            row = df.iloc[0]
            return ('success', code, {
                'date': target_date,
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

def build_0408():
    """4/8 데이터 구축"""
    target_date = '2026-04-08'
    
    print("=" * 60)
    print(f"🚀 {target_date} 데이터 구축 시작")
    print("=" * 60)
    
    # 종목 리스트
    symbols = get_all_symbols()
    print(f"총 대상: {len(symbols)}개 종목\n")
    
    # DB 연결
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # 이미 있는 종목 확인
    cursor.execute("SELECT DISTINCT code FROM price_data WHERE date = ?", (target_date,))
    existing = set([row[0] for row in cursor.fetchall()])
    print(f"✅ 이미 구축: {len(existing)}개")
    
    # 구축할 종목
    to_build = [s for s in symbols if s not in existing]
    print(f"⚠️  구축 필요: {len(to_build)}개\n")
    
    if not to_build:
        print("모든 종목이 이미 구축되었습니다.")
        conn.close()
        return
    
    # 병렬 처리
    success = 0
    failed = 0
    args_list = [(code, target_date) for code in to_build]
    
    print(f"🔧 병렬 구축 시작 (workers: 8)\n")
    
    with ProcessPoolExecutor(max_workers=8) as executor:
        futures = {executor.submit(process_stock, arg): arg for arg in args_list}
        
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
                if success % 500 == 0:
                    conn.commit()
                    print(f"   진행: {success}/{len(to_build)} ({success/len(to_build)*100:.1f}%)")
            else:
                failed += 1
    
    conn.commit()
    conn.close()
    
    print("\n" + "=" * 60)
    print(f"✅ 완료: 성공 {success}개, 실패 {failed}개")
    print("=" * 60)

if __name__ == '__main__':
    build_0408()
