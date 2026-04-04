#!/usr/bin/env python3
"""
서킷 브레이커 - 페이퍼트레이딩 연동
OKComputer 시스템에서 추출
"""

from datetime import datetime, timedelta
from enum import Enum
from typing import Dict, List, Optional, Any
from collections import deque
import json


class CircuitState(Enum):
    """서킷 브레이커 상태"""
    CLOSED = "closed"      # 정상 작동
    OPEN = "open"          # 차단 상태
    HALF_OPEN = "half_open"  # 테스트 모드


class CircuitBreaker:
    """
    연속 손실 감지, 일일 손한도 관리, 자동 중지 기능
    """
    
    def __init__(
        self,
        consecutive_losses_threshold: int = 3,
        daily_loss_limit_percent: float = 5.0,
        open_duration_minutes: int = 30,
        max_trades_per_hour: int = 20,
        max_trades_per_day: int = 100
    ):
        self.consecutive_losses_threshold = consecutive_losses_threshold
        self.daily_loss_limit_percent = daily_loss_limit_percent
        self.open_duration_minutes = open_duration_minutes
        self.max_trades_per_hour = max_trades_per_hour
        self.max_trades_per_day = max_trades_per_day
        
        self.state = CircuitState.CLOSED
        self._loss_history: deque = deque()
        self._trade_history: deque = deque()
        self._state_changed_at: Optional[datetime] = None
        self._daily_pnl = 0.0
        self._initial_balance = 0.0
        
        # 상태 파일
        self.state_file = "paper_trading_data/circuit_state.json"
        self._load_state()
    
    def _load_state(self):
        """상태 로드"""
        import os
        if os.path.exists(self.state_file):
            try:
                with open(self.state_file, 'r') as f:
                    data = json.load(f)
                    self.state = CircuitState(data.get('state', 'closed'))
                    self._daily_pnl = data.get('daily_pnl', 0.0)
            except:
                pass
    
    def _save_state(self):
        """상태 저장"""
        import os
        os.makedirs(os.path.dirname(self.state_file), exist_ok=True)
        with open(self.state_file, 'w') as f:
            json.dump({
                'state': self.state.value,
                'daily_pnl': self._daily_pnl,
                'updated_at': datetime.now().isoformat()
            }, f)
    
    def set_initial_balance(self, balance: float):
        """초기 잔고 설정"""
        self._initial_balance = balance
    
    def record_trade(self, coin: str, side: str, pnl: float, pnl_pct: float):
        """거래 결과 기록"""
        now = datetime.now()
        
        self._trade_history.append({
            'timestamp': now,
            'coin': coin,
            'side': side,
            'pnl': pnl,
            'pnl_pct': pnl_pct
        })
        
        self._daily_pnl += pnl
        
        # 손실 기록
        if pnl < 0:
            self._loss_history.append({
                'timestamp': now,
                'pnl': pnl
            })
        else:
            # 수익 시 연속 손실 초기화
            self._loss_history.clear()
        
        # 서킷 브레이커 체크
        self._check_circuit_breaker()
        self._save_state()
    
    def _check_circuit_breaker(self):
        """서킷 브레이커 체크"""
        # 일일 손한도 체크
        if self._initial_balance > 0:
            daily_loss_pct = abs(min(0, self._daily_pnl)) / self._initial_balance * 100
            if daily_loss_pct >= self.daily_loss_limit_percent:
                self._change_state(CircuitState.OPEN, f"일일 손한도 도달: {daily_loss_pct:.2f}%")
                return
        
        # 연속 손실 체크
        window = timedelta(minutes=60)
        cutoff = datetime.now() - window
        recent_losses = [l for l in self._loss_history if l['timestamp'] > cutoff]
        
        if len(recent_losses) >= self.consecutive_losses_threshold:
            self._change_state(
                CircuitState.OPEN, 
                f"연속 손실 {len(recent_losses)}회 도달"
            )
            return
    
    def _change_state(self, new_state: CircuitState, reason: str):
        """상태 변경"""
        old_state = self.state
        self.state = new_state
        self._state_changed_at = datetime.now()
        
        print(f"\n{'='*60}")
        print(f"🛑 서킷 브레이커 발동!")
        print(f"   상태: {old_state.value} → {new_state.value}")
        print(f"   사유: {reason}")
        print(f"   시간: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"{'='*60}\n")
    
    def can_trade(self) -> bool:
        """거래 가능 여부 확인"""
        # 차단 상태 체크
        if self.state == CircuitState.OPEN:
            if self._state_changed_at:
                elapsed = datetime.now() - self._state_changed_at
                if elapsed >= timedelta(minutes=self.open_duration_minutes):
                    self._change_state(CircuitState.HALF_OPEN, "자동 복구 시도")
                    return True
            return False
        
        return True
    
    def get_status(self) -> Dict[str, Any]:
        """상태 조회"""
        window = timedelta(minutes=60)
        cutoff = datetime.now() - window
        recent_losses = [l for l in self._loss_history if l['timestamp'] > cutoff]
        
        daily_loss_pct = 0
        if self._initial_balance > 0:
            daily_loss_pct = abs(min(0, self._daily_pnl)) / self._initial_balance * 100
        
        return {
            'state': self.state.value,
            'can_trade': self.can_trade(),
            'daily_pnl': self._daily_pnl,
            'daily_loss_percent': daily_loss_pct,
            'consecutive_losses': len(recent_losses),
            'consecutive_losses_threshold': self.consecutive_losses_threshold,
            'daily_loss_limit_percent': self.daily_loss_limit_percent
        }
    
    def reset(self):
        """수동 리셋"""
        self.state = CircuitState.CLOSED
        self._loss_history.clear()
        self._daily_pnl = 0.0
        self._save_state()
        print("✅ 서킷 브레이커 리셋 완료")


# 전역 인스턴스
circuit_breaker = CircuitBreaker()
