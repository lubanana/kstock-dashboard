#!/usr/bin/env python3
"""
SMC FVG Backtest with Yahoo Finance Data
야후 파이낸스 데이터를 활용한 SMC FVG 백테스트
"""

import pandas as pd
import numpy as np
import yfinance as yf
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
import json
from dataclasses import dataclass, asdict
import warnings
warnings.filterwarnings('ignore')


@dataclass
class Trade:
    """개별 거래 기록"""
    entry_time: datetime
    exit_time: Optional[datetime] = None
    entry_price: float = 0.0
    exit_price: Optional[float] = None
    sl_price: float = 0.0
    tp_price: float = 0.0
    position: str = 'LONG'
    status: str = 'OPEN'
    pnl: float = 0.0
    pnl_pct: float = 0.0
    rr_ratio: float = 0.0
    fvg_size: float = 0.0
    size: float = 0.0


class SMCFVGYahooBacktest:
    """
    SMC FVG 백테스트 엔진 (야후 파이낸스 데이터)
    """
    
    def __init__(self,
                 initial_capital: float = 10000.0,
                 risk_per_trade: float = 0.02,
                 min_rr_ratio: float = 2.5,
                 fvg_min_size: float = 0.001,
                 msb_strength: float = 0.005,
                 fee_rate: float = 0.0004):
        
        self.initial_capital = initial_capital
        self.risk_per_trade = risk_per_trade
        self.min_rr_ratio = min_rr_ratio
        self.fvg_min_size = fvg_min_size
        self.msb_strength = msb_strength
        self.fee_rate = fee_rate
        
        self.capital = initial_capital
        self.trades: List[Trade] = []
        self.equity_curve = []
    
    def fetch_data(self, symbol: str = 'BTC-USD', period: str = '1y', 
                   interval: str = '1h') -> pd.DataFrame:
        """
        야후 파이낸스에서 데이터 가져오기
        """
        print(f"\n📥 데이터 다운로드: {symbol} ({period}, {interval})")
        
        try:
            ticker = yf.Ticker(symbol)
            df = ticker.history(period=period, interval=interval)
            
            if df.empty:
                print("❌ 데이터를 가져올 수 없습니다")
                return pd.DataFrame()
            
            # 컬럼명 소문자로
            df.columns = [c.lower().replace(' ', '_') for c in df.columns]
            
            # 인덱스 정리
            df.index = pd.to_datetime(df.index)
            
            # 필요한 컬럼만
            df = df[['open', 'high', 'low', 'close', 'volume']]
            
            print(f"   ✓ 기간: {df.index[0]} ~ {df.index[-1]}")
            print(f"   ✓ 총 {len(df)}개 봉")
            print(f"   ✓ 가격 범위: ${df['low'].min():,.2f} ~ ${df['high'].max():,.2f}")
            
            return df
            
        except Exception as e:
            print(f"❌ 데이터 다운로드 오류: {e}")
            return pd.DataFrame()
    
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
                   end_idx: int, lookback: int = 30) -> List[Dict]:
        """FVG 감지"""
        fvgs = []
        start_idx = max(0, end_idx - lookback)
        
        for i in range(start_idx, min(end_idx - 2, len(highs) - 2)):
            c1_high, c1_low = highs[i], lows[i]
            c2_high, c2_low = highs[i+1], lows[i+1]
            c3_high, c3_low = highs[i+2], lows[i+2]
            
            # 불리쉬 FVG: 캔들1 고가 < 캔들3 저가
            if c1_high < c3_low:
                size = (c3_low - c1_high) / c1_high
                if size >= self.fvg_min_size:
                    fvgs.append({
                        'type': 'BULLISH',
                        'idx': i+1,
                        'top': float(c3_low),
                        'bottom': float(c1_high),
                        'size': float(size * 100),
                        'ob_low': float(c2_low),
                        'timestamp': i+1
                    })
            
            # 베리쉬 FVG
            elif c1_low > c3_high:
                size = (c1_low - c3_high) / c3_high
                if size >= self.fvg_min_size:
                    fvgs.append({
                        'type': 'BEARISH',
                        'idx': i+1,
                        'top': float(c1_low),
                        'bottom': float(c3_high),
                        'size': float(size * 100),
                        'ob_high': float(c2_high),
                        'timestamp': i+1
                    })
        
        return fvgs
    
    def check_long_signal(self, df: pd.DataFrame, idx: int,
                          swing_highs: List[int], swing_lows: List[int]) -> Optional[Dict]:
        """롱 진입 신호 확인"""
        highs = df['high'].values
        lows = df['low'].values
        closes = df['close'].values
        
        # 과거 스윙 하이
        past_swings = [s for s in swing_highs if s < idx - 3]
        if len(past_swings) < 2:
            return None
        
        # MSB 확인
        prev_swing_high = highs[past_swings[-2]]
        current_close = closes[idx]
        
        if current_close < prev_swing_high * (1 + self.msb_strength):
            return None
        
        # FVG 확인
        fvgs = self.detect_fvg(highs, lows, idx)
        bullish_fvgs = [f for f in fvgs if f['type'] == 'BULLISH']
        
        if not bullish_fvgs:
            return None
        
        # 가장 최근 FVG
        fvg = max(bullish_fvgs, key=lambda x: x['idx'])
        
        # Retest 확인
        current_low = lows[idx]
        current_high = highs[idx]
        
        if not (current_low <= fvg['top'] and current_high >= fvg['bottom']):
            return None
        
        # 진입 레벨 계산
        entry_price = current_close
        sl_price = fvg['ob_low'] * 0.998
        
        # TP 계산
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
            'entry_price': float(entry_price),
            'sl_price': float(sl_price),
            'tp_price': float(tp_price),
            'rr_ratio': float(rr),
            'fvg': fvg,
            'risk': float(risk),
            'reward': float(reward)
        }
    
    def run(self, symbol: str = 'BTC-USD', period: str = '1y', 
            interval: str = '1h') -> Dict:
        """백테스트 실행"""
        print("\n" + "="*70)
        print("🚀 SMC FVG 백테스트 (Yahoo Finance)")
        print("="*70)
        
        # 데이터 로드
        df = self.fetch_data(symbol, period, interval)
        if df.empty:
            return {'error': 'No data'}
        
        print(f"\n💰 초기 자본: ${self.initial_capital:,.2f}")
        print(f"⚙️  파라미터: R:R 1:{self.min_rr_ratio}, FVG min {self.fvg_min_size*100:.2f}%")
        
        highs = df['high'].values
        lows = df['low'].values
        closes = df['close'].values
        
        # 스윙 포인트 계산
        swing_highs, swing_lows = self.identify_swing_points(highs, lows)
        print(f"\n📊 스윙 포인트: High {len(swing_highs)}개, Low {len(swing_lows)}개")
        
        current_trade = None
        cooldown = 0  # 거래 간 쿨다운
        
        for i in range(50, len(df)):
            current_time = df.index[i]
            current_price = closes[i]
            
            # 자본 기록
            portfolio = self.capital
            if current_trade:
                unrealized = (current_price - current_trade.entry_price) / current_trade.entry_price
                portfolio += unrealized * current_trade.size * current_trade.entry_price
            
            self.equity_curve.append({
                'time': current_time.isoformat(),
                'value': float(portfolio)
            })
            
            # 현재 거래 체크
            if current_trade:
                # SL
                if current_price <= current_trade.sl_price:
                    self._close_trade(current_trade, current_time, current_price, 'CLOSED_SL')
                    current_trade = None
                    cooldown = 10
                    continue
                
                # TP
                if current_price >= current_trade.tp_price:
                    self._close_trade(current_trade, current_time, current_price, 'CLOSED_TP')
                    current_trade = None
                    cooldown = 10
                    continue
            
            # 쿨다운 감소
            if cooldown > 0:
                cooldown -= 1
                continue
            
            # 새 신호 체크 (10봉 간격)
            if not current_trade and i % 10 == 0:
                signal = self.check_long_signal(df, i, swing_highs, swing_lows)
                if signal:
                    size = self._calculate_position_size(signal['risk'])
                    current_trade = Trade(
                        entry_time=current_time,
                        entry_price=signal['entry_price'],
                        sl_price=signal['sl_price'],
                        tp_price=signal['tp_price'],
                        rr_ratio=signal['rr_ratio'],
                        fvg_size=signal['fvg']['size'],
                        size=size
                    )
                    self.trades.append(current_trade)
                    print(f"   📈 진입: ${signal['entry_price']:,.2f} (RR 1:{signal['rr_ratio']:.2f})")
        
        return self._calculate_results()
    
    def _calculate_position_size(self, risk_amount: float) -> float:
        """포지션 크기 계산"""
        if risk_amount <= 0:
            return 0
        risk_capital = self.capital * self.risk_per_trade
        return risk_capital / risk_amount
    
    def _close_trade(self, trade: Trade, exit_time: datetime,
                    exit_price: float, status: str):
        """거래 종료"""
        trade.exit_time = exit_time
        trade.exit_price = exit_price
        trade.status = status
        
        pnl_pct = (exit_price - trade.entry_price) / trade.entry_price * 100
        trade.pnl_pct = pnl_pct
        trade.pnl = pnl_pct / 100 * trade.size * trade.entry_price
        
        fee = trade.size * trade.entry_price * self.fee_rate * 2
        trade.pnl -= fee
        
        self.capital += trade.pnl
        
        emoji = "✅" if trade.pnl > 0 else "❌"
        print(f"   {emoji} 청산: ${exit_price:,.2f} | PnL: ${trade.pnl:,.2f} ({pnl_pct:.2f}%)")
    
    def _calculate_results(self) -> Dict:
        """결과 계산"""
        closed = [t for t in self.trades if t.status != 'OPEN']
        
        if not closed:
            return {'error': 'No completed trades'}
        
        wins = [t for t in closed if t.pnl > 0]
        losses = [t for t in closed if t.pnl <= 0]
        
        total_return = (self.capital - self.initial_capital) / self.initial_capital * 100
        win_rate = len(wins) / len(closed) * 100
        
        avg_win = np.mean([t.pnl_pct for t in wins]) if wins else 0
        avg_loss = np.mean([t.pnl_pct for t in losses]) if losses else 0
        
        total_profit = sum(t.pnl for t in wins)
        total_loss = abs(sum(t.pnl for t in losses))
        profit_factor = total_profit / total_loss if total_loss > 0 else float('inf')
        
        # 최대 낙폭
        values = [e['value'] for e in self.equity_curve]
        peak = self.initial_capital
        max_dd = 0
        for v in values:
            if v > peak:
                peak = v
            dd = (peak - v) / peak * 100
            max_dd = max(max_dd, dd)
        
        results = {
            'symbol': 'BTC-USD',
            'initial_capital': self.initial_capital,
            'final_capital': self.capital,
            'total_return': total_return,
            'total_trades': len(closed),
            'winning_trades': len(wins),
            'losing_trades': len(losses),
            'win_rate': win_rate,
            'avg_win_pct': avg_win,
            'avg_loss_pct': avg_loss,
            'profit_factor': profit_factor,
            'max_drawdown': max_dd,
            'equity_curve': self.equity_curve,
            'trades': [asdict(t) for t in closed]
        }
        
        self._print_results(results)
        return results
    
    def _print_results(self, results: Dict):
        """결과 출력"""
        print("\n" + "="*70)
        print("📊 백테스트 결과")
        print("="*70)
        print(f"총 수익률: {results['total_return']:.2f}%")
        print(f"최종 자본: ${results['final_capital']:,.2f}")
        print(f"총 거래: {results['total_trades']}회")
        print(f"승률: {results['win_rate']:.1f}%")
        print(f"평균 수익: {results['avg_win_pct']:.2f}%")
        print(f"평균 손실: {results['avg_loss_pct']:.2f}%")
        print(f"Profit Factor: {results['profit_factor']:.2f}")
        print(f"최대 낙폭: {results['max_drawdown']:.2f}%")
        print("="*70)


def main():
    """메인 실행"""
    # BTC 1년치 1시간봉
    backtest = SMCFVGYahooBacktest(
        initial_capital=10000,
        risk_per_trade=0.02,
        min_rr_ratio=2.5
    )
    
    results = backtest.run(
        symbol='BTC-USD',
        period='1y',      # 1년
        interval='1h'     # 1시간봉
    )
    
    # 결과 저장
    with open('./smc_fvg_yahoo_results.json', 'w') as f:
        json.dump(results, f, indent=2, default=str)
    print("\n💾 결과 저장: ./smc_fvg_yahoo_results.json")


if __name__ == '__main__':
    main()
