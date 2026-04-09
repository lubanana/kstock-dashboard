# fibonacci_target_integrated.py
"""
스캐너 통합용 목표가/손절가 계산 모듈
ATR + 피볼나치 하이브리드 방법론 적용
"""
import numpy as np
import pandas as pd
from dataclasses import dataclass
from typing import Tuple, Optional

@dataclass
class TargetStopLoss:
    """목표가/손절가 데이터 클래스"""
    entry: float
    stop_loss: float
    tp1: float  # 127.2%
    tp2: float  # 161.8% 
    tp3: float  # 261.8%
    atr: float
    risk_reward_1: float
    risk_reward_2: float
    risk_reward_3: float
    stop_pct: float
    tp1_pct: float
    tp2_pct: float
    tp3_pct: float
    method: str
    
class FibonacciATRCalculator:
    """피볼나치 + ATR 기반 목표가/손절가 계산기"""
    
    # 피볼나치 확장 레벨
    FIB_EXT_TP1 = 0.272   # 127.2%
    FIB_EXT_TP2 = 0.618   # 161.8%
    FIB_EXT_TP3 = 1.618   # 261.8%
    
    # ATR 승수
    ATR_SL_MULT = 2.0     # 손절가
    ATR_TP1_MULT = 2.0    # TP1
    ATR_TP2_MULT = 3.0    # TP2
    ATR_TP3_MULT = 4.0    # TP3
    
    def __init__(self, max_lookback: int = 60):
        self.max_lookback = max_lookback
    
    def calculate_atr(self, df: pd.DataFrame, period: int = 14) -> float:
        """ATR 계산"""
        if len(df) < period + 1:
            return 0.0
        
        # 컬럼명 대소문자 처리
        high_col = 'High' if 'High' in df.columns else 'high'
        low_col = 'Low' if 'Low' in df.columns else 'low'
        close_col = 'Close' if 'Close' in df.columns else 'close'
            
        high_low = df[high_col] - df[low_col]
        high_close = np.abs(df[high_col] - df[close_col].shift())
        low_close = np.abs(df[low_col] - df[close_col].shift())
        
        ranges = pd.concat([high_low, high_close, low_close], axis=1)
        true_range = np.max(ranges, axis=1)
        atr = true_range.rolling(period).mean().iloc[-1]
        
        return atr
    
    def find_swing_points(self, df: pd.DataFrame, lookback: int = 40) -> Tuple[float, float]:
        """
        스윙 고점/저점 찾기
        Returns: (swing_high, swing_low)
        """
        if len(df) < lookback:
            lookback = len(df)
            
        recent_df = df.tail(lookback)
        
        # 컬럼명 대소문자 처리
        high_col = 'High' if 'High' in df.columns else 'high'
        low_col = 'Low' if 'Low' in df.columns else 'low'
            
        # 단순 고점/저점
        swing_high = recent_df[high_col].max()
        swing_low = recent_df[low_col].min()
        
        return swing_high, swing_low
    
    def calculate_fibonacci_levels(self, swing_high: float, swing_low: float, 
                                    current: float) -> dict:
        """
        피볼나치 되돌림 레벨 계산
        """
        range_size = swing_high - swing_low
        
        levels = {
            'swing_high': swing_high,
            'swing_low': swing_low,
            'range': range_size,
            '23.6%': swing_high - range_size * 0.236,
            '38.2%': swing_high - range_size * 0.382,
            '50%': swing_high - range_size * 0.5,
            '61.8%': swing_high - range_size * 0.618,
            '78.6%': swing_high - range_size * 0.786,
        }
        
        # 현재 위치 계산
        if range_size > 0:
            retracement = (swing_high - current) / range_size
            levels['current_retracement'] = retracement
        else:
            levels['current_retracement'] = 0
            
        return levels
    
    def calculate_targets(self, df: pd.DataFrame, entry: float, 
                          method: str = 'hybrid') -> Optional[TargetStopLoss]:
        """
        목표가/손절가 통합 계산
        
        Args:
            df: OHLCV 데이터프레임
            entry: 진입가
            method: 'atr', 'fibonacci', 'hybrid'
        
        Returns:
            TargetStopLoss 객체
        """
        if len(df) < 20:
            return None
            
        # ATR 계산
        atr = self.calculate_atr(df)
        atr_pct = atr / entry * 100 if entry > 0 else 0
        
        # 스윙 포인트 찾기
        swing_high, swing_low = self.find_swing_points(df)
        swing_range = swing_high - swing_low
        
        # 손절가 계산
        if method == 'atr':
            stop_loss = entry - (atr * self.ATR_SL_MULT)
            
        elif method == 'fibonacci':
            # 피볼나치 61.8% 또는 78.6% 기준
            fib_618 = swing_high - swing_range * 0.618
            fib_786 = swing_high - swing_range * 0.786
            
            # 진입가와의 거리 고려
            if entry > fib_618:
                stop_loss = fib_786
            else:
                stop_loss = fib_618
                
        else:  # hybrid (권장)
            # ATR과 피볼나치 중 보수적인 쪽 선택
            atr_stop = entry - (atr * self.ATR_SL_MULT)
            fib_618 = swing_high - swing_range * 0.618
            fib_786 = swing_high - swing_range * 0.786
            
            # 진입가 위치에 따른 피볼나치 손절가 선택
            # 진입가가 fib_618 아래면 fib_786 사용, 아니면 fib_618 사용
            if entry < fib_618:
                fib_stop = fib_786  # 더 깊은 되돌림 기준
            else:
                fib_stop = fib_618
            
            # ATR 손절가와 피볼나치 손절가 중 높은쪽 선택 (손실 제한)
            stop_loss = max(atr_stop, fib_stop)
            
            # 최대 -7% 제한 (stop_loss가 너무 낮아지지 않도록)
            max_stop_limit = entry * 0.93
            if stop_loss < max_stop_limit:
                stop_loss = max_stop_limit
        
        # 목표가 계산 (피볼나치 확장 기반)
        tp1 = swing_high + (swing_range * self.FIB_EXT_TP1)
        tp2 = swing_high + (swing_range * self.FIB_EXT_TP2)
        tp3 = swing_high + (swing_range * self.FIB_EXT_TP3)
        
        # ATR 기반 목표가와 비교하여 더 높은 값 선택
        atr_tp1 = entry + (atr * self.ATR_TP1_MULT)
        atr_tp2 = entry + (atr * self.ATR_TP2_MULT)
        atr_tp3 = entry + (atr * self.ATR_TP3_MULT)
        
        tp1 = max(tp1, atr_tp1)
        tp2 = max(tp2, atr_tp2)
        tp3 = max(tp3, atr_tp3)
        
        # 손익비 계산
        risk = entry - stop_loss
        if risk <= 0:
            risk = entry * 0.01  # 최소 1% 리스크
            
        reward1 = tp1 - entry
        reward2 = tp2 - entry
        reward3 = tp3 - entry
        
        rr1 = reward1 / risk if risk > 0 else 0
        rr2 = reward2 / risk if risk > 0 else 0
        rr3 = reward3 / risk if risk > 0 else 0
        
        return TargetStopLoss(
            entry=entry,
            stop_loss=round(stop_loss, 0),
            tp1=round(tp1, 0),
            tp2=round(tp2, 0),
            tp3=round(tp3, 0),
            atr=round(atr, 0),
            risk_reward_1=round(rr1, 2),
            risk_reward_2=round(rr2, 2),
            risk_reward_3=round(rr3, 2),
            stop_pct=round((stop_loss - entry) / entry * 100, 2),
            tp1_pct=round((tp1 - entry) / entry * 100, 2),
            tp2_pct=round((tp2 - entry) / entry * 100, 2),
            tp3_pct=round((tp3 - entry) / entry * 100, 2),
            method=method
        )
    
    def get_position_sizing(self, capital: float, risk_pct: float, 
                           entry: float, stop_loss: float) -> dict:
        """
        포지션 사이징 계산 (퍼센트 리스크법)
        """
        risk_amount = capital * (risk_pct / 100)
        risk_per_share = abs(entry - stop_loss)
        
        if risk_per_share <= 0:
            return {'shares': 0, 'position_value': 0, 'risk_amount': 0}
            
        shares = int(risk_amount / risk_per_share)
        position_value = shares * entry
        
        return {
            'shares': shares,
            'position_value': position_value,
            'risk_amount': shares * risk_per_share,
            'risk_pct': risk_pct
        }


