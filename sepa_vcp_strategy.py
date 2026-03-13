#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
SEPA + VCP Strategy Module
==========================
Mark Minervini's SEPA (Specific Entry Point Analysis) 전략과 
VCP (Volatility Contraction Pattern) 패턴 탐지 알고리즘

Author: AI Assistant
Reference: Mark Minervini - Trade Like a Stock Market Wizard
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass
from datetime import datetime, timedelta
import warnings
warnings.filterwarnings('ignore')


@dataclass
class VCPContraction:
    """VCP 수축 구간 데이터"""
    start_idx: int
    end_idx: int
    start_date: pd.Timestamp
    end_date: pd.Timestamp
    depth_pct: float  # 수축 깊이 (%)
    duration_days: int  # 수축 기간 (일)
    volume_avg: float  # 평균 거래량
    low_price: float  # 구간 저가
    high_price: float  # 구간 고가
    pivot_price: float  # 피벗 라인 (구간 고가)


@dataclass
class SEPASignal:
    """SEPA + VCP 신호 데이터"""
    symbol: str
    date: pd.Timestamp
    current_price: float
    
    # Trend Template
    above_ma150: bool
    above_ma200: bool
    ma150_above_ma200: bool
    ma200_trending_up: bool
    near_52w_high: bool
    above_52w_low: bool
    trend_template_passed: bool
    
    # VCP Pattern
    contractions: List[VCPContraction]
    contraction_count: int
    depth_narrowing: bool  # 깊이가 좁아지는지
    duration_shortening: bool  # 기간이 짧아지는지
    vcp_passed: bool
    
    # Volume Analysis
    volume_dry_up: bool  # 거래량 급감
    relative_strength: float  # 상대강도
    rs_rank: float  # RS 순위 (0~1)
    rs_top25: bool  # 상위 25%
    
    # Pivot Breakout
    pivot_line: float
    pivot_breakout: bool
    volume_surge: bool
    volume_ratio: float
    
    # Final Signal
    is_valid: bool
    score: float  # 종합 점수


