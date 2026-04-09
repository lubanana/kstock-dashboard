#!/usr/bin/env python3
"""
Unified Daily Price Updater - 통합 일일 주가 업데이터
======================================================
스캐너가 사용하는 level1_prices.db를 업데이트하는 통합 스크립트

Features:
- level1_prices.db의 price_data 테이블 업데이트
- 병렬 처리로 빠른 데이터 수집
- 자동 지표 계산 (MA, RSI, MACD)
- FinanceDataReader 사용

Usage:
    python3 unified_daily_updater.py --date 2026-04-09
    python3 unified_daily_updater.py  # 오늘 날짜 자동 사용
"""

import sys
sys.path.insert(0, '.')

import pandas as pd
import numpy as np
import sqlite3
import FinanceDataReader as fdr
from datetime import datetime, timedelta
from multiprocessing import Pool, cpu_count
from typing import List, Tuple, Optional
import argparse
import time

# 설정
DB_PATH = 'data/level1_prices.db'
MAX_WORKERS = min(cpu_count(), 8)
BATCH_SIZE = 50


def get_all_symbols() -> List[str]:
    """전체 종목 리스트 로드"""
    symbols = set()
    
    try:
        kospi = fdr.StockListing('KOSPI')
        symbols.update(kospi['Code'].tolist())
        print(f"✅ KOSPI: {len(kospi)} 종목")
    except Exception as e:
        print(f"❌ KOSPI 로드 실패: {e}")
    
    try:
        kosdaq = fdr.StockListing('KOSDAQ')
        symbols.update(kosdaq['Code'].tolist())
        print(f"✅ KOSDAQ: {len(kosdaq)} 종목")
    except Exception as e:
        print(f"❌ KOSDAQ 로드 실패: {e}")
    
    # ETF/ETN 필터링
    exclude_patterns = ['K', 'Q', 'V', 'W', 'T']
    filtered = [s for s in symbols if not any(s.startswith(p) for p in exclude_patterns)]
    
    print(f"📊 총 종목: {len(filtered)}개 (ETF/ETN 필터링 후)")
    return sorted(filtered)


def check_exists(symbol: str, target_date: str) -> bool:
    """해당 종목/날짜 데이터 존재 여부 확인"""
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute(
            'SELECT 1 FROM price_data WHERE code = ? AND date = ? LIMIT 1',
            (symbol, target_date)
        )
        exists = cursor.fetchone() is not None
        conn.close()
        return exists
    except Exception as e:
        print(f"⚠️ DB 체크 오류 ({symbol}): {e}")
        return False


def calculate_indicators(df: pd.DataFrame) -> pd.DataFrame:
    """기술적 지표 계산"""
    if len(df) < 20:
        return df
    
    df = df.copy()
    
    # 이동평균
    df['ma5'] = df['close'].rolling(5, min_periods=1).mean()
    df['ma20'] = df['close'].rolling(20, min_periods=1).mean()
    df['ma60'] = df['close'].rolling(60, min_periods=1).mean()
    
    # RSI
    delta = df['close'].diff()
    gain = delta.where(delta > 0, 0)
    loss = -delta.where(delta < 0, 0)
    avg_gain = gain.ewm(span=14, adjust=False, min_periods=1).mean()
    avg_loss = loss.ewm(span=14, adjust=False, min_periods=1).mean()
    rs = avg_gain / avg_loss.replace(0, np.nan)
    df['rsi'] = 100 - (100 / (1 + rs))
    df['rsi'] = df['rsi'].fillna(50)
    
    # MACD
    ema12 = df['close'].ewm(span=12, adjust=False, min_periods=1).mean()
    ema26 = df['close'].ewm(span=26, adjust=False, min_periods=1).mean()
    df['macd'] = ema12 - ema26
    
    return df


