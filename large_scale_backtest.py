#!/usr/bin/env python3
"""
대규모 백테스트 - 개선된 캔들 패턴 + 더 많은 종목
"""

import sys
sys.path.insert(0, '/root/.openclaw/workspace/strg')

import json
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from fdr_wrapper import get_price
from advanced_candle_detector import scan_with_candles


# 확장 종목 리스트 (KOSPI 대형주 + 중형주)
LARGE_CAP_STOCKS = [
    # 삼성계열
    '005930',  # 삼성전자
    '005935',  # 삼성전자우
    '000660',  # SK하이닉스
    '005380',  # 현대차
    '005385',  # 현대차우
    '005387',  # 현대차2우B
    '051910',  # LG화학
    '051915',  # LG화학우
    '035420',  # NAVER
    '035720',  # 카카오
    '006400',  # 삼성SDI
    '028260',  # 삼성물산
    '032830',  # 삼성생명
    '010140',  # 삼성중공업
    '010145',  # 삼성중공우
    '009150',  # 삼성전기
    '009155',  # 삼성전기우
]

MID_CAP_STOCKS = [
    # 중형주
    '042700',  # 한미반도체
    '055550',  # 신한지주
    '086790',  # 하나금융지주
    '032640',  # LG유플러스
    '033780',  # KT&G
    '012330',  # 현대모비스
    '018260',  # 삼성에스디에스
    '009540',  # 한국조선해양
    '316140',  # 우리금융지주
    '024110',  # 기업은행
    '138930',  # 마이다스에스엘
    '010130',  # 고려아연
    '010950',  # S-Oil
    '010955',  # S-Oil우
    '161890',  # 한국타이어앤테크놀로지
    '271560',  # 오리온
    '267250',  # 현대중공업
]

GROWTH_STOCKS = [
    # 성장주
    '035900',  # JYP Ent.
    '122870',  # YG PLUS
    '263750',  # 펄어비스
    '251270',  # 넷마블
    '194480',  # 데브시스터즈
    '336570',  # 리노공업
    '036830',  # 솔브레인홀딩스
    '357780',  # 솔브레인
    '225570',  # 넥슨게임즈
    '293490',  # 카카오게임즈
    '348210',  # 넥스틴
    '140860',  # 파크시스템스
    '041930',  # 동아에스티
    '033100',  # 제룡전기
    '012210',  # 삼미금속
    '025980',  # 아난티
]

ALL_STOCKS = list(set(LARGE_CAP_STOCKS + MID_CAP_STOCKS + GROWTH_STOCKS))

def simulate_trade(signal):
    """거래 시뮬레이션"""
    try:
        entry = signal['price']
        entry_dt = datetime.strptime(signal['date'], '%Y-%m-%d')
        
        # 더 긴 보유 기간 (5~15일)
        df = get_price(signal['symbol'],
                      (entry_dt + timedelta(days=1)).strftime('%Y-%m-%d'),
                      (entry_dt + timedelta(days=20)).strftime('%Y-%m-%d'))
        
        if df is None or len(df) < 5:
            return None
        
        # 동적 손절/목표
        score = signal['score']
        if score >= 60:
            stop_pct = 0.93  # -7%
            target_pct = 1.18  # +18%
            max_days = 15
        elif score >= 50:
            stop_pct = 0.94  # -6%
            target_pct = 1.15  # +15%
            max_days = 12
        else:
            stop_pct = 0.95  # -5%
            target_pct = 1.12  # +12%
            max_days = 10
        
        stop = entry * stop_pct
        target = entry * target_pct
        
        for idx in range(min(max_days, len(df))):
            row = df.iloc[idx]
            if row['Low'] <= stop:
                return {'return': round((stop - entry) / entry * 100, 2), 'exit': 'stop', 'days': idx+1}
            if row['High'] >= target:
                return {'return': round((target - entry) / entry * 100, 2), 'exit': 'target', 'days': idx+1}
        
        # 보유 만기
        final = df['Close'].iloc[min(max_days-1, len(df)-1)]
        ret = ((final - entry) / entry) * 100
        return {'return': round(ret, 2), 'exit': 'hold', 'days': min(max_days, len(df))}
        
    except Exception as e:
        return None


def run_large_scale_backtest():
    """대규모 백테스트 실행"""
    print("=" * 80)
    print("🔥 대규모 백테스트 - 개선 캔들 패턴")
    print("=" * 80)
    print(f"대상 종목: {len(ALL_STOCKS)}개")
    
    # 테스트 날짜 (12개)
    dates = ['2026-01-13', '2026-01-20', '2026-01-27',
             '2026-02-03', '2026-02-10', '2026-02-17', '2026-02-24', 
             '2026-03-03', '2026-03-10', '2026-03-17', '2026-03-24', '2026-03-31']
    
    print(f"테스트 날짜: {len(dates)}개")
    print(f"총 조합: {len(ALL_STOCKS) * len(dates)}개")
    print("=" * 80)
    
    all_trades = []
    pattern_stats = {}
    
    for symbol in ALL_STOCKS:
        print(f"\n📊 {symbol} 스캐닝...", end=' ')
        symbol_signals = 0
        
        for date in dates:
            signal = scan_with_candles(symbol, date, combo_type='normal')
            if signal:
                symbol_signals += 1
                trade = simulate_trade(signal)
                if trade:
                    trade.update({
                        'symbol': symbol,
                        'date': date,
                        'score': signal['score'],
                        'pattern': signal['pattern'],
                        'pattern_reliability': signal['pattern_reliability'],
                        'retracement': signal['retracement'],
                        'rvol': signal['rvol'],
                        'reasons': signal['reasons']
                    })
                    all_trades.append(trade)
                    
                    # 패턴 통계
                    pat = signal['pattern']
                    if pat not in pattern_stats:
                        pattern_stats[pat] = {'count': 0, 'wins': 0, 'returns': []}
                    pattern_stats[pat]['count'] += 1
                    pattern_stats[pat]['returns'].append(trade['return'])
                    if trade['return'] > 0:
                        pattern_stats[pat]['wins'] += 1
        
        print(f"{symbol_signals}개 신호")
    
    return all_trades, pattern_stats


