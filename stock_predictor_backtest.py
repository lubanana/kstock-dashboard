#!/usr/bin/env python3
"""
Stock Price Predictor V2 - Backtest System
주가 예측 모델 백테스팅 시스템
"""

import sys
import warnings
import numpy as np
import pandas as pd
from datetime import datetime
from typing import Optional
from dataclasses import dataclass

warnings.filterwarnings('ignore')

from sklearn.preprocessing import RobustScaler
from sklearn.ensemble import RandomForestRegressor, GradientBoostingRegressor
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score, accuracy_score

from fdr_wrapper import FDRWrapper


@dataclass
class BacktestResult:
    symbol: str
    total_predictions: int
    mae: float
    rmse: float
    r2: float
    direction_accuracy: float
    buy_hold_return: float
    strategy_return: float


class StockPredictorBacktest:
    def __init__(self):
        self.fdr = FDRWrapper()
        self.features = self._get_features()
    
    def _get_features(self):
        return [
            'Close_MA5_ratio', 'Close_MA20_ratio', 'Close_MA60_ratio',
            'MA5_MA20_ratio', 'MA20_MA60_ratio',
            'RSI14', 'RSI14_change',
            'MACD', 'MACD_hist', 'MACD_change',
            'BB_position_20',
            'Volume_ratio', 'Volume_change',
            'ATR14_ratio', 'Daily_range',
            'Trend_5d', 'Trend_20d', 'Return_5d', 'Return_20d',
            'Consecutive_up', 'Consecutive_down',
            'Body_pct', 'Is_bullish',
            'Momentum_1d', 'Momentum_5d', 'Momentum_accel'
        ]
    
    def fetch_data(self, symbol: str, days: int = 500):
        try:
            df = self.fdr.get_price(symbol, min_days=days)
            if df is None or len(df) < 100:
                return None
            if 'date' in df.columns:
                df['date'] = pd.to_datetime(df['date'])
                df = df.sort_values('date')
            return df.reset_index(drop=True)
        except:
            return None
    
    def calculate_indicators(self, df: pd.DataFrame):
        df = df.copy()
        
        # Moving averages
        for window in [5, 20, 60]:
            df[f'MA{window}'] = df['close'].rolling(window=window).mean()
            df[f'Close_MA{window}_ratio'] = df['close'] / df[f'MA{window}'] - 1
        
        df['MA5_MA20_ratio'] = df['MA5'] / df['MA20'] - 1
        df['MA20_MA60_ratio'] = df['MA20'] / df['MA60'] - 1
        
        # RSI
        delta = df['close'].diff()
        gain = delta.where(delta > 0, 0).rolling(window=14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
        df['RSI14'] = 100 - (100 / (1 + gain / (loss + 1e-10)))
        df['RSI14_change'] = df['RSI14'].diff()
        
        # MACD
        exp1 = df['close'].ewm(span=12, adjust=False).mean()
        exp2 = df['close'].ewm(span=26, adjust=False).mean()
        df['MACD'] = exp1 - exp2
        df['MACD_signal'] = df['MACD'].ewm(span=9, adjust=False).mean()
        df['MACD_hist'] = df['MACD'] - df['MACD_signal']
        df['MACD_change'] = df['MACD'].diff()
        
        # Bollinger
        ma20 = df['close'].rolling(window=20).mean()
        std20 = df['close'].rolling(window=20).std()
        df['BB_position_20'] = (df['close'] - (ma20 - std20*2)) / ((ma20 + std20*2) - (ma20 - std20*2) + 1e-10)
        
        # Volume
        df['Volume_MA20'] = df['volume'].rolling(window=20).mean()
        df['Volume_ratio'] = df['volume'] / df['Volume_MA20']
        df['Volume_change'] = df['volume'].pct_change()
        
        # Volatility
        high_low = df['high'] - df['low']
        high_close = np.abs(df['high'] - df['close'].shift())
        low_close = np.abs(df['low'] - df['close'].shift())
        df['ATR14'] = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1).rolling(14).mean()
        df['ATR14_ratio'] = df['ATR14'] / df['close']
        df['Daily_range'] = (df['high'] - df['low']) / df['close']
        
        # Trend
        df['Trend_5d'] = (df['close'] > df['close'].shift(5)).astype(int)
        df['Trend_20d'] = (df['close'] > df['close'].shift(20)).astype(int)
        df['Return_5d'] = df['close'].pct_change(5)
        df['Return_20d'] = df['close'].pct_change(20)
        
        # Consecutive
        df['Price_up'] = (df['close'] > df['close'].shift(1)).astype(int)
        df['Consecutive_up'] = df['Price_up'].groupby((df['Price_up'] != df['Price_up'].shift()).cumsum()).cumsum()
        df['Consecutive_down'] = (1 - df['Price_up']).groupby(((1 - df['Price_up']) != (1 - df['Price_up']).shift()).cumsum()).cumsum()
        
        # Candlestick
        df['Body_pct'] = (df['close'] - df['open']) / df['close']
        df['Is_bullish'] = (df['close'] > df['open']).astype(int)
        
        # Momentum
        df['Momentum_1d'] = df['close'].pct_change(1)
        df['Momentum_5d'] = df['close'].pct_change(5)
        df['Momentum_accel'] = df['Momentum_1d'] - df['Momentum_1d'].shift(1)
        
        return df
    
    def prepare_features(self, df: pd.DataFrame, lookback: int = 20):
        window = df[self.features].iloc[-lookback:]
        return np.concatenate([window.mean().values, window.std().values, window.iloc[-1].values])
    
    def backtest(self, symbol: str, train_days: int = 100, step_days: int = 5):
        print(f"\n{'='*60}")
        print(f"🔍 {symbol} 백테스트")
        print(f"{'='*60}")
        
        df = self.fetch_data(symbol, days=400)
        if df is None:
            return None
        
        df = self.calculate_indicators(df).dropna().reset_index(drop=True)
        
        if len(df) < 150:
            print(f"❌ 데이터 부족: {len(df)}일")
            return None
        
        print(f"📊 총 데이터: {len(df)}일")
        
        predictions = []
        actuals = []
        prices = []
        
        # Walk-forward
        start_idx = train_days
        
        for current_idx in range(start_idx, len(df) - 1, step_days):
            train_df = df.iloc[:current_idx].copy()
            train_df['target'] = np.log(train_df['close'].shift(-1) / train_df['close']) * 100
            train_clean = train_df[self.features + ['target']].dropna()
            
            if len(train_clean) < 50:
                continue
            
            X_train, y_train = [], []
            for i in range(20, len(train_clean)):
                w = train_clean[self.features].iloc[i-20:i]
                X_train.append(np.concatenate([w.mean().values, w.std().values, w.iloc[-1].values]))
                y_train.append(train_clean['target'].iloc[i])
            
            X_train = np.array(X_train)
            y_train = np.array(y_train)
            
            scaler = RobustScaler()
            X_train_scaled = scaler.fit_transform(X_train)
            
            rf = RandomForestRegressor(n_estimators=100, max_depth=15, random_state=42, n_jobs=-1)
            gb = GradientBoostingRegressor(n_estimators=100, learning_rate=0.05, max_depth=5, random_state=42)
            rf.fit(X_train_scaled, y_train)
            gb.fit(X_train_scaled, y_train)
            
            # Predict next days
            for offset in range(step_days):
                test_idx = current_idx + offset
                if test_idx >= len(df) - 1:
                    break
                
                test_df = df.iloc[:test_idx]
                if len(test_df) < 20:
                    continue
                
                X_test = self.prepare_features(test_df, 20).reshape(1, -1)
                X_test_scaled = scaler.transform(X_test)
                
                pred = (rf.predict(X_test_scaled)[0] + gb.predict(X_test_scaled)[0]) / 2
                actual = np.log(df['close'].iloc[test_idx + 1] / df['close'].iloc[test_idx]) * 100
                
                predictions.append(pred)
                actuals.append(actual)
                prices.append(df['close'].iloc[test_idx])
        
        if len(predictions) < 10:
            print(f"❌ 예측 부족: {len(predictions)}개")
            return None
        
        predictions = np.array(predictions)
        actuals = np.array(actuals)
        prices = np.array(prices)
        
        # Metrics
        mae = mean_absolute_error(actuals, predictions)
        rmse = np.sqrt(mean_squared_error(actuals, predictions))
        r2 = r2_score(actuals, predictions)
        direction_acc = accuracy_score(np.sign(actuals), np.sign(predictions))
        
        # Returns
        buy_hold = (prices[-1] / prices[0] - 1) * 100
        
        # Strategy: 예측 > 0 이면 매수, 아니면 현금
        strategy_returns = []
        for pred, actual in zip(predictions, actuals):
            if pred > 0:  # 상승 예상
                strategy_returns.append(actual)
            else:  # 하띋 예상 → 현금 보유
                strategy_returns.append(0)
        
        strategy_cum = np.sum(strategy_returns)
        
        print(f"✅ 완료! 예측 {len(predictions)}개")
        
        return BacktestResult(
            symbol=symbol,
            total_predictions=len(predictions),
            mae=mae,
            rmse=rmse,
            r2=r2,
            direction_accuracy=direction_acc,
            buy_hold_return=buy_hold,
            strategy_return=strategy_cum
        )
    
    def print_result(self, result: BacktestResult):
        print(f"\n{'='*60}")
        print(f"📊 {result.symbol} 백테스트 결과")
        print(f"{'='*60}")
        print(f"총 예측 횟수: {result.total_predictions}회")
        print(f"\n📈 예측 정확도:")
        print(f"   MAE (평균절대오차): {result.mae:.3f}%")
        print(f"   RMSE (제곱근평균제곱오차): {result.rmse:.3f}%")
        print(f"   R² (설명력): {result.r2:.3f}")
        print(f"   방향정확도: {result.direction_accuracy*100:.1f}%")
        print(f"\n💰 수익률 비교:")
        print(f"   Buy & Hold: {result.buy_hold_return:+.2f}%")
        print(f"   전략 수익률: {result.strategy_return:+.2f}%")
        
        if result.strategy_return > result.buy_hold_return:
            print(f"   ✅ 전략이 Buy & Hold보다 {result.strategy_return - result.buy_hold_return:.2f}% 우수")
        print(f"{'='*60}\n")


def main():
    if len(sys.argv) < 2:
        print("사용법: python3 stock_predictor_backtest.py [종목코드]")
        print("예시: python3 stock_predictor_backtest.py 005930")
        sys.exit(1)
    
    symbol = sys.argv[1].zfill(6)
    
    bt = StockPredictorBacktest()
    result = bt.backtest(symbol)
    
    if result:
        bt.print_result(result)
    else:
        print(f"❌ {symbol} 백테스트 실패")
        sys.exit(1)


if __name__ == '__main__':
    main()
