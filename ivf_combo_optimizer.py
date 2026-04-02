#!/usr/bin/env python3
"""
IVF 조합 최적화 테스터
여러 지표 조합을 테스트하여 최적의 승률 조합 찾기
"""

import sys
sys.path.insert(0, '/root/.openclaw/workspace/strg')

import json
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from dataclasses import dataclass
from typing import List, Dict, Tuple
from fdr_wrapper import get_price
from ivf_scanner_v2 import calculate_rsi, calculate_stochastic, detect_candle_patterns, analyze_rsi_divergence


@dataclass
class IndicatorCombo:
    """지표 조합 정의"""
    name: str
    use_fib: bool = True
    use_rsi_stoch: bool = False
    use_candle: bool = False
    use_divergence: bool = False
    use_volume: bool = True
    min_score: int = 50
    description: str = ""


# 테스트할 조합 목록
COMBINATIONS = [
    # 기본 조합
    IndicatorCombo("Base", True, False, False, False, True, 50, "Fib + Volume만"),
    
    # 단일 추가 지표
    IndicatorCombo("Fib+RSI", True, True, False, False, True, 55, "Fib + RSI/Stochastic"),
    IndicatorCombo("Fib+Candle", True, False, True, False, True, 55, "Fib + 캔들 패턴"),
    IndicatorCombo("Fib+Div", True, False, False, True, True, 55, "Fib + RSI 다이버전스"),
    
    # 2개 조합
    IndicatorCombo("Fib+RSI+Candle", True, True, True, False, True, 60, "Fib + RSI + 캔들"),
    IndicatorCombo("Fib+RSI+Div", True, True, False, True, True, 60, "Fib + RSI + 다이버전스"),
    IndicatorCombo("Fib+Candle+Div", True, False, True, True, True, 60, "Fib + 캔들 + 다이버전스"),
    
    # 3개 조합
    IndicatorCombo("Fib+RSI+Candle+Div", True, True, True, True, True, 65, "모든 지표"),
    
    # 점수 조정
    IndicatorCombo("Fib+Div_High", True, False, False, True, True, 70, "Fib + 다이버전스 (70점+)"),
    IndicatorCombo("Fib+Candle_High", True, False, True, False, True, 70, "Fib + 캔들 (70점+)"),
]


def calculate_combo_score(df: pd.DataFrame, combo: IndicatorCombo) -> Dict:
    """특정 조합의 점수 계산"""
    closes = df['Close'].values
    highs = df['High'].values
    lows = df['Low'].values
    volumes = df['Volume'].values
    opens = df['Open'].values
    
    current_price = closes[-1]
    score = 0
    confluence = []
    details = {}
    
    # 1. Fibonacci (기본, 항상 포함)
    if combo.use_fib:
        recent_high = np.max(highs[-20:])
        recent_low = np.min(lows[-20:])
        
        if recent_high > recent_low:
            retracement = ((recent_high - current_price) / (recent_high - recent_low)) * 100
        else:
            retracement = 50
        
        if 38.2 <= retracement <= 61.8:
            score += 25
            confluence.append(f'Fib_{retracement:.0f}')
            details['fib'] = retracement
        elif 30 <= retracement < 38.2:
            score += 15
            confluence.append('Fib_Shallow')
            details['fib'] = retracement
        else:
            return None  # 피볼나치 조건 불충족 시 스킵
    
    # 2. RSI + Stochastic
    if combo.use_rsi_stoch:
        rsi = calculate_rsi(closes[-20:], 14)
        k, d = calculate_stochastic(highs[-20:], lows[-20:], closes[-20:])
        
        if 30 <= rsi <= 50:
            score += 8
            confluence.append('RSI_Recovery')
        
        if k > d and k < 50:
            score += 7
            confluence.append('Stoch_GC')
        
        details['rsi'] = rsi
        details['stoch_k'] = k
    
    # 3. 캔들 패턴
    if combo.use_candle:
        patterns = detect_candle_patterns(df)
        if 'Bullish_Pinbar' in patterns:
            score += 10
            confluence.append('Pinbar')
        elif 'Hammer' in patterns:
            score += 8
            confluence.append('Hammer')
        
        details['patterns'] = patterns
    
    # 4. RSI 다이버전스
    if combo.use_divergence:
        divergence = analyze_rsi_divergence(df)
        if divergence == 'Bullish_Divergence':
            score += 15
            confluence.append('RSI_Divergence')
            details['divergence'] = True
        else:
            details['divergence'] = False
    
    # 5. 거래량
    if combo.use_volume:
        avg_vol_20 = np.mean(volumes[-20:])
        rvol = volumes[-1] / avg_vol_20 if avg_vol_20 > 0 else 1.0
        
        if rvol >= 2.0:
            score += 10
            confluence.append('RVol_2.0')
        elif rvol >= 1.5:
            score += 7
            confluence.append('RVol_1.5')
        elif rvol >= 1.2:
            score += 5
            confluence.append('RVol_Up')
        
        details['rvol'] = rvol
    
    # 최소 점수 확인
    if score < combo.min_score:
        return None
    
    # 리스크 계산
    atr = np.mean([highs[-i] - lows[-i] for i in range(1, 15)])
    stop_loss = current_price - (atr * 1.5)
    target_price = current_price + (atr * 3.0)
    
    return {
        'symbol': '',  # 나중에 채움
        'date': '',
        'combo_name': combo.name,
        'score': score,
        'price': round(current_price, 0),
        'stop_loss': round(stop_loss, 0),
        'target_price': round(target_price, 0),
        'confluence': confluence,
        'details': details
    }


