#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Local Database Usage Examples
=============================
local_db.py 사용 예시
"""

from local_db import LocalDB, init_database
from pivot_strategy import PivotPointStrategy
import FinanceDataReader as fdr
import pandas as pd
from datetime import datetime, timedelta


def example_1_basic_usage():
    """
    예시 1: 기본 사용법
    """
    print("=" * 60)
    print("예시 1: 데이터베이스 기본 사용법")
    print("=" * 60)
    
    # 데이터베이스 초기화
    db = init_database('./data/my_strategy.db')
    
    # 주가 데이터 수집 및 저장
    print("\n📊 삼성전자 데이터 수집 중...")
    df = fdr.DataReader('005930', '2024-01-01', '2024-03-31')
    db.save_prices(df, '005930')
    
    # 저장된 데이터 조회
    print("\n📋 저장된 데이터 조회:")
    cached_df = db.get_prices('005930', '2024-01-01', '2024-01-31')
    print(cached_df.head())
    
    # 캐시 확인
    last_update = db.get_last_update('005930')
    print(f"\n💾 마지막 업데이트: {last_update}")
    
    db.close()


def example_2_backtest_with_cache():
    """
    예시 2: 캐시를 활용한 백테스트
    """
    print("\n" + "=" * 60)
    print("예시 2: 캐시를 활용한 백테스트")
    print("=" * 60)
    
    db = init_database()
    symbol = '035420'  # NAVER
    start_date = '2024-01-01'
    end_date = '2024-12-31'
    
    # 캐시 확인
    cached_data = db.get_prices(symbol, start_date, end_date)
    
    if cached_data.empty:
        print(f"📥 {symbol} 데이터 캐시 없음 → API 호출")
        df = fdr.DataReader(symbol, start_date, end_date)
        db.save_prices(df, symbol)
    else:
        print(f"💾 {symbol} 데이터 캐시 사용 ({len(cached_data)}건)")
        df = cached_data
    
    # 백테스트 실행
    strategy = PivotPointStrategy(
        symbol=symbol,
        start_date=start_date,
        end_date=end_date,
        initial_capital=10_000_000,
        pivot_period=20,
        volume_threshold=1.5,
    )
    
    result, trades_df = strategy.run_backtest()
    
    # 결과 저장
    backtest_id = db.save_backtest(strategy, result, trades_df)
    print(f"\n✅ 백테스트 결과 저장됨 (ID: {backtest_id})")
    
    db.close()


def example_3_portfolio_management():
    """
    예시 3: 포트폴리오 관리
    """
    print("\n" + "=" * 60)
    print("예시 3: 포트폴리오 관리")
    print("=" * 60)
    
    db = init_database()
    
    # 포지션 추가
    print("\n📈 포지션 추가:")
    db.add_position('005930', '2024-03-20', 76900, 39, '1차 진입')
    db.add_position('000660', '2024-03-15', 145000, 20, 'SK하이닉스')
    
    # 포지션 업데이트 (현재가 반영)
    print("\n🔄 포지션 업데이트:")
    db.update_position('005930', 75000)  # 현재가 75,000원
    db.update_position('000660', 150000)  # 현재가 150,000원
    
    # 포트폴리오 조회
    print("\n📊 현재 포트폴리오:")
    portfolio = db.get_portfolio()
    print(portfolio[['symbol', 'entry_price', 'current_price', 'shares', 
                     'unrealized_pnl', 'unrealized_return_pct']].to_string())
    
    db.close()


def example_4_scan_and_save():
    """
    예시 4: 스캔 결과 저장 및 조회
    """
    print("\n" + "=" * 60)
    print("예시 4: 스캔 결과 관리")
    print("=" * 60)
    
    db = init_database()
    
    # 예시 스캔 결과
    scan_results = pd.DataFrame({
        'symbol': ['005930', '035420', '000660'],
        'name': ['삼성전자', 'NAVER', 'SK하이닉스'],
        'market': ['KOSPI', 'KOSPI', 'KOSPI'],
        'close': [76900, 350000, 145000],
        'volume': [15000000, 500000, 8000000],
        'volume_ratio': [1.8, 2.1, 1.6],
        'price_change_pct': [2.5, 3.2, 1.8],
        'score': [85.5, 92.3, 78.1]
    })
    
    # 오늘 날짜로 저장
    today = datetime.now().strftime('%Y-%m-%d')
    db.save_scan_results(scan_results, today)
    
    # 저장된 결과 조회
    print(f"\n📋 {today} 스캔 결과:")
    saved_results = db.get_scan_results(scan_date=today, min_score=80)
    print(saved_results.to_string())
    
    db.close()


def example_5_batch_backtest():
    """
    예시 5: 여러 종목 일괄 백테스트
    """
    print("\n" + "=" * 60)
    print("예시 5: 여러 종목 일괄 백테스트")
    print("=" * 60)
    
    db = init_database()
    
    symbols = ['005930', '035420', '000660']
    start_date = '2024-01-01'
    end_date = '2024-12-31'
    
    results = []
    
    for symbol in symbols:
        print(f"\n🔍 {symbol} 백테스트 중...")
        
        # 캐시 확인 및 데이터 수집
        cached = db.get_prices(symbol, start_date, end_date)
        if cached.empty:
            df = fdr.DataReader(symbol, start_date, end_date)
            db.save_prices(df, symbol)
        
        # 백테스트
        strategy = PivotPointStrategy(
            symbol=symbol,
            start_date=start_date,
            end_date=end_date,
            initial_capital=10_000_000,
            pivot_period=20,
            volume_threshold=1.5,
        )
        
        result, trades_df = strategy.run_backtest()
        backtest_id = db.save_backtest(strategy, result, trades_df)
        
        results.append({
            'symbol': symbol,
            'return': result.final_return,
            'mdd': result.mdd,
            'trades': len(result.trades)
        })
    
    # 결과 비교
    print("\n📊 종목별 백테스트 결과 비교:")
    results_df = pd.DataFrame(results)
    print(results_df.to_string(index=False))
    
    # 전체 히스토리 조회
    print("\n📋 저장된 백테스트 히스토리:")
    history = db.get_backtest_history()
    print(history[['symbol', 'total_return_pct', 'mdd_pct', 'total_trades', 'created_at']].to_string())
    
    db.close()


def example_6_data_export():
    """
    예시 6: 데이터 낳춰 (CSV)
    """
    print("\n" + "=" * 60)
    print("예시 6: 데이터 낳춰")
    print("=" * 60)
    
    db = init_database()
    
    # 백테스트 결과 낳춰
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    db.export_to_csv('backtest_results', f'./reports/backtest_history_{timestamp}.csv')
    
    db.close()


if __name__ == "__main__":
    print("🚀 Local Database 사용 예시\n")
    
    # 원하는 예시 실행 (주석 해제)
    
    # example_1_basic_usage()
    # example_2_backtest_with_cache()
    # example_3_portfolio_management()
    # example_4_scan_and_save()
    # example_5_batch_backtest()
    # example_6_data_export()
    
    # 한번에 모두 실행
    example_1_basic_usage()
    example_2_backtest_with_cache()
    example_3_portfolio_management()
    example_4_scan_and_save()
    
    print("\n" + "=" * 60)
    print("모든 예시 완료!")
    print("=" * 60)
