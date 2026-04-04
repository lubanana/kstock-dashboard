"""
Crypto Signal Aggregator - Paper Trading 연동 모듈

OKComputer Paper Trading 시스템과 연동하여 자동 주문 실행
"""

import sys
sys.path.insert(0, '/tmp/okcomputer_analysis/bithumb_trading')

from paper_trading import PaperAccount, PaperTradingEngine, Order
from typing import Optional
from datetime import datetime
import json
import os


class PaperTradingConnector:
    """페이퍼트레이딩 연동 클래스"""
    
    def __init__(self, initial_balance: float = 10_000_000):
        self.initial_balance = initial_balance
        self.account = PaperAccount(initial_balance=initial_balance)
        self.engine = PaperTradingEngine(self.account)
        self.data_dir = '/tmp/crypto_signal_data'
        self.state_file = f"{self.data_dir}/paper_account.json"
        
        # 기존 상태 로드
        self._load_state()
    
    def _load_state(self):
        """계좌 상태 로드"""
        if os.path.exists(self.state_file):
            try:
                with open(self.state_file, 'r') as f:
                    data = json.load(f)
                self.account.balance = data.get('balance', self.initial_balance)
                
                # 포지션 복원
                positions_data = data.get('positions', {})
                for coin, pos_data in positions_data.items():
                    from paper_trading import Position
                    position = Position(
                        coin=coin,
                        amount=pos_data.get('amount', 0),
                        avg_buy_price=pos_data.get('avg_buy_price', 0)
                    )
                    self.account.positions[coin] = position
                
                print(f"📂 페이퍼트레이딩 상태 로드됨: {self.account.balance:,.0f} KRW, 포지션 {len(self.account.positions)}개")
            except Exception as e:
                print(f"⚠️ 상태 로드 실패: {e}")
    
    def _save_state(self):
        """계좌 상태 저장"""
        try:
            os.makedirs(self.data_dir, exist_ok=True)
            
            # 포지션 직렬화
            positions_data = {}
            for coin, pos in self.account.positions.items():
                positions_data[coin] = {
                    'amount': pos.amount,
                    'avg_buy_price': pos.avg_buy_price
                }
            
            with open(self.state_file, 'w') as f:
                json.dump({
                    'balance': self.account.balance,
                    'initial_balance': self.initial_balance,
                    'positions': positions_data,
                    'last_update': datetime.now().isoformat(),
                    'trade_count': len(self.account.trade_history)
                }, f, indent=2)
        except Exception as e:
            print(f"⚠️ 상태 저장 실패: {e}")
    
    def execute_signal(self, signal, max_investment_pct: float = 10.0) -> Optional[Order]:
        """
        신호에 따라 페이퍼트레이딩 주문 실행
        
        Args:
            signal: TradingSignal 객체
            max_investment_pct: 최대 투자 비율 (%)
            
        Returns:
            Order 객체 또는 None
        """
        from crypto_signal_aggregator import SignalStrength
        
        # BUY 신호만 처리
        if signal.strength not in [SignalStrength.BUY, SignalStrength.STRONG_BUY]:
            print(f"⏭️ {signal.strength.value} 신호 - 주문 생략")
            return None
        
        # 이미 보유 중인지 확인
        coin = signal.symbol
        position = self.account.get_position(coin)
        if position and position.amount > 0:
            print(f"⏭️ {coin} 이미 보유 중 - 중복 주문 방지")
            return None
        
        # 투자 금액 계산
        max_investment = self.account.balance * (max_investment_pct / 100)
        
        # 신호 강도에 따른 투자 비율 조정
        if signal.strength == SignalStrength.STRONG_BUY:
            investment = min(max_investment * 1.0, self.account.balance * 0.10)  # 10%
        else:  # BUY
            investment = min(max_investment * 0.7, self.account.balance * 0.07)   # 7%
        
        if investment < 100_000:  # 최소 10만원
            print(f"⏭️ 투자 금액 부족: {investment:,.0f} KRW")
            return None
        
        # 매수 실행
        entry_price = signal.entry_price
        if not entry_price:
            print("⏭️ 진입가 없음")
            return None
        
        try:
            order = self.engine.buy(coin, price=entry_price, krw_amount=investment)
            
            print(f"\n{'='*60}")
            print(f"🟢 페이퍼트레이딩 주문 실행: {coin}")
            print(f"{'='*60}")
            print(f"   구분: 매수 ({signal.strength.value})")
            print(f"   가격: {order.price:,.0f} KRW")
            print(f"   수량: {order.amount:.8f}")
            print(f"   금액: {order.total_value:,.0f} KRW")
            print(f"   잔고: {self.account.balance:,.0f} KRW")
            print(f"{'='*60}\n")
            
            # 상태 저장
            self._save_state()
            
            return order
            
        except Exception as e:
            print(f"❌ 주문 실패: {e}")
            return None
    
    def check_take_profit_stop_loss(self, current_prices: dict):
        """
        익절/손절 체크
        
        Args:
            current_prices: {coin: price} 딕셔너리
        """
        for coin, current_price in current_prices.items():
            position = self.account.get_position(coin)
            if not position or position.amount <= 0:
                continue
            
            # 수익률 계산
            pnl_pct = (current_price - position.avg_buy_price) / position.avg_buy_price * 100
            
            # 익절 (+21%)
            if pnl_pct >= 21:
                print(f"\n🎯 익절 실행: {coin} (+{pnl_pct:.1f}%)")
                order = self.engine.sell_all(coin, price=current_price)
                print(f"   실현 손익: {order.realized_pnl:+,.0f} KRW")
                self._save_state()
            
            # 손절 (-7%)
            elif pnl_pct <= -7:
                print(f"\n🛑 손절 실행: {coin} ({pnl_pct:.1f}%)")
                order = self.engine.sell_all(coin, price=current_price)
                print(f"   실현 손익: {order.realized_pnl:+,.0f} KRW")
                self._save_state()
    
    def get_portfolio_summary(self, current_prices: dict) -> dict:
        """포트폴리오 요약"""
        portfolio_value = self.engine.get_portfolio_value(current_prices)
        pnl_info = self.account.get_pnl(current_prices)
        
        return {
            'initial_balance': self.initial_balance,
            'cash': self.account.balance,
            'position_value': pnl_info['position_value'],
            'total_value': portfolio_value,
            'pnl': pnl_info['pnl'],
            'pnl_pct': pnl_info['pnl_rate'],
            'trade_count': len(self.account.trade_history)
        }
    
    def print_portfolio(self, current_prices: dict):
        """포트폴리오 출력"""
        summary = self.get_portfolio_summary(current_prices)
        
        print(f"\n{'='*60}")
        print(f"💰 페이퍼트레이딩 계좌 현황")
        print(f"{'='*60}")
        print(f"   초기 자본: {summary['initial_balance']:>15,.0f} KRW")
        print(f"   현금 잔고: {summary['cash']:>15,.0f} KRW")
        print(f"   포지션 가치: {summary['position_value']:>15,.0f} KRW")
        print(f"   총 자산: {summary['total_value']:>15,.0f} KRW")
        
        emoji = "📈" if summary['pnl'] >= 0 else "📉"
        print(f"\n   {emoji} 총 손익: {summary['pnl']:+,.0f} KRW ({summary['pnl_pct']:+.2f}%)")
        print(f"   거래 횟수: {summary['trade_count']}회")
        
        # 포지션 상세
        if self.account.positions:
            print(f"\n   보유 포지션:")
            for coin, pos in self.account.positions.items():
                current = current_prices.get(coin, pos.avg_buy_price)
                pnl = (current - pos.avg_buy_price) / pos.avg_buy_price * 100
                status = "🟢" if pnl >= 0 else "🔴"
                print(f"     {status} {coin}: {pos.amount:.8f} @ {pos.avg_buy_price:,.0f} ({pnl:+.1f}%)")
        
        print(f"{'='*60}\n")


# 편의 함수
def get_paper_connector() -> PaperTradingConnector:
    """페이퍼트레이딩 연동 인스턴스 반환"""
    return PaperTradingConnector()
