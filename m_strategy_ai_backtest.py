#!/usr/bin/env python3
"""
M-Strategy (Meta Labeling) + AI Prediction Backtest System
M전략(메타 레이블링) + AI 예측 결합 백테스트

진입 조건:
1. Primary Model: 상승 예측
2. Meta Model: 예측이 맞을 것으로 예측 (확신도 >= threshold)
3. AI 예측: 상승 (확신도 >= threshold)

청산 조건:
- 목표가 (+15%) 도달
- 손절가 (-7%) 도달  
- 보유 20일 경과
"""

import json
import warnings
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass

warnings.filterwarnings('ignore')

from fdr_wrapper import FDRWrapper
from sklearn.preprocessing import RobustScaler
from sklearn.ensemble import RandomForestClassifier, GradientBoostingClassifier


@dataclass
class Trade:
    symbol: str
    entry_date: str
    entry_price: float
    exit_date: Optional[str] = None
    exit_price: Optional[float] = None
    return_pct: float = 0
    holding_days: int = 0
    exit_reason: str = ''
    primary_pred: str = ''
    meta_confidence: float = 0
    ai_confidence: float = 0


class MStrategyAIPredictor:
    """M전략용 AI 예측기 (Primary + Meta Model)"""
    
    def __init__(self):
        self.fdr = FDRWrapper()
        self.primary_model = None
        self.meta_model = None
        self.scaler_primary = RobustScaler()
        self.scaler_meta = RobustScaler()
        self.lookback = 20
        
    def get_training_stocks(self) -> List[str]:
        return ['005930', '000660', '051910', '005380', '035720', 
                '068270', '207940', '006400', '000270', '012330',
                '005490', '028260', '105560', '018260', '032830']
    
    def calculate_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """기술적 지표 계산"""
        df = df.copy()
        
        for window in [5, 10, 20, 60]:
            df[f'MA{window}'] = df['close'].rolling(window=window).mean()
            df[f'Close_MA{window}_ratio'] = df['close'] / df[f'MA{window}'] - 1
        
        # RSI
        delta = df['close'].diff()
        gain = delta.where(delta > 0, 0).rolling(window=14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
        df['RSI14'] = 100 - (100 / (1 + gain / (loss + 1e-10)))
        
        # MACD
        exp1 = df['close'].ewm(span=12, adjust=False).mean()
        exp2 = df['close'].ewm(span=26, adjust=False).mean()
        df['MACD'] = exp1 - exp2
        df['MACD_signal'] = df['MACD'].ewm(span=9, adjust=False).mean()
        
        # 볼린저
        ma20 = df['close'].rolling(window=20).mean()
        std20 = df['close'].rolling(window=20).std()
        df['BB_position'] = (df['close'] - (ma20 - std20*2)) / ((ma20 + std20*2) - (ma20 - std20*2) + 1e-10)
        
        # 거래량
        df['Volume_MA20'] = df['volume'].rolling(window=20).mean()
        df['Volume_ratio'] = df['volume'] / df['Volume_MA20']
        
        # 변동성
        df['volatility'] = df['close'].rolling(window=20).std() / df['close'].rolling(window=20).mean()
        
        return df
    
    def train(self):
        """Primary + Meta 모델 학습"""
        print("📊 M-Strategy AI 모델 학습 중...")
        
        # Primary Model 학습 데이터
        X_primary_list, y_primary_list = [], []
        # Meta Model 학습 데이터
        X_meta_list, y_meta_list = [], []
        
        for symbol in self.get_training_stocks():
            try:
                df = self.fdr.get_price(symbol, min_days=400)
                if df is None or len(df) < 200:
                    continue
                
                df = self.calculate_features(df)
                df = df.dropna()
                
                features = ['Close_MA5_ratio', 'Close_MA20_ratio', 'RSI14', 'MACD', 
                           'BB_position', 'Volume_ratio', 'Close_MA60_ratio', 'volatility']
                
                for i in range(self.lookback, len(df) - 5):  # 5일 후 확인을 위해 -5
                    window = df[features].iloc[i-self.lookback:i]
                    feat = np.concatenate([window.mean().values, window.iloc[-1].values])
                    
                    # Primary label: 5일 후 상승/하락
                    future_return = (df['close'].iloc[i+5] / df['close'].iloc[i] - 1) * 100
                    primary_label = 1 if future_return > 0 else 0
                    
                    X_primary_list.append(feat)
                    y_primary_list.append(primary_label)
                    
                    # Meta label: Primary 예측이 맞았는지
                    # 여기서는 실제 결과를 알고 있으므로 meta label 생성
                    # 상승 예측일 때 실제 상승이면 1, 하락이면 0
                    # 하락 예측일 때 실제 하락이면 1, 상승이면 0
                    # 간단화: Primary가 예측한 방향이 맞았는지
                    meta_features = np.concatenate([
                        feat,  # 원래 특성
                        [primary_label],  # Primary 예측
                        [abs(future_return)],  # 예상 수익률 크기
                        [df['volatility'].iloc[i]]  # 현재 변동성
                    ])
                    
                    X_meta_list.append(meta_features)
                    y_meta_list.append(1 if future_return > 0 else 0)  # 실제로 상승했는지
                    
            except Exception as e:
                continue
        
        if len(X_primary_list) < 100:
            print("❌ 학습 데이터 부족")
            return False
        
        # Primary Model 학습
        X_primary = np.array(X_primary_list)
        y_primary = np.array(y_primary_list)
        X_primary_scaled = self.scaler_primary.fit_transform(X_primary)
        
        self.primary_model = RandomForestClassifier(
            n_estimators=200, max_depth=15, class_weight='balanced', random_state=42, n_jobs=-1
        )
        self.primary_model.fit(X_primary_scaled, y_primary)
        
        # Meta Model 학습
        X_meta = np.array(X_meta_list)
        y_meta = np.array(y_meta_list)
        X_meta_scaled = self.scaler_meta.fit_transform(X_meta)
        
        self.meta_model = GradientBoostingClassifier(
            n_estimators=150, learning_rate=0.05, max_depth=5, random_state=42
        )
        self.meta_model.fit(X_meta_scaled, y_meta)
        
        print(f"   ✅ Primary Model 학습 완료: {len(X_primary)}개 샘플")
        print(f"   ✅ Meta Model 학습 완료: {len(X_meta)}개 샘플")
        return True
    
    def predict(self, symbol: str, date: Optional[str] = None) -> Dict:
        """Primary + Meta 예측"""
        try:
            if date:
                end_date = pd.to_datetime(date)
                start_date = end_date - timedelta(days=150)
                df = self.fdr.get_price(symbol, start=start_date.strftime('%Y-%m-%d'), 
                                       end=end_date.strftime('%Y-%m-%d'))
            else:
                df = self.fdr.get_price(symbol, min_days=100)
            
            if df is None or len(df) < 50:
                return {'direction': 'unknown', 'confidence': 0, 'meta_confidence': 0}
            
            df = self.calculate_features(df)
            df = df.dropna()
            
            if len(df) < self.lookback + 1:
                return {'direction': 'unknown', 'confidence': 0, 'meta_confidence': 0}
            
            features = ['Close_MA5_ratio', 'Close_MA20_ratio', 'RSI14', 'MACD', 
                       'BB_position', 'Volume_ratio', 'Close_MA60_ratio', 'volatility']
            
            window = df[features].iloc[-self.lookback:]
            feat = np.concatenate([window.mean().values, window.iloc[-1].values])
            feat_scaled = self.scaler_primary.transform(feat.reshape(1, -1))
            
            # Primary 예측
            primary_proba = self.primary_model.predict_proba(feat_scaled)[0]
            primary_pred = 1 if primary_proba[1] > 0.5 else 0
            primary_confidence = max(primary_proba) * 100
            
            # Meta 예측 (Primary 예측이 맞을 확률)
            meta_features = np.concatenate([
                feat,
                [primary_pred],
                [primary_confidence / 100],
                [df['volatility'].iloc[-1]]
            ])
            meta_scaled = self.scaler_meta.transform(meta_features.reshape(1, -1))
            meta_proba = self.meta_model.predict_proba(meta_scaled)[0]
            meta_confidence = max(meta_proba) * 100
            
            direction = '상승' if primary_pred == 1 else '하락'
            
            return {
                'direction': direction,
                'confidence': primary_confidence,
                'meta_confidence': meta_confidence,
                'up_prob': primary_proba[1] * 100,
                'meta_up_prob': meta_proba[1] * 100
            }
        except Exception as e:
            return {'direction': 'unknown', 'confidence': 0, 'meta_confidence': 0}


class MStrategyAIBacktest:
    """M전략 + AI 백테스트"""
    
    def __init__(self, initial_capital: float = 100_000_000, 
                 confidence_threshold: float = 60.0,
                 meta_threshold: float = 60.0):
        self.fdr = FDRWrapper()
        self.predictor = MStrategyAIPredictor()
        self.initial_capital = initial_capital
        self.confidence_threshold = confidence_threshold
        self.meta_threshold = meta_threshold
        
        # 전 종목 리스트
        self.all_stocks = self._get_all_stocks()
    
    def _get_all_stocks(self) -> List[str]:
        """전 종목 코드 가져오기"""
        try:
            import sqlite3
            conn = sqlite3.connect('./data/pivot_strategy.db')
            cursor = conn.cursor()
            cursor.execute("SELECT DISTINCT symbol FROM stock_prices LIMIT 1000")
            symbols = [row[0] for row in cursor.fetchall()]
            conn.close()
            return symbols if symbols else ['005930', '000660', '051910', '005380', '035720']
        except:
            return ['005930', '000660', '051910', '005380', '035720', 
                   '068270', '207940', '006400', '000270', '012330',
                   '005490', '028260', '105560', '018260', '032830']
    
    def run_backtest(self, start_date: str = '2025-01-01', end_date: str = '2026-03-18') -> Dict:
        """백테스트 실행"""
        print(f"\n{'='*60}")
        print(f"📊 M-Strategy (Meta Labeling) + AI 백테스트")
        print(f"{'='*60}")
        print(f"기간: {start_date} ~ {end_date}")
        print(f"초기자본: ₩{self.initial_capital:,.0f}")
        print(f"AI 확신도 임계값: {self.confidence_threshold}%")
        print(f"Meta 확신도 임계값: {self.meta_threshold}%")
        print(f"대상 종목: {len(self.all_stocks)}개")
        
        # AI 모델 학습
        if not self.predictor.train():
            return {}
        
        trades = []
        capital = self.initial_capital
        equity_curve = []
        
        # 매월 1일 리밸런싱
        current_date = datetime.strptime(start_date, '%Y-%m-%d')
        end = datetime.strptime(end_date, '%Y-%m-%d')
        
        rebalance_count = 0
        
        while current_date <= end:
            rebalance_count += 1
            print(f"\n📅 {current_date.strftime('%Y-%m-%d')} 리밸런싱... ({rebalance_count})")
            
            # 종목 스캔
            selected = []
            scan_start = (current_date - timedelta(days=200)).strftime('%Y-%m-%d')
            scan_end = current_date.strftime('%Y-%m-%d')
            
            scanned = 0
            for symbol in self.all_stocks[:200]:  # 상위 200개만 스캔
                try:
                    df = self.fdr.get_price(symbol, start=scan_start, end=scan_end)
                    scanned += 1
                    if df is None or len(df) < 60:
                        continue
                    
                    df['date'] = pd.to_datetime(df.index if 'date' not in df.columns else df['date'])
                    df_filtered = df[df['date'] <= current_date]
                    
                    if len(df_filtered) < 60:
                        continue
                    
                    # M-Strategy 예측
                    pred = self.predictor.predict(symbol, date=current_date.strftime('%Y-%m-%d'))
                    
                    # 진입 조건:
                    # 1. Primary: 상승 예측
                    # 2. AI 확신도 >= threshold
                    # 3. Meta 확신도 >= threshold (Primary 예측이 맞을 확신)
                    if (pred['direction'] == '상승' and 
                        pred['confidence'] >= self.confidence_threshold and
                        pred['meta_confidence'] >= self.meta_threshold):
                        
                        selected.append({
                            'symbol': symbol,
                            'price': df_filtered['close'].iloc[-1],
                            'primary_confidence': pred['confidence'],
                            'meta_confidence': pred['meta_confidence'],
                            'up_prob': pred['up_prob']
                        })
                    
                except Exception as e:
                    continue
            
            print(f"   스캔: {scanned}개, 조건 충족: {len(selected)}개")
            
            if len(selected) == 0:
                print(f"   ⏭️ 선정 종목 없음")
                equity_curve.append({'date': current_date.strftime('%Y-%m-%d'), 'equity': capital})
                current_date += timedelta(days=30)
                continue
            
            # Meta 점수순 정렬 후 상위 5개만 선택
            selected.sort(key=lambda x: x['meta_confidence'], reverse=True)
            selected = selected[:5]
            
            print(f"   ✅ 선정: {len(selected)}개 종목")
            for s in selected:
                print(f"      {s['symbol']}: Primary {s['primary_confidence']:.1f}%, Meta {s['meta_confidence']:.1f}%")
            
            # 포지션 분할 (동일 비중)
            position_size = capital / len(selected)
            
            # 1개월 보유 후 결과 계산
            exit_date = current_date + timedelta(days=30)
            
            for pos in selected:
                try:
                    entry_start = (current_date - timedelta(days=60)).strftime('%Y-%m-%d')
                    exit_end = (exit_date + timedelta(days=5)).strftime('%Y-%m-%d')
                    
                    df = self.fdr.get_price(pos['symbol'], start=entry_start, end=exit_end)
                    df['date'] = pd.to_datetime(df.index if 'date' not in df.columns else df['date'])
                    
                    entry_df = df[df['date'] <= current_date]
                    exit_df = df[df['date'] <= exit_date]
                    
                    if len(entry_df) == 0 or len(exit_df) == 0:
                        continue
                    
                    entry_price = entry_df['close'].iloc[-1]
                    exit_price = exit_df['close'].iloc[-1]
                    
                    # 목표가/손절가 체크
                    target_price = entry_price * 1.15
                    stop_price = entry_price * 0.93
                    
                    exit_reason = '기간만료'
                    for idx, row in exit_df.iterrows():
                        if row['high'] >= target_price:
                            exit_price = target_price
                            exit_reason = '목표가도달'
                            break
                        elif row['low'] <= stop_price:
                            exit_price = stop_price
                            exit_reason = '손절'
                            break
                    
                    return_pct = (exit_price / entry_price - 1) * 100
                    holding_days = min(30, len(exit_df) - len(entry_df) + 1)
                    
                    trades.append(Trade(
                        symbol=pos['symbol'],
                        entry_date=current_date.strftime('%Y-%m-%d'),
                        entry_price=entry_price,
                        exit_date=exit_df['date'].iloc[-1].strftime('%Y-%m-%d') if hasattr(exit_df['date'].iloc[-1], 'strftime') else str(exit_df['date'].iloc[-1]),
                        exit_price=exit_price,
                        return_pct=return_pct,
                        holding_days=holding_days,
                        exit_reason=exit_reason,
                        primary_pred='상승',
                        meta_confidence=pos['meta_confidence'],
                        ai_confidence=pos['primary_confidence']
                    ))
                    
                    # 자본 업데이트
                    pnl = position_size * (return_pct / 100)
                    capital += pnl
                    
                except Exception as e:
                    continue
            
            equity_curve.append({'date': current_date.strftime('%Y-%m-%d'), 'equity': capital})
            current_date += timedelta(days=30)
        
        # 결과 분석
        return self._analyze_results(trades, equity_curve)
    
    def _analyze_results(self, trades: List[Trade], equity_curve: List[Dict]) -> Dict:
        """결과 분석"""
        if len(trades) == 0:
            print("\n❌ 거래 없음")
            return {}
        
        df_trades = pd.DataFrame([{
            'symbol': t.symbol,
            'entry_date': t.entry_date,
            'return_pct': t.return_pct,
            'holding_days': t.holding_days,
            'exit_reason': t.exit_reason,
            'meta_confidence': t.meta_confidence,
            'ai_confidence': t.ai_confidence
        } for t in trades])
        
        total_return = (equity_curve[-1]['equity'] / self.initial_capital - 1) * 100
        win_trades = len(df_trades[df_trades['return_pct'] > 0])
        lose_trades = len(df_trades[df_trades['return_pct'] <= 0])
        
        # 최대 낙폭
        equity_values = [e['equity'] for e in equity_curve]
        peak = equity_values[0]
        max_dd = 0
        for equity in equity_values:
            if equity > peak:
                peak = equity
            dd = (peak - equity) / peak * 100
            if dd > max_dd:
                max_dd = dd
        
        # 청산 사유별 통계
        reason_stats = df_trades.groupby('exit_reason').agg({
            'return_pct': ['count', 'mean']
        }).round(2)
        
        # Meta confidence별 승률 분석
        high_meta = df_trades[df_trades['meta_confidence'] >= 70]
        low_meta = df_trades[df_trades['meta_confidence'] < 70]
        
        print(f"\n{'='*60}")
        print(f"📈 M-Strategy + AI 백테스트 결과")
        print(f"{'='*60}")
        print(f"총 거래 횟수: {len(trades)}회")
        print(f"승률: {win_trades/len(trades)*100:.1f}% ({win_trades}/{len(trades)})")
        print(f"평균 수익률: {df_trades['return_pct'].mean():.2f}%")
        print(f"총 수익률: {total_return:.2f}%")
        print(f"최대 낙폭: {max_dd:.2f}%")
        print(f"최종 자본: ₩{equity_curve[-1]['equity']:,.0f}")
        
        print(f"\n📊 청산 사유:")
        for reason, stats in reason_stats.iterrows():
            print(f"   {reason}: {int(stats[('return_pct', 'count')])}회 (평균 {stats[('return_pct', 'mean')]:.2f}%)")
        
        if len(high_meta) > 0:
            high_win = len(high_meta[high_meta['return_pct'] > 0])
            print(f"\n📊 Meta Confidence >= 70%: {len(high_meta)}회, 승률 {high_win/len(high_meta)*100:.1f}%")
        if len(low_meta) > 0:
            low_win = len(low_meta[low_meta['return_pct'] > 0])
            print(f"📊 Meta Confidence < 70%: {len(low_meta)}회, 승률 {low_win/len(low_meta)*100:.1f}%")
        
        # 결과 저장
        result = {
            'total_trades': len(trades),
            'win_rate': win_trades / len(trades) * 100,
            'avg_return': df_trades['return_pct'].mean(),
            'total_return': total_return,
            'max_drawdown': max_dd,
            'final_capital': equity_curve[-1]['equity'],
            'trades': [t.__dict__ for t in trades],
            'equity_curve': equity_curve
        }
        
        # JSON 저장
        import os
        os.makedirs('./reports/m_strategy', exist_ok=True)
        timestamp = datetime.now().strftime('%Y%m%d_%H%M')
        filepath = f'./reports/m_strategy/m_ai_backtest_{timestamp}.json'
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(result, f, ensure_ascii=False, indent=2, default=str)
        print(f"\n💾 결과 저장: {filepath}")
        
        return result


if __name__ == '__main__':
    backtest = MStrategyAIBacktest(
        initial_capital=100_000_000,
        confidence_threshold=60.0,
        meta_threshold=60.0
    )
    results = backtest.run_backtest('2025-01-01', '2026-03-18')