def format_target_output(target: TargetStopLoss) -> str:
    """출력 포맷팅"""
    return f"""
======================================================================
🎯 목표가/손절가 분석
======================================================================
진입가: {target.entry:,.0f}원
ATR(14): {target.atr:,.0f}원

📉 손절가: {target.stop_loss:,.0f}원 ({target.stop_pct:+.1f}%)

📈 목표가:
  TP1 (127.2%): {target.tp1:,.0f}원 ({target.tp1_pct:+.1f}%) | R:R = 1:{target.risk_reward_1:.1f}
  TP2 (161.8%): {target.tp2:,.0f}원 ({target.tp2_pct:+.1f}%) | R:R = 1:{target.risk_reward_2:.1f} ⭐
  TP3 (261.8%): {target.tp3:,.0f}원 ({target.tp3_pct:+.1f}%) | R:R = 1:{target.risk_reward_3:.1f}

💡 분할 익절 전략:
  1차 (30%): {target.tp1:,.0f}원 도달 시
  2차 (40%): {target.tp2:,.0f}원 도달 시 + 트레일링 스탑
  3차 (30%): {target.tp3:,.0f}원 도달 시

계산방법: {target.method}
"""


# 스캐너 통합용 래퍼 함수
def calculate_scanner_targets(df: pd.DataFrame, entry: float) -> Optional[dict]:
    """
    스캐너에서 호출하는 통합 함수
    Returns: dict with target/stoploss data
    """
    calc = FibonacciATRCalculator()
    result = calc.calculate_targets(df, entry, method='hybrid')
    
    if result is None:
        return None
        
    return {
        'entry': result.entry,
        'stop_loss': result.stop_loss,
        'tp1': result.tp1,
        'tp2': result.tp2,
        'tp3': result.tp3,
        'atr': result.atr,
        'risk_reward_tp2': result.risk_reward_2,
        'stop_pct': result.stop_pct,
        'tp2_pct': result.tp2_pct,
        'method': result.method
    }


if __name__ == '__main__':
    # 테스트
    print("모듈 테스트 - 신원종합개발(017000) 현재가 3,025원 기준")
    print("스캐너 통합용 모듈 로드 완료")
