#!/usr/bin/env python3
"""
Japanese Classic Technical Analysis Scanner
===========================================
고전 일본 기법 기반 스캐너

1. 혼마 묘네히사 (Honma Munehisa) - 캔들차트
2. 사카타 5법 (Sakata 5 Methods)
   - 삼산 (三尊): Triple Top
   - 삼공 (三空): Three Gaps
   - 삼천 (三底): Triple Bottom
3. 일목균형표 (Ichimoku Kinko Hyo) - 호소다 고이치

Author: Gap-Up Scanner Project
Date: 2026-04-10
"""

import sqlite3
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Tuple
import json
import os
from dataclasses import dataclass
from enum import Enum


class PatternType(Enum):
    """패턴 타입"""
    TRIPLE_TOP = "triple_top"      # 삼산
    TRIPLE_BOTTOM = "triple_bottom"  # 삼천
    THREE_GAPS = "three_gaps"      # 삼공
    DOJI = "doji"                  # 도지
    ENGULFING = "engulfing"        # 인걸핑
    MORNING_STAR = "morning_star"  # 모닝스타
    EVENING_STAR = "evening_star"  # 이브닝스타
    HAMMER = "hammer"              # 함머
    SHOOTING_STAR = "shooting_star"  # 슈팅스타


@dataclass
class Candle:
    """캔들 데이터"""
    date: str
    open: float
    high: float
    low: float
    close: float
    volume: int
    
    @property
    def body(self) -> float:
        return abs(self.close - self.open)
    
    @property
    def upper_shadow(self) -> float:
        return self.high - max(self.open, self.close)
    
    @property
    def lower_shadow(self) -> float:
        return min(self.open, self.close) - self.low
    
    @property
    def range(self) -> float:
        return self.high - self.low
    
    @property
    def is_bullish(self) -> bool:
        return self.close > self.open
    
    @property
    def is_bearish(self) -> bool:
        return self.close < self.open
    
    @property
    def is_doji(self, threshold: float = 0.1) -> bool:
        return self.body <= self.range * threshold


class SakataFiveMethods:
    """
    사카타 5법 (酒田五法)
    ===================
    1. 삼산 (三尊) - Triple Top
    2. 삼공 (三空) - Three Gaps
    3. 삼천 (三底) - Triple Bottom
    """
    
    @staticmethod
    def detect_triple_top(df: pd.DataFrame, lookback: int = 20, tolerance: float = 0.02) -> bool:
        """
        삼산 (三尊) - Triple Top Pattern
        
        조건:
        - 3개의 유사한 고점 형성
        - 두 번째 고점이 가장 높음 (머리)
        - 첫/세 번째 고점이 어깨 (유사한 높이)
        """
        if len(df) < lookback:
            return False
        
        highs = df['high'].values
        
        # 최근 N일 고점들
        recent_highs = highs[-lookback:]
        
        # 고점 탐색 (local maxima)
        from scipy.signal import find_peaks
        peaks, _ = find_peaks(recent_highs, distance=3, prominence=recent_highs.std() * 0.5)
        
        if len(peaks) < 3:
            return False
        
        # 마지막 3개 고점 확인
        last_3_peaks = recent_highs[peaks[-3:]]
        
        # 패턴: 어깨-머리-어깨
        left_shoulder = last_3_peaks[0]
        head = last_3_peaks[1]
        right_shoulder = last_3_peaks[2]
        
        # 머리가 어깨보다 높아야 함
        if head <= max(left_shoulder, right_shoulder):
            return False
        
        # 어깨들이 유사한 높이 (±tolerance)
        shoulder_diff = abs(left_shoulder - right_shoulder) / left_shoulder
        if shoulder_diff > tolerance:
            return False
        
        return True
    
    @staticmethod
    def detect_triple_bottom(df: pd.DataFrame, lookback: int = 20, tolerance: float = 0.02) -> bool:
        """
        삼천 (三底) - Triple Bottom Pattern
        
        조건:
        - 3개의 유사한 저점 형성
        - 두 번째 저점이 가장 낮음 (머리)
        - 첫/세 번째 저점이 어깨 (유사한 높이)
        """
        if len(df) < lookback:
            return False
        
        lows = df['low'].values
        
        # 최근 N일 저점들
        recent_lows = lows[-lookback:]
        
        # 저점 탐색 (local minima)
        from scipy.signal import find_peaks
        troughs, _ = find_peaks(-recent_lows, distance=3, prominence=recent_lows.std() * 0.5)
        
        if len(troughs) < 3:
            return False
        
        # 마지막 3개 저점 확인
        last_3_troughs = recent_lows[troughs[-3:]]
        
        # 패턴: 어깨-머리-어깨
        left_shoulder = last_3_troughs[0]
        head = last_3_troughs[1]
        right_shoulder = last_3_troughs[2]
        
        # 머리가 어깨보다 낮아야 함
        if head >= min(left_shoulder, right_shoulder):
            return False
        
        # 어깨들이 유사한 높이 (±tolerance)
        shoulder_diff = abs(left_shoulder - right_shoulder) / left_shoulder
        if shoulder_diff > tolerance:
            return False
        
        return True
    
    @staticmethod
    def detect_three_gaps(df: pd.DataFrame) -> Dict:
        """
        삼공 (三空) - Three Gaps Pattern
        
        조건:
        - 상승/하락 추세 중 3개의 갭 연속 발생
        - 3번째 갭 = 추세 종료 신호
        """
        if len(df) < 10:
            return {'detected': False}
        
        gaps = []
        for i in range(1, len(df)):
            prev_close = df.iloc[i-1]['close']
            curr_open = df.iloc[i]['open']
            
            # 상승 갭
            if curr_open > prev_close * 1.01:
                gaps.append({'type': 'up', 'idx': i, 'size': (curr_open - prev_close) / prev_close})
            # 하락 갭
            elif curr_open < prev_close * 0.99:
                gaps.append({'type': 'down', 'idx': i, 'size': (prev_close - curr_open) / prev_close})
        
        # 연속 3개 갭 확인
        if len(gaps) >= 3:
            last_3 = gaps[-3:]
            if all(g['type'] == last_3[0]['type'] for g in last_3):
                return {
                    'detected': True,
                    'type': last_3[0]['type'],
                    'gaps': last_3,
                    'signal': 'reverse'  # 3번째 갭 = 추세 종료
                }
        
        return {'detected': False}


