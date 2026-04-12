#!/usr/bin/env python3
"""
2604 V7 + Japanese Strategy Integration Module
===============================================
2604 통합 스캐너에 일본 전략(일목균형표) 통합 및 추천 보유일수 계산

Integration Points:
1. Ichimoku Cloud signals (TK_CROSS, Price vs Cloud)
2. Recommended holding period calculation based on:
   - Tenkan-sen/Kijun-sen distance (momentum)
   - Cloud thickness (trend strength)
   - Historical volatility
   - Strategy type (short-term/medium-term)

Scoring Update:
- 기존 100점 → 120점 (Japanese +20점)
- 거래량 (25점), 기술적 (20점), 피볼나치 (20점)
- 시장맥락 (15점), 모멘텀 (10점), 일목균형 (20점)
- 진입 조건: 90점+

Holding Period Recommendation:
- 단기 (1-3일): TK_CROSS + 강한 모멘텀
- 중기 (5-10일): 구름 돌파 + 안정적 추세
- 장기 (10-20일): 강한 구름 지지 + 꾸준한 상승
"""

import pandas as pd
import numpy as np
from typing import Dict, Optional, Tuple
from dataclasses import dataclass
from enum import Enum


class HoldingPeriod(Enum):
    """추천 보유 기간"""
    DAY_TRADE = (1, 1, "당일 청산")
    SHORT = (2, 3, "단기 (2-3일)")
    MEDIUM = (5, 10, "중기 (5-10일)")
    LONG = (10, 20, "장기 (10-20일)")
    TREND_FOLLOW = (20, 60, "추세 추종 (20-60일)")
    
    def __init__(self, min_days: int, max_days: int, description: str):
        self.min_days = min_days
        self.max_days = max_days
        self.description = description


@dataclass
class JapaneseSignal:
    """일본 전략 신호"""
    tk_cross_bullish: bool
    tk_cross_bearish: bool
    price_above_cloud: bool
    price_below_cloud: bool
    bullish_cloud: bool
    tenkan_sen: float
    kijun_sen: float
    cloud_thickness: float
    tenkan_kijun_distance: float  # 전환선-기준선 거리 (모멘텀)
    
    @property
    def score(self) -> int:
        """일목균형표 점수 (0-20점)"""
        score = 0
        
        # TK_CROSS 골든크로스: 8점
        if self.tk_cross_bullish:
            score += 8
        
        # 구름 위: 5점
        if self.price_above_cloud:
            score += 5
        
        # 상승 구름: 4점
        if self.bullish_cloud:
            score += 4
        
        # 전환선 > 기준선 (기울기): 3점
        if self.tenkan_sen > self.kijun_sen:
            score += 3
        
        return min(score, 20)


