#!/usr/bin/env python3
"""
어제(2026-03-11) 종가 기준 스캐너 실행
"""

from datetime import datetime, timedelta
from multi_stock_scanner import MultiStockScanner
from import_kospi_stocks import get_all_stocks
import pandas as pd

print('🔍 어제(2026-03-11) 종가 기준 스캔 시작')
print('=' * 60)

# 어제 날짜 설정
yesterday = '2026-03-11'

# 스캐너 초기화 (테스트용 50개 종목만)
scanner = MultiStockScanner(
    pivot_period=20,
    volume_threshold=1.5,
    min_price=1000,
    min_volume=100000,
    max_stocks=50  # 테스트용 50개
)

# 종목 리스트 가져오기
stocks = get_all_stocks()
target_stocks = stocks[:50]  # 상위 50개

print(f'\n📊 대상 종목: {len(target_stocks)}개')
print(f'📅 기준일: {yesterday}')

# 스캔 실행
results = []
for i, stock in enumerate(target_stocks):
    symbol = stock['symbol']
    name = stock['name']
    market = stock['market']
    
    print(f'[{i+1}/{len(target_stocks)}] {symbol} {name}...', end=' ', flush=True)
    
    result = scanner.scan_stock(symbol, name, market)
    if result:
        results.append(result)
        vol_ratio = result['volume_ratio']
        print(f'✅ 신호 감지! (거래량 {vol_ratio:.1f}배)')
    else:
        print('❌')

print('\n' + '='*60)
print(f'📈 스캔 완료: {len(results)}개 종목 신호 감지')

if results:
    df = pd.DataFrame(results)
    df = df.sort_values('volume_ratio', ascending=False)
    
    # 결과 저장
    output_file = f'./data/scan_result_{yesterday}.csv'
    df.to_csv(output_file, index=False, encoding='utf-8-sig')
    print(f'\n💾 결과 저장: {output_file}')
    
    # Excel로도 저장
    excel_file = f'./data/scan_result_{yesterday}.xlsx'
    df.to_excel(excel_file, index=False, sheet_name='Scan Results')
    print(f'💾 Excel 저장: {excel_file}')
    
    # 상위 10개 출력
    print('\n🏆 TOP 10:')
    top10 = df[['symbol', 'name', 'market', 'close', 'volume_ratio', 'price_change_pct']].head(10)
    print(top10.to_string(index=False))
else:
    print('\n⚠️ 신호 감지된 종목 없음')

print('\n✅ 스캔 완료!')
