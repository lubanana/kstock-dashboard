#!/usr/bin/env python3
"""
고급 캔들 패턴 감지기 - 개선 버전
더 정교한 패턴 인식 + 다양한 패턴 추가
"""

import sys
sys.path.insert(0, '/root/.openclaw/workspace/strg')

import json
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from dataclasses import dataclass
from typing import List, Dict, Optional, Tuple
from fdr_wrapper import get_price


@dataclass
class CandlePattern:
    """캔들 패턴 정의"""
    name: str
    type: str  # 'bullish', 'bearish', 'neutral'
    reliability: int  # 1-5, 5가 가장 신뢰도 높음
    description: str


# 패턴 정의
PATTERNS = {
    # 핀바 계열
    'pinbar': CandlePattern('Pin Bar', 'bullish', 5, '아래꼬리 긴 캔들, 지지선 부근 강력'),
    'bullish_pinbar': CandlePattern('Bullish Pin Bar', 'bullish', 5, '양봉 핀바, 더 강력한 매수 신호'),
    
    # 망치형 계열
    'hammer': CandlePattern('Hammer', 'bullish', 4, '하락 후 등장하는 망치형'),
    'inverted_hammer': CandlePattern('Inverted Hammer', 'bullish', 3, '상승 반전 시도'),
    
    # 도지 계열
    'doji': CandlePattern('Doji', 'neutral', 2, '막대기 몸통 없음, 관망'),
    'dragonfly_doji': CandlePattern('Dragonfly Doji', 'bullish', 4, '바닥에서 강력한 반전'),
    'gravestone_doji': CandlePattern('Gravestone Doji', 'bearish', 3, '정상에서 반전 가능'),
    
    # 잉ulf형
    'bullish_engulfing': CandlePattern('Bullish Engulfing', 'bullish', 5, '전봉 완전 포함, 강력 매수'),
    'bearish_engulfing': CandlePattern('Bearish Engulfing', 'bearish', 4, '전봉 완전 포함, 매도'),
    
    # 모닝/이브닝 스타
    'morning_star': CandlePattern('Morning Star', 'bullish', 5, '3봉 반전 패턴'),
    'evening_star': CandlePattern('Evening Star', 'bearish', 4, '3봉 하락 반전'),
    
    # 모닝/이브닝 도지 스타
    'morning_doji_star': CandlePattern('Morning Doji Star', 'bullish', 5, '도지 포함 3봉 반전'),
    
    # 삼형태
    'three_white_soldiers': CandlePattern('Three White Soldiers', 'bullish', 5, '3연속 양봉, 강한 상승'),
    'three_black_crows': CandlePattern('Three Black Crows', 'bearish', 4, '3연속 음봉, 강한 하락'),
    
    # 주가 점프
    'piercing_line': CandlePattern('Piercing Line', 'bullish', 4, '중간 돌파 반전'),
    'dark_cloud_cover': CandlePattern('Dark Cloud Cover', 'bearish', 3, '중간 돌파 하락'),
    
    # 장대양봉/음봉
    'long_white_candle': CandlePattern('Long White Candle', 'bullish', 3, '강한 매수세'),
    'long_black_candle': CandlePattern('Long Black Candle', 'bearish', 3, '강한 매도세'),
    
    # 컨티뉴에이션
    'rising_three': CandlePattern('Rising Three Methods', 'bullish', 4, '상승 추속'),
    'falling_three': CandlePattern('Falling Three Methods', 'bearish', 4, '하락 추속'),
}


