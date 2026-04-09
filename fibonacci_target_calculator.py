#!/usr/bin/env python3
"""
피볼나치 + 엘리엇 파동 목표가 계산기
"""

import sys
sys.path.insert(0, '/root/.openclaw/workspace/strg')

import pandas as pd
import numpy as np
import sqlite3
from datetime import datetime, timedelta

DB_PATH = '/root/.openclaw/workspace/strg/data/level1_prices.db'

def get_stock_data(code, days=120):
    """종목 데이터 로드"""
    conn = sqlite3.connect(DB_PATH)
    
    query = f"""
    SELECT date, open, high, low, close, volume 
    FROM price_data 
    WHERE code = '{code}' 
    ORDER BY date DESC
    LIMIT {days}
    """
    
    df = pd.read_sql_query(query, conn)
    df['date'] = pd.to_datetime(df['date'])
    df = df.sort_values('date').reset_index(drop=True)
    
    conn.close()
    return df

def calculate_atr(df, period=14):
    """ATR 계산"""
    df = df.copy()
    df['tr1'] = df['high'] - df['low']
    df['tr2'] = abs(df['high'] - df['close'].shift(1))
    df['tr3'] = abs(df['low'] - df['close'].shift(1))
    df['tr'] = df[['tr1', 'tr2', 'tr3']].max(axis=1)
    df['atr'] = df['tr'].rolling(window=period, min_periods=1).mean()
    return df['atr'].iloc[-1]

def find_swing_points(df, lookback=40):
    """스윙 고점/저점 찾기"""
    recent = df.tail(lookback)
    
    swing_high = recent['high'].max()
    swing_high_idx = recent['high'].idxmax()
    swing_high_date = recent.loc[swing_high_idx, 'date']
    
    swing_low = recent['low'].min()
    swing_low_idx = recent['low'].idxmin()
    swing_low_date = recent.loc[swing_low_idx, 'date']
    
    return {
        'high': swing_high,
        'high_date': swing_high_date,
        'low': swing_low,
        'low_date': swing_low_date
    }

def calculate_fibonacci_levels(swing_high, swing_low, current_price):
    """피볼나치 레벨 계산"""
    diff = swing_high - swing_low
    
    levels = {
        '0%_extension': swing_high + diff * 0.272,
        '23.6%': swing_high - diff * 0.236,
        '38.2%': swing_high - diff * 0.382,
        '50%': swing_high - diff * 0.50,
        '61.8%': swing_high - diff * 0.618,
        '78.6%': swing_high - diff * 0.786,
        '100%': swing_low,
        '127.2%_ext': swing_high + diff * 0.272,
        '161.8%_ext': swing_high + diff * 0.618,
        '261.8%_ext': swing_high + diff * 1.618,
    }
    
    # 현재가 위치 확인
    if current_price >= levels['38.2%']:
        position = "38.2% ~ 23.6% (되돌림 약함)"
    elif current_price >= levels['50%']:
        position = "50% ~ 38.2% (정상 되돌림)"
    elif current_price >= levels['61.8%']:
        position = "61.8% ~ 50% (깊은 되돌림)"
    elif current_price >= levels['78.6%']:
        position = "78.6% ~ 61.8% (매우 깊은 되돌림)"
    else:
        position = "100% 이하 (추세 전환 가능)"
    
    return levels, position

def calculate_elliott_targets(df, swing_high, swing_low):
    """엘리엇 파동 목표가 계산"""
    wave_1_2_range = swing_high - swing_low
    
    # 파동 3 목표 (파동 1의 1.618배 ~ 2.618배)
    wave_3_target_1 = swing_high + wave_1_2_range * 1.618
    wave_3_target_2 = swing_high + wave_1_2_range * 2.0
    wave_3_target_3 = swing_high + wave_1_2_range * 2.618
    
    # 파동 5 목표 (파동 1의 0.618배 ~ 1.0배, 파동 3 대비)
    wave_5_target_1 = wave_3_target_1 + wave_1_2_range * 0.618
    wave_5_target_2 = wave_3_target_2 + wave_1_2_range * 1.0
    
    return {
        'wave_3_tp1': wave_3_target_1,
        'wave_3_tp2': wave_3_target_2,
        'wave_3_tp3': wave_3_target_3,
        'wave_5_tp1': wave_5_target_1,
        'wave_5_tp2': wave_5_target_2
    }

