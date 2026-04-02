#!/usr/bin/env python3
"""
간단한 조합 테스트 - 핵심 지표만
"""

import sys
sys.path.insert(0, '/root/.openclaw/workspace/strg')

import json
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from fdr_wrapper import get_price


def test_combination(symbol, date, combo_type):
    """지표 조합 테스트"""
    try:
        end_dt = datetime.strptime(date, '%Y-%m-%d')
        start_dt = end_dt - timedelta(days=90)
        
        df = get_price(symbol, start_dt.strftime('%Y-%m-%d'), date)
        if df is None or len(df) < 30:
            return None
        
        df = df.reset_index()
        closes = df['Close'].values
        highs = df['High'].values
        lows = df['Low'].values
        volumes = df['Volume'].values
        
        current_price = closes[-1]
        score = 0
        reasons = []
        
        # 기본: 추세
        ma5 = np.mean(closes[-5:])
        ma20 = np.mean(closes[-20:])
        if current_price > ma5 > ma20:
            score += 15
            reasons.append('Bullish_Trend')
        
        # 기본: 피볼나치 (확장된 범위)
        recent_high = np.max(highs[-20:])
        recent_low = np.min(lows[-20:])
        if recent_high > recent_low:
            retracement = ((recent_high - current_price) / (recent_high - recent_low)) * 100
        else:
            retracement = 50
        
        # 확장된 피볼나치 범위 30~70%
        if 30 <= retracement <= 70:
            score += 20
            reasons.append(f'Fib_{retracement:.0f}')
        else:
            return None  # 피볼나치 범위 밖
        
        # 기본: 거래량
        avg_vol = np.mean(volumes[-20:])
        rvol = volumes[-1] / avg_vol if avg_vol > 0 else 1.0
        if rvol >= 1.2:
            score += 10
            reasons.append(f'RVol_{rvol:.1f}')
        
        # 조합별 추가 조건
        if combo_type == 'base':
            # 기본만
            pass
        
        elif combo_type == 'rsi':
            # RSI 과매도 회복
            rsi = calculate_simple_rsi(closes[-15:])
            if 30 <= rsi <= 50:
                score += 15
                reasons.append(f'RSI_{rsi:.0f}')
            else:
                return None
        
        elif combo_type == 'candle':
            # 캔들 패턴
            if detect_pinbar(df):
                score += 15
                reasons.append('Pinbar')
            else:
                return None
        
        elif combo_type == 'divergence':
            # RSI 다이버전스 (간단 버전)
            if check_simple_divergence(closes, highs, lows):
                score += 20
                reasons.append('Divergence')
            else:
                return None
        
        elif combo_type == 'rsi_candle':
            rsi = calculate_simple_rsi(closes[-15:])
            if 30 <= rsi <= 50 and detect_pinbar(df):
                score += 25
                reasons.append(f'RSI_{rsi:.0f}')
                reasons.append('Pinbar')
            else:
                return None
        
        elif combo_type == 'rsi_div':
            rsi = calculate_simple_rsi(closes[-15:])
            if 30 <= rsi <= 50 and check_simple_divergence(closes, highs, lows):
                score += 30
                reasons.append(f'RSI_{rsi:.0f}')
                reasons.append('Divergence')
            else:
                return None
        
        elif combo_type == 'all':
            rsi = calculate_simple_rsi(closes[-15:])
            has_pinbar = detect_pinbar(df)
            has_div = check_simple_divergence(closes, highs, lows)
            
            if 30 <= rsi <= 50:
                score += 10
                reasons.append(f'RSI_{rsi:.0f}')
            if has_pinbar:
                score += 10
                reasons.append('Pinbar')
            if has_div:
                score += 10
                reasons.append('Divergence')
            
            if not (30 <= rsi <= 50 or has_pinbar or has_div):
                return None
        
        return {
            'symbol': symbol,
            'date': date,
            'combo': combo_type,
            'score': score,
            'price': round(current_price, 0),
            'retracement': round(retracement, 1),
            'rvol': round(rvol, 2),
            'reasons': reasons
        }
        
    except Exception as e:
        return None


def calculate_simple_rsi(prices, period=14):
    """간단한 RSI"""
    if len(prices) < period:
        return 50
    deltas = np.diff(prices)
    gains = np.sum(np.where(deltas > 0, deltas, 0)) / period
    losses = np.sum(np.where(deltas < 0, -deltas, 0)) / period
    if losses == 0:
        return 100
    rs = gains / losses
    return 100 - (100 / (1 + rs))


