#!/usr/bin/env python3
"""
Fill Missing Data - 누락된 날짜 데이터 병렬 채우기
"""

import sys
sys.path.insert(0, '.')
import sqlite3
from datetime import datetime, timedelta, timezone
from fdr_wrapper import get_price
from multiprocessing import Pool, cpu_count
import time

DB_PATH = 'data/pivot_strategy.db'
MAX_WORKERS = min(cpu_count(), 8)
BATCH_SIZE = 50


def get_missing_symbols(target_date):
    """해당 날짜에 없는 종목 리스트"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # 기준일 (전날)에 있었던 종목들 중 target_date에 없는 것
    prev_date = (datetime.strptime(target_date, '%Y-%m-%d') - timedelta(days=1)).strftime('%Y-%m-%d')
    
    cursor.execute('''
        SELECT DISTINCT symbol FROM stock_prices WHERE date = ?
        EXCEPT
        SELECT DISTINCT symbol FROM stock_prices WHERE date = ?
    ''', (prev_date, target_date))
    
    symbols = [row[0] for row in cursor.fetchall()]
    conn.close()
    return symbols


def update_single(args):
    """단일 종목 업데이트"""
    symbol, target_date = args
    
    try:
        df = get_price(symbol, target_date, target_date)
        if df is not None and not df.empty:
            return {'symbol': symbol, 'status': 'updated'}
        else:
            return {'symbol': symbol, 'status': 'empty'}
    except Exception as e:
        return {'symbol': symbol, 'status': 'failed', 'error': str(e)[:30]}


def fill_missing_data(target_date):
    """누락 데이터 채우기"""
    start_time = datetime.now()
    
    print("="*70)
    print(f"🚀 누락 데이터 채우기 - {target_date}")
    print(f"🔄 워커 수: {MAX_WORKERS}개")
    print("="*70)
    
    # 누락 종목 확인
    missing = get_missing_symbols(target_date)
    print(f"\n📋 누락 종목: {len(missing):,}개")
    
    if not missing:
        print("✅ 누락된 종목이 없습니다!")
        return
    
    # 배치 처리
    stats = {'updated': 0, 'empty': 0, 'failed': 0}
    batch_count = (len(missing) + BATCH_SIZE - 1) // BATCH_SIZE
    
    print(f"\n🔄 총 {batch_count}개 배치 처리 시작...\n")
    
    for i in range(0, len(missing), BATCH_SIZE):
        batch = missing[i:i+BATCH_SIZE]
        batch_num = i // BATCH_SIZE + 1
        
        print(f"   [{batch_num}/{batch_count}] 처리 중... ({len(batch)}개)", end='', flush=True)
        
        # 병렬 처리
        args = [(s, target_date) for s in batch]
        with Pool(processes=MAX_WORKERS) as pool:
            results = pool.map(update_single, args)
        
        # 결과 집계
        for r in results:
            stats[r['status']] = stats.get(r['status'], 0) + 1
        
        print(f" ✓")
        
        # 20배치마다 진행 보고
        if batch_num % 20 == 0 or batch_num == batch_count:
            elapsed = datetime.now() - start_time
            processed = sum(stats.values())
            progress = processed / len(missing) * 100
            speed = processed / elapsed.total_seconds() * 60 if elapsed.total_seconds() > 0 else 0
            print(f"\n   📊 진행: {processed:,}/{len(missing):,} ({progress:.1f}%) | "
                  f"속도: {speed:.0f}종목/분 | 시간: {str(elapsed).split('.')[0]}\n")
        
        time.sleep(0.3)  # Rate limit 방지
    
    # 최종 보고
    elapsed = datetime.now() - start_time
    print("\n" + "="*70)
    print("✅ 누락 데이터 채우기 완료")
    print("="*70)
    print(f"   총 소요 시간: {str(elapsed).split('.')[0]}")
    print(f"   업데이트: {stats.get('updated', 0):,}")
    print(f"   데이터없음: {stats.get('empty', 0):,}")
    print(f"   실패: {stats.get('failed', 0):,}")
    print("="*70)


if __name__ == '__main__':
    import sys
    target_date = sys.argv[1] if len(sys.argv) > 1 else '2026-04-01'
    fill_missing_data(target_date)
