#!/usr/bin/env python3
"""
MODERATE 모드 백테스트
조건: 고신뢰도 패턴 (Morning Star, Engulfing, Pinbar), 45점+
"""

import sys
sys.path.insert(0, '/root/.openclaw/workspace/strg')

import json
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from fdr_wrapper import get_price
from advanced_candle_detector import AdvancedCandleDetector


ALL_STOCKS = [
    '005930', '005935', '000660', '005380', '005385', '005387',
    '051910', '051915', '035420', '035720', '006400', '028260',
    '032830', '010140', '010145', '009150', '009155',
    '055550', '086790', '316140', '024110', '138930',
    '032640', '033780', '012330', '018260', '009540', '010130',
    '010950', '010955', '161890', '271560', '267250',
    '042700', '348210', '140860', '357780', '036830', '336570',
    '035900', '122870', '263750', '251270', '194480', '225570', '293490',
    '041930', '033100', '012210', '025980',
]


def scan_moderate_mode(symbol: str, date: str) -> dict:
    """
    MODERATE 모드 스캔
    조건:
    1. 고신뢰도 패턴 (Morning Star, Engulfing, Bullish Pinbar)
    2. 최소 45점
    3. 피볼나치 25~75%
    4. 거래량 1.0x+
    """
    try:
        end_dt = datetime.strptime(date, '%Y-%m-%d')
        start_dt = end_dt - timedelta(days=90)
        
        df = get_price(symbol, start_dt.strftime('%Y-%m-%d'), date)
        if df is None or len(df) < 30:
            return None
        
        detector = AdvancedCandleDetector(df)
        closes = detector.closes
        highs = detector.highs
        lows = detector.lows
        volumes = detector.volumes
        current_price = closes[-1]
        
        # 1. 피볼나치 확인 (25~75% - 확장)
        recent_high = np.max(highs[-20:])
        recent_low = np.min(lows[-20:])
        if recent_high <= recent_low:
            return None
        
        retracement = ((recent_high - current_price) / (recent_high - recent_low)) * 100
        if not (25 <= retracement <= 75):
            return None
        
        # 2. 거래량 확인 (1.0x+)
        avg_vol = np.mean(volumes[-20:])
        rvol = volumes[-1] / avg_vol if avg_vol > 0 else 0
        if rvol < 1.0:
            return None
        
        # 3. MODERATE 패턴 확인
        all_patterns = detector.detect_all_patterns(min_reliability=3)
        
        # 허용 패턴 (신뢰도 순)
        allowed_patterns = ['morning_star', 'bullish_engulfing', 'bullish_pinbar', 'hammer']
        
        valid_pattern = None
        for p in all_patterns:
            if p['pattern'] in allowed_patterns:
                valid_pattern = p
                break
        
        if not valid_pattern:
            return None
        
        # 4. 점수 계산
        score = 0
        reasons = []
        
        # 피볼나치 점수 (25~75%)
        if 38.2 <= retracement <= 61.8:
            score += 20
        else:
            score += 15
        reasons.append(f'Fib_{retracement:.0f}')
        
        # 거래량 점수
        if rvol >= 2.0:
            score += 15
        elif rvol >= 1.5:
            score += 10
        elif rvol >= 1.0:
            score += 5
        reasons.append(f'RVol_{rvol:.1f}')
        
        # 패턴 점수
        pat_name = valid_pattern['pattern']
        pat_rel = valid_pattern['reliability']
        
        if pat_name == 'morning_star':
            score += 25
        elif pat_name == 'bullish_engulfing':
            score += 20
        elif pat_name == 'bullish_pinbar':
            score += 15
        else:  # hammer
            score += 12
        reasons.append(pat_name.upper())
        
        # 추가 점수: 신뢰도 5점+
        if pat_rel >= 5:
            score += 5
            reasons.append('High_Reliability')
        
        # 추세 점수
        ma5 = np.mean(closes[-5:])
        ma20 = np.mean(closes[-20:])
        if current_price > ma5 > ma20:
            score += 10
            reasons.append('Bullish_Trend')
        elif current_price > ma20:
            score += 5
            reasons.append('Above_MA20')
        
        # 최소 45점 확인
        if score < 45:
            return None
        
        return {
            'symbol': symbol,
            'date': date,
            'score': score,
            'price': round(current_price, 0),
            'pattern': pat_name,
            'pattern_reliability': pat_rel,
            'retracement': round(retracement, 1),
            'rvol': round(rvol, 2),
            'reasons': reasons
        }
        
    except Exception as e:
        return None


