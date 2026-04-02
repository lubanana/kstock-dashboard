#!/usr/bin/env python3
"""
IVF 고품질 스캐너 - 디버그 버전
"""

import sys
sys.path.insert(0, '/root/.openclaw/workspace/strg')

import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from fdr_wrapper import get_price
from ivf_scanner_quality import analyze_structure_quality, analyze_fibonacci_quality, analyze_volume_quality


def debug_signal(symbol, date_str):
    """디버그용 신호 분석"""
    print(f"\n🔍 {symbol} ({date_str}) 분석")
    print("-" * 50)
    
    try:
        end_dt = datetime.strptime(date_str, '%Y-%m-%d')
        start_dt = end_dt - timedelta(days=90)
        
        df = get_price(symbol, start_dt.strftime('%Y-%m-%d'), date_str)
        if df is None or len(df) < 30:
            print("❌ 데이터 부족")
            return
        
        current_price = df['Close'].iloc[-1]
        print(f"현재가: {current_price:,.0f}원")
        
        # 각 분석 수행
        struct = analyze_structure_quality(df)
        fib = analyze_fibonacci_quality(df)
        vol = analyze_volume_quality(df)
        
        print(f"\n📈 구조 분석:")
        print(f"   유효: {struct['valid']}")
        if struct['valid']:
            print(f"   Bullish Trend: {struct['bullish_trend']}")
            print(f"   Higher Highs: {struct['higher_highs']}")
            print(f"   Higher Lows: {struct['higher_lows']}")
            print(f"   Breakout: {struct['breakout']}")
            print(f"   Volume Confirm: {struct['volume_confirm']}")
            print(f"   구조 점수: {struct['structure_score']}/5")
        
        print(f"\n📊 피볼나치 분석:")
        print(f"   유효: {fib['valid']}")
        if fib['valid']:
            print(f"   되돌림: {fib['retracement']:.1f}%")
            print(f"   Optimal Zone (38.2~61.8%): {fib['optimal_zone']}")
            print(f"   Ideal Zone (50~61.8%): {fib['ideal_zone']}")
        
        print(f"\n💧 수급 분석:")
        print(f"   유효: {vol['valid']}")
        if vol['valid']:
            print(f"   RVol: {vol['rvol']:.2f}")
            print(f"   High Volume (≥2.0): {vol['high_volume']}")
            print(f"   Accumulation: {vol['accumulation']}")
            print(f"   Strong Accumulation: {vol['strong_accumulation']}")
        
        # 합치 계산
        confluence = []
        score = 0
        
        if struct['valid'] and struct['bullish_trend']:
            score += 15
            confluence.append('Bullish_Trend')
        
        if struct['valid'] and struct['higher_highs'] and struct['higher_lows']:
            score += 15
            confluence.append('HH_HL')
        
        if fib['valid'] and fib['optimal_zone']:
            score += 20
            confluence.append('Fib_38-62')
        
        if fib['valid'] and fib['ideal_zone']:
            score += 15
            confluence.append('Fib_50-62')
        
        if vol['valid'] and vol['strong_accumulation']:
            score += 20
            confluence.append('Strong_Accum')
        elif vol['valid'] and vol['accumulation']:
            score += 10
            confluence.append('Accumulation')
        
        if vol['valid'] and vol['high_volume']:
            score += 15
            confluence.append('High_RVol')
        
        print(f"\n🎯 종합:")
        print(f"   점수: {score}")
        print(f"   합치: {confluence}")
        
        min_met = (struct['valid'] and (struct['bullish_trend'] or struct['higher_highs'])) and \
                  (fib['valid'] and fib['optimal_zone']) and len(confluence) >= 2
        
        print(f"   최소조건 충족: {min_met}")
        
        if score >= 70:
            print(f"   ✅ 고품질 신호!")
        elif score >= 60:
            print(f"   △ 중간 품질")
        else:
            print(f"   ❌ 낮은 점수")
            
    except Exception as e:
        print(f"❌ 오류: {e}")


if __name__ == '__main__':
    print("=" * 70)
    print("🔥 IVF 고품질 스캐너 - 디버그 모드")
    print("=" * 70)
    
    symbols = ['005930', '042700', '033100', '012210', '348210']
    test_date = '2026-03-03'
    
    for symbol in symbols:
        debug_signal(symbol, test_date)
