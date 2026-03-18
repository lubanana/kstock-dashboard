#!/usr/bin/env python3
"""
Advanced Stock Predictor with Multi-Stock Training, Hyperparameter Tuning, and External Data
고급 주가 예측 시스템
"""

import sys
import warnings
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from typing import Optional, Dict, List, Tuple

warnings.filterwarnings('ignore')

from sklearn.preprocessing import RobustScaler
from sklearn.ensemble import RandomForestClassifier, GradientBoostingClassifier
from sklearn.metrics import accuracy_score

from fdr_wrapper import FDRWrapper


class AdvancedStockPredictor:
    """고급 주가 예측 시스템"""
    
    def __init__(self):
        self.fdr = FDRWrapper()
        self.params = {
            'rf_n_estimators': 300,
            'rf_max_depth': 20,
            'rf_min_samples_split': 3,
            'lookback': 20,
            'threshold': 0.55
        }
        self.models = {}
        self.scaler = RobustScaler()
        
    def get_training_stocks(self) -> List[str]:
        """멀티 종목 학습용 대형주 리스트"""
        return [
            '005930', '000660', '051910', '005380', '035720',
            '068270', '207940', '006400', '000270', '012330',
            '005490', '028260', '105560', '018260', '032830',
        ]
    
    def calculate_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        """고급 기술적 지표"""
        df = df.copy()
        
        # 이동평균
        for window in [5, 10, 20, 60]:
            df[f'MA{window}'] = df['close'].rolling(window=window).mean()
            df[f'EMA{window}'] = df['close'].ewm(span=window, adjust=False).mean()
            df[f'Close_MA{window}_ratio'] = df['close'] / df[f'MA{window}'] - 1
        
        df['MA5_MA20_ratio'] = df['MA5'] / df['MA20'] - 1
        df['MA20_MA60_ratio'] = df['MA20'] / df['MA60'] - 1
        df['MA5_slope'] = df['MA5'].diff(5) / df['MA5'].shift(5)
        
        # RSI
        for window in [7, 14, 21]:
            delta = df['close'].diff()
            gain = delta.where(delta > 0, 0).rolling(window=window).mean()
            loss = (-delta.where(delta < 0, 0)).rolling(window=window).mean()
            df[f'RSI{window}'] = 100 - (100 / (1 + gain / (loss + 1e-10)))
        
        # MACD
        exp1 = df['close'].ewm(span=12, adjust=False).mean()
        exp2 = df['close'].ewm(span=26, adjust=False).mean()
        df['MACD'] = exp1 - exp2
        df['MACD_signal'] = df['MACD'].ewm(span=9, adjust=False).mean()
        df['MACD_hist'] = df['MACD'] - df['MACD_signal']
        df['MACD_cross'] = np.where(df['MACD'] > df['MACD_signal'], 1, -1)
        
        # 볼린저
        ma20 = df['close'].rolling(window=20).mean()
        std20 = df['close'].rolling(window=20).std()
        df['BB_upper'] = ma20 + std20 * 2
        df['BB_lower'] = ma20 - std20 * 2
        df['BB_position'] = (df['close'] - df['BB_lower']) / (df['BB_upper'] - df['BB_lower'] + 1e-10)
        df['BB_width'] = (df['BB_upper'] - df['BB_lower']) / ma20
        
        # 거래량
        df['Volume_MA20'] = df['volume'].rolling(window=20).mean()
        df['Volume_ratio'] = df['volume'] / df['Volume_MA20']
        df['Volume_spike'] = (df['Volume_ratio'] > 2).astype(int)
        
        # 변동성
        high_low = df['high'] - df['low']
        high_close = np.abs(df['high'] - df['close'].shift())
        low_close = np.abs(df['low'] - df['close'].shift())
        df['ATR14'] = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1).rolling(14).mean()
        df['ATR_ratio'] = df['ATR14'] / df['close']
        
        # 추세
        df['Trend_5d'] = (df['close'] > df['close'].shift(5)).astype(int)
        df['Trend_20d'] = (df['close'] > df['close'].shift(20)).astype(int)
        df['Return_5d'] = df['close'].pct_change(5)
        df['Return_20d'] = df['close'].pct_change(20)
        
        df['Price_up'] = (df['close'] > df['close'].shift(1)).astype(int)
        df['Consecutive_up'] = df['Price_up'].groupby((df['Price_up'] != df['Price_up'].shift()).cumsum()).cumsum()
        df['Consecutive_down'] = (1 - df['Price_up']).groupby(((1 - df['Price_up']) != (1 - df['Price_up']).shift()).cumsum()).cumsum()
        
        # 캔들스틱
        df['Body_pct'] = (df['close'] - df['open']) / df['close']
        df['Upper_shadow'] = (df['high'] - np.maximum(df['open'], df['close'])) / df['close']
        df['Lower_shadow'] = (np.minimum(df['open'], df['close']) - df['low']) / df['close']
        
        # 모멘텀
        df['Momentum_1d'] = df['close'].pct_change(1)
        df['Momentum_5d'] = df['close'].pct_change(5)
        df['Momentum_accel'] = df['Momentum_1d'] - df['Momentum_1d'].shift(1)
        
        # 52주
        df['Price_vs_52w_high'] = df['close'] / df['close'].rolling(252).max()
        df['Price_vs_52w_low'] = df['close'] / df['close'].rolling(252).min()
        
        return df
    
    def collect_multi_stock_data(self, target_symbol: str) -> Tuple[np.ndarray, np.ndarray]:
        """멀티 종목 데이터 수집"""
        print(f"\n📊 멀티 종목 데이터 수집 중...")
        
        training_stocks = self.get_training_stocks()
        all_X, all_y = [], []
        
        for symbol in training_stocks:
            try:
                df = self.fdr.get_price(symbol, min_days=400)
                if df is None or len(df) < 200:
                    continue
                
                if 'date' in df.columns:
                    df['date'] = pd.to_datetime(df['date'])
                
                df = self.calculate_indicators(df)
                df = df.dropna()
                
                if len(df) < 100:
                    continue
                
                X, y = self._extract_features(df)
                
                if len(X) > 0:
                    all_X.append(X)
                    all_y.append(y)
                    print(f"   ✅ {symbol}: {len(X)}개 샘플")
                
            except Exception as e:
                continue
        
        if not all_X:
            return None, None
        
        X_combined = np.vstack(all_X)
        y_combined = np.concatenate(all_y)
        
        print(f"\n📈 총 학습 데이터: {len(X_combined)}개 샘플 (약 {len(X_combined)/250:.0f}년치)")
        return X_combined, y_combined
    
    def _extract_features(self, df: pd.DataFrame) -> Tuple[np.ndarray, np.ndarray]:
        """피처 추출"""
        features = [
            'Close_MA5_ratio', 'Close_MA10_ratio', 'Close_MA20_ratio', 'Close_MA60_ratio',
            'MA5_MA20_ratio', 'MA20_MA60_ratio', 'MA5_slope',
            'RSI7', 'RSI14', 'RSI21',
            'MACD', 'MACD_hist', 'MACD_cross',
            'BB_position', 'BB_width',
            'Volume_ratio', 'Volume_spike',
            'ATR_ratio',
            'Trend_5d', 'Trend_20d', 'Return_5d', 'Return_20d',
            'Consecutive_up', 'Consecutive_down',
            'Body_pct', 'Upper_shadow', 'Lower_shadow',
            'Momentum_1d', 'Momentum_5d', 'Momentum_accel',
            'Price_vs_52w_high', 'Price_vs_52w_low'
        ]
        
        feature_cols = [f for f in features if f in df.columns]
        
        X, y = [], []
        lookback = self.params['lookback']
        
        for i in range(lookback, len(df)):
            window = df[feature_cols].iloc[i-lookback:i]
            if window.isnull().any().any():
                continue
            
            feat = np.concatenate([
                window.mean().values,
                window.std().values,
                window.iloc[-1].values
            ])
            X.append(feat)
            y.append(1 if df['close'].iloc[i] > df['close'].iloc[i-1] else 0)
        
        return np.array(X), np.array(y)
    
    def train_models(self, X: np.ndarray, y: np.ndarray):
        """모델 학습"""
        print(f"\n🤖 모델 학습 중...")
        print(f"   학습 데이터: {len(X)}개")
        print(f"   클래스 분포: 상승={sum(y)}, 하강={len(y)-sum(y)}")
        
        # 분할
        split = int(len(X) * 0.8)
        X_train, X_test = X[:split], X[split:]
        y_train, y_test = y[:split], y[split:]
        
        # 스케일링
        X_train_scaled = self.scaler.fit_transform(X_train)
        X_test_scaled = self.scaler.transform(X_test)
        
        # Random Forest
        print(f"   🌲 Random Forest 학습 중...")
        rf = RandomForestClassifier(
            n_estimators=self.params['rf_n_estimators'],
            max_depth=self.params['rf_max_depth'],
            min_samples_split=self.params['rf_min_samples_split'],
            class_weight='balanced',
            random_state=42,
            n_jobs=-1
        )
        rf.fit(X_train_scaled, y_train)
        rf_acc = accuracy_score(y_test, rf.predict(X_test_scaled))
        print(f"      정확도: {rf_acc*100:.1f}%")
        
        # Gradient Boosting
        print(f"   🚀 Gradient Boosting 학습 중...")
        gb = GradientBoostingClassifier(
            n_estimators=200,
            learning_rate=0.05,
            max_depth=5,
            random_state=42
        )
        gb.fit(X_train_scaled, y_train)
        gb_acc = accuracy_score(y_test, gb.predict(X_test_scaled))
        print(f"      정확도: {gb_acc*100:.1f}%")
        
        self.models = {'rf': rf, 'gb': gb}
        
        return {'rf_acc': rf_acc, 'gb_acc': gb_acc}
    
    def predict(self, symbol: str):
        """예측"""
        print(f"\n{'='*60}")
        print(f"🔮 {symbol} 고급 예측")
        print(f"{'='*60}")
        
        # 1. 멀티 종목 데이터로 학습
        X, y = self.collect_multi_stock_data(symbol)
        if X is None:
            print("❌ 데이터 수집 실패")
            return None
        
        metrics = self.train_models(X, y)
        
        # 2. 타겟 종목 예측
        df = self.fdr.get_price(symbol, min_days=400)
        if df is None:
            return None
        
        if 'date' in df.columns:
            df['date'] = pd.to_datetime(df['date'])
        
        df = self.calculate_indicators(df)
        df = df.dropna()
        
        print(f"   타겟 종목 데이터: {len(df)}일")
        
        if len(df) < 50:
            print(f"❌ 데이터 부족: {len(df)}일")
            return None
        
        X_target, _ = self._extract_features(df)
        if len(X_target) == 0:
            print("❌ 피처 추출 실패")
            return None
        
        X_target_scaled = self.scaler.transform(X_target[-1:])
        
        # 예측
        rf_pred = self.models['rf'].predict(X_target_scaled)[0]
        rf_proba = self.models['rf'].predict_proba(X_target_scaled)[0]
        gb_pred = self.models['gb'].predict(X_target_scaled)[0]
        gb_proba = self.models['gb'].predict_proba(X_target_scaled)[0]
        
        # 앙상블
        avg_proba = (rf_proba + gb_proba) / 2
        final_pred = 1 if avg_proba[1] > self.params['threshold'] else 0
        confidence = max(avg_proba)
        
        current_price = df['close'].iloc[-1]
        prediction_date = (datetime.now() + timedelta(days=1)).strftime('%Y-%m-%d')
        
        # 결과 출력
        print(f"\n{'='*60}")
        print(f"📊 {symbol} 예측 결과")
        print(f"{'='*60}")
        print(f"📅 예측일: {prediction_date}")
        print(f"💰 현재가: {current_price:,.0f}원")
        print(f"📈 예상 방향: {'상승' if final_pred == 1 else '하띋'}")
        print(f"🎯 확신도: {confidence*100:.1f}%")
        print(f"\n📊 모델 상세:")
        print(f"   Random Forest: {'상승' if rf_pred == 1 else '하띋'} ({rf_proba[1]*100:.1f}%)")
        print(f"   Gradient Boosting: {'상승' if gb_pred == 1 else '하띋'} ({gb_proba[1]*100:.1f}%)")
        print(f"   검증 정확도: RF={metrics['rf_acc']*100:.1f}%, GB={metrics['gb_acc']*100:.1f}%")
        
        if confidence >= self.params['threshold']:
            print(f"\n   ✅ 확신도 {self.params['threshold']*100:.0f}% 이상 - 신호 유효")
        else:
            print(f"\n   ⚠️ 확신도 낮음 - 관망 권장")
        
        print(f"{'='*60}\n")
        
        return {
            'symbol': symbol,
            'direction': '상승' if final_pred == 1 else '하띋',
            'confidence': confidence,
            'price': current_price,
            'date': prediction_date
        }


def main():
    if len(sys.argv) < 2:
        print("사용법: python3 advanced_predictor.py [종목코드]")
        print("예시: python3 advanced_predictor.py 005930")
        sys.exit(1)
    
    symbol = sys.argv[1].zfill(6)
    
    predictor = AdvancedStockPredictor()
    result = predictor.predict(symbol)
    
    if result is None:
        print(f"❌ {symbol} 예측 실패")
        sys.exit(1)


if __name__ == '__main__':
    main()