def simulate_moderate(signal: dict) -> dict:
    """MODERATE 모드 시뮬레이션"""
    try:
        entry = signal['price']
        entry_dt = datetime.strptime(signal['date'], '%Y-%m-%d')
        score = signal['score']
        
        # 점수별 보유 기간 및 손절/목표
        if score >= 60:
            max_days = 15
            stop_pct = 0.93
            target_pct = 1.18
        elif score >= 55:
            max_days = 12
            stop_pct = 0.94
            target_pct = 1.15
        elif score >= 50:
            max_days = 10
            stop_pct = 0.95
            target_pct = 1.12
        else:  # 45~49
            max_days = 8
            stop_pct = 0.96
            target_pct = 1.10
        
        stop = entry * stop_pct
        target = entry * target_pct
        
        df = get_price(signal['symbol'],
                      (entry_dt + timedelta(days=1)).strftime('%Y-%m-%d'),
                      (entry_dt + timedelta(days=25)).strftime('%Y-%m-%d'))
        
        if df is None or len(df) < 5:
            return None
        
        for idx in range(min(max_days, len(df))):
            row = df.iloc[idx]
            if row['Low'] <= stop:
                return {'return': round((stop - entry) / entry * 100, 2), 'exit': 'stop', 'days': idx + 1}
            if row['High'] >= target:
                return {'return': round((target - entry) / entry * 100, 2), 'exit': 'target', 'days': idx + 1}
        
        final = df['Close'].iloc[min(max_days-1, len(df)-1)]
        ret = ((final - entry) / entry) * 100
        return {'return': round(ret, 2), 'exit': 'hold', 'days': min(max_days, len(df))}
        
    except Exception as e:
        return None


def run_moderate_backtest():
    """MODERATE 모드 백테스트"""
    print("=" * 80)
    print("🔥 MODERATE 모드 백테스트")
    print("=" * 80)
    print("조건: 고신뢰도 패턴 (Morning Star, Engulfing, Pinbar, Hammer), 45점+")
    print(f"대상 종목: {len(ALL_STOCKS)}개")
    print("=" * 80)
    
    dates = ['2026-01-13', '2026-01-20', '2026-01-27',
             '2026-02-03', '2026-02-10', '2026-02-17', '2026-02-24', 
             '2026-03-03', '2026-03-10', '2026-03-17', '2026-03-24', '2026-03-31']
    
    all_trades = []
    pattern_stats = {}
    total_signals = 0
    
    for symbol in ALL_STOCKS:
        print(f"\n📊 {symbol} 스캐닝...", end=' ')
        symbol_count = 0
        
        for date in dates:
            signal = scan_moderate_mode(symbol, date)
            if signal:
                total_signals += 1
                symbol_count += 1
                trade = simulate_moderate(signal)
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
                    
                    pat = signal['pattern']
                    if pat not in pattern_stats:
                        pattern_stats[pat] = {'count': 0, 'wins': 0, 'returns': []}
                    pattern_stats[pat]['count'] += 1
                    pattern_stats[pat]['returns'].append(trade['return'])
                    if trade['return'] > 0:
                        pattern_stats[pat]['wins'] += 1
        
        print(f"{symbol_count}개 신호")
    
    return all_trades, pattern_stats, total_signals


