#!/usr/bin/env python3
"""
Update DB with latest price data (2026-03-19)
"""

import sqlite3
import pandas as pd
from datetime import datetime
import FinanceDataReader as fdr
import sys

def update_latest_data():
    """Fetch and update latest price data"""
    
    db_path = '/root/.openclaw/workspace/strg/data/pivot_strategy.db'
    today = '2026-03-19'
    
    print(f"📊 Updating DB with data for {today}")
    
    # Connect to DB
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Get symbols from yesterday
    cursor.execute("SELECT DISTINCT symbol FROM stock_prices WHERE date = '2026-03-18'")
    symbols = [row[0] for row in cursor.fetchall()]
    print(f"   Found {len(symbols)} symbols to update")
    
    # Fetch data for today
    updated_count = 0
    failed_symbols = []
    
    for i, symbol in enumerate(symbols, 1):
        if i % 100 == 0:
            print(f"   Progress: {i}/{len(symbols)}...")
        
        try:
            # Fetch data
            df = fdr.DataReader(symbol, start='2026-03-19', end='2026-03-19')
            
            if len(df) == 0:
                failed_symbols.append(symbol)
                continue
            
            # Normalize columns
            df = df.reset_index()
            if 'Date' in df.columns:
                df = df.rename(columns={'Date': 'date'})
            
            # Prepare data for insert
            row = df.iloc[0]
            date_str = today
            open_price = float(row.get('Open', row.get('open', 0)))
            high_price = float(row.get('High', row.get('high', 0)))
            low_price = float(row.get('Low', row.get('low', 0)))
            close_price = float(row.get('Close', row.get('close', 0)))
            volume = int(row.get('Volume', row.get('volume', 0)))
            
            # Insert into DB
            cursor.execute('''
                INSERT OR REPLACE INTO stock_prices 
                (symbol, date, open, high, low, close, volume)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (symbol, date_str, open_price, high_price, low_price, close_price, volume))
            
            updated_count += 1
            
        except Exception as e:
            failed_symbols.append(symbol)
            continue
    
    # Commit changes
    conn.commit()
    
    # Verify
    cursor.execute(f"SELECT COUNT(*) FROM stock_prices WHERE date = '{today}'")
    final_count = cursor.fetchone()[0]
    
    conn.close()
    
    print(f"\n✅ Update complete!")
    print(f"   Updated: {updated_count} symbols")
    print(f"   Failed: {len(failed_symbols)} symbols")
    print(f"   Total in DB for {today}: {final_count}")
    
    if failed_symbols[:10]:
        print(f"   Sample failed: {failed_symbols[:5]}")
    
    return updated_count

if __name__ == '__main__':
    update_latest_data()
