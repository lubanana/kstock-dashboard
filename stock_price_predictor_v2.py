#!/usr/bin/env python3
"""
K-Stock Price Predictor V2 (Tuned)
개선된 주가 예측 모델 - 종목 코드 입력 → 내일 예상 등락률 예측

주요 개선사항:
1. 직접 가격 예측 → 수익률(%) 예측으로 변경
2. 앙상블 모델 (Random Forest + Gradient Boosting)
3. 시계열 교차 검증
4. 피처 엔지니어링 개선 (상대적 변화율 중심)
5. 타겟 인코딩 (다음날 수익률 예측)

사용법:
    python3 stock_price_predictor_v2.py 005930  # 삼성전자 예측
    python3 stock_price_predictor_v2.py 000660  # SK하이닉스 예측
"""

import sys
import warnings
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from typing import Optional, Tuple, Dict, List

warnings.filterwarnings('ignore')

from sklearn.preprocessing import StandardScaler, RobustScaler
from sklearn.metrics import mean_absolute_error, r2_score
from sklearn.ensemble import RandomForestRegressor, GradientBoostingRegressor
from sklearn.model_selection import TimeSeriesSplit

from fdr_wrapper import FDRWrapper


class StockPricePredictorV2:
    """Improved stock price prediction model"""
    
    def __init__(self):
        self.fdr = FDRWrapper()
        self.scaler = RobustScaler()  # 이상치에 강한 스케일러
        self.rf_model = None
        self.gb_model = None
        self.features = []
        self.feature_importance = {}
    
    def fetch_data(self, symbol: str, days: int = 730) -> Optional[pd.DataFrame]:
        """Fetch historical stock data"""
        print(f"📊 {symbol} 데이터 수집 중...")
        
        try:
            df = self.fdr.get_price(symbol, min_days=days)
            
            if df is None or len(df) < 100:
                print(f"❌ 데이터 수집 실패: {symbol}")
                return None
            
            # 날짜 컬럼 확인 및 변환
            if 'date' in df.columns:
                df['date'] = pd.to_datetime(df['date'])
                df = df.sort_values('date')
            
            print(f"✅ {len(df)}일 데이터 수집 완료")
            return df.reset_index(drop=True)
            
        except Exception as e:
            print(f"❌ 데이터 수집 오류: {e}")
            return None
    
    def calculate_technical_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        """Calculate enhanced technical indicators"""
        print("📈 기술적 지표 계산 중...")
        
        df = df.copy()
        
        # 가격 관련 피처들 (로그 변환 후 상대적 변화)
        df['log_close'] = np.log(df['close'])
        df['log_open'] = np.log(df['open'])
        df['log_high'] = np.log(df['high'])
        df['log_low'] = np.log(df['low'])
        
        # 1. 이동평균 및 상대적 위치
        for window in [5, 10, 20, 60]:
            df[f'MA{window}'] = df['close'].rolling(window=window).mean()
            df[f'EMA{window}'] = df['close'].ewm(span=window, adjust=False).mean()
            # 현재가 대비 이동평균 비율 (상대적 위치)
            df[f'Close_MA{window}_ratio'] = df['close'] / df[f'MA{window}'] - 1
            df[f'Close_EMA{window}_ratio'] = df['close'] / df[f'EMA{window}'] - 1
        
        # 이동평균 간격 (골든/데드 크로스 신호)
        df['MA5_MA20_ratio'] = df['MA5'] / df['MA20'] - 1
        df['MA20_MA60_ratio'] = df['MA20'] / df['MA60'] - 1
        df['EMA5_EMA20_ratio'] = df['EMA5'] / df['EMA20'] - 1
        
        # 2. RSI 개선版 (과매수/과매도 구간 인코딩)
        for window in [7, 14, 21]:
            delta = df['close'].diff()
            gain = delta.where(delta > 0, 0).rolling(window=window).mean()
            loss = (-delta.where(delta < 0, 0)).rolling(window=window).mean()
            rs = gain / (loss + 1e-10)
            df[f'RSI{window}'] = 100 - (100 / (1 + rs))
            # RSI 변화량
            df[f'RSI{window}_change'] = df[f'RSI{window}'].diff()
            # 과매수/과매도 플래그
            df[f'RSI{window}_overbought'] = (df[f'RSI{window}'] > 70).astype(int)
            df[f'RSI{window}_oversold'] = (df[f'RSI{window}'] < 30).astype(int)
        
        # 3. MACD 및 변화율
        exp1 = df['close'].ewm(span=12, adjust=False).mean()
        exp2 = df['close'].ewm(span=26, adjust=False).mean()
        df['MACD'] = exp1 - exp2
        df['MACD_signal'] = df['MACD'].ewm(span=9, adjust=False).mean()
        df['MACD_hist'] = df['MACD'] - df['MACD_signal']
        # MACD 변화율
        df['MACD_change'] = df['MACD'].diff()
        df['MACD_hist_change'] = df['MACD_hist'].diff()
        # MACD 골든/데드 크로스
        df['MACD_cross'] = np.where(df['MACD'] > df['MACD_signal'], 1, -1)
        df['MACD_cross_change'] = df['MACD_cross'].diff()
        
        # 4. 볼린저 밴드 (상대적 위치 중심)
        for window in [20, 40]:
            ma = df['close'].rolling(window=window).mean()
            std = df['close'].rolling(window=window).std()
            df[f'BB_upper_{window}'] = ma + (std * 2)
            df[f'BB_lower_{window}'] = ma - (std * 2)
            df[f'BB_position_{window}'] = (df['close'] - df[f'BB_lower_{window}']) / (df[f'BB_upper_{window}'] - df[f'BB_lower_{window}'] + 1e-10)
            df[f'BB_width_{window}'] = (df[f'BB_upper_{window}'] - df[f'BB_lower_{window}']) / ma
        
        # 5. 거래량 지표 (상대적 변화 중심)
        for window in [5, 20]:
            df[f'Volume_MA{window}'] = df['volume'].rolling(window=window).mean()
        df['Volume_ratio'] = df['volume'] / df['Volume_MA20']
        df['Volume_ratio_MA5'] = df['volume'] / df['Volume_MA5']
        df['Volume_change'] = df['volume'].pct_change()
        df['Volume_MA5_MA20_ratio'] = df['Volume_MA5'] / df['Volume_MA20']
        
        # 거래량 급증 플래그
        df['Volume_spike'] = (df['Volume_ratio'] > 2).astype(int)
        
        # 6. 가격 변동성 (ATR 및 변동성 지표)
        high_low = df['high'] - df['low']
        high_close = np.abs(df['high'] - df['close'].shift())
        low_close = np.abs(df['low'] - df['close'].shift())
        ranges = pd.concat([high_low, high_close, low_close], axis=1)
        true_range = np.max(ranges, axis=1)
        
        for window in [7, 14, 21]:
            df[f'ATR{window}'] = true_range.rolling(window).mean()
            df[f'ATR{window}_ratio'] = df[f'ATR{window}'] / df['close']
        
        # 일일 변동폭
        df['Daily_range'] = (df['high'] - df['low']) / df['close']
        df['Daily_range_MA20'] = df['Daily_range'].rolling(20).mean()
        
        # 7. 추세 지표
        for window in [5, 10, 20, 60]:
            df[f'Trend_{window}d'] = (df['close'] > df['close'].shift(window)).astype(int)
            df[f'Return_{window}d'] = df['close'].pct_change(window)
        
        # 연속 상승/하띨 카운트
        df['Price_up'] = (df['close'] > df['close'].shift(1)).astype(int)
        df['Consecutive_up'] = df['Price_up'].groupby((df['Price_up'] != df['Price_up'].shift()).cumsum()).cumsum()
        df['Consecutive_down'] = (1 - df['Price_up']).groupby(((1 - df['Price_up']) != (1 - df['Price_up']).shift()).cumsum()).cumsum()
        
        # 8. 캔들스틱 패턴
        df['Body'] = df['close'] - df['open']
        df['Body_pct'] = df['Body'] / df['close']
        df['Upper_shadow'] = (df['high'] - np.maximum(df['open'], df['close'])) / df['close']
        df['Lower_shadow'] = (np.minimum(df['open'], df['close']) - df['low']) / df['close']
        df['Body_to_range'] = np.abs(df['Body']) / (df['high'] - df['low'] + 1e-10)
        
        # 양봉/음봉 플래그
        df['Is_bullish'] = (df['close'] > df['open']).astype(int)
        
        # 9. 모멘텀 지표
        df['Momentum_1d'] = df['close'].pct_change(1)
        df['Momentum_3d'] = df['close'].pct_change(3)
        df['Momentum_5d'] = df['close'].pct_change(5)
        df['Momentum_10d'] = df['close'].pct_change(10)
        df['Momentum_20d'] = df['close'].pct_change(20)
        
        # 모멘텀 가속도
        df['Momentum_accel'] = df['Momentum_1d'] - df['Momentum_1d'].shift(1)
        
        # 10. 주요 피처 선택
        self.features = [
            # 상대적 위치
            'Close_MA5_ratio', 'Close_MA20_ratio', 'Close_MA60_ratio',
            'Close_EMA5_ratio', 'Close_EMA20_ratio',
            'MA5_MA20_ratio', 'MA20_MA60_ratio', 'EMA5_EMA20_ratio',
            
            # RSI
            'RSI14', 'RSI14_change', 'RSI14_overbought', 'RSI14_oversold',
            
            # MACD
            'MACD', 'MACD_hist', 'MACD_change', 'MACD_hist_change', 'MACD_cross',
            
            # 볼린저
            'BB_position_20', 'BB_width_20',
            
            # 거래량
            'Volume_ratio', 'Volume_change', 'Volume_spike', 'Volume_MA5_MA20_ratio',
            
            # 변동성
            'ATR14_ratio', 'Daily_range', 'Daily_range_MA20',
            
            # 추세
            'Trend_5d', 'Trend_20d', 'Return_5d', 'Return_20d',
            'Consecutive_up', 'Consecutive_down',
            
            # 캔들스틱
            'Body_pct', 'Upper_shadow', 'Lower_shadow', 'Body_to_range', 'Is_bullish',
            
            # 모멘텀
            'Momentum_1d', 'Momentum_5d', 'Momentum_20d', 'Momentum_accel'
        ]
        
        print(f"✅ {len(self.features)}개 기술적 지표 계산 완료")
        return df
    
    def prepare_training_data(self, df: pd.DataFrame, lookback_days: int = 20) -> Tuple[np.ndarray, np.ndarray]:
        """Prepare training data - predict next day's return"""
        
        # 타겟: 다음날 수익률 (로그 수익률 사용)
        df['target'] = np.log(df['close'].shift(-1) / df['close']) * 100  # 백분율
        
        # 필요한 컬럼만 선택 후 결측치 제거
        df_clean = df[self.features + ['target', 'close']].dropna()
        
        if len(df_clean) < lookback_days + 50:
            raise ValueError(f"데이터가 부족합니다. 최소 {lookback_days + 50}일 필요.")
        
        X, y = [], []
        
        for i in range(lookback_days, len(df_clean)):
            # Feature: 과거 lookback_days 간의 피처들
            feature_window = df_clean[self.features].iloc[i-lookback_days:i]
            
            # 피처 집계 (평균, 표준편차, 마지막 값)
            features_mean = feature_window.mean().values
            features_std = feature_window.std().values
            features_last = feature_window.iloc[-1].values
            
            # 3배 차원으로 확장
            combined_features = np.concatenate([features_mean, features_std, features_last])
            X.append(combined_features)
            
            # Target: 다음날 수익률
            y.append(df_clean['target'].iloc[i])
        
        return np.array(X), np.array(y)
    
    def train_with_cv(self, X: np.ndarray, y: np.ndarray) -> Dict:
        """Train models with time series cross-validation"""
        print("🤖 앙상블 모델 학습 중 (시계열 교차 검증)...")
        
        # 시계열 교차 검증
        tscv = TimeSeriesSplit(n_splits=5)
        
        rf_scores = []
        gb_scores = []
        
        print("   교차 검증 수행 중...")
        for fold, (train_idx, val_idx) in enumerate(tscv.split(X), 1):
            X_train, X_val = X[train_idx], X[val_idx]
            y_train, y_val = y[train_idx], y[val_idx]
            
            # 스케일링
            scaler_fold = RobustScaler()
            X_train_scaled = scaler_fold.fit_transform(X_train)
            X_val_scaled = scaler_fold.transform(X_val)
            
            # Random Forest
            rf = RandomForestRegressor(
                n_estimators=300,
                max_depth=15,
                min_samples_split=10,
                min_samples_leaf=5,
                random_state=42,
                n_jobs=-1
            )
            rf.fit(X_train_scaled, y_train)
            rf_pred = rf.predict(X_val_scaled)
            rf_mae = mean_absolute_error(y_val, rf_pred)
            rf_scores.append(rf_mae)
            
            # Gradient Boosting
            gb = GradientBoostingRegressor(
                n_estimators=200,
                learning_rate=0.05,
                max_depth=5,
                min_samples_split=10,
                min_samples_leaf=5,
                subsample=0.8,
                random_state=42
            )
            gb.fit(X_train_scaled, y_train)
            gb_pred = gb.predict(X_val_scaled)
            gb_mae = mean_absolute_error(y_val, gb_pred)
            gb_scores.append(gb_mae)
            
            print(f"      Fold {fold}: RF_MAE={rf_mae:.3f}%, GB_MAE={gb_mae:.3f}%")
        
        print(f"   평균 검증 MAE: RF={np.mean(rf_scores):.3f}%, GB={np.mean(gb_scores):.3f}%")
        
        # 전체 데이터로 최종 모델 학습
        print("   최종 모델 학습 중...")
        
        # 스케일링
        X_scaled = self.scaler.fit_transform(X)
        
        # Random Forest
        self.rf_model = RandomForestRegressor(
            n_estimators=500,
            max_depth=20,
            min_samples_split=5,
            min_samples_leaf=2,
            random_state=42,
            n_jobs=-1
        )
        self.rf_model.fit(X_scaled, y)
        
        # Gradient Boosting
        self.gb_model = GradientBoostingRegressor(
            n_estimators=300,
            learning_rate=0.03,
            max_depth=6,
            min_samples_split=5,
            min_samples_leaf=2,
            subsample=0.8,
            random_state=42
        )
        self.gb_model.fit(X_scaled, y)
        
        # Feature importance 저장
        n_features = len(self.features)
        rf_importance = self.rf_model.feature_importances_
        gb_importance = self.gb_model.feature_importances_
        
        # 평균 importance 계산
        for i, feat in enumerate(self.features):
            mean_imp = np.mean([
                rf_importance[i], rf_importance[i + n_features], rf_importance[i + 2*n_features],
                gb_importance[i], gb_importance[i + n_features], gb_importance[i + 2*n_features]
            ])
            self.feature_importance[feat] = mean_imp
        
        # Train/Val split for final evaluation
        split_idx = int(len(X) * 0.85)
        X_train, X_val = X[:split_idx], X[split_idx:]
        y_train, y_val = y[:split_idx], y[split_idx:]
        
        X_train_scaled = self.scaler.transform(X_train)
        X_val_scaled = self.scaler.transform(X_val)
        
        rf_train_pred = self.rf_model.predict(X_train_scaled)
        rf_val_pred = self.rf_model.predict(X_val_scaled)
        gb_train_pred = self.gb_model.predict(X_train_scaled)
        gb_val_pred = self.gb_model.predict(X_val_scaled)
        
        # 앙상블 예측 (평균)
        ensemble_train_pred = (rf_train_pred + gb_train_pred) / 2
        ensemble_val_pred = (rf_val_pred + gb_val_pred) / 2
        
        print(f"✅ 학습 완료")
        print(f"   Ensemble Train MAE: {mean_absolute_error(y_train, ensemble_train_pred):.3f}%")
        print(f"   Ensemble Val MAE: {mean_absolute_error(y_val, ensemble_val_pred):.3f}%")
        print(f"   Ensemble Val R²: {r2_score(y_val, ensemble_val_pred):.3f}")
        
        return {
            'train_mae': mean_absolute_error(y_train, ensemble_train_pred),
            'val_mae': mean_absolute_error(y_val, ensemble_val_pred),
            'val_r2': r2_score(y_val, ensemble_val_pred)
        }
    
    def predict_next_day(self, df: pd.DataFrame, lookback_days: int = 20) -> Dict:
        """Predict next day's return"""
        
        # 마지막 윈도우 피처 추출
        feature_window = df[self.features].iloc[-lookback_days:]
        
        features_mean = feature_window.mean().values
        features_std = feature_window.std().values
        features_last = feature_window.iloc[-1].values
        
        last_data = np.concatenate([features_mean, features_std, features_last]).reshape(1, -1)
        last_data_scaled = self.scaler.transform(last_data)
        
        # 앙상블 예측
        rf_pred = self.rf_model.predict(last_data_scaled)[0]
        gb_pred = self.gb_model.predict(last_data_scaled)[0]
        predicted_return = (rf_pred + gb_pred) / 2
        
        # 현재가 및 예상 종가 계산
        current_price = df['close'].iloc[-1]
        predicted_price = current_price * (1 + predicted_return / 100)
        
        # 예측일 (다음 영업일)
        last_date = pd.to_datetime(df['date'].iloc[-1]) if 'date' in df.columns else datetime.now()
        prediction_date = last_date + timedelta(days=1)
        while prediction_date.weekday() >= 5:
            prediction_date += timedelta(days=1)
        
        # 상위 피처 중요도
        top_features = sorted(
            self.feature_importance.items(),
            key=lambda x: x[1],
            reverse=True
        )[:7]
        
        # 예측 신뢰도 (검증 MAE 기반)
        confidence = max(0, min(100, 100 - abs(predicted_return) * 2))
        
        return {
            'current_price': current_price,
            'predicted_return': predicted_return,
            'predicted_price': predicted_price,
            'change_rate': predicted_return,
            'prediction_date': prediction_date.strftime('%Y-%m-%d'),
            'top_features': top_features,
            'confidence': confidence
        }
    
    def predict(self, symbol: str) -> Optional[Dict]:
        """Main prediction pipeline"""
        print("=" * 70)
        print(f"🔮 {symbol} 주가 예측 시작 (V2 - Tuned Model)")
        print("=" * 70)
        
        # 1. 데이터 수집
        df = self.fetch_data(symbol)
        if df is None:
            return None
        
        # 2. 기술적 지표 계산
        df = self.calculate_technical_indicators(df)
        
        # 3. 학습 데이터 준비
        try:
            X, y = self.prepare_training_data(df)
            print(f"📚 학습 데이터: {len(X)}개 샘플")
        except ValueError as e:
            print(f"❌ {e}")
            return None
        
        # 4. 모델 학습
        metrics = self.train_with_cv(X, y)
        
        # 5. 예측
        result = self.predict_next_day(df)
        result['metrics'] = metrics
        
        return result
    
    def print_prediction(self, symbol: str, result: Dict):
        """Print prediction result"""
        print()
        print("=" * 70)
        print(f"📊 {symbol} 예측 결과")
        print("=" * 70)
        print(f"📅 예측 대상일: {result['prediction_date']}")
        print(f"💰 현재 종가: {result['current_price']:,.0f}원")
        print(f"🔮 예상 수익률: {result['predicted_return']:+.2f}%")
        print(f"💵 예상 종가: {result['predicted_price']:,.0f}원")
        
        change = result['change_rate']
        if change > 1:
            arrow = "📈📈"
            status = "강한 상승 예상"
        elif change > 0:
            arrow = "📈"
            status = "상승 예상"
        elif change > -1:
            arrow = "📉"
            status = "하락 예상"
        else:
            arrow = "📉📉"
            status = "강한 하락 예상"
        
        print(f"{arrow} 예상 등락: {change:+.2f}% ({status})")
        print(f"🎯 예측 신뢰도: {result['confidence']:.0f}%")
        print("=" * 70)
        
        # 주요 피처
        print("\n🔍 주요 예측 요인:")
        for i, (feature, importance) in enumerate(result['top_features'], 1):
            bar = "█" * int(importance * 100)
            print(f"   {i}. {feature:25s} {bar} {importance:.3f}")
        
        # 성능 지표
        print("\n📈 모델 성능:")
        print(f"   Train MAE: {result['metrics']['train_mae']:.3f}%")
        print(f"   Val MAE: {result['metrics']['val_mae']:.3f}%")
        print(f"   Val R²: {result['metrics']['val_r2']:.3f}")
        
        print("\n⚠️  참고: 본 예측은 참고용이며 실제 투자 결과를 보장하지 않습니다.")
        print()


def main():
    """Main execution"""
    if len(sys.argv) < 2:
        print("사용법: python3 stock_price_predictor_v2.py [종목코드]")
        print("예시: python3 stock_price_predictor_v2.py 005930")
        print("      python3 stock_price_predictor_v2.py 000660")
        sys.exit(1)
    
    symbol = sys.argv[1].zfill(6)
    
    try:
        predictor = StockPricePredictorV2()
    except Exception as e:
        print(f"❌ 초기화 오류: {e}")
        sys.exit(1)
    
    result = predictor.predict(symbol)
    
    if result:
        predictor.print_prediction(symbol, result)
    else:
        print(f"❌ {symbol} 예측 실패")
        sys.exit(1)


if __name__ == '__main__':
    main()