def simulate_trade(signal: Dict, symbol: str, entry_date: str) -> Dict:
    """거래 시뮬레이션"""
    try:
        entry_price = signal['price']
        stop_loss = signal['stop_loss']
        target_price = signal['target_price']
        
        entry_dt = datetime.strptime(entry_date, '%Y-%m-%d')
        end_dt = entry_dt + timedelta(days=12)
        
        df = get_price(symbol,
                      (entry_dt + timedelta(days=1)).strftime('%Y-%m-%d'),
                      end_dt.strftime('%Y-%m-%d'))
        
        if df is None or len(df) < 3:
            return None
        
        # 시뮬레이션
        exit_price = None
        exit_reason = None
        hold_days = 0
        
        for idx in range(min(10, len(df))):
            row = df.iloc[idx]
            hold_days = idx + 1
            
            if row['Low'] <= stop_loss:
                exit_price = stop_loss
                exit_reason = '손절'
                break
            
            if row['High'] >= target_price:
                exit_price = target_price
                exit_reason = '목표도달'
                break
        
        if exit_price is None:
            exit_price = df['Close'].iloc[min(9, len(df)-1)]
            exit_reason = '보유만기'
        
        return_pct = ((exit_price - entry_price) / entry_price) * 100
        
        return {
            'symbol': symbol,
            'entry_date': entry_date,
            'combo': signal['combo_name'],
            'score': signal['score'],
            'return_pct': round(return_pct, 2),
            'exit_reason': exit_reason,
            'hold_days': hold_days,
            'confluence': signal['confluence']
        }
        
    except Exception as e:
        return None


def run_combo_backtest(symbols: List[str], dates: List[str]) -> Dict:
    """모든 조합 백테스트 실행"""
    print("=" * 80)
    print("🔥 IVF 지표 조합 최적화 테스터")
    print("=" * 80)
    print(f"대상 종목: {len(symbols)}개")
    print(f"테스트 날짜: {len(dates)}개")
    print(f"테스트 조합: {len(COMBINATIONS)}개")
    print("=" * 80)
    
    results = {combo.name: {'trades': [], 'signals': 0} for combo in COMBINATIONS}
    
    # 각 종목/날짜별 모든 조합 테스트
    for symbol in symbols:
        print(f"\n📊 {symbol} 분석 중...")
        
        for date in dates:
            # 데이터 로드
            end_dt = datetime.strptime(date, '%Y-%m-%d')
            start_dt = end_dt - timedelta(days=90)
            
            df = get_price(symbol, start_dt.strftime('%Y-%m-%d'), date)
            if df is None or len(df) < 30:
                continue
            
            df = df.reset_index()
            
            # 각 조합 테스트
            for combo in COMBINATIONS:
                signal = calculate_combo_score(df, combo)
                if signal:
                    signal['symbol'] = symbol
                    signal['date'] = date
                    results[combo.name]['signals'] += 1
                    
                    # 시뮬레이션
                    trade = simulate_trade(signal, symbol, date)
                    if trade:
                        results[combo.name]['trades'].append(trade)
    
    return results


