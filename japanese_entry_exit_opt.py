#!/usr/bin/env python3
"""
Japanese Pattern Entry & Exit Optimization
==========================================
일본 패턴 매수/매도 시점 및 손익가 최적화

테스트 항목:
1. 진입 시점: 시가 / 저가 / 종가 / 다음날 변동성 기반
2. 손절가: 고정% / ATR 기반 / 피볼나치
3. 목표가: 고정% / ATR 기반 / 피볼나치 확장
4. 리스크/리워드 비율: 1:1.5 / 1:2 / 1:3
5. 트레일링 스탑 옵션
"""

import sqlite3
import pandas as pd
import numpy as np
from typing import List, Dict, Optional, Tuple
import json
from dataclasses import dataclass
from enum import Enum


class EntryType(Enum):
    """진입 유형"""
    NEXT_OPEN = "next_open"      # 다음날 시가
    NEXT_LOW = "next_low"        # 다음날 저가 (저점 매수)
    PULLBACK_50 = "pullback_50"  # 당일 종가 대비 50% 되돌림
    BELOW_KIJUN = "below_kijun"  # 기준선 아래


class ExitType(Enum):
    """청산 유형"""
    FIXED = "fixed"              # 고정 %
    ATR_BASED = "atr"            # ATR 기반
    FIBONACCI = "fibonacci"      # 피볼나치 확장


@dataclass
class RiskRewardParams:
    """리스크/리워드 파라미터"""
    name: str
    entry_type: EntryType
    exit_type: ExitType
    stop_loss_pct: float
    take_profit_pct: float
    trailing_stop: bool = False
    atr_multiplier_sl: float = 1.5
    atr_multiplier_tp: float = 3.0
    fib_level_tp: float = 1.618


def calculate_atr(df: pd.DataFrame, period: int = 14) -> float:
    """ATR 계산"""
    high_low = df['high'] - df['low']
    high_close = np.abs(df['high'] - df['close'].shift())
    low_close = np.abs(df['low'] - df['close'].shift())
    
    tr = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
    atr = tr.rolling(window=period).mean()
    
    return atr.iloc[-1] if not pd.isna(atr.iloc[-1]) else 0


def calculate_fibonacci_extension(high: float, low: float, close: float, 
                                   entry: float, level: float = 1.618) -> float:
    """피볼나치 확장 목표가 계산"""
    range_size = high - low
    return entry + (range_size * level)


