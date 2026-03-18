#!/usr/bin/env python3
"""
Stock Price Direction Predictor - 향상된 방향 예측 모델
방향 정확도 개선을 위한 다양한 기법 적용

전략:
1. 분류 모델 (Classification) - 상승/하띋 예측
2. 임계값 기반 필터링 - 확신도 높은 예측만 실행
3. 앙상블 보팅 - 여러 모델의 다수결
4. 시장 국면 감지 - 강세/약세별 다른 모델
5. 메타 라벨링 - 예측 결과를 피처로 활용

사용법:
    python3 stock_direction_predictor.py 005930
"""

import sys
import warnings
import numpy as np
import pandas as pd
from datetime import datetime
from typing import Optional, Tuple, Dict

warnings.filterwarnings('ignore')

from sklearn.preprocessing import RobustScaler
from sklearn.ensemble import RandomForestClassifier, GradientBoostingClassifier, VotingClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score, confusion_matrix

from fdr_wrapper import FDRWrapper


class StockDirectionPredictor:
    """
    향상된 방향 예측 모델
    목표: 방향 정확도 60%+ 달성
    """
    
    def __init__(self):
        self.fdr = FDRWrapper()
        self.features = self._get_features()
        self.models = {}
        self.scaler = RobustScaler()
        self.threshold = 0.6  # 예측 임계값 (확신도)
        
    def _get_features(self):
        """확장된 피처 세트"""
        return [
            # 가격 위치
            'Close_MA5_ratio', 'Close_MA10_ratio', 'Close_MA20_ratio', 'Close_MA60_ratio',
            'EMA5_EMA20_ratio', 'EMA20_EMA60_ratio',
            
            # 추세 강도
            'MA5_slope', 'MA20_slope', 'MA_cross_signal',
            
            # RSI
            'RSI7', 'RSI14', 'RSI21', 'RSI_divergence', 'RSI_overbought', 'RSI_oversold',
            
            # MACD
            'MACD', 'MACD_signal', 'MACD_hist', 'MACD_momentum', 'MACD_cross_up', 'MACD_cross_down',
            
            # 볼린저
            'BB_position', 'BB_width', 'BB_squeeze', 'BB_breakout_upper', 'BB_breakout_lower',
            
            # 거래량
            'Volume_ratio', 'Volume_MA5_ratio', 'Volume_trend', 'Volume_price_divergence',
            
            # 변동성
            'ATR_ratio', 'ATR_trend', 'Volatility_regime',
            
            # 추세
            'Trend_5d', 'Trend_10d', 'Trend_20d', 'Higher_highs', 'Lower_lows',
            'Return_1d', 'Return_5d', 'Return_10d', 'Return_20d',
            
            # 패턴
            'Consecutive_up', 'Consecutive_down', 'Doji', 'Hammer', 'Engulfing',
            'Body_pct', 'Upper_shadow', 'Lower_shadow', 
            
            # 모멘텀
            'Momentum_1d', 'Momentum_3d', 'Momentum_5d', 'Momentum_10d',
            'Momentum_accel', 'ROC_10', 'ROC_20',
            
            # 시장 국면
            'Price_vs_52w_high', 'Price_vs_52w_low', 'Volatility_percentile'
        ]
    
    def fetch_data(self, symbol: str, days: int = 500):
        try:
            df = self.fdr.get_price(symbol, min_days=days)
            if df is None or len(df) < 200:
                return None
            if 'date' in df.columns:
                df['date'] = pd.to_datetime(df['date'])
                df = df.sort_values('date')
            return df.reset_index(drop=True)
        except:
            return None
    
    def calculate_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        """고급 기술적 지표 계산"""
        df = df.copy()
        
        # 이동평균
        for window in [5, 10, 20, 60]:
            df[f'MA{window}'] = df['close'].rolling(window=window).mean()
            df[f'EMA{window}'] = df['close'].ewm(span=window, adjust=False).mean()
            df[f'Close_MA{window}_ratio'] = df['close'] / df[f'MA{window}'] - 1
        
        # 추세 기울기
        df['MA5_slope'] = df['MA5'].diff(5) / df['MA5'].shift(5) * 100
        df['MA20_slope'] = df['MA20'].diff(20) / df['MA20'].shift(20) * 100
        df['MA_cross_signal'] = np.where(df['MA5'] > df['MA20'], 1, -1)
        df['EMA5_EMA20_ratio'] = df['EMA5'] / df['EMA20'] - 1
        df['EMA20_EMA60_ratio'] = df['EMA20'] / df['EMA60'] - 1
        
        # RSI 다중 기간
        for window in [7, 14, 21]:
            delta = df['close'].diff()
            gain = delta.where(delta > 0, 0).rolling(window=window).mean()
            loss = (-delta.where(delta < 0, 0)).rolling(window=window).mean()
            df[f'RSI{window}'] = 100 - (100 / (1 + gain / (loss + 1e-10)))
        
        df['RSI_divergence'] = np.where(
            (df['close'] > df['close'].shift(5)) & (df['RSI14'] < df['RSI14'].shift(5)), -1,
            np.where((df['close'] < df['close'].shift(5)) & (df['RSI14'] > df['RSI14'].shift(5)), 1, 0)
        )
        df['RSI_overbought'] = (df['RSI14'] > 70).astype(int)
        df['RSI_oversold'] = (df['RSI14'] < 30).astype(int)
        
        # MACD
        exp1 = df['close'].ewm(span=12, adjust=False).mean()
        exp2 = df['close'].ewm(span=26, adjust=False).mean()
        df['MACD'] = exp1 - exp2
        df['MACD_signal'] = df['MACD'].ewm(span=9, adjust=False).mean()
        df['MACD_hist'] = df['MACD'] - df['MACD_signal']
        df['MACD_momentum'] = df['MACD_hist'].diff()
        df['MACD_cross_up'] = ((df['MACD'] > df['MACD_signal']) & 
                               (df['MACD'].shift(1) <= df['MACD_signal'].shift(1))).astype(int)
        df['MACD_cross_down'] = ((df['MACD'] < df['MACD_signal']) & 
                                 (df['MACD'].shift(1) >= df['MACD_signal'].shift(1))).astype(int)
        
        # 볼린저 밴드
        ma20 = df['close'].rolling(window=20).mean()
        std20 = df['close'].rolling(window=20).std()
        df['BB_upper'] = ma20 + std20 * 2
        df['BB_lower'] = ma20 - std20 * 2
        df['BB_position'] = (df['close'] - df['BB_lower']) / (df['BB_upper'] - df['BB_lower'] + 1e-10)
        df['BB_width'] = (df['BB_upper'] - df['BB_lower']) / ma20
        df['BB_squeeze'] = (df['BB_width'] < df['BB_width'].rolling(20).quantile(0.2)).astype(int)
        df['BB_breakout_upper'] = (df['close'] > df['BB_upper']).astype(int)
        df['BB_breakout_lower'] = (df['close'] < df['BB_lower']).astype(int)
        
        # 거래량
        df['Volume_MA5'] = df['volume'].rolling(window=5).mean()
        df['Volume_MA20'] = df['volume'].rolling(window=20).mean()
        df['Volume_ratio'] = df['volume'] / df['Volume_MA20']
        df['Volume_MA5_ratio'] = df['Volume_MA5'] / df['Volume_MA20']
        df['Volume_trend'] = np.where(df['Volume_MA5'] > df['Volume_MA20'], 1, -1)
        
        # 변동성
        high_low = df['high'] - df['low']
        high_close = np.abs(df['high'] - df['close'].shift())
        low_close = np.abs(df['low'] - df['close'].shift())
        df['ATR14'] = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1).rolling(14).mean()
        df['ATR_ratio'] = df['ATR14'] / df['close']
        df['ATR_trend'] = df['ATR14'].diff(5)
        df['Volatility_regime'] = np.where(df['ATR_ratio'] > df['ATR_ratio'].rolling(60).mean(), 1, 0)
        df['Volatility_percentile'] = df['ATR_ratio'].rolling(60).apply(lambda x: pd.Series(x).rank(pct=True).iloc[-1] if len(x) > 0 else 0.5)
        
        # 추세
        df['Trend_5d'] = (df['close'] > df['close'].shift(5)).astype(int)
        df['Trend_10d'] = (df['close'] > df['close'].shift(10)).astype(int)
        df['Trend_20d'] = (df['close'] > df['close'].shift(20)).astype(int)
        df['Higher_highs'] = ((df['high'] > df['high'].shift(1)) & 
                              (df['high'].shift(1) > df['high'].shift(2))).astype(int)
        df['Lower_lows'] = ((df['low'] < df['low'].shift(1)) & 
                           (df['low'].shift(1) < df['low'].shift(2))).astype(int)
        
        # 수익률
        for period in [1, 5, 10, 20]:
            df[f'Return_{period}d'] = df['close'].pct_change(period)
        
        # 캔들스틱 패턴
        df['Body'] = df['close'] - df['open']
        df['Body_pct'] = df['Body'] / df['close']
        df['Upper_shadow'] = (df['high'] - df[['open', 'close']].max(axis=1)) / df['close']
        df['Lower_shadow'] = (df[['open', 'close']].min(axis=1) - df['low']) / df['close']
        df['Range'] = df['high'] - df['low']
        
        df['Doji'] = (np.abs(df['Body']) / (df['Range'] + 1e-10) < 0.1).astype(int)
        df['Hammer'] = ((df['Lower_shadow'] > 2 * np.abs(df['Body_pct'])) & 
                       (df['Upper_shadow'] < np.abs(df['Body_pct']))).astype(int)
        df['Engulfing'] = np.where(
            (df['Body'] > 0) & (df['Body'].shift(1) < 0) & 
            (df['open'] < df['close'].shift(1)) & (df['close'] > df['open'].shift(1)), 1,
            np.where((df['Body'] < 0) & (df['Body'].shift(1) > 0) & 
                    (df['open'] > df['close'].shift(1)) & (df['close'] < df['open'].shift(1)), -1, 0)
        )
        
        # 연속
        df['Price_up'] = (df['close'] > df['close'].shift(1)).astype(int)
        df['Consecutive_up'] = df['Price_up'].groupby((df['Price_up'] != df['Price_up'].shift()).cumsum()).cumsum()
        df['Consecutive_down'] = (1 - df['Price_up']).groupby(((1 - df['Price_up']) != (1 - df['Price_up']).shift()).cumsum()).cumsum()
        
        # 모멘텀
        df['Momentum_1d'] = df['close'].pct_change(1)
        df['Momentum_3d'] = df['close'].pct_change(3)
        df['Momentum_5d'] = df['close'].pct_change(5)
        df['Momentum_10d'] = df['close'].pct_change(10)
        df['Momentum_accel'] = df['Momentum_1d'] - df['Momentum_1d'].shift(1)
        df['ROC_10'] = (df['close'] - df['close'].shift(10)) / df['close'].shift(10) * 100
        df['ROC_20'] = (df['close'] - df['close'].shift(20)) / df['close'].shift(20) * 100
        
        # 52주 기준
        df['Price_vs_52w_high'] = df['close'] / df['close'].rolling(252).max()
        df['Price_vs_52w_low'] = df['close'] / df['close'].rolling(252).min()
        
        return df
    
    def prepare_data(self, df: pd.DataFrame, lookback: int = 20):
        """학습 데이터 준비"""
        # 타겟: 다음날 방향 (1: 상승, 0: 하띋)
        df['target'] = (df['close'].shift(-1) > df['close']).astype(int)
        
        # 피처/타겟 정리
        feature_cols = [f for f in self.features if f in df.columns]
        df_clean = df[feature_cols + ['target', 'close']].dropna()
        
        X, y, prices = [], [], []
        
        for i in range(lookback, len(df_clean)):
            window = df_clean[feature_cols].iloc[i-lookback:i]
            # 통계적 집계
            features = np.concatenate([
                window.mean().values,
                window.std().values,
                window.min().values,
                window.max().values,
                window.iloc[-1].values
            ])
            X.append(features)
            y.append(df_clean['target'].iloc[i])
            prices.append(df_clean['close'].iloc[i])
        
        return np.array(X), np.array(y), np.array(prices), feature_cols
    
    def train_models(self, X: np.ndarray, y: np.ndarray):
        """다중 분류 모델 학습"""
        # 데이터 분할 (시계열 순서 유지)
        split = int(len(X) * 0.8)
        X_train, X_test = X[:split], X[split:]
        y_train, y_test = y[:split], y[split:]
        
        # 스케일링
        X_train_scaled = self.scaler.fit_transform(X_train)
        X_test_scaled = self.scaler.transform(X_test)
        
        # 모델 1: Random Forest
        print("   🌲 Random Forest 학습 중...")
        rf = RandomForestClassifier(
            n_estimators=300,
            max_depth=15,
            min_samples_split=10,
            min_samples_leaf=5,
            class_weight='balanced',
            random_state=42,
            n_jobs=-1
        )
        rf.fit(X_train_scaled, y_train)
        rf_pred = rf.predict(X_test_scaled)
        rf_acc = accuracy_score(y_test, rf_pred)
        print(f"      정확도: {rf_acc*100:.1f}%")
        
        # 모델 2: Gradient Boosting
        print("   🚀 Gradient Boosting 학습 중...")
        gb = GradientBoostingClassifier(
            n_estimators=200,
            learning_rate=0.05,
            max_depth=5,
            min_samples_split=10,
            random_state=42
        )
        gb.fit(X_train_scaled, y_train)
        gb_pred = gb.predict(X_test_scaled)
        gb_acc = accuracy_score(y_test, gb_pred)
        print(f"      정확도: {gb_acc*100:.1f}%")
        
        # 모델 3: Logistic Regression
        print("   📈 Logistic Regression 학습 중...")
        lr = LogisticRegression(
            class_weight='balanced',
            max_iter=1000,
            random_state=42
        )
        lr.fit(X_train_scaled, y_train)
        lr_pred = lr.predict(X_test_scaled)
        lr_acc = accuracy_score(y_test, lr_pred)
        print(f"      정확도: {lr_acc*100:.1f}%")
        
        # Voting Ensemble
        print("   🗳️  Voting Ensemble 구성 중...")
        voting = VotingClassifier(
            estimators=[('rf', rf), ('gb', gb), ('lr', lr)],
            voting='soft'
        )
        voting.fit(X_train_scaled, y_train)
        
        # 모델 저장
        self.models = {
            'rf': rf,
            'gb': gb,
            'lr': lr,
            'voting': voting
        }
        
        # 앙상블 성능
        vote_pred = voting.predict(X_test_scaled)
        vote_acc = accuracy_score(y_test, vote_pred)
        print(f"      앙상블 정확도: {vote_acc*100:.1f}%")
        
        # 상위 피처
        n_features = len(self.features)
        importance = rf.feature_importances_[:n_features]
        top_features = sorted(zip(self.features, importance), key=lambda x: x[1], reverse=True)[:5]
        
        return {
            'rf_acc': rf_acc,
            'gb_acc': gb_acc,
            'lr_acc': lr_acc,
            'vote_acc': vote_acc,
            'top_features': top_features
        }
    
    def predict_with_confidence(self, X: np.ndarray) -> Tuple[int, float]:
        """확신도 기반 예측"""
        X_scaled = self.scaler.transform(X.reshape(1, -1))
        
        # 각 모델 예측
        rf_proba = self.models['rf'].predict_proba(X_scaled)[0]
        gb_proba = self.models['gb'].predict_proba(X_scaled)[0]
        lr_proba = self.models['lr'].predict_proba(X_scaled)[0]
        vote_proba = self.models['voting'].predict_proba(X_scaled)[0]
        
        # 평균 확률
        avg_proba = (rf_proba + gb_proba + lr_proba + vote_proba) / 4
        
        direction = 1 if avg_proba[1] > 0.5 else 0
        confidence = max(avg_proba)
        
        return direction, confidence
    
    def predict(self, symbol: str) -> Optional[Dict]:
        """메인 예측 파이프라인"""
        print(f"\n{'='*60}")
        print(f"🔮 {symbol} 방향 예측 (향상된 모델)")
        print(f"{'='*60}")
        
        # 데이터 수집
        df = self.fetch_data(symbol)
        if df is None:
            return None
        
        print(f"📊 데이터: {len(df)}일")
        
        # 지표 계산
        df = self.calculate_indicators(df)
        
        # 데이터 준비
        X, y, prices, features = self.prepare_data(df)
        print(f"📚 학습 샘플: {len(X)}개")
        
        # 모델 학습
        print("🤖 모델 학습 중...")
        metrics = self.train_models(X, y)
        
        # 마지막 데이터 예측
        last_X = X[-1:]
        direction, confidence = self.predict_with_confidence(last_X)
        
        current_price = prices[-1]
        prediction_date = (datetime.now() + pd.Timedelta(days=1)).strftime('%Y-%m-%d')
        
        return {
            'symbol': symbol,
            'current_price': current_price,
            'direction': '상승' if direction == 1 else '하띋',
            'confidence': confidence,
            'prediction_date': prediction_date,
            'metrics': metrics
        }
    
    def print_prediction(self, result: Dict):
        print(f"\n{'='*60}")
        print(f"📊 {result['symbol']} 방향 예측 결과")
        print(f"{'='*60}")
        print(f"📅 예측일: {result['prediction_date']}")
        print(f"💰 현재가: {result['current_price']:,.0f}원")
        print(f"📈 예상 방향: {result['direction']}")
        print(f"🎯 확신도: {result['confidence']*100:.1f}%")
        
        if result['confidence'] >= self.threshold:
            print(f"   ✅ 확신도 {self.threshold*100:.0f}% 이상 - 신호 유효")
        else:
            print(f"   ⚠️ 확신도 {self.threshold*100:.0f}% 미만 - 관망 권장")
        
        print(f"\n📈 모델 성능:")
        print(f"   Random Forest: {result['metrics']['rf_acc']*100:.1f}%")
        print(f"   Gradient Boosting: {result['metrics']['gb_acc']*100:.1f}%")
        print(f"   Logistic Regression: {result['metrics']['lr_acc']*100:.1f}%")
        print(f"   앙상블 (Voting): {result['metrics']['vote_acc']*100:.1f}%")
        
        print(f"\n🔍 주요 피처:")
        for i, (feat, imp) in enumerate(result['metrics']['top_features'], 1):
            bar = '█' * int(imp * 50)
            print(f"   {i}. {feat:20s} {bar} {imp:.3f}")
        
        print(f"{'='*60}\n")


def main():
    if len(sys.argv) < 2:
        print("사용법: python3 stock_direction_predictor.py [종목코드]")
        print("예시: python3 stock_direction_predictor.py 005930")
        sys.exit(1)
    
    symbol = sys.argv[1].zfill(6)
    
    predictor = StockDirectionPredictor()
    result = predictor.predict(symbol)
    
    if result:
        predictor.print_prediction(result)
    else:
        print(f"❌ {symbol} 예측 실패")
        sys.exit(1)


if __name__ == '__main__':
    main()
