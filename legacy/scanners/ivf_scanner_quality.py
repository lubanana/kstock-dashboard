#!/usr/bin/env python3
"""
IVF 스캐너 - 고품질 신호 전용 (Quality over Quantity)
매매 빈도 ↓, 승률 ↑
"""

import sys
sys.path.insert(0, '/root/.openclaw/workspace/strg')

import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from fdr_wrapper import get_price


def analyze_structure_quality(df):
    """고품질 추세 구조 분석"""
    if len(df) < 30:
        return {'valid': False}
    
    closes = df['Close'].values
    highs = df['High'].values
    lows = df['Low'].values
    volumes = df['Volume'].values
    
    # 이동평균
    ma5 = np.mean(closes[-5:])
    ma20 = np.mean(closes[-20:])
    ma60 = np.mean(closes[-60:]) if len(closes) >= 60 else ma20
    
    # 추세 확인 (정배열)
    bullish_trend = closes[-1] > ma5 > ma20
    
    # 고점/저점 추적 (최근 20봉)
    recent_highs = highs[-20:]
    recent_lows = lows[-20:]
    
    # 상승 구조: 고점과 저점이 모두 상승
    higher_highs = recent_highs[-1] > np.mean(recent_highs[:10])
    higher_lows = recent_lows[-1] > np.mean(recent_lows[:10])
    
    # 돌파 확인 - 최근 10봉 내 고점 돌파
    recent_swing_high = np.max(recent_highs[:-5])  # 최근 5봉 제외
    breakout = highs[-1] > recent_swing_high * 0.98  # 2% 이내 근접
    
    # 거래량 확인
    avg_vol = np.mean(volumes[-20:])
    recent_vol = np.mean(volumes[-3:])
    volume_confirm = recent_vol >= avg_vol * 1.5
    
    return {
        'valid': True,
        'bullish_trend': bullish_trend,
        'higher_highs': higher_highs,
        'higher_lows': higher_lows,
        'breakout': breakout,
        'volume_confirm': volume_confirm,
        'structure_score': sum([bullish_trend, higher_highs, higher_lows, breakout, volume_confirm])
    }


def analyze_fibonacci_quality(df):
    """고품질 피볼나치 분석 - 38.2~61.8% 구간만"""
    if len(df) < 20:
        return {'valid': False}
    
    closes = df['Close'].values
    highs = df['High'].values
    lows = df['Low'].values
    
    # 최근 추세 고점/저점
    recent_high = np.max(highs[-20:])
    recent_low = np.min(lows[-20:])
    current = closes[-1]
    
    if recent_high <= recent_low:
        return {'valid': False}
    
    # 되돌림 계산
    retracement = ((recent_high - current) / (recent_high - recent_low)) * 100
    
    # 최적 진입 구간: 38.2% ~ 61.8%
    optimal_zone = 38.2 <= retracement <= 61.8
    
    # 이상적 구간: 50% ~ 61.8%
    ideal_zone = 50 <= retracement <= 61.8
    
    return {
        'valid': True,
        'retracement': retracement,
        'optimal_zone': optimal_zone,
        'ideal_zone': ideal_zone,
        'high': recent_high,
        'low': recent_low
    }


def analyze_volume_quality(df):
    """고품질 수급 분석"""
    if len(df) < 20:
        return {'valid': False}
    
    volumes = df['Volume'].values
    closes = df['Close'].values
    highs = df['High'].values
    lows = df['Low'].values
    
    # RVol 계산
    avg_vol_20 = np.mean(volumes[-20:])
    current_vol = volumes[-1]
    rvol = current_vol / avg_vol_20 if avg_vol_20 > 0 else 1.0
    
    # 고품질 수급: RVol >= 2.0
    high_volume = rvol >= 2.0
    
    # 누적 패턴 (Accumulation)
    close_positions = [(closes[-i] - lows[-i]) / (highs[-i] - lows[-i]) 
                       if highs[-i] > lows[-i] else 0.5 for i in range(1, 4)]
    avg_close_pos = np.mean(close_positions)
    accumulation = avg_close_pos > 0.6
    
    # 거래량 급증 + 종가 상단 = 강한 누적
    strong_accumulation = rvol >= 2.0 and accumulation
    
    return {
        'valid': True,
        'rvol': rvol,
        'high_volume': high_volume,
        'accumulation': accumulation,
        'strong_accumulation': strong_accumulation,
        'quality_score': (2 if strong_accumulation else 1 if accumulation else 0) + 
                        (1 if high_volume else 0)
    }


