#!/usr/bin/env python3
"""
IVF 스캐너 v2.0 - 승률 향상 버전
추가: 다중 시간대, RSI+Stochastic, 캔들 패턴, 시장 폭
"""

import sys
sys.path.insert(0, '/root/.openclaw/workspace/strg')

import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from fdr_wrapper import get_price


def calculate_rsi(prices, period=14):
    """RSI 계산"""
    deltas = np.diff(prices)
    gains = np.where(deltas > 0, deltas, 0)
    losses = np.where(deltas < 0, -deltas, 0)
    
    avg_gain = np.mean(gains[:period])
    avg_loss = np.mean(losses[:period])
    
    if avg_loss == 0:
        return 100
    
    rs = avg_gain / avg_loss
    rsi = 100 - (100 / (1 + rs))
    
    return rsi


def calculate_stochastic(highs, lows, closes, k_period=14, d_period=3):
    """스토캐스틱 계산"""
    lowest_low = np.min(lows[-k_period:])
    highest_high = np.max(highs[-k_period:])
    
    if highest_high == lowest_low:
        return 50, 50
    
    k = 100 * (closes[-1] - lowest_low) / (highest_high - lowest_low)
    # D선은 K선의 이동평균 (간소화)
    d = k  # 실제로는 K선의 3일 평균
    
    return k, d


def detect_candle_patterns(df):
    """캔들 패턴 감지"""
    if len(df) < 5:
        return []
    
    opens = df['Open'].values
    highs = df['High'].values
    lows = df['Low'].values
    closes = df['Close'].values
    volumes = df['Volume'].values
    
    patterns = []
    
    # 최근 3봉 분석
    for i in range(-3, 0):
        body = abs(closes[i] - opens[i])
        upper_shadow = highs[i] - max(opens[i], closes[i])
        lower_shadow = min(opens[i], closes[i]) - lows[i]
        total_range = highs[i] - lows[i]
        
        if total_range == 0:
            continue
        
        # 핀바 (Pin Bar) - 아래꼬리 긴 캔들
        if lower_shadow >= body * 2 and lower_shadow >= total_range * 0.6:
            if closes[i] > opens[i]:  # 양봉
                patterns.append('Bullish_Pinbar')
        
        # 망치형 (Hammer) - 하락 후 등장
        if i > -3 and closes[i-1] < opens[i-1]:  # 전봉 음봉
            if lower_shadow >= body * 2 and closes[i] > opens[i]:
                patterns.append('Hammer')
        
        # 도지 (Doji) - 신뢰성은 낮지만 확인용
        if body <= total_range * 0.1:
            patterns.append('Doji')
    
    return patterns


def analyze_rsi_divergence(df, lookback=10):
    """RSI 다이버전스 감지"""
    closes = df['Close'].values
    
    # RSI 계산
    rsi_values = []
    for i in range(lookback, len(closes)):
        rsi = calculate_rsi(closes[i-14:i])
        rsi_values.append(rsi)
    
    if len(rsi_values) < lookback:
        return None
    
    # 최근 저점 찾기
    recent_closes = closes[-lookback:]
    recent_rsi = rsi_values[-lookback:]
    
    # Bullish Divergence: 가격 저점 하락 + RSI 저점 상승
    price_low_idx = np.argmin(recent_closes)
    rsi_low_idx = np.argmin(recent_rsi)
    
    if price_low_idx != rsi_low_idx:
        # 2개 저점 비교
        if len(recent_closes) >= 5:
            first_price_low = np.min(recent_closes[:5])
            second_price_low = np.min(recent_closes[5:])
            first_rsi_low = np.min(recent_rsi[:5])
            second_rsi_low = np.min(recent_rsi[5:])
            
            if second_price_low < first_price_low and second_rsi_low > first_rsi_low:
                return 'Bullish_Divergence'
    
    return None


def check_market_breadth_simulated():
    """
    시장 폭 확인 (시뮬레이션)
    실제 구현 시 외부 API 필요
    """
    # TODO: 실제 A/D Line, % Above 200MA 데이터 연동
    # 현재는 neutral 반환
    return {
        'ad_line_trend': 'neutral',
        'pct_above_200ma': 55,
        'signal': 'NEUTRAL'  # GO / CAUTION / STOP
    }


