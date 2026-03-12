#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Stock List Usage Examples
=========================
DB에 저장된 종목 리스트 활용 예시
"""

from local_db import LocalDB
from import_kospi_stocks import get_stock_info, search_stocks_by_name, get_all_stocks
import FinanceDataReader as fdr


def example_1_search_stock():
    """
    예시 1: 종목 검색
    """
    print("=" * 60)
    print("예시 1: 종목 검색")
    print("=" * 60)
    
    # 삼성전자 검색
    result = search_stocks_by_name("삼성")
    print(f"\n'삼성' 검색 결과: {len(result)}개")
    for stock in result[:5]:
        print(f"   - {stock['symbol']}: {stock['name']}")
    
    # 특정 종목 정보 조회
    info = get_stock_info("005930")
    print(f"\n📊 삼성전자 정보:")
    print(f"   - 코드: {info.get('symbol')}")
    print(f"   - 이름: {info.get('name')}")
    print(f"   - 시장: {info.get('market')}")
    print(f"   - ISIN: {info.get('isin')}")


def example_2_batch_download():
    """
    예시 2: 전체 종목 주가 데이터 다운로드 (테스트용 10개만)
    """
    print("\n" + "=" * 60)
    print("예시 2: 주가 데이터 다운로드 (10개 샘플)")
    print("=" * 60)
    
    db = LocalDB()
    
    # 모든 종목 조회
    all_stocks = get_all_stocks()
    
    # 테스트용 10개만
    sample_stocks = all_stocks[:10]
    
    print(f"\n📥 {len(sample_stocks)}개 종목 주가 다운로드 중...")
    
    for stock in sample_stocks:
        symbol = stock['symbol']
        name = stock['name']
        
        # 이미 캐시된 데이터 확인
        cached = db.get_prices(symbol)
        
        if not cached.empty:
            print(f"   ✅ {symbol} ({name}): 캐시됨 ({len(cached)}일)")
        else:
            # FinanceDataReader로 다운로드
            try:
                df = fdr.DataReader(symbol, '2024-01-01', '2024-12-31')
                if not df.empty:
                    db.save_prices(df, symbol)
                    print(f"   💾 {symbol} ({name}): 다운로드 완료 ({len(df)}일)")
            except Exception as e:
                print(f"   ⚠️ {symbol} ({name}): 실패 - {e}")
    
    db.close()


def example_3_scan_with_stock_list():
    """
    예시 3: 스캐너에 종목 리스트 연동
    """
    print("\n" + "=" * 60)
    print("예시 3: 스캐너용 종목 리스트 준비")
    print("=" * 60)
    
    # KOSPI 종목만 필터링 (ETF 제외)
    all_stocks = get_all_stocks()
    
    # ETF 제외 (일반적으로 ETF는 symbol이 숫자가 아닌 경우도 있음)
    # 또는 특정 패턴으로 필터링
    kospi_stocks = [
        s for s in all_stocks 
        if s['market'] == 'KOSPI' 
        and not any(x in s['name'] for x in ['ETF', '레버리지', '인버스', '선물'])
    ][:50]  # 테스트용 50개만
    
    print(f"\n📊 스캔 대상 종목: {len(kospi_stocks)}개")
    print("\n상위 10개:")
    for stock in kospi_stocks[:10]:
        print(f"   - {stock['symbol']}: {stock['name']}")
    
    # 스캔 대상 리스트 저장
    import json
    with open('./data/scan_target.json', 'w', encoding='utf-8') as f:
        json.dump(kospi_stocks, f, ensure_ascii=False, indent=2)
    
    print(f"\n💾 스캔 대상 리스트 저장: ./data/scan_target.json")


def example_4_update_stock_prices():
    """
    예시 4: 특정 종목 주가 업데이트
    """
    print("\n" + "=" * 60)
    print("예시 4: 주가 데이터 업데이트")
    print("=" * 60)
    
    db = LocalDB()
    
    # 삼성전자 최신 데이터
    symbol = "005930"
    
    # 마지막 업데이트 날짜 확인
    last_update = db.get_last_update(symbol)
    print(f"\n📊 삼성전자 ({symbol})")
    print(f"   - 마지막 업데이트: {last_update or '없음'}")
    
    # 최신 데이터 다운로드
    df = fdr.DataReader(symbol, '2024-01-01')
    db.save_prices(df, symbol)
    
    # 다시 확인
    last_update = db.get_last_update(symbol)
    print(f"   - 업데이트 후: {last_update}")
    
    # 데이터 조회
    prices = db.get_prices(symbol, '2024-01-01', '2024-01-31')
    print(f"   - 저장된 데이터: {len(prices)}일")
    print(prices.head())
    
    db.close()


def example_5_integrated_scanner():
    """
    예시 5: 종목 리스트와 스캐너 통합
    """
    print("\n" + "=" * 60)
    print("예시 5: 통합 스캐너 실행")
    print("=" * 60)
    
    from multi_stock_scanner import MultiStockScanner
    
    # DB에서 종목 리스트 가져오기
    all_stocks = get_all_stocks()
    
    # 상위 20개만 테스트
    target_symbols = [s['symbol'] for s in all_stocks[:20]]
    
    print(f"\n🔍 {len(target_symbols)}개 종목 스캔 시작...")
    
    scanner = MultiStockScanner(
        pivot_period=20,
        volume_threshold=1.5,
    )
    
    # 스캔 실행
    results = []
    for symbol in target_symbols:
        result = scanner.scan_stock(symbol)
        if result:
            results.append(result)
    
    print(f"\n✅ 신호 감지: {len(results)}개 종목")
    
    if results:
        import pandas as pd
        df = pd.DataFrame(results)
        print(df[['symbol', 'name', 'close', 'volume_ratio']].to_string(index=False))


if __name__ == "__main__":
    print("🚀 Stock List 활용 예시\n")
    
    # 원하는 예시 실행
    example_1_search_stock()
    example_2_batch_download()
    example_3_scan_with_stock_list()
    # example_4_update_stock_prices()  # API 호출이 많아 주석 처리
    # example_5_integrated_scanner()   # API 호출이 많아 주석 처리
    
    print("\n" + "=" * 60)
    print("모든 예시 완료!")
    print("=" * 60)
