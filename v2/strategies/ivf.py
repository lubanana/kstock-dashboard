"""
V2 Strategy - IVF (Institutional Volume Fibonacci)
기관 수급 + 거래량 + 피볼나치 + ICT 통합 스캐너

4가지 핵심 요소:
1. 수급 (Supply/Demand): 기관/외국인 순매수, 캐피털 플로우
2. 거래량 (Volume): Volume Profile, POC, Value Area
3. 피볼나치 파동 (Fibonacci): 되돌림 38.2%/61.8%, 확장 161.8%
4. ICT (Inner Circle Trader): FVG, Order Blocks, MSB/CHoCH

특징:
- RSI, MACD 같은 소매 지표 제외
- 스마트 머니/기관 흔름 중심
- 알고리즘 트레이딩 발자국 읽기
"""
import pandas as pd
import numpy as np
from typing import Optional, Dict, Any, List, Tuple
from strategy_base import StrategyBase, Signal, StrategyConfig
from indicators import Indicators


class IVFScanner(StrategyBase):
    """
    IVF (Institutional Volume Fibonacci) 스캐너
    
    스코어링 (100점 만점):
    - 수급 (Supply/Demand): 30점
      * 기관 연속 순매수 (15점)
      * 외국인 연속 순매수 (15점)
    
    - 거래량 (Volume Profile): 25점
      * POC (Point of Control) 근접 (10점)
      * Value Area 내 위치 (10점)
      * 거래량 급증 (5점)
    
    - 피볼나치 (Fibonacci): 25점
      * 38.2% ~ 61.8% 되돌림 구간 (15점)
      * 161.8% 확장 근접 (10점)
    
    - ICT (Market Structure): 20점
      * Fair Value Gap (FVG) (8점)
      * Order Block 존재 (7점)
      * MSB/CHoCH 확인 (5점)
    
    진입 조건:
    - 총점 75점+
    - 최소 2개 영역에서 60%+ 점수
    """
    
    def __init__(self):
        config = StrategyConfig(
            name="IVF (Institutional Volume Fibonacci)",
            description="기관 수급 + 거래량 + 피볼나치 + ICT 통합",
            min_score=75.0,
            position_size=0.15,
            stop_loss=-0.05,  # 5% ( tighter for ICT)
            take_profit=0.20  # 20%
        )
        super().__init__(config)
    
    def analyze(self, df: pd.DataFrame, code: str, date: str) -> Optional[Signal]:
        """IVF 분석"""
        if len(df) < 60:
            return None
        
        # 기술적 지표 계산
        df['ma20'] = Indicators.ma(df['close'], 20)
        df['ma60'] = Indicators.ma(df['close'], 60)
        df['atr'] = Indicators.atr(df, 14)
        
        latest = df.iloc[-1]
        current_price = latest['close']
        
        # 각 영역 분석
        scores = {}
        metadata = {}
        reasons = []
        
        # 1. 수급 분석 (30점)
        supply_score, supply_meta = self._analyze_supply_demand(df)
        scores['supply'] = supply_score
        metadata.update(supply_meta)
        if supply_score >= 15:
            reasons.append(f"강한 수급 ({supply_score:.0f}점)")
        
        # 2. 거래량 프로파일 (25점)
        volume_score, volume_meta = self._analyze_volume_profile(df)
        scores['volume'] = volume_score
        metadata.update(volume_meta)
        if volume_score >= 12:
            reasons.append(f"볼륨 프로파일 우위 ({volume_score:.0f}점)")
        
        # 3. 피볼나치 파동 (25점)
        fib_score, fib_meta = self._analyze_fibonacci(df)
        scores['fibonacci'] = fib_score
        metadata.update(fib_meta)
        if fib_score >= 12:
            reasons.append(f"피볼나치 적중 ({fib_score:.0f}점)")
        
        # 4. ICT 구조 (20점)
        ict_score, ict_meta = self._analyze_ict(df)
        scores['ict'] = ict_score
        metadata.update(ict_meta)
        if ict_score >= 10:
            reasons.append(f"ICT 시그널 ({ict_score:.0f}점)")
        
        # 총점 계산
        total_score = sum(scores.values())
        metadata['scores'] = scores
        metadata['total_score'] = total_score
        
        # 진입 조건 체크
        if total_score < self.config.min_score:
            return None
        
        # 최소 2개 영역 60%+ 체크
        high_scores = sum(1 for s in scores.values() if s >= 15)
        if high_scores < 2:
            return None
        
        return Signal(
            code=code,
            name=latest.get('name', code),
            date=date,
            signal_type='buy' if total_score >= 85 else 'hold',
            score=total_score,
            reason=reasons if reasons else ["IVF 복합 신호"],
            metadata=metadata
        )
    
    def _analyze_supply_demand(self, df: pd.DataFrame) -> Tuple[float, Dict]:
        """수급 분석 (30점 만점)"""
        score = 0.0
        meta = {}
        
        # 거래대금 추정 (실제 수급 데이터가 없으므로 근사)
        # 고가/저가/종가 기반으로 기관성 매수 추정
        df['buying_pressure'] = (df['close'] - df['low']) / (df['high'] - df['low'] + 0.001)
        df['selling_pressure'] = (df['high'] - df['close']) / (df['high'] - df['low'] + 0.001)
        
        # 연속 매수세 체크 (최근 5일)
        recent_pressure = df['buying_pressure'].tail(5).mean()
        meta['buying_pressure'] = recent_pressure
        
        if recent_pressure >= 0.7:
            score += 30
            meta['supply_signal'] = 'strong_buying'
        elif recent_pressure >= 0.6:
            score += 20
            meta['supply_signal'] = 'moderate_buying'
        elif recent_pressure >= 0.5:
            score += 10
            meta['supply_signal'] = 'neutral'
        else:
            meta['supply_signal'] = 'selling'
        
        return score, meta
    
    def _analyze_volume_profile(self, df: pd.DataFrame) -> Tuple[float, Dict]:
        """거래량 프로파일 분석 (25점 만점)"""
        score = 0.0
        meta = {}
        
        # 최근 20일 Volume Profile
        recent = df.tail(20).copy()
        
        # POC (최대 거래량 가격대)
        # 근사: 거래량이 가장 많았던 종가
        poc_idx = recent['volume'].idxmax()
        poc_price = recent.loc[poc_idx, 'close']
        meta['poc_price'] = poc_price
        
        current_price = df.iloc[-1]['close']
        poc_distance = abs(current_price - poc_price) / poc_price
        
        # POC 근접 점수
        if poc_distance <= 0.02:  # 2% 이내
            score += 10
            meta['poc_proximity'] = 'very_close'
        elif poc_distance <= 0.05:  # 5% 이내
            score += 7
            meta['poc_proximity'] = 'close'
        
        # Value Area (70% 거래량 구간)
        total_volume = recent['volume'].sum()
        recent_sorted = recent.sort_values('close')
        
        # 누적 거래량 15%~85% 구간
        volume_cumsum = recent_sorted['volume'].cumsum()
        va_start = recent_sorted[volume_cumsum >= total_volume * 0.15]['close'].iloc[0] if len(recent_sorted[volume_cumsum >= total_volume * 0.15]) > 0 else recent_sorted['close'].iloc[0]
        va_end = recent_sorted[volume_cumsum >= total_volume * 0.85]['close'].iloc[0] if len(recent_sorted[volume_cumsum >= total_volume * 0.85]) > 0 else recent_sorted['close'].iloc[-1]
        
        meta['value_area'] = (va_start, va_end)
        
        if va_start <= current_price <= va_end:
            score += 10
            meta['in_value_area'] = True
        else:
            meta['in_value_area'] = False
        
        # 거래량 급증
        volume_ratio = df.iloc[-1]['volume'] / df['volume'].tail(20).mean()
        meta['volume_ratio'] = volume_ratio
        
        if volume_ratio >= 2.0:
            score += 5
        
        return score, meta
    
    def _analyze_fibonacci(self, df: pd.DataFrame) -> Tuple[float, Dict]:
        """피볼나치 파동 분석 (25점 만점)"""
        score = 0.0
        meta = {}
        
        # 최근 추세의 고점/저점 찾기
        recent = df.tail(40)
        swing_high = recent['high'].max()
        swing_low = recent['low'].min()
        
        if swing_high == swing_low:
            return 0, meta
        
        # 되돌림 레벨 계산
        diff = swing_high - swing_low
        fib_levels = {
            '0.0': swing_high,
            '0.382': swing_high - diff * 0.382,
            '0.5': swing_high - diff * 0.5,
            '0.618': swing_high - diff * 0.618,
            '1.0': swing_low
        }
        
        current_price = df.iloc[-1]['close']
        
        # 38.2% ~ 61.8% 되돌림 구간 확인
        in_retracement = fib_levels['0.382'] >= current_price >= fib_levels['0.618']
        
        # 각 레벨과의 근접도
        min_distance = min(abs(current_price - level) / current_price 
                          for level in fib_levels.values())
        
        meta['fib_levels'] = fib_levels
        meta['current_price'] = current_price
        meta['min_distance'] = min_distance
        
        # 되돌림 구간 점수
        if in_retracement:
            score += 15
            meta['retracement_zone'] = True
            
            # 정확히 레벨에 근접하면 본점
            if min_distance <= 0.01:  # 1% 이내
                score += 5
        else:
            meta['retracement_zone'] = False
        
        # 161.8% 확장 레벨 (다음 목표)
        extension_1618 = swing_high + diff * 0.618
        meta['extension_1618'] = extension_1618
        
        # 확장 가능성 점수
        if current_price > swing_high * 0.95:  # 고점 근처
            score += 5
            meta['near_high'] = True
        
        return score, meta
    
    def _analyze_ict(self, df: pd.DataFrame) -> Tuple[float, Dict]:
        """ICT 구조 분석 (20점 만점)"""
        score = 0.0
        meta = {}
        
        # Fair Value Gap (FVG) 감지
        # 조건: 전봉 고점 < 현봉 저점 (상승 FVG)
        fvg_detected = False
        
        for i in range(2, len(df)):
            prev_high = df.iloc[i-1]['high']
            curr_low = df.iloc[i]['low']
            
            if prev_high < curr_low:
                fvg_detected = True
                meta['fvg_date'] = df.iloc[i]['date']
                meta['fvg_range'] = (prev_high, curr_low)
                break
        
        if fvg_detected:
            score += 8
            meta['fvg'] = True
        else:
            meta['fvg'] = False
        
        # Order Block 근사 감지
        # 큰 양봉 이후의 눌림목
        df['candle_size'] = df['close'] - df['open']
        df['body_size'] = abs(df['candle_size'])
        
        # 큰 양봉 찾기
        large_bullish = df[df['candle_size'] > df['body_size'].quantile(0.8)]
        
        if len(large_bullish) > 0:
            # 최근 큰 양봉의 저점
            last_ob_low = large_bullish.iloc[-1]['low']
            current_price = df.iloc[-1]['close']
            
            # Order Block 근접
            ob_distance = (current_price - last_ob_low) / current_price
            
            if 0 <= ob_distance <= 0.05:  # 5% 이내 상승
                score += 7
                meta['order_block'] = True
                meta['ob_level'] = last_ob_low
            else:
                meta['order_block'] = False
        
        # MSB (Market Structure Break) 근사
        # 고점/저점 갱신 체크
        recent = df.tail(10)
        higher_highs = all(recent['high'].iloc[i] >= recent['high'].iloc[i-1] 
                          for i in range(1, len(recent)-2))
        
        if higher_highs:
            score += 5
            meta['msb'] = 'bullish'
        else:
            meta['msb'] = 'none'
        
        return score, meta
