#!/usr/bin/env python3
"""
Japanese Pattern Parameter Sweep Backtest
=========================================
일본 고전 기법 파라미터 스윕 백테스트

테스트 파라미터:
1. 일목균형표 기간: 단기(5,10,20) / 표준(9,26,52) / 장기(13,26,78)
2. 보유기간: 1일(단타) / 3일 / 5일 / 10일(중기)
3. 손절/익절: -3%/+6% (단타) / -5%/+10% (중기) / -7%/+15% (장기)
"""

import sqlite3
import pandas as pd
import numpy as np
from typing import List, Dict, Optional, Tuple
import json
from dataclasses import dataclass
from datetime import datetime


@dataclass
class IchimokuParams:
    """일목균형표 파라미터"""
    name: str
    tenkan: int
    kijun: int
    senkou_b: int
    displacement: int
    desc: str


# 테스트할 파라미터 세트
PARAMS_SETS = [
    IchimokuParams("Short", 5, 10, 20, 10, "단기: 5/10/20"),
    IchimokuParams("Standard", 9, 26, 52, 26, "표준: 9/26/52"),
    IchimokuParams("Long", 13, 39, 78, 26, "장기: 13/39/78"),
]

HOLDING_PERIODS = [1, 3, 5, 10]
STOP_PROFIT_SETS = [
    (-3, 6),   # 단타
    (-5, 10),  # 중기
    (-7, 15),  # 장기
]


class FlexibleIchimoku:
    """가변 파라미터 일목균형표"""
    
    def __init__(self, params: IchimokuParams):
        self.params = params
    
    def calculate(self, df: pd.DataFrame) -> pd.DataFrame:
        """일목균형표 계산"""
        data = df.copy()
        p = self.params
        
        # 전환선
        data['tenkan'] = (data['high'].rolling(window=p.tenkan).max() + 
                          data['low'].rolling(window=p.tenkan).min()) / 2
        
        # 기준선
        data['kijun'] = (data['high'].rolling(window=p.kijun).max() + 
                         data['low'].rolling(window=p.kijun).min()) / 2
        
        return data
    
    def get_signals(self, df: pd.DataFrame) -> List[str]:
        """신호 생성"""
        if len(df) < max(self.params.tenkan, self.params.kijun) + 5:
            return []
        
        data = self.calculate(df)
        
        signals = []
        latest = data.iloc[-1]
        prev = data.iloc[-2]
        
        # 골든크로스
        if prev['tenkan'] <= prev['kijun'] and latest['tenkan'] > latest['kijun']:
            signals.append('TK_CROSS_BULLISH')
        
        # 데드크로스
        elif prev['tenkan'] >= prev['kijun'] and latest['tenkan'] < latest['kijun']:
            signals.append('TK_CROSS_BEARISH')
        
        # 가격 vs 기준선
        if latest['close'] > latest['kijun']:
            signals.append('PRICE_ABOVE_KIJUN')
        else:
            signals.append('PRICE_BELOW_KIJUN')
        
        return signals


