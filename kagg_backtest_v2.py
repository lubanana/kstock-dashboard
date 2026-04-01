#!/usr/bin/env python3
"""
KAGGRESSIVE 백테스트 v2 - 실제 점수 필터 적용
70점+만 진입, 3일 보유
"""

import sys
sys.path.insert(0, '/root/.openclaw/workspace/strg')

import sqlite3
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from fdr_wrapper import get_price
from kagg import KAggressiveScanner


def run_kagg_backtest():
    """KAGGRESSIVE 전략 백테스트"""
    
    print('='*70)
    print('🔥 KAGGRESSIVE 백테스트 (70점+ / 3일 보유)')
    print('='*70)
    
    scanner = KAggressiveScanner()
    conn = sqlite3.connect('data/pivot_strategy.db')
    cursor = conn.cursor()
    
    # 테스트 기간 (월초)
    test_dates = [
        '2026-01-02', '2026-01-13', '2026-01-20',
        '2026-02-03', '2026-02-13', '2026-02-20',
        '2026-03-02', '2026-03-13', '2026-03-20',
    ]
    
    all_trades = []
    
    for date in test_dates:
        print(f'\n📅 {date} 스캔 중...')
        
        # 해당 날짜에 거래 가능한 종목
        cursor.execute('''
            SELECT DISTINCT s.symbol, s.name
            FROM stock_info s
            JOIN stock_prices p ON s.symbol = p.symbol
            WHERE p.date = ?
        ''', (date,))
        
        symbols = cursor.fetchall()
        
        if not symbols:
            print(f'   ⚠️ 데이터 없음')
            continue
        
        # KAGGRESSIVE 점수 계산
        candidates = []
        for sym, name in symbols:
            try:
                result = scanner.calculate_kagg_score(sym, date)
                if result and result['kagg_score'] >= 70:
                    candidates.append({
                        'date': date,
                        'symbol': sym,
                        'name': result['name'],
                        'score': result['kagg_score'],
                        'entry_price': result['price'],
                        'rsi': result['rsi']
                    })
            except Exception as e:
                continue
        
        print(f'   70점+ 종목: {len(candidates)}개')
        
        if not candidates:
            continue
        
        # 상위 3개만 거래 (자금 한계)
        top3 = sorted(candidates, key=lambda x: x['score'], reverse=True)[:3]
        
        # 수익률 계산 (3거래일 후)
        for stock in top3:
            try:
                entry_date = datetime.strptime(date, '%Y-%m-%d')
                
                # 청산일 찾기 (3거래일 후)
                cursor.execute('''
                    SELECT date FROM stock_prices
                    WHERE symbol = ? AND date > ?
                    ORDER BY date LIMIT 3
                ''', (stock['symbol'], date))
                
                exit_dates = cursor.fetchall()
                if len(exit_dates) < 3:
                    continue
                
                exit_date = exit_dates[-1][0]
                
                # 진입가/청산가
                df_entry = get_price(stock['symbol'], date, date)
                df_exit = get_price(stock['symbol'], exit_date, exit_date)
                
                if df_entry is None or df_exit is None:
                    continue
                if df_entry.empty or df_exit.empty:
                    continue
                
                entry_price = df_entry['Close'].iloc[0]
                exit_price = df_exit['Close'].iloc[0]
                
                return_pct = ((exit_price - entry_price) / entry_price) * 100
                
                trade = {
                    'entry_date': date,
                    'exit_date': exit_date,
                    'symbol': stock['symbol'],
                    'name': stock['name'],
                    'score': stock['score'],
                    'entry': entry_price,
                    'exit': exit_price,
                    'return': return_pct
                }
                
                all_trades.append(trade)
                
                result_emoji = '🟢' if return_pct > 0 else '🔴'
                print(f"   {result_emoji} {stock['name']}: {return_pct:+.2f}% ({stock['score']}점)")
                
            except Exception as e:
                continue
    
    conn.close()
    
    # 결과 출력
    print('\n' + '='*70)
    print('📊 백테스트 결과')
    print('='*70)
    
    if not all_trades:
        print('⚠️ 거래 없음')
        return []
    
    df = pd.DataFrame(all_trades)
    
    print(f'\n총 거래: {len(df)}회')
    print(f'승률: {(df["return"] > 0).mean() * 100:.1f}%')
    print(f'평균 수익률: {df["return"].mean():+.2f}%')
    print(f'누적 수익률: {df["return"].sum():+.2f}%')
    print(f'최대 수익: {df["return"].max():+.2f}%')
    print(f'최대 손실: {df["return"].min():+.2f}%')
    print(f'평균 보유일: 3일')
    
    # 월별 분석
    print('\n📅 월별 결과:')
    df['month'] = df['entry_date'].str[:7]
    monthly = df.groupby('month').agg({
        'return': ['count', 'sum', 'mean']
    }).round(2)
    print(monthly)
    
    # 상세 거래 내역
    print('\n📋 상세 거래 내역:')
    for _, trade in df.iterrows():
        result = '승' if trade['return'] > 0 else '패'
        print(f"{trade['entry_date']} | {trade['name'][:8]:<8} | {trade['score']}점 | "
              f"{trade['return']:+.2f}% | {result}")
    
    return all_trades


if __name__ == '__main__':
    results = run_kagg_backtest()
