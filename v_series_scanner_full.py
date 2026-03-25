#!/usr/bin/env python3
"""
V-Series 전체 종목 스캐너 (DB 기반)
이미 업데이트된 DB를 사용하여 빠르게 스캔
"""

import pandas as pd
import numpy as np
import sqlite3
from datetime import datetime, timedelta
import json
import os

def get_all_symbols_from_db(db_path='data/pivot_strategy.db'):
    """DB에서 모든 종목 코드 가져오기"""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT DISTINCT symbol 
        FROM stock_prices 
        WHERE date = '2026-03-25'
        ORDER BY symbol
    """)
    
    symbols = [row[0] for row in cursor.fetchall()]
    conn.close()
    
    return symbols

def get_stock_data(symbol, db_path='data/pivot_strategy.db', days=100):
    """DB에서 종목 데이터 가져오기"""
    conn = sqlite3.connect(db_path)
    
    query = """
        SELECT date, open, high, low, close, volume
        FROM stock_prices
        WHERE symbol = ?
        ORDER BY date DESC
        LIMIT ?
    """
    
    df = pd.read_sql_query(query, conn, params=(symbol, days))
    conn.close()
    
    if len(df) < 60:
        return None
    
    df = df.sort_values('date')
    df['date'] = pd.to_datetime(df['date'])
    
    return df

def calculate_atr(df, period=14):
    """ATR 계산"""
    high = df['high']
    low = df['low']
    close = df['close']
    
    tr1 = high - low
    tr2 = abs(high - close.shift(1))
    tr3 = abs(low - close.shift(1))
    
    tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
    atr = tr.rolling(window=period, min_periods=1).mean()
    
    return atr

def calculate_fibonacci_levels(df, lookback=20):
    """Fibonacci 레벨 계산"""
    recent_high = df['high'].rolling(window=lookback, min_periods=5).max().iloc[-1]
    recent_low = df['low'].rolling(window=lookback, min_periods=5).min().iloc[-1]
    
    price_range = recent_high - recent_low
    
    fib_382 = recent_high - price_range * 0.382
    fib_50 = recent_high - price_range * 0.5
    fib_618 = recent_high - price_range * 0.618
    fib_1382 = recent_high + price_range * 0.382
    fib_1618 = recent_high + price_range * 0.618
    
    return {
        'high': recent_high,
        'low': recent_low,
        'fib_382': fib_382,
        'fib_50': fib_50,
        'fib_618': fib_618,
        'fib_1382': fib_1382,
        'fib_1618': fib_1618
    }

def calculate_value_score(df):
    """가치 점수 계산"""
    current_price = df['close'].iloc[-1]
    
    # 52주 최고/최저
    high_52w = df['high'].rolling(252, min_periods=60).max().iloc[-1]
    low_52w = df['low'].rolling(252, min_periods=60).min().iloc[-1]
    price_range = (current_price - low_52w) / (high_52w - low_52w) if high_52w > low_52w else 0.5
    
    # 추세 점수
    ma20 = df['close'].rolling(20).mean().iloc[-1]
    ma60 = df['close'].rolling(60).mean().iloc[-1]
    trend_score = 100 if current_price > ma20 > ma60 else 50 if current_price > ma60 else 0
    
    # 거래량 안정성
    volume_mean = df['volume'].rolling(20).mean().iloc[-1]
    volume_std = df['volume'].rolling(20).std().iloc[-1]
    volume_stability = 100 - min(100, (volume_std / volume_mean * 100)) if volume_mean > 0 else 0
    
    value_score = (price_range * 30) + (trend_score * 0.4) + (volume_stability * 0.3)
    
    # 전략 분류
    if price_range < 0.3:
        strategy = "Graham_NetNet"
    elif trend_score >= 80:
        strategy = "Quality_FairPrice"
    elif volume_stability >= 70:
        strategy = "Dividend_Machine"
    else:
        strategy = "Value_Blend"
    
    return value_score, strategy

def scan_all_stocks(min_value_score=65, min_rr=1.5):
    """전체 종목 스캔"""
    
    print("🔍 V-Series 전체 종목 스캔 시작 (DB 기반)")
    print("=" * 60)
    
    # 종목 리스트 가져오기
    symbols = get_all_symbols_from_db()
    print(f"대상 종목: {len(symbols):,}개")
    print("-" * 60)
    
    candidates = []
    
    for i, symbol in enumerate(symbols, 1):
        if i % 500 == 0:
            print(f"  진행: {i}/{len(symbols)}... ({i/len(symbols)*100:.1f}%)")
        
        try:
            # 데이터 가져오기
            df = get_stock_data(symbol)
            if df is None or len(df) < 60:
                continue
            
            # 1. 가치 점수 계산
            value_score, strategy_type = calculate_value_score(df)
            if value_score < min_value_score:
                continue
            
            # 2. ATR 계산
            atr = calculate_atr(df, 14).iloc[-1]
            current_price = df['close'].iloc[-1]
            
            # 최소 거래대금 확인 (10억)
            avg_volume = df['volume'].rolling(20).mean().iloc[-1]
            avg_amount = avg_volume * current_price
            if avg_amount < 1_000_000_000:
                continue
            
            # 3. Fibonacci 레벨
            fib_levels = calculate_fibonacci_levels(df)
            
            # 4. 진입가 확인 (Fibonacci 50% 근처)
            tolerance = fib_levels['fib_50'] * 0.05
            if not (fib_levels['fib_50'] - tolerance <= current_price <= fib_levels['fib_50'] + tolerance):
                # fib_382도 체크
                tolerance_382 = fib_levels['fib_382'] * 0.05
                if not (fib_levels['fib_382'] - tolerance_382 <= current_price <= fib_levels['fib_382'] + tolerance_382):
                    continue
                fib_level_used = 'fib_382'
            else:
                fib_level_used = 'fib_50'
            
            entry_price = current_price
            target_price = fib_levels['fib_1618']
            stop_loss = entry_price - (atr * 1.5)
            
            # 5. 손익비 확인
            if entry_price <= stop_loss or target_price <= entry_price:
                continue
            
            risk = entry_price - stop_loss
            reward = target_price - entry_price
            rr_ratio = reward / risk if risk > 0 else 0
            
            if rr_ratio < min_rr:
                continue
            
            expected_return = (target_price - entry_price) / entry_price * 100
            expected_loss = (stop_loss - entry_price) / entry_price * 100
            
            candidates.append({
                'symbol': symbol,
                'value_score': value_score,
                'strategy_type': strategy_type,
                'current_price': current_price,
                'entry_price': entry_price,
                'target_price': target_price,
                'stop_loss': stop_loss,
                'rr_ratio': rr_ratio,
                'atr': atr,
                'fib_level': fib_level_used,
                'fib_high': fib_levels['high'],
                'fib_low': fib_levels['low'],
                'expected_return': expected_return,
                'expected_loss': expected_loss,
                'avg_volume': avg_volume,
                'avg_amount': avg_amount
            })
            
        except Exception as e:
            continue
    
    print(f"\n✅ 스캔 완료: {len(symbols):,}개 중 {len(candidates)}개 통과")
    
    # 가치점수 순으로 정렬
    candidates.sort(key=lambda x: x['value_score'], reverse=True)
    
    return candidates

def main():
    """메인 실행"""
    scan_date = datetime(2026, 3, 25)
    
    # 전체 스캔
    results = scan_all_stocks(min_value_score=65, min_rr=1.5)
    
    if not results:
        print("❌ 선정된 종목이 없습니다.")
        return
    
    # 결과 출력
    print("\n" + "=" * 60)
    print(f"📈 V-Series 선정 종목 TOP {min(20, len(results))} (2026-03-25)")
    print("=" * 60)
    
    for i, stock in enumerate(results[:20], 1):
        print(f"\n{i}. {stock['symbol']} ({stock['strategy_type']})")
        print(f"   가치점수: {stock['value_score']:.1f}")
        print(f"   현재가: ₩{stock['current_price']:,.0f}")
        print(f"   목표가: ₩{stock['target_price']:,.0f} ({stock['expected_return']:+.1f}%)")
        print(f"   손절가: ₩{stock['stop_loss']:,.0f} ({stock['expected_loss']:+.1f}%)")
        print(f"   손익비: 1:{stock['rr_ratio']:.2f}")
    
    # JSON 저장
    output = {
        'scan_date': '2026-03-25',
        'total_symbols': 3299,
        'selected_count': len(results),
        'parameters': {
            'min_value_score': 65,
            'min_rr': 1.5,
            'atr_multiplier': 1.5
        },
        'top_stocks': results[:50]  # TOP 50 저장
    }
    
    output_path = './reports/v_series/v_series_scan_20260325_full.json'
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(output, f, ensure_ascii=False, indent=2)
    
    print(f"\n💾 결과 저장: {output_path}")
    print(f"   총 {len(results)}개 종목 선정")

if __name__ == "__main__":
    main()