def calculate_quality_signal(symbol, date_str):
    """고품질 신호 계산 - 확실한 케이스만"""
    try:
        # 데이터 로드
        end_dt = datetime.strptime(date_str, '%Y-%m-%d')
        start_dt = end_dt - timedelta(days=90)
        
        df = get_price(symbol, start_dt.strftime('%Y-%m-%d'), date_str)
        if df is None or len(df) < 30:
            return None
        
        current_price = df['Close'].iloc[-1]
        
        # 각 분석 수행
        struct = analyze_structure_quality(df)
        fib = analyze_fibonacci_quality(df)
        vol = analyze_volume_quality(df)
        
        if not struct['valid'] or not fib['valid'] or not vol['valid']:
            return None
        
        # 고품질 조건 검사 (최소 3개 합치 필요)
        confluence = []
        score = 0
        
        # 1. 추세 구조 (필수) - 30점
        if struct['bullish_trend']:
            score += 15
            confluence.append('Bullish_Trend')
        
        if struct['higher_highs'] and struct['higher_lows']:
            score += 15
            confluence.append('HH_HL')
        
        # 2. 피볼나치 (필수) - 35점
        if fib['optimal_zone']:
            score += 20
            confluence.append('Fib_38-62')
        
        if fib['ideal_zone']:
            score += 15
            confluence.append('Fib_50-62')
        
        # 3. 수급 (선택) - 25점 (완화)
        if vol['strong_accumulation']:
            score += 25
            confluence.append('Strong_Accum')
        elif vol['accumulation']:
            score += 15
            confluence.append('Accumulation')
        elif vol['rvol'] >= 1.5:
            score += 10
            confluence.append('Volume_Up')
        
        # 4. 거래량 (선택) - 10점 (완화)
        if vol['rvol'] >= 2.0:
            score += 10
            confluence.append('High_RVol')
        elif vol['rvol'] >= 1.5:
            score += 5
            confluence.append('RVol_1.5')
        
        # 최소 조건: 추세 + 피볼나치 (2개 합치)
        min_met = (struct['bullish_trend'] or struct['higher_highs']) and \
                  fib['optimal_zone'] and len(confluence) >= 2
        
        if not min_met:
            return None
        
        # 신호 등급 (70점 이상만 실제 매수)
        if score >= 80:
            signal = 'STRONG_BUY'
        elif score >= 70:
            signal = 'BUY'
        elif score >= 60:
            signal = 'WATCH'
        else:
            signal = 'NEUTRAL'
        
        # ATR 계산 (간단)
        highs = df['High'].values[-20:]
        lows = df['Low'].values[-20:]
        closes = df['Close'].values[-20:]
        tr_list = []
        for i in range(1, len(closes)):
            tr = max(
                highs[i] - lows[i],
                abs(highs[i] - closes[i-1]),
                abs(lows[i] - closes[i-1])
            )
            tr_list.append(tr)
        atr = np.mean(tr_list) if tr_list else current_price * 0.02
        
        # 진입/손절/목표가 계산
        entry_price = current_price
        stop_loss = entry_price - (atr * 1.5)  # ATR 1.5배
        target_price = entry_price + (atr * 3.0)  # ATR 3배 (1:2 R:R)
        
        # R:R 계산
        risk = entry_price - stop_loss
        reward = target_price - entry_price
        rr = reward / risk if risk > 0 else 0
        
        # 최소 1:1.5 R:R
        if rr < 1.5:
            return None
        
        return {
            'symbol': symbol,
            'date': date_str,
            'signal': signal,
            'score': score,
            'price': current_price,
            'confluence': confluence,
            'fib_retracement': round(fib['retracement'], 1),
            'rvol': round(vol['rvol'], 2),
            'structure_score': struct['structure_score'],
            'entry_price': round(entry_price, 0),
            'stop_loss': round(stop_loss, 0),
            'target_price': round(target_price, 0),
            'rr_ratio': round(rr, 2)
        }
        
    except Exception as e:
        return None


if __name__ == '__main__':
    print("=" * 70)
    print("🔥 IVF 고품질 스캐너 (Quality over Quantity)")
    print("=" * 70)
    
    symbols = ['005930', '042700', '033100', '348210', '012210', '025980']
    test_date = '2026-03-03'
    
    results = []
    for symbol in symbols:
        result = calculate_quality_signal(symbol, test_date)
        if result:
            results.append(result)
            emoji = '📈' if result['signal'] in ['BUY', 'STRONG_BUY'] else '➖'
            print(f"\n{emoji} {result['symbol']}")
            print(f"   신호: {result['signal']} ({result['score']}점)")
            print(f"   현재가: {result['price']:,.0f}원")
            print(f"   합치: {', '.join(result['confluence'])}")
            print(f"   피볼나치: {result['fib_retracement']:.1f}%")
            print(f"   RVol: {result['rvol']}")
            print(f"   손절가: {result['stop_loss']:,.0f}원")
            print(f"   목표가: {result['target_price']:,.0f}원")
            print(f"   R:R = 1:{result['rr_ratio']:.1f}")
    
    if not results:
        print("\n⚠️ 고품질 신호 없음")
    
    print(f"\n\n총 {len(results)}개 고품질 신호 감지")
