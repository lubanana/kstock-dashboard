#!/usr/bin/env python3
"""
K-Stock Price Predictor
종목 코드 입력 → 내일 예상 종가 및 등락률 예측

사용법:
    python3 stock_price_predictor.py 005930  # 삼성전자 예측
    python3 stock_price_predictor.py 000660  # SK하이닉스 예측
"""

import sys
import warnings
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from typing import Optional, Tuple, Dict

# Suppress warnings
warnings.filterwarnings('ignore')

# Technical analysis
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import mean_absolute_error
from sklearn.ensemble import RandomForestRegressor

# Import our wrapper
from fdr_wrapper import FDRWrapper


class StockPricePredictor:
    """Stock price prediction using technical indicators and ML"""
    
    def __init__(self):
        self.fdr = FDRWrapper()
        self.scaler = StandardScaler()
        self.model = None
        self.features = []
    
    def fetch_data(self, symbol: str, days: int = 730) -> Optional[pd.DataFrame]:
        """Fetch historical stock data using fdr_wrapper"""
        print(f"📊 {symbol} 데이터 수집 중...")
        
        try:
            # Get data from fdr_wrapper
            df = self.fdr.get_price(symbol, min_days=days)
            
            if df is None or len(df) < 60:
                print(f"❌ 데이터 수집 실패: {symbol}")
                return None
            
            # Ensure required columns exist
            required_cols = ['open', 'high', 'low', 'close', 'volume']
            for col in required_cols:
                if col not in df.columns:
                    print(f"❌ 필수 컬럼 누락: {col}")
                    return None
            
            print(f"✅ {len(df)}일 데이터 수집 완료 ({df.index[0]} ~ {df.index[-1]})")
            return df.sort_index()
            
        except Exception as e:
            print(f"❌ 데이터 수집 오류: {e}")
            return None
    
    def calculate_technical_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        """Calculate technical indicators"""
        print("📈 기술적 지표 계산 중...")
        
        df = df.copy()
        
        # 1. 이동평균선 (Moving Averages)
        df['MA5'] = df['close'].rolling(window=5).mean()
        df['MA20'] = df['close'].rolling(window=20).mean()
        df['MA60'] = df['close'].rolling(window=60).mean()
        
        # MA 간격
        df['MA5_MA20_gap'] = df['MA5'] - df['MA20']
        df['MA20_MA60_gap'] = df['MA20'] - df['MA60']
        
        # 2. RSI (Relative Strength Index) - 14일
        delta = df['close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
        rs = gain / loss
        df['RSI14'] = 100 - (100 / (1 + rs))
        
        # 3. MACD
        exp1 = df['close'].ewm(span=12, adjust=False).mean()
        exp2 = df['close'].ewm(span=26, adjust=False).mean()
        df['MACD'] = exp1 - exp2
        df['MACD_signal'] = df['MACD'].ewm(span=9, adjust=False).mean()
        df['MACD_hist'] = df['MACD'] - df['MACD_signal']
        
        # 4. 볼린저 밴드 (Bollinger Bands) - 20일
        df['BB_middle'] = df['close'].rolling(window=20).mean()
        bb_std = df['close'].rolling(window=20).std()
        df['BB_upper'] = df['BB_middle'] + (bb_std * 2)
        df['BB_lower'] = df['BB_middle'] - (bb_std * 2)
        df['BB_position'] = (df['close'] - df['BB_lower']) / (df['BB_upper'] - df['BB_lower'])
        
        # 5. 거래량 지표
        df['Volume_MA5'] = df['volume'].rolling(window=5).mean()
        df['Volume_MA20'] = df['volume'].rolling(window=20).mean()
        df['Volume_ratio'] = df['volume'] / df['Volume_MA20']
        df['Volume_change'] = df['volume'].pct_change()
        
        # 6. 가격 변동률
        df['Price_change'] = df['close'].pct_change()
        df['Price_change_1d'] = df['close'].pct_change(periods=1)
        df['Price_change_5d'] = df['close'].pct_change(periods=5)
        df['Price_change_20d'] = df['close'].pct_change(periods=20)
        
        # 7. 변동성 (ATR - Average True Range)
        high_low = df['high'] - df['low']
        high_close = np.abs(df['high'] - df['close'].shift())
        low_close = np.abs(df['low'] - df['close'].shift())
        ranges = pd.concat([high_low, high_close, low_close], axis=1)
        true_range = np.max(ranges, axis=1)
        df['ATR14'] = true_range.rolling(14).mean()
        df['ATR_ratio'] = df['ATR14'] / df['close']
        
        # 8. 추세 지표
        df['Trend_5d'] = np.where(df['close'] > df['close'].shift(5), 1, -1)
        df['Trend_20d'] = np.where(df['close'] > df['close'].shift(20), 1, -1)
        
        # 9. 캔들스틱 패턴
        df['Body'] = df['close'] - df['open']
        df['Upper_shadow'] = df['high'] - np.maximum(df['open'], df['close'])
        df['Lower_shadow'] = np.minimum(df['open'], df['close']) - df['low']
        df['Body_ratio'] = np.abs(df['Body']) / (df['high'] - df['low'] + 0.001)
        
        # Feature list
        self.features = [
            'MA5', 'MA20', 'MA60', 'MA5_MA20_gap', 'MA20_MA60_gap',
            'RSI14', 'MACD', 'MACD_signal', 'MACD_hist',
            'BB_position', 'BB_upper', 'BB_lower',
            'Volume_ratio', 'Volume_change',
            'Price_change_1d', 'Price_change_5d', 'Price_change_20d',
            'ATR_ratio', 'Trend_5d', 'Trend_20d',
            'Body_ratio', 'Upper_shadow', 'Lower_shadow'
        ]
        
        print(f"✅ {len(self.features)}개 기술적 지표 계산 완료")
        return df
    
    def prepare_training_data(self, df: pd.DataFrame, lookback_days: int = 20) -> Tuple[np.ndarray, np.ndarray]:
        """Prepare training data with lookback window"""
        
        # Drop NaN values
        df_clean = df[self.features + ['close']].dropna()
        
        if len(df_clean) < lookback_days + 30:
            raise ValueError(f"데이터가 부족합니다. 최소 {lookback_days + 30}일 필요.")
        
        X, y = [], []
        
        for i in range(lookback_days, len(df_clean) - 1):
            # Feature: past lookback_days technical indicators
            X.append(df_clean[self.features].iloc[i-lookback_days:i].values.flatten())
            # Target: next day's close price
            y.append(df_clean['close'].iloc[i+1])
        
        return np.array(X), np.array(y)
    
    def train_model(self, X: np.ndarray, y: np.ndarray) -> None:
        """Train the prediction model"""
        print("🤖 머신러닝 모델 학습 중...")
        print("   사용 모델: Random Forest Regressor")
        
        # Split data (use last 20% for validation)
        split_idx = int(len(X) * 0.8)
        X_train, X_val = X[:split_idx], X[split_idx:]
        y_train, y_val = y[:split_idx], y[split_idx:]
        
        # Scale features
        X_train_scaled = self.scaler.fit_transform(X_train)
        X_val_scaled = self.scaler.transform(X_val)
        
        # Use Random Forest
        self.model = RandomForestRegressor(
            n_estimators=200,
            max_depth=10,
            min_samples_split=5,
            min_samples_leaf=3,
            random_state=42,
            n_jobs=-1
        )
        
        # Train
        self.model.fit(X_train_scaled, y_train)
        
        # Evaluate
        train_pred = self.model.predict(X_train_scaled)
        val_pred = self.model.predict(X_val_scaled)
        
        train_mae = mean_absolute_error(y_train, train_pred)
        val_mae = mean_absolute_error(y_val, val_pred)
        
        print(f"✅ 학습 완료")
        print(f"   Train MAE: {train_mae:,.0f}원")
        print(f"   Val MAE: {val_mae:,.0f}원")
    
    def predict_next_day(self, df: pd.DataFrame, lookback_days: int = 20) -> Dict:
        """Predict next day's closing price"""
        
        # Get last lookback_days features
        last_data = df[self.features].iloc[-lookback_days:].values.flatten().reshape(1, -1)
        last_data_scaled = self.scaler.transform(last_data)
        
        # Predict
        predicted_price = self.model.predict(last_data_scaled)[0]
        
        # Get current price
        current_price = df['close'].iloc[-1]
        
        # Calculate change rate
        change_rate = ((predicted_price - current_price) / current_price) * 100
        
        # Feature importance
        feature_importance = None
        if hasattr(self.model, 'feature_importances_'):
            importance = self.model.feature_importances_
            # Aggregate importance by feature type
            n_features = len(self.features)
            aggregated = []
            for i in range(n_features):
                avg_imp = np.mean(importance[i::n_features])
                aggregated.append(avg_imp)
            
            feature_importance = sorted(
                zip(self.features, aggregated),
                key=lambda x: x[1],
                reverse=True
            )[:5]
        
        # Get prediction date (next business day)
        last_date = pd.to_datetime(df['date'].iloc[-1]) if 'date' in df.columns else datetime.now()
        prediction_date = last_date + timedelta(days=1)
        # Skip weekends
        while prediction_date.weekday() >= 5:  # 5=Saturday, 6=Sunday
            prediction_date += timedelta(days=1)
        
        return {
            'current_price': current_price,
            'predicted_price': predicted_price,
            'change_rate': change_rate,
            'prediction_date': prediction_date.strftime('%Y-%m-%d'),
            'feature_importance': feature_importance
        }
    
    def predict(self, symbol: str) -> Optional[Dict]:
        """Main prediction pipeline"""
        print("=" * 60)
        print(f"🔮 {symbol} 주가 예측 시작")
        print("=" * 60)
        
        # 1. Fetch data
        df = self.fetch_data(symbol)
        if df is None:
            return None
        
        # 2. Calculate technical indicators
        df = self.calculate_technical_indicators(df)
        
        # 3. Prepare training data
        try:
            X, y = self.prepare_training_data(df)
            print(f"📚 학습 데이터: {len(X)}개 샘플")
        except ValueError as e:
            print(f"❌ {e}")
            return None
        
        # 4. Train model
        self.train_model(X, y)
        
        # 5. Predict
        result = self.predict_next_day(df)
        
        return result
    
    def print_prediction(self, symbol: str, result: Dict):
        """Print prediction result in clean format"""
        print()
        print("=" * 60)
        print(f"📊 {symbol} 예측 결과")
        print("=" * 60)
        print(f"📅 예측 대상일: {result['prediction_date']}")
        print(f"💰 현재 종가: {result['current_price']:,.0f}원")
        print(f"🔮 예상 종가: {result['predicted_price']:,.0f}원")
        
        # Change rate with color indicator
        change = result['change_rate']
        if change > 0:
            arrow = "📈"
            status = "상승 예상"
        elif change < 0:
            arrow = "📉"
            status = "하락 예상"
        else:
            arrow = "➡️"
            status = "보합 예상"
        
        print(f"{arrow} 예상 등락률: {change:+.2f}% ({status})")
        print("=" * 60)
        
        # Feature importance
        if result['feature_importance']:
            print("\n🔍 주요 예측 요인:")
            for i, (feature, importance) in enumerate(result['feature_importance'], 1):
                bar = "█" * int(importance * 50)
                print(f"   {i}. {feature:20s} {bar} {importance:.3f}")
        
        print()


def main():
    """Main execution"""
    if len(sys.argv) < 2:
        print("사용법: python3 stock_price_predictor.py [종목코드]")
        print("예시: python3 stock_price_predictor.py 005930")
        print("      python3 stock_price_predictor.py 000660")
        sys.exit(1)
    
    symbol = sys.argv[1].zfill(6)
    
    # Create predictor
    try:
        predictor = StockPricePredictor()
    except Exception as e:
        print(f"❌ 초기화 오류: {e}")
        sys.exit(1)
    
    # Run prediction
    result = predictor.predict(symbol)
    
    if result:
        predictor.print_prediction(symbol, result)
    else:
        print(f"❌ {symbol} 예측 실패")
        sys.exit(1)


if __name__ == '__main__':
    main()
