#!/usr/bin/env python3
"""
Meta Labeling Backtest System (Simplified)
메타 라벨링 기반 방향 예측 + 백테스트

구조:
1. Primary Model (1차): 방향 예측 (Up/Down)
2. Meta Model (2차): 1차 모델의 예측이 맞을지 틀릴지 예측
3. Combined: 1차(상승) AND 2차(맞을 확률 높음) → 매수
"""

import sys
import warnings
import numpy as np
import pandas as pd
from datetime import datetime
from typing import Optional, Dict
from dataclasses import dataclass

warnings.filterwarnings('ignore')

from sklearn.preprocessing import RobustScaler
from sklearn.ensemble import RandomForestClassifier, GradientBoostingClassifier
from sklearn.metrics import accuracy_score

from fdr_wrapper import FDRWrapper


@dataclass
class MetaLabelingResult:
    symbol: str
    primary_acc: float
    meta_acc: float
    combined_acc: float
    primary_return: float
    combined_return: float
    buy_hold_return: float
    total_trades: int
    win_rate: float


class MetaLabelingBacktest:
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
    
    def calculate_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        """핵심 지표 계산"""
        df = df.copy()
        
        # 이동평균
        for window in [5, 20, 60]:
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
        df['RSI_overbought'] = (df['RSI14'] > 70).astype(int)
        df['RSI_oversold'] = (df['RSI14'] < 30).astype(int)
        
        # MACD
        exp1 = df['close'].ewm(span=12, adjust=False).mean()
        exp2 = df['close'].ewm(span=26, adjust=False).mean()
        df['MACD'] = exp1 - exp2
        df['MACD_hist'] = df['MACD'] - df['MACD'].ewm(span=9, adjust=False).mean()
        
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
        df['ATR_percentile'] = df['ATR_ratio'].rolling(20).apply(lambda x: pd.Series(x).rank(pct=True).iloc[-1] if len(x) > 0 else 0.5)
        
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
        
        return df
    
    def get_features(self, df: pd.DataFrame, lookback: int = 20):
        """피처 추출"""
        features = [
            'Close_MA5_ratio', 'Close_MA20_ratio', 'Close_MA60_ratio',
            'MA5_slope', 'MA_cross',
            'RSI14', 'RSI_change', 'RSI_overbought', 'RSI_oversold',
            'MACD', 'MACD_hist',
            'BB_position', 'BB_width',
            'Volume_ratio', 'Volume_spike',
            'ATR_ratio', 'ATR_percentile',
            'Trend_5d', 'Trend_20d', 'Return_5d', 'Return_20d',
            'Consecutive_up', 'Consecutive_down',
            'Body_pct', 'Upper_shadow', 'Lower_shadow',
            'Momentum_1d', 'Momentum_5d', 'Momentum_accel',
            'Price_vs_52w_high'
        ]
        
        feature_cols = [f for f in features if f in df.columns]
        
        X, y = [], []
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
        
        return np.array(X), np.array(y), feature_cols
    
    def get_meta_features(self, df: pd.DataFrame, primary_preds: np.ndarray, primary_confs: np.ndarray, feature_cols: list, lookback: int = 20):
        """메타 모델 피처 추출"""
        df_temp = df.copy()
        
        # 1차 모델 결과 추가
        df_temp['primary_pred'] = np.nan
        df_temp['primary_conf'] = np.nan
        df_temp.loc[20:20+len(primary_preds)-1, 'primary_pred'] = primary_preds
        df_temp.loc[20:20+len(primary_confs)-1, 'primary_conf'] = primary_confs
        
        # 메타 피처 = 기존 피처 + 1차 모델 결과
        meta_feature_cols = feature_cols + ['primary_pred', 'primary_conf']
        
        X_meta, y_meta = [], []
        for i in range(lookback, len(df_temp)):
            if i < lookback + len(primary_preds):
                window = df_temp[meta_feature_cols].iloc[i-lookback:i]
                if window.isnull().any().any():
                    continue
                feat = np.concatenate([
                    window.mean().values,
                    window.std().values,
                    window.iloc[-1].values
                ])
                X_meta.append(feat)
                
                # 메타 타겟: 1차 모델이 맞았는지?
                actual = 1 if df_temp['close'].iloc[i] > df_temp['close'].iloc[i-1] else 0
                pred = primary_preds[i - lookback]
                y_meta.append(1 if actual == pred else 0)
        
        return np.array(X_meta), np.array(y_meta), meta_feature_cols
    
    def walk_forward_backtest(self, symbol: str, train_days: int = 100, step_days: int = 5):
        print(f"\n{'='*70}")
        print(f"🔮 {symbol} 메타 라벨링 백테스트")
        print(f"{'='*70}")
        
        df = self.fetch_data(symbol)
        if df is None:
            return None
        
        df = self.calculate_indicators(df)
        df_clean = df.dropna().reset_index(drop=True)
        
        if len(df_clean) < 200:
            print(f"❌ 데이터 부족: {len(df_clean)}일")
            return None
        
        print(f"📊 총 데이터: {len(df_clean)}일")
        
        results = {
            'date': [], 'price': [], 'actual_return': [],
            'primary_pred': [], 'primary_correct': [],
            'meta_pred': [], 'combined_signal': [], 'trade_return': []
        }
        
        start_idx = train_days
        
        for current_idx in range(start_idx, len(df_clean) - step_days, step_days):
            train_df = df_clean.iloc[:current_idx].copy()
            
            # 1차 모델 학습
            X_p, y_p, feature_cols = self.get_features(train_df)
            if len(X_p) < 50:
                continue
            
            scaler_p = RobustScaler()
            X_p_scaled = scaler_p.fit_transform(X_p)
            
            primary_model = RandomForestClassifier(n_estimators=100, max_depth=10, random_state=42, n_jobs=-1)
            primary_model.fit(X_p_scaled, y_p)
            
            # 1차 모델 훈련 데이터 예측 (메타 모델용)
            primary_train_pred = primary_model.predict(X_p_scaled)
            primary_train_proba = primary_model.predict_proba(X_p_scaled)
            primary_train_conf = np.max(primary_train_proba, axis=1)
            
            # 메타 모델 학습
            X_m, y_m, meta_feature_cols = self.get_meta_features(train_df, primary_train_pred, primary_train_conf, feature_cols)
            
            meta_model = None
            if len(X_m) >= 30 and len(np.unique(y_m)) >= 2:
                scaler_m = RobustScaler()
                X_m_scaled = scaler_m.fit_transform(X_m)
                
                meta_model = GradientBoostingClassifier(n_estimators=100, learning_rate=0.05, max_depth=4, random_state=42)
                meta_model.fit(X_m_scaled, y_m)
            
            # 테스트
            for offset in range(step_days):
                test_idx = current_idx + offset
                if test_idx >= len(df_clean) - 1:
                    break
                
                test_df = df_clean.iloc[:test_idx]
                if len(test_df) < 20:
                    continue
                
                # 1차 모델 예측
                X_p_test, _, _ = self.get_features(test_df)
                if len(X_p_test) == 0:
                    continue
                X_p_test_scaled = scaler_p.transform(X_p_test[-1:])
                primary_pred = primary_model.predict(X_p_test_scaled)[0]
                primary_proba = primary_model.predict_proba(X_p_test_scaled)[0]
                primary_conf = max(primary_proba)
                
                # 메타 모델 예측
                if meta_model is not None:
                    X_m_test, _, _ = self.get_meta_features(test_df, np.array([primary_pred]), np.array([primary_conf]), feature_cols)
                    if len(X_m_test) > 0:
                        X_m_test_scaled = scaler_m.transform(X_m_test[-1:])
                        meta_pred = meta_model.predict(X_m_test_scaled)[0]
                    else:
                        meta_pred = 1
                else:
                    meta_pred = 1
                
                # 결합: 1차(상승) AND 메타(맞을 확률 높음)
                combined_signal = (primary_pred == 1) and (meta_pred == 1)
                
                # 실제 결과
                actual_return = (df_clean['close'].iloc[test_idx + 1] / df_clean['close'].iloc[test_idx] - 1) * 100
                actual_direction = 1 if actual_return > 0 else 0
                primary_correct = (primary_pred == actual_direction)
                
                results['date'].append(df_clean['date'].iloc[test_idx] if 'date' in df_clean else test_idx)
                results['price'].append(df_clean['close'].iloc[test_idx])
                results['actual_return'].append(actual_return)
                results['primary_pred'].append(primary_pred)
                results['primary_correct'].append(primary_correct)
                results['meta_pred'].append(meta_pred)
                results['combined_signal'].append(combined_signal)
                results['trade_return'].append(actual_return if combined_signal else 0)
        
        return self._analyze_results(results)
    
    def _analyze_results(self, results: Dict) -> MetaLabelingResult:
        if len(results['date']) == 0:
            return None
        
        df = pd.DataFrame(results)
        
        # 정확도
        primary_acc = df['primary_correct'].mean()
        meta_acc = ((df['meta_pred'] == 1) == df['primary_correct']).mean()
        
        combined_signals = df[df['combined_signal'] == True]
        combined_acc = (combined_signals['actual_return'] > 0).mean() if len(combined_signals) > 0 else 0
        
        # 수익률
        buy_hold = (df['price'].iloc[-1] / df['price'].iloc[0] - 1) * 100
        primary_ret = df[df['primary_pred'] == 1]['actual_return'].sum()
        combined_ret = df['trade_return'].sum()
        
        # 거래 통계
        total_trades = df['combined_signal'].sum()
        win_rate = (combined_signals['actual_return'] > 0).mean() if len(combined_signals) > 0 else 0
        
        return MetaLabelingResult(
            symbol='Unknown',
            primary_acc=primary_acc,
            meta_acc=meta_acc,
            combined_acc=combined_acc,
            primary_return=primary_ret,
            combined_return=combined_ret,
            buy_hold_return=buy_hold,
            total_trades=int(total_trades),
            win_rate=win_rate
        )
    
    def print_results(self, result: MetaLabelingResult, symbol: str):
        print(f"\n{'='*70}")
        print(f"📊 {symbol} 메타 라벨링 백테스트 결과")
        print(f"{'='*70}")
        
        print(f"\n🎯 예측 정확도:")
        print(f"   1차 모델 (방향):     {result.primary_acc*100:.1f}%")
        print(f"   메타 모델 (맞춤여부): {result.meta_acc*100:.1f}%")
        print(f"   결합 모델:           {result.combined_acc*100:.1f}%")
        
        print(f"\n💰 수익률 비교:")
        print(f"   Buy & Hold:    {result.buy_hold_return:+.2f}%")
        print(f"   1차 모델:      {result.primary_return:+.2f}%")
        print(f"   결합 모델:     {result.combined_return:+.2f}%")
        
        print(f"\n📈 거래 통계:")
        print(f"   총 거래 횟수: {result.total_trades}회")
        print(f"   승률:         {result.win_rate*100:.1f}%")
        
        if result.combined_return > result.primary_return:
            print(f"\n   ✅ 메타 라벨링이 1차 모델보다 우수!")
        if result.combined_return > result.buy_hold_return:
            print(f"   ✅ 결합 모델이 Buy & Hold를 이김!")
        
        print(f"{'='*70}\n")


def main():
    if len(sys.argv) < 2:
        print("사용법: python3 meta_labeling_backtest.py [종목코드]")
        print("예시: python3 meta_labeling_backtest.py 005930")
        sys.exit(1)
    
    symbol = sys.argv[1].zfill(6)
    
    backtest = MetaLabelingBacktest()
    result = backtest.walk_forward_backtest(symbol)
    
    if result:
        backtest.print_results(result, symbol)
    else:
        print(f"❌ {symbol} 백테스트 실패")
        sys.exit(1)


if __name__ == '__main__':
    main()
