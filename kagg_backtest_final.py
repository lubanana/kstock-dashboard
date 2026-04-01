#!/usr/bin/env python3
"""
KAGGRESSIVE 실제 거래 기반 백테스트
사용 가능한 날짜만 테스트
"""

import sys
sys.path.insert(0, '/root/.openclaw/workspace/strg')

import sqlite3
import pandas as pd
from datetime import datetime, timedelta
from fdr_wrapper import get_price
from kagg import KAggressiveScanner


def run_real_backtest():
    """실제 데이터로 백테스트"""
    
    print('='*70)
    print('🔥 KAGGRESSIVE 실제 백테스트 (사용 가능한 날짜)')
    print('='*70)
    
    scanner = KAggressiveScanner()
    conn = sqlite3.connect('data/pivot_strategy.db')
    cursor = conn.cursor()
    
    # 실제 사용 가능한 날짜
    test_dates = [
        '2026-03-05', '2026-03-06', '2026-03-09',
        '2026-03-10', '2026-03-11', '2026-03-12',
        '2026-03-13', '2026-03-16', '2026-03-17',
        '2026-03-18'
    ]
    
    all_trades_70 = []  # 70점+
    all_trades_60 = []  # 60-69점
    
    for date in test_dates:
        print(f'\n📅 {date}')
        
        # 모든 종목 스캔
        cursor.execute('''
            SELECT DISTINCT s.symbol, s.name
            FROM stock_info s
            JOIN stock_prices p ON s.symbol = p.symbol AND p.date = ?
            LIMIT 300
        ''', (date,))
        
        symbols = cursor.fetchall()
        print(f'   대상 종목: {len(symbols)}개')
        
        if not symbols:
            continue
        
        # 점수 계산
        candidates = []
        for sym, name in symbols:
            try:
                result = scanner.calculate_kagg_score(sym, date)
                if result and result['kagg_score'] >= 60:
                    candidates.append({
                        'symbol': sym,
                        'name': result['name'],
                        'score': result['kagg_score'],
                        'price': result['price']
                    })
            except Exception as e:
                continue
        
        # 분류
        tier70 = [c for c in candidates if c['score'] >= 70]
        tier60 = [c for c in candidates if 60 <= c['score'] < 70]
        
        print(f'   70점+: {len(tier70)}개, 60-69점: {len(tier60)}개')
        
        # 70점+ 거래 (상위 3개)
        for stock in sorted(tier70, key=lambda x: x['score'], reverse=True)[:3]:
            ret = calculate_return(cursor, stock['symbol'], date, 3)
            if ret is not None:
                all_trades_70.append({
                    'date': date, **stock, 'return': ret
                })
        
        # 60-69점 거래 (상위 3개)
        for stock in sorted(tier60, key=lambda x: x['score'], reverse=True)[:3]:
            ret = calculate_return(cursor, stock['symbol'], date, 3)
            if ret is not None:
                all_trades_60.append({
                    'date': date, **stock, 'return': ret
                })
    
    conn.close()
    
    # 결과 출력
    print('\n' + '='*70)
    print('📊 백테스트 결과')
    print('='*70)
    
    # 70점+ 결과
    print('\n🔥 70점+ (적극매수 기준):')
    if all_trades_70:
        df70 = pd.DataFrame(all_trades_70)
        print(f'   거래: {len(df70)}회')
        print(f'   승률: {(df70["return"] > 0).mean() * 100:.1f}%')
        print(f'   평균 수익률: {df70["return"].mean():+.2f}%')
        print(f'   누적 수익률: {df70["return"].sum():+.2f}%')
    else:
        print('   거래 없음')
    
    # 60-69점 결과
    print('\n👀 60-69점 (관심 기준):')
    if all_trades_60:
        df60 = pd.DataFrame(all_trades_60)
        print(f'   거래: {len(df60)}회')
        print(f'   승률: {(df60["return"] > 0).mean() * 100:.1f}%')
        print(f'   평균 수익률: {df60["return"].mean():+.2f}%')
        print(f'   누적 수익률: {df60["return"].sum():+.2f}%')
        
        # 상세 거래
        print('\n   상세 거래:')
        for _, t in df60.iterrows():
            emoji = '🟢' if t['return'] > 0 else '🔴'
            print(f"   {emoji} {t['date']} {t['name'][:8]}: {t['return']:+.2f}% ({t['score']}점)")
    else:
        print('   거래 없음')
    
    return all_trades_70, all_trades_60


def calculate_return(cursor, symbol, entry_date, hold_days):
    """수익률 계산"""
    try:
        # 청산일 찾기
        cursor.execute('''
            SELECT date FROM stock_prices
            WHERE symbol = ? AND date > ?
            ORDER BY date LIMIT ?
        ''', (symbol, entry_date, hold_days))
        
        dates = cursor.fetchall()
        if len(dates) < hold_days:
            return None
        
        exit_date = dates[-1][0]
        
        # 가격 조회
        df_entry = get_price(symbol, entry_date, entry_date)
        df_exit = get_price(symbol, exit_date, exit_date)
        
        if df_entry is None or df_exit is None:
            return None
        if df_entry.empty or df_exit.empty:
            return None
        
        entry = df_entry['Close'].iloc[0]
        exit_ = df_exit['Close'].iloc[0]
        
        return ((exit_ - entry) / entry) * 100
        
    except Exception as e:
        return None


if __name__ == '__main__':
    run_real_backtest()
