#!/bin/bash
# DART Disclosure Builder Progress Monitor
# Runs every 10 minutes to check build progress

cd /root/.openclaw/workspace/strg

# Get current stats
echo "📊 DART Disclosure Build Progress - $(date '+%Y-%m-%d %H:%M:%S')"
echo "=================================================="

# Check if builder is running
if pgrep -f "dart_disclosure_builder.py" > /dev/null; then
    echo "✅ Builder is running"
else
    echo "⚠️ Builder is not running"
fi

# Get cache stats
python3 -c "
import sqlite3
try:
    conn = sqlite3.connect('./data/dart_cache.db')
    cursor = conn.cursor()
    
    # Total disclosures
    cursor.execute('SELECT COUNT(*) FROM disclosures')
    total_disc = cursor.fetchone()[0]
    
    # Unique companies
    cursor.execute('SELECT COUNT(DISTINCT corp_code) FROM disclosures')
    unique_corp = cursor.fetchone()[0]
    
    # Progress (assuming 3286 total stocks)
    progress = unique_corp / 3286 * 100
    
    print(f'📈 Cached Companies: {unique_corp:,} / 3,286 ({progress:.1f}%)')
    print(f'📄 Total Disclosures: {total_disc:,}')
    
    # Top 5
    cursor.execute('''
        SELECT corp_code, COUNT(*) as cnt 
        FROM disclosures 
        GROUP BY corp_code 
        ORDER BY cnt DESC 
        LIMIT 5
    ''')
    print('')
    print('🏆 Top 5 Companies:')
    for i, (corp, cnt) in enumerate(cursor.fetchall(), 1):
        print(f'  {i}. {corp}: {cnt:,} disclosures')
    
    conn.close()
except Exception as e:
    print(f'Error: {e}')
"

echo ""
echo "=================================================="
