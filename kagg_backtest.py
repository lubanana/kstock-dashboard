#!/usr/bin/env python3
"""
KAGGRESSIVE 백테스트 (현재 전략 기준)
- 70점+만 적극매수
- 60-69점은 관심 (백테스트 대상 제외 또는 별도 분석)
"""

import sys
sys.path.insert(0, '/root/.openclaw/workspace/strg')

import sqlite3
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from fdr_wrapper import get_price
from kagg import KAggressiveScanner


def backtest_kagg_strategy(start_date='2025-01-01', end_date='2026-04-01'):
    """KAGGRESSIVE 전략 백테스트"""
    
    print('='*70)
    print('🔥 KAGGRESSIVE 백테스트')
    print(f'   기간: {start_date} ~ {end_date}')
    print('='*70)
    
    # 매달 마지막 거래일 기준으로 스캔
    test_dates = pd.date_range(start=start_date, end=end_date, freq='M')
    
    results = []
    
    for test_date in test_dates:
        date_str = test_date.strftime('%Y-%m-%d')
        print(f'\n📅 {date_str} 스캔 중...')
        
        # 해당 날짜 기준으로 스캔
        scanner = KAggressiveScanner()
        
        # DB에서 종목 가져오기
        conn = sqlite3.connect('data/pivot_strategy.db')
        symbols = [r[0] for r in conn.execute('SELECT symbol FROM stock_info').fetchall()]
        conn.close()
        
        # 간단한 스캔 (최소 점수 60)
        scan_results = []
        for symbol in symbols[:100]:  # 샘플링
            try:
                result = scanner.calculate_kagg_score(symbol, date_str)
                if result and result['kagg_score'] >= 60:
                    scan_results.append({
                        'date': date_str,
                        'symbol': symbol,
                        'name': result['name'],
                        'score': result['kagg_score'],
                        'price': result['price'],
                        'rsi': result['rsi']
                    })
            except:
                continue
        
        # 70점+ 종목 선별
        tier1 = [r for r in scan_results if r['score'] >= 70]
        tier2 = [r for r in scan_results if 60 <= r['score'] < 70]
        
        print(f'   70점+: {len(tier1)}개, 60-69점: {len(tier2)}개')
        
        # 수익률 계산 (3일 후)
        for stock in tier1:
            try:
                entry_date = datetime.strptime(stock['date'], '%Y-%m-%d')
                exit_date = entry_date + timedelta(days=3)
                
                df = get_price(stock['symbol'], stock['date'], exit_date.strftime('%Y-%m-%d'))
                if df is not None and len(df) >= 2:
                    entry_price = df['Close'].iloc[0]
                    exit_price = df['Close'].iloc[-1]
                    return_pct = ((exit_price - entry_price) / entry_price) * 100
                    
                    stock['return_3d'] = return_pct
                    stock['exit_price'] = exit_price
                    results.append(stock)
            except:
                continue
    
    return pd.DataFrame(results)


def quick_backtest_sample():
    """빠른 샘플 백테스트 (최근 3개월)"""
    
    print('='*70)
    print('🔥 KAGGRESSIVE 샘플 백테스트')
    print('='*70)
    
    scanner = KAggressiveScanner()
    conn = sqlite3.connect('data/pivot_strategy.db')
    
    # 최근 거래일 확인
    cursor = conn.cursor()
    cursor.execute('SELECT MAX(date) FROM stock_prices')
    latest_date = cursor.fetchone()[0]
    print(f'\n📅 기준일: {latest_date}')
    
    # 70점+ 백테스트용 과거 데이터
    test_periods = [
        ('2026-01-02', '2026-01-07', '1월'),
        ('2026-02-03', '2026-02-06', '2월'),
        ('2026-03-02', '2026-03-05', '3월'),
    ]
    
    all_results = []
    
    for start, end, month in test_periods:
        print(f'\n📊 {month} 테스트 ({start} ~ {end}):')
        
        # 해당 기간의 고득점 종목 찾기
        cursor.execute('''
            SELECT DISTINCT s.symbol, s.name
            FROM stock_info s
            JOIN stock_prices p ON s.symbol = p.symbol
            WHERE p.date = ?
            LIMIT 50
        ''', (start,))
        
        symbols = cursor.fetchall()
        
        results = []
        for sym, name in symbols:
            try:
                # 진입가
                df_entry = get_price(sym, start, start)
                if df_entry is None or df_entry.empty:
                    continue
                entry_price = df_entry['Close'].iloc[0]
                
                # 청산가 (3거래일 후)
                df_exit = get_price(sym, end, end)
                if df_exit is None or df_exit.empty:
                    continue
                exit_price = df_exit['Close'].iloc[0]
                
                return_pct = ((exit_price - entry_price) / entry_price) * 100
                
                results.append({
                    'month': month,
                    'symbol': sym,
                    'name': name,
                    'entry': entry_price,
                    'exit': exit_price,
                    'return': return_pct
                })
            except:
                continue
        
        if results:
            df = pd.DataFrame(results)
            avg_return = df['return'].mean()
            win_rate = (df['return'] > 0).mean() * 100
            
            print(f'   테스트 종목: {len(df)}개')
            print(f'   평균 수익률: {avg_return:+.2f}%')
            print(f'   승률: {win_rate:.1f}%')
            
            all_results.extend(results)
    
    conn.close()
    
    # 종합 결과
    if all_results:
        print('\n' + '='*70)
        print('📊 종합 결과')
        print('='*70)
        
        total_df = pd.DataFrame(all_results)
        print(f'총 거래: {len(total_df)}회')
        print(f'평균 수익률: {total_df["return"].mean():+.2f}%')
        print(f'승률: {(total_df["return"] > 0).mean() * 100:.1f}%')
        print(f'최대 수익: {total_df["return"].max():+.2f}%')
        print(f'최대 손실: {total_df["return"].min():+.2f}%')
    
    return all_results


if __name__ == '__main__':
    results = quick_backtest_sample()
