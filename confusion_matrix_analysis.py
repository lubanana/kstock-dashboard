#!/usr/bin/env python3
"""
Stock Direction Predictor - Confusion Matrix Analysis
방향 예측 모델 혼동 행렬 분석
"""

import sys
import warnings
import numpy as np
import pandas as pd
from datetime import datetime

warnings.filterwarnings('ignore')

from sklearn.preprocessing import RobustScaler
from sklearn.ensemble import RandomForestClassifier, GradientBoostingClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score, confusion_matrix

from fdr_wrapper import FDRWrapper


class ConfusionMatrixAnalyzer:
    """혼동 행렬 분석기"""
    
    def __init__(self):
        self.fdr = FDRWrapper()
        
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
    
    def calculate_indicators(self, df: pd.DataFrame):
        """핵심 지표 계산"""
        df = df.copy()
        
        # 이동평균
        for window in [5, 10, 20, 60]:
            df[f'MA{window}'] = df['close'].rolling(window=window).mean()
            df[f'Close_MA{window}_ratio'] = df['close'] / df[f'MA{window}'] - 1
        
        df['MA5_slope'] = df['MA5'].diff(5) / df['MA5'].shift(5)
        df['MA_cross'] = np.where(df['MA5'] > df['MA20'], 1, -1)
        
        # RSI
        delta = df['close'].diff()
        gain = delta.where(delta > 0, 0).rolling(window=14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
        df['RSI14'] = 100 - (100 / (1 + gain / (loss + 1e-10)))
        df['RSI_change'] = df['RSI14'].diff()
        
        # MACD
        exp1 = df['close'].ewm(span=12, adjust=False).mean()
        exp2 = df['close'].ewm(span=26, adjust=False).mean()
        df['MACD'] = exp1 - exp2
        df['MACD_hist'] = df['MACD'] - df['MACD'].ewm(span=9, adjust=False).mean()
        
        # 볼린저
        ma20 = df['close'].rolling(window=20).mean()
        std20 = df['close'].rolling(window=20).std()
        df['BB_position'] = (df['close'] - (ma20 - std20*2)) / ((ma20 + std20*2) - (ma20 - std20*2) + 1e-10)
        
        # 거래량
        df['Volume_MA20'] = df['volume'].rolling(window=20).mean()
        df['Volume_ratio'] = df['volume'] / df['Volume_MA20']
        
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
        
        # 캔들스틱
        df['Body_pct'] = (df['close'] - df['open']) / df['close']
        df['Upper_shadow'] = (df['high'] - np.maximum(df['open'], df['close'])) / df['close']
        df['Lower_shadow'] = (np.minimum(df['open'], df['close']) - df['low']) / df['close']
        
        # 연속
        df['Price_up'] = (df['close'] > df['close'].shift(1)).astype(int)
        df['Consecutive_up'] = df['Price_up'].groupby((df['Price_up'] != df['Price_up'].shift()).cumsum()).cumsum()
        df['Consecutive_down'] = (1 - df['Price_up']).groupby(((1 - df['Price_up']) != (1 - df['Price_up']).shift()).cumsum()).cumsum()
        
        # 모멘텀
        df['Momentum_1d'] = df['close'].pct_change(1)
        df['Momentum_5d'] = df['close'].pct_change(5)
        df['Momentum_10d'] = df['close'].pct_change(10)
        df['Momentum_accel'] = df['Momentum_1d'] - df['Momentum_1d'].shift(1)
        
        # 52주
        df['Price_vs_52w_high'] = df['close'] / df['close'].rolling(252).max()
        
        return df
    
    def prepare_data(self, df: pd.DataFrame):
        """학습 데이터 준비"""
        features = [
            'Close_MA5_ratio', 'Close_MA20_ratio', 'Close_MA60_ratio',
            'MA5_slope', 'MA_cross',
            'RSI14', 'RSI_change',
            'MACD', 'MACD_hist',
            'BB_position', 'Volume_ratio', 'ATR_ratio',
            'Trend_5d', 'Trend_20d', 'Return_5d', 'Return_20d',
            'Consecutive_up', 'Consecutive_down',
            'Body_pct', 'Upper_shadow', 'Lower_shadow',
            'Momentum_1d', 'Momentum_5d', 'Momentum_10d', 'Momentum_accel',
            'Price_vs_52w_high'
        ]
        
        df['target'] = (df['close'].shift(-1) > df['close']).astype(int)
        
        feature_cols = [f for f in features if f in df.columns]
        df_clean = df[feature_cols + ['target']].dropna()
        
        X, y = [], []
        lookback = 20
        
        for i in range(lookback, len(df_clean)):
            window = df_clean[feature_cols].iloc[i-lookback:i]
            X.append(np.concatenate([
                window.mean().values,
                window.std().values,
                window.iloc[-1].values
            ]))
            y.append(df_clean['target'].iloc[i])
        
        return np.array(X), np.array(y)
    
    def analyze(self, symbol: str):
        """혼동 행렬 분석"""
        print(f"\n{'='*70}")
        print(f"📊 {symbol} 혼동 행렬 분석")
        print(f"{'='*70}")
        
        # 데이터
        df = self.fetch_data(symbol)
        if df is None:
            return
        
        df = self.calculate_indicators(df)
        X, y = self.prepare_data(df)
        
        print(f"📈 총 샘플: {len(X)}개")
        print(f"📊 클래스 분포: 상승={sum(y)}, 하강={len(y)-sum(y)} ({sum(y)/len(y)*100:.1f}% / {(len(y)-sum(y))/len(y)*100:.1f}%)")
        
        # 분할
        split = int(len(X) * 0.8)
        X_train, X_test = X[:split], X[split:]
        y_train, y_test = y[:split], y[split:]
        
        print(f"\n📚 학습: {len(X_train)}개, 테스트: {len(X_test)}개")
        
        # 스케일링
        scaler = RobustScaler()
        X_train_scaled = scaler.fit_transform(X_train)
        X_test_scaled = scaler.transform(X_test)
        
        # 모델 학습
        models = {
            'Random Forest': RandomForestClassifier(n_estimators=200, max_depth=15, random_state=42, n_jobs=-1),
            'Gradient Boosting': GradientBoostingClassifier(n_estimators=150, learning_rate=0.05, max_depth=5, random_state=42),
            'Logistic Regression': LogisticRegression(max_iter=1000, random_state=42)
        }
        
        results = {}
        
        for name, model in models.items():
            model.fit(X_train_scaled, y_train)
            y_pred = model.predict(X_test_scaled)
            
            # 혼동 행렬
            cm = confusion_matrix(y_test, y_pred)
            tn, fp, fn, tp = cm.ravel()
            
            # 메트릭
            acc = accuracy_score(y_test, y_pred)
            prec = precision_score(y_test, y_pred, zero_division=0)
            rec = recall_score(y_test, y_pred, zero_division=0)
            f1 = f1_score(y_test, y_pred, zero_division=0)
            
            # 특이도, 민감도
            specificity = tn / (tn + fp) if (tn + fp) > 0 else 0
            sensitivity = tp / (tp + fn) if (tp + fn) > 0 else 0
            
            results[name] = {
                'cm': cm, 'tn': tn, 'fp': fp, 'fn': fn, 'tp': tp,
                'acc': acc, 'prec': prec, 'rec': rec, 'f1': f1,
                'specificity': specificity, 'sensitivity': sensitivity
            }
        
        # 결과 출력
        for name, r in results.items():
            print(f"\n{'─'*70}")
            print(f"🤖 {name}")
            print(f"{'─'*70}")
            
            # 혼동 행렬 시각화
            print(f"\n📋 혼동 행렬:")
            print(f"                    예측")
            print(f"                 하강    상승")
            print(f"    실제  하강   [{r['tn']:3d}]   [{r['fp']:3d}]   (특이도: {r['specificity']:.2%})")
            print(f"          상승   [{r['fn']:3d}]   [{r['tp']:3d}]   (민감도: {r['sensitivity']:.2%})")
            
            print(f"\n📊 성능 지표:")
            print(f"   정확도(Accuracy):    {r['acc']*100:6.2f}%")
            print(f"   정밀도(Precision):   {r['prec']*100:6.2f}% (예측 상승 중 실제 상승 비율)")
            print(f"   재현율(Recall):      {r['rec']*100:6.2f}% (실제 상승 중 예측 상승 비율)")
            print(f"   F1-Score:            {r['f1']*100:6.2f}%")
            print(f"   민감도(Sensitivity): {r['sensitivity']*100:6.2f}% (상승 감지율)")
            print(f"   특이도(Specificity): {r['specificity']*100:6.2f}% (하강 감지율)")
            
            # 해석
            print(f"\n💡 해석:")
            if r['prec'] > 0.55:
                print(f"   ✅ 상승 예측이 {r['prec']:.1%}로 신뢰할 만함")
            else:
                print(f"   ⚠️ 상승 예측 신뢰도 낮음 ({r['prec']:.1%})")
            
            if r['rec'] > 0.55:
                print(f"   ✅ 상승 기회를 {r['rec']:.1%} 놓치지 않음")
            else:
                print(f"   ⚠️ 상승 기회를 많이 놓침 ({r['rec']:.1%})")
        
        # 비교 요약
        print(f"\n{'='*70}")
        print(f"📈 모델 비교 요약")
        print(f"{'='*70}")
        print(f"{'모델':<20} {'정확도':<10} {'정밀도':<10} {'재현율':<10} {'F1':<10}")
        print(f"{'─'*70}")
        for name, r in results.items():
            print(f"{name:<20} {r['acc']*100:>8.1f}%   {r['prec']*100:>8.1f}%   {r['rec']*100:>8.1f}%   {r['f1']*100:>8.1f}%")
        
        print(f"{'='*70}\n")


def main():
    if len(sys.argv) < 2:
        print("사용법: python3 confusion_matrix_analysis.py [종목코드]")
        print("예시: python3 confusion_matrix_analysis.py 005930")
        sys.exit(1)
    
    symbol = sys.argv[1].zfill(6)
    
    analyzer = ConfusionMatrixAnalyzer()
    analyzer.analyze(symbol)


if __name__ == '__main__':
    main()
