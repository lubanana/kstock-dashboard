#!/usr/bin/env python3
"""
M10 Strategy Scanner with Updated Prices
- Load existing scan results
- Update prices using fdr_wrapper (fixed version)
- Perform market intelligence on top stocks
- Generate HTML report
"""

import pandas as pd
import sys
sys.path.insert(0, '/root/.openclaw/workspace/strg')

from fdr_wrapper import FDRWrapper
from datetime import datetime
import json

print("🚀 M10 전략 스캐너 (업데이트된 가격)")
print("=" * 60)

# 1. Load existing scan results
print("\n📊 기존 스캔 결과 로드 중...")
df = pd.read_csv('/root/.openclaw/workspace/strg/reports/multi_strategy_scan.csv')
print(f"✅ {len(df)}개 종목 로드 완료")

# 2. Update prices for top 20 stocks
print("\n💰 TOP 20 종목 가격 업데이트 중...")
fdr = FDRWrapper()

top_20 = df.head(20).copy()
updated_prices = {}

for idx, row in top_20.iterrows():
    symbol = str(row['종목코드']).zfill(6)
    name = row['종목명']
    
    try:
        # Get latest price
        price_df = fdr.get_price(symbol, start='2026-03-17', end='2026-03-18')
        if price_df is not None and len(price_df) > 0:
            latest = price_df.iloc[-1]
            updated_prices[symbol] = {
                'name': name,
                'price': int(latest['close']),
                'date': str(price_df.index[-1]),
                'volume': int(latest['volume'])
            }
            print(f"  ✅ {symbol} {name}: {updated_prices[symbol]['price']:,}원")
        else:
            print(f"  ⚠️ {symbol} {name}: 데이터 없음")
    except Exception as e:
        print(f"  ❌ {symbol} {name}: {e}")

print(f"\n✅ {len(updated_prices)}개 종목 가격 업데이트 완료")

# 3. Save updated prices
with open('/root/.openclaw/workspace/strg/m10_updated_prices.json', 'w', encoding='utf-8') as f:
    json.dump(updated_prices, f, ensure_ascii=False, indent=2)

print("\n💾 업데이트된 가격 저장 완료: m10_updated_prices.json")

# 4. Show summary
print("\n" + "=" * 60)
print("📈 TOP 10 종목 최신 가격")
print("=" * 60)

for i, (symbol, data) in enumerate(list(updated_prices.items())[:10], 1):
    old_price = df[df['종목코드'] == int(symbol)]['현재가'].values[0] if len(df[df['종목코드'] == int(symbol)]) > 0 else 0
    new_price = data['price']
    change = ((new_price - old_price) / old_price * 100) if old_price > 0 else 0
    change_str = f"{change:+.1f}%" if old_price > 0 else "N/A"
    print(f"{i:2d}. {symbol} {data['name']}: {new_price:,}원 ({change_str})")

print("\n✅ 완료!")
