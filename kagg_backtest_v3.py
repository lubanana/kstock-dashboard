#!/usr/bin/env python3
"""
KAGGRESSIVE 백테스트 v3 - 60점+ 기준
"""

import sys
sys.path.insert(0, '/root/.openclaw/workspace/strg')

import sqlite3
import pandas as pd
from datetime import datetime, timedelta
from fdr_wrapper import get_price
from kagg import KAggressiveScanner


def run_kagg_backtest_v3(threshold=60):
    """KAGGRESSIVE 백테스트 (60점+ 기준)"""
    
    print('='*70)
    print(f'🔥 KAGGRESSIVE 백테스트 ({threshold}점+ / 3일 보유)')
    print('='*70)
    
    scanner = KAggressiveScanner()
    conn = sqlite3.connect('data/pivot_strategy.db')
    cursor = conn.cursor()
    
    # 테스트 기간
    test_dates = [
        '2026-01-02', '2026-01-13', '2026-01-20',
        '2026-02-03', '2026-02-13', '2026-02-20',
        '2026-03-02', '2026-03-13', '2026-03-20',
    ]
    
    all_trades = []
    daily_results = []
    
    for date in test_dates:
        print(f'\n📅 {date} 스캔 중...')
        
        # 종목 가져오기
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
        
        # 점수 계산 (제한된 샘플)
        candidates = []
        for sym, name in symbols[:200]:  # 속도를 위해 200개만
            try:
                result = scanner.calculate_kagg_score(sym, date)
                if result and result['kagg_score'] >= threshold:
                    candidates.append({
                        'date': date,
                        'symbol': sym,
                        'name': result['name'],
                        'score': result['kagg_score'],
                        'entry_price': result['price']
                    })
            except:
                continue
        
        print(f'   {threshold}점+ 종목: {len(candidates)}개')
        
        # 상위 5개 거래
        top5 = sorted(candidates, key=lambda x: x['score'], reverse=True)[:5]
        
        day_returns = []
        for stock in top5:
            try:
                # 3거래일 후 청산
                cursor.execute('''
                    SELECT date FROM stock_prices
                    WHERE symbol = ? AND date > ?
                    ORDER BY date LIMIT 3
                ''', (stock['symbol'], date))
                
                exit_dates = cursor.fetchall()
                if len(exit_dates) < 3:
                    continue
                
                exit_date = exit_dates[-1][0]
                
                # 가격
                df_entry = get_price(stock['symbol'], date, date)
                df_exit = get_price(stock['symbol'], exit_date, exit_date)
                
                if df_entry is None or df_exit is None or df_entry.empty or df_exit.empty:
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
                    'return': return_pct
                }
                
                all_trades.append(trade)
                day_returns.append(return_pct)
                
            except:
                continue
        
        if day_returns:
            avg_day = sum(day_returns) / len(day_returns)
            print(f'   평균 수익률: {avg_day:+.2f}%')
            daily_results.append({'date': date, 'return': avg_day, 'count': len(day_returns)})
    
    conn.close()
    
    # 결과
    print('\n' + '='*70)
    print('📊 백테스트 결과')
    print('='*70)
    
    if not all_trades:
        print('⚠️ 거래 없음')
        return
    
    df = pd.DataFrame(all_trades)
    win_rate = (df['return'] > 0).mean() * 100
    avg_return = df['return'].mean()
    total_return = df['return'].sum()
    
    print(f'\n총 거래: {len(df)}회')
    print(f'승률: {win_rate:.1f}%')
    print(f'평균 수익률: {avg_return:+.2f}%')
    print(f'누적 수익률: {total_return:+.2f}%')
    print(f'최대 수익: {df["return"].max():+.2f}%')
    print(f'최대 손실: {df["return"].min():+.2f}%')
    
    # 점수별 분석
    print('\n📈 점수별 성과:')
    df70 = df[df['score'] >= 70]
    df60 = df[(df['score'] >= 60) & (df['score'] < 70)]
    
    if len(df70) > 0:
        print(f'   70점+ (n={len(df70)}): 승률 {(df70["return"] > 0).mean()*100:.1f}%, 평균 {df70["return"].mean():+.2f}%')
    else:
        print(f'   70점+: 데이터 없음')
    
    if len(df60) > 0:
        print(f'   60-69점 (n={len(df60)}): 승률 {(df60["return"] > 0).mean()*100:.1f}%, 평균 {df60["return"].mean():+.2f}%')
    
    # 상위 수익 종목
    print('\n🏆 상위 수익 종목:')
    top_profit = df.nlargest(5, 'return')
    for _, t in top_profit.iterrows():
        print(f"   {t['entry_date']} {t['name'][:8]}: {t['return']:+.2f}% ({t['score']}점)")
    
    # 하위 종목
    print('\n🔻 하위 종목:')
    bottom = df.nsmallest(3, 'return')
    for _, t in bottom.iterrows():
        print(f"   {t['entry_date']} {t['name'][:8]}: {t['return']:+.2f}% ({t['score']}점)")


if __name__ == '__main__':
    run_kagg_backtest_v3(threshold=60)
