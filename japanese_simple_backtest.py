#!/usr/bin/env python3
"""
Japanese Classic Patterns - Simple Backtest
===========================================
일본 고전 기법 간략 백테스트
- TK_CROSS (전환선/기준선 교차)만 집중
"""

import sqlite3
import pandas as pd
import numpy as np
import json
from typing import List, Dict, Optional


def get_signal_data(db_path: str = 'data/level1_prices.db') -> List[Dict]:
    """스캔 데이터에서 TK_CROSS만 추출"""
    
    with open('reports/japanese_fast_scan_sample.json', 'r') as f:
        data = json.load(f)
    
    # TK_CROSS만 필터
    tk_cross = [d for d in data if any('TK_CROSS' in s for s in d['signals'])]
    
    return tk_cross


def backtest_signal(db_path: str, signal: Dict, 
                   holding_days: int = 5,
                   stop_loss: float = -5,
                   take_profit: float = 10) -> Optional[Dict]:
    """단일 신호 백테스트"""
    
    conn = sqlite3.connect(db_path)
    
    # 다음날 데이터 조회
    query = """
    SELECT date, open, high, low, close
    FROM price_data
    WHERE code = ? AND date > ?
    ORDER BY date
    LIMIT ?
    """
    
    df = pd.read_sql(query, conn, params=(signal['code'], signal['date'], holding_days + 2))
    conn.close()
    
    if len(df) < 2:
        return None
    
    entry_price = df.iloc[1]['open']
    
    max_profit = 0
    max_loss = 0
    exit_price = entry_price
    exit_day = 0
    exit_reason = 'hold'
    final_return = 0
    
    for day_idx, (_, row) in enumerate(df.iloc[2:].iterrows(), 1):
        day_return = (row['close'] - entry_price) / entry_price * 100
        day_high = (row['high'] - entry_price) / entry_price * 100
        day_low = (row['low'] - entry_price) / entry_price * 100
        
        max_profit = max(max_profit, day_high)
        max_loss = min(max_loss, day_low)
        
        if day_low <= stop_loss:
            final_return = stop_loss
            exit_reason = 'stop_loss'
            break
        
        if day_high >= take_profit:
            final_return = take_profit
            exit_reason = 'take_profit'
            break
        
        if day_idx >= holding_days:
            final_return = day_return
            exit_reason = 'time_exit'
            break
    
    signal_type = 'BULLISH' if 'TK_CROSS_BULLISH' in signal['signals'] else 'BEARISH'
    
    return {
        'code': signal['code'],
        'name': signal['name'],
        'signal_type': signal_type,
        'entry_price': entry_price,
        'final_return': final_return,
        'max_profit': max_profit,
        'max_loss': max_loss,
        'exit_reason': exit_reason,
    }


def main():
    db_path = 'data/level1_prices.db'
    
    # 데이터 로드
    signals = get_signal_data()
    
    print(f"📊 총 신호: {len(signals)}개")
    print(f"  - 골든크로스: {sum(1 for s in signals if 'TK_CROSS_BULLISH' in s['signals'])}개")
    print(f"  - 데드크로스: {sum(1 for s in signals if 'TK_CROSS_BEARISH' in s['signals'])}개")
    
    # 백테스트
    print("\n🧪 백테스트 진행...")
    
    bullish_results = []
    bearish_results = []
    
    for sig in signals:
        result = backtest_signal(db_path, sig)
        if result:
            if result['signal_type'] == 'BULLISH':
                bullish_results.append(result)
            else:
                bearish_results.append(result)
    
    # 결과 출력
    print("\n" + "=" * 70)
    print("📊 TK_CROSS 백테스트 결과")
    print("=" * 70)
    
    if bullish_results:
        bull_returns = [r['final_return'] for r in bullish_results]
        bull_wins = len([r for r in bullish_results if r['final_return'] > 0])
        
        print(f"\n🟢 골든크로스 (매수 신호)")
        print(f"  총 신호: {len(bullish_results)}개")
        print(f"  승률: {bull_wins/len(bullish_results)*100:.1f}%")
        print(f"  평균 수익률: {np.mean(bull_returns):+.2f}%")
        print(f"  최대 수익: {max(bull_returns):+.1f}%")
        print(f"  최대 손실: {min(bull_returns):+.1f}%")
    
    if bearish_results:
        bear_returns = [r['final_return'] for r in bearish_results]
        bear_wins = len([r for r in bearish_results if r['final_return'] > 0])
        
        print(f"\n🔴 데드크로스 (매도 신호)")
        print(f"  총 신호: {len(bearish_results)}개")
        print(f"  승률: {bear_wins/len(bearish_results)*100:.1f}%")
        print(f"  평균 수익률: {np.mean(bear_returns):+.2f}%")


if __name__ == '__main__':
    main()
