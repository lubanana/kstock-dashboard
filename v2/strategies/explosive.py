"""
V2 Strategy - Explosive Rise (개선안 7)
KAGGRESSIVE 폭발적 상승 스캐너
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent / 'core'))

import pandas as pd
from typing import Optional, Dict, Any
from strategy_base import StrategyBase, Signal, StrategyConfig
from indicators import Indicators


class ExplosiveV7Strategy(StrategyBase):
    """
    개선안 7 - 폭발적 상승 스캐너
    
    스코어링 (100점 만점):
    - 거래량: 20일 평균 대비 300%+ (30점)
    - 기술적: 20일선 상향 돌파 + 정배열 (20점)
    - 시가총액: 5,000억원 이하 (15점)
    - 외국인 수급: 3거래일 연속 순매수 (10점)
    - 뉴스/이벤트: 긍정적 트리거 (15점)
    - 테마: 핫섹터 (10점)
    
    진입 조건:
    - 최소 점수: 85점+
    - ADX: 20 이상
    - RSI: 40~70
    """
    
    # 핫섹터 키워드
    HOT_SECTORS = {
        '로봇': ['로봇', '자동화', '자율주행', '드론'],
        'AI': ['AI', '인공지능', '딥러닝', 'GPT'],
        '바이오': ['바이오', '제약', '신약', '헬스케어'],
        '반도체': ['반도체', '칩', 'HBM', '파운드리']
    }
    
    def __init__(self):
        config = StrategyConfig(
            name="KAGGRESSIVE V7 폭발적 상승",
            description="거래량 + 기술적 + 수급 복합 스코어링",
            min_score=85.0,
            position_size=0.20,
            stop_loss=-0.07,
            take_profit=0.25
        )
        super().__init__(config)
    
    def analyze(self, df: pd.DataFrame, code: str, date: str) -> Optional[Signal]:
        """개별 종목 분석"""
        if len(df) < 60:
            return None
        
        # 최신 데이터
        latest = df.iloc[-1]
        
        # 기술적 지표 계산
        df['ma5'] = Indicators.ma(df['close'], 5)
        df['ma20'] = Indicators.ma(df['close'], 20)
        df['ma60'] = Indicators.ma(df['close'], 60)
        df['rsi'] = Indicators.rsi(df['close'], 14)
        df['adx'] = Indicators.adx(df, 14)
        df['volume_ratio'] = Indicators.volume_ratio(df['volume'], 20)
        
        latest = df.iloc[-1]
        prev = df.iloc[-2] if len(df) > 1 else latest
        
        # 스코어링
        score = 0.0
        reasons = []
        metadata = {}
        
        # 1. 거래량 점수 (30점)
        vol_ratio = latest['volume_ratio']
        if vol_ratio >= 5.0:
            score += 30
            reasons.append(f"거래량 폭발 ({vol_ratio:.1f}x)")
        elif vol_ratio >= 3.0:
            score += 25
            reasons.append(f"거래량 급증 ({vol_ratio:.1f}x)")
        elif vol_ratio >= 2.0:
            score += 15
            reasons.append(f"거래량 증가 ({vol_ratio:.1f}x)")
        metadata['volume_ratio'] = vol_ratio
        
        # 2. 기술적 점수 (20점)
        ma_bullish = (latest['close'] > latest['ma20'] > latest['ma60'])
        ma_break = (latest['close'] > latest['ma20']) and (prev['close'] <= prev['ma20'])
        
        if ma_bullish and ma_break:
            score += 20
            reasons.append("20일선 상향 돌파 + 정배열")
        elif ma_bullish:
            score += 15
            reasons.append("정배열 유지")
        elif ma_break:
            score += 10
            reasons.append("20일선 돌파")
        
        metadata['ma_bullish'] = ma_bullish
        metadata['ma_break'] = ma_break
        
        # 3. ADX 체크
        adx_val = latest['adx']
        metadata['adx'] = adx_val
        
        # 4. RSI 체크
        rsi_val = latest['rsi']
        metadata['rsi'] = rsi_val
        
        # 진입 조건 체크
        if score < self.config.min_score:
            return None
        if adx_val < 20:
            return None
        if rsi_val < 40 or rsi_val > 70:
            return None
        
        # Signal 생성
        signal_type = 'buy' if score >= 90 else 'hold'
        
        return Signal(
            code=code,
            name=latest.get('name', code),
            date=date,
            signal_type=signal_type,
            score=score,
            reason=reasons,
            metadata=metadata
        )