class MultiParamBacktester:
    """다중 파라미터 백테스터"""
    
    def __init__(self, db_path: str = 'data/level1_prices.db'):
        self.db_path = db_path
    
    def get_stock_data(self, code: str, days: int = 100) -> pd.DataFrame:
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
    
    def get_liquid_stocks(self, date: str, limit: int = 300) -> List[Dict]:
        """유동성 상위 종목"""
        conn = sqlite3.connect(self.db_path)
        
        query = """
        SELECT code, name, close, volume
        FROM price_data
        WHERE date = ? AND close >= 2000
        ORDER BY (close * volume) DESC
        LIMIT ?
        """
        
        df = pd.read_sql(query, conn, params=(date, limit))
        conn.close()
        
        return df.to_dict('records')
    
    def find_signals_for_date(self, date: str, params: IchimokuParams) -> List[Dict]:
        """특정 날짜 신호 탐색"""
        stocks = self.get_liquid_stocks(date)
        signals = []
        
        ichi = FlexibleIchimoku(params)
        
        for stock in stocks:
            df = self.get_stock_data(stock['code'])
            if len(df) < 60:
                continue
            
            # 해당 날짜까지 필터
            df_up_to = df[df['date'] <= date]
            if len(df_up_to) < max(params.tenkan, params.kijun) + 5:
                continue
            
            sigs = ichi.get_signals(df_up_to)
            
            if sigs and ('TK_CROSS_BULLISH' in sigs or 'TK_CROSS_BEARISH' in sigs):
                latest = df_up_to.iloc[-1]
                signals.append({
                    'code': stock['code'],
                    'name': stock['name'],
                    'date': date,
                    'close': float(latest['close']),
                    'signals': sigs,
                    'params': params.name,
                })
        
        return signals
    
    def backtest_single(self, signal: Dict, 
                       holding_days: int,
                       stop_loss: float,
                       take_profit: float) -> Optional[Dict]:
        """단일 백테스트"""
        conn = sqlite3.connect(self.db_path)
        
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
        
        entry_price = df.iloc[1]['open']
        
        for day_idx, (_, row) in enumerate(df.iloc[2:].iterrows(), 1):
            day_high = (row['high'] - entry_price) / entry_price * 100
            day_low = (row['low'] - entry_price) / entry_price * 100
            day_return = (row['close'] - entry_price) / entry_price * 100
            
            # 손절
            if day_low <= stop_loss:
                return {
                    'return': stop_loss,
                    'days': day_idx,
                    'reason': 'stop_loss',
                }
            
            # 익절
            if day_high >= take_profit:
                return {
                    'return': take_profit,
                    'days': day_idx,
                    'reason': 'take_profit',
                }
            
            # 기간 종료
            if day_idx >= holding_days:
                return {
                    'return': day_return,
                    'days': day_idx,
                    'reason': 'time_exit',
                }
        
        return None
    
    def run_sweep(self, dates: List[str]) -> Dict:
        """파라미터 스윕 실행"""
        results = {}
        
        for params in PARAMS_SETS:
            print(f"\n{'='*70}")
            print(f"📊 파라미터: {params.name} ({params.desc})")
            print(f"{'='*70}")
            
            # 신호 수집
            all_signals = []
            for date in dates:
                sigs = self.find_signals_for_date(date, params)
                all_signals.extend(sigs)
            
            print(f"총 신호: {len(all_signals)}개")
            
            if not all_signals:
                continue
            
            # 각 조합 테스트
            for holding in HOLDING_PERIODS:
                for stop, profit in STOP_PROFIT_SETS:
                    key = f"{params.name}_H{holding}_SL{stop}_TP{profit}"
                    
                    print(f"\n  테스트: 보유{holding}일 / 손절{stop}% / 익절{profit}%")
                    
                    backtests = []
                    for sig in all_signals:
                        result = self.backtest_single(sig, holding, stop, profit)
                        if result:
                            backtests.append(result)
                    
                    if backtests:
                        returns = [b['return'] for b in backtests]
                        wins = len([b for b in backtests if b['return'] > 0])
                        
                        results[key] = {
                            'params': params.name,
                            'holding_days': holding,
                            'stop_loss': stop,
                            'take_profit': profit,
                            'total_trades': len(backtests),
                            'win_rate': wins / len(backtests) * 100,
                            'avg_return': np.mean(returns),
                            'median_return': np.median(returns),
                            'max_return': max(returns),
                            'min_return': min(returns),
                        }
                        
                        print(f"    승률: {results[key]['win_rate']:.1f}%")
                        print(f"    평균수익: {results[key]['avg_return']:+.2f}%")
        
        return results
    
    def print_best_results(self, results: Dict):
        """최고 결과 출력"""
        print("\n" + "=" * 70)
        print("🏆 TOP 10 파라미터 조합")
        print("=" * 70)
        
        sorted_results = sorted(
            results.items(),
            key=lambda x: (x[1]['win_rate'], x[1]['avg_return']),
            reverse=True
        )[:10]
        
        for key, r in sorted_results:
            print(f"\n{key}")
            print(f"  거래: {r['total_trades']}건")
            print(f"  승률: {r['win_rate']:.1f}%")
            print(f"  평균: {r['avg_return']:+.2f}%")
            print(f"  중간: {r['median_return']:+.2f}%")


def main():
    backtester = MultiParamBacktester()
    
    # 테스트 기간 (2주)
    test_dates = [
        '2026-03-25', '2026-03-26', '2026-03-27',
        '2026-03-28', '2026-03-31', '2026-04-01',
        '2026-04-02', '2026-04-03', '2026-04-07',
        '2026-04-08'
    ]
    
    print(f"📅 테스트 기간: {test_dates[0]} ~ {test_dates[-1]}")
    
    results = backtester.run_sweep(test_dates)
    backtester.print_best_results(results)
    
    # 결과 저장
    import os
    os.makedirs('reports', exist_ok=True)
    
    with open('reports/japanese_param_sweep.json', 'w', encoding='utf-8') as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    
    print(f"\n💾 저장: reports/japanese_param_sweep.json")


if __name__ == '__main__':
    main()
