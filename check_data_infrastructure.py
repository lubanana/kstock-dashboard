#!/usr/bin/env python3
"""
한국 주식 데이터 인프라 현황 점검 및 구축 계획
"""

import sqlite3
import os
from pathlib import Path
from datetime import datetime
from typing import Dict, List


def check_database(db_path: str, db_name: str) -> Dict:
    """개별 DB 상태 확인"""
    result = {
        'name': db_name,
        'exists': False,
        'size_mb': 0,
        'tables': [],
        'status': 'N/A'
    }
    
    if not os.path.exists(db_path):
        return result
    
    result['exists'] = True
    result['size_mb'] = round(os.path.getsize(db_path) / (1024 * 1024), 2)
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # 테이블 목록
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
        tables = [row[0] for row in cursor.fetchall()]
        result['tables'] = tables
        
        # 테이블별 통계
        table_stats = {}
        for table in tables:
            try:
                cursor.execute(f'SELECT COUNT(*) FROM "{table}"')
                count = cursor.fetchone()[0]
                table_stats[table] = count
            except:
                table_stats[table] = 'error'
        result['table_stats'] = table_stats
        
        # 특정 DB별 추가 정보
        if 'price_data' in tables:
            try:
                cursor.execute('SELECT COUNT(DISTINCT code) FROM price_data')
                symbols = cursor.fetchone()[0]
                cursor.execute('SELECT MIN(date), MAX(date) FROM price_data')
                dates = cursor.fetchone()
                result['price_data_info'] = {
                    'symbols': symbols,
                    'date_range': f"{dates[0]} ~ {dates[1]}" if dates[0] else 'N/A'
                }
            except:
                pass
        
        if 'stock_prices' in tables:
            try:
                cursor.execute('SELECT COUNT(DISTINCT symbol) FROM stock_prices')
                symbols = cursor.fetchone()[0]
                cursor.execute('SELECT MIN(date), MAX(date) FROM stock_prices')
                dates = cursor.fetchone()
                result['stock_prices_info'] = {
                    'symbols': symbols,
                    'date_range': f"{dates[0]} ~ {dates[1]}" if dates[0] else 'N/A'
                }
            except:
                pass
        
        conn.close()
        result['status'] = 'OK'
        
    except Exception as e:
        result['status'] = f'Error: {str(e)}'
    
    return result


def main():
    data_dir = Path('/root/.openclaw/workspace/strg/data')
    
    # 확인할 DB 목록
    db_files = [
        'level1_prices.db',
        'level1_daily.db',
        'level1_final.db',
        'level1_consolidated.db',
        'minervini_signals.db',
        'dart_cache.db',
        'dart_financial.db',
        'dart_focused.db',
        'pivot_strategy.db',
        'job_queue.db',
        'livermore_signals.db',
    ]
    
    print("=" * 80)
    print("🔍 한국 주식 데이터 인프라 현황 점검")
    print("=" * 80)
    print(f"점검일: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print(f"데이터 디렉토리: {data_dir}")
    print("=" * 80)
    
    results = []
    for db_file in db_files:
        db_path = data_dir / db_file
        result = check_database(str(db_path), db_file)
        results.append(result)
    
    # 결과 출력
    print("\n📊 DB별 현황")
    print("-" * 80)
    print(f"{'DB 이름':<30} {'존재':<6} {'크기(MB)':<12} {'테이블수':<10} {'상태':<10}")
    print("-" * 80)
    
    for r in results:
        exists = '✓' if r['exists'] else '✗'
        size = f"{r['size_mb']:.1f}" if r['exists'] else '-'
        tables = len(r['tables']) if r['exists'] else 0
        print(f"{r['name']:<30} {exists:<6} {size:<12} {tables:<10} {r['status']:<10}")
    
    # 상세 분석
    print("\n" + "=" * 80)
    print("📈 상세 분석")
    print("=" * 80)
    
    for r in results:
        if not r['exists']:
            continue
        
        print(f"\n🗄️  {r['name']} ({r['size_mb']:.1f} MB)")
        print(f"   테이블: {', '.join(r['tables'][:5])}{'...' if len(r['tables']) > 5 else ''}")
        
        if 'table_stats' in r:
            for table, count in list(r['table_stats'].items())[:3]:
                print(f"   - {table}: {count:,} rows")
        
        if 'price_data_info' in r:
            info = r['price_data_info']
            print(f"   📊 종목수: {info['symbols']}, 기간: {info['date_range']}")
        
        if 'stock_prices_info' in r:
            info = r['stock_prices_info']
            print(f"   📊 종목수: {info['symbols']}, 기간: {info['date_range']}")
    
    # 누락 항목 분석
    print("\n" + "=" * 80)
    print("⚠️ 누락/부족 항목 분석")
    print("=" * 80)
    
    missing_dbs = [r['name'] for r in results if not r['exists']]
    if missing_dbs:
        print("\n❌ 존재하지 않는 DB:")
        for db in missing_dbs:
            print(f"   - {db}")
    
    # 가격 데이터 기간 분석
    print("\n📉 가격 데이터 기간 분석:")
    for r in results:
        if 'price_data_info' in r:
            info = r['price_data_info']
            date_range = info['date_range']
            if date_range and '~' in date_range:
                parts = date_range.split(' ~ ')
                if parts[0] == parts[1]:
                    print(f"   ⚠️  {r['name']}: 단일 날짜 데이터 ({date_range}) - 부족!")
                else:
                    print(f"   ✓  {r['name']}: {date_range}")
    
    # 구축 계획
    print("\n" + "=" * 80)
    print("🛠️  데이터 구축 계획")
    print("=" * 80)
    
    plans = [
        {
            'priority': 'P0-긴급',
            'item': 'pivot_strategy.db',
            'description': 'fdr_wrapper 기본 DB, OHLCV 데이터 저장',
            'action': '신규 생성 및 1년치 역사 데이터 수집',
            'est_time': '4시간'
        },
        {
            'priority': 'P1-높음',
            'item': 'level1_prices.db',
            'description': '현재 단일 날짜(3/10) 데이터만 존재',
            'action': '일별 업데이터 구축 및 역사 데이터 백필',
            'est_time': '2시간'
        },
        {
            'priority': 'P1-높음',
            'item': 'daily_pivot_db',
            'description': '피벗 포인트 분석용 일별 데이터',
            'action': 'build_daily_pivot_db.py 실행 및 스케줄링',
            'est_time': '1시간'
        },
        {
            'priority': 'P2-중간',
            'item': '기술적 지표 DB',
            'description': 'RSI, MACD, 이동평균 등 사전 계산',
            'action': '기존 DB에 컬럼 추가 또는 별도 테이블 생성',
            'est_time': '2시간'
        },
        {
            'priority': 'P3-낮음',
            'item': '분봉 데이터',
            'description': '1분/5분/15분/60분봉',
            'action': '필요시 pykrx 또는 CCXT로 구축',
            'est_time': '4시간'
        }
    ]
    
    for plan in plans:
        print(f"\n[{plan['priority']}] {plan['item']}")
        print(f"   설명: {plan['description']}")
        print(f"   작업: {plan['action']}")
        print(f"   예상시간: {plan['est_time']}")
    
    # JSON 저장
    import json
    output = {
        'check_date': datetime.now().strftime('%Y-%m-%d %H:%M'),
        'db_status': results,
        'build_plan': plans
    }
    
    with open('data_infrastructure_status.json', 'w', encoding='utf-8') as f:
        json.dump(output, f, ensure_ascii=False, indent=2, default=str)
    
    print(f"\n✅ 결과 저장: data_infrastructure_status.json")


if __name__ == '__main__':
    main()
