#!/usr/bin/env python3
"""
SMC FVG Backtest Engine
SMC FVG 전략 백테스트 엔진
"""

import pandas as pd
import numpy as np
from datetime import datetime
from typing import Dict, List, Optional, Tuple
import json
from dataclasses import dataclass, asdict


@dataclass
class Trade:
    """개별 거래 기록"""
    entry_time: datetime
    exit_time: Optional[datetime]
    entry_price: float
    exit_price: Optional[float]
    sl_price: float
    tp_price: float
    position: str  # 'LONG' or 'SHORT'
    status: str    # 'OPEN', 'CLOSED_SL', 'CLOSED_TP'
    pnl: float
    pnl_pct: float
    rr_ratio: float
    fvg_size: float
    size: float = 0.0


class SMCFVGBacktest:
    """
    SMC FVG 백테스트 엔진
    """
    
    def __init__(self,
                 initial_capital: float = 10000.0,
                 risk_per_trade: float = 0.02,  # 2% 리스크
                 min_rr_ratio: float = 2.5,
                 fvg_min_size: float = 0.001,
                 msb_strength: float = 0.005,
                 fee_rate: float = 0.0004):    # 0.04% 수수료
        
        self.initial_capital = initial_capital
        self.risk_per_trade = risk_per_trade
        self.min_rr_ratio = min_rr_ratio
        self.fvg_min_size = fvg_min_size
        self.msb_strength = msb_strength
        self.fee_rate = fee_rate
        
        self.capital = initial_capital
        self.trades: List[Trade] = []
        self.equity_curve = []
        
    def identify_swing_points(self, highs: np.ndarray, lows: np.ndarray, 
                              window: int = 5) -> Tuple[List[int], List[int]]:
        """스윙 포인트 식별"""
        swing_highs = []
        swing_lows = []
        
        for i in range(window, len(highs) - window):
            if highs[i] == max(highs[i-window:i+window+1]):
                swing_highs.append(i)
            if lows[i] == min(lows[i-window:i+window+1]):
                swing_lows.append(i)
        
        return swing_highs, swing_lows
    
    def detect_fvg(self, highs: np.ndarray, lows: np.ndarray, 
                   start_idx: int, lookback: int = 20) -> List[Dict]:
        """FVG 감지"""
        fvgs = []
        end_idx = min(start_idx, len(highs) - 3)
        start_search = max(0, end_idx - lookback)
        
        for i in range(start_search, end_idx):
            c1_high, c1_low = highs[i], lows[i]
            c2_high, c2_low = highs[i+1], lows[i+1]
            c3_high, c3_low = highs[i+2], lows[i+2]
            
            # 불리쉬 FVG
            if c1_high < c3_low:
                size = (c3_low - c1_high) / c1_high
                if size >= self.fvg_min_size:
                    fvgs.append({
                        'type': 'BULLISH',
                        'idx': i+1,
                        'top': c3_low,
                        'bottom': c1_high,
                        'size': size,
                        'ob_low': c2_low
                    })
        
        return fvgs
    
    def check_long_signal(self, df: pd.DataFrame, idx: int,
                          swing_highs: List[int]) -> Optional[Dict]:
        """
        롱 진입 신호 확인
        """
        highs = df['high'].values
        lows = df['low'].values
        closes = df['close'].values
        
        # 과거 스윙 하이 필터
        past_swings = [s for s in swing_highs if s < idx - 3]
        if len(past_swings) < 2:
            return None
        
        # MSB 확인: 현재가가 이전 스윙 하이 돌파
        prev_swing_high = highs[past_swings[-2]]
        if closes[idx] < prev_swing_high * (1 + self.msb_strength):
            return None
        
        # FVG 확인
        fvgs = self.detect_fvg(highs, lows, idx)
        bullish_fvgs = [f for f in fvgs if f['type'] == 'BULLISH']
        
        if not bullish_fvgs:
            return None
        
        # 가장 최근 FVG
        fvg = max(bullish_fvgs, key=lambda x: x['idx'])
        
        # Retest 확인: 현재가가 FVG 구간 내
        current_low = lows[idx]
        current_high = highs[idx]
        
        if not (current_low <= fvg['top'] and current_high >= fvg['bottom']):
            return None
        
        # 진입 레벨 계산
        entry_price = closes[idx]
        sl_price = fvg['ob_low'] * 0.998  # 오더블록 하단 아래
        
        # TP: 다음 스윙 하이 또는 1:2.5 R/R
        next_resistances = [highs[s] for s in past_swings if highs[s] > entry_price]
        if next_resistances:
            tp_price = min(next_resistances)
        else:
            tp_price = entry_price * 1.05
        
        # R/R 확인
        risk = entry_price - sl_price
        reward = tp_price - entry_price
        
        if risk <= 0:
            return None
        
        rr = reward / risk
        if rr < self.min_rr_ratio:
            tp_price = entry_price + (risk * self.min_rr_ratio)
            reward = tp_price - entry_price
            rr = self.min_rr_ratio
        
        return {
            'entry_price': entry_price,
            'sl_price': sl_price,
            'tp_price': tp_price,
            'rr_ratio': rr,
            'fvg': fvg,
            'risk': risk,
            'reward': reward
        }
    
    def run(self, df: pd.DataFrame) -> Dict:
        """
        백테스트 실행
        """
        print(f"\n🔙 SMC FVG 백테스트 시작")
        print(f"   초기 자본: ${self.initial_capital:,.2f}")
        print(f"   데이터 기간: {df.index[0]} ~ {df.index[-1]}")
        print(f"   총 봉 수: {len(df)}")
        
        highs = df['high'].values
        lows = df['low'].values
        closes = df['close'].values
        
        # 스윙 포인트 사전 계산
        swing_highs, swing_lows = self.identify_swing_points(highs, lows)
        print(f"   스윙 하이: {len(swing_highs)}개, 스윙 로우: {len(swing_lows)}개")
        
        current_trade = None
        
        for i in range(50, len(df)):
            current_time = df.index[i]
            current_price = closes[i]
            
            # 자본 기록
            portfolio_value = self.capital
            if current_trade:
                unrealized = (current_price - current_trade.entry_price) / current_trade.entry_price * current_trade.size
                portfolio_value += unrealized
            self.equity_curve.append({'time': current_time, 'value': portfolio_value})
            
            # 현재 거래 체크
            if current_trade:
                # SL 체크
                if current_price <= current_trade.sl_price:
                    self._close_trade(current_trade, current_time, current_trade.sl_price, 'CLOSED_SL')
                    current_trade = None
                    continue
                
                # TP 체크
                if current_price >= current_trade.tp_price:
                    self._close_trade(current_trade, current_time, current_trade.tp_price, 'CLOSED_TP')
                    current_trade = None
                    continue
            
            # 새 신호 체크 (20봉 간격)
            if not current_trade and i % 20 == 0:
                signal = self.check_long_signal(df, i, swing_highs)
                if signal:
                    position_size = self._calculate_position_size(signal['risk'])
                    current_trade = Trade(
                        entry_time=current_time,
                        exit_time=None,
                        entry_price=signal['entry_price'],
                        exit_price=None,
                        sl_price=signal['sl_price'],
                        tp_price=signal['tp_price'],
                        position='LONG',
                        status='OPEN',
                        pnl=0,
                        pnl_pct=0,
                        rr_ratio=signal['rr_ratio'],
                        fvg_size=signal['fvg']['size'],
                        size=position_size
                    )
                    self.trades.append(current_trade)
        
        # 결과 계산
        return self._calculate_results()
    
    def _calculate_position_size(self, risk_amount: float) -> float:
        """포지션 크기 계산"""
        risk_capital = self.capital * self.risk_per_trade
        return risk_capital / risk_amount if risk_amount > 0 else 0
    
    def _close_trade(self, trade: Trade, exit_time: datetime, 
                    exit_price: float, status: str):
        """거래 종료"""
        trade.exit_time = exit_time
        trade.exit_price = exit_price
        trade.status = status
        
        # PnL 계산
        pnl_pct = (exit_price - trade.entry_price) / trade.entry_price
        trade.pnl_pct = pnl_pct * 100
        trade.pnl = pnl_pct * trade.size * trade.entry_price
        
        # 수수료 차감
        fee = trade.size * trade.entry_price * self.fee_rate * 2  # 진입+청산
        trade.pnl -= fee
        
        # 자본 업데이트
        self.capital += trade.pnl
    
    def _calculate_results(self) -> Dict:
        """백테스트 결과 계산"""
        closed_trades = [t for t in self.trades if t.status != 'OPEN']
        
        if not closed_trades:
            return {'error': 'No completed trades'}
        
        wins = [t for t in closed_trades if t.pnl > 0]
        losses = [t for t in closed_trades if t.pnl <= 0]
        
        total_pnl = sum(t.pnl for t in closed_trades)
        win_rate = len(wins) / len(closed_trades) * 100 if closed_trades else 0
        
        avg_win = np.mean([t.pnl_pct for t in wins]) if wins else 0
        avg_loss = np.mean([t.pnl_pct for t in losses]) if losses else 0
        
        profit_factor = abs(sum(t.pnl for t in wins) / sum(t.pnl for t in losses)) if losses else float('inf')
        
        # 최대 낙폭
        equity_values = [e['value'] for e in self.equity_curve]
        peak = self.initial_capital
        max_dd = 0
        for val in equity_values:
            if val > peak:
                peak = val
            dd = (peak - val) / peak * 100
            if dd > max_dd:
                max_dd = dd
        
        results = {
            'initial_capital': self.initial_capital,
            'final_capital': self.capital,
            'total_return': (self.capital - self.initial_capital) / self.initial_capital * 100,
            'total_trades': len(closed_trades),
            'winning_trades': len(wins),
            'losing_trades': len(losses),
            'win_rate': win_rate,
            'avg_win_pct': avg_win,
            'avg_loss_pct': avg_loss,
            'profit_factor': profit_factor,
            'max_drawdown': max_dd,
            'trades': [asdict(t) for t in closed_trades]
        }
        
        self._print_results(results)
        return results
    
    def _print_results(self, results: Dict):
        """결과 출력"""
        print("\n" + "="*60)
        print("📊 백테스트 결과")
        print("="*60)
        print(f"총 수익률: {results['total_return']:.2f}%")
        print(f"총 거래: {results['total_trades']}회")
        print(f"승률: {results['win_rate']:.1f}%")
        print(f"평균 수익: {results['avg_win_pct']:.2f}%")
        print(f"평균 손실: {results['avg_loss_pct']:.2f}%")
        print(f"Profit Factor: {results['profit_factor']:.2f}")
        print(f"최대 낙폭: {results['max_drawdown']:.2f}%")
        print("="*60)