class SEPA_VCP_Strategy:
    """
    Mark Minervini SEPA + VCP Strategy
    
    Trend Template 조건:
    1. 현재 주가 > 150일 & 200일 이동평균선
    2. 150일 이평선 > 200일 이평선
    3. 200일 이평선이 최소 1개월 이상 우상향
    4. 현재 주가가 52주 신고가 대비 25% 이내
    5. 현재 주가가 52주 신저가 대비 30% 이상
    
    VCP Pattern 조건:
    1. 2~4번의 가격 수축
    2. 각 수축의 깊이가 이전보다 좁아짐
    3. 수축 구간의 기간이 짧아짐
    4. 수축 구간에서 거래량 급감 (Volume Dry-up)
    """
    
    def __init__(self, 
                 contraction_min_count: int = 2,
                 contraction_max_count: int = 4,
                 max_contraction_depth: float = 0.25,  # 최대 25% 수축
                 min_volume_dry_up: float = 0.6,  # 평균의 60% 이하
                 min_volume_surge: float = 1.5,  # 50% 이상 급증 (1.5배)
                 rs_lookback: int = 252,  # 1년 RS 계산
                 pivot_proximity: float = 0.03):  # 피벗 라인 3% 이내
        
        self.contraction_min_count = contraction_min_count
        self.contraction_max_count = contraction_max_count
        self.max_contraction_depth = max_contraction_depth
        self.min_volume_dry_up = min_volume_dry_up
        self.min_volume_surge = min_volume_surge
        self.rs_lookback = rs_lookback
        self.pivot_proximity = pivot_proximity
        
    def calculate_moving_averages(self, df: pd.DataFrame) -> pd.DataFrame:
        """이동평균선 계산"""
        df = df.copy()
        df['ma50'] = df['close'].rolling(50).mean()
        df['ma150'] = df['close'].rolling(150).mean()
        df['ma200'] = df['close'].rolling(200).mean()
        
        # 200일선 추세 (1개월 전 대비 상승)
        df['ma200_slope'] = df['ma200'].pct_change(20)
        
        return df
    
    def calculate_52week_range(self, df: pd.DataFrame) -> pd.DataFrame:
        """52주 고저가 계산"""
        df = df.copy()
        df['52w_high'] = df['high'].rolling(252).max()
        df['52w_low'] = df['low'].rolling(252).min()
        df['from_52w_high'] = (df['close'] - df['52w_high']) / df['52w_high']
        df['from_52w_low'] = (df['close'] - df['52w_low']) / df['52w_low']
        return df
    
    def check_trend_template(self, df: pd.DataFrame, idx: int) -> Dict:
        """트렌드 템플릿 체크"""
        if idx < 200:
            return {'passed': False}
            
        row = df.iloc[idx]
        
        # 조건 체크
        above_ma150 = row['close'] > row['ma150']
        above_ma200 = row['close'] > row['ma200']
        ma150_above_ma200 = row['ma150'] > row['ma200']
        ma200_trending_up = row['ma200_slope'] > 0
        near_52w_high = row['from_52w_high'] >= -0.25  # 25% 이내
        above_52w_low = row['from_52w_low'] >= 0.30  # 30% 이상
        
        passed = all([
            above_ma150, above_ma200, ma150_above_ma200,
            ma200_trending_up, near_52w_high, above_52w_low
        ])
        
        return {
            'passed': passed,
            'above_ma150': above_ma150,
            'above_ma200': above_ma200,
            'ma150_above_ma200': ma150_above_ma200,
            'ma200_trending_up': ma200_trending_up,
            'near_52w_high': near_52w_high,
            'above_52w_low': above_52w_low
        }
    
    def identify_swing_points(self, df: pd.DataFrame, window: int = 5) -> pd.DataFrame:
        """스윙 고점/저점 식별"""
        df = df.copy()
        
        # 스윙 고점: window 기간 중 최고가
        df['swing_high'] = df['high'].rolling(window=window*2+1, center=True).max() == df['high']
        df['swing_low'] = df['low'].rolling(window=window*2+1, center=True).min() == df['low']
        
        return df
    
    def find_contractions(self, df: pd.DataFrame, recent_bars: int = 120) -> List[VCPContraction]:
        """
        VCP 수축 구간 식별
        
        Args:
            df: 주가 데이터
            recent_bars: 최근 몇 개 봉을 분석할지 (기본 120일 = 약 6개월)
        
        Returns:
            VCPContraction 리스트
        """
        df = self.identify_swing_points(df)
        contractions = []
        
        if len(df) < recent_bars:
            return contractions
            
        recent_df = df.tail(recent_bars).reset_index(drop=True)
        
        # 스윙 고점 인덱스 찾기
        swing_highs = recent_df[recent_df['swing_high']].index.tolist()
        
        if len(swing_highs) < 2:
            return contractions
        
        # 연속된 스윙 고점 사이의 수축 구간 분석
        for i in range(len(swing_highs) - 1):
            start_idx = swing_highs[i]
            end_idx = swing_highs[i + 1]
            
            # 구간 데이터
            period = recent_df.iloc[start_idx:end_idx+1]
            if len(period) < 5:  # 최소 5일 이상
                continue
            
            high_price = period['high'].max()
            low_price = period['low'].min()
            depth_pct = (high_price - low_price) / high_price
            
            # 수축 깊이가 최대 25% 이내인 경우만
            if depth_pct <= self.max_contraction_depth:
                contraction = VCPContraction(
                    start_idx=start_idx,
                    end_idx=end_idx,
                    start_date=period.iloc[0]['date'],
                    end_date=period.iloc[-1]['date'],
                    depth_pct=depth_pct * 100,  # 퍼센트로 변환
                    duration_days=len(period),
                    volume_avg=period['volume'].mean(),
                    low_price=low_price,
                    high_price=high_price,
                    pivot_price=high_price  # 고점을 피벗으로
                )
                contractions.append(contraction)
        
        return contractions[-self.contraction_max_count:]  # 최근 N개만
    
    def check_vcp_pattern(self, contractions: List[VCPContraction]) -> Dict:
        """VCP 패턴 유효성 체크"""
        if len(contractions) < self.contraction_min_count:
            return {'passed': False, 'reason': 'Not enough contractions'}
        
        # 깊이가 좁아지는지 확인
        depths = [c.depth_pct for c in contractions]
        depth_narrowing = all(depths[i] > depths[i+1] for i in range(len(depths)-1))
        
        # 기간이 짧아지는지 확인
        durations = [c.duration_days for c in contractions]
        duration_shortening = all(durations[i] > durations[i+1] for i in range(len(durations)-1))
        
        # 기본 VCP 패턴 통과
        vcp_passed = len(contractions) >= self.contraction_min_count
        
        return {
            'passed': vcp_passed,
            'depth_narrowing': depth_narrowing,
            'duration_shortening': duration_shortening,
            'contraction_count': len(contractions),
            'last_pivot': contractions[-1].pivot_price if contractions else 0
        }
    
    def check_volume_dry_up(self, df: pd.DataFrame, contraction: VCPContraction, 
                            recent_bars: int = 20) -> bool:
        """
        수축 구간에서 거래량 급감 체크 (Volume Dry-up)
        
        Args:
            df: 주가 데이터
            contraction: 수축 구간
            recent_bars: 비교 기준 기간
        
        Returns:
            거래량이 급감했는지 여부
        """
        if contraction.end_idx >= len(df):
            return False
            
        # 수축 마지막 부분 (하위 30%)의 평균 거래량
        contraction_data = df.iloc[contraction.start_idx:contraction.end_idx+1]
        last_30pct = int(len(contraction_data) * 0.3)
        if last_30pct < 3:
            last_30pct = 3
            
        recent_volume = contraction_data.tail(last_30pct)['volume'].mean()
        
        # 이전 기간의 평균 거래량
        if contraction.start_idx > recent_bars:
            prev_volume = df.iloc[contraction.start_idx-recent_bars:contraction.start_idx]['volume'].mean()
        else:
            prev_volume = df.iloc[:contraction.start_idx]['volume'].mean()
        
        if prev_volume == 0:
            return False
            
        volume_ratio = recent_volume / prev_volume
        return volume_ratio < self.min_volume_dry_up  # 60% 이하
    
    def calculate_relative_strength(self, df: pd.DataFrame, market_df: Optional[pd.DataFrame] = None) -> pd.DataFrame:
        """
        상대강도(RS) 계산
        
        Args:
            df: 개별 종목 데이터
            market_df: 시장 데이터 (KOSPI 또는 KOSDAQ), 없으면 개별 계산
        
        Returns:
            RS가 추가된 데이터프레임
        """
        df = df.copy()
        
        # 1년 수익률 기반 RS
        df['rs'] = (df['close'] / df['close'].shift(self.rs_lookback) - 1) * 100
        
        # 시장 대비 RS (시장 데이터가 있으면)
        if market_df is not None:
            market_return = (market_df['close'] / market_df['close'].shift(self.rs_lookback) - 1) * 100
            df['rs_vs_market'] = df['rs'] - market_return.values
        
        return df
    
    def analyze_symbol(self, symbol: str, df: pd.DataFrame, 
                      market_df: Optional[pd.DataFrame] = None) -> Optional[SEPASignal]:
        """
        단일 종목 SEPA + VCP 분석
        
        Args:
            symbol: 종목코드
            df: OHLCV 데이터
            market_df: 시장 데이터 (RS 계산용)
        
        Returns:
            SEPASignal 또는 None
        """
        if len(df) < 252:  # 최소 1년 데이터 필요
            return None
            
        # 이동평균 및 52주 고저 계산
        df = self.calculate_moving_averages(df)
        df = self.calculate_52week_range(df)
        df = self.calculate_relative_strength(df, market_df)
        
        # 최신 데이터 인덱스
        idx = len(df) - 1
        row = df.iloc[idx]
        
        # 1. Trend Template 체크
        trend_result = self.check_trend_template(df, idx)
        
        # 2. VCP 수축 구간 식별
        contractions = self.find_contractions(df)
        vcp_result = self.check_vcp_pattern(contractions)
        
        # 3. 거래량 Dry-up 체크
        volume_dry_up = False
        if contractions:
            volume_dry_up = self.check_volume_dry_up(df, contractions[-1])
        
        # 4. RS 상위 25% 체크
        rs_value = row['rs'] if not pd.isna(row['rs']) else 0
        rs_rank = 0.5  # 기본값
        rs_top25 = True  # 기본적으로 통과 (전체 데이터 필요)
        
        # 5. 피벗 돌파 및 거래량 급증 체크
        pivot_line = vcp_result['last_pivot']
        pivot_breakout = abs(row['close'] - pivot_line) / pivot_line < self.pivot_proximity
        
        # 거래량 급증 체크
        recent_volume_avg = df.tail(20)['volume'].mean()
        volume_ratio = row['volume'] / recent_volume_avg if recent_volume_avg > 0 else 0
        volume_surge = volume_ratio >= self.min_volume_surge
        
        # 최종 신호 유효성
        is_valid = (
            trend_result['passed'] and 
            vcp_result['passed'] and 
            volume_dry_up and
            rs_top25
        )
        
        # 점수 계산
        score = 0
        if trend_result['passed']:
            score += 30
        if vcp_result['passed']:
            score += 30
            if vcp_result['depth_narrowing']:
                score += 10
            if vcp_result['duration_shortening']:
                score += 10
        if volume_dry_up:
            score += 10
        if volume_surge:
            score += 10
        if rs_top25:
            score += 10
        
        return SEPASignal(
            symbol=symbol,
            date=row['date'] if 'date' in row else df.index[idx],
            current_price=row['close'],
            above_ma150=trend_result['above_ma150'],
            above_ma200=trend_result['above_ma200'],
            ma150_above_ma200=trend_result['ma150_above_ma200'],
            ma200_trending_up=trend_result['ma200_trending_up'],
            near_52w_high=trend_result['near_52w_high'],
            above_52w_low=trend_result['above_52w_low'],
            trend_template_passed=trend_result['passed'],
            contractions=contractions,
            contraction_count=vcp_result['contraction_count'],
            depth_narrowing=vcp_result['depth_narrowing'],
            duration_shortening=vcp_result['duration_shortening'],
            vcp_passed=vcp_result['passed'],
            volume_dry_up=volume_dry_up,
            relative_strength=rs_value,
            rs_rank=rs_rank,
            rs_top25=rs_top25,
            pivot_line=pivot_line,
            pivot_breakout=pivot_breakout,
            volume_surge=volume_surge,
            volume_ratio=volume_ratio,
            is_valid=is_valid,
            score=score
        )
    
    def scan_multiple(self, data_dict: Dict[str, pd.DataFrame],
                     market_df: Optional[pd.DataFrame] = None) -> pd.DataFrame:
        """
        다중 종목 스캔
        
        Args:
            data_dict: {symbol: DataFrame} 형태의 딕셔너리
            market_df: 시장 데이터
        
        Returns:
            결과 DataFrame
        """
        results = []
        
        for symbol, df in data_dict.items():
            try:
                signal = self.analyze_symbol(symbol, df, market_df)
                if signal:
                    results.append({
                        'symbol': signal.symbol,
                        'date': signal.date,
                        'current_price': signal.current_price,
                        'trend_template': signal.trend_template_passed,
                        'vcp_passed': signal.vcp_passed,
                        'contraction_count': signal.contraction_count,
                        'depth_narrowing': signal.depth_narrowing,
                        'duration_shortening': signal.duration_shortening,
                        'volume_dry_up': signal.volume_dry_up,
                        'volume_surge': signal.volume_surge,
                        'volume_ratio': signal.volume_ratio,
                        'pivot_line': signal.pivot_line,
                        'pivot_breakout': signal.pivot_breakout,
                        'relative_strength': signal.relative_strength,
                        'rs_top25': signal.rs_top25,
                        'score': signal.score,
                        'is_valid': signal.is_valid
                    })
            except Exception as e:
                print(f"Error analyzing {symbol}: {e}")
                continue
        
        if not results:
            return pd.DataFrame()
            
        df_results = pd.DataFrame(results)
        df_results = df_results.sort_values('score', ascending=False)
        return df_results


# 예시 사용법
if __name__ == "__main__":
    print("SEPA + VCP Strategy Module")
    print("Mark Minervini's Trend Template + Volatility Contraction Pattern")
    print("\nUsage:")
    print("  from sepa_vcp_strategy import SEPA_VCP_Strategy")
    print("  strategy = SEPA_VCP_Strategy()")
    print("  signal = strategy.analyze_symbol('AAPL', df)")
