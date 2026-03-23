#!/usr/bin/env python3
"""
Full DB Update - 모든 종목 가격정보 업데이트
Progress report every 10 minutes
"""

import sys
import os
# Unbuffered output
sys.stdout = os.fdopen(sys.stdout.fileno(), 'w', buffering=1)
sys.stderr = os.fdopen(sys.stderr.fileno(), 'w', buffering=1)

sys.path.insert(0, '.')
import sqlite3
from datetime import datetime, timedelta, timezone
from fdr_wrapper import get_price

DB_PATH = 'data/pivot_strategy.db'


def log(message):
    """로그 출력 (flush 즉시)"""
    now = datetime.now(timezone(timedelta(hours=9)))
    print(f"[{now.strftime('%H:%M:%S')}] {message}", flush=True)


def get_all_symbols_from_db():
    """DB에서 모든 종목 조회"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('SELECT DISTINCT symbol FROM stock_prices')
    symbols = [row[0] for row in cursor.fetchall()]
    conn.close()
    return symbols


def get_latest_date(symbol):
    """종목별 최신 날짜"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('SELECT MAX(date) FROM stock_prices WHERE symbol = ?', (symbol,))
    result = cursor.fetchone()
    conn.close()
    return result[0] if result else None


def full_update(target_date=None):
    """전체 종목 업데이트"""
    if target_date is None:
        target_date = datetime.now(timezone(timedelta(hours=9))).strftime('%Y-%m-%d')
    
    symbols = get_all_symbols_from_db()
    total = len(symbols)
    
    log("=" * 70)
    log(f"📅 전체 DB 업데이트 - {target_date}")
    log(f"총 종목: {total}개")
    log("=" * 70)
    
    stats = {'updated': 0, 'skipped': 0, 'failed': 0}
    start_time = datetime.now()
    last_report = start_time
    
    for i, symbol in enumerate(symbols, 1):
        try:
            # 이미 최신 데이터 있는지 확인
            latest = get_latest_date(symbol)
            if latest and latest >= target_date:
                stats['skipped'] += 1
                continue
            
            # 데이터 업데이트
            df = get_price(symbol, start_date=target_date, end_date=target_date)
            
            if not df.empty:
                stats['updated'] += 1
            else:
                stats['failed'] += 1
                
        except Exception as e:
            stats['failed'] += 1
        
        # 10분마다 보고
        elapsed = (datetime.now() - last_report).total_seconds()
        if elapsed >= 600:  # 10 minutes
            processed = stats['updated'] + stats['skipped'] + stats['failed']
            progress = (processed / total) * 100
            elapsed_str = str(datetime.now() - start_time).split('.')[0]
            
            log("")
            log("=" * 60)
            log("📊 10분 간격 진행 보고")
            log("=" * 60)
            log(f"   총 경과: {elapsed_str}")
            log(f"   진행: {processed}/{total} ({progress:.1f}%)")
            log(f"   ✅ 업데이트: {stats['updated']}")
            log(f"   ⏭️ 스킵: {stats['skipped']}")
            log(f"   ❌ 실패: {stats['failed']}")
            log("=" * 60)
            log("")
            
            last_report = datetime.now()
        
        # 진행률 표시 (100개마다)
        if i % 100 == 0:
            processed = stats['updated'] + stats['skipped'] + stats['failed']
            progress = (processed / total) * 100
            log(f"   진행 중... {i}/{total} ({progress:.1f}%)")
    
    # 최종 보고
    log("")
    log("=" * 70)
    log("✅ 전체 업데이트 완료")
    log("=" * 70)
    log(f"총 소요: {str(datetime.now() - start_time).split('.')[0]}")
    log(f"✅ 업데이트: {stats['updated']}")
    log(f"⏭️ 스킵: {stats['skipped']}")
    log(f"❌ 실패: {stats['failed']}")
    log("=" * 70)
    
    return stats


if __name__ == '__main__':
    if len(sys.argv) > 1:
        target = sys.argv[1]
    else:
        target = None  # 오늘 날짜로 자동 설정
    full_update(target)
