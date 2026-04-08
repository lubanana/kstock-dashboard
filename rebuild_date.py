#!/usr/bin/env python3
"""
특정일 데이터 강제 재구축
"""

import sys
sys.path.insert(0, '/root/.openclaw/workspace/strg')

import FinanceDataReader as fdr
import pandas as pd
from datetime import datetime
from concurrent.futures import ProcessPoolExecutor, as_completed
from fdr_wrapper import get_price
from v2.core.data_manager import DataManager


def process_stock(args):
    """개별 종목 처리 (모듈 레벨 함수)"""
    code, target_date = args
    try:
        df = get_price(code, target_date, target_date)
        if df is not None and len(df) > 0:
            return ('success', code)
        return ('empty', code)
    except Exception as e:
        return ('error', code, str(e))


def rebuild_date(target_date: str, max_workers: int = 4):
    """
    특정 날짜 데이터 강제 재구축
    """
    print(f"🚀 {target_date} 데이터 재구축 시작")
    print("=" * 60)
    
    # 종목 리스트
    stocks = fdr.StockListing('KOSPI')
    stocks_kosdaq = fdr.StockListing('KOSDAQ')
    all_stocks = pd.concat([stocks, stocks_kosdaq])
    
    # ETF/ETN/스팩 필터링
    exclude_patterns = ['ETF', 'ETN', '스팩']
    for pattern in exclude_patterns:
        all_stocks = all_stocks[~all_stocks['Name'].str.contains(pattern, na=False)]
    
    all_codes = all_stocks['Code'].tolist()
    print(f"📋 총 {len(all_codes)}개 종목")
    
    # 이미 있는 종목 확인
    dm = DataManager()
    conn = dm._get_connection()
    existing = pd.read_sql_query(
        f"SELECT DISTINCT code FROM price_data WHERE date='{target_date}'", 
        conn
    )
    existing_codes = set(existing['code'].tolist())
    conn.close()
    
    print(f"✅ 이미 구축: {len(existing_codes)}개")
    
    # 누락 종목
    missing_codes = [c for c in all_codes if c not in existing_codes]
    print(f"⚠️ 누락: {len(missing_codes)}개")
    
    if len(missing_codes) == 0:
        print("\n✅ 이미 완료!")
        return
    
    # 병렬 처리
    print(f"\n🔧 병렬 구축 시작 (workers: {max_workers})")
    print("=" * 60)
    
    updated = 0
    failed = 0
    
    # 작업 인자 준비
    args_list = [(code, target_date) for code in missing_codes]
    
    with ProcessPoolExecutor(max_workers=max_workers) as executor:
        futures = {executor.submit(process_stock, args): args[0] for args in args_list}
        
        for i, future in enumerate(as_completed(futures)):
            result = future.result()
            
            if result[0] == 'success':
                updated += 1
            else:
                failed += 1
            
            # 진행률 출력 (100개마다)
            if (i + 1) % 100 == 0:
                progress = (i + 1) / len(missing_codes) * 100
                print(f"   [{progress:.1f}%] 성공: {updated}, 실패: {failed}")
    
    print("=" * 60)
    print(f"✅ 완료: 성공 {updated}개, 실패 {failed}개")
    
    # 최종 확인
    conn = dm._get_connection()
    final_count = pd.read_sql_query(
        f"SELECT COUNT(*) as cnt FROM price_data WHERE date='{target_date}'",
        conn
    ).iloc[0]['cnt']
    conn.close()
    
    print(f"📊 최종: {target_date} = {final_count}종목")


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser()
    parser.add_argument('--date', required=True, help='YYYYMMDD')
    parser.add_argument('--workers', type=int, default=4)
    
    args = parser.parse_args()
    
    # 날짜 포맷 변환
    date_str = f"{args.date[:4]}-{args.date[4:6]}-{args.date[6:8]}"
    
    rebuild_date(date_str, args.workers)