def generate_test_data():
    """테스트 데이터 생성"""
    np.random.seed(42)
    n = 500
    
    dates = pd.date_range(start='2025-01-01', periods=n, freq='1h')
    
    # 추세 + 횡보 패턴
    trend = np.linspace(40000, 50000, n) + np.sin(np.linspace(0, 10*np.pi, n)) * 3000
    noise = np.random.randn(n) * 200
    
    closes = trend + noise
    opens = closes + np.random.randn(n) * 100
    highs = np.maximum(opens, closes) + np.abs(np.random.randn(n)) * 150
    lows = np.minimum(opens, closes) - np.abs(np.random.randn(n)) * 150
    volumes = np.random.randint(1000, 10000, n)
    
    df = pd.DataFrame({
        'open': opens,
        'high': highs,
        'low': lows,
        'close': closes,
        'volume': volumes
    }, index=dates)
    
    return df


def main():
    """메인 실행"""
    print("🚀 SMC FVG 백테스트")
    
    # 테스트 데이터
    df = generate_test_data()
    
    # 백테스트 실행
    backtest = SMCFVGBacktest(
        initial_capital=10000,
        risk_per_trade=0.02,
        min_rr_ratio=2.5
    )
    
    results = backtest.run(df)
    
    # 결과 저장
    with open('./smc_fvg_backtest_results.json', 'w') as f:
        json.dump(results, f, indent=2, default=str)
    print("\n💾 결과 저장: ./smc_fvg_backtest_results.json")


if __name__ == '__main__':
    main()