class IchimokuCalculator:
    """일목균형표 계산기"""
    
    def __init__(self, tenkan_period: int = 9, kijun_period: int = 26,
                 senkou_b_period: int = 52, displacement: int = 26):
        self.tenkan_period = tenkan_period
        self.kijun_period = kijun_period
        self.senkou_b_period = senkou_b_period
        self.displacement = displacement
    
    def calculate(self, df: pd.DataFrame) -> pd.DataFrame:
        """일목균형표 지표 계산"""
        data = df.copy()
        
        # 전환선 (Tenkan-sen): (9일 최고 + 9일 최저) / 2
        high_9 = data['high'].rolling(window=self.tenkan_period).max()
        low_9 = data['low'].rolling(window=self.tenkan_period).min()
        data['tenkan_sen'] = (high_9 + low_9) / 2
        
        # 기준선 (Kijun-sen): (26일 최고 + 26일 최저) / 2
        high_26 = data['high'].rolling(window=self.kijun_period).max()
        low_26 = data['low'].rolling(window=self.kijun_period).min()
        data['kijun_sen'] = (high_26 + low_26) / 2
        
        # 선행스팬1 (Senkou Span A)
        data['senkou_span_a'] = ((data['tenkan_sen'] + data['kijun_sen']) / 2).shift(-self.displacement)
        
        # 선행스팬2 (Senkou Span B)
        high_52 = data['high'].rolling(window=self.senkou_b_period).max()
        low_52 = data['low'].rolling(window=self.senkou_b_period).min()
        data['senkou_span_b'] = ((high_52 + low_52) / 2).shift(-self.displacement)
        
        # 후행스팬 (Chikou Span)
        data['chikou_span'] = data['close'].shift(self.displacement)
        
        # 구름 두께
        data['cloud_top'] = data[['senkou_span_a', 'senkou_span_b']].max(axis=1)
        data['cloud_bottom'] = data[['senkou_span_a', 'senkou_span_b']].min(axis=1)
        data['cloud_thickness'] = data['cloud_top'] - data['cloud_bottom']
        data['cloud_thickness_pct'] = data['cloud_thickness'] / data['close'] * 100
        
        return data
    
    def generate_signal(self, df: pd.DataFrame) -> JapaneseSignal:
        """일목균형표 신호 생성"""
        if len(df) < 60:
            return JapaneseSignal(False, False, False, False, False, 0, 0, 0, 0)
        
        latest = df.iloc[-1]
        prev = df.iloc[-2]
        
        # TK_CROSS 감지
        tk_cross_bullish = (prev['tenkan_sen'] <= prev['kijun_sen'] and 
                           latest['tenkan_sen'] > latest['kijun_sen'])
        tk_cross_bearish = (prev['tenkan_sen'] >= prev['kijun_sen'] and 
                           latest['tenkan_sen'] < latest['kijun_sen'])
        
        # 구름 위치
        price_above_cloud = latest['close'] > latest['cloud_top']
        price_below_cloud = latest['close'] < latest['cloud_bottom']
        
        # 구름 방향
        bullish_cloud = latest['senkou_span_a'] > latest['senkou_span_b']
        
        # 모멘텀 지표
        tenkan_kijun_distance = abs(latest['tenkan_sen'] - latest['kijun_sen']) / latest['close'] * 100
        
        return JapaneseSignal(
            tk_cross_bullish=tk_cross_bullish,
            tk_cross_bearish=tk_cross_bearish,
            price_above_cloud=price_above_cloud,
            price_below_cloud=price_below_cloud,
            bullish_cloud=bullish_cloud,
            tenkan_sen=latest['tenkan_sen'],
            kijun_sen=latest['kijun_sen'],
            cloud_thickness=latest['cloud_thickness_pct'],
            tenkan_kijun_distance=tenkan_kijun_distance
        )


class HoldingPeriodCalculator:
    """추천 보유일수 계산기"""
    
    def __init__(self):
        self.ichimoku = IchimokuCalculator()
    
    def calculate(self, df: pd.DataFrame, signal_score: int, 
                  volatility: float, adx: float) -> Tuple[HoldingPeriod, Dict]:
        """
        추천 보유일수 계산
        
        Parameters:
        -----------
        df : DataFrame with price data
        signal_score : 종합 점수 (0-120)
        volatility : 변동성 (ATR %)
        adx : 추세 강도 (0-100)
        
        Returns:
        --------
        (HoldingPeriod, details)
        """
        # 일목균형표 계산
        ichimoku_df = self.ichimoku.calculate(df)
        j_signal = self.ichimoku.generate_signal(ichimoku_df)
        
        # 계산 요소들
        factors = {
            'tk_cross': j_signal.tk_cross_bullish,
            'cloud_position': 'above' if j_signal.price_above_cloud else 'inside',
            'cloud_thickness': j_signal.cloud_thickness,
            'tenkan_kijun_dist': j_signal.tenkan_kijun_distance,
            'signal_score': signal_score,
            'volatility': volatility,
            'adx': adx
        }
        
        # 보유일수 결정 로직
        
        # 1. 고점수 + TK_CROSS + 높은 ADX = 단기 (2-3일)
        if signal_score >= 100 and j_signal.tk_cross_bullish and adx >= 30:
            return HoldingPeriod.SHORT, factors
        
        # 2. 당일 청산 (Fire Ant 스타일)
        if signal_score >= 90 and volatility >= 5 and j_signal.tenkan_kijun_distance >= 3:
            return HoldingPeriod.DAY_TRADE, factors
        
        # 3. 구름 돌파 + 안정적 추세 = 중기 (5-10일)
        if j_signal.price_above_cloud and adx >= 25 and volatility <= 3:
            return HoldingPeriod.MEDIUM, factors
        
        # 4. 강한 구름 + 낮은 변동성 = 장기 (10-20일)
        if j_signal.price_above_cloud and j_signal.cloud_thickness >= 5 and adx >= 20:
            return HoldingPeriod.LONG, factors
        
        # 5. 기본값: 중기
        return HoldingPeriod.MEDIUM, factors
    
    def get_exit_strategy(self, holding_period: HoldingPeriod, 
                         j_signal: JapaneseSignal) -> Dict:
        """
        보유 기간별 청산 전략
        
        Returns:
        --------
        {
            'primary_exit': 'TP2' or 'trailing_stop' or 'time_exit',
            'time_stop': days,
            'trail_activation': pct,
            'notes': str
        }
        """
        strategies = {
            HoldingPeriod.DAY_TRADE: {
                'primary_exit': 'time_exit',
                'time_stop': 1,
                'trail_activation': None,
                'notes': '장 마감 전 청산'
            },
            HoldingPeriod.SHORT: {
                'primary_exit': 'TP2',
                'time_stop': 3,
                'trail_activation': 5.0,
                'notes': 'TP2 도달 후 트레일링 스탑'
            },
            HoldingPeriod.MEDIUM: {
                'primary_exit': 'trailing_stop',
                'time_stop': 10,
                'trail_activation': 10.0,
                'notes': '10% 수익 시 트레일링 시작'
            },
            HoldingPeriod.LONG: {
                'primary_exit': 'trailing_stop',
                'time_stop': 20,
                'trail_activation': 15.0,
                'notes': '15% 수익 시 트레일링 시작, 기준선 기반 스탑'
            },
            HoldingPeriod.TREND_FOLLOW: {
                'primary_exit': 'trailing_stop',
                'time_stop': 60,
                'trail_activation': 20.0,
                'notes': '기준선/Kijun-sen 이탈 시 청산'
            }
        }
        
        return strategies.get(holding_period, strategies[HoldingPeriod.MEDIUM])


