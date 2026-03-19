#!/usr/bin/env python3
"""
B01 + AI Prediction Backtest System
B01 전략 + AI 예측 결합 백테스트

진입 조건:
1. B01 등급 A 또는 B (score >= 65)
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


class B01AIPredictor:
    """B01용 AI 예측기 (멀티 종목 학습)"""
    
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
            # 백테스트 시점에 맞는 날짜 범위로 데이터 요청
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
            
            rf_proba = self.models['rf'].predict_proba(feat_scaled)[0]
            gb_proba = self.models['gb'].predict_proba(feat_scaled)[0]
            
            avg_proba = (rf_proba + gb_proba) / 2
            confidence = max(avg_proba)
            direction = '상승' if avg_proba[1] > avg_proba[0] else '하띋'
            
            return {
                'direction': direction,
                'confidence': confidence * 100,
                'up_probability': avg_proba[1] * 100
            }
        except Exception as e:
            return {'direction': 'unknown', 'confidence': 0}


class B01AIBacktest:
    """B01 + AI 백테스트"""
    
    def __init__(self, initial_capital: float = 100_000_000, confidence_threshold: float = 60):
        self.fdr = FDRWrapper()
        self.predictor = B01AIPredictor()
        self.initial_capital = initial_capital
        self.confidence_threshold = confidence_threshold
        
        self.b01_stocks = [
            '005930', '000660', '051910', '005380', '035720',
            '068270', '207940', '006400', '000270', '012330',
            '005490', '028260', '105560', '018260', '032830',
            '011200', '030200', '009150', '097950', '051900',
            '128940', '139480', '316140', '018880', '010950',
            '024110', '139130', '298050', '012450', '161390',
            '282330', '032640', '086280', '100090', '950160',
        ]
    
    def calculate_b01_score(self, df: pd.DataFrame) -> Dict:
        """B01 점수 계산"""
        if len(df) < 60:
            return {'score': 0, 'grade': 'F'}
        
        returns = df['close'].pct_change().dropna()
        annual_return = (df['close'].iloc[-1] / df['close'].iloc[0] - 1) * 100 if len(df) > 0 else 0
        volatility = returns.std() * np.sqrt(252) * 100 if len(returns) > 0 else 0
        roe_proxy = annual_return / (volatility + 1e-10) * 10
        
        cummax = df['close'].cummax()
        drawdown = (df['close'] - cummax) / cummax
        max_dd = drawdown.min() * 100
        debt_proxy = abs(max_dd) * 2
        
        df['MA20'] = df['close'].rolling(20).mean()
        trend_strength = (df['close'].iloc[-1] / df['MA20'].iloc[-1] - 1) * 100 if not pd.isna(df['MA20'].iloc[-1]) else 0
        margin_proxy = trend_strength + 10
        
        high_52w = df['close'].rolling(252).max().iloc[-1] if len(df) >= 252 else df['close'].max()
        pbr_proxy = df['close'].iloc[-1] / high_52w * 2 if high_52w > 0 else 2
        
        volume_amount = df['close'].iloc[-1] * df['volume'].rolling(20).mean().iloc[-1]
        
        current = df['close'].iloc[-1]
        high_20d = df['close'].iloc[-21:-1].max() if len(df) >= 21 else df['close'].max()
        breakout = current > high_20d
        
        score = 0
        if roe_proxy >= 15: score += 20
        if debt_proxy <= 50: score += 15
        if margin_proxy >= 10: score += 20
        if pbr_proxy <= 2.0: score += 15
        if volume_amount >= 50 * 1e8: score += 15
        if breakout: score += 15
        
        if score >= 80: grade = 'A'
        elif score >= 65: grade = 'B'
        elif score >= 50: grade = 'C'
        else: grade = 'D'
        
        return {
            'score': score,
            'grade': grade,
            'current_price': df['close'].iloc[-1],
            'breakout': breakout,
            'roe_proxy': roe_proxy,
            'volume_amount': volume_amount / 1e8
        }
    
    def run_backtest(self, start_date: str = '2025-01-01', end_date: str = '2026-03-18') -> Dict:
        """백테스트 실행"""
        print(f"\n{'='*60}")
        print(f"📊 B01 + AI 백테스트")
        print(f"{'='*60}")
        print(f"기간: {start_date} ~ {end_date}")
        print(f"초기자본: ₩{self.initial_capital:,.0f}")
        print(f"AI 확신도 임계값: {self.confidence_threshold}%")
        
        # AI 모델 학습
        if not self.predictor.train():
            return {}
        
        trades = []
        capital = self.initial_capital
        equity_curve = []
        
        # 매월 1일 리밸런싱
        current_date = datetime.strptime(start_date, '%Y-%m-%d')
        end = datetime.strptime(end_date, '%Y-%m-%d')
        
        while current_date <= end:
            print(f"\n📅 {current_date.strftime('%Y-%m-%d')} 리밸런싱...")
            
            # 종목 스캔
            selected = []
            scan_start = (current_date - timedelta(days=200)).strftime('%Y-%m-%d')
            scan_end = current_date.strftime('%Y-%m-%d')
            
            for symbol in self.b01_stocks:
                try:
                    # 백테스트 시점에 맞는 날짜 범위로 데이터 요청
                    df = self.fdr.get_price(symbol, start=scan_start, end=scan_end)
                    if df is None or len(df) < 60:
                        continue
                    
                    # 데이터가 해당 날짜까지 있는지 확인
                    df['date'] = pd.to_datetime(df.index if 'date' not in df.columns else df['date'])
                    df_filtered = df[df['date'] <= current_date]
                    
                    if len(df_filtered) < 60:
                        continue
                    
                    b01 = self.calculate_b01_score(df_filtered)
                    
                    # B01 조건: B등급 이상
                    if b01['score'] < 65:
                        continue
                    
                    # AI 예측
                    pred = self.predictor.predict(symbol, date=current_date.strftime('%Y-%m-%d'))
                    
                    # AI 조건: 상승 예측 + 확신도 >= 임계값
                    if pred['direction'] != '상승' or pred['confidence'] < self.confidence_threshold:
                        continue
                    
                    selected.append({
                        'symbol': symbol,
                        'price': b01['current_price'],
                        'score': b01['score'],
                        'grade': b01['grade'],
                        'ai_confidence': pred['confidence']
                    })
                    
                except Exception as e:
                    continue
            
            if len(selected) == 0:
                print(f"   ⏭️ 선정 종목 없음")
                equity_curve.append({'date': current_date.strftime('%Y-%m-%d'), 'equity': capital})
                current_date += timedelta(days=30)
                continue
            
            # 점수순 정렬 후 상위 5개만 선택
            selected.sort(key=lambda x: x['score'] + x['ai_confidence']/10, reverse=True)
            selected = selected[:5]
            
            print(f"   ✅ 선정: {len(selected)}개 종목")
            for s in selected:
                print(f"      {s['symbol']}: {s['grade']}등급/{s['score']}점, AI확신도 {s['ai_confidence']:.1f}%")
            
            # 포지션 분할 (동일 비중)
            position_size = capital / len(selected)
            
            # 1개월 보유 후 결과 계산
            exit_date = current_date + timedelta(days=30)
            
            for pos in selected:
                try:
                    # 백테스트 시점에 맞는 날짜 범위로 데이터 요청
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
                        exit_reason=exit_reason
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
            'exit_reason': t.exit_reason
        } for t in trades])
        
        total_return = (equity_curve[-1]['equity'] / self.initial_capital - 1) * 100
        win_trades = len(df_trades[df_trades['return_pct'] > 0])
        win_rate = win_trades / len(trades) * 100
        avg_return = df_trades['return_pct'].mean()
        
        # 최대 낙폭
        equity_values = [e['equity'] for e in equity_curve]
        peak = self.initial_capital
        max_dd = 0
        for eq in equity_values:
            if eq > peak:
                peak = eq
            dd = (peak - eq) / peak * 100
            if dd > max_dd:
                max_dd = dd
        
        print(f"\n{'='*60}")
        print(f"📈 백테스트 결과")
        print(f"{'='*60}")
        print(f"총 거래 횟수: {len(trades)}회")
        print(f"승률: {win_rate:.1f}% ({win_trades}/{len(trades)})")
        print(f"평균 수익률: {avg_return:.2f}%")
        print(f"총 수익률: {total_return:.2f}%")
        print(f"최대 낙폭: {max_dd:.2f}%")
        print(f"최종 자본: ₩{equity_curve[-1]['equity']:,.0f}")
        
        print(f"\n📊 청산 사유:")
        for reason, count in df_trades['exit_reason'].value_counts().items():
            avg_ret = df_trades[df_trades['exit_reason'] == reason]['return_pct'].mean()
            print(f"   {reason}: {count}회 (평균 {avg_ret:.2f}%)")
        
        return {
            'trades': trades,
            'equity_curve': equity_curve,
            'total_return': total_return,
            'win_rate': win_rate,
            'max_drawdown': max_dd,
            'num_trades': len(trades)
        }
    
    def save_results(self, results: Dict, filename: str = None):
        """결과 저장"""
        if filename is None:
            filename = f"b01_ai_backtest_{datetime.now().strftime('%Y%m%d_%H%M')}"
        
        # JSON
        data = {
            'summary': {
                'total_return': results['total_return'],
                'win_rate': results['win_rate'],
                'max_drawdown': results['max_drawdown'],
                'num_trades': results['num_trades'],
                'initial_capital': self.initial_capital,
                'final_capital': results['equity_curve'][-1]['equity'] if results['equity_curve'] else self.initial_capital
            },
            'trades': [{
                'symbol': t.symbol,
                'entry_date': t.entry_date,
                'entry_price': t.entry_price,
                'exit_date': t.exit_date,
                'exit_price': t.exit_price,
                'return_pct': t.return_pct,
                'holding_days': t.holding_days,
                'exit_reason': t.exit_reason
            } for t in results['trades']],
            'equity_curve': results['equity_curve']
        }
        
        import os
        os.makedirs('./reports/b01_value', exist_ok=True)
        
        with open(f'./reports/b01_value/{filename}.json', 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        
        print(f"\n💾 결과 저장: ./reports/b01_value/{filename}.json")


def main():
    backtest = B01AIBacktest(initial_capital=100_000_000, confidence_threshold=60)
    results = backtest.run_backtest(start_date='2025-01-01', end_date='2026-03-18')
    
    if results:
        backtest.save_results(results)


if __name__ == '__main__':
    main()