def detect_pinbar(df):
    """핀바 감지"""
    if len(df) < 3:
        return False
    
    for i in range(-3, 0):
        row = df.iloc[i]
        body = abs(row['Close'] - row['Open'])
        lower_shadow = min(row['Close'], row['Open']) - row['Low']
        total = row['High'] - row['Low']
        
        if total > 0 and lower_shadow >= body * 1.5 and lower_shadow >= total * 0.5:
            return True
    return False


def check_simple_divergence(closes, highs, lows):
    """간단한 다이버전스 체크"""
    if len(closes) < 20:
        return False
    
    # 최근 10봉 vs 그 이전 10봉
    recent_low = np.min(closes[-10:])
    prev_low = np.min(closes[-20:-10])
    
    # 가격은 낮아지지만 RSI는 높아지는 경우
    price_lower = recent_low < prev_low * 0.98
    
    # RSI 계산
    rsi_recent = calculate_simple_rsi(closes[-10:])
    rsi_prev = calculate_simple_rsi(closes[-20:-10])
    rsi_higher = rsi_recent > rsi_prev * 1.05
    
    return price_lower and rsi_higher


def simulate(signal):
    """간단한 시뮬레이션"""
    try:
        entry = signal['price']
        entry_dt = datetime.strptime(signal['date'], '%Y-%m-%d')
        
        df = get_price(signal['symbol'],
                      (entry_dt + timedelta(days=1)).strftime('%Y-%m-%d'),
                      (entry_dt + timedelta(days=15)).strftime('%Y-%m-%d'))
        
        if df is None or len(df) < 3:
            return None
        
        stop = entry * 0.94  # -6%
        target = entry * 1.12  # +12%
        
        for idx in range(min(10, len(df))):
            row = df.iloc[idx]
            if row['Low'] <= stop:
                return {'return': -6.0, 'exit': 'stop'}
            if row['High'] >= target:
                return {'return': 12.0, 'exit': 'target'}
        
        final = df['Close'].iloc[min(9, len(df)-1)]
        ret = ((final - entry) / entry) * 100
        return {'return': round(ret, 2), 'exit': 'hold'}
        
    except:
        return None


# 테스트
print("=" * 70)
print("🔥 복합 지표 조합 백테스트")
print("=" * 70)

symbols = ['033100', '140860', '348210', '006730', '009620', '012210', '025980', '042700',
           '005930', '000660', '055550']

dates = ['2026-01-13', '2026-01-20', '2026-01-27',
         '2026-02-03', '2026-02-10', '2026-02-17', '2026-02-24', 
         '2026-03-03', '2026-03-10', '2026-03-17', '2026-03-24', '2026-03-31']

combos = ['base', 'rsi', 'candle', 'divergence', 'rsi_candle', 'rsi_div', 'all']
results = {c: [] for c in combos}

for symbol in symbols:
    for date in dates:
        for combo in combos:
            signal = test_combination(symbol, date, combo)
            if signal and signal['score'] >= 40:
                trade = simulate(signal)
                if trade:
                    results[combo].append({
                        'symbol': symbol,
                        'date': date,
                        'score': signal['score'],
                        'return': trade['return'],
                        'reasons': signal['reasons']
                    })

# 결과 분석
print("\n📊 조합별 성과")
print("-" * 70)
print(f"{'조합':<15} {'거래수':<8} {'승률':<10} {'평균수익':<12} {'총수익':<10}")
print("-" * 70)

summary = []
for combo, trades in results.items():
    if not trades:
        continue
    
    returns = [t['return'] for t in trades]
    wins = [r for r in returns if r > 0]
    
    total = len(trades)
    win_rate = len(wins) / total * 100
    avg_ret = np.mean(returns)
    total_ret = sum(returns)
    
    summary.append({
        'combo': combo,
        'trades': total,
        'win_rate': win_rate,
        'avg_return': avg_ret,
        'total_return': total_ret
    })
    
    print(f"{combo:<15} {total:<8} {win_rate:>7.1f}%   {avg_ret:>+8.2f}%    {total_ret:>+7.2f}%")

# 정렬
summary.sort(key=lambda x: x['win_rate'], reverse=True)

print("\n" + "=" * 70)
print("🏆 최종 순위 (승률 기준)")
print("=" * 70)

for i, s in enumerate(summary, 1):
    print(f"{i}. {s['combo']}: 승률 {s['win_rate']:.1f}%, 평균 {s['avg_return']:+.2f}%, 총 {s['total_return']:+.2f}%")

# 저장
with open('docs/ivf_combo_simple.json', 'w', encoding='utf-8') as f:
    json.dump({'results': results, 'summary': summary}, f, ensure_ascii=False, indent=2)

print("\n✅ 저장: docs/ivf_combo_simple.json")