def analyze_combo_results(results: Dict) -> List[Dict]:
    """조합별 결과 분석"""
    print("\n" + "=" * 80)
    print("📊 조합별 성과 분석")
    print("=" * 80)
    
    analysis = []
    
    for combo_name, data in results.items():
        trades = data['trades']
        signals = data['signals']
        
        if not trades:
            continue
        
        returns = [t['return_pct'] for t in trades]
        wins = [r for r in returns if r > 0]
        
        total = len(trades)
        win_rate = len(wins) / total * 100 if total > 0 else 0
        avg_return = np.mean(returns)
        total_return = sum(returns)
        
        gross_profit = sum([r for r in returns if r > 0])
        gross_loss = abs(sum([r for r in returns if r <= 0]))
        pf = gross_profit / gross_loss if gross_loss > 0 else 0
        
        analysis.append({
            'combo': combo_name,
            'signals': signals,
            'trades': total,
            'win_rate': win_rate,
            'avg_return': avg_return,
            'total_return': total_return,
            'profit_factor': pf,
            'avg_win': np.mean(wins) if wins else 0,
            'avg_loss': np.mean([r for r in returns if r <= 0]) if len(returns) > len(wins) else 0
        })
    
    # 승률 기준 정렬
    analysis.sort(key=lambda x: x['win_rate'], reverse=True)
    
    # 결과 출력
    print(f"\n{'순위':<4} {'조합명':<20} {'신호':<6} {'거래':<6} {'승률':<8} {'평균수익':<10} {'PF':<6}")
    print("-" * 80)
    
    for i, a in enumerate(analysis, 1):
        print(f"{i:<4} {a['combo']:<20} {a['signals']:<6} {a['trades']:<6} "
              f"{a['win_rate']:>6.1f}%  {a['avg_return']:>+7.2f}%   {a['profit_factor']:>5.2f}")
    
    # TOP 3 상세 분석
    print("\n" + "=" * 80)
    print("🏆 TOP 3 조합 상세 분석")
    print("=" * 80)
    
    for i, a in enumerate(analysis[:3], 1):
        print(f"\n{i}위: {a['combo']}")
        print(f"   승률: {a['win_rate']:.1f}% ({a['trades']}회 거래)")
        print(f"   평균 수익률: {a['avg_return']:+.2f}%")
        print(f"   총 수익률: {a['total_return']:+.2f}%")
        print(f"   Profit Factor: {a['profit_factor']:.2f}")
        print(f"   평균 수익: {a['avg_win']:+.2f}%")
        print(f"   평균 손실: {a['avg_loss']:.2f}%")
    
    return analysis


if __name__ == '__main__':
    symbols = ['033100', '140860', '348210', '006730', '009620', '012210', '025980', '042700',
               '005930', '000660', '055550', '051910', '028260']
    
    dates = ['2026-01-13', '2026-01-20', '2026-01-27',
             '2026-02-03', '2026-02-10', '2026-02-17', '2026-02-24', 
             '2026-03-03', '2026-03-10', '2026-03-17', '2026-03-24', '2026-03-31']
    
    results = run_combo_backtest(symbols, dates)
    analysis = analyze_combo_results(results)
    
    # 저장
    output = {
        'combinations': [c.__dict__ for c in COMBINATIONS],
        'results': results,
        'analysis': analysis
    }
    
    with open('docs/ivf_combo_optimization.json', 'w', encoding='utf-8') as f:
        json.dump(output, f, ensure_ascii=False, indent=2, default=str)
    
    print("\n✅ 저장: docs/ivf_combo_optimization.json")
