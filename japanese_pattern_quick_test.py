#!/usr/bin/env python3
"""
Japanese Pattern Quick Test (빠른 테스트)
"""

import sqlite3
import pandas as pd
import numpy as np
from japanese_pattern_scanner import JapanesePatternScanner, SakataFiveMethods, IchimokuCloud

# 테스트
scanner = JapanesePatternScanner()

# 특정 종목 테스트
test_stocks = [
    ('005930', '삼성전자'),
    ('000660', 'SK하이닉스'),
    ('035720', '카카오'),
    ('035420', 'NAVER'),
]

print("=" * 70)
print("일본 고전 기법 테스트 (2026-04-09)")
print("=" * 70)

for code, name in test_stocks:
    print(f"\n📊 {name} ({code})")
    print("-" * 50)
    
    result = scanner.scan_stock(code, name, '2026-04-09')
    
    if result:
        print(f"  신호 개수: {result['signal_count']}")
        print(f"  신호 목록: {result['signals']}")
        
        ichimoku = result['ichimoku']
        if 'tenkan_sen' in ichimoku:
            print(f"\n  [일목균형표]")
            print(f"    전환선: {ichimoku['tenkan_sen']:.0f}")
            print(f"    기준선: {ichimoku['kijun_sen']:.0f}")
            print(f"    선행스팬A: {ichimoku['senkou_span_a']:.0f}")
            print(f"    선행스팬B: {ichimoku['senkou_span_b']:.0f}")
            print(f"    가격vs구름: {ichimoku['price_vs_cloud']}")
    else:
        print("  ❌ 신호 없음")

# 전체 시장 샘플 (10일만)
print("\n" + "=" * 70)
print("전체 시장 샘플 스캔 (최근 10거래일)")
print("=" * 70)

conn = sqlite3.connect(scanner.db_path)
cursor = conn.execute("""
    SELECT DISTINCT date FROM price_data 
    WHERE date >= '2026-04-01'
    ORDER BY date
    LIMIT 10
""")
dates = [row[0] for row in cursor.fetchall()]
conn.close()

all_signals = []
for date in dates[:3]:  # 3일만
    print(f"\n📅 {date}")
    signals = scanner.scanner.scan_market(date, min_signals=2) if hasattr(scanner, 'scanner') else scanner.scan_market(date, min_signals=2)
    all_signals.extend(signals)
    
    for s in signals[:3]:  # 상위 3개만
        print(f"  ✅ {s['name']}: {s['signal_count']}개 신호")

print(f"\n📊 총 신호: {len(all_signals)}개")
