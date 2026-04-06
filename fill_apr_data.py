"""
4월 1-3일 누락 데이터 구축 스크립트
"""
import sqlite3
import pandas as pd
import FinanceDataReader as fdr
from datetime import datetime
from concurrent.futures import ProcessPoolExecutor, as_completed
import sys
import numpy as np

sys.path.insert(0, '/root/.openclaw/workspace/strg')

def get_stock_data_batch(codes_with_names, start_date, end_date):
    """배치로 주식 데이터 가져오기"""
    results = []
    
    for code, name in codes_with_names:
        try:
            df = fdr.DataReader(code, start=start_date, end=end_date)
            if not df.empty:
                for date, row in df.iterrows():
                    date_str = date.strftime('%Y-%m-%d')
                    change_pct = row.get('Change', 0) * 100 if 'Change' in row else None
                    
                    results.append({
                        'date': date_str,
                        'code': code,
                        'name': name,
                        'open': float(row['Open']),
                        'high': float(row['High']),
                        'low': float(row['Low']),
                        'close': float(row['Close']),
                        'volume': int(row['Volume']),
                        'change_pct': change_pct
                    })
        except Exception as e:
            pass
    
    return results

def fill_missing_data(dates_to_fill, max_workers=8):
    """누락된 데이터 채우기"""
    db_path = "data/level1_prices.db"
    
    conn = sqlite3.connect(db_path)
    
    # 3월 31일 기준 종목 목록 가져오기
    query = "SELECT DISTINCT code, name FROM price_data WHERE date = '2026-03-31'"
    df_symbols = pd.read_sql(query, conn)
    conn.close()
    
    print(f"📊 대상 종목: {len(df_symbols)}개")
    print(f"📅 채울 날짜: {dates_to_fill}")
    print(f"🔄 워커 수: {max_workers}")
    print("=" * 60)
    
    # 배치 처리
    batch_size = 50
    all_codes = list(zip(df_symbols['code'], df_symbols['name']))
    batches = [all_codes[i:i+batch_size] for i in range(0, len(all_codes), batch_size)]
    
    all_results = []
    
    start_time = datetime.now()
    
    with ProcessPoolExecutor(max_workers=max_workers) as executor:
        futures = {
            executor.submit(get_stock_data_batch, batch, '2026-04-01', '2026-04-03'): i 
            for i, batch in enumerate(batches)
        }
        
        for future in as_completed(futures):
            batch_idx = futures[future]
            try:
                results = future.result()
                all_results.extend(results)
                
                if batch_idx % 10 == 0:
                    elapsed = (datetime.now() - start_time).total_seconds()
                    progress = (batch_idx + 1) / len(batches) * 100
                    print(f"   [{batch_idx+1}/{len(batches)}] {progress:.1f}% - 수집: {len(all_results)}건 ({elapsed:.0f}초)")
                    
            except Exception as e:
                print(f"   배치 {batch_idx} 오류: {e}")
    
    print(f"\n✅ 총 수집: {len(all_results)}건")
    
    # DB에 저장
    if all_results:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # 기존 데이터 삭제 (해당 날짜들)
        for date in dates_to_fill:
            cursor.execute("DELETE FROM price_data WHERE date = ?", (date,))
            print(f"🗑️  {date} 기존 데이터 삭제")
        
        # 새 데이터 삽입
        inserted = 0
        for record in all_results:
            if record['date'] in dates_to_fill:
                try:
                    cursor.execute("""
                        INSERT INTO price_data 
                        (date, code, name, open, high, low, close, volume, change_pct)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """, (
                        record['date'], record['code'], record['name'],
                        record['open'], record['high'], record['low'],
                        record['close'], record['volume'], record['change_pct']
                    ))
                    inserted += 1
                except Exception as e:
                    pass
        
        conn.commit()
        conn.close()
        
        print(f"💾 DB 저장 완료: {inserted}건")
        
        # 검증
        conn = sqlite3.connect(db_path)
        for date in dates_to_fill:
            query = f"SELECT COUNT(*) as count FROM price_data WHERE date = '{date}'"
            count = pd.read_sql(query, conn).iloc[0]['count']
            print(f"   📅 {date}: {count}개 종목")
        conn.close()

if __name__ == "__main__":
    dates = ['2026-04-01', '2026-04-02', '2026-04-03']
    fill_missing_data(dates, max_workers=8)