def analyze_moderate_results(trades, pattern_stats, total_signals):
    """MODERATE 모드 결과 분석"""
    print("\n" + "=" * 80)
    print("📊 MODERATE 모드 결과 분석")
    print("=" * 80)
    
    if not trades:
        print("\n⚠️ 유효한 거래가 없습니다.")
        return None
    
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
    print(f"   총 신호: {total_signals}개")
    print(f"   유효 거래: {total}회")
    print(f"   신호→거래 전환률: {total/total_signals*100:.1f}%")
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
    for threshold in [60, 55, 50, 45]:
        subset = [t for t in trades if t['score'] >= threshold]
        if subset:
            r = [t['return'] for t in subset]
            wr = len([x for x in r if x > 0]) / len(r) * 100
            print(f"   {threshold}점+: {len(subset)}회, 승률 {wr:.1f}%, 평균 {np.mean(r):+.2f}%")
    
    # 패털별 성과
    print(f"\n🕯️ 패털별 성과")
    for pat, stats in sorted(pattern_stats.items(), key=lambda x: x[1]['count'], reverse=True):
        if stats['count'] > 0:
            wr = stats['wins'] / stats['count'] * 100
            avg = np.mean(stats['returns'])
            print(f"   {pat}: {stats['count']}회, 승률 {wr:.1f}%, 평균 {avg:+.2f}%")
    
    # 종목별 성과
    print(f"\n📈 종목별 성과 (TOP 15)")
    symbol_stats = {}
    for t in trades:
        sym = t['symbol']
        if sym not in symbol_stats:
            symbol_stats[sym] = []
        symbol_stats[sym].append(t['return'])
    
    symbol_summary = []
    for sym, rets in symbol_stats.items():
        symbol_summary.append({
            'symbol': sym,
            'trades': len(rets),
            'win_rate': len([r for r in rets if r > 0]) / len(rets) * 100,
            'avg_return': np.mean(rets),
            'total_return': sum(rets)
        })
    
    symbol_summary.sort(key=lambda x: x['avg_return'], reverse=True)
    for s in symbol_summary[:15]:
        print(f"   {s['symbol']}: {s['trades']}회, 승률 {s['win_rate']:.1f}%, 평균 {s['avg_return']:+.2f}%")
    
    # TOP/WORST
    print(f"\n🏆 TOP 10 수익 거래")
    for t in sorted(trades, key=lambda x: x['return'], reverse=True)[:10]:
        print(f"   {t['symbol']} ({t['date'][:10]}): {t['return']:+.2f}% ({t['pattern']}, {t['score']}점, {t['exit']})")
    
    print(f"\n⚠️ TOP 10 손실 거래")
    for t in sorted(trades, key=lambda x: x['return'])[:10]:
        print(f"   {t['symbol']} ({t['date'][:10]}): {t['return']:.2f}% ({t['pattern']}, {t['score']}점, {t['exit']})")
    
    # 청산 방식
    print(f"\n📤 청산 방식별 성과")
    exit_stats = {}
    for t in trades:
        exit_type = t['exit']
        if exit_type not in exit_stats:
            exit_stats[exit_type] = []
        exit_stats[exit_type].append(t['return'])
    
    for exit_type, rets in exit_stats.items():
        wr = len([r for r in rets if r > 0]) / len(rets) * 100
        print(f"   {exit_type}: {len(rets)}회, 승률 {wr:.1f}%, 평균 {np.mean(rets):+.2f}%")
    
    return {
        'trades': trades,
        'summary': {
            'total_signals': total_signals,
            'total_trades': total,
            'signal_to_trade_rate': total/total_signals*100,
            'win_rate': win_rate,
            'avg_return': avg_return,
            'total_return': total_return,
            'profit_factor': pf
        }
    }


if __name__ == '__main__':
    trades, pattern_stats, total_signals = run_moderate_backtest()
    results = analyze_moderate_results(trades, pattern_stats, total_signals)
    
    if results:
        with open('docs/moderate_mode_backtest.json', 'w', encoding='utf-8') as f:
            json.dump(results, f, ensure_ascii=False, indent=2, default=str)
        print("\n✅ 저장: docs/moderate_mode_backtest.json")
