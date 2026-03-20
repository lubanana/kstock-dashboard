#!/usr/bin/env python3
"""
M10 Scanner - M-Strategy Real-time Scanner
M-Strategy 기반 실시간 종목 스캐너

Features:
- AI Prediction 기반 선별 (Primary 60%+ / Meta 65%+)
- 기술적 필터: RSI, Volume, ADX
- Fibonacci 목표가/손절가 계산
- 시장조사 리포트 생성
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Tuple
import json
import os
import warnings
warnings.filterwarnings('ignore')

import sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from fdr_wrapper import FDRWrapper, get_price


def normalize_columns(df: pd.DataFrame) -> pd.DataFrame:
    """컬럼명 표준화"""
    df = df.copy()
    column_map = {}
    for col in df.columns:
        col_cap = col.capitalize()
        if col_cap in ['Open', 'High', 'Low', 'Close', 'Volume', 'Date']:
            column_map[col] = col_cap
    df.rename(columns=column_map, inplace=True)
    return df


def calculate_rsi(prices: pd.Series, period: int = 14) -> pd.Series:
    """RSI 계산"""
    delta = prices.diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
    rs = gain / loss
    rsi = 100 - (100 / (1 + rs))
    return rsi


def calculate_atr(df: pd.DataFrame, period: int = 14) -> pd.Series:
    """ATR 계산"""
    high = df['High']
    low = df['Low']
    close = df['Close']
    
    tr1 = high - low
    tr2 = abs(high - close.shift(1))
    tr3 = abs(low - close.shift(1))
    
    tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
    atr = tr.rolling(window=period, min_periods=1).mean()
    
    return atr


def calculate_adx(df: pd.DataFrame, period: int = 14) -> pd.Series:
    """ADX 계산"""
    high = df['High']
    low = df['Low']
    close = df['Close']
    
    plus_dm = high.diff()
    minus_dm = low.diff().abs()
    
    plus_dm[plus_dm < 0] = 0
    minus_dm[minus_dm < 0] = 0
    
    tr = pd.concat([
        high - low,
        abs(high - close.shift(1)),
        abs(low - close.shift(1))
    ], axis=1).max(axis=1)
    
    atr = tr.rolling(window=period).mean()
    
    plus_di = 100 * (plus_dm.rolling(window=period).mean() / atr)
    minus_di = 100 * (minus_dm.rolling(window=period).mean() / atr)
    
    dx = 100 * abs(plus_di - minus_di) / (plus_di + minus_di)
    adx = dx.rolling(window=period).mean()
    
    return adx


def calculate_fibonacci_levels(df: pd.DataFrame, lookback: int = 20) -> Dict[str, float]:
    """Fibonacci 레벨 계산"""
    recent_high = df['High'].rolling(window=lookback, min_periods=5).max().iloc[-1]
    recent_low = df['Low'].rolling(window=lookback, min_periods=5).min().iloc[-1]
    
    price_range = recent_high - recent_low
    current_close = df['Close'].iloc[-1]
    
    # Extension levels for targets
    fib_1382 = recent_high + price_range * 0.382
    fib_1618 = recent_high + price_range * 0.618
    fib_2000 = recent_high + price_range * 1.0
    
    return {
        'high': recent_high,
        'low': recent_low,
        'fib_1382': fib_1382,
        'fib_1618': fib_1618,
        'fib_2000': fib_2000,
        'current': current_close
    }


def ai_predict_direction(df: pd.DataFrame) -> Tuple[float, float]:
    """
    AI 방향성 예측 (간단한 규칙 기반)
    Returns: (primary_confidence, meta_confidence)
    """
    # Primary 모델: 추세 + 모멘텀
    ma20 = df['Close'].rolling(20).mean().iloc[-1]
    ma60 = df['Close'].rolling(60).mean().iloc[-1]
    current = df['Close'].iloc[-1]
    
    rsi = calculate_rsi(df['Close'], 14).iloc[-1]
    
    # 추세 점수
    trend_score = 0
    if current > ma20 > ma60:
        trend_score = 70
    elif current > ma20:
        trend_score = 60
    elif current > ma60:
        trend_score = 50
    else:
        trend_score = 40
    
    # 모멘텀 점수
    momentum_score = 0
    if 50 <= rsi <= 70:
        momentum_score = 10
    elif rsi > 70:
        momentum_score = 5
    elif rsi < 30:
        momentum_score = -5
    
    primary_confidence = min(99, trend_score + momentum_score)
    
    # Meta 모델: 거래량 + 변동성
    volume_ma = df['Volume'].rolling(20).mean().iloc[-1]
    current_volume = df['Volume'].iloc[-1]
    volume_ratio = current_volume / volume_ma if volume_ma > 0 else 1.0
    
    meta_score = 65
    if volume_ratio > 1.5:
        meta_score += 10
    elif volume_ratio > 1.0:
        meta_score += 5
    
    # 변동성 체크
    atr = calculate_atr(df, 14).iloc[-1]
    atr_ratio = atr / current
    if atr_ratio < 0.03:  # 낮은 변동성
        meta_score += 5
    
    meta_confidence = min(99, meta_score)
    
    return primary_confidence, meta_confidence


class M10Scanner:
    """
    M10 Scanner - M-Strategy 기반 실시간 스캐너
    """
    
    def __init__(self,
                 primary_threshold: float = 60.0,
                 meta_threshold: float = 65.0,
                 rsi_min: float = 35.0,
                 rsi_max: float = 75.0,
                 volume_threshold: float = 0.8,
                 adx_threshold: float = 15.0,
                 risk_reward_ratio: float = 1.5,
                 atr_multiplier: float = 1.5):
        
        self.primary_threshold = primary_threshold
        self.meta_threshold = meta_threshold
        self.rsi_min = rsi_min
        self.rsi_max = rsi_max
        self.volume_threshold = volume_threshold
        self.adx_threshold = adx_threshold
        self.risk_reward_ratio = risk_reward_ratio
        self.atr_multiplier = atr_multiplier
    
    def scan(self, symbols: List[str], scan_date: Optional[datetime] = None) -> List[Dict]:
        """
        M10 스캔 실행
        """
        if scan_date is None:
            scan_date = datetime.now()
        
        candidates = []
        start_dt = scan_date - timedelta(days=100)
        start_str = start_dt.strftime('%Y-%m-%d')
        end_str = scan_date.strftime('%Y-%m-%d')
        
        print(f"\n🔍 M10 스캔 시작 ({len(symbols)}개 종목)")
        print(f"   기준일: {scan_date.strftime('%Y-%m-%d')}")
        print(f"   Primary 신뢰도: {self.primary_threshold}%+")
        print(f"   Meta 신뢰도: {self.meta_threshold}%+")
        print(f"   RSI: {self.rsi_min}~{self.rsi_max}")
        print("-" * 60)
        
        for i, symbol in enumerate(symbols, 1):
            if i % 10 == 0:
                print(f"   진행: {i}/{len(symbols)}...")
            
            try:
                # 데이터 로드
                df = get_price(symbol, start=start_str, end=end_str)
                
                if len(df) < 60:
                    continue
                
                df = normalize_columns(df)
                
                current_price = df['Close'].iloc[-1]
                
                # 1. AI 예측
                primary_conf, meta_conf = ai_predict_direction(df)
                
                if primary_conf < self.primary_threshold or meta_conf < self.meta_threshold:
                    continue
                
                # 2. 기술적 필터
                rsi = calculate_rsi(df['Close'], 14).iloc[-1]
                if not (self.rsi_min <= rsi <= self.rsi_max):
                    continue
                
                # 거래량 체크
                volume_ma = df['Volume'].rolling(20).mean().iloc[-1]
                current_volume = df['Volume'].iloc[-1]
                volume_ratio = current_volume / volume_ma if volume_ma > 0 else 0
                
                if volume_ratio < self.volume_threshold:
                    continue
                
                # ADX 체크
                adx = calculate_adx(df, 14).iloc[-1]
                if adx < self.adx_threshold:
                    continue
                
                # 3. Fibonacci 레벨 계산
                fib_levels = calculate_fibonacci_levels(df)
                
                # 4. 진입가/목표가/손절가 계산
                entry_price = current_price
                target_price = fib_levels['fib_1618']
                
                # ATR 기반 손절가
                atr = calculate_atr(df, 14).iloc[-1]
                stop_loss = entry_price - (atr * self.atr_multiplier)
                
                # 손익비 확인
                if target_price <= entry_price or stop_loss >= entry_price:
                    continue
                
                risk = entry_price - stop_loss
                reward = target_price - entry_price
                rr_ratio = reward / risk if risk > 0 else 0
                
                if rr_ratio < self.risk_reward_ratio:
                    continue
                
                # 예상 수익률/손실률
                expected_return = (target_price - entry_price) / entry_price * 100
                expected_loss = (stop_loss - entry_price) / entry_price * 100
                
                candidates.append({
                    'symbol': symbol,
                    'primary_confidence': primary_conf,
                    'meta_confidence': meta_conf,
                    'rsi': rsi,
                    'volume_ratio': volume_ratio,
                    'adx': adx,
                    'current_price': current_price,
                    'entry_price': entry_price,
                    'target_price': target_price,
                    'stop_loss': stop_loss,
                    'rr_ratio': rr_ratio,
                    'expected_return': expected_return,
                    'expected_loss': expected_loss,
                    'atr': atr,
                    'fib_high': fib_levels['high'],
                    'fib_low': fib_levels['low']
                })
                
            except Exception as e:
                continue
        
        print(f"\n   스캔 완료: {len(symbols)}개 중 {len(candidates)}개 통과")
        
        # AI 신뢰도 순으로 정렬
        candidates.sort(key=lambda x: x['meta_confidence'] + x['primary_confidence'], reverse=True)
        
        return candidates


def main():
    """메인 실행"""
    # 테스트용 대형주 리스트
    symbols = [
        '005930', '000660', '051910', '005380', '035720',
        '068270', '207940', '006400', '000270', '012330',
        '005490', '028260', '105560', '018260', '032830',
        '000100', '000150', '000250', '000300', '000400',
        '000500', '000650', '000700', '000850', '000950',
        '003550', '004020', '005070', '005110', '005860',
        '009240', '009830', '010130', '010950', '011200',
        '016360', '024110', '028050', '034220', '034730',
        '001040', '001460', '001740', '002320', '002700',
        '003200', '003490', '004170', '004800', '005500'
    ]
    
    print("📊 M10 스캐너 실행")
    print(f"   종목: {len(symbols)}개")
    
    # 스캐너 초기화
    scanner = M10Scanner(
        primary_threshold=60.0,
        meta_threshold=65.0,
        rsi_min=35.0,
        rsi_max=75.0,
        volume_threshold=0.8,
        adx_threshold=15.0,
        risk_reward_ratio=1.5,
        atr_multiplier=1.5
    )
    
    # 스캔 실행
    scan_date = datetime(2026, 3, 20)  # 2026-03-20 기준
    results = scanner.scan(symbols, scan_date)
    
    # TOP 20 선택
    top_stocks = results[:20]
    
    # 결과 출력
    print(f"\n{'='*80}")
    print(f"📈 M10 선정 종목 TOP {len(top_stocks)} ({scan_date.strftime('%Y-%m-%d')})")
    print(f"{'='*80}")
    
    for i, stock in enumerate(top_stocks, 1):
        print(f"\n{i}. {stock['symbol']}")
        print(f"   AI 신뢰도: Primary {stock['primary_confidence']:.1f}% | Meta {stock['meta_confidence']:.1f}%")
        print(f"   기술적: RSI {stock['rsi']:.1f} | Volume {stock['volume_ratio']:.2f}x | ADX {stock['adx']:.1f}")
        print(f"   현재가: ₩{stock['current_price']:,.0f}")
        print(f"   🎯 목표가: ₩{stock['target_price']:,.0f} (+{stock['expected_return']:.1f}%)")
        print(f"   🛑 손절가: ₩{stock['stop_loss']:,.0f} ({stock['expected_loss']:.1f}%)")
        print(f"   ⚖️  손익비: 1:{stock['rr_ratio']:.2f}")
    
    # JSON 저장
    output_dir = './reports/m10'
    os.makedirs(output_dir, exist_ok=True)
    
    timestamp = scan_date.strftime('%Y%m%d')
    filename = f'{output_dir}/m10_scan_{timestamp}.json'
    
    # numpy 타입을 Python native 타입으로 변환
    def convert_to_native(obj):
        if isinstance(obj, np.integer):
            return int(obj)
        elif isinstance(obj, np.floating):
            return float(obj)
        elif isinstance(obj, np.ndarray):
            return obj.tolist()
        return obj
    
    # 변환 적용
    top_stocks_native = []
    for stock in top_stocks:
        stock_native = {k: convert_to_native(v) for k, v in stock.items()}
        top_stocks_native.append(stock_native)
    
    with open(filename, 'w', encoding='utf-8') as f:
        json.dump({
            'scan_date': scan_date.strftime('%Y-%m-%d'),
            'total_symbols': len(symbols),
            'selected_count': len(results),
            'parameters': {
                'primary_threshold': scanner.primary_threshold,
                'meta_threshold': scanner.meta_threshold,
                'rsi_range': [scanner.rsi_min, scanner.rsi_max],
                'volume_threshold': scanner.volume_threshold,
                'adx_threshold': scanner.adx_threshold,
                'risk_reward_ratio': scanner.risk_reward_ratio,
                'atr_multiplier': scanner.atr_multiplier
            },
            'top_stocks': top_stocks_native
        }, f, ensure_ascii=False, indent=2)
    
    print(f"\n💾 결과 저장: {filename}")
    
    return top_stocks


if __name__ == '__main__':
    main()
