import sqlite3
import pandas as pd
import numpy as np

# DB 연결
conn = sqlite3.connect('data/level1_prices.db')
df = pd.read_sql_query("SELECT * FROM price_data WHERE date >= date('now', '-60 days') ORDER BY code, date", conn)
df['date'] = pd.to_datetime(df['date'])
conn.close()

# 이동평균, RSI, ADX 계산 함수
def calc_ma(s, n):
    return s.rolling(window=n, min_periods=1).mean()

def calc_rsi(s, n=14):
    delta = s.diff()
    gain = delta.where(delta > 0, 0)
    loss = -delta.where(delta < 0, 0)
    avg_gain = gain.ewm(span=n, adjust=False, min_periods=1).mean()
    avg_loss = loss.ewm(span=n, adjust=False, min_periods=1).mean()
    rs = avg_gain / avg_loss.replace(0, np.nan)
    return (100 - (100 / (1 + rs))).fillna(50)

results = []
for code in df['code'].unique():
    stock = df[df['code'] == code].sort_values('date').reset_index(drop=True)
    if len(stock) < 30:
        continue
    
    stock['ma5'] = calc_ma(stock['close'], 5)
    stock['ma20'] = calc_ma(stock['close'], 20)
    stock['rsi'] = calc_rsi(stock['close'])
    
    latest = stock.iloc[-1]
    vol_20_avg = stock['volume'].tail(20).mean()
    vol_ratio = latest['volume'] / vol_20_avg if vol_20_avg > 0 else 0
    
    # 점수 계산
    score_details = {}
    
    # 거래량 점수
    if vol_ratio >= 5: score_details['volume'] = 30
    elif vol_ratio >= 4: score_details['volume'] = 27
    elif vol_ratio >= 3: score_details['volume'] = 24
    elif vol_ratio >= 2.5: score_details['volume'] = 20
    elif vol_ratio >= 2: score_details['volume'] = 15
    elif vol_ratio >= 1.5: score_details['volume'] = 10
    else: score_details['volume'] = 0
    
    # 기술적 점수
    ma_aligned = latest['close'] > latest['ma5'] > latest['ma20'] if pd.notna(latest['ma20']) else False
    ma20_breakout = False
    if len(stock) > 1 and pd.notna(latest['ma20']):
        ma20_breakout = (latest['close'] > latest['ma20']) and (stock.iloc[-2]['close'] <= stock.iloc[-2]['ma20'])
    
    tech_score = 0
    if ma20_breakout: tech_score += 12
    if ma_aligned: tech_score += 8
    score_details['technical'] = tech_score
    
    # 기타 점수
    score_details['market_cap'] = 15
    score_details['foreign'] = 5
    score_details['news'] = 8
    
    # 테마 점수
    hot_sectors = ['로봇', '자동화', 'AI', '인공지능', '바이오', '제약', '반도체', '칩']
    theme_score = 10 if any(k in latest['name'] for k in hot_sectors) else 0
    score_details['theme'] = theme_score
    
    # 볼너스
    bonus = 0
    if 50 <= latest['rsi'] <= 70: bonus += 3
    score_details['bonus'] = bonus
    
    total = sum(score_details.values())
    score_details['total'] = min(total, 100)
    
    results.append({
        'code': code,
        'name': latest['name'],
        'score': score_details['total'],
        'vol_ratio': vol_ratio,
        'rsi': latest['rsi'],
        'ma_aligned': ma_aligned,
        'ma20_breakout': ma20_breakout,
        'close': latest['close'],
        'score_details': score_details
    })

# 점수순 정렬
results.sort(key=lambda x: x['score'], reverse=True)

print('=== 상위 30개 종목 (점수 기준) ===')
for i, r in enumerate(results[:30], 1):
    print(f"{i}. {r['name']} ({r['code']}) - {r['score']}점, 거래량 {r['vol_ratio']:.1f}배, RSI {r['rsi']:.1f}")

print(f'\n점수 분포:')
print(f'80점 이상: {len([r for r in results if r["score"] >= 80])}개')
print(f'70점 이상: {len([r for r in results if r["score"] >= 70])}개')
print(f'60점 이상: {len([r for r in results if r["score"] >= 60])}개')
print(f'50점 이상: {len([r for r in results if r["score"] >= 50])}개')

# 상위 50개 JSON으로 저장
import json
with open('top_candidates_check.json', 'w', encoding='utf-8') as f:
    json.dump(results[:50], f, ensure_ascii=False, indent=2, default=str)
print('\ntop_candidates_check.json 저장 완료')