def calculate_ivf_v2_score(symbol, date_str):
    """
    IVF v2.0 종합 점수 계산
    """
    try:
        # 데이터 로드
        end_dt = datetime.strptime(date_str, '%Y-%m-%d')
        start_dt = end_dt - timedelta(days=90)
        
        df = get_price(symbol, start_dt.strftime('%Y-%m-%d'), date_str)
        if df is None or len(df) < 30:
            return None
        
        df = df.reset_index()
        closes = df['Close'].values
        highs = df['High'].values
        lows = df['Low'].values
        volumes = df['Volume'].values
        opens = df['Open'].values
        
        current_price = closes[-1]
        score = 0
        confluence = []
        
        # 1. 추세 구조 분석 (25점)
        ma5 = np.mean(closes[-5:])
        ma20 = np.mean(closes[-20:])
        ma60 = np.mean(closes[-60:]) if len(closes) >= 60 else ma20
        
        bullish_trend = current_price > ma5 > ma20
        higher_highs = highs[-1] > np.mean(highs[-20:-5])
        higher_lows = lows[-1] > np.mean(lows[-20:-5])
        
        if bullish_trend:
            score += 15
            confluence.append('Bullish_Trend')
        
        if higher_highs and higher_lows:
            score += 10
            confluence.append('HH_HL')
        
        # 2. 피볼나치 되돌림 (20점)
        recent_high = np.max(highs[-20:])
        recent_low = np.min(lows[-20:])
        
        if recent_high > recent_low:
            retracement = ((recent_high - current_price) / (recent_high - recent_low)) * 100
        else:
            retracement = 50
        
        if 38.2 <= retracement <= 61.8:
            score += 20
            confluence.append(f'Fib_{retracement:.0f}')
        elif 30 <= retracement < 38.2:
            score += 10
            confluence.append('Fib_Shallow')
        
        # 3. 수급/거래량 (15점)
        avg_vol_20 = np.mean(volumes[-20:])
        rvol = volumes[-1] / avg_vol_20 if avg_vol_20 > 0 else 1.0
        
        if rvol >= 2.0:
            score += 15
            confluence.append('High_RVol')
        elif rvol >= 1.5:
            score += 10
            confluence.append('RVol_1.5')
        elif rvol >= 1.2:
            score += 5
            confluence.append('RVol_Up')
        
        # 누적 확인
        close_pos = (closes[-1] - lows[-1]) / (highs[-1] - lows[-1]) if highs[-1] > lows[-1] else 0.5
        if close_pos > 0.6 and rvol > 1.2:
            score += 5
            confluence.append('Accumulation')
        
        # 4. RSI + Stochastic (15점) - NEW
        rsi = calculate_rsi(closes[-20:], 14)
        k, d = calculate_stochastic(highs[-20:], lows[-20:], closes[-20:])
        
        if 30 <= rsi <= 50:  # 과매도 회복 구간
            score += 5
            confluence.append('RSI_Oversold_Recovery')
        
        if rsi > 40 and rsi < 30:  # 30→40 돌파
            score += 5
            confluence.append('RSI_30_Break')
        
        if k > d and k < 50:  # 스토캐스틱 골든크로스
            score += 5
            confluence.append('Stoch_GC')
        
        # 5. 캔들 패턴 (10점) - NEW
        patterns = detect_candle_patterns(df)
        if 'Bullish_Pinbar' in patterns:
            score += 10
            confluence.append('Pinbar')
        elif 'Hammer' in patterns:
            score += 8
            confluence.append('Hammer')
        
        # 6. RSI 다이버전스 (10점) - NEW
        divergence = analyze_rsi_divergence(df)
        if divergence == 'Bullish_Divergence':
            score += 10
            confluence.append('RSI_Divergence')
        
        # 7. 시장 폭 (10점) - NEW
        breadth = check_market_breadth_simulated()
        if breadth['signal'] == 'GO':
            score += 10
            confluence.append('Market_Breadth_OK')
        elif breadth['signal'] == 'CAUTION':
            score += 5
            confluence.append('Market_Caution')
        
        # 진입 가능 여부
        if score >= 85:
            signal = 'STRONG_BUY'
        elif score >= 70:
            signal = 'BUY'
        elif score >= 55:
            signal = 'WATCH'
        else:
            signal = 'NEUTRAL'
        
        # 리스크 관리
        atr = np.mean([highs[-i] - lows[-i] for i in range(1, 15)])
        stop_loss = current_price - (atr * 1.5)
        target_price = current_price + (atr * 3.0)
        
        return {
            'symbol': symbol,
            'date': date_str,
            'signal': signal,
            'score': score,
            'price': round(current_price, 0),
            'rsi': round(rsi, 1),
            'stoch_k': round(k, 1),
            'rvol': round(rvol, 2),
            'fib_retracement': round(retracement, 1),
            'confluence': confluence,
            'patterns': patterns,
            'divergence': divergence,
            'stop_loss': round(stop_loss, 0),
            'target_price': round(target_price, 0),
            'rr_ratio': round((target_price - current_price) / (current_price - stop_loss), 2) if (current_price - stop_loss) > 0 else 0
        }
        
    except Exception as e:
        return None


if __name__ == '__main__':
    print("=" * 70)
    print("🔥 IVF 스캐너 v2.0 - 승률 향상 버전")
    print("=" * 70)
    
    symbols = ['005930', '042700', '033100', '012210', '348210', '000660']
    test_date = '2026-03-03'
    
    results = []
    for symbol in symbols:
        result = calculate_ivf_v2_score(symbol, test_date)
        if result:
            results.append(result)
            
            emoji = '📈' if result['signal'] in ['BUY', 'STRONG_BUY'] else '➖'
            print(f"\n{emoji} {result['symbol']}")
            print(f"   신호: {result['signal']} ({result['score']}점)")
            print(f"   현재가: {result['price']:,.0f}원")
            print(f"   RSI: {result['rsi']}, Stoch: {result['stoch_k']}")
            print(f"   피볼나치: {result['fib_retracement']:.1f}%, RVol: {result['rvol']}")
            print(f"   패턴: {result['patterns']}")
            print(f"   다이버전스: {result['divergence']}")
            print(f"   합치: {', '.join(result['confluence'])}")
            print(f"   손절: {result['stop_loss']:,.0f}, 목표: {result['target_price']:,.0f}")
    
    print(f"\n\n📊 총 {len(results)}개 신호 감지")
    strong = len([r for r in results if r['signal'] == 'STRONG_BUY'])
    buy = len([r for r in results if r['signal'] == 'BUY'])
    print(f"   STRONG_BUY: {strong}개, BUY: {buy}개")