class IchimokuCloud:
    """
    일목균형표 (Ichimoku Kinko Hyo)
    ================================
    호소다 고이치 (細田護一) - 1930년대 개발
    
    구성요소:
    1. 전환선 (Tenkan-sen): 9일 고저평균
    2. 기준선 (Kijun-sen): 26일 고저평균
    3. 선행스팬1 (Senkou Span A): 전환선+기준선/2, 26일 선행
    4. 선행스팬2 (Senkou Span B): 52일 고저평균, 26일 선행
    5. 후행스팬 (Chikou Span): 종가, 26일 후행
    """
    
    def __init__(self, tenkan_period: int = 9, kijun_period: int = 26, 
                 senkou_b_period: int = 52, displacement: int = 26):
        self.tenkan_period = tenkan_period
        self.kijun_period = kijun_period
        self.senkou_b_period = senkou_b_period
        self.displacement = displacement
    
    def calculate(self, df: pd.DataFrame) -> pd.DataFrame:
        """일목균형표 계산"""
        data = df.copy()
        
        # 전환선 (Tenkan-sen): (9일 최고 + 9일 최저) / 2
        data['tenkan_sen'] = (data['high'].rolling(window=self.tenkan_period).max() + 
                              data['low'].rolling(window=self.tenkan_period).min()) / 2
        
        # 기준선 (Kijun-sen): (26일 최고 + 26일 최저) / 2
        data['kijun_sen'] = (data['high'].rolling(window=self.kijun_period).max() + 
                             data['low'].rolling(window=self.kijun_period).min()) / 2
        
        # 선행스팬1 (Senkou Span A): (전환선 + 기준선) / 2, 26일 선행
        data['senkou_span_a'] = ((data['tenkan_sen'] + data['kijun_sen']) / 2).shift(-self.displacement)
        
        # 선행스팬2 (Senkou Span B): (52일 최고 + 52일 최저) / 2, 26일 선행
        data['senkou_span_b'] = ((data['high'].rolling(window=self.senkou_b_period).max() + 
                                  data['low'].rolling(window=self.senkou_b_period).min()) / 2).shift(-self.displacement)
        
        # 후행스팬 (Chikou Span): 종가, 26일 후행
        data['chikou_span'] = data['close'].shift(self.displacement)
        
        # 구름 (Kumo)
        data['kumo_top'] = data[['senkou_span_a', 'senkou_span_b']].max(axis=1)
        data['kumo_bottom'] = data[['senkou_span_a', 'senkou_span_b']].min(axis=1)
        
        return data
    
    def generate_signals(self, df: pd.DataFrame) -> Dict:
        """일목균형표 매매 신호 생성"""
        data = self.calculate(df)
        
        if len(data) < 60:
            return {'error': 'Insufficient data'}
        
        latest = data.iloc[-1]
        prev = data.iloc[-2]
        
        signals = []
        
        # 1. 전환선/기준선 골든크로스
        if prev['tenkan_sen'] <= prev['kijun_sen'] and latest['tenkan_sen'] > latest['kijun_sen']:
            signals.append('TK_CROSS_BULLISH')
        
        # 2. 전환선/기준선 데드크로스
        elif prev['tenkan_sen'] >= prev['kijun_sen'] and latest['tenkan_sen'] < latest['kijun_sen']:
            signals.append('TK_CROSS_BEARISH')
        
        # 3. 가격이 구름 위로 돌파
        if prev['close'] <= prev['kumo_top'] and latest['close'] > latest['kumo_top']:
            signals.append('PRICE_ABOVE_CLOUD')
        
        # 4. 가격이 구름 아래로 돌파
        elif prev['close'] >= prev['kumo_bottom'] and latest['close'] < latest['kumo_bottom']:
            signals.append('PRICE_BELOW_CLOUD')
        
        # 5. 구름 전환 (구름 상승)
        if latest['senkou_span_a'] > latest['senkou_span_b']:
            signals.append('BULLISH_CLOUD')
        elif latest['senkou_span_a'] < latest['senkou_span_b']:
            signals.append('BEARISH_CLOUD')
        
        # 종합 점수
        bullish_count = sum(1 for s in signals if 'BULLISH' in s or 'ABOVE' in s)
        bearish_count = sum(1 for s in signals if 'BEARISH' in s or 'BELOW' in s)
        
        return {
            'signals': signals,
            'bullish_count': bullish_count,
            'bearish_count': bearish_count,
            'tenkan_sen': latest['tenkan_sen'],
            'kijun_sen': latest['kijun_sen'],
            'senkou_span_a': latest['senkou_span_a'],
            'senkou_span_b': latest['senkou_span_b'],
            'price_vs_cloud': 'above' if latest['close'] > latest['kumo_top'] else 
                             'below' if latest['close'] < latest['kumo_bottom'] else 'inside'
        }