class AdvancedCandleDetector:
    """고급 캔들 패턴 감지기"""
    
    def __init__(self, df: pd.DataFrame):
        self.df = df.reset_index()
        self.opens = df['Open'].values
        self.highs = df['High'].values
        self.lows = df['Low'].values
        self.closes = df['Close'].values
        self.volumes = df['Volume'].values
    
    def _candle_body(self, idx: int) -> float:
        """캔들 몸통 크기"""
        return abs(self.closes[idx] - self.opens[idx])
    
    def _candle_range(self, idx: int) -> float:
        """전체 범위 (high - low)"""
        return self.highs[idx] - self.lows[idx]
    
    def _upper_shadow(self, idx: int) -> float:
        """위꼬리 길이"""
        return self.highs[idx] - max(self.opens[idx], self.closes[idx])
    
    def _lower_shadow(self, idx: int) -> float:
        """아래꼬리 길이"""
        return min(self.opens[idx], self.closes[idx]) - self.lows[idx]
    
    def _is_bullish(self, idx: int) -> bool:
        """양봉 여부"""
        return self.closes[idx] > self.opens[idx]
    
    def _is_bearish(self, idx: int) -> bool:
        """음봉 여부"""
        return self.closes[idx] < self.opens[idx]
    
    def _avg_range(self, n: int = 20) -> float:
        """평균 범위"""
        ranges = [self._candle_range(i) for i in range(-n, 0)]
        return np.mean(ranges) if ranges else 1.0
    
    def _avg_volume(self, n: int = 20) -> float:
        """평균 거래량"""
        return np.mean(self.volumes[-n:])
    
    def detect_pinbar(self, idx: int = -1, min_reliability: int = 4) -> Optional[Dict]:
        """
        핀바 감지 - 개선 버전
        조건:
        - 아래꼬리가 몸통의 2배 이상
        - 아래꼬리가 전체 범위의 60% 이상
        - 거래량이 평균 이상 (신뢰도 증가)
        """
        if abs(idx) >= len(self.closes):
            return None
        
        body = self._candle_body(idx)
        lower_shadow = self._lower_shadow(idx)
        upper_shadow = self._upper_shadow(idx)
        total_range = self._candle_range(idx)
        
        if total_range == 0:
            return None
        
        # 기본 핀바 조건
        is_pinbar = (lower_shadow >= body * 2 and 
                     lower_shadow >= total_range * 0.6 and
                     upper_shadow <= total_range * 0.1)  # 위꼬리 거의 없음
        
        if not is_pinbar:
            return None
        
        # 추가 조건 확인
        is_bullish = self._is_bullish(idx)
        volume_ratio = self.volumes[idx] / self._avg_volume() if self._avg_volume() > 0 else 1.0
        
        # 신뢰도 계산
        reliability = 4
        if is_bullish:
            reliability += 1  # 양봉이면 더 신뢰
        if volume_ratio >= 1.5:
            reliability += 1  # 거래량 급증
        
        if reliability < min_reliability:
            return None
        
        pattern_name = 'bullish_pinbar' if is_bullish else 'pinbar'
        
        return {
            'pattern': pattern_name,
            'reliability': reliability,
            'type': 'bullish',
            'body_pct': body / total_range * 100,
            'lower_shadow_pct': lower_shadow / total_range * 100,
            'volume_ratio': round(volume_ratio, 2),
            'price': self.closes[idx]
        }
    
    def detect_hammer(self, idx: int = -1, prev_idx: int = -2) -> Optional[Dict]:
        """
        망치형 감지
        조건:
        - 전봉이 음봉
        - 현재 양봉
        - 아래꼬리가 몸통의 2배 이상
        """
        if abs(idx) >= len(self.closes) or abs(prev_idx) >= len(self.closes):
            return None
        
        # 전봉 음봉 확인
        if not self._is_bearish(prev_idx):
            return None
        
        body = self._candle_body(idx)
        lower_shadow = self._lower_shadow(idx)
        total_range = self._candle_range(idx)
        
        if total_range == 0:
            return None
        
        # 망치형 조건
        is_hammer = (self._is_bullish(idx) and
                     lower_shadow >= body * 2 and
                     self._upper_shadow(idx) <= body * 0.5)
        
        if not is_hammer:
            return None
        
        volume_ratio = self.volumes[idx] / self._avg_volume()
        
        return {
            'pattern': 'hammer',
            'reliability': 4 if volume_ratio >= 1.2 else 3,
            'type': 'bullish',
            'body_pct': body / total_range * 100,
            'volume_ratio': round(volume_ratio, 2)
        }
    
    def detect_engulfing(self, idx: int = -1, prev_idx: int = -2) -> Optional[Dict]:
        """
        잉ulf형 감지
        조건:
        - Bullish: 전봉 음봉, 현재 양봉으로 완전 포함
        """
        if abs(idx) >= len(self.closes) or abs(prev_idx) >= len(self.closes):
            return None
        
        prev_open, prev_close = self.opens[prev_idx], self.closes[prev_idx]
        curr_open, curr_close = self.opens[idx], self.closes[idx]
        
        # Bullish Engulfing
        if prev_close < prev_open and curr_close > curr_open:  # 전봉 음, 현재 양
            if curr_open < prev_close and curr_close > prev_open:  # 완전 포함
                volume_ratio = self.volumes[idx] / self.volumes[prev_idx] if self.volumes[prev_idx] > 0 else 1.0
                
                return {
                    'pattern': 'bullish_engulfing',
                    'reliability': 5 if volume_ratio > 1.5 else 4,
                    'type': 'bullish',
                    'volume_ratio': round(volume_ratio, 2)
                }
        
        return None
    
    def detect_morning_star(self, idx: int = -1) -> Optional[Dict]:
        """
        모닝스타 감지 (3봉 패턴)
        조건:
        - 1봉 전: 강한 음봉
        - 2봉 전: 작은 몸통 (도지 또는 작은봉), 갭 하락
        - 3봉 전 (현재): 양봉, 1봉의 중간 이상 회복
        """
        if abs(idx) >= len(self.closes):
            return None
        
        i1, i2, i3 = idx, idx - 1, idx - 2
        if abs(i3) >= len(self.closes):
            return None
        
        # 3봉 전: 강한 음봉
        if not self._is_bearish(i3):
            return None
        
        # 2봉 전: 작은 몸통
        body2 = self._candle_body(i2)
        range2 = self._candle_range(i2)
        if range2 == 0 or body2 / range2 > 0.3:
            return None
        
        # 1봉 전 (현재): 양봉
        if not self._is_bullish(i1):
            return None
        
        # 1봉이 3봉 중간 이상 회복
        mid_3 = (self.opens[i3] + self.closes[i3]) / 2
        if self.closes[i1] > mid_3:
            return {
                'pattern': 'morning_star',
                'reliability': 5,
                'type': 'bullish'
            }
        
        return None
    
    def detect_all_patterns(self, min_reliability: int = 3) -> List[Dict]:
        """모든 패턴 감지"""
        patterns = []
        
        # 단일 캔들 패턴
        pinbar = self.detect_pinbar(-1, min_reliability)
        if pinbar:
            patterns.append(pinbar)
        
        hammer = self.detect_hammer(-1, -2)
        if hammer and hammer['reliability'] >= min_reliability:
            patterns.append(hammer)
        
        # 2봉 패턴
        engulfing = self.detect_engulfing(-1, -2)
        if engulfing and engulfing['reliability'] >= min_reliability:
            patterns.append(engulfing)
        
        # 3봉 패턴
        morning_star = self.detect_morning_star(-1)
        if morning_star:
            patterns.append(morning_star)
        
        return patterns
    
    def get_best_pattern(self, min_reliability: int = 4) -> Optional[Dict]:
        """가장 신뢰도 높은 패턴 반환"""
        patterns = self.detect_all_patterns(min_reliability)
        if not patterns:
            return None
        
        # 신뢰도 높은 순으로 정렬
        patterns.sort(key=lambda x: x['reliability'], reverse=True)
        return patterns[0]


