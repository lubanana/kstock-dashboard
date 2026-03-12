#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Import KOSPI Stocks from GitHub to Local Database
==================================================
kospi_stocks.json 파일을 로컬 SQLite DB에 임포트하는 스크립트
"""

import json
import sqlite3
import requests
from pathlib import Path
from typing import List, Dict


def download_kospi_stocks(url: str = None) -> List[Dict]:
    """
    GitHub에서 kospi_stocks.json 다운로드 또는 로컬 파일 로드
    """
    if url is None:
        url = "https://raw.githubusercontent.com/lubanana/kstock-dashboard/main/data/kospi_stocks.json"
    
    print(f"📥 데이터 다운로드 중...")
    
    try:
        response = requests.get(url, timeout=30)
        response.raise_for_status()
        data = response.json()
        print(f"✅ {data.get('count', 0)}개 종목 로드됨 (업데이트: {data.get('updated_at', 'N/A')})")
        return data.get('stocks', [])
    except Exception as e:
        print(f"⚠️ 다운로드 실패: {e}")
        # 로컬 파일 시도
        local_path = Path(__file__).parent / "kospi_stocks.json"
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
    
    # 인덱스 생성
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_stock_market ON stock_info(market)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_stock_name ON stock_info(name)')
    
    # 데이터 삽입 (UPSERT)
    inserted = 0
    updated = 0
    
    for stock in stocks:
        symbol = stock.get('code', '')
        name = stock.get('name', '')
        market = stock.get('market', 'KOSPI')
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


def get_stock_info(symbol: str, db_path: str = './data/pivot_strategy.db') -> Dict:
    """
    특정 종목 정보 조회
    """
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    cursor.execute('SELECT * FROM stock_info WHERE symbol = ?', (symbol,))
    row = cursor.fetchone()
    conn.close()
    
    if row:
        return dict(row)
    return {}


def search_stocks_by_name(keyword: str, db_path: str = './data/pivot_strategy.db') -> List[Dict]:
    """
    종목명으로 검색
    """
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT * FROM stock_info 
        WHERE name LIKE ? 
        ORDER BY name
    ''', (f'%{keyword}%',))
    
    rows = cursor.fetchall()
    conn.close()
    
    return [dict(row) for row in rows]


def get_all_stocks(market: str = None, db_path: str = './data/pivot_strategy.db') -> List[Dict]:
    """
    전체 종목 목록 조회
    """
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    if market:
        cursor.execute('''
            SELECT * FROM stock_info 
            WHERE market = ?
            ORDER BY symbol
        ''', (market,))
    else:
        cursor.execute('SELECT * FROM stock_info ORDER BY symbol')
    
    rows = cursor.fetchall()
    conn.close()
    
    return [dict(row) for row in rows]


def export_to_json(db_path: str = './data/pivot_strategy.db', output_path: str = './data/stock_list.json'):
    """
    DB의 종목 정보를 JSON으로 낳춰
    """
    stocks = get_all_stocks(db_path=db_path)
    
    data = {
        'count': len(stocks),
        'stocks': stocks
    }
    
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    
    print(f"📁 JSON 낳춰 완료: {output_path} ({len(stocks)}개 종목)")


def main():
    """
    메인 실행 함수
    """
    print("=" * 60)
    print("KOSPI 종목 데이터 임포트")
    print("=" * 60)
    
    # 1. GitHub에서 데이터 다운로드
    stocks = download_kospi_stocks()
    
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
    
    # 5. JSON으로도 낳춰 (백업용)
    export_to_json()
    
    print("\n✅ 모든 작업 완료!")


if __name__ == "__main__":
    main()
