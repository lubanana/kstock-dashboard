#!/usr/bin/env python3
"""
S-Strategy + AI Prediction Backtest System
S전략(S1/S2/S3) + AI 예측 결합 백테스트

진입 조건:
1. S1/S2/S3 중 하나 이상 해당
2. AI 예측 상승
3. 확신도 >= 60%

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
    strategy: str = ''  # S1, S2, S3


class SStrategyAIPredictor:
    """S전략용 AI 예측기"""
    
    def __init__(self):
        self.fdr = FDRWrapper()
        self.models = {}
        self.scaler = RobustScaler()
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
        
        return df
    
    def train(self):
        """모델 학습"""
        print("📊 AI 모델 학습 중...")
        
        X_list, y_list = [], []
        
        for symbol in self.get_training_stocks():
            try:
                df = self.fdr.get_price(symbol, min_days=400)
                if df is None or len(df) < 200:
                    continue
                
                df = self.calculate_features(df)
                df = df.dropna()
                
                features = ['Close_MA5_ratio', 'Close_MA20_ratio', 'RSI14', 'MACD', 
                           'BB_position', 'Volume_ratio', 'Close_MA60_ratio']
                
                for i in range(self.lookback, len(df)):
                    window = df[features].iloc[i-self.lookback:i]
                    feat = np.concatenate([window.mean().values, window.iloc[-1].values])
                    X_list.append(feat)
                    y_list.append(1 if df['close'].iloc[i] > df['close'].iloc[i-1] else 0)
                    
            except Exception as e:
                continue
        
        if len(X_list) < 100:
            print("❌ 학습 데이터 부족")
            return False
        
        X = np.array(X_list)
        y = np.array(y_list)
        
        X_scaled = self.scaler.fit_transform(X)
        
        # Random Forest
        self.models['rf'] = RandomForestClassifier(
            n_estimators=200, max_depth=15, class_weight='balanced', random_state=42, n_jobs=-1
        )
        self.models['rf'].fit(X_scaled, y)
        
        # Gradient Boosting
        self.models['gb'] = GradientBoostingClassifier(
            n_estimators=150, learning_rate=0.05, max_depth=5, random_state=42
        )
        self.models['gb'].fit(X_scaled, y)
        
        print(f"   ✅ 학습 완료: {len(X)}개 샘플")
        return True
    
    def predict(self, symbol: str, date: Optional[str] = None) -> Dict:
        """예측"""
        try:
            if date:
                end_date = pd.to_datetime(date)
                start_date = end_date - timedelta(days=150)
                df = self.fdr.get_price(symbol, start=start_date.strftime('%Y-%m-%d'), 
                                       end=end_date.strftime('%Y-%m-%d'))
            else:
                df = self.fdr.get_price(symbol, min_days=100)
            
            if df is None or len(df) < 50:
                return {'direction': 'unknown', 'confidence': 0}
            
            df = self.calculate_features(df)
            df = df.dropna()
            
            if len(df) < self.lookback + 1:
                return {'direction': 'unknown', 'confidence': 0}
            
            features = ['Close_MA5_ratio', 'Close_MA20_ratio', 'RSI14', 'MACD', 
                       'BB_position', 'Volume_ratio', 'Close_MA60_ratio']
            
            window = df[features].iloc[-self.lookback:]
            feat = np.concatenate([window.mean().values, window.iloc[-1].values])
            feat_scaled = self.scaler.transform(feat.reshape(1, -1))
            
            # 앙상블 예측
            pred_rf = self.models['rf'].predict_proba(feat_scaled)[0]
            pred_gb = self.models['gb'].predict_proba(feat_scaled)[0]
            
            avg_proba = (pred_rf + pred_gb) / 2
            direction = '상승' if avg_proba[1] > 0.5 else '하락'
            confidence = max(avg_proba) * 100
            
            return {
                'direction': direction,
                'confidence': confidence,
                'up_prob': avg_proba[1] * 100
            }
        except Exception as e:
            return {'direction': 'unknown', 'confidence': 0}


class SStrategyAIBacktest:
    """S전략 + AI 백테스트"""
    
    def __init__(self, initial_capital: float = 100_000_000, 
                 confidence_threshold: float = 60.0):
        self.fdr = FDRWrapper()
        self.predictor = SStrategyAIPredictor()
        self.initial_capital = initial_capital
        self.confidence_threshold = confidence_threshold
        
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
    
    def calculate_s1_score(self, df: pd.DataFrame) -> Tuple[bool, float]:
        """S1: 거래대금 TOP 20 유사 점수"""
        if len(df) < 20:
            return False, 0
        
        avg_volume = df['volume'].rolling(20).mean().iloc[-1]
        avg_price = df['close'].rolling(20).mean().iloc[-1]
        avg_amount = avg_volume * avg_price
        
        # 100억 이상 거래대금
        if avg_amount >= 10e9:
            return True, min(100, avg_amount / 10e9 * 50)
        return False, 0
    
    def calculate_s2_score(self, df: pd.DataFrame) -> Tuple[bool, float]:
        """S2: 턴어라운드 점수"""
        if len(df) < 60:
            return False, 0
        
        # 60일 저점 대비 반등률
        low_60d = df['close'].rolling(60).min().iloc[-1]
        current = df['close'].iloc[-1]
        rebound = (current / low_60d - 1) * 100
        
        # RSI
        delta = df['close'].diff()
        gain = delta.where(delta > 0, 0).rolling(window=14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
        rsi = 100 - (100 / (1 + gain / (loss + 1e-10)))
        current_rsi = rsi.iloc[-1]
        
        # 조건: 10% 이상 반등 + RSI 40-60
        if rebound >= 10 and 40 <= current_rsi <= 60:
            score = 50 + rebound * 2 + (60 - abs(current_rsi - 50))
            return True, min(100, score)
        return False, 0
    
    def calculate_s3_score(self, df: pd.DataFrame) -> Tuple[bool, float]:
        """S3: 신규 모멘텀 점수"""
        if len(df) < 26:
            return False, 0
        
        # MACD
        exp1 = df['close'].ewm(span=12, adjust=False).mean()
        exp2 = df['close'].ewm(span=26, adjust=False).mean()
        macd = (exp1 - exp2).iloc[-1]
        
        # RSI
        delta = df['close'].diff()
        gain = delta.where(delta > 0, 0).rolling(window=14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
        rsi = 100 - (100 / (1 + gain / (loss + 1e-10)))
        current_rsi = rsi.iloc[-1]
        
        # 조건: MACD > 0 + RSI > 50
        if macd > 0 and current_rsi > 50:
            score = 50 + min(30, macd / 1000) + (current_rsi - 50) * 1.5
            return True, min(100, score)
        return False, 0
    
    def run_backtest(self, start_date: str = '2025-01-01', end_date: str = '2026-03-18') -> Dict:
        """백테스트 실행"""
        print(f"\n{'='*60}")
        print(f"📊 S-Strategy + AI 백테스트")
        print(f"{'='*60}")
        print(f"기간: {start_date} ~ {end_date}")
        print(f"초기자본: ₩{self.initial_capital:,.0f}")
        print(f"AI 확신도 임계값: {self.confidence_threshold}%")
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
            for symbol in self.all_stocks[:200]:  # 상위 200개만 스캔 (속도 고려)
                try:
                    df = self.fdr.get_price(symbol, start=scan_start, end=scan_end)
                    scanned += 1
                    if df is None or len(df) < 60:
                        continue
                    
                    df['date'] = pd.to_datetime(df.index if 'date' not in df.columns else df['date'])
                    df_filtered = df[df['date'] <= current_date]
                    
                    if len(df_filtered) < 60:
                        continue
                    
                    # S전략 체크
                    s1_pass, s1_score = self.calculate_s1_score(df_filtered)
                    s2_pass, s2_score = self.calculate_s2_score(df_filtered)
                    s3_pass, s3_score = self.calculate_s3_score(df_filtered)
                    
                    strategies = []
                    if s1_pass: strategies.append(('S1', s1_score))
                    if s2_pass: strategies.append(('S2', s2_score))
                    if s3_pass: strategies.append(('S3', s3_score))
                    
                    if not strategies:
                        continue
                    
                    # AI 예측
                    pred = self.predictor.predict(symbol, date=current_date.strftime('%Y-%m-%d'))
                    
                    # AI 조건: 상승 예측 + 확신도 >= 임계값
                    if pred['direction'] != '상승' or pred['confidence'] < self.confidence_threshold:
                        continue
                    
                    # 최고 점수 전략 선택
                    best_strategy = max(strategies, key=lambda x: x[1])
                    
                    selected.append({
                        'symbol': symbol,
                        'price': df_filtered['close'].iloc[-1],
                        'strategy': best_strategy[0],
                        'strategy_score': best_strategy[1],
                        'ai_confidence': pred['confidence'],
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
            
            # 점수순 정렬 후 상위 5개만 선택
            selected.sort(key=lambda x: x['strategy_score'] + x['ai_confidence'], reverse=True)
            selected = selected[:5]
            
            print(f"   ✅ 선정: {len(selected)}개 종목")
            for s in selected:
                print(f"      {s['symbol']}: {s['strategy']}/{s['strategy_score']:.0f}점, AI확신도 {s['ai_confidence']:.1f}%")
            
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
                        strategy=pos['strategy']
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
            'strategy': t.strategy
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
        
        # 전략별 통계
        strategy_stats = df_trades.groupby('strategy').agg({
            'return_pct': ['count', 'mean', 'sum']
        }).round(2)
        
        print(f"\n{'='*60}")
        print(f"📈 S-Strategy + AI 백테스트 결과")
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
        
        print(f"\n📊 전략별 결과:")
        for strategy, stats in strategy_stats.iterrows():
            print(f"   {strategy}: {int(stats[('return_pct', 'count')])}회 (평균 {stats[('return_pct', 'mean')]:.2f}%, 총 {stats[('return_pct', 'sum')]:.2f}%)")
        
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
        os.makedirs('./reports/s_strategy', exist_ok=True)
        timestamp = datetime.now().strftime('%Y%m%d_%H%M')
        filepath = f'./reports/s_strategy/s_ai_backtest_{timestamp}.json'
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(result, f, ensure_ascii=False, indent=2, default=str)
        print(f"\n💾 결과 저장: {filepath}")
        
        return result


if __name__ == '__main__':
    backtest = SStrategyAIBacktest(
        initial_capital=100_000_000,
        confidence_threshold=60.0
    )
    results = backtest.run_backtest('2025-01-01', '2026-03-18')
