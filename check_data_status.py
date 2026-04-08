#!/usr/bin/env python3
"""Daily data status checker - 매일 데이터 구축 상태 확인"""

import sqlite3
import datetime
import sys

DB_PATH = 'data/pivot_strategy.db'

def check_data_status():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Get last 7 days
    today = datetime.date.today()
    dates = [(today - datetime.timedelta(days=i)).strftime('%Y-%m-%d') 
             for i in range(7)]
    
    print(f"📊 데이터 구축 상태 확인 ({today})")
    print("=" * 60)
    
    issues = []
    
    for date in dates:
        # Skip weekends
        dt = datetime.datetime.strptime(date, '%Y-%m-%d')
        if dt.weekday() >= 5:  # Saturday=5, Sunday=6
            continue
            
        cursor.execute(
            'SELECT COUNT(DISTINCT symbol) FROM stock_prices WHERE date = ?',
            (date,)
        )
        count = cursor.fetchone()[0]
        
        status = "✅" if count >= 3500 else "⚠️" if count >= 3000 else "❌"
        if count < 3500:
            issues.append(f"{date}: {count}종목 (부족)")
        
        print(f"{status} {date}: {count:,}종목")
    
    conn.close()
    
    print("=" * 60)
    if issues:
        print(f"⚠️  누락 발견: {len(issues)}일")
        for issue in issues:
            print(f"   - {issue}")
        return 1
    else:
        print("✅ 모든 날짜 정상")
        return 0

if __name__ == '__main__':
    sys.exit(check_data_status())
