#!/usr/bin/env python3
"""
V-Series + Fibonacci + ATR Backtest
Buffett 가치 투자 + Fibonacci 진입 + ATR 리스크 관리
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Tuple
import json
import os
import warnings
warnings.filterwarnings('ignore')

import sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from fdr_wrapper import FDRWrapper
fdr = FDRWrapper()


def normalize_columns(df: pd.DataFrame) -> pd.DataFrame:
    """컬럼명 표준화"""
    df = df.copy()
    column_map = {}
    for col in df.columns:
        col_cap = col.capitalize()
        if col_cap in ['Open', 'High', 'Low', 'Close', 'Volume', 'Date']:
            column_map[col] = col_cap
    df.rename(columns=column_map, inplace=True)
    return df


class ValueFibATRStrategy:
    """
    V-Series + Fibonacci + ATR 전략
    - Buffett 가치 필터로 선별
    - Fibonacci 레벨에서 진입
    - ATR 기반 손절/목표가
    - 1:2 손익비 필터
    """
    
    def __init__(self,
                 value_score_threshold: float = 70.0,  # 가치점수 B+ 이상
                 risk_reward_ratio: float = 2.0,       # 1:2 손익비
                 atr_multiplier: float = 2.0,          # ATR × 2
                 fib_entry_tolerance: float = 0.05,    # Fibonacci 진입 허용 범위 ±5%
                 min_market_cap: float = 1000,         # 최소 시총 1000억
                 min_volume: float = 1_000_000):       # 최소 거래대금 10억
        
        self.value_score_threshold = value_score_threshold
        self.risk_reward_ratio = risk_reward_ratio
        self.atr_multiplier = atr_multiplier
        self.fib_entry_tolerance = fib_entry_tolerance
        self.min_market_cap = min_market_cap
        self.min_volume = min_volume
        
        # 가치 투자 필터 파라미터
        self.graham_params = {
            'max_pe': 15,
            'max_pb': 1.5,
            'min_ncav_ratio': 1.0
        }
        
        self.quality_params = {
            'min_roe': 15,
            'min_profit_margin': 10,
            'max_debt_ratio': 100
        }
        
        self.dividend_params = {
            'min_dividend_yield': 2.0,
            'min_dividend_growth': 5
        }
    
    def calculate_atr(self, df: pd.DataFrame, period: int = 14) -> pd.Series:
        """ATR 계산"""
        high = df['High']
        low = df['Low']
        close = df['Close']
        
        tr1 = high - low
        tr2 = abs(high - close.shift(1))
        tr3 = abs(low - close.shift(1))
        
        tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
        atr = tr.rolling(window=period, min_periods=1).mean()
        
        return atr
    
    def calculate_fibonacci_levels(self, df: pd.DataFrame, lookback: int = 20) -> Dict[str, float]:
        """Fibonacci 레벨 계산"""
        recent_high = df['High'].rolling(window=lookback, min_periods=5).max().iloc[-1]
        recent_low = df['Low'].rolling(window=lookback, min_periods=5).min().iloc[-1]
        
        price_range = recent_high - recent_low
        
        # Retracement levels
        fib_382 = recent_high - price_range * 0.382
        fib_50 = recent_high - price_range * 0.5
        fib_618 = recent_high - price_range * 0.618
        
        # Extension levels for targets
        fib_1382 = recent_high + price_range * 0.382
        fib_1618 = recent_high + price_range * 0.618
        
        current_close = df['Close'].iloc[-1]
        
        return {
            'high': recent_high,
            'low': recent_low,
            'range': price_range,
            'fib_382': fib_382,
            'fib_50': fib_50,
            'fib_618': fib_618,
            'fib_1382': fib_1382,
            'fib_1618': fib_1618,
            'current': current_close
        }
    
    def calculate_risk_reward(self, entry: float, target: float, stop_loss: float) -> float:
        """손익비 계산"""
        if entry <= stop_loss or target <= entry:
            return 0.0
        reward = target - entry
        risk = entry - stop_loss
        return reward / risk if risk > 0 else 0.0
    
    def calculate_value_score(self, symbol: str, date: datetime) -> Tuple[float, str]:
        """
        간단한 가치점수 계산 (기술적 지표 기반)
        실제로는 재무 데이터 필요하지만, 여기서는 기술적 패턴으로 근사
        """
        try:
            start_dt = date - timedelta(days=252)  # 1년
            start_str = start_dt.strftime('%Y-%m-%d')
            end_str = date.strftime('%Y-%m-%d')
            
            df = fdr.get_price(symbol, start=start_str, end=end_str)
            df = normalize_columns(df)
            
            if len(df) < 60:
                return 0, "데이터부족"
            
            # 기술적 가치 지표들
            current_price = df['Close'].iloc[-1]
            
            # 1. Graham Net-Net 근사 (주가가 52주 최저가 근처)
            low_52w = df['Low'].rolling(252, min_periods=60).min().iloc[-1]
            high_52w = df['High'].rolling(252, min_periods=60).max().iloc[-1]
            price_range = (current_price - low_52w) / (high_52w - low_52w) if high_52w > low_52w else 0.5
            
            # 2. Quality 근사 (추세 방향성)
            ma20 = df['Close'].rolling(20).mean().iloc[-1]
            ma60 = df['Close'].rolling(60).mean().iloc[-1]
            trend_score = 100 if current_price > ma20 > ma60 else 50 if current_price > ma60 else 0
            
            # 3. Dividend 근사 (거래량 안정성)
            volume_mean = df['Volume'].rolling(20).mean().iloc[-1]
            volume_std = df['Volume'].rolling(20).std().iloc[-1]
            volume_stability = 100 - min(100, (volume_std / volume_mean * 100)) if volume_mean > 0 else 0
            
            # 종합 점수
            value_score = (price_range * 30) + (trend_score * 0.4) + (volume_stability * 0.3)
            
            # 전략 분류
            if price_range < 0.3:
                strategy = "Graham_NetNet"
            elif trend_score >= 80:
                strategy = "Quality_FairPrice"
            elif volume_stability >= 70:
                strategy = "Dividend_Machine"
            else:
                strategy = "Value_Blend"
            
            return value_score, strategy
            
        except Exception as e:
            return 0, f"오류: {e}"
    
    def scan_and_select(self,
                       symbols: List[str],
                       scan_date: datetime,
                       max_positions: int = 5) -> List[Dict]:
        """V-Series + Fibonacci + ATR 종목 선정"""
        candidates = []
        
        start_dt = scan_date - timedelta(days=100)
        start_str = start_dt.strftime('%Y-%m-%d')
        end_str = scan_date.strftime('%Y-%m-%d')
        
        print(f"\n🔍 V-Series 스캔: {len(symbols)}개 종목 (기준일: {scan_date.strftime('%Y-%m-%d')})")
        
        for symbol in symbols:
            try:
                # 1. 가치 점수 계산
                value_score, strategy_type = self.calculate_value_score(symbol, scan_date)
                
                if value_score < self.value_score_threshold:
                    continue
                
                # 2. 기술적 데이터 로드
                df = fdr.get_price(symbol, start=start_str, end=end_str)
                df = normalize_columns(df)
                
                if len(df) < 60:
                    continue
                
                # 3. ATR 계산
                atr = self.calculate_atr(df, 14).iloc[-1]
                current_price = df['Close'].iloc[-1]
                
                # 최소 거래대금 확인
                avg_volume = df['Volume'].rolling(20).mean().iloc[-1]
                avg_amount = avg_volume * current_price
                if avg_amount < self.min_volume:
                    continue
                
                # 4. Fibonacci 레벨 계산
                fib_levels = self.calculate_fibonacci_levels(df)
                
                # 5. 진입가 설정 (Fibonacci 50% 또는 38.2%)
                # 현재가가 Fibonacci 레벨 근처인지 확인
                entry_price = None
                fib_level_used = None
                
                for level_name, level_price in [
                    ('fib_50', fib_levels['fib_50']),
                    ('fib_382', fib_levels['fib_382']),
                    ('fib_618', fib_levels['fib_618'])
                ]:
                    tolerance = level_price * self.fib_entry_tolerance
                    if level_price - tolerance <= current_price <= level_price + tolerance:
                        entry_price = level_price
                        fib_level_used = level_name
                        break
                
                if entry_price is None:
                    continue
                
                # 6. 목표가 및 손절가 설정
                # 목표가: Fibonacci 138.2% 또는 161.8%
                target_price = fib_levels['fib_1618']
                
                # 손절가: 진입가 - (ATR × multiplier)
                stop_loss = entry_price - (atr * self.atr_multiplier)
                
                # 7. 손익비 확인
                rr_ratio = self.calculate_risk_reward(entry_price, target_price, stop_loss)
                
                if rr_ratio < self.risk_reward_ratio:
                    continue
                
                candidates.append({
                    'symbol': symbol,
                    'value_score': value_score,
                    'strategy_type': strategy_type,
                    'current_price': current_price,
                    'entry_price': entry_price,
                    'target_price': target_price,
                    'stop_loss': stop_loss,
                    'rr_ratio': rr_ratio,
                    'atr': atr,
                    'fib_level': fib_level_used,
                    'fib_high': fib_levels['high'],
                    'fib_low': fib_levels['low']
                })
                
            except Exception as e:
                continue
        
        print(f"   스캔: {len(symbols)}개, 가치조건: {len(candidates)}개")
        
        # 가치점수 순으로 정렬 후 상위 선택
        candidates.sort(key=lambda x: x['value_score'], reverse=True)
        selected = candidates[:max_positions]
        
        print(f"   ✅ 최종 선정: {len(selected)}개 종목")
        for c in selected:
            print(f"      {c['symbol']} ({c['strategy_type']}): 가치점수 {c['value_score']:.1f}, "
                  f"진입 ₩{c['entry_price']:,.0f} → 목표 ₩{c['target_price']:,.0f} (R:R 1:{c['rr_ratio']:.1f})")
        
        return selected


class BacktestEngine:
    """백테스트 엔진"""
    
    def __init__(self,
                 strategy: ValueFibATRStrategy,
                 initial_capital: float = 100_000_000,
                 rebalance_days: int = 30):
        self.strategy = strategy
        self.initial_capital = initial_capital
        self.rebalance_days = rebalance_days
        self.portfolio = {}
        self.trades = []
        self.equity_curve = []
        self.capital = initial_capital
        self.last_rebalance = None
    
    def run_backtest(self,
                    symbols: List[str],
                    start_date: str,
                    end_date: str,
                    max_positions: int = 5) -> Dict:
        """백테스트 실행"""
        
        print(f"\n{'='*60}")
        print(f"📈 V-Series + Fibonacci + ATR 백테스트")
        print(f"{'='*60}")
        print(f"기간: {start_date} ~ {end_date}")
        print(f"초기자본: ₩{self.initial_capital:,.0f}")
        print(f"리밸런싱: {self.rebalance_days}일")
        print(f"최대포지션: {max_positions}개")
        print(f"가치점수 기준: {self.strategy.value_score_threshold}점+")
        print(f"손익비 필터: 1:{self.strategy.risk_reward_ratio}")
        print(f"{'='*60}\n")
        
        current_date = datetime.strptime(start_date, '%Y-%m-%d')
        end_dt = datetime.strptime(end_date, '%Y-%m-%d')
        rebalance_count = 0
        
        while current_date <= end_dt:
            # 거래일 확인
            try:
                test_df = fdr.get_price('005930',
                                       start=(current_date - timedelta(days=5)).strftime('%Y-%m-%d'),
                                       end=current_date.strftime('%Y-%m-%d'))
                test_df = normalize_columns(test_df)
                if len(test_df) == 0:
                    current_date += timedelta(days=1)
                    continue
            except:
                current_date += timedelta(days=1)
                continue
            
            # 리밸런싱일
            if rebalance_count == 0 or (current_date - self.last_rebalance).days >= self.rebalance_days:
                self._rebalance(current_date, symbols, max_positions)
                self.last_rebalance = current_date
                rebalance_count += 1
                print(f"\n📅 {current_date.strftime('%Y-%m-%d')} 리밸런싱... ({rebalance_count})")
            
            # 포지션 모니터링
            self._monitor_positions(current_date)
            
            # 자산 기록
            self._record_equity(current_date)
            
            current_date += timedelta(days=1)
        
        # 최종 결과
        final_equity = self._calculate_total_equity(end_dt)
        
        results = {
            'total_trades': len(self.trades),
            'win_rate': sum(1 for t in self.trades if t['return_pct'] > 0) / len(self.trades) * 100 if self.trades else 0,
            'avg_return': sum(t['return_pct'] for t in self.trades) / len(self.trades) if self.trades else 0,
            'total_return': (final_equity - self.initial_capital) / self.initial_capital * 100,
            'final_capital': final_equity,
            'trades': self.trades,
            'equity_curve': self.equity_curve,
            'parameters': {
                'value_score_threshold': self.strategy.value_score_threshold,
                'risk_reward_ratio': self.strategy.risk_reward_ratio,
                'atr_multiplier': self.strategy.atr_multiplier,
                'fib_entry_tolerance': self.strategy.fib_entry_tolerance
            }
        }
        
        self._print_results(results)
        return results
    
    def _rebalance(self, date: datetime, symbols: List[str], max_positions: int):
        """리밸런싱"""
        # 기존 포지션 유지 (새로운 종목만 추가)
        current_symbols = set(self.portfolio.keys())
        
        # 새 종목 선정
        selected = self.strategy.scan_and_select(symbols, date, max_positions)
        
        if not selected:
            return
        
        # 새 종목만 포트폴리오에 추가 (기존 포지션은 유지)
        capital_per_stock = self.capital / (len(self.portfolio) + len(selected))
        
        for stock in selected:
            if stock['symbol'] not in current_symbols:
                shares = int(capital_per_stock / stock['entry_price'])
                if shares > 0:
                    self.portfolio[stock['symbol']] = {
                        'entry_date': date.strftime('%Y-%m-%d'),
                        'entry_price': stock['entry_price'],
                        'target_price': stock['target_price'],
                        'stop_loss': stock['stop_loss'],
                        'shares': shares,
                        'rr_ratio': stock['rr_ratio'],
                        'value_score': stock['value_score'],
                        'strategy_type': stock['strategy_type']
                    }
    
    def _monitor_positions(self, date: datetime):
        """포지션 모니터링"""
        date_str = date.strftime('%Y-%m-%d')
        
        for symbol, pos in list(self.portfolio.items()):
            try:
                df = fdr.get_price(symbol,
                                  start=(date - timedelta(days=5)).strftime('%Y-%m-%d'),
                                  end=date_str)
                df = normalize_columns(df)
                
                if len(df) == 0:
                    continue
                
                current_price = df['Close'].iloc[-1]
                current_high = df['High'].iloc[-1]
                current_low = df['Low'].iloc[-1]
                
                exit_triggered = False
                exit_price = current_price
                exit_reason = ""
                
                # 목표가 도달
                if current_high >= pos['target_price']:
                    exit_triggered = True
                    exit_price = pos['target_price']
                    exit_reason = "목표가도달"
                
                # 손절가 도달
                elif current_low <= pos['stop_loss']:
                    exit_triggered = True
                    exit_price = pos['stop_loss']
                    exit_reason = "손절"
                
                # 최대 보유기간 (60일)
                entry_date = datetime.strptime(pos['entry_date'], '%Y-%m-%d')
                if (date - entry_date).days >= 60:
                    exit_triggered = True
                    exit_reason = "기간만료"
                
                if exit_triggered:
                    return_pct = (exit_price - pos['entry_price']) / pos['entry_price'] * 100
                    profit = (exit_price - pos['entry_price']) * pos['shares']
                    self.capital += profit
                    
                    self.trades.append({
                        'symbol': symbol,
                        'entry_date': pos['entry_date'],
                        'entry_price': pos['entry_price'],
                        'exit_date': date_str,
                        'exit_price': exit_price,
                        'return_pct': return_pct,
                        'holding_days': (date - entry_date).days,
                        'exit_reason': exit_reason,
                        'rr_ratio': pos['rr_ratio'],
                        'value_score': pos.get('value_score', 0),
                        'strategy_type': pos.get('strategy_type', 'Unknown')
                    })
                    
                    del self.portfolio[symbol]
                    
            except Exception as e:
                continue
    
    def _record_equity(self, date: datetime):
        """자산 기록"""
        equity = self.capital
        
        for symbol, pos in self.portfolio.items():
            try:
                df = fdr.get_price(symbol,
                                  start=(date - timedelta(days=5)).strftime('%Y-%m-%d'),
                                  end=date.strftime('%Y-%m-%d'))
                df = normalize_columns(df)
                if len(df) > 0:
                    current_price = df['Close'].iloc[-1]
                    equity += current_price * pos['shares']
            except:
                equity += pos['entry_price'] * pos['shares']
        
        self.equity_curve.append({
            'date': date.strftime('%Y-%m-%d'),
            'equity': equity
        })
    
    def _calculate_total_equity(self, date: datetime) -> float:
        """총 자산 계산"""
        equity = self.capital
        
        for symbol, pos in self.portfolio.items():
            try:
                df = fdr.get_price(symbol,
                                  start=(date - timedelta(days=5)).strftime('%Y-%m-%d'),
                                  end=date.strftime('%Y-%m-%d'))
                df = normalize_columns(df)
                if len(df) > 0:
                    current_price = df['Close'].iloc[-1]
                    equity += current_price * pos['shares']
                else:
                    equity += pos['entry_price'] * pos['shares']
            except:
                equity += pos['entry_price'] * pos['shares']
        
        return equity
    
    def _print_results(self, results: Dict):
        """결과 출력"""
        print(f"\n{'='*60}")
        print(f"📊 백테스트 결과")
        print(f"{'='*60}")
        print(f"총 거래 횟수: {results['total_trades']}회")
        print(f"승률: {results['win_rate']:.1f}%")
        print(f"평균 수익률: {results['avg_return']:.2f}%")
        print(f"총 수익률: {results['total_return']:.2f}%")
        print(f"최종 자본: ₩{results['final_capital']:,.0f}")
        print(f"{'='*60}")
        
        if results['trades']:
            print(f"\n📋 거래 상세:")
            for i, trade in enumerate(results['trades'][:10], 1):
                emoji = "🟢" if trade['return_pct'] > 0 else "🔴"
                print(f"   {emoji} {trade['symbol']} ({trade['strategy_type']}): "
                      f"{trade['return_pct']:+.2f}% ({trade['exit_reason']}, {trade['holding_days']}일)")


def main():
    # 전략 설정
    strategy = ValueFibATRStrategy(
        value_score_threshold=65.0,     # 가치점수 65점+
        risk_reward_ratio=1.5,          # 1:1.5 손익비 (완화)
        atr_multiplier=1.5,             # ATR × 1.5
        fib_entry_tolerance=0.05        # ±5% 허용
    )
    
    # 대형주 위주 종목 리스트
    symbols = [
        # 대형주
        '005930', '000660', '051910', '005380', '035720',
        '068270', '207940', '006400', '000270', '012330',
        '005490', '028260', '105560', '018260', '032830',
        '000100', '000150', '000250', '000300', '000400',
        '000500', '000650', '000700', '000850', '000950',
        # 중형주
        '003550', '004020', '005070', '005110', '005860',
        '009240', '009830', '010130', '010950', '011200',
        '016360', '024110', '028050', '034220', '034730',
        # 소형 가치주
        '001040', '001460', '001740', '002320', '002700',
        '003200', '003490', '004170', '004800', '005500'
    ]
    
    # 백테스트 실행
    engine = BacktestEngine(
        strategy=strategy,
        initial_capital=100_000_000,
        rebalance_days=30
    )
    
    results = engine.run_backtest(
        symbols=symbols,
        start_date='2025-01-01',
        end_date='2026-03-18',
        max_positions=5
    )
    
    # 결과 저장
    output_dir = './reports/v_series'
    os.makedirs(output_dir, exist_ok=True)
    
    timestamp = datetime.now().strftime('%Y%m%d_%H%M')
    filename = f'{output_dir}/v_series_fib_atr_backtest_{timestamp}.json'
    
    with open(filename, 'w', encoding='utf-8') as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    
    print(f"\n💾 결과 저장: {filename}")


if __name__ == '__main__':
    main()
