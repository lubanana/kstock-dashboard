#!/usr/bin/env python3
"""
KAGGRESSIVE 간편 백테스트 - run_integrated_scan 사용
"""

import sys
sys.path.insert(0, '/root/.openclaw/workspace/strg')

import sqlite3
import pandas as pd
from datetime import datetime
from kagg import KAggressiveScanner


def simple_backtest():
    """간편 백테스트"""
    
    print('='*70)
    print('🔥 KAGGRESSIVE 백테스트 (run_integrated_scan 기반)')
    print('='*70)
    
    scanner = KAggressiveScanner()
    
    # 테스트 날짜들
    test_dates = [
        '2026-03-13', '2026-03-16', '2026-03-17',
        '2026-03-18', '2026-03-19', '2026-03-20'
    ]
    
    results_70 = []
    results_60 = []
    
    for date in test_dates:
        print(f'\n📅 {date} 스캔 중...')
        
        # run_integrated_scan 사용
        try:
            # 데이터 필터링을 위해 날짜 기준 종목 가져오기
            conn = sqlite3.connect('data/pivot_strategy.db')
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT DISTINCT s.symbol
                FROM stock_info s
                JOIN stock_prices p ON s.symbol = p.symbol AND p.date = ?
                LIMIT 500
            ''', (date,))
            
            symbols = [r[0] for r in cursor.fetchall()]
            conn.close()
            
            print(f'   대상: {len(symbols)}종목')
            
            # 각 종목 점수 계산 (샘플)
            scored = []
            for sym in symbols[:100]:  # 100개만
                try:
                    # 직접 점수 계산
                    result = scanner.calculate_kagg_score_for_backtest(sym, date)
                    if result and result['kagg_score'] >= 60:
                        scored.append(result)
                except:
                    continue
            
            tier70 = [s for s in scored if s['kagg_score'] >= 70]
            tier60 = [s for s in scored if 60 <= s['kagg_score'] < 70]
            
            print(f'   70점+: {len(tier70)}개, 60-69점: {len(tier60)}개')
            
            # 결과 저장 (가상 수익률 - 실제로는 3일 후 계산)
            for s in tier70[:3]:
                results_70.append({'date': date, **s, 'return': 0})
            for s in tier60[:3]:
                results_60.append({'date': date, **s, 'return': 0})
                
        except Exception as e:
            print(f'   오류: {e}')
    
    print('\n' + '='*70)
    print('📊 백테스트 결과 (선별 통계)')
    print('='*70)
    print(f'\n70점+ 발견: {len(results_70)}회')
    print(f'60-69점 발견: {len(results_60)}회')
    
    if results_70:
        print('\n🔥 70점+ 종목:')
        for r in results_70:
            print(f"   {r['date']} {r['name']} ({r['symbol']}): {r['kagg_score']}점")
    
    if results_60:
        print('\n👀 60-69점 종목:')
        for r in results_60:
            print(f"   {r['date']} {r['name']} ({r['symbol']}): {r['kagg_score']}점")


if __name__ == '__main__':
    simple_backtest()
