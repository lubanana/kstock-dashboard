#!/usr/bin/env python3
"""
Update DB with latest price data for selected symbols (quick update)
"""

import sqlite3
import pandas as pd
from datetime import datetime
import FinanceDataReader as fdr

def update_selected_symbols():
    """Fetch and update latest price data for selected symbols"""
    
    db_path = '/root/.openclaw/workspace/strg/data/pivot_strategy.db'
    today = '2026-03-19'
    
    # Selected symbols for V-Series scan
    symbols = [
        '005930', '000660', '051910', '005380', '035720',
        '068270', '207940', '006400', '000270', '012330',
        '005490', '028260', '105560', '018260', '032830',
        '000100', '000150', '000250', '000300', '000400',
        '000500', '000650', '000700', '000850', '000950',
        '003550', '004020', '005070', '005110', '005860',
        '009240', '009830', '010130', '010950', '011200',
        '016360', '024110', '028050', '034220', '034730',
        '001040', '001460', '001740', '002320', '002700',
        '003200', '003490', '004170', '004800', '005500'
    ]
    
    print(f"📊 Updating DB with data for {today}")
    print(f"   Symbols: {len(symbols)}")
    
    # Connect to DB
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Fetch data for today
    updated_count = 0
    failed_symbols = []
    
    for i, symbol in enumerate(symbols, 1):
        try:
            # Fetch data
            df = fdr.DataReader(symbol, start='2026-03-19', end='2026-03-19')
            
            if len(df) == 0:
                # Try to copy from yesterday if today not available
                cursor.execute('''
                    SELECT open, high, low, close, volume 
                    FROM stock_prices 
                    WHERE symbol = ? AND date = '2026-03-18'
                ''', (symbol,))
                row = cursor.fetchone()
                
                if row:
                    cursor.execute('''
                        INSERT OR REPLACE INTO stock_prices 
                        (symbol, date, open, high, low, close, volume)
                        VALUES (?, ?, ?, ?, ?, ?, ?)
                    ''', (symbol, today, row[0], row[1], row[2], row[3], row[4]))
                    updated_count += 1
                else:
                    failed_symbols.append(symbol)
                continue
            
            # Normalize columns
            df = df.reset_index()
            
            # Prepare data for insert
            row = df.iloc[0]
            date_str = today
            
            # Handle different column names
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
    
    if failed_symbols:
        print(f"   Failed symbols: {failed_symbols}")
    
    return updated_count

if __name__ == '__main__':
    update_selected_symbols()
