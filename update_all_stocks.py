#!/usr/bin/env python3
"""
Update all KOSPI/KOSDAQ stocks for 2026-03-20
"""

import sys
sys.path.insert(0, '.')
from fdr_wrapper import get_price
import sqlite3
from datetime import datetime

# 전체 종목 리스트 (코스피 + 코스닥 대형주)
ALL_SYMBOLS = [
    # 코스피 대형주
    '005930', '000660', '051910', '005380', '035720', '068270', '207940',
    '006400', '000270', '012330', '005490', '028260', '105560', '018260',
    '032830', '034730', '000150', '016360', '009830', '003490', '004170',
    '000100', '011200', '030200', '010950', '034220', '086790', '055550',
    '047050', '032640', '009540', '030000', '018880', '000810', '024110',
    '005940', '010140', '001040', '003550', '008770', '007310', '006800',
    '000120', '001120', '010130', '002790', '001800', '003000', '005420',
    # 코스닥 대형주
    '247540', '086520', '091990', '035900', '293490', '263750', '151860',
    '196170', '214150', '221840', '183490', '095340', '100090', '137310',
    '058470', '048260', '042000', '041140', '025980', '014990', '039030',
    '008500', '004560', '004100', '002100', '001500', '000500', '000400',
]

def update_all_stocks():
    print("=" * 70)
    print("📊 Updating all stocks for 2026-03-20")
    print("=" * 70)
    
    conn = sqlite3.connect('data/pivot_strategy.db')
    cursor = conn.cursor()
    
    success = 0
    failed = 0
    
    for i, symbol in enumerate(ALL_SYMBOLS, 1):
        try:
            df = get_price(symbol, start_date='2026-03-20', end_date='2026-03-20')
            if not df.empty:
                success += 1
                if i % 10 == 0:
                    print(f"   Progress: {i}/{len(ALL_SYMBOLS)} - Success: {success}")
            else:
                failed += 1
        except Exception as e:
            failed += 1
            print(f"   ⚠️ {symbol}: {e}")
    
    conn.close()
    
    print(f"\n✅ Update complete!")
    print(f"   Success: {success}")
    print(f"   Failed: {failed}")

if __name__ == '__main__':
    update_all_stocks()