def fetch_and_save(args: Tuple[str, str, str]) -> dict:
    """
    단일 종목 데이터 가져와서 저장
    
    Args:
        args: (symbol, target_date, name)
    
    Returns:
        status dict
    """
    symbol, target_date, name = args
    
    # 이미 있으면 스킵
    if check_exists(symbol, target_date):
        return {'symbol': symbol, 'status': 'skipped', 'name': name}
    
    try:
        # 데이터 조회 (60일치)
        start_date = (datetime.strptime(target_date, '%Y-%m-%d') - timedelta(days=90)).strftime('%Y-%m-%d')
        df = fdr.DataReader(symbol, start=start_date, end=target_date)
        
        if df is None or len(df) < 5:
            return {'symbol': symbol, 'status': 'no_data', 'name': name}
        
        # 컬럼명 표준화
        df = df.rename(columns={
            'Open': 'open',
            'High': 'high',
            'Low': 'low',
            'Close': 'close',
            'Volume': 'volume'
        })
        
        # 지표 계산
        df = calculate_indicators(df)
        
        # target_date 데이터만 추출
        if target_date in df.index.strftime('%Y-%m-%d').values:
            row = df.loc[df.index.strftime('%Y-%m-%d') == target_date].iloc[-1]
        else:
            # 해당 날짜가 없으면 마지막 데이터 사용
            row = df.iloc[-1]
            actual_date = df.index[-1].strftime('%Y-%m-%d')
        
        actual_date = target_date
        
        # 전일 대비 변동률
        if len(df) >= 2:
            prev_close = df['close'].iloc[-2]
            change_pct = (row['close'] - prev_close) / prev_close * 100
        else:
            change_pct = 0
        
        # DB 저장
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT OR REPLACE INTO price_data 
            (code, name, date, open, high, low, close, volume, 
             change_pct, ma5, ma20, ma60, rsi, macd, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, datetime('now'))
        ''', (
            symbol, name, actual_date,
            float(row['open']), float(row['high']), float(row['low']), 
            float(row['close']), int(row['volume']),
            float(change_pct),
            float(row.get('ma5', 0)), float(row.get('ma20', 0)), float(row.get('ma60', 0)),
            float(row.get('rsi', 50)), float(row.get('macd', 0))
        ))
        
        conn.commit()
        conn.close()
        
        return {
            'symbol': symbol, 
            'status': 'success', 
            'name': name,
            'price': float(row['close']),
            'change_pct': float(change_pct)
        }
        
    except Exception as e:
        return {'symbol': symbol, 'status': 'error', 'name': name, 'error': str(e)}


def init_db():
    """DB 테이블 초기화"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS price_data (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            code TEXT NOT NULL,
            name TEXT,
            market TEXT,
            date TEXT NOT NULL,
            open REAL,
            high REAL,
            low REAL,
            close REAL,
            volume INTEGER,
            change_pct REAL,
            ma5 REAL,
            ma20 REAL,
            ma60 REAL,
            rsi REAL,
            macd REAL,
            score REAL,
            recommendation TEXT,
            status TEXT,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(code, date)
        )
    ''')
    
    # 인덱스 생성
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_price_code ON price_data(code)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_price_date ON price_data(date)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_price_code_date ON price_data(code, date)')
    
    conn.commit()
    conn.close()
    print("✅ DB 초기화 완료")


def batch_update(target_date: str, workers: int = MAX_WORKERS):
    """
    전체 종목 배치 업데이트
    
    Args:
        target_date: 업데이트할 날짜 (YYYY-MM-DD)
        workers: 병렬 워커 수
    """
    print(f"\n{'='*60}")
    print(f"📅 통합 일일 주가 업데이트 - {target_date}")
    print(f"{'='*60}\n")
    
    # DB 초기화
    init_db()
    
    # 종목 리스트 로드
    symbols = get_all_symbols()
    
    # 종목명 매핑
    name_map = {}
    try:
        kospi = fdr.StockListing('KOSPI')
        for _, row in kospi.iterrows():
            name_map[row['Code']] = row.get('Name', row['Code'])
    except:
        pass
    
    try:
        kosdaq = fdr.StockListing('KOSDAQ')
        for _, row in kosdaq.iterrows():
            name_map[row['Code']] = row.get('Name', row['Code'])
    except:
        pass
    
    # 작업 큐 생성
    tasks = [(s, target_date, name_map.get(s, s)) for s in symbols]
    
    # 통계
    stats = {'success': 0, 'skipped': 0, 'no_data': 0, 'error': 0}
    
    print(f"\n🔄 병렬 처리 시작 (workers: {workers})\n")
    start_time = time.time()
    
    # 병렬 처리
    with Pool(processes=workers) as pool:
        results = pool.imap_unordered(fetch_and_save, tasks)
        
        for i, result in enumerate(results, 1):
            status = result['status']
            stats[status] = stats.get(status, 0) + 1
            
            # 진행 상황 출력
            if i % 100 == 0 or i == len(tasks):
                elapsed = time.time() - start_time
                rate = i / elapsed if elapsed > 0 else 0
                print(f"   진행: {i}/{len(tasks)} ({i/len(tasks)*100:.1f}%) | "
                      f"성공:{stats['success']} 스킵:{stats['skipped']} "
                      f"에러:{stats['error']} | {rate:.1f}종목/초")
    
    elapsed = time.time() - start_time
    
    print(f"\n{'='*60}")
    print(f"✅ 업데이트 완료 - {target_date}")
    print(f"{'='*60}")
    print(f"📊 통계:")
    print(f"   - 성공: {stats['success']}종목")
    print(f"   - 스킵(이미존재): {stats['skipped']}종목")
    print(f"   - 데이터없음: {stats['no_data']}종목")
    print(f"   - 에러: {stats['error']}종목")
    print(f"⏱️  소요시간: {elapsed:.1f}초 ({elapsed/60:.1f}분)")
    print(f"{'='*60}\n")
    
    return stats


def main():
    """메인 실행"""
    parser = argparse.ArgumentParser(description='통합 일일 주가 업데이터')
    parser.add_argument('--date', type=str, default=None, 
                       help='업데이트할 날짜 (YYYY-MM-DD), 미지정시 오늘')
    parser.add_argument('--workers', type=int, default=MAX_WORKERS,
                       help=f'병렬 워커 수 (기본: {MAX_WORKERS})')
    args = parser.parse_args()
    
    # 날짜 설정
    if args.date:
        target_date = args.date
    else:
        target_date = datetime.now().strftime('%Y-%m-%d')
    
    # 실행
    batch_update(target_date, workers=args.workers)


if __name__ == '__main__':
    main()