def analyze_results(trades, pattern_stats):
    """결과 분석"""
    print("\n" + "=" * 80)
    print("📊 백테스트 결과 분석")
    print("=" * 80)
    
    if not trades:
        print("\n⚠️ 유효한 거래가 없습니다.")
        return None
    
    # 기본 통계
    returns = [t['return'] for t in trades]
    wins = [r for r in returns if r > 0]
    
    total = len(trades)
    win_rate = len(wins) / total * 100
    avg_return = np.mean(returns)
    total_return = sum(returns)
    
    gross_profit = sum([r for r in returns if r > 0])
    gross_loss = abs(sum([r for r in returns if r <= 0]))
    pf = gross_profit / gross_loss if gross_loss > 0 else 0
    
    print(f"\n📈 종합 성과")
    print(f"   총 거래: {total}회")
    print(f"   승률: {win_rate:.1f}% ({len(wins)}승 {total - len(wins)}패)")
    print(f"   평균 수익률: {avg_return:+.2f}%")
    print(f"   총 수익률: {total_return:+.2f}%")
    print(f"   Profit Factor: {pf:.2f}")
    
    print(f"\n📊 세부 통계")
    print(f"   평균 수익: {np.mean(wins) if wins else 0:+.2f}%")
    print(f"   평균 손실: {np.mean([r for r in returns if r <= 0]) if len(returns) > len(wins) else 0:.2f}%")
    print(f"   최고 수익: {max(returns):+.2f}%")
    print(f"   최저 손실: {min(returns):.2f}%")
    print(f"   평균 보유일: {np.mean([t['days'] for t in trades]):.1f}일")
    
    # 점수별 분석
    print(f"\n🎯 점수별 성과")
    for threshold in [60, 50, 40]:
        subset = [t for t in trades if t['score'] >= threshold]
        if subset:
            r = [t['return'] for t in subset]
            wr = len([x for x in r if x > 0]) / len(r) * 100
            print(f"   {threshold}점+: {len(subset)}회, 승률 {wr:.1f}%, 평균 {np.mean(r):+.2f}%")
    
    # 패털별 성과
    print(f"\n🕯️ 패털별 성과")
    pattern_analysis = []
    for pat, stats in pattern_stats.items():
        if stats['count'] >= 2:  # 최소 2회 이상
            wr = stats['wins'] / stats['count'] * 100
            avg = np.mean(stats['returns'])
            pattern_analysis.append({
                'pattern': pat,
                'count': stats['count'],
                'win_rate': wr,
                'avg_return': avg
            })
    
    pattern_analysis.sort(key=lambda x: x['win_rate'], reverse=True)
    for p in pattern_analysis[:10]:
        print(f"   {p['pattern']}: {p['count']}회, 승률 {p['win_rate']:.1f}%, 평균 {p['avg_return']:+.2f}%")
    
    # 종목별 성과
    print(f"\n📈 종목별 성과 (TOP 10)")
    symbol_returns = {}
    for t in trades:
        sym = t['symbol']
        if sym not in symbol_returns:
            symbol_returns[sym] = []
        symbol_returns[sym].append(t['return'])
    
    symbol_summary = []
    for sym, rets in symbol_returns.items():
        symbol_summary.append({
            'symbol': sym,
            'trades': len(rets),
            'win_rate': len([r for r in rets if r > 0]) / len(rets) * 100,
            'avg_return': np.mean(rets),
            'total_return': sum(rets)
        })
    
    symbol_summary.sort(key=lambda x: x['avg_return'], reverse=True)
    for s in symbol_summary[:10]:
        print(f"   {s['symbol']}: {s['trades']}회, 승률 {s['win_rate']:.1f}%, 평균 {s['avg_return']:+.2f}%")
    
    # TOP/WORST 거래
    print(f"\n🏆 TOP 10 수익 거래")
    for t in sorted(trades, key=lambda x: x['return'], reverse=True)[:10]:
        print(f"   {t['symbol']} ({t['date'][:10]}): {t['return']:+.2f}% ({t['pattern']}, {t['score']}점)")
    
    print(f"\n⚠️ TOP 10 손실 거래")
    for t in sorted(trades, key=lambda x: x['return'])[:10]:
        print(f"   {t['symbol']} ({t['date'][:10]}): {t['return']:.2f}% ({t['pattern']}, {t['score']}점)")
    
    return {
        'trades': trades,
        'summary': {
            'total': total,
            'win_rate': win_rate,
            'avg_return': avg_return,
            'total_return': total_return,
            'profit_factor': pf
        },
        'pattern_analysis': pattern_analysis,
        'symbol_summary': symbol_summary
    }


if __name__ == '__main__':
    trades, pattern_stats = run_large_scale_backtest()
    results = analyze_results(trades, pattern_stats)
    
    if results:
        with open('docs/large_scale_candle_backtest.json', 'w', encoding='utf-8') as f:
            json.dump(results, f, ensure_ascii=False, indent=2, default=str)
        print("\n✅ 저장: docs/large_scale_candle_backtest.json")
