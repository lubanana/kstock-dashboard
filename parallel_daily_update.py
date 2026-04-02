#!/usr/bin/env python3
"""
Parallel Daily Price Update Batch - 병렬 전체 종목 가격정보 업데이트
Multi-process parallel processing for faster data building
"""

import sys
sys.path.insert(0, '.')
import sqlite3
from datetime import datetime, timedelta, timezone
from fdr_wrapper import get_price
from multiprocessing import Pool, cpu_count, Manager
from functools import partial
import time

DB_PATH = 'data/pivot_strategy.db'
BATCH_SIZE = 50  # 워커당 처리 단위
MAX_WORKERS = min(cpu_count(), 8)  # 최대 8개 워커


def get_all_symbols():
    """전체 종목 리스트 로드"""
    import FinanceDataReader as fdr
    
    symbols = set()
    
    # DB 기존 종목
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('SELECT DISTINCT symbol FROM stock_prices')
    db_symbols = [row[0] for row in cursor.fetchall()]
    conn.close()
    symbols.update(db_symbols)
    
    # KOSPI/KOSDAQ
    try:
        kospi = fdr.StockListing('KOSPI')
        symbols.update(kospi['Code'].tolist())
    except:
        pass
    
    try:
        kosdaq = fdr.StockListing('KOSDAQ')
        symbols.update(kosdaq['Code'].tolist())
    except:
        pass
    
    # ETF 필터링
    exclude_patterns = ['K', 'Q', 'V', 'W', 'T']
    filtered = [s for s in symbols if not any(s.startswith(p) for p in exclude_patterns)]
    
    return sorted(filtered)


def check_exists(symbol, target_date):
    """해당 종목/날짜 데이터 존재 여부 확인"""
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute(
            'SELECT 1 FROM stock_prices WHERE symbol = ? AND date = ? LIMIT 1',
            (symbol, target_date)
        )
        exists = cursor.fetchone() is not None
        conn.close()
        return exists
    except:
        return False


def update_single(args):
    """단일 종목 업데이트 (워커 함수)"""
    symbol, target_date = args
    
    # 이미 있으면 스킵
    if check_exists(symbol, target_date):
        return {'symbol': symbol, 'status': 'skipped'}
    
    try:
        # 데이터 조회 및 저장
        df = get_price(symbol, target_date, target_date)
        
        if df is not None and not df.empty:
            return {'symbol': symbol, 'status': 'updated'}
        else:
            return {'symbol': symbol, 'status': 'failed', 'reason': 'empty'}
    except Exception as e:
        return {'symbol': symbol, 'status': 'failed', 'reason': str(e)[:50]}


def process_batch(symbols, target_date, progress_queue):
    """배치 처리"""
    args = [(s, target_date) for s in symbols]
    
    with Pool(processes=MAX_WORKERS) as pool:
        results = pool.map(update_single, args)
    
    # 결과 집계
    for r in results:
        progress_queue.put(r['status'])
    
    return results


def log_progress(stats, total, start_time):
    """진행 상황 로깅"""
    elapsed = datetime.now() - start_time
    elapsed_str = str(elapsed).split('.')[0]
    
    processed = sum(stats.values())
    progress_pct = (processed / total) * 100 if total > 0 else 0
    
    speed = processed / elapsed.total_seconds() * 60 if elapsed.total_seconds() > 0 else 0
    eta_seconds = (total - processed) / (processed / elapsed.total_seconds()) if processed > 0 else 0
    eta_min = int(eta_seconds / 60)
    
    print(f"\n{'='*60}")
    print(f"📊 진행 상황 - {datetime.now().strftime('%H:%M:%S')}")
    print(f"{'='*60}")
    print(f"   경과 시간: {elapsed_str}")
    print(f"   진행률: {processed}/{total} ({progress_pct:.1f}%)")
    print(f"   ✅ 업데이트: {stats.get('updated', 0)}")
    print(f"   ⏭️  스킵: {stats.get('skipped', 0)}")
    print(f"   ❌ 실패: {stats.get('failed', 0)}")
    print(f"   처리 속도: {speed:.0f} 종목/분")
    print(f"   예상 남은 시간: {eta_min}분")
    print(f"{'='*60}\n", flush=True)


def parallel_daily_update(target_date=None):
    """병렬 일일 업데이트 실행"""
    if target_date is None:
        target_date = datetime.now(timezone(timedelta(hours=9))).strftime('%Y-%m-%d')
    
    start_time = datetime.now()
    
    print("="*70)
    print(f"🚀 병렬 전체 종목 일일 가격 업데이트 - {target_date}")
    print(f"🔄 워커 수: {MAX_WORKERS}개")
    print("="*70, flush=True)
    
    # 전체 종목 로드
    print("\n📋 전체 종목 로드 중...")
    all_symbols = get_all_symbols()
    total = len(all_symbols)
    print(f"   총 {total:,}개 종목")
    
    # 이미 있는 종목 필터링
    print("\n🔍 이미 구축된 종목 확인 중...")
    existing = [s for s in all_symbols if check_exists(s, target_date)]
    to_update = [s for s in all_symbols if not check_exists(s, target_date)]
    
    print(f"   이미 구축: {len(existing):,}개")
    print(f"   업데이트 필요: {len(to_update):,}개")
    
    if not to_update:
        print("\n✅ 모든 종목이 이미 구축되었습니다!")
        return
    
    # 배치 처리
    stats = {'updated': 0, 'skipped': 0, 'failed': 0}
    batch_count = (len(to_update) + BATCH_SIZE - 1) // BATCH_SIZE
    
    print(f"\n🔄 총 {batch_count}개 배치 처리 시작...\n")
    
    for i in range(0, len(to_update), BATCH_SIZE):
        batch = to_update[i:i+BATCH_SIZE]
        batch_num = i // BATCH_SIZE + 1
        
        print(f"   [{batch_num}/{batch_count}] 배치 처리 중... ({len(batch)}개)", end='', flush=True)
        
        # 병렬 처리
        args = [(s, target_date) for s in batch]
        with Pool(processes=MAX_WORKERS) as pool:
            results = pool.map(update_single, args)
        
        # 결과 집계
        for r in results:
            stats[r['status']] = stats.get(r['status'], 0) + 1
        
        print(f" ✓ (누적: {sum(stats.values())}/{len(to_update)})")
        
        # 10배치마다 진행 보고
        if batch_num % 10 == 0 or batch_num == batch_count:
            log_progress(stats, len(to_update), start_time)
        
        # API rate limit 방지
        time.sleep(0.5)
    
    # 최종 보고
    elapsed = datetime.now() - start_time
    print("\n" + "="*70)
    print("✅ 병렬 업데이트 완료")
    print("="*70)
    print(f"   총 소요 시간: {str(elapsed).split('.')[0]}")
    print(f"   업데이트: {stats.get('updated', 0):,}")
    print(f"   스킵: {stats.get('skipped', 0):,}")
    print(f"   실패: {stats.get('failed', 0):,}")
    print(f"   처리 속도: {sum(stats.values()) / elapsed.total_seconds() * 60:.0f} 종목/분")
    print("="*70)


def main():
    import sys
    target_date = sys.argv[1] if len(sys.argv) > 1 else None
    parallel_daily_update(target_date)


if __name__ == '__main__':
    main()