class JapanesePatternScanner:
    """
    일본 고전 기법 통합 스캐너
    """
    
    def __init__(self, db_path: str = 'data/level1_prices.db'):
        self.db_path = db_path
        self.sakata = SakataFiveMethods()
        self.ichimoku = IchimokuCloud()
    
    def get_stock_data(self, code: str, days: int = 100) -> pd.DataFrame:
        """종목 데이터 조회"""
        conn = sqlite3.connect(self.db_path)
        
        query = """
        SELECT date, open, high, low, close, volume
        FROM price_data
        WHERE code = ? AND date <= date('now')
        ORDER BY date DESC
        LIMIT ?
        """
        
        df = pd.read_sql(query, conn, params=(code, days))
        conn.close()
        
        return df.sort_values('date').reset_index(drop=True)
    
    def scan_stock(self, code: str, name: str, date: str) -> Optional[Dict]:
        """단일 종목 스캔"""
        df = self.get_stock_data(code, days=100)
        
        if len(df) < 60:
            return None
        
        # 해당 날짜까지의 데이터
        df_up_to_date = df[df['date'] <= date]
        if len(df_up_to_date) < 60:
            return None
        
        signals = []
        
        # 1. 사카타 5법 패턴 탐지
        try:
            if SakataFiveMethods.detect_triple_top(df_up_to_date):
                signals.append('TRIPLE_TOP')
            
            if SakataFiveMethods.detect_triple_bottom(df_up_to_date):
                signals.append('TRIPLE_BOTTOM')
            
            gap_result = SakataFiveMethods.detect_three_gaps(df_up_to_date)
            if gap_result['detected']:
                signals.append(f"THREE_GAPS_{gap_result['type'].upper()}")
        except Exception as e:
            pass
        
        # 2. 일목균형표 신호
        ichimoku_signals = self.ichimoku.generate_signals(df_up_to_date)
        if 'signals' in ichimoku_signals:
            signals.extend(ichimoku_signals['signals'])
        
        if not signals:
            return None
        
        latest = df_up_to_date.iloc[-1]
        
        return {
            'code': code,
            'name': name,
            'date': date,
            'close': float(latest['close']),
            'signals': signals,
            'ichimoku': ichimoku_signals,
            'signal_count': len(signals),
        }
    
    def scan_market(self, date: str, min_signals: int = 2) -> List[Dict]:
        """전체 시장 스캔"""
        conn = sqlite3.connect(self.db_path)
        
        # 해당 날짜의 모든 종목
        query = """
        SELECT DISTINCT code, name
        FROM price_data
        WHERE date = ? AND close >= 2000
        """
        
        stocks = pd.read_sql(query, conn, params=(date,))
        conn.close()
        
        print(f"🔍 {date} 스캔: {len(stocks)} 종목")
        
        results = []
        for _, stock in stocks.iterrows():
            result = self.scan_stock(stock['code'], stock['name'], date)
            if result and result['signal_count'] >= min_signals:
                results.append(result)
        
        # 신호 개수 순 정렬
        results = sorted(results, key=lambda x: x['signal_count'], reverse=True)
        
        print(f"  ✅ {len(results)} 종목 발견 (신호 {min_signals}개 이상)")
        return results


if __name__ == '__main__':
    # 테스트
    scanner = JapanesePatternScanner()
    
    # 삼성전자 테스트
    result = scanner.scan_stock('005930', '삼성전자', '2026-04-09')
    if result:
        print(f"\n📊 삼성전자 신호:")
        print(f"  신호: {result['signals']}")
        print(f"  일목균형표: {result['ichimoku']}")
    else:
        print("\n❌ 삼성전자: 신호 없음")