# 통합 모듈 테스트
if __name__ == '__main__':
    import sqlite3
    
    print("=" * 60)
    print("2604 + Japanese Strategy Integration Test")
    print("=" * 60)
    
    # 샘플 데이터로 테스트
    db_path = 'data/level1_prices.db'
    conn = sqlite3.connect(db_path)
    
    # 비트컴퓨터 데이터 (4월 10일 선정 종목)
    query = """
    SELECT date, open, high, low, close, volume
    FROM price_data
    WHERE code = '032850'
    ORDER BY date DESC
    LIMIT 100
    """
    
    df = pd.read_sql(query, conn)
    df = df.sort_values('date').reset_index(drop=True)
    conn.close()
    
    print(f"\n테스트 종목: 비트컴퓨터 (032850)")
    print(f"데이터 기간: {df['date'].min()} ~ {df['date'].max()}")
    
    # 일목균형표 계산
    ichimoku = IchimokuCalculator()
    df_ichimoku = ichimoku.calculate(df)
    signal = ichimoku.generate_signal(df_ichimoku)
    
    print(f"\n📊 일목균형표 분석")
    print(f"   전환선 (Tenkan): {signal.tenkan_sen:,.0f}")
    print(f"   기준선 (Kijun): {signal.kijun_sen:,.0f}")
    print(f"   구름 두께: {signal.cloud_thickness:.2f}%")
    print(f"   TK_CROSS: {'✅ 골든' if signal.tk_cross_bullish else '❌ 없음'}")
    print(f"   구름 위치: {'위' if signal.price_above_cloud else '남'}")
    print(f"   일본전략 점수: {signal.score}/20점")
    
    # 보유일수 계산
    calc = HoldingPeriodCalculator()
    
    # ATR 계산 (간단)
    df['tr'] = np.maximum(
        df['high'] - df['low'],
        np.maximum(
            abs(df['high'] - df['close'].shift(1)),
            abs(df['low'] - df['close'].shift(1))
        )
    )
    atr = df['tr'].rolling(14).mean().iloc[-1]
    volatility = atr / df['close'].iloc[-1] * 100
    
    # ADX (간단 근사치)
    adx = 27  # 테스트용
    
    holding, factors = calc.calculate(df, signal_score=82, 
                                      volatility=volatility, adx=adx)
    
    print(f"\n📅 추천 보유 전략")
    print(f"   보유 기간: {holding.description}")
    print(f"   최소: {holding.min_days}일 / 최대: {holding.max_days}일")
    
    exit_strategy = calc.get_exit_strategy(holding, signal)
    print(f"\n🎯 청산 전략")
    print(f"   주 청산: {exit_strategy['primary_exit']}")
    print(f"   시간 스탑: {exit_strategy['time_stop']}일")
    print(f"   트레일링 활성화: {exit_strategy['trail_activation']}%")
    print(f"   📝 {exit_strategy['notes']}")
    
    print("\n" + "=" * 60)
    print("통합 테스트 완료!")
    print("=" * 60)
