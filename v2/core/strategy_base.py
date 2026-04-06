"""
V2 Core - Strategy Base
전략 베이스 클래스
"""
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Dict, List, Optional, Any
import pandas as pd
from datetime import datetime


@dataclass
class Signal:
    """매매 신호 데이터클스"""
    code: str
    name: str
    date: str
    signal_type: str  # 'buy', 'sell', 'hold'
    score: float
    reason: List[str]
    metadata: Dict[str, Any]
    
    def to_dict(self) -> dict:
        return {
            'code': self.code,
            'name': self.name,
            'date': self.date,
            'signal_type': self.signal_type,
            'score': self.score,
            'reason': self.reason,
            'metadata': self.metadata
        }


@dataclass 
class StrategyConfig:
    """전략 설정 데이터클스"""
    name: str
    description: str
    min_score: float = 70.0
    position_size: float = 0.1  # 포지션 비중 (10%)
    stop_loss: float = -0.07    # 손절 -7%
    take_profit: float = 0.25   # 익절 +25%
    max_holding_days: int = 7   # 최대 보유일


class StrategyBase(ABC):
    """전략 베이스 클래스"""
    
    def __init__(self, config: StrategyConfig):
        self.config = config
        self.signals: List[Signal] = []
    
    @abstractmethod
    def analyze(self, 
                df: pd.DataFrame, 
                code: str,
                date: str) -> Optional[Signal]:
        """
        개별 종목 분석
        
        Args:
            df: 종목 데이터 (최소 60일)
            code: 종목코드
            date: 기준일
            
        Returns:
            Signal 객체 또는 None
        """
        pass
    
    def filter_by_score(self, min_score: Optional[float] = None) -> List[Signal]:
        """점수 기준 필터링"""
        threshold = min_score or self.config.min_score
        return [s for s in self.signals if s.score >= threshold]
    
    def get_top_signals(self, n: int = 10) -> List[Signal]:
        """상위 N개 신호"""
        sorted_signals = sorted(self.signals, key=lambda x: x.score, reverse=True)
        return sorted_signals[:n]
    
    def run(self, 
           data_manager,
           date: str,
           codes: Optional[List[str]] = None) -> List[Signal]:
        """
        전략 실행
        
        Args:
            data_manager: DataManager 인스턴스
            date: 기준일
            codes: 분석할 종목 리스트 (None=전체)
            
        Returns:
            신호 리스트
        """
        self.signals = []
        
        if codes is None:
            codes = data_manager.get_all_codes(date)
        
        for code in codes:
            df = data_manager.load_stock_data(code, date)
            if df is None or len(df) < 20:
                continue
                
            signal = self.analyze(df, code, date)
            if signal:
                self.signals.append(signal)
        
        return self.signals
    
    def get_stats(self) -> Dict[str, Any]:
        """전략 실행 통계"""
        if not self.signals:
            return {
                'total': 0, 
                'avg_score': 0, 
                'max_score': 0,
                'min_score': 0,
                'buy_signals': 0,
                'hold_signals': 0
            }
        
        scores = [s.score for s in self.signals]
        return {
            'total': len(self.signals),
            'avg_score': sum(scores) / len(scores),
            'max_score': max(scores),
            'min_score': min(scores),
            'buy_signals': len([s for s in self.signals if s.signal_type == 'buy']),
            'hold_signals': len([s for s in self.signals if s.signal_type == 'hold'])
        }
