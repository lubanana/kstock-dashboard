#!/usr/bin/env python3
"""
한국 주식 승률 향상 전략 연구
현재: RSI(6) < 25 + 거래량 1.5배 + 5일 수익률 < -5% = 54.2% 승률
목표: 65%+ 승률 달성
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import json
import warnings
warnings.filterwarnings('ignore')

import sys
sys.path.insert(0, '/root/.openclaw/workspace/strg')
from fdr_wrapper import get_price

def calculate_rsi(prices, period=14):
    delta = prices.diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
    rs = gain / loss
    return 100 - (100 / (1 + rs))

def backtest_strategy(df, strategy_params, ticker, name):
    """백테스트 실행"""
    if df is None or len(df) < 50:
        return []
    
    fee_rate = 0.00015
    
    # 지표 계산
    df['RSI'] = calculate_rsi(df['Close'], strategy_params.get('rsi_period', 6))
    df['Volume_MA'] = df['Volume'].rolling(window=20).mean()
    df['Volume_Ratio'] = df['Volume'] / df['Volume_MA']
    df['Return_5d'] = df['Close'].pct_change(5) * 100
    
    # 이동평균 (추가 필터용)
    df['EMA20'] = df['Close'].ewm(span=20, adjust=False).mean()
    df['EMA60'] = df['Close'].ewm(span=60, adjust=False).mean()
    
    # 볼린저밴드 (추가 필터용)
    df['BB_Middle'] = df['Close'].rolling(window=20).mean()
    df['BB_Std'] = df['Close'].rolling(window=20).std()
    df['BB_Lower'] = df['BB_Middle'] - (df['BB_Std'] * 2)
    df['BB_Position'] = (df['Close'] - df['BB_Lower']) / (df['BB_Upper'] - df['BB_Lower']) if 'BB_Upper' in df else 0
    df['BB_Upper'] = df['BB_Middle'] + (df['BB_Std'] * 2)
    df['BB_Position'] = (df['Close'] - df['BB_Lower']) / (df['BB_Upper'] - df['BB_Lower'])
    
    # ATR (변동성 필터용)
    df['TR'] = np.maximum(df['High'] - df['Low'], 
                          np.maximum(abs(df['High'] - df['Close'].shift(1)),
                                    abs(df['Low'] - df['Close'].shift(1))))
    df['ATR'] = df['TR'].rolling(window=14).mean()
    df['ATR_Ratio'] = df['ATR'] / df['Close'] * 100
    
    # 매수 신호 조합
    conditions = []
    
    # 기본 RSI 조건
    rsi_condition = df['RSI'] < strategy_params.get('rsi_threshold', 25)
    conditions.append(rsi_condition)
    
    # 거래량 조건
    if strategy_params.get('use_volume', True):
        vol_condition = df['Volume_Ratio'] >= strategy_params.get('volume_threshold', 1.5)
        conditions.append(vol_condition)
    
    # 5일 수익률 조건
    if strategy_params.get('use_return_5d', True):
        ret_condition = df['Return_5d'] < strategy_params.get('return_5d_threshold', -5)
        conditions.append(ret_condition)
    
    # 추가 필터들
    if strategy_params.get('use_trend_filter', False):
        # 추세 필터: EMA20 > EMA60 (상승 추세에서만)
        trend_condition = df['EMA20'] > df['EMA60']
        conditions.append(trend_condition)
    
    if strategy_params.get('use_bb_filter', False):
        # BB 필터: BB 하단 근접
        bb_condition = df['Close'] <= df['BB_Lower'] * 1.02
        conditions.append(bb_condition)
    
    if strategy_params.get('use_atr_filter', False):
        # 변동성 필터: ATR 비율이 너무 높지 않은 경우
        atr_condition = df['ATR_Ratio'] < strategy_params.get('atr_threshold', 5)
        conditions.append(atr_condition)
    
    if strategy_params.get('use_candle_filter', False):
        # 캔들 패턴: 양봉 또는 도지
        candle_condition = df['Close'] >= df['Open']
        conditions.append(candle_condition)
    
    if strategy_params.get('use_volume_trend', False):
        # 거래량 추세: 3일 연속 증가
        vol_trend = (df['Volume'] > df['Volume'].shift(1)) & (df['Volume'].shift(1) > df['Volume'].shift(2))
        conditions.append(vol_trend)
    
    # 모든 조건 결합
    df['Signal'] = conditions[0]
    for cond in conditions[1:]:
        df['Signal'] = df['Signal'] & cond
    
    trades = []
    position = None
    entry_price = entry_date = None
    
    sl_rate = strategy_params.get('sl_rate', 0.02)
    tp_rate = strategy_params.get('tp_rate', 0.03)
    max_hold_days = strategy_params.get('max_hold_days', 2)
    
    for i in range(30, len(df)):
        date = df.index[i]
        row = df.iloc[i]
        
        # 매수
        if position is None and row['Signal']:
            position = 'LONG'
            entry_price = row['Close']
            entry_date = date
            entry_rsi = row['RSI']
        
        # 매도
        elif position == 'LONG':
            current_price = row['Close']
            holding_days = (pd.to_datetime(date) - pd.to_datetime(entry_date)).days
            pnl_rate = (current_price - entry_price) / entry_price
            
            exit_reason = None
            if pnl_rate <= -sl_rate:
                exit_reason = 'STOP_LOSS'
            elif pnl_rate >= tp_rate:
                exit_reason = 'TAKE_PROFIT'
            elif holding_days >= max_hold_days:
                exit_reason = 'TIME_EXIT'
            
            if exit_reason:
                net_pnl_rate = (pnl_rate - fee_rate * 2) * 100
                trades.append({
                    'symbol': ticker,
                    'name': name,
                    'entry_date': str(entry_date)[:10],
                    'exit_date': str(date)[:10],
                    'entry_rsi': round(entry_rsi, 1),
                    'net_pnl_rate': round(net_pnl_rate, 2),
                    'result': 'WIN' if net_pnl_rate > 0 else 'LOSS',
                    'exit_reason': exit_reason
                })
                position = None
    
    return trades


def test_strategy_variant(name, params, stocks):
    """전략 변형 테스트"""
    print(f"\n{'='*70}")
    print(f"📊 테스트: {name}")
    print(f"   파라미터: {params}")
    print(f"{'='*70}")
    
    all_trades = []
    
    for i, (code, stock_name) in enumerate(stocks, 1):
        print(f"[{i:2d}/{len(stocks)}] {code} ({stock_name})", end=' ')
        
        try:
            df = get_price(code, '2024-01-01', '2025-03-30')
            trades = backtest_strategy(df, params, code, stock_name)
            
            if trades:
                all_trades.extend(trades)
                wins = sum(1 for t in trades if t['result'] == 'WIN')
                print(f"→ {len(trades)}거래 (승: {wins}, {wins/len(trades)*100:.0f}%)")
            else:
                print("→ 신호 없음")
        except Exception as e:
            print(f"→ 오류: {str(e)[:20]}")
    
    # 결과 계산
    if all_trades:
        wins = sum(1 for t in all_trades if t['result'] == 'WIN')
        win_rate = wins / len(all_trades) * 100
        avg_pnl = np.mean([t['net_pnl_rate'] for t in all_trades])
        total_return = ((1 + np.array([t['net_pnl_rate'] for t in all_trades])/100).prod() - 1) * 100
        
        print(f"\n✅ 결과: {len(all_trades)}거래, 승률 {win_rate:.1f}%, 평균 {avg_pnl:.2f}%, 총수익 {total_return:.2f}%")
        
        return {
            'name': name,
            'params': params,
            'trades': len(all_trades),
            'win_rate': win_rate,
            'avg_pnl': avg_pnl,
            'total_return': total_return
        }
    else:
        print("\n⚠️ 거래 없음")
        return None


def main():
    stocks = [
        ('005930', '삼성전자'), ('000660', 'SK하이닉스'), ('005380', '현대차'),
        ('035420', 'NAVER'), ('035720', '카카오'), ('051910', 'LG화학'),
        ('006400', '삼성SDI'), ('028260', '삼성물산'), ('068270', '셀트리온'),
        ('207940', '삼성바이오'), ('012330', '현대모비스'), ('005490', 'POSCO'),
        ('105560', 'KB금융'), ('055550', '신한지주'), ('032830', '삼성생명'),
        ('009150', '삼성전기'), ('003670', '포스코퓨처엤'), ('086790', '하나금융'),
        ('033780', 'KT&G'), ('000270', '기아'),
    ]
    
    print("="*70)
    print("🔬 한국 주식 승률 향상 전략 연구")
    print("   기준: RSI(6)+Volume (54.2% 승률)")
    print("   목표: 65%+ 승률")
    print("="*70)
    
    results = []
    
    # 테스트 1: 기준 (현재 전략)
    results.append(test_strategy_variant(
        "기준: RSI(6)+Volume+5일수익률",
        {'rsi_period': 6, 'rsi_threshold': 25, 'volume_threshold': 1.5, 'use_return_5d': True, 'return_5d_threshold': -5},
        stocks
    ))
    
    # 테스트 2: RSI 기간 변경 (더 단기)
    results.append(test_strategy_variant(
        "개선1: RSI(4) 단기화",
        {'rsi_period': 4, 'rsi_threshold': 20, 'volume_threshold': 1.5, 'use_return_5d': True, 'return_5d_threshold': -5},
        stocks
    ))
    
    # 테스트 3: RSI 임계값 하향
    results.append(test_strategy_variant(
        "개선2: RSI(6) < 20 (더 과매도)",
        {'rsi_period': 6, 'rsi_threshold': 20, 'volume_threshold': 1.5, 'use_return_5d': True, 'return_5d_threshold': -5},
        stocks
    ))
    
    # 테스트 4: 양봉 필터 추가
    results.append(test_strategy_variant(
        "개선3: 양봉 필터 추가",
        {'rsi_period': 6, 'rsi_threshold': 25, 'volume_threshold': 1.5, 'use_return_5d': True, 
         'return_5d_threshold': -5, 'use_candle_filter': True},
        stocks
    ))
    
    # 테스트 5: 변동성 필터 추가
    results.append(test_strategy_variant(
        "개선4: ATR 필터 (변동성 제한)",
        {'rsi_period': 6, 'rsi_threshold': 25, 'volume_threshold': 1.5, 'use_return_5d': True,
         'return_5d_threshold': -5, 'use_atr_filter': True, 'atr_threshold': 4},
        stocks
    ))
    
    # 테스트 6: 볼린저밴드 필터 추가
    results.append(test_strategy_variant(
        "개선5: BB 하단 터치 필터",
        {'rsi_period': 6, 'rsi_threshold': 30, 'volume_threshold': 1.5, 'use_return_5d': True,
         'return_5d_threshold': -5, 'use_bb_filter': True},
        stocks
    ))
    
    # 테스트 7: 거래량 추세 필터
    results.append(test_strategy_variant(
        "개선6: 거래량 3일 연속 증가",
        {'rsi_period': 6, 'rsi_threshold': 25, 'volume_threshold': 1.3, 'use_return_5d': True,
         'return_5d_threshold': -5, 'use_volume_trend': True},
        stocks
    ))
    
    # 테스트 8: 복합 (RSI 20 + 양봉 + ATR)
    results.append(test_strategy_variant(
        "개선7: 복합 (RSI<20 + 양봉 + ATR<4)",
        {'rsi_period': 6, 'rsi_threshold': 20, 'volume_threshold': 1.5, 'use_return_5d': True,
         'return_5d_threshold': -5, 'use_candle_filter': True, 'use_atr_filter': True, 'atr_threshold': 4},
        stocks
    ))
    
    # 테스트 9: 손절/익절 조정
    results.append(test_strategy_variant(
        "개선8: R:R 1:2 (-2%/+4%)",
        {'rsi_period': 6, 'rsi_threshold': 25, 'volume_threshold': 1.5, 'use_return_5d': True,
         'return_5d_threshold': -5, 'sl_rate': 0.02, 'tp_rate': 0.04},
        stocks
    ))
    
    # 테스트 10: 보유기간 연장
    results.append(test_strategy_variant(
        "개선9: 보유 3일로 연장",
        {'rsi_period': 6, 'rsi_threshold': 25, 'volume_threshold': 1.5, 'use_return_5d': True,
         'return_5d_threshold': -5, 'max_hold_days': 3},
        stocks
    ))
    
    # 종합 결과
    print("\n" + "="*70)
    print("📊 전략 비교 종합")
    print("="*70)
    
    valid_results = [r for r in results if r is not None]
    
    if valid_results:
        print(f"\n{'전략':<30} {'거래수':<8} {'승률':<10} {'총수익률':<12}")
        print("-"*70)
        
        for r in sorted(valid_results, key=lambda x: x['win_rate'], reverse=True):
            print(f"{r['name']:<30} {r['trades']:<8} {r['win_rate']:.1f}%      {r['total_return']:+.2f}%")
        
        # 최고 성과 전략
        best = max(valid_results, key=lambda x: x['win_rate'])
        print(f"\n🏆 최고 승률 전략: {best['name']}")
        print(f"   승률: {best['win_rate']:.1f}% | 총수익률: {best['total_return']:.2f}%")
        print(f"   파라미터: {best['params']}")
    
    # 저장
    output = f'/root/.openclaw/workspace/strg/docs/korea_winrate_improvement_{datetime.now().strftime("%Y%m%d")}.json'
    with open(output, 'w', encoding='utf-8') as f:
        json.dump([r for r in results if r], f, ensure_ascii=False, indent=2)
    
    print(f"\n📄 저장: {output}")


if __name__ == '__main__':
    main()
