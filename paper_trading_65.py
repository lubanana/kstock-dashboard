#!/usr/bin/env python3
"""
KAGGRESSIVE Paper Trading - 65점 기준 1주일 시뮬레이션
"""

import sys
sys.path.insert(0, '/root/.openclaw/workspace/strg')

import sqlite3
import pandas as pd
from datetime import datetime, timedelta
from fdr_wrapper import get_price
from risk_calculator import RiskCalculator
import json


def run_paper_trading_65():
    """65점 기준 페이퍼트레이딩"""
    
    print('='*70)
    print('📊 KAGGRESSIVE 페이퍼트레이딩 (65점+ / 1주일)')
    print('='*70)
    
    # 설정
    ENTRY_DATE = '2026-03-03'  # 진입일 (3월 첫 거래일)
    HOLD_DAYS = 7              # 보유일
    THRESHOLD = 65             # 진입 기준점수
    
    exit_date = '2026-03-12'   # 7거래일 후
    
    print(f'\n📅 진입일: {ENTRY_DATE}')
    print(f'📅 청산일: {exit_date} (7거래일 후)')
    print(f'🎯 진입 기준: {THRESHOLD}점+')
    print('-'*70)
    
    # 선정 종목 (65점+ from latest scan)
    selected_stocks = [
        {'symbol': '033100', 'name': '제룡전기', 'score': 65.0, 'source': 'KAGGRESSIVE'},
        {'symbol': '140860', 'name': '파크시스템스', 'score': 65.0, 'source': 'KAGGRESSIVE'},
        {'symbol': '348210', 'name': '넥스틴', 'score': 65.0, 'source': 'KAGGRESSIVE'},
        {'symbol': '006730', 'name': '서부T&D', 'score': 65.0, 'source': '단기급등'},
        {'symbol': '009620', 'name': '삼보산업', 'score': 65.0, 'source': '단기급등'},
        {'symbol': '012210', 'name': '삼미금속', 'score': 65.0, 'source': '단기급등'},
        {'symbol': '025980', 'name': '아난티', 'score': 65.0, 'source': '단기급등'},
        {'symbol': '042700', 'name': '한미반도체', 'score': 65.0, 'source': '단기급등'},
    ]
    
    conn = sqlite3.connect('data/pivot_strategy.db')
    cursor = conn.cursor()
    
    trades = []
    
    print('\n🔍 거래 시뮬레이션 중...\n')
    
    for stock in selected_stocks:
        symbol = stock['symbol']
        name = stock['name']
        score = stock['score']
        
        try:
            # 진입가 (ENTRY_DATE 시가)
            df_entry = get_price(symbol, ENTRY_DATE, ENTRY_DATE)
            if df_entry is None or df_entry.empty:
                print(f'   ⚠️ {name}: 진입 데이터 없음')
                continue
            
            entry_price = df_entry['Close'].iloc[0]
            
            # 7거래일 후 청산일 찾기
            cursor.execute('''
                SELECT date FROM stock_prices
                WHERE symbol = ? AND date > ?
                ORDER BY date LIMIT 7
            ''', (symbol, ENTRY_DATE))
            
            exit_dates = cursor.fetchall()
            if len(exit_dates) < 7:
                print(f'   ⚠️ {name}: 청산일 데이터 부족')
                continue
            
            actual_exit_date = exit_dates[-1][0]
            
            # 청산가
            df_exit = get_price(symbol, actual_exit_date, actual_exit_date)
            if df_exit is None or df_exit.empty:
                print(f'   ⚠️ {name}: 청산 데이터 없음')
                continue
            
            exit_price = df_exit['Close'].iloc[0]
            
            # 수익률 계산
            return_pct = ((exit_price - entry_price) / entry_price) * 100
            
            # 리스크 관리 (손절가 확인)
            risk_plan = RiskCalculator.get_trading_plan(symbol, name, score)
            stop_loss = risk_plan['stop_loss'] if risk_plan else entry_price * 0.93
            
            # 최저가 확인 (손절 여부)
            df_period = get_price(symbol, ENTRY_DATE, actual_exit_date)
            if df_period is not None and not df_period.empty:
                lowest_price = df_period['Low'].min()
                hit_stop_loss = lowest_price <= stop_loss
                
                # 손절가 도달 시 손절가로 청산 가정
                if hit_stop_loss:
                    actual_return = ((stop_loss - entry_price) / entry_price) * 100
                    exit_type = '손절'
                else:
                    actual_return = return_pct
                    exit_type = '보유만기'
            else:
                actual_return = return_pct
                exit_type = '보유만기'
            
            trade = {
                'symbol': symbol,
                'name': name,
                'score': score,
                'entry_date': ENTRY_DATE,
                'exit_date': actual_exit_date,
                'entry_price': entry_price,
                'exit_price': exit_price,
                'stop_loss': stop_loss,
                'return_pct': actual_return,
                'exit_type': exit_type,
                'source': stock['source']
            }
            
            trades.append(trade)
            
            emoji = '🟢' if actual_return > 0 else '🔴'
            print(f"   {emoji} {name}: {actual_return:+.2f}% ({exit_type})")
            
        except Exception as e:
            print(f'   ❌ {name}: 오류 - {e}')
            continue
    
    conn.close()
    
    # 결과 분석
    print('\n' + '='*70)
    print('📊 페이퍼트레이딩 결과')
    print('='*70)
    
    if not trades:
        print('⚠️ 거래 없음')
        return
    
    df = pd.DataFrame(trades)
    
    # 통계
    total_trades = len(df)
    winning_trades = len(df[df['return_pct'] > 0])
    losing_trades = len(df[df['return_pct'] <= 0])
    win_rate = (winning_trades / total_trades) * 100
    avg_return = df['return_pct'].mean()
    total_return = df['return_pct'].sum()
    
    print(f'\n📈 종합 통계')
    print(f'   총 거래: {total_trades}회')
    print(f'   승률: {win_rate:.1f}% ({winning_trades}승 / {losing_trades}패)')
    print(f'   평균 수익률: {avg_return:+.2f}%')
    print(f'   총 수익률 (합계): {total_return:+.2f}%')
    print(f'   최고 수익: {df["return_pct"].max():+.2f}%')
    print(f'   최대 손실: {df["return_pct"].min():+.2f}%')
    
    # 출처별 분석
    print('\n📊 출처별 성과:')
    for source in df['source'].unique():
        source_df = df[df['source'] == source]
        print(f"   {source}: {len(source_df)}종목, 평균 {source_df['return_pct'].mean():+.2f}%")
    
    # 종목별 상세
    print('\n📋 종목별 상세 결과:')
    print('-'*70)
    print(f'{"종목":<12} {"진입가":>10} {"청산가":>10} {"수익률":>8} {"유형":<6}')
    print('-'*70)
    
    for _, t in df.iterrows():
        print(f"{t['name']:<12} {t['entry_price']:>10,.0f} {t['exit_price']:>10,.0f} {t['return_pct']:>+7.2f}% {t['exit_type']:<6}")
    
    # 리포트 저장
    report = {
        'type': 'paper_trading',
        'threshold': THRESHOLD,
        'entry_date': ENTRY_DATE,
        'hold_days': HOLD_DAYS,
        'summary': {
            'total_trades': total_trades,
            'win_rate': win_rate,
            'avg_return': avg_return,
            'total_return': total_return
        },
        'trades': trades
    }
    
    with open('docs/paper_trading_65_20260325.json', 'w', encoding='utf-8') as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    
    print('\n✅ 리포트 저장: docs/paper_trading_65_20260325.json')
    
    return df


if __name__ == '__main__':
    run_paper_trading_65()
