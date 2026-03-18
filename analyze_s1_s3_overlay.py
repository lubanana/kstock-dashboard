#!/usr/bin/env python3
"""
S1 + S3 Overlay Analysis
S1(거래대금 TOP 20)과 S3(신규 모멘텀) 동시 충족 종목 분석
"""

import pandas as pd
import json
import sys
sys.path.insert(0, '/root/.openclaw/workspace/strg')

print("🔍 S1 + S3 동시 충족 종목 분석")
print("=" * 60)

# S1 결과 로드
s1_df = pd.read_csv('/root/.openclaw/workspace/strg/reports/strategy_sequential/s1_top20_20260318_0933.csv')
print(f"📊 S1 종목: {len(s1_df)}개")

# S3 결과 로드
with open('/root/.openclaw/workspace/strg/reports/strategy_sequential/s3_momentum_20260318_0933.json', 'r') as f:
    s3_data = json.load(f)
s3_df = pd.DataFrame(s3_data)
print(f"📊 S3 종목: {len(s3_df)}개")

# 동시 충족 종목 찾기
s1_symbols = set(s1_df['symbol'].astype(str).str.zfill(6))
s3_symbols = set(s3_df['symbol'].astype(str).str.zfill(6))

overlap = s1_symbols & s3_symbols
print(f"\n✅ S1 + S3 동시 충족: {len(overlap)}개 종목")

if len(overlap) == 0:
    print("\n⚠️ 동시 충족 종목이 없습니다.")
    sys.exit(0)

# 동시 충족 종목 상세 정보
print("\n🏆 S1 + S3 동시 충족 종목 상세:")
print("-" * 60)

results = []
for symbol in sorted(overlap):
    s1_row = s1_df[s1_df['symbol'].astype(str).str.zfill(6) == symbol].iloc[0]
    s3_row = s3_df[s3_df['symbol'].astype(str).str.zfill(6) == symbol].iloc[0]
    
    # 종목명 정제 (리스트인 경우 첫번째 값 사용)
    name = s1_row['name']
    if isinstance(name, list):
        name = name[0]
    
    result = {
        'symbol': symbol,
        'name': name,
        'rank': s1_row['rank'],
        'avg_amount': s1_row['avg_amount'],
        'current_price': s3_row['current_price'],
        'macd': s3_row['macd'],
        'rsi': s3_row['rsi']
    }
    results.append(result)
    
    print(f"  {result['rank']:2d}. {symbol} {name}")
    print(f"      💰 거래대금: {result['avg_amount']/1e8:.0f}억원 (S1 #{result['rank']})")
    print(f"      📈 현재가: {result['current_price']:,.0f}원")
    print(f"      📊 MACD: {result['macd']:,.0f} | RSI: {result['rsi']:.1f}")
    print()

# 결과 저장
output = {
    'timestamp': '2026-03-18T09:33:00',
    'strategy': 'S1 + S3 Overlay',
    'description': '거래대금 TOP 20 + 신규 모멘텀 동시 충족',
    'total': len(results),
    'stocks': results
}

with open('/root/.openclaw/workspace/strg/s1_s3_overlay.json', 'w', encoding='utf-8') as f:
    json.dump(output, f, ensure_ascii=False, indent=2)

print(f"💾 결과 저장: s1_s3_overlay.json")
