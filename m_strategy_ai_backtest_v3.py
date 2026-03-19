#!/usr/bin/env python3
"""
M-Strategy + AI v3 Backtest
- Fibonacci Retracement for Entry/Target
- ATR-based Stop Loss
- Risk-Reward Ratio Filter (1:2 minimum)
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Tuple
import json
import os
import warnings
warnings.filterwarnings('ignore')

from sklearn.ensemble import RandomForestClassifier, GradientBoostingClassifier
from sklearn.preprocessing import RobustScaler

import sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from local_db import LocalDB
from fdr_wrapper import FDRWrapper
fdr = FDRWrapper()


def normalize_columns(df: pd.DataFrame) -> pd.DataFrame:
    """컬럼명을 표준화 (Open, High, Low, Close, Volume, Date)"""
    df = df.copy()
    column_map = {}
    for col in df.columns:
        col_cap = col.capitalize()
        if col_cap in ['Open', 'High', 'Low', 'Close', 'Volume', 'Date']:
            column_map[col] = col_cap
    df.rename(columns=column_map, inplace=True)
    return df


class FibonacciATRStrategy:
    """Fibonacci + ATR 기반 리스크 관리 전략"""
    
    def __init__(self, 
                 primary_threshold: float = 60.0,
                 meta_threshold: float = 65.0,
                 risk_reward_ratio: float = 2.0,  # 1:2 minimum
                 atr_multiplier: float = 2.0,     # ATR × 2 for stop loss
                 fib_entry_level: float = 0.5,    # 50% retracement
                 fib_target_level: float = 1.618, # 161.8% extension
                 rsi_min: float = 35.0,
                 rsi_max: float = 75.0,
                 volume_threshold: float = 0.8,
                 adx_threshold: float = 15.0):
        
        self.primary_threshold = primary_threshold
        self.meta_threshold = meta_threshold
        self.risk_reward_ratio = risk_reward_ratio
        self.atr_multiplier = atr_multiplier
        self.fib_entry_level = fib_entry_level
        self.fib_target_level = fib_target_level
        self.rsi_min = rsi_min
        self.rsi_max = rsi_max
        self.volume_threshold = volume_threshold
        self.adx_threshold = adx_threshold
        
        self.primary_model = None
        self.meta_model = None
        self.scaler = RobustScaler()
        self.is_trained = False
        
    def calculate_atr(self, df: pd.DataFrame, period: int = 14) -> pd.Series:
        """ATR (Average True Range) 계산"""
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
        """Fibonacci Retracement 및 Extension 레벨 계산"""
        recent_high = df['High'].rolling(window=lookback, min_periods=5).max().iloc[-1]
        recent_low = df['Low'].rolling(window=lookback, min_periods=5).min().iloc[-1]
        
        price_range = recent_high - recent_low
        
        # Retracement levels (for entry)
        fib_382 = recent_high - price_range * 0.382
        fib_50 = recent_high - price_range * 0.5
        fib_618 = recent_high - price_range * 0.618
        
        # Extension levels (for target)
        fib_1382 = recent_high + price_range * 0.382
        fib_1618 = recent_high + price_range * 0.618
        fib_200 = recent_high + price_range
        
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
            'fib_200': fib_200,
            'current': current_close
        }
    
    def calculate_risk_reward(self, entry: float, target: float, stop_loss: float) -> float:
        """손익비 계산 (Reward/Risk)"""
        if entry <= stop_loss or target <= entry:
            return 0.0
        reward = target - entry
        risk = entry - stop_loss
        return reward / risk if risk > 0 else 0.0
    
    def generate_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """기술적 특성 생성"""
        df = df.copy()
        
        # Returns
        df['Return_1d'] = df['Close'].pct_change(1)
        df['Return_5d'] = df['Close'].pct_change(5)
        df['Return_10d'] = df['Close'].pct_change(10)
        df['Return_20d'] = df['Close'].pct_change(20)
        
        # Volatility
        df['Volatility_10d'] = df['Return_1d'].rolling(10).std()
        df['Volatility_20d'] = df['Return_1d'].rolling(20).std()
        
        # Moving averages
        df['MA5'] = df['Close'].rolling(5).mean()
        df['MA10'] = df['Close'].rolling(10).mean()
        df['MA20'] = df['Close'].rolling(20).mean()
        df['MA60'] = df['Close'].rolling(60).mean()
        
        df['Close_MA5_ratio'] = (df['Close'] - df['MA5']) / df['MA5']
        df['Close_MA20_ratio'] = (df['Close'] - df['MA20']) / df['MA20']
        df['Close_MA60_ratio'] = (df['Close'] - df['MA60']) / df['MA60']
        
        # RSI
        delta = df['Close'].diff()
        gain = delta.where(delta > 0, 0).rolling(14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
        rs = gain / loss
        df['RSI'] = 100 - (100 / (1 + rs))
        
        # MACD
        ema12 = df['Close'].ewm(span=12, adjust=False).mean()
        ema26 = df['Close'].ewm(span=26, adjust=False).mean()
        df['MACD'] = ema12 - ema26
        df['MACD_Signal'] = df['MACD'].ewm(span=9, adjust=False).mean()
        df['MACD_Hist'] = df['MACD'] - df['MACD_Signal']
        
        # Volume
        df['Volume_MA20'] = df['Volume'].rolling(20).mean()
        df['Volume_Ratio'] = df['Volume'] / df['Volume_MA20']
        
        # ATR
        df['ATR'] = self.calculate_atr(df, 14)
        df['ATR_Ratio'] = df['ATR'] / df['Close']
        
        # ADX
        plus_dm = df['High'].diff()
        minus_dm = df['Low'].diff().abs()
        plus_dm = plus_dm.where((plus_dm > minus_dm) & (plus_dm > 0), 0)
        minus_dm = minus_dm.where((minus_dm > plus_dm) & (minus_dm > 0), 0)
        
        atr = df['ATR']
        plus_di = 100 * plus_dm.rolling(14).mean() / atr
        minus_di = 100 * minus_dm.rolling(14).mean() / atr
        dx = 100 * abs(plus_di - minus_di) / (plus_di + minus_di)
        df['ADX'] = dx.rolling(14).mean()
        
        # Bollinger Bands
        df['BB_Middle'] = df['Close'].rolling(20).mean()
        bb_std = df['Close'].rolling(20).std()
        df['BB_Upper'] = df['BB_Middle'] + 2 * bb_std
        df['BB_Lower'] = df['BB_Middle'] - 2 * bb_std
        df['BB_Width'] = (df['BB_Upper'] - df['BB_Lower']) / df['BB_Middle']
        df['BB_Position'] = (df['Close'] - df['BB_Lower']) / (df['BB_Upper'] - df['BB_Lower'])
        
        return df.dropna()
    
    def train(self, symbols: List[str], start_date: str, end_date: str):
        """AI 모델 학습"""
        print(f"🤖 AI 모델 학습 중... ({len(symbols)}개 종목)")
        
        all_data = []
        for symbol in symbols:
            try:
                df = fdr.get_price(symbol, start=start_date, end=end_date)
                df = normalize_columns(df)
                if len(df) < 100:
                    continue
                    
                df = self.generate_features(df)
                df['Symbol'] = symbol
                all_data.append(df)
            except Exception as e:
                print(f"  ⚠️ {symbol} 데이터 오류: {e}")
                continue
        
        if not all_data:
            raise ValueError("학습 데이터가 부족합니다")
        
        combined = pd.concat(all_data, ignore_index=True)
        
        # 레이블 생성 (5일 후 수익률)
        combined['Future_Return'] = combined.groupby('Symbol')['Close'].shift(-5).pct_change(5)
        combined['Target'] = (combined['Future_Return'] > 0.02).astype(int)
        
        feature_cols = [
            'Return_1d', 'Return_5d', 'Return_10d', 'Return_20d',
            'Volatility_10d', 'Volatility_20d',
            'Close_MA5_ratio', 'Close_MA20_ratio', 'Close_MA60_ratio',
            'RSI', 'MACD', 'MACD_Hist',
            'Volume_Ratio', 'ATR_Ratio', 'ADX',
            'BB_Width', 'BB_Position'
        ]
        
        train_data = combined.dropna(subset=feature_cols + ['Target'])
        
        X = train_data[feature_cols].values
        y = train_data['Target'].values
        
        # Primary Model
        self.primary_model = RandomForestClassifier(
            n_estimators=100,
            max_depth=10,
            min_samples_split=5,
            random_state=42,
            n_jobs=-1
        )
        self.primary_model.fit(X, y)
        
        # Meta Model
        primary_probs = self.primary_model.predict_proba(X)[:, 1]
        meta_features = np.column_stack([X, primary_probs])
        
        self.meta_model = GradientBoostingClassifier(
            n_estimators=50,
            max_depth=5,
            learning_rate=0.1,
            random_state=42
        )
        self.meta_model.fit(meta_features, y)
        
        self.is_trained = True
        print(f"✅ 학습 완료: {len(train_data)}개 샘플")
        
        return self
    
    def predict(self, df: pd.DataFrame) -> Tuple[str, float, float]:
        """예측 수행"""
        if not self.is_trained:
            raise ValueError("모델이 학습되지 않았습니다")
        
        feature_cols = [
            'Return_1d', 'Return_5d', 'Return_10d', 'Return_20d',
            'Volatility_10d', 'Volatility_20d',
            'Close_MA5_ratio', 'Close_MA20_ratio', 'Close_MA60_ratio',
            'RSI', 'MACD', 'MACD_Hist',
            'Volume_Ratio', 'ATR_Ratio', 'ADX',
            'BB_Width', 'BB_Position'
        ]
        
        latest = df[feature_cols].iloc[-1:].values
        
        primary_prob = self.primary_model.predict_proba(latest)[0, 1]
        meta_features = np.column_stack([latest, [[primary_prob]]])
        meta_prob = self.meta_model.predict_proba(meta_features)[0, 1]
        
        direction = "상승" if meta_prob > 0.6 else "하락" if meta_prob < 0.4 else "중립"
        
        return direction, primary_prob * 100, meta_prob * 100
    
    def scan_and_select(self, 
                       symbols: List[str], 
                       scan_date: datetime,
                       max_positions: int = 5) -> List[Dict]:
        """Fibonacci + ATR 기반 종목 선정"""
        candidates = []
        
        start_dt = scan_date - timedelta(days=100)
        start_str = start_dt.strftime('%Y-%m-%d')
        end_str = scan_date.strftime('%Y-%m-%d')
        
        print(f"\n🔍 스캔: {len(symbols)}개 종목 (기준일: {scan_date.strftime('%Y-%m-%d')})")
        
        for symbol in symbols:
            try:
                df = fdr.get_price(symbol, start=start_str, end=end_str)
                df = normalize_columns(df)
                if len(df) < 60:
                    continue
                
                df = self.generate_features(df)
                latest = df.iloc[-1]
                
                # 기본 필터
                if not (self.rsi_min <= latest['RSI'] <= self.rsi_max):
                    continue
                if latest['Volume_Ratio'] < self.volume_threshold:
                    continue
                if latest['ADX'] < self.adx_threshold:
                    continue
                if latest['Close_MA20_ratio'] < -0.05 or latest['Close_MA60_ratio'] < -0.10:
                    continue
                
                # AI 예측
                direction, primary_conf, meta_conf = self.predict(df)
                
                if direction != "상승" or primary_conf < self.primary_threshold or meta_conf < self.meta_threshold:
                    continue
                
                # Fibonacci 레벨 계산
                fib_levels = self.calculate_fibonacci_levels(df)
                atr = latest['ATR']
                current_price = latest['Close']
                
                # 진입가: Fibonacci 50% retracement
                entry_price = fib_levels['fib_50']
                
                # 목표가: Fibonacci 161.8% extension
                target_price = fib_levels['fib_1618']
                
                # 손절가: ATR × multiplier (진입가 아래)
                stop_loss = entry_price - (atr * self.atr_multiplier)
                
                # 현재가가 진입가附近인지 확인 (±2%)
                if not (entry_price * 0.98 <= current_price <= entry_price * 1.02):
                    continue
                
                # 손익비 계산
                rr_ratio = self.calculate_risk_reward(entry_price, target_price, stop_loss)
                
                if rr_ratio < self.risk_reward_ratio:
                    continue
                
                candidates.append({
                    'symbol': symbol,
                    'current_price': current_price,
                    'entry_price': entry_price,
                    'target_price': target_price,
                    'stop_loss': stop_loss,
                    'rr_ratio': rr_ratio,
                    'atr': atr,
                    'primary_conf': primary_conf,
                    'meta_conf': meta_conf,
                    'rsi': latest['RSI'],
                    'volume_ratio': latest['Volume_Ratio'],
                    'adx': latest['ADX'],
                    'trend': '정배열' if latest['Close_MA20_ratio'] > 0 else '역배열',
                    'fib_high': fib_levels['high'],
                    'fib_low': fib_levels['low']
                })
                
            except Exception as e:
                continue
        
        print(f"   스캔: {len(symbols)}개, AI조건: {len(candidates)}개")
        
        # Meta Confidence 순으로 정렬 후 상위 선택
        candidates.sort(key=lambda x: x['meta_conf'], reverse=True)
        selected = candidates[:max_positions]
        
        print(f"   ✅ 최종 선정: {len(selected)}개 종목")
        for c in selected:
            print(f"      {c['symbol']}: 진입 ₩{c['entry_price']:,.0f} → 목표 ₩{c['target_price']:,.0f} (R:R 1:{c['rr_ratio']:.1f})")
        
        return selected


class BacktestEngine:
    """백테스트 엔진"""
    
    def __init__(self, 
                 strategy: FibonacciATRStrategy,
                 initial_capital: float = 100_000_000,
                 rebalance_days: int = 30):
        self.strategy = strategy
        self.initial_capital = initial_capital
        self.rebalance_days = rebalance_days
        self.portfolio = {}  # symbol -> {'entry_date', 'entry_price', 'target', 'stop', 'shares'}
        self.trades = []
        self.equity_curve = []
        self.capital = initial_capital
        
    def run_backtest(self,
                    symbols: List[str],
                    start_date: str,
                    end_date: str,
                    max_positions: int = 5) -> Dict:
        """백테스트 실행"""
        
        print(f"\n{'='*60}")
        print(f"📈 M-Strategy + AI v3 (Fibonacci + ATR) 백테스트")
        print(f"{'='*60}")
        print(f"기간: {start_date} ~ {end_date}")
        print(f"초기자본: ₩{self.initial_capital:,.0f}")
        print(f"리밸런싱: {self.rebalance_days}일")
        print(f"최대포지션: {max_positions}개")
        print(f"손익비 필터: 1:{self.strategy.risk_reward_ratio}")
        print(f"{'='*60}\n")
        
        current_date = datetime.strptime(start_date, '%Y-%m-%d')
        end_dt = datetime.strptime(end_date, '%Y-%m-%d')
        rebalance_count = 0
        
        while current_date <= end_dt:
            # 거래일 확인
            test_df = fdr.get_price('005930', 
                                         start=(current_date - timedelta(days=5)).strftime('%Y-%m-%d'),
                                         end=current_date.strftime('%Y-%m-%d'))
            test_df = normalize_columns(test_df)
            if len(test_df) == 0 or test_df['Date'].iloc[-1].strftime('%Y-%m-%d') != current_date.strftime('%Y-%m-%d'):
                current_date += timedelta(days=1)
                continue
            
            # 리밸런싱일
            if rebalance_count == 0 or (current_date - self.last_rebalance).days >= self.rebalance_days:
                self._rebalance(current_date, symbols, max_positions)
                self.last_rebalance = current_date
                rebalance_count += 1
                print(f"\n📅 {current_date.strftime('%Y-%m-%d')} 리밸런싱... ({rebalance_count})")
            
            # 포지션 모니터링 (손절/목표가 체크)
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
                'primary_threshold': self.strategy.primary_threshold,
                'meta_threshold': self.strategy.meta_threshold,
                'risk_reward_ratio': self.strategy.risk_reward_ratio,
                'atr_multiplier': self.strategy.atr_multiplier,
                'fib_entry_level': self.strategy.fib_entry_level,
                'fib_target_level': self.strategy.fib_target_level
            }
        }
        
        self._print_results(results)
        return results
    
    def _rebalance(self, date: datetime, symbols: List[str], max_positions: int):
        """리밸런싱"""
        # 기존 포지션 정리
        self.portfolio = {}
        
        # 새 종목 선정
        selected = self.strategy.scan_and_select(symbols, date, max_positions)
        
        if not selected:
            return
        
        # 자산 분배
        capital_per_stock = self.capital / len(selected)
        
        for stock in selected:
            shares = int(capital_per_stock / stock['entry_price'])
            if shares > 0:
                self.portfolio[stock['symbol']] = {
                    'entry_date': date.strftime('%Y-%m-%d'),
                    'entry_price': stock['entry_price'],
                    'target_price': stock['target_price'],
                    'stop_loss': stock['stop_loss'],
                    'shares': shares,
                    'rr_ratio': stock['rr_ratio']
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
                
                # 최대 보유기간 (30일)
                entry_date = datetime.strptime(pos['entry_date'], '%Y-%m-%d')
                if (date - entry_date).days >= 30:
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
                        'rr_ratio': pos['rr_ratio']
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


def main():
    # 전략 설정
    strategy = FibonacciATRStrategy(
        primary_threshold=60.0,
        meta_threshold=65.0,
        risk_reward_ratio=2.0,      # 1:2 손익비
        atr_multiplier=2.0,          # ATR × 2
        fib_entry_level=0.5,         # 50% retracement
        fib_target_level=1.618,      # 161.8% extension
        rsi_min=35.0,
        rsi_max=75.0,
        volume_threshold=0.8,
        adx_threshold=15.0
    )
    
    # 학습 데이터
    training_symbols = [
        '005930', '000660', '051910', '005380', '035720',
        '068270', '207940', '006400', '000270', '012330',
        '005490', '028260', '105560', '018260', '032830'
    ]
    
    # 학습 (2024년 데이터)
    strategy.train(training_symbols, '2024-01-01', '2024-12-31')
    
    # 백테스트 종목 (대형주 중심 - 속도 개선)
    backtest_symbols = training_symbols + [f"{i:06d}" for i in range(100, 1000, 50)]
    
    # 백테스트 실행
    engine = BacktestEngine(
        strategy=strategy,
        initial_capital=100_000_000,
        rebalance_days=30
    )
    
    results = engine.run_backtest(
        symbols=backtest_symbols,
        start_date='2025-01-01',
        end_date='2026-03-18',
        max_positions=5
    )
    
    # 결과 저장
    output_dir = './reports/m_strategy'
    os.makedirs(output_dir, exist_ok=True)
    
    timestamp = datetime.now().strftime('%Y%m%d_%H%M')
    filename = f'{output_dir}/m_ai_v3_fib_atr_backtest_{timestamp}.json'
    
    with open(filename, 'w', encoding='utf-8') as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    
    print(f"\n💾 결과 저장: {filename}")


if __name__ == '__main__':
    main()
