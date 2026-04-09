#!/usr/bin/env python3
"""
빠른 누락 데이터 백필 (Fast Missing Data Backfill)
=================================================
누락된 특정 날짜의 데이터만 빠르게 채우는 프로그램

Usage:
    python3 fast_backfill.py --date 2026-04-09
"""

import sqlite3
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import FinanceDataReader as fdr
import time
import sys

DB_PATH = 'data/level1_prices.db'
BATCH_SIZE = 50


def get_missing_stocks(target_date: str) -> list:
    """누락 종목 리스트 조회"""
    conn = sqlite3.connect(DB_PATH)
    
    # target_date 기준 전일
    prev_date = (datetime.strptime(target_date, '%Y-%m-%d') - timedelta(days=1)).strftime('%Y-%m-%d')
    
    cursor = conn.execute('''
        SELECT DISTINCT p.code, p.name 
        FROM price_data p
        WHERE p.date = ?
        AND p.code NOT IN (
            SELECT DISTINCT code FROM price_data WHERE date = ?
        )
    ''', (prev_date, target_date))
    
    missing = [(r[0], r[1]) for r in cursor.fetchall()]
    conn.close()
    
    return missing


def fetch_and_insert(code: str, name: str, target_date: str) -> bool:
    """단일 종목 데이터 수집 및 삽입"""
    try:
        # 3일치 데이터 수집 (지표 계산용)
        start = (datetime.strptime(target_date, '%Y-%m-%d') - timedelta(days=5)).strftime('%Y-%m-%d')
        df = fdr.DataReader(code, start=start)
        
        if df is None or df.empty:
            return False
        
        # target_date만 필터
        df = df.reset_index()
        df['Date'] = pd.to_datetime(df['Date'])
        df = df[df['Date'].dt.strftime('%Y-%m-%d') == target_date]
        
        if df.empty:
            return False
        
        # 컬럼 변환
        row = df.iloc[0]
        data = {
            'date': target_date,
            'code': code,
            'name': name,
            'open': float(row.get('Open', 0)),
            'high': float(row.get('High', 0)),
            'low': float(row.get('Low', 0)),
            'close': float(row.get('Close', 0)),
            'volume': int(row.get('Volume', 0)),
            'change_pct': float(row.get('Change', 0)) if not pd.isna(row.get('Change')) else 0
        }
        
        # 지표 계산을 위해 과거 데이터도 가져오기
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.execute('''
            SELECT close, volume FROM price_data 
            WHERE code = ? AND date < ?
            ORDER BY date DESC LIMIT 60
        ''', (code, target_date))
        
        hist = cursor.fetchall()
        if len(hist) >= 20:
            closes = [h[0] for h in reversed(hist)] + [data['close']]
            
            # MA 계산
            data['ma5'] = np.mean(closes[-5:])
            data['ma20'] = np.mean(closes[-20:])
            if len(closes) >= 60:
                data['ma60'] = np.mean(closes[-60:])
            else:
                data['ma60'] = None
            
            # RSI 계산
            deltas = np.diff(closes[-15:])
            gains = np.where(deltas > 0, deltas, 0)
            losses = np.where(deltas < 0, -deltas, 0)
            avg_gain = np.mean(gains[-14:]) if len(gains) >= 14 else 0
            avg_loss = np.mean(losses[-14:]) if len(losses) >= 14 else 0
            
            if avg_loss != 0:
                rs = avg_gain / avg_loss
                data['rsi'] = 100 - (100 / (1 + rs))
            else:
                data['rsi'] = 50
        else:
            data['ma5'] = data['ma20'] = data['ma60'] = data['rsi'] = None
        
        # 삽입
        conn.execute('''
            INSERT OR REPLACE INTO price_data 
            (date, code, name, open, high, low, close, volume, change_pct, ma5, ma20, ma60, rsi)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            data['date'], data['code'], data['name'], data['open'], data['high'],
            data['low'], data['close'], data['volume'], data['change_pct'],
            data['ma5'], data['ma20'], data['ma60'], data['rsi']
        ))
        conn.commit()
        conn.close()
        
        return True
        
    except Exception as e:
        return False


def main():
    target_date = '2026-04-09'
    
    print(f"{'='*60}")
    print(f"🚀 빠른 누락 데이터 백필: {target_date}")
    print(f"{'='*60}\n")
    
    # 누락 종목 확인
    missing = get_missing_stocks(target_date)
    print(f"누락 종목: {len(missing)}개\n")
    
    if not missing:
        print("✅ 누락된 데이터 없음")
        return
    
    # 진행
    success = 0
    failed = 0
    
    for i, (code, name) in enumerate(missing):
        if fetch_and_insert(code, name, target_date):
            success += 1
            print(f"✅ {code} ({name})")
        else:
            failed += 1
            print(f"❌ {code}")
        
        if (i + 1) % 10 == 0:
            print(f"\n진행: {i+1}/{len(missing)} (성공: {success}, 실패: {failed})\n")
        
        time.sleep(0.05)  # API 부하 방지
    
    print(f"\n{'='*60}")
    print(f"완료: 성공 {success}개, 실패 {failed}개")
    print(f"{'='*60}")


if __name__ == '__main__':
    main()