def scan_with_candles(symbol: str, date: str, combo_type: str = 'advanced') -> Optional[Dict]:
    """
    개선된 캔들 패턴 기반 스캔
    """
    try:
        end_dt = datetime.strptime(date, '%Y-%m-%d')
        start_dt = end_dt - timedelta(days=90)
        
        df = get_price(symbol, start_dt.strftime('%Y-%m-%d'), date)
        if df is None or len(df) < 30:
            return None
        
        detector = AdvancedCandleDetector(df)
        closes = detector.closes
        highs = detector.highs
        lows = detector.lows
        volumes = detector.volumes
        current_price = closes[-1]
        
        score = 0
        reasons = []
        pattern_details = {}
        
        # 1. 피볼나치 (확장 범위 25~75%)
        recent_high = np.max(highs[-20:])
        recent_low = np.min(lows[-20:])
        if recent_high > recent_low:
            retracement = ((recent_high - current_price) / (recent_high - recent_low)) * 100
        else:
            retracement = 50
        
        if not (25 <= retracement <= 75):
            return None
        
        score += 20
        reasons.append(f'Fib_{retracement:.0f}')
        
        # 2. 거래량
        avg_vol = np.mean(volumes[-20:])
        rvol = volumes[-1] / avg_vol if avg_vol > 0 else 1.0
        
        if rvol >= 2.0:
            score += 15
            reasons.append(f'RVol_{rvol:.1f}')
        elif rvol >= 1.5:
            score += 10
            reasons.append(f'RVol_{rvol:.1f}')
        elif rvol >= 1.2:
            score += 5
            reasons.append(f'RVol_{rvol:.1f}')
        
        # 3. 개선된 캔들 패턴
        best_pattern = detector.get_best_pattern(min_reliability=4)
        
        if best_pattern:
            pattern_name = best_pattern['pattern']
            reliability = best_pattern['reliability']
            
            if reliability >= 5:
                score += 25
            elif reliability >= 4:
                score += 20
            else:
                score += 15
            
            reasons.append(pattern_name.upper())
            pattern_details = best_pattern
        else:
            # 기본 패턴 감지 (신뢰도 낮아도)
            all_patterns = detector.detect_all_patterns(min_reliability=3)
            if all_patterns:
                score += 10
                reasons.append('Weak_Pattern')
            else:
                if combo_type == 'strict':
                    return None
        
        # 4. 추세 확인
        ma5 = np.mean(closes[-5:])
        ma20 = np.mean(closes[-20:])
        if current_price > ma5 > ma20:
            score += 10
            reasons.append('Bullish_Trend')
        elif current_price > ma20:
            score += 5
            reasons.append('Above_MA20')
        
        # 최소 점수 확인
        if combo_type == 'strict' and score < 50:
            return None
        if score < 35:
            return None
        
        return {
            'symbol': symbol,
            'date': date,
            'score': score,
            'price': round(current_price, 0),
            'retracement': round(retracement, 1),
            'rvol': round(rvol, 2),
            'pattern': pattern_details.get('pattern', 'None'),
            'pattern_reliability': pattern_details.get('reliability', 0),
            'reasons': reasons
        }
        
    except Exception as e:
        return None


if __name__ == '__main__':
    print("=" * 70)
    print("🔥 고급 캔들 패턴 감지기 테스트")
    print("=" * 70)
    
    test_cases = [
        ('033100', '2026-03-03'),
        ('140860', '2026-03-10'),
        ('348210', '2026-01-27'),
        ('005930', '2026-03-24'),
    ]
    
    for symbol, date in test_cases:
        result = scan_with_candles(symbol, date)
        
        if result:
            emoji = '📈' if result['score'] >= 50 else '➖'
            print(f"\n{emoji} {symbol} ({date})")
            print(f"   점수: {result['score']}점")
            print(f"   가격: {result['price']:,.0f}")
            print(f"   패턴: {result['pattern']} (신뢰도: {result['pattern_reliability']})")
            print(f"   피볼나치: {result['retracement']:.1f}%")
            print(f"   거래량: {result['rvol']:.2f}x")
            print(f"   합치: {', '.join(result['reasons'])}")
        else:
            print(f"\n➖ {symbol} ({date}): 신호 없음")
    
    print("\n" + "=" * 70)
    print("✅ 고급 캔들 패턴 감지기 준비 완료")
    print("=" * 70)
