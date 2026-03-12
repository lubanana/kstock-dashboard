#!/usr/bin/env python3
"""
Sample Daily Pivot Data Generator (for demonstration)
샘플 일자별 전환점 데이터 생성기
"""

import json
import os
from datetime import datetime, timedelta
import random

# 출력 디렉토리
output_dir = 'data/daily_pivot'
os.makedirs(output_dir, exist_ok=True)

# 종목 샘플
sample_stocks = [
    ('005930', '삼성전자', 'KOSPI'),
    ('000660', 'SK하이닉스', 'KOSPI'),
    ('035420', 'NAVER', 'KOSPI'),
    ('005380', '현대차', 'KOSPI'),
    ('035720', '카카오', 'KOSPI'),
    ('051910', 'LG화학', 'KOSPI'),
    ('006400', '삼성SDI', 'KOSPI'),
    ('028260', '삼성물산', 'KOSPI'),
    ('012330', '현대모비스', 'KOSPI'),
    ('207940', '삼성바이오', 'KOSPI'),
    ('247540', '에코프로비엠', 'KOSDAQ'),
    ('086520', '에코프로', 'KOSDAQ'),
    ('196170', '알테오젠', 'KOSDAQ'),
    ('323410', '카카오뱅크', 'KOSPI'),
    ('377300', '카카오페이', 'KOSPI'),
]

# 2026년 1월 2일부터 2월 28일까지 영업일 생성
start = datetime(2026, 1, 2)
end = datetime(2026, 2, 28)

current = start
business_days = []
while current <= end:
    if current.weekday() < 5:
        business_days.append(current.strftime('%Y-%m-%d'))
    current += timedelta(days=1)

print("📊 샘플 일자별 전환점 데이터 생성")
print("="*60)
print(f"기간: 2026-01-02 ~ 2026-02-28")
print(f"영업일: {len(business_days)}일")
print("="*60)

# 일자별 데이터 생성
for date_str in business_days:
    signals = []
    
    # 무작위로 0~5개 종목 선택
    num_signals = random.randint(0, 5)
    selected = random.sample(sample_stocks, min(num_signals, len(sample_stocks)))
    
    for code, name, market in selected:
        base_price = random.randint(50000, 500000)
        score = random.uniform(60, 100)
        
        signals.append({
            'date': date_str,
            'code': code,
            'name': name,
            'market': market,
            'current_price': base_price,
            'score': round(score, 1),
            'volume_ratio': round(random.uniform(1.5, 3.5), 2),
            'break_strength': round(random.uniform(2, 10), 2),
            'entry_1': base_price,
            'entry_2': round(base_price * 1.05, 0),
            'entry_3': round(base_price * 1.1025, 0),
            'stop_loss': round(base_price * 0.90, 0)
        })
    
    # 저장
    output = {
        'date': date_str,
        'signals_found': len(signals),
        'signals': sorted(signals, key=lambda x: x['score'], reverse=True)
    }
    
    with open(f'{output_dir}/{date_str}.json', 'w', encoding='utf-8') as f:
        json.dump(output, f, ensure_ascii=False, indent=2)
    
    if signals:
        print(f"✅ {date_str}: {len(signals)}개 신호")
        for i, s in enumerate(signals[:3], 1):
            print(f"   {i}. {s['name']}: {s['score']}pts")

# 요약 저장
summary = [{'date': d, 'signals': random.randint(0, 5)} for d in business_days]
with open(f'{output_dir}/_summary.json', 'w', encoding='utf-8') as f:
    json.dump({
        'start_date': '2026-01-02',
        'end_date': '2026-02-28',
        'total_days': len(business_days),
        'daily_stats': summary
    }, f, ensure_ascii=False, indent=2)

print("\n" + "="*60)
print("✅ 샘플 데이터 생성 완료!")
print(f"   저장 위치: {output_dir}/")
print(f"   총 파일: {len(business_days)}개")
print("="*60)
