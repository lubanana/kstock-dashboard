#!/usr/bin/env python3
"""2월 샘플 데이터 생성 및 리포트"""

import pandas as pd
import random
from datetime import datetime, timedelta
from pathlib import Path

# 샘플 종목 리스트
sample_stocks = [
    ('005930', '삼성전자', 'KOSPI'), ('035420', 'NAVER', 'KOSPI'), ('000660', 'SK하이닉스', 'KOSPI'),
    ('207940', '삼성바이오로직스', 'KOSPI'), ('051910', 'LG화학', 'KOSPI'), ('005380', '현대차', 'KOSPI'),
    ('035720', '카카오', 'KOSPI'), ('006400', '삼성SDI', 'KOSPI'), ('000270', '기아', 'KOSPI'),
    ('068270', '셀트리온', 'KOSPI'), ('005490', 'POSCO홀딩스', 'KOSPI'), ('028260', '삼성물산', 'KOSPI'),
    ('105560', 'KB금융', 'KOSPI'), ('012330', '현대모비스', 'KOSPI'), ('055550', '신한지주', 'KOSPI'),
]

# 2월 샘플 데이터 생성
random.seed(42)
data = []
base_date = datetime(2026, 2, 1)

for day in range(28):
    current_date = (base_date + timedelta(days=day)).strftime('%Y-%m-%d')
    num_stocks = random.randint(5, 15)  # 하루 5~15개 종목
    
    selected = random.sample(sample_stocks, min(num_stocks, len(sample_stocks)))
    for symbol, name, market in selected:
        data.append({
            'scan_date': current_date,
            'symbol': symbol,
            'name': name,
            'market': market,
            'close': random.randint(50000, 800000),
            'open': random.randint(50000, 800000),
            'high': random.randint(50000, 800000),
            'low': random.randint(50000, 800000),
            'volume': random.randint(1000000, 10000000),
            'pivot_high': random.randint(50000, 800000),
            'volume_ma20': random.randint(1000000, 10000000),
            'volume_ratio': round(random.uniform(1.5, 25.0), 1),
            'price_change_pct': round(random.uniform(-5.0, 30.0), 2),
            'score': round(random.uniform(100, 1500), 1)
        })

df = pd.DataFrame(data)
df = df.sort_values('score', ascending=False)

# 저장
output_dir = Path('./data/daily_scans')
output_dir.mkdir(parents=True, exist_ok=True)

# 일별 CSV 저장
for date in df['scan_date'].unique():
    day_df = df[df['scan_date'] == date]
    day_df.to_csv(output_dir / f'scan_{date}.csv', index=False, encoding='utf-8-sig')

# 통합 CSV 저장
df.to_csv(output_dir / 'combined_2026-02-01_2026-02-28.csv', index=False, encoding='utf-8-sig')

print(f"✅ 2월 샘플 데이터 생성 완료: {len(df)}개 신호")
print(f"   기간: 2026-02-01 ~ 2026-02-28")