class OptimizedJapaneseBacktester:
    """최적화 일본 패턴 백테스터"""
    
    def __init__(self, db_path: str = 'data/level1_prices.db'):
        self.db_path = db_path
    
    def get_stock_data(self, code: str, days: int = 80) -> pd.DataFrame:
        """종목 데이터 조회"""
        conn = sqlite3.connect(self.db_path)
        
        query = """
        SELECT date, open, high, low, close, volume
        FROM price_data
        WHERE code = ? AND date <= date('now')
        ORDER BY date DESC
        LIMIT ?
        """
        
        df = pd.read_sql(query, conn, params=(code, days))
        conn.close()
        
        return df.sort_values('date').reset_index(drop=True)
    
    def get_ichimoku_signals(self, df: pd.DataFrame, 
                            tenkan: int = 5, kijun: int = 10) -> Dict:
        """일목균형표 신호 (단기 파라미터)"""
        if len(df) < kijun + 5:
            return {}
        
        # 전환선, 기준선 계산
        df['tenkan'] = (df['high'].rolling(window=tenkan).max() + 
                        df['low'].rolling(window=tenkan).min()) / 2
        df['kijun'] = (df['high'].rolling(window=kijun).max() + 
                       df['low'].rolling(window=kijun).min()) / 2
        
        latest = df.iloc[-1]
        prev = df.iloc[-2]
        
        signals = []
        
        # 골든크로스
        if prev['tenkan'] <= prev['kijun'] and latest['tenkan'] > latest['kijun']:
            signals.append('TK_CROSS_BULLISH')
        
        # 데드크로스
        elif prev['tenkan'] >= prev['kijun'] and latest['tenkan'] < latest['kijun']:
            signals.append('TK_CROSS_BEARISH')
        
        return {
            'signals': signals,
            'tenkan': latest['tenkan'],
            'kijun': latest['kijun'],
            'close': latest['close'],
            'high': latest['high'],
            'low': latest['low'],
            'atr': calculate_atr(df),
        }
    
    def find_entry_signals(self, date: str, top_n: int = 300) -> List[Dict]:
        """진입 신호 탐색"""
        conn = sqlite3.connect(self.db_path)
        
        # 유동성 상위 종목
        query = """
        SELECT code, name, close, volume
        FROM price_data
        WHERE date = ? AND close >= 2000
        ORDER BY (close * volume) DESC
        LIMIT ?
        """
        
        stocks = pd.read_sql(query, conn, params=(date, top_n))
        conn.close()
        
        signals = []
        for _, stock in stocks.iterrows():
            df = self.get_stock_data(stock['code'])
            if len(df) < 20:
                continue
            
            df_up_to = df[df['date'] <= date]
            if len(df_up_to) < 15:
                continue
            
            ichi = self.get_ichimoku_signals(df_up_to)
            
            if ichi and 'TK_CROSS_BULLISH' in ichi.get('signals', []):
                signals.append({
                    'code': stock['code'],
                    'name': stock['name'],
                    'date': date,
                    'close': ichi['close'],
                    'high': ichi['high'],
                    'low': ichi['low'],
                    'tenkan': ichi['tenkan'],
                    'kijun': ichi['kijun'],
                    'atr': ichi['atr'],
                })
        
        return signals
    
    def calculate_entry_price(self, signal: Dict, entry_type: EntryType,
                             next_day_data: pd.DataFrame) -> float:
        """진입가 계산"""
        if next_day_data.empty:
            return signal['close']
        
        next_day = next_day_data.iloc[0]
        
        if entry_type == EntryType.NEXT_OPEN:
            return next_day['open']
        
        elif entry_type == EntryType.NEXT_LOW:
            # 당일 종가와 다음날 저가 중 더 낮은 가격
            return min(signal['close'], next_day['low'])
        
        elif entry_type == EntryType.PULLBACK_50:
            # 당일 범위의 50% 되돌림
            day_range = signal['high'] - signal['low']
            pullback_price = signal['close'] - (day_range * 0.5)
            return max(pullback_price, next_day['low'])  # 실행 가능 가격
        
        elif entry_type == EntryType.BELOW_KIJUN:
            # 기준선 아래 진입
            target_price = signal['kijun'] * 0.99  # 기준선 아래 1%
            if next_day['low'] <= target_price:
                return target_price
            return next_day['open']
        
        return next_day['open']
    
    def calculate_exit_levels(self, entry: float, signal: Dict, 
                             params: RiskRewardParams) -> Tuple[float, float]:
        """손절/익절가 계산"""
        
        if params.exit_type == ExitType.FIXED:
            stop_loss = entry * (1 + params.stop_loss_pct / 100)
            take_profit = entry * (1 + params.take_profit_pct / 100)
        
        elif params.exit_type == ExitType.ATR_BASED:
            atr = signal['atr']
            stop_loss = entry - (atr * params.atr_multiplier_sl)
            take_profit = entry + (atr * params.atr_multiplier_tp)
        
        elif params.exit_type == ExitType.FIBONACCI:
            # 당일 고저 기준 피볼나치
            stop_loss = signal['low'] * 0.99  # 당일 저가 아래
            take_profit = calculate_fibonacci_extension(
                signal['high'], signal['low'], signal['close'],
                entry, params.fib_level_tp
            )
        
        return stop_loss, take_profit
    
    def backtest_signal(self, signal: Dict, params: RiskRewardParams,
                       holding_days: int = 5) -> Optional[Dict]:
        """단일 신호 백테스트"""
        conn = sqlite3.connect(self.db_path)
        
        # 다음날 데이터 조회
        query = """
        SELECT date, open, high, low, close
        FROM price_data
        WHERE code = ? AND date > ?
        ORDER BY date
        LIMIT ?
        """
        
        df = pd.read_sql(query, conn, 
                        params=(signal['code'], signal['date'], holding_days + 2))
        conn.close()
        
        if len(df) < 2:
            return None
        
        # 진입가 계산
        entry_price = self.calculate_entry_price(
            signal, params.entry_type, df.iloc[1:2]
        )
        
        # 손절/익절가
        stop_loss, take_profit = self.calculate_exit_levels(
            entry_price, signal, params
        )
        
        # 백테스트 시뮬레이션
        max_profit = 0
        max_loss = 0
        exit_price = entry_price
        exit_day = 0
        exit_reason = 'hold'
        
        # 트레일링 스탑 초기값
        trailing_stop = stop_loss
        highest_price = entry_price
        
        for day_idx, (_, row) in enumerate(df.iloc[2:].iterrows(), 1):
            day_high = row['high']
            day_low = row['low']
            day_close = row['close']
            
            # 최고가 업데이트 (트레일링 스탑용)
            if day_high > highest_price:
                highest_price = day_high
                if params.trailing_stop:
                    # ATR의 절반만큼 트레일링
                    trail_distance = signal['atr'] * 1.0
                    trailing_stop = max(trailing_stop, highest_price - trail_distance)
            
            # 수익률 계산
            day_high_return = (day_high - entry_price) / entry_price * 100
            day_low_return = (day_low - entry_price) / entry_price * 100
            
            max_profit = max(max_profit, day_high_return)
            max_loss = min(max_loss, day_low_return)
            
            # 손절 체크
            current_stop = trailing_stop if params.trailing_stop else stop_loss
            if day_low <= current_stop:
                exit_price = current_stop
                exit_day = day_idx
                exit_reason = 'trailing_stop' if params.trailing_stop else 'stop_loss'
                break
            
            # 익절 체크
            if day_high >= take_profit:
                exit_price = take_profit
                exit_day = day_idx
                exit_reason = 'take_profit'
                break
            
            # 기간 종료
            if day_idx >= holding_days:
                exit_price = day_close
                exit_day = day_idx
                exit_reason = 'time_exit'
                break
        
        final_return = (exit_price - entry_price) / entry_price * 100
        r_r_ratio = (take_profit - entry_price) / (entry_price - stop_loss)
        
        return {
            'code': signal['code'],
            'name': signal['name'],
            'entry_price': entry_price,
            'stop_loss': stop_loss,
            'take_profit': take_profit,
            'exit_price': exit_price,
            'final_return': final_return,
            'exit_day': exit_day,
            'exit_reason': exit_reason,
            'max_profit': max_profit,
            'max_loss': max_loss,
            'r_r_ratio': r_r_ratio,
        }
    
    def run_optimization(self, dates: List[str]) -> Dict:
        """최적화 실행"""
        
        # 테스트할 파라미터 조합
        param_combos = [
            # 기본 진입 + 고정 손익
            RiskRewardParams("Basic_Fixed", EntryType.NEXT_OPEN, ExitType.FIXED, -5, 10),
            RiskRewardParams("Basic_Fixed_RR2", EntryType.NEXT_OPEN, ExitType.FIXED, -5, 15),
            RiskRewardParams("Basic_Fixed_RR3", EntryType.NEXT_OPEN, ExitType.FIXED, -5, 20),
            
            # 저가 진입 + 고정 손익
            RiskRewardParams("LowEntry_Fixed", EntryType.NEXT_LOW, ExitType.FIXED, -5, 10),
            
            # 기준선 아래 진입
            RiskRewardParams("BelowKijun_Fixed", EntryType.BELOW_KIJUN, ExitType.FIXED, -5, 10),
            
            # ATR 기반
            RiskRewardParams("ATR_1.5_3.0", EntryType.NEXT_OPEN, ExitType.ATR_BASED, 0, 0, 
                           atr_multiplier_sl=1.5, atr_multiplier_tp=3.0),
            RiskRewardParams("ATR_2.0_4.0", EntryType.NEXT_OPEN, ExitType.ATR_BASED, 0, 0,
                           atr_multiplier_sl=2.0, atr_multiplier_tp=4.0),
            
            # ATR + 트레일링
            RiskRewardParams("ATR_Trail_1.5", EntryType.NEXT_OPEN, ExitType.ATR_BASED, 0, 0,
                           trailing_stop=True, atr_multiplier_sl=1.5, atr_multiplier_tp=4.0),
            
            # 피볼나치
            RiskRewardParams("Fib_1.618", EntryType.NEXT_OPEN, ExitType.FIBONACCI, 0, 0,
                           fib_level_tp=1.618),
            RiskRewardParams("Fib_2.0", EntryType.NEXT_OPEN, ExitType.FIBONACCI, 0, 0,
                           fib_level_tp=2.0),
        ]
        
        results = {}
        
        for params in param_combos:
            print(f"\n{'='*60}")
            print(f"🧪 테스트: {params.name}")
            print(f"   진입: {params.entry_type.value}, 청산: {params.exit_type.value}")
            
            all_signals = []
            for date in dates:
                signals = self.find_entry_signals(date)
                all_signals.extend(signals)
            
            print(f"   총 신호: {len(all_signals)}개")
            
            if not all_signals:
                continue
            
            backtests = []
            for sig in all_signals:
                result = self.backtest_signal(sig, params)
                if result:
                    backtests.append(result)
            
            if backtests:
                returns = [b['final_return'] for b in backtests]
                wins = len([b for b in backtests if b['final_return'] > 0])
                
                results[params.name] = {
                    'total': len(backtests),
                    'win_rate': wins / len(backtests) * 100,
                    'avg_return': np.mean(returns),
                    'median_return': np.median(returns),
                    'max_return': max(returns),
                    'min_return': min(returns),
                    'avg_r_r': np.mean([b['r_r_ratio'] for b in backtests]),
                }
                
                print(f"   승률: {results[params.name]['win_rate']:.1f}%")
                print(f"   평균수익: {results[params.name]['avg_return']:+.2f}%")
                print(f"   평균R:R: {results[params.name]['avg_r_r']:.2f}")
        
        return results
    
    def print_best(self, results: Dict):
        """최고 결과 출력"""
        print("\n" + "=" * 70)
        print("🏆 최적화 결과 TOP 10")
        print("=" * 70)
        
        sorted_results = sorted(
            results.items(),
            key=lambda x: (x[1]['win_rate'], x[1]['avg_return']),
            reverse=True
        )[:10]
        
        for i, (name, r) in enumerate(sorted_results, 1):
            print(f"\n{i}. {name}")
            print(f"   거래: {r['total']}건")
            print(f"   승률: {r['win_rate']:.1f}%")
            print(f"   평균: {r['avg_return']:+.2f}%")
            print(f"   중간: {r['median_return']:+.2f}%")
            print(f"   R:R: {r['avg_r_r']:.2f}")


def main():
    backtester = OptimizedJapaneseBacktester()
    
    # 테스트 기간
    test_dates = [
        '2026-03-25', '2026-03-26', '2026-03-27',
        '2026-03-28', '2026-03-31', '2026-04-01',
        '2026-03-28', '2026-04-02', '2026-04-03',
        '2026-04-07', '2026-04-08'
    ]
    
    print(f"📅 테스트 기간: {test_dates[0]} ~ {test_dates[-1]}")
    
    results = backtester.run_optimization(test_dates)
    backtester.print_best(results)
    
    # 저장
    import os
    os.makedirs('reports', exist_ok=True)
    
    with open('reports/japanese_entry_exit_opt.json', 'w', encoding='utf-8') as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    
    print(f"\n💾 저장: reports/japanese_entry_exit_opt.json")


if __name__ == '__main__':
    main()
