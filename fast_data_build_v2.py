#!/usr/bin/env python3
"""
고속 주가 데이터 구축 - 배치 처리 최적화
"""

import FinanceDataReader as fdr
import sqlite3
from datetime import datetime

def main():
    print('='*70)
    print('🚀 고속 주가 데이터 구축 (배치 최적화)')
    print('='*70)
    
    conn = sqlite3.connect('data/pivot_strategy.db')
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
    print('-'*70)
    
    target_date = '2026-03-31'
    success = 0
    fail = 0
    data_buffer = []
    
    for i, symbol in enumerate(symbols, 1):
        try:
            df = fdr.DataReader(symbol, '2026-03-30', '2026-03-31')
            
            if df is not None and len(df) >= 2:
                last_row = df.iloc[-1]
                last_date = df.index[-1].strftime('%Y-%m-%d')
                
                if last_date == target_date:
                    data_buffer.append((
                        symbol, target_date, 
                        float(last_row['Open']), float(last_row['High']),
                        float(last_row['Low']), float(last_row['Close']), 
                        int(last_row['Volume'])
                    ))
                    success += 1
            else:
                fail += 1
                
        except Exception as e:
            fail += 1
        
        # 배치 저장 (100개마다)
        if len(data_buffer) >= 100:
            try:
                cursor.executemany('''
                    INSERT OR REPLACE INTO stock_prices 
                    (symbol, date, open, high, low, close, volume)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                ''', data_buffer)
                conn.commit()
                data_buffer = []
            except:
                conn.rollback()
        
        # 진행률 출력
        if i % 200 == 0 or i == total:
            progress = (i / total) * 100
            current = cursor.execute('SELECT COUNT(DISTINCT symbol) FROM stock_prices WHERE date = ?', (target_date,)).fetchone()[0]
            print(f'[{i}/{total}] {progress:.1f}% | 누적:{current}개')
    
    # 남은 데이터 저장
    if data_buffer:
        try:
            cursor.executemany('''
                INSERT OR REPLACE INTO stock_prices 
                (symbol, date, open, high, low, close, volume)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', data_buffer)
            conn.commit()
        except:
            pass
    
    # 최종 결과
    today_count = cursor.execute('SELECT COUNT(DISTINCT symbol) FROM stock_prices WHERE date = ?', (target_date,)).fetchone()[0]
    print(f'\n✅ 완료: 2026-03-31 = {today_count}개 종목')
    print(f'   성공: {success}개 / 실패: {fail}개')
    
    conn.close()

if __name__ == '__main__':
    main()
