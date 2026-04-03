#!/usr/bin/env python3
"""
Bithumb Paper Trading System - 빗썸 페이퍼트레이딩 시스템
실시간 시장 데이터 기반 가상 매매
"""

import sys
sys.path.insert(0, '.')
import json
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional
from dataclasses import dataclass, asdict
import pandas as pd
import numpy as np

from bithumb_trading_simulator import BithumbPublicAPI


@dataclass
class Position:
    """포지션 정보"""
    coin: str
    entry_price: float
    volume: float
    entry_time: str
    entry_reason: str
    stop_loss: float
    take_profit: float
    
    @property
    def value(self, current_price: float = None) -> float:
        if current_price:
            return self.volume * current_price
        return self.volume * self.entry_price
    
    @property
    def pnl_pct(self, current_price: float) -> float:
        return (current_price - self.entry_price) / self.entry_price * 100


@dataclass
class Trade:
    """거래 내역"""
    id: str
    type: str  # BUY or SELL
    coin: str
    price: float
    volume: float
    amount: float
    fee: float
    timestamp: str
    reason: str
    pnl: Optional[float] = None
    pnl_pct: Optional[float] = None


class PaperTradingSystem:
    """페이퍼트레이딩 시스템"""
    
    def __init__(self, 
                 initial_balance: float = 10_000_000,
                 fee_rate: float = 0.0005,
                 data_dir: str = "paper_trading_data"):
        """
        Parameters:
        -----------
        initial_balance : float
            초기 자본 (KRW)
        fee_rate : float
            거래 수수료
        data_dir : str
            데이터 저장 경로
        """
        self.api = BithumbPublicAPI()
        self.initial_balance = initial_balance
        self.balance_krw = initial_balance
        self.fee_rate = fee_rate
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(exist_ok=True)
        
        self.positions: Dict[str, Position] = {}
        self.trades: List[Trade] = []
        self.daily_snapshots = []
        
        # 전략 파라미터
        self.risk_per_trade = 0.02  # 2% 리스크
        self.stop_loss_pct = 0.03   # 3% 손절
        self.take_profit_pct = 0.09 # 9% 익절
        
        # 데이터 로드
        self._load_data()
    
    def _load_data(self):
        """저장된 데이터 로드"""
        positions_file = self.data_dir / "positions.json"
        trades_file = self.data_dir / "trades.json"
        balance_file = self.data_dir / "balance.json"
        
        if positions_file.exists():
            with open(positions_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                self.positions = {k: Position(**v) for k, v in data.items()}
        
        if trades_file.exists():
            with open(trades_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                self.trades = [Trade(**t) for t in data]
        
        if balance_file.exists():
            with open(balance_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                self.balance_krw = data.get('balance', self.initial_balance)
    
    def _save_data(self):
        """데이터 저장"""
        positions_file = self.data_dir / "positions.json"
        trades_file = self.data_dir / "trades.json"
        balance_file = self.data_dir / "balance.json"
        
        with open(positions_file, 'w', encoding='utf-8') as f:
            json.dump({k: asdict(v) for k, v in self.positions.items()}, f, ensure_ascii=False, indent=2)
        
        with open(trades_file, 'w', encoding='utf-8') as f:
            json.dump([asdict(t) for t in self.trades], f, ensure_ascii=False, indent=2, default=str)
        
        with open(balance_file, 'w', encoding='utf-8') as f:
            json.dump({'balance': self.balance_krw}, f)
    
    def get_portfolio_value(self) -> float:
        """현재 포트폴리오 가치"""
        position_value = 0
        for coin, pos in self.positions.items():
            ticker = self.api.get_ticker(coin)
            if ticker and 'data' in ticker:
                current_price = float(ticker['data'].get('closing_price', pos.entry_price))
                position_value += pos.volume * current_price
        return self.balance_krw + position_value
    
    def calculate_position_size(self, price: float) -> float:
        """포지션 크기 계산 (2% 리스크)"""
        risk_amount = self.balance_krw * self.risk_per_trade
        position_value = risk_amount / self.stop_loss_pct
        volume = position_value / price
        return volume
    
    def buy(self, coin: str, price: float, reason: str = "") -> bool:
        """매수 주문"""
        volume = self.calculate_position_size(price)
        amount = price * volume
        fee = amount * self.fee_rate
        total_cost = amount + fee
        
        if total_cost > self.balance_krw:
            print(f"❌ 잔고 부족: 필요 {total_cost:,.0f}, 보유 {self.balance_krw:,.0f}")
            return False
        
        self.balance_krw -= total_cost
        
        # 스탑로스/익절가 설정
        stop_loss = price * (1 - self.stop_loss_pct)
        take_profit = price * (1 + self.take_profit_pct)
        
        if coin in self.positions:
            # 추가 매수
            old_pos = self.positions[coin]
            total_volume = old_pos.volume + volume
            avg_price = (old_pos.entry_price * old_pos.volume + price * volume) / total_volume
            self.positions[coin] = Position(
                coin=coin,
                entry_price=avg_price,
                volume=total_volume,
                entry_time=datetime.now().isoformat(),
                entry_reason=f"{old_pos.entry_reason} + {reason}",
                stop_loss=min(old_pos.stop_loss, stop_loss),
                take_profit=max(old_pos.take_profit, take_profit)
            )
        else:
            self.positions[coin] = Position(
                coin=coin,
                entry_price=price,
                volume=volume,
                entry_time=datetime.now().isoformat(),
                entry_reason=reason,
                stop_loss=stop_loss,
                take_profit=take_profit
            )
        
        trade = Trade(
            id=f"BUY_{datetime.now().strftime('%Y%m%d%H%M%S')}_{coin}",
            type="BUY",
            coin=coin,
            price=price,
            volume=volume,
            amount=amount,
            fee=fee,
            timestamp=datetime.now().isoformat(),
            reason=reason
        )
        self.trades.append(trade)
        self._save_data()
        
        print(f"🔵 [{coin}] 매수 완료")
        print(f"   가격: {price:,.0f} KRW")
        print(f"   수량: {volume:.6f}")
        print(f"   금액: {amount:,.0f} KRW")
        print(f"   수수료: {fee:,.0f} KRW")
        print(f"   손절가: {stop_loss:,.0f} KRW")
        print(f"   익절가: {take_profit:,.0f} KRW")
        
        return True
    
    def sell(self, coin: str, price: float, reason: str = "") -> bool:
        """매도 주문"""
        if coin not in self.positions:
            print(f"❌ {coin} 포지션 없음")
            return False
        
        pos = self.positions[coin]
        amount = price * pos.volume
        fee = amount * self.fee_rate
        net_proceeds = amount - fee
        
        # 손익 계산
        cost_basis = pos.entry_price * pos.volume
        buy_fee = cost_basis * self.fee_rate
        pnl = net_proceeds - cost_basis - buy_fee
        pnl_pct = (price - pos.entry_price) / pos.entry_price * 100
        
        self.balance_krw += net_proceeds
        del self.positions[coin]
        
        trade = Trade(
            id=f"SELL_{datetime.now().strftime('%Y%m%d%H%M%S')}_{coin}",
            type="SELL",
            coin=coin,
            price=price,
            volume=pos.volume,
            amount=amount,
            fee=fee,
            timestamp=datetime.now().isoformat(),
            reason=reason,
            pnl=pnl,
            pnl_pct=pnl_pct
        )
        self.trades.append(trade)
        self._save_data()
        
        emoji = "🟢" if pnl > 0 else "🔴"
        print(f"{emoji} [{coin}] 매도 완료")
        print(f"   가격: {price:,.0f} KRW")
        print(f"   수량: {pos.volume:.6f}")
        print(f"   실현손익: {pnl:+,.0f} KRW ({pnl_pct:+.2f}%)")
        
        return True
    
    def check_signals(self, coin: str, strategy: str = "mean_reversion") -> Dict:
        """매매 신호 확인"""
        # OHLCV 데이터 조회
        df = self.api.get_ohlcv(coin, chart_intervals="24h", count=50)
        if df.empty or len(df) < 30:
            return {'signal': 'HOLD', 'reason': '데이터 부족'}
        
        # 지표 계산
        df['sma20'] = df['close'].rolling(20).mean()
        df['std20'] = df['close'].rolling(20).std()
        df['upper'] = df['sma20'] + df['std20'] * 2
        df['lower'] = df['sma20'] - df['std20'] * 2
        
        delta = df['close'].diff()
        gain = delta.where(delta > 0, 0).rolling(14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
        rs = gain / loss
        df['rsi'] = 100 - (100 / (1 + rs))
        
        latest = df.iloc[-1]
        current_price = latest['close']
        
        has_position = coin in self.positions
        
        # 포지션 있음 - 손절/익절 체크
        if has_position:
            pos = self.positions[coin]
            pnl_pct = (current_price - pos.entry_price) / pos.entry_price * 100
            
            if current_price <= pos.stop_loss:
                return {'signal': 'SELL', 'reason': f'STOP_LOSS ({pnl_pct:.1f}%)'}
            
            if current_price >= pos.take_profit:
                return {'signal': 'SELL', 'reason': f'TAKE_PROFIT ({pnl_pct:.1f}%)'}
            
            # 평균회귀 매도
            if strategy == "mean_reversion" and latest['rsi'] > 60:
                return {'signal': 'SELL', 'reason': 'RSI 과매수'}
            
            return {'signal': 'HOLD', 'reason': '포지션 유지'}
        
        # 포지션 없음 - 매수 신호
        if strategy == "mean_reversion":
            # RSI 과매도 + 가격이 볼린저 하단 근처
            if latest['rsi'] < 35 and current_price < latest['lower'] * 1.02:
                return {
                    'signal': 'BUY',
                    'reason': f'평균회귀 매수 (RSI: {latest["rsi"]:.1f}, Price: {current_price:,.0f})'
                }
        
        elif strategy == "rsi_bollinger":
            if latest['rsi'] < 35 and current_price < latest['lower'] * 1.02:
                return {
                    'signal': 'BUY',
                    'reason': f'RSI 과매도 (RSI: {latest["rsi"]:.1f})'
                }
        
        return {'signal': 'HOLD', 'reason': '신호 없음'}
    
    def run_scan(self, coins: List[str], strategy: str = "mean_reversion"):
        """종목 스캔 및 신호 확인"""
        print("="*70)
        print(f"🔍 페이퍼트레이딩 스캔 | {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("="*70)
        print(f"전략: {strategy}")
        print(f"대상: {', '.join(coins)}")
        print(f"잔고: {self.balance_krw:,.0f} KRW")
        print(f"포지션: {len(self.positions)}개")
        print("="*70)
        
        signals = []
        
        for coin in coins:
            try:
                ticker = self.api.get_ticker(coin)
                if not ticker or 'data' not in ticker:
                    continue
                
                current_price = float(ticker['data'].get('closing_price', 0))
                if current_price == 0:
                    continue
                
                # 신호 확인
                signal = self.check_signals(coin, strategy)
                signal['coin'] = coin
                signal['price'] = current_price
                signals.append(signal)
                
                status = "📊"
                if signal['signal'] == 'BUY':
                    status = "🔵 매수"
                elif signal['signal'] == 'SELL':
                    status = "🟢 매도" if coin in self.positions and self.positions[coin].pnl_pct(current_price) > 0 else "🔴 매도"
                elif coin in self.positions:
                    pos = self.positions[coin]
                    pnl = (current_price - pos.entry_price) / pos.entry_price * 100
                    status = f"💰 {pnl:+.1f}%"
                
                print(f"{status:12} {coin:8} {current_price:12,.0f} | {signal['reason']}")
                
                # 매매 실행
                if signal['signal'] == 'BUY':
                    self.buy(coin, current_price, signal['reason'])
                elif signal['signal'] == 'SELL':
                    self.sell(coin, current_price, signal['reason'])
                
                time.sleep(0.5)  # API rate limit
                
            except Exception as e:
                print(f"⚠️ {coin} 오류: {e}")
        
        # 현재 상태 출력
        self._print_status()
        return signals
    
    def _print_status(self):
        """현재 상태 출력"""
        print("\n" + "="*70)
        print("📊 현재 포트폴리오 상태")
        print("="*70)
        
        portfolio_value = self.balance_krw
        
        if self.positions:
            print(f"\n💼 보유 포지션:")
            for coin, pos in self.positions.items():
                ticker = self.api.get_ticker(coin)
                if ticker and 'data' in ticker:
                    current_price = float(ticker['data'].get('closing_price', pos.entry_price))
                    pnl_pct = (current_price - pos.entry_price) / pos.entry_price * 100
                    value = pos.volume * current_price
                    portfolio_value += value
                    print(f"   {coin}: {pos.volume:.6f} @ {pos.entry_price:,.0f} → {current_price:,.0f} ({pnl_pct:+.1f}%) | {value:,.0f} KRW")
        else:
            print(f"\n💼 보유 포지션: 없음")
        
        print(f"\n💰 현금: {self.balance_krw:,.0f} KRW")
        print(f"📈 총 평가: {portfolio_value:,.0f} KRW")
        
        total_return = (portfolio_value - self.initial_balance) / self.initial_balance * 100
        print(f"📊 총 수익률: {total_return:+.2f}%")
        
        # 거래 통계
        sell_trades = [t for t in self.trades if t.type == 'SELL']
        if sell_trades:
            wins = len([t for t in sell_trades if t.pnl and t.pnl > 0])
            print(f"🔄 거래: {len(sell_trades)}회 (승률: {wins}/{len(sell_trades)} = {wins/len(sell_trades)*100:.1f}%)")
    
    def run_monitoring(self, coins: List[str], interval_minutes: int = 60, strategy: str = "mean_reversion"):
        """지속 모니터링"""
        print("="*70)
        print("🚀 페이퍼트레이딩 모니터링 시작")
        print("="*70)
        print(f"체크 간격: {interval_minutes}분")
        print(f"전략: {strategy}")
        print("Ctrl+C로 종료")
        print("="*70)
        
        try:
            while True:
                self.run_scan(coins, strategy)
                print(f"\n⏱️ 다음 체크: {interval_minutes}분 후")
                time.sleep(interval_minutes * 60)
        except KeyboardInterrupt:
            print("\n\n✅ 모니터링 종료")
            self._print_status()


def main():
    import argparse
    
    parser = argparse.ArgumentParser(description='Bithumb Paper Trading')
    parser.add_argument('--mode', choices=['scan', 'monitor', 'status'], default='scan',
                       help='실행 모드')
    parser.add_argument('--coins', default='BTC,ETH,XRP,SOL',
                       help='대상 코인 (쉼표 구분)')
    parser.add_argument('--strategy', default='mean_reversion',
                       choices=['mean_reversion', 'rsi_bollinger'],
                       help='전략')
    parser.add_argument('--interval', type=int, default=60,
                       help='모니터링 간격 (분)')
    
    args = parser.parse_args()
    
    coins = [c.strip().upper() for c in args.coins.split(',')]
    
    # 시스템 초기화
    paper = PaperTradingSystem()
    
    if args.mode == 'scan':
        # 한번만 스캔
        paper.run_scan(coins, args.strategy)
    
    elif args.mode == 'monitor':
        # 지속 모니터링
        paper.run_monitoring(coins, args.interval, args.strategy)
    
    elif args.mode == 'status':
        # 현재 상태만 출력
        paper._print_status()


if __name__ == '__main__':
    main()
