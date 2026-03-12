#!/usr/bin/env python3
import os
import json
import FinanceDataReader as fdr
from datetime import datetime, timedelta
import pandas as pd

def load_stocks():
    stocks = []
    for fname in ['kospi_stocks.json', 'kosdaq_stocks.json']:
        try:
            with open(f'data/{fname}', 'r') as f:
                data = json.load(f)
                mkt = 'KOSPI' if 'kospi' in fname else 'KOSDAQ'
                for s in data.get('stocks', []):
                    stocks.append({'code': s['code'], 'name': s['name'], 'market': mkt})
        except:
            pass
    return stocks

def scan_date(date_str, stocks):
    results = []
    total = len(stocks)
    
    for i, stock in enumerate(stocks, 1):
        try:
            target = datetime.strptime(date_str, '%Y-%m-%d')
            start = target - timedelta(days=60)
            df = fdr.DataReader(stock['code'], start.strftime('%Y-%m-%d'), target.strftime('%Y-%m-%d'))
            
            if df is None or len(df) < 21:
                continue
            
            dates = [d.strftime('%Y-%m-%d') for d in df.index]
            if date_str not in dates:
                continue
            
            idx = dates.index(date_str)
            if idx == 0:
                continue
            
            current = df.iloc[idx]['Close']
            prev_df = df.iloc[:idx]
            high_20 = prev_df['High'].tail(20).max()
            volume_ma = prev_df['Volume'].tail(20).mean()
            
            if pd.isna(high_20) or current <= high_20:
                continue
            
            vol_ratio = df.iloc[idx]['Volume'] / volume_ma if volume_ma > 0 else 1
            strength = (current / high_20 - 1) * 100
            score = min(40, strength * 4) + (30 if vol_ratio >= 1.5 else 15)
            
            results.append({
                'date': date_str,
                'code': stock['code'],
                'name': stock['name'],
                'market': stock['market'],
                'price': float(current),
                'score': float(score),
                'volume_ratio': float(vol_ratio),
                'break_strength': float(strength)
            })
        except:
            pass
        
        if i % 500 == 0 or i == total:
            print(f"  {i}/{total} ({i/total*100:.0f}%) - 신호: {len(results)}", flush=True)
    
    return sorted(results, key=lambda x: x['score'], reverse=True)

# 메인
stocks = load_stocks()
print(f"총 종목: {len(stocks)}개")

start = datetime(2026, 1, 2)
end = datetime(2026, 3, 11)
os.makedirs('data/daily_pivot', exist_ok=True)

current = start
while current <= end:
    if current.weekday() < 5:
        date_str = current.strftime('%Y-%m-%d')
        fname = f'data/daily_pivot/{date_str}.json'
        
        if os.path.exists(fname):
            print(f"\n⏭️  {date_str} - 이미 처리됨")
            current += timedelta(days=1)
            continue
        
        print(f"\n📅 {date_str} 처리 중...")
        results = scan_date(date_str, stocks)
        
        with open(fname, 'w', encoding='utf-8') as f:
            json.dump({
                'date': date_str,
                'signals_found': len(results),
                'signals': results
            }, f, ensure_ascii=False, indent=2)
        
        print(f"✅ {date_str}: {len(results)}개 신호 저장")
        
        if results:
            for i, r in enumerate(results[:3], 1):
                print(f"   {i}. {r['name']}: {r['score']:.1f}pts")
    
    current += timedelta(days=1)

print("\n🎉 완료!")
