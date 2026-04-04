#!/usr/bin/env python3
"""
리스크 매니저 - 포지션 크기 계산
OKComputer 시스템에서 추출
"""

from dataclasses import dataclass
from typing import Dict, Any


@dataclass
class RiskConfig:
    """리스크 설정"""
    max_position_size_percent: float = 10.0  # 최대 포지션 크기 (%)
    max_single_trade_percent: float = 5.0   # 한 번에 투자할 최대 비율
    max_positions: int = 5                   # 최대 동시 포지션 개수
    daily_loss_limit_percent: float = 5.0    # 일일 최대 손실 한도
    stop_loss_pct: float = 3.0               # 손절 비율
    take_profit_pct: float = 6.0             # 익절 비율


class RiskManager:
    """리스크 관리 시스템"""
    
    def __init__(self, config: RiskConfig = None):
        self.config = config or RiskConfig()
    
    def calculate_position_size(
        self,
        balance: float,
        confidence: float = 0.5,
        current_price: float = 0
    ) -> float:
        """
        포지션 크기 계산 (켈리 공식 기반)
        
        Args:
            balance: 사용 가능한 잔고
            confidence: 전략 신뢰도 (0.0 ~ 1.0)
            current_price: 현재가 (코인 수량 계산용)
            
        Returns:
            투자 금액 (KRW)
        """
        # 신뢰도 기반 포지션 크기 조정
        # confidence 1.0 → max_position_size_percent
        # confidence 0.0 → 0
        max_position = balance * (self.config.max_position_size_percent / 100)
        position_value = max_position * confidence
        
        # 한 번에 투자할 최대 비율 제한
        max_single = balance * (self.config.max_single_trade_percent / 100)
        position_value = min(position_value, max_single)
        
        return position_value
    
    def calculate_coin_units(self, investment_krw: float, price: float) -> float:
        """코인 수량 계산"""
        if price <= 0:
            return 0
        return investment_krw / price
    
    def check_position_limit(self, current_positions: int) -> bool:
        """포지션 개수 제한 체크"""
        return current_positions < self.config.max_positions
    
    def calculate_stop_loss(self, entry_price: float) -> float:
        """손절가 계산"""
        return entry_price * (1 - self.config.stop_loss_pct / 100)
    
    def calculate_take_profit(self, entry_price: float) -> float:
        """익절가 계산"""
        return entry_price * (1 + self.config.take_profit_pct / 100)
    
    def get_risk_metrics(self, balance: float, positions_value: float) -> Dict[str, Any]:
        """리스크 메트릭스"""
        used_percent = (positions_value / balance * 100) if balance > 0 else 0
        
        return {
            'balance': balance,
            'positions_value': positions_value,
            'available': balance - positions_value,
            'used_percent': used_percent,
            'max_position_size_percent': self.config.max_position_size_percent,
            'max_single_trade_percent': self.config.max_single_trade_percent,
            'remaining_capacity': self.config.max_position_size_percent - used_percent
        }


# 편의 함수
def create_conservative_risk_config() -> RiskConfig:
    """보수적 리스크 설정"""
    return RiskConfig(
        max_position_size_percent=5.0,
        max_single_trade_percent=2.0,
        max_positions=3,
        daily_loss_limit_percent=2.0,
        stop_loss_pct=2.0,
        take_profit_pct=4.0
    )


def create_aggressive_risk_config() -> RiskConfig:
    """공격적 리스크 설정"""
    return RiskConfig(
        max_position_size_percent=20.0,
        max_single_trade_percent=10.0,
        max_positions=10,
        daily_loss_limit_percent=10.0,
        stop_loss_pct=5.0,
        take_profit_pct=10.0
    )


# 전역 인스턴스
risk_manager = RiskManager()
