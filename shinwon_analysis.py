#!/usr/bin/env python3
"""
신원종합개발 (017000) 기술적 분석
"""

import sys
sys.path.insert(0, '/root/.openclaw/workspace/strg')

import pandas as pd
import numpy as np
import sqlite3
from datetime import datetime, timedelta

def calculate_indicators(df):
    """기술적 지표 계산"""
    df = df.copy()
    df = df.sort_values('date').reset_index(drop=True)
    
    # 이동평균선
    df['ma5'] = df['close'].rolling(window=5).mean()
    df['ma20'] = df['close'].rolling(window=20).mean()
    df['ma60'] = df['close'].rolling(window=60).mean()
    
    # ATR
    df['high_low'] = df['high'] - df['low']
    df['high_close'] = abs(df['high'] - df['close'].shift())
    df['low_close'] = abs(df['low'] - df['close'].shift())
    df['tr'] = df[['high_low', 'high_close', 'low_close']].max(axis=1)
    df['atr'] = df['tr'].rolling(window=14).mean()
    
    # RSI
    delta = df['close'].diff()
    gain = delta.where(delta > 0, 0).rolling(window=14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
    rs = gain / loss
    df['rsi'] = 100 - (100 / (1 + rs))
    
    # MACD
    exp1 = df['close'].ewm(span=12).mean()
    exp2 = df['close'].ewm(span=26).mean()
    df['macd'] = exp1 - exp2
    df['macd_signal'] = df['macd'].ewm(span=9).mean()
    df['macd_hist'] = df['macd'] - df['macd_signal']
    
    # 볼린저 밴드
    df['bb_middle'] = df['close'].rolling(window=20).mean()
    bb_std = df['close'].rolling(window=20).std()
    df['bb_upper'] = df['bb_middle'] + (bb_std * 2)
    df['bb_lower'] = df['bb_middle'] - (bb_std * 2)
    df['bb_position'] = (df['close'] - df['bb_lower']) / (df['bb_upper'] - df['bb_lower'])
    
    # 거래량 이동평균
    df['volume_ma20'] = df['volume'].rolling(window=20).mean()
    
    return df

def fibonacci_levels(high, low):
    """피볼나치 레벨 계산"""
    diff = high - low
    return {
        '0': high,
        '236': high - diff * 0.236,
        '382': high - diff * 0.382,
        '500': high - diff * 0.5,
        '618': high - diff * 0.618,
        '100': low
    }

def analyze_stock(code, name):
    """종목 분석"""
    conn = sqlite3.connect('data/level1_prices.db')
    
    # 최근 100일 데이터 조회
    query = f"""
    SELECT date, open, high, low, close, volume
    FROM price_data
    WHERE code = '{code}'
    ORDER BY date DESC
    LIMIT 100
    """
    df = pd.read_sql_query(query, conn)
    conn.close()
    
    if len(df) < 40:
        print(f"❌ 데이터 부족: {len(df)}일")
        return
    
    df = df.sort_values('date').reset_index(drop=True)
    df = calculate_indicators(df)
    
    latest = df.iloc[-1]
    
    # 52주 고가/저가
    high_52w = df['high'].max()
    low_52w = df['low'].min()
    
    # 피볼나치 레벨 (최근 20일 기준)
    recent_20 = df.tail(20)
    fib_high = recent_20['high'].max()
    fib_low = recent_20['low'].min()
    fib_levels = fibonacci_levels(fib_high, fib_low)
    
    # 현재가가 어느 피볼나치 레벨에 있는지
    current_price = latest['close']
    fib_position = None
    for level_name, level_price in sorted(fib_levels.items(), key=lambda x: x[1], reverse=True):
        if current_price >= level_price:
            fib_position = level_name
            break
    
    # 기술적 분석
    print("=" * 70)
    print(f"📊 {name} ({code}) 기술적 분석")
    print("=" * 70)
    print(f"\n📅 기준일: {latest['date']}")
    print(f"💰 현재가: {current_price:,.0f}원")
    
    # 이동평균선 분석
    print(f"\n📈 이동평균선")
    print(f"   - 5일선:  {latest['ma5']:,.0f}원")
    print(f"   - 20일선: {latest['ma20']:,.0f}원")
    print(f"   - 60일선: {latest['ma60']:,.0f}원")
    
    if current_price > latest['ma5'] > latest['ma20'] > latest['ma60']:
        ma_trend = "강한 정배열 (상승세)"
    elif current_price > latest['ma5'] > latest['ma20']:
        ma_trend = "단기 정배열"
    elif current_price < latest['ma5'] < latest['ma20']:
        ma_trend = "역배열 (하락세)"
    else:
        ma_trend = "혼조세"
    print(f"   - 추세: {ma_trend}")
    
    # RSI 분석
    rsi = latest['rsi']
    print(f"\n📊 RSI(14): {rsi:.1f}")
    if rsi > 70:
        rsi_status = "과매수 (조정 가능성)"
    elif rsi > 50:
        rsi_status = "중립~강세"
    elif rsi > 30:
        rsi_status = "중립~약세"
    else:
        rsi_status = "과매도 (반등 가능성)"
    print(f"   - 상태: {rsi_status}")
    
    # MACD 분석
    print(f"\n📉 MACD")
    print(f"   - MACD: {latest['macd']:.2f}")
    print(f"   - Signal: {latest['macd_signal']:.2f}")
    print(f"   - Histogram: {latest['macd_hist']:.2f}")
    if latest['macd_hist'] > 0 and latest['macd_hist'] > df.iloc[-2]['macd_hist']:
        macd_status = "상승 모멘텀 강화"
    elif latest['macd_hist'] > 0:
        macd_status = "상승 모멘텀 유지"
    elif latest['macd_hist'] < 0 and latest['macd_hist'] < df.iloc[-2]['macd_hist']:
        macd_status = "하락 모멘텀 강화"
    else:
        macd_status = "하락 모멘텀 약화"
    print(f"   - 상태: {macd_status}")
    
    # 볼린저 밴드
    print(f"\n🎯 볼린저 밴드")
    print(f"   - 상단: {latest['bb_upper']:,.0f}원")
    print(f"   - 중간: {latest['bb_middle']:,.0f}원")
    print(f"   - 하단: {latest['bb_lower']:,.0f}원")
    bb_pos = latest['bb_position']
    if bb_pos > 0.8:
        bb_status = "상단 근접 (과매수)"
    elif bb_pos < 0.2:
        bb_status = "하단 근접 (과매도)"
    else:
        bb_status = "중간 범위"
    print(f"   - 위치: {bb_status} ({bb_pos*100:.1f}%)")
    
    # 피볼나치 레벨
    print(f"\n🔺 피볼나치 되돌림 (최근 20일)")
    print(f"   - 0%:   {fib_levels['0']:,.0f}원 (고점)")
    print(f"   - 38.2%: {fib_levels['382']:,.0f}원")
    print(f"   - 50%:  {fib_levels['500']:,.0f}원")
    print(f"   - 61.8%: {fib_levels['618']:,.0f}원")
    print(f"   - 100%: {fib_levels['100']:,.0f}원 (저점)")
    print(f"   - 현재가 위치: {fib_position}% 구간")
    
    # 거래량
    vol_ratio = latest['volume'] / latest['volume_ma20'] if latest['volume_ma20'] > 0 else 0
    print(f"\n📊 거래량")
    print(f"   - 당일: {latest['volume']:,.0f}주")
    print(f"   - 20일평균: {latest['volume_ma20']:,.0f}주")
    print(f"   - 비율: {vol_ratio:.1f}x")
    
    # 52주 범위
    print(f"\n📈 52주 범위")
    print(f"   - 고가: {high_52w:,.0f}원")
    print(f"   - 저가: {low_52w:,.0f}원")
    print(f"   - 현재가 위치: {(current_price - low_52w) / (high_52w - low_52w) * 100:.1f}%")
    
    # ATR 기반 목표가/손절가
    atr = latest['atr']
    print(f"\n" + "=" * 70)
    print(f"🎯 매매 전략 (ATR 기반)")
    print("=" * 70)
    
    # 진입가 (현재가 기준)
    entry = current_price
    
    # 목표가 (피볼나치 1.618 확장 또는 ATR * 2)
    tp1 = entry + (atr * 1.5)
    tp2 = entry + (atr * 2.0)
    tp3 = fib_levels['382'] if current_price < fib_levels['382'] else entry * 1.15
    
    # 손절가 (피볼나치 -1.0 확장 또는 ATR * 1.5)
    stop_loss = entry - (atr * 1.5)
    
    # 피볼나치 지지선 근처면 조정
    if abs(current_price - fib_levels['618']) / current_price < 0.03:
        print(f"\n✅ 현재가가 61.8% 지지선 근처 - 지지선 기반 전략")
        stop_loss = fib_levels['100'] * 0.98  # 저점 아래
        tp1 = fib_levels['382']
        tp2 = fib_levels['0']
    elif abs(current_price - fib_levels['500']) / current_price < 0.03:
        print(f"\n✅ 현재가가 50% 지지선 근처 - 중간 지지선 기반 전략")
        stop_loss = fib_levels['618'] * 0.98
        tp1 = fib_levels['382']
        tp2 = fib_levels['0']
    
    print(f"\n💵 진입가: {entry:,.0f}원")
    print(f"\n🎯 목표가:")
    print(f"   - TP1 (보수적): {tp1:,.0f}원 (+{(tp1-entry)/entry*100:.1f}%)")
    print(f"   - TP2 (중간):   {tp2:,.0f}원 (+{(tp2-entry)/entry*100:.1f}%)")
    print(f"   - TP3 (공격적): {tp3:,.0f}원 (+{(tp3-entry)/entry*100:.1f}%)")
    
    print(f"\n🛑 손절가: {stop_loss:,.0f}원 ({(stop_loss-entry)/entry*100:.1f}%)")
    
    # 손익비
    risk = entry - stop_loss
    reward1 = tp1 - entry
    reward2 = tp2 - entry
    print(f"\n📊 손익비:")
    print(f"   - TP1 기준: 1:{reward1/risk:.1f}")
    print(f"   - TP2 기준: 1:{reward2/risk:.1f}")
    
    # 보유일수 추천
    if rsi > 70 or bb_pos > 0.8:
        holding = "단기 (1-3일) - 과매수 구간"
    elif rsi < 30 or bb_pos < 0.2:
        holding = "단기 (2-5일) - 반등 기대"
    elif latest['macd_hist'] > 0:
        holding = "중기 (5-10일) - 상승 모멘텀"
    else:
        holding = "단기 (3-7일) - 모멘텀 약화"
    print(f"\n⏱️ 추천 보유기간: {holding}")
    
    # 종합 판단
    print(f"\n" + "=" * 70)
    print(f"📋 종합 판단")
    print("=" * 70)
    
    score = 0
    if current_price > latest['ma5']: score += 1
    if current_price > latest['ma20']: score += 1
    if rsi > 50: score += 1
    if latest['macd_hist'] > 0: score += 1
    if vol_ratio > 1.0: score += 1
    
    if score >= 4:
        overall = "매수 우선 (강한 상승 신호)"
    elif score >= 3:
        overall = "매수 고려 (양호한 신호)"
    elif score >= 2:
        overall = "관망 (혼조세)"
    else:
        overall = "매도/관망 (약세 신호)"
    
    print(f"\n기술적 점수: {score}/5")
    print(f"종합 판단: {overall}")
    
    print(f"\n" + "=" * 70)

if __name__ == '__main__':
    analyze_stock('017000', '신원종합개발')