def calculate_risk_management(entry_price, atr, fib_levels):
    """리스크 관리 계산"""
    # 손절가: ATR 1.5배 또는 61.8% 레벨 중 가까운 것
    atr_stop = entry_price - (atr * 1.5)
    fib_stop = fib_levels['61.8%']
    stop_loss = max(atr_stop, fib_stop)  # 더 가까운 손절 (보수적)
    
    # 목표가
    tp1 = fib_levels['127.2%_ext']  # 피볼나치 127.2% 확장
    tp2 = fib_levels['161.8%_ext']  # 피볼나치 161.8% 확장 (골디락스)
    tp3 = fib_levels['261.8%_ext']  # 피볼나치 261.8% 확장 (공격적)
    
    # 리스크/리워드
    risk = entry_price - stop_loss
    rr_1 = (tp1 - entry_price) / risk if risk > 0 else 0
    rr_2 = (tp2 - entry_price) / risk if risk > 0 else 0
    rr_3 = (tp3 - entry_price) / risk if risk > 0 else 0
    
    return {
        'entry': entry_price,
        'stop_loss': stop_loss,
        'risk_pct': (risk / entry_price) * 100,
        'tp1': tp1,
        'tp2': tp2,
        'tp3': tp3,
        'rr_1': rr_1,
        'rr_2': rr_2,
        'rr_3': rr_3
    }

