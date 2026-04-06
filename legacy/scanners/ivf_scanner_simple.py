#!/usr/bin/env python3
"""
IVF 스캐너 단순 버전 - 백테스트용
"""

import sys
sys.path.insert(0, '/root/.openclaw/workspace/strg')

import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from fdr_wrapper import get_price


def analyze_ict_simple(df):
    """간단한 ICT 분석"""
    if len(df) < 20:
        return {'structure': 'neutral', 'ob_near': False, 'fvg_near': False}
    
    closes = df['Close'].values
    highs = df['High'].values
    lows = df['Low'].values
    
    # 추세 확인 (간단)
    ma20 = np.mean(closes[-20:])
    ma10 = np.mean(closes[-10:])
    
    if closes[-1] > ma10 > ma20:
        structure = 'bullish'
    elif closes[-1] < ma10 < ma20:
        structure = 'bearish'
    else:
        structure = 'neutral'
    
    # Order Block 근접 확인 (단순)
    recent_low = np.min(lows[-10:])
    ob_near = abs(closes[-1] - recent_low) / closes[-1] < 0.03
    
    return {
        'structure': structure,
        'ob_near': ob_near,
        'fvg_near': False
    }


def analyze_volume_simple(df):
    """간단한 수급 분석"""
    if len(df) < 20:
        return {'rvol': 1.0, 'accumulation': False}
    
    volumes = df['Volume'].values
    closes = df['Close'].values
    lows = df['Low'].values
    highs = df['High'].values
    
    # RVol
    rvol = volumes[-1] / np.mean(volumes[-20:]) if np.mean(volumes[-20:]) > 0 else 1.0
    
    # 누적 확인 (종가가 상단에 위치)
    close_pos = (closes[-1] - lows[-1]) / (highs[-1] - lows[-1]) if highs[-1] > lows[-1] else 0.5
    accumulation = close_pos > 0.6 and rvol > 1.2
    
    return {
        'rvol': rvol,
        'accumulation': accumulation
    }


def analyze_fibonacci_simple(df):
    """간단한 피볼나치 분석"""
    if len(df) < 20:
        return {'retracement': 50, 'ote_zone': False}
    
    highs = df['High'].values[-20:]
    lows = df['Low'].values[-20:]
    current = df['Close'].iloc[-1]
    
    recent_high = np.max(highs)
    recent_low = np.min(lows)
    
    if recent_high > recent_low:
        retracement = ((recent_high - current) / (recent_high - recent_low)) * 100
    else:
        retracement = 50
    
    # OTE Zone 50~79%
    ote_zone = 50 <= retracement <= 79
    
    return {
        'retracement': retracement,
        'ote_zone': ote_zone
    }


def calculate_signal(symbol, date_str):
    """특정 날짜의 신호 계산"""
    try:
        # 데이터 로드
        end_dt = datetime.strptime(date_str, '%Y-%m-%d')
        start_dt = end_dt - timedelta(days=60)
        
        df = get_price(symbol, start_dt.strftime('%Y-%m-%d'), date_str)
        if df is None or len(df) < 30:
            return None
        
        current_price = df['Close'].iloc[-1]
        
        # 각 분석 수행
        ict = analyze_ict_simple(df)
        vol = analyze_volume_simple(df)
        fib = analyze_fibonacci_simple(df)
        
        # 점수 계산
        score = 0
        confluence = []
        
        # ICT (35점)
        if ict['structure'] == 'bullish':
            score += 20
            confluence.append('Bullish_Structure')
        if ict['ob_near']:
            score += 15
            confluence.append('OB_Near')
        
        # 수급 (25점)
        if vol['rvol'] >= 2.0:
            score += 15
            confluence.append('High_RVol')
        elif vol['rvol'] >= 1.5:
            score += 10
            confluence.append('Volume_Up')
        
        if vol['accumulation']:
            score += 10
            confluence.append('Accumulation')
        
        # 피볼나치 (25점)
        if fib['ote_zone']:
            score += 25
            confluence.append('OTE_Zone')
        elif 40 <= fib['retracement'] < 50:
            score += 15
            confluence.append('Fib_382')
        
        # 신호 등급
        if score >= 70:
            signal = 'STRONG_BUY'
        elif score >= 55:
            signal = 'BUY'
        elif score >= 40:
            signal = 'WATCH'
        else:
            signal = 'NEUTRAL'
        
        return {
            'symbol': symbol,
            'date': date_str,
            'signal': signal,
            'score': score,
            'price': current_price,
            'confluence': confluence,
            'ict_structure': ict['structure'],
            'rvol': round(vol['rvol'], 2),
            'fib_retracement': round(fib['retracement'], 1)
        }
        
    except Exception as e:
        return None


if __name__ == '__main__':
    # 테스트
    print("=" * 70)
    print("🔥 IVF 스캐너 (단순 버전) 테스트")
    print("=" * 70)
    
    symbols = ['005930', '042700', '033100', '348210']
    test_date = '2026-03-03'
    
    results = []
    for symbol in symbols:
        result = calculate_signal(symbol, test_date)
        if result:
            results.append(result)
            emoji = '📈' if result['signal'] in ['BUY', 'STRONG_BUY'] else '➖'
            print(f"\n{emoji} {result['symbol']}")
            print(f"   신호: {result['signal']} ({result['score']}점)")
            print(f"   현재가: {result['price']:,.0f}원")
            print(f"   구조: {result['ict_structure']}, RVol: {result['rvol']}")
            print(f"   피볼나치: {result['fib_retracement']:.1f}%")
            print(f"   합치: {', '.join(result['confluence'])}")
