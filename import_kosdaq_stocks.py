#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Import KOSDAQ Stocks from GitHub to Local Database
===================================================
kosdaq_stocks.json 파일을 로컬 SQLite DB에 임포트하는 스크립트
"""

import json
import sqlite3
import requests
from pathlib import Path
from typing import List, Dict


def download_kosdaq_stocks(url: str = None) -> List[Dict]:
    """
    GitHub에서 kosdaq_stocks.json 다운로드 또는 로컬 파일 로드
    """
    if url is None:
        url = "https://raw.githubusercontent.com/lubanana/kstock-dashboard/main/data/kosdaq_stocks.json"
    
    print(f"📥 KOSDAQ 데이터 다운로드 중...")
    
    try:
        response = requests.get(url, timeout=30)
        response.raise_for_status()
        data = response.json()
        print(f"✅ {data.get('count', 0)}개 종목 로드됨 (업데이트: {data.get('updated_at', 'N/A')})")
        return data.get('stocks', [])
    except Exception as e:
        print(f"⚠️ 다운로드 실패: {e}")
        # 로컬 파일 시도
        local_path = Path(__file__).parent / "kosdaq_stocks.json"
        if local_path.exists():
            with open(local_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                return data.get('stocks', [])
        return []


def import_to_database(stocks: List[Dict], db_path: str = './data/pivot_strategy.db'):
    """
    종목 데이터를 SQLite DB에 임포트
    """
    Path(db_path).parent.mkdir(parents=True, exist_ok=True)
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # stock_info 테이블이 없으면 생성
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS stock_info (
            symbol TEXT PRIMARY KEY,
            name TEXT,
            market TEXT,
            sector TEXT,
            isin TEXT,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # 데이터 삽입 (UPSERT)
    inserted = 0
    updated = 0
    
    for stock in stocks:
        # KOSDAQ 심볼에서 .KQ 제거
        symbol = stock.get('code', '')
        name = stock.get('name', '')
        market = stock.get('market', 'KOSDAQ')
        isin = stock.get('isin', '')
        
        # 이미 존재하는지 확인
        cursor.execute('SELECT 1 FROM stock_info WHERE symbol = ?', (symbol,))
        exists = cursor.fetchone() is not None
        
        if exists:
            cursor.execute('''
                UPDATE stock_info 
                SET name = ?, market = ?, isin = ?, updated_at = CURRENT_TIMESTAMP
                WHERE symbol = ?
            ''', (name, market, isin, symbol))
            updated += 1
        else:
            cursor.execute('''
                INSERT INTO stock_info (symbol, name, market, isin)
                VALUES (?, ?, ?, ?)
            ''', (symbol, name, market, isin))
            inserted += 1
    
    conn.commit()
    conn.close()
    
    print(f"✅ DB 임포트 완료: 신규 {inserted}개, 업데이트 {updated}개")
    return inserted, updated


def main():
    """
    메인 실행 함수
    """
    print("=" * 60)
    print("KOSDAQ 종목 데이터 임포트")
    print("=" * 60)
    
    # 1. GitHub에서 데이터 다운로드
    stocks = download_kosdaq_stocks()
    
    if not stocks:
        print("❌ 종목 데이터를 가져올 수 없습니다.")
        return
    
    # 2. DB에 임포트
    inserted, updated = import_to_database(stocks)
    
    # 3. 결과 출력
    print("\n📊 임포트 결과:")
    print(f"   - 총 종목 수: {inserted + updated}개")
    print(f"   - 신규 추가: {inserted}개")
    print(f"   - 업데이트: {updated}개")
    
    # 4. 샘플 조회
    print("\n📝 샘플 종목 (처음 5개):")
    sample = stocks[:5]
    for s in sample:
        print(f"   - {s['code']}: {s['name']}")
    
    print("\n✅ 모든 작업 완료!")


if __name__ == "__main__":
    main()
