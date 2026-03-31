#!/usr/bin/env python3
"""
고속 주가 데이터 구축 스크립트 - 병렬 처리
"""

import FinanceDataReader as fdr
import sqlite3
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed
import threading

# 스레드-safe DB 연결
db_lock = threading.Lock()

def process_symbol(symbol, target_date='2026-03-31'):
    """단일 종목 처리"""
    try:
        df = fdr.DataReader(symbol, '2026-03-30', '2026-03-31')
        
        if df is not None and len(df) >= 2:
            last_row = df.iloc[-1]
            last_date = df.index[-1].strftime('%Y-%m-%d')
            
            if last_date == target_date:
                return {
                    'symbol': symbol,
                    'date': target_date,
                    'open': float(last_row['Open']),
                    'high': float(last_row['High']),
                    'low': float(last_row['Low']),
                    'close': float(last_row['Close']),
                    'volume': int(last_row['Volume'])
                }
    except:
        pass
    return None

def batch_insert(conn, data_batch):
    """배치 삽입"""
    with db_lock:
        cursor = conn.cursor()
        cursor.executemany('''
            INSERT OR REPLACE INTO stock_prices 
            (symbol, date, open, high, low, close, volume)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', [(d['symbol'], d['date'], d['open'], d['high'], d['low'], d['close'], d['volume']) for d in data_batch])
        conn.commit()

def main():
    print('='*70)
    print('🚀 고속 주가 데이터 구축 (병렬 처리)')
    print('='*70)
    
    conn = sqlite3.connect('data/pivot_strategy.db', check_same_thread=False)
    cursor = conn.cursor()
    
    # 대상 종목
    cursor.execute('''
        SELECT DISTINCT symbol FROM stock_prices 
        WHERE date = '2026-03-30'
        AND symbol NOT IN (SELECT DISTINCT symbol FROM stock_prices WHERE date = '2026-03-31')
    ''')
    symbols = [s[0] for s in cursor.fetchall()]
    
    total = len(symbols)
    print(f'\n📥 구축 대상: {total}개 종목')
    print(f'⚡ 병렬 처리: 20개 스레드')
    print('-'*70)
    
    target_date = '2026-03-31'
    success = 0
    batch = []
    batch_size = 100
    
    with ThreadPoolExecutor(max_workers=20) as executor:
        futures = {executor.submit(process_symbol, symbol, target_date): symbol for symbol in symbols}
        
        for i, future in enumerate(as_completed(futures), 1):
            result = future.result()
            if result:
                batch.append(result)
                success += 1
            
            # 배치 저장
            if len(batch) >= batch_size:
                batch_insert(conn, batch)
                batch = []
            
            # 진행률 출력
            if i % 200 == 0:
                progress = (i / total) * 100
                print(f'[{i}/{total}] {progress:.1f}% | 성공:{success}')
    
    # 남은 배치 저장
    if batch:
        batch_insert(conn, batch)
    
    # 최종 결과
    today_count = cursor.execute('SELECT COUNT(DISTINCT symbol) FROM stock_prices WHERE date = ?', (target_date,)).fetchone()[0]
    print(f'\n✅ 완료: 2026-03-31 = {today_count}개 종목')
    
    conn.close()

if __name__ == '__main__':
    main()