def analyze_stock(code, name, current_price):
    """종목 종합 분석"""
    print("=" * 70)
    print(f"🔮 피볼나치 + 엘리엇 파동 분석")
    print("=" * 70)
    print(f"종목: {name} ({code})")
    print(f"현재가: {current_price:,}원")
    print(f"분석일: {datetime.now().strftime('%Y-%m-%d')}")
    print("=" * 70)
    
    # 데이터 로드
    df = get_stock_data(code)
    if len(df) < 40:
        print("⚠️ 데이터 부족 (40일 미만)")
        return
    
    # ATR 계산
    atr = calculate_atr(df)
    print(f"\n📊 ATR(14): {atr:,.0f}원 ({(atr/current_price)*100:.2f}%)")
    
    # 스윙 포인트
    swing = find_swing_points(df)
    print(f"\n📈 최근 40일 스윙")
    print(f"  고점: {swing['high']:,.0f}원 ({swing['high_date'].strftime('%m/%d')})")
    print(f"  저점: {swing['low']:,.0f}원 ({swing['low_date'].strftime('%m/%d')})")
    print(f"  구간: {swing['high'] - swing['low']:,.0f}원 ({((swing['high']/swing['low'])-1)*100:.1f}%)")
    
    # 피볼나치 레벨
    fib_levels, position = calculate_fibonacci_levels(swing['high'], swing['low'], current_price)
    
    print(f"\n🎯 피볼나치 되돌림 레벨")
    print(f"  현재 위치: {position}")
    print(f"\n  저항 (Resistance):")
    print(f"    23.6%: {fib_levels['23.6%']:,.0f}원 ({((fib_levels['23.6%']/current_price)-1)*100:+.1f}%)")
    print(f"    38.2%: {fib_levels['38.2%']:,.0f}원 ({((fib_levels['38.2%']/current_price)-1)*100:+.1f}%)")
    print(f"    50%:   {fib_levels['50%']:,.0f}원 ({((fib_levels['50%']/current_price)-1)*100:+.1f}%)")
    
    print(f"\n  지지 (Support):")
    print(f"    61.8%: {fib_levels['61.8%']:,.0f}원 ({((fib_levels['61.8%']/current_price)-1)*100:+.1f}%)")
    print(f"    78.6%: {fib_levels['78.6%']:,.0f}원 ({((fib_levels['78.6%']/current_price)-1)*100:+.1f}%)")
    print(f"    100%:  {fib_levels['100%']:,.0f}원 ({((fib_levels['100%']/current_price)-1)*100:+.1f}%)")
    
    # 피볼나치 확장 (목표가)
    print(f"\n🚀 피볼나치 확장 목표가")
    print(f"    127.2%: {fib_levels['127.2%_ext']:,.0f}원 ({((fib_levels['127.2%_ext']/current_price)-1)*100:+.1f}%)")
    print(f"    161.8%: {fib_levels['161.8%_ext']:,.0f}원 ({((fib_levels['161.8%_ext']/current_price)-1)*100:+.1f}%)")
    print(f"    261.8%: {fib_levels['261.8%_ext']:,.0f}원 ({((fib_levels['261.8%_ext']/current_price)-1)*100:+.1f}%)")
    
    # 엘리엇 파동
    elliott = calculate_elliott_targets(df, swing['high'], swing['low'])
    print(f"\n🌊 엘리엇 파동 이론 기준")
    print(f"  [파동 3 목표] (파동 1 대비)")
    print(f"    보수적 (1.618x): {elliott['wave_3_tp1']:,.0f}원")
    print(f"    중립적 (2.0x):   {elliott['wave_3_tp2']:,.0f}원")
    print(f"    공격적 (2.618x): {elliott['wave_3_tp3']:,.0f}원")
    
    # 리스크 관리
    risk = calculate_risk_management(current_price, atr, fib_levels)
    
    print(f"\n⚠️  리스크 관리 (진입가 {current_price:,}원 기준)")
    print(f"  손절가: {risk['stop_loss']:,.0f}원 (-{risk['risk_pct']:.1f}%)")
    print(f"\n  목표가:")
    print(f"    TP1 (127.2%): {risk['tp1']:,.0f}원 (+{((risk['tp1']/current_price)-1)*100:.1f}%) | R:R = 1:{risk['rr_1']:.1f}")
    print(f"    TP2 (161.8%): {risk['tp2']:,.0f}원 (+{((risk['tp2']/current_price)-1)*100:.1f}%) | R:R = 1:{risk['rr_2']:.1f} ⭐ 추천")
    print(f"    TP3 (261.8%): {risk['tp3']:,.0f}원 (+{((risk['tp3']/current_price)-1)*100:.1f}%) | R:R = 1:{risk['rr_3']:.1f}")
    
    # 추천 전략
    print(f"\n💡 추천 전략")
    print(f"  1. 진입: 현재가 ~ {fib_levels['61.8%']:,.0f}원 (61.8% 지지선 근처)")
    print(f"  2. 손절: {risk['stop_loss']:,.0f}원 이탈 시 (-{risk['risk_pct']:.1f}%)")
    print(f"  3. 목표: TP2 {risk['tp2']:,.0f}원까지 추격 (피볼나치 161.8%)")
    print(f"  4. 분할익절: TP1(30%) → TP2(40%) → TP3(30%)")
    
    # 엘리엇 추가
    print(f"\n  [엘리엇 파동 시나리오]")
    print(f"    현재가가 파동 2의 되돌림이라면:")
    print(f"    → 파동 3 목표: {elliott['wave_3_tp2']:,.0f}원 (파동 1의 2배)")
    print(f"    → 이후 파동 4 되돌림 후 파동 5 목표: {elliott['wave_5_tp2']:,.0f}원")
    
    print("\n" + "=" * 70)
    print("※ 본 분석은 기술적 분석 기반 참고 자료이며, 투자 결정은 본인의 판단과 책임 하에 이루어져야 합니다.")
    print("=" * 70)

if __name__ == '__main__':
    # 신원종합개발 (017000) - 4/8 선정 종목
    analyze_stock('017000', '신원종합개발', 3120)
