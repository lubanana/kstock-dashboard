#!/usr/bin/env python3
"""
level1_prices.db 역사 데이터 백필
pivot_strategy.db에서 데이터를 마이그레이션하여 level1_prices.db 완성
"""

import sys
sys.path.insert(0, '/root/.openclaw/workspace/strg')

import sqlite3
import pandas as pd
from datetime import datetime, timedelta
from fdr_wrapper import get_price


def migrate_from_pivot_db():
    """pivot_strategy.db에서 level1_prices.db로 데이터 마이그레이션"""
    print("=" * 80)
    print("🔄 level1_prices.db 역사 데이터 백필")
    print("=" * 80)
    
    # 소스 DB (pivot_strategy.db)
    src_conn = sqlite3.connect('data/pivot_strategy.db')
    
    # 대상 DB (level1_prices.db)
    dst_conn = sqlite3.connect('data/level1_prices.db')
    dst_cursor = dst_conn.cursor()
    
    # 테이블 구조 확인
    print("\n📊 소스 DB (pivot_strategy.db) 현황:")
    df = pd.read_sql_query(
        "SELECT COUNT(*) as rows, COUNT(DISTINCT symbol) as symbols, "
        "MIN(date) as start, MAX(date) as end FROM stock_prices",
        src_conn
    )
    print(df.to_string(index=False))
    
    # 대상 테이블 확인
    print("\n📊 대상 DB (level1_prices.db) 현황:")
    dst_cursor.execute("SELECT COUNT(*) FROM price_data")
    current_count = dst_cursor.fetchone()[0]
    print(f"현재 데이터: {current_count:,} rows")
    
    if current_count > 10000:
        print("\n⚠️  이미 충분한 데이터가 있습니다. 마이그레이션을 건ップ합니다.")
        print("   (데이터 덮어쓰기를 원하면 수동으로 진행하세요)")
        src_conn.close()
        dst_conn.close()
        return
    
    # 마이그레이션
    print("\n🚀 마이그레이션 시작...")
    print("-" * 80)
    
    # 배치 처리
    batch_size = 50000
    total_migrated = 0
    
    # 심볼 목록
    symbols_df = pd.read_sql_query(
        "SELECT DISTINCT symbol FROM stock_prices ORDER BY symbol",
        src_conn
    )
    symbols = symbols_df['symbol'].tolist()
    
    print(f"총 {len(symbols)}개 종목 마이그레이션")
    
    for i, symbol in enumerate(symbols):
        try:
            # 소스에서 데이터 조회
            df = pd.read_sql_query(
                f"SELECT * FROM stock_prices WHERE symbol = '{symbol}' ORDER BY date",
                src_conn
            )
            
            if df.empty:
                continue
            
            # 종목 정보 조회 (첫 행에서 추정)
            # name과 market 정보는 없으므로 'Unknown'으로 설정
            # 실제 환경에서는 별도 매핑 테이블 필요
            
            # 컬럼 매핑
            df.rename(columns={
                'symbol': 'code',
                'Open': 'open',
                'High': 'high',
                'Low': 'low',
                'Close': 'close',
                'Volume': 'volume'
            }, inplace=True)
            
            # 추가 컬럼
            df['name'] = 'Unknown'
            df['market'] = 'KOSPI'
            df['change_pct'] = df['close'].pct_change() * 100
            df['ma5'] = df['close'].rolling(5).mean()
            df['ma20'] = df['close'].rolling(20).mean()
            df['ma60'] = df['close'].rolling(60).mean()
            df['rsi'] = None  # 계산 필요
            df['macd'] = None  # 계산 필요
            df['score'] = 50  # 기본값
            df['recommendation'] = 'HOLD'
            df['status'] = 'active'
            df['updated_at'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            
            # 대상 테이블에 저장
            df.to_sql('price_data', dst_conn, if_exists='append', index=False)
            
            total_migrated += len(df)
            
            if (i + 1) % 100 == 0:
                print(f"   {i+1}/{len(symbols)} 종목 완료 ({total_migrated:,} rows)")
            
        except Exception as e:
            print(f"   ⚠️  {symbol} 오류: {e}")
            continue
    
    print("-" * 80)
    print(f"✅ 마이그레이션 완료: {total_migrated:,} rows")
    
    # 결과 확인
    dst_cursor.execute("SELECT COUNT(*) FROM price_data")
    final_count = dst_cursor.fetchone()[0]
    dst_cursor.execute("SELECT MIN(date), MAX(date) FROM price_data")
    date_range = dst_cursor.fetchone()
    
    print(f"\n📊 최종 결과:")
    print(f"   총 데이터: {final_count:,} rows")
    print(f"   기간: {date_range[0]} ~ {date_range[1]}")
    
    src_conn.close()
    dst_conn.close()


def update_stock_info():
    """종목 정보 업데이트 (code → name, market 매핑)"""
    print("\n" + "=" * 80)
    print("📝 종목 정보 업데이트")
    print("=" * 80)
    
    # 종목 정보 로드 (stock_info.json 또는 DB에서)
    try:
        import json
        with open('data/stock_info.json', 'r', encoding='utf-8') as f:
            stock_info = {item['code']: item for item in json.load(f)}
        print(f"종목 정보 로드: {len(stock_info)}개")
    except:
        print("⚠️  stock_info.json 없음, FinanceDataReader로 조회")
        stock_info = {}
    
    conn = sqlite3.connect('data/level1_prices.db')
    cursor = conn.cursor()
    
    # 고유 코드 목록
    cursor.execute("SELECT DISTINCT code FROM price_data WHERE name = 'Unknown'")
    codes = [row[0] for row in cursor.fetchall()]
    
    print(f"업데이트 필요: {len(codes)}개 종목")
    
    updated = 0
    for code in codes:
        if code in stock_info:
            info = stock_info[code]
            cursor.execute(
                "UPDATE price_data SET name = ?, market = ? WHERE code = ?",
                (info.get('name', 'Unknown'), info.get('market', 'KOSPI'), code)
            )
            updated += 1
            
            if updated % 100 == 0:
                print(f"   {updated}개 업데이트...")
    
    conn.commit()
    print(f"✅ {updated}개 종목 정보 업데이트 완료")
    conn.close()


if __name__ == '__main__':
    migrate_from_pivot_db()
    # update_stock_info()  # 종목 정보가 준비되면 실행
