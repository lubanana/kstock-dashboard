#!/usr/bin/env python3
"""
V-Series Daily Scanner
오늘 기준 V-Series (Value + Fibonacci + ATR) 종목 스캔

Usage:
    python v_series_scanner.py                    # 오늘 날짜로 스캔
    python v_series_scanner.py --date 2026-03-24  # 지정 날짜로 스캔
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Tuple
import json
import os
import sys
import argparse
import warnings
warnings.filterwarnings('ignore')

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from fdr_wrapper import get_price


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


class ValueFibATRScanner:
    """
    V-Series 실시간 스캐너
    - Value Score 기반 선별
    - Fibonacci 레벨 진입 체크
    - ATR 기반 손절/목표가 계산
    - 1:1.5+ 손익비 필터
    """
    
    def __init__(self,
                 value_score_threshold: float = 65.0,
                 risk_reward_ratio: float = 1.5,
                 atr_multiplier: float = 1.5,
                 fib_entry_tolerance: float = 0.05,
                 min_volume: float = 1_000_000_000):  # 최소 거래대금 10억
        
        self.value_score_threshold = value_score_threshold
        self.risk_reward_ratio = risk_reward_ratio
        self.atr_multiplier = atr_multiplier
        self.fib_entry_tolerance = fib_entry_tolerance
        self.min_volume = min_volume
    
    def calculate_atr(self, df: pd.DataFrame, period: int = 14) -> pd.Series:
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
    
    def calculate_fibonacci_levels(self, df: pd.DataFrame, lookback: int = 20) -> Dict[str, float]:
        """Fibonacci 레벨 계산"""
        recent_high = df['High'].rolling(window=lookback, min_periods=5).max().iloc[-1]
        recent_low = df['Low'].rolling(window=lookback, min_periods=5).min().iloc[-1]
        
        price_range = recent_high - recent_low
        
        # Retracement levels
        fib_382 = recent_high - price_range * 0.382
        fib_50 = recent_high - price_range * 0.5
        fib_618 = recent_high - price_range * 0.618
        
        # Extension levels for targets
        fib_1382 = recent_high + price_range * 0.382
        fib_1618 = recent_high + price_range * 0.618
        
        current_close = df['Close'].iloc[-1]
        
        return {
            'high': recent_high,
            'low': recent_low,
            'range': price_range,
            'fib_382': fib_382,
            'fib_50': fib_50,
            'fib_618': fib_618,
            'fib_1382': fib_1382,
            'fib_1618': fib_1618,
            'current': current_close
        }
    
    def calculate_risk_reward(self, entry: float, target: float, stop_loss: float) -> float:
        """손익비 계산"""
        if entry <= stop_loss or target <= entry:
            return 0.0
        reward = target - entry
        risk = entry - stop_loss
        return reward / risk if risk > 0 else 0.0
    
    def calculate_value_score(self, symbol: str, date: datetime) -> Tuple[float, str]:
        """간단한 가치점수 계산 (기술적 지표 기반)"""
        try:
            start_dt = date - timedelta(days=252)
            start_str = start_dt.strftime('%Y-%m-%d')
            end_str = date.strftime('%Y-%m-%d')
            
            df = get_price(symbol, start_date=start_str, end_date=end_str)
            df = normalize_columns(df)
            
            if len(df) < 60:
                return 0, "데이터부족"
            
            current_price = df['Close'].iloc[-1]
            
            # 1. Graham Net-Net 근사 (주가가 52주 최저가 근처)
            low_52w = df['Low'].rolling(252, min_periods=60).min().iloc[-1]
            high_52w = df['High'].rolling(252, min_periods=60).max().iloc[-1]
            price_range = (current_price - low_52w) / (high_52w - low_52w) if high_52w > low_52w else 0.5
            
            # 2. Quality 근사 (추세 방향성)
            ma20 = df['Close'].rolling(20).mean().iloc[-1]
            ma60 = df['Close'].rolling(60).mean().iloc[-1]
            trend_score = 100 if current_price > ma20 > ma60 else 50 if current_price > ma60 else 0
            
            # 3. Volume stability
            volume_mean = df['Volume'].rolling(20).mean().iloc[-1]
            volume_std = df['Volume'].rolling(20).std().iloc[-1]
            volume_stability = 100 - min(100, (volume_std / volume_mean * 100)) if volume_mean > 0 else 0
            
            # 종합 점수
            value_score = (price_range * 30) + (trend_score * 0.4) + (volume_stability * 0.3)
            
            # 전략 분류
            if price_range < 0.3:
                strategy = "Graham_NetNet"
            elif trend_score >= 80:
                strategy = "Quality_FairPrice"
            elif volume_stability >= 70:
                strategy = "Dividend_Machine"
            else:
                strategy = "Value_Blend"
            
            return value_score, strategy
            
        except Exception as e:
            return 0, f"오류: {e}"
    
    def scan(self, symbols: List[str], scan_date: Optional[datetime] = None) -> List[Dict]:
        """
        V-Series 종목 스캔
        
        Parameters:
        -----------
        symbols : List[str]
            스캔할 종목 코드 리스트
        scan_date : datetime, optional
            스캔 기준일 (기본: 오늘)
        
        Returns:
        --------
        List[Dict]
            선정된 종목 리스트 (가치점수 순 정렬)
        """
        if scan_date is None:
            scan_date = datetime.now()
        
        candidates = []
        start_dt = scan_date - timedelta(days=100)
        start_str = start_dt.strftime('%Y-%m-%d')
        end_str = scan_date.strftime('%Y-%m-%d')
        
        print(f"\n🔍 V-Series 스캔 시작 ({len(symbols)}개 종목)")
        print(f"   기준일: {scan_date.strftime('%Y-%m-%d')}")
        print(f"   가치점수 기준: {self.value_score_threshold}점+")
        print(f"   최소 손익비: 1:{self.risk_reward_ratio}")
        print("-" * 60)
        
        for i, symbol in enumerate(symbols, 1):
            if i % 50 == 0:
                print(f"   진행: {i}/{len(symbols)}...")
            
            try:
                # 1. 가치 점수 계산
                value_score, strategy_type = self.calculate_value_score(symbol, scan_date)
                
                if value_score < self.value_score_threshold:
                    continue
                
                # 2. 기술적 데이터 로드
                df = get_price(symbol, start_date=start_str, end_date=end_str)
                df = normalize_columns(df)
                
                if len(df) < 60:
                    continue
                
                # 3. ATR 계산
                atr = self.calculate_atr(df, 14).iloc[-1]
                current_price = df['Close'].iloc[-1]
                
                # 최소 거래대금 확인
                avg_volume = df['Volume'].rolling(20).mean().iloc[-1]
                avg_amount = avg_volume * current_price
                if avg_amount < self.min_volume:
                    continue
                
                # 4. Fibonacci 레벨 계산
                fib_levels = self.calculate_fibonacci_levels(df)
                
                # 5. 진입가 설정 (Fibonacci 레벨 근처 현재가)
                entry_price = None
                fib_level_used = None
                
                for level_name, level_price in [
                    ('fib_50', fib_levels['fib_50']),
                    ('fib_382', fib_levels['fib_382']),
                    ('fib_618', fib_levels['fib_618'])
                ]:
                    tolerance = level_price * self.fib_entry_tolerance
                    if level_price - tolerance <= current_price <= level_price + tolerance:
                        entry_price = current_price  # 현재가 기준
                        fib_level_used = level_name
                        break
                
                # Fibonacci 레벨 근처가 아니면 스킵
                if entry_price is None:
                    continue
                
                # 6. 목표가 및 손절가 설정
                target_price = fib_levels['fib_1618']
                stop_loss = entry_price - (atr * self.atr_multiplier)
                
                # 7. 손익비 확인
                rr_ratio = self.calculate_risk_reward(entry_price, target_price, stop_loss)
                
                if rr_ratio < self.risk_reward_ratio:
                    continue
                
                # 8. 예상 수익률/손실률 계산
                expected_return = (target_price - entry_price) / entry_price * 100
                expected_loss = (stop_loss - entry_price) / entry_price * 100
                
                candidates.append({
                    'symbol': symbol,
                    'value_score': value_score,
                    'strategy_type': strategy_type,
                    'current_price': current_price,
                    'entry_price': entry_price,
                    'target_price': target_price,
                    'stop_loss': stop_loss,
                    'rr_ratio': rr_ratio,
                    'atr': atr,
                    'fib_level': fib_level_used,
                    'fib_high': fib_levels['high'],
                    'fib_low': fib_levels['low'],
                    'expected_return': expected_return,
                    'expected_loss': expected_loss,
                    'avg_volume': avg_volume,
                    'avg_amount': avg_amount
                })
                
            except Exception as e:
                continue
        
        print(f"\n   스캔 완료: {len(symbols)}개 중 {len(candidates)}개 통과")
        
        # 가치점수 순으로 정렬
        candidates.sort(key=lambda x: x['value_score'], reverse=True)
        
        return candidates


def load_kospi_kosdaq_symbols() -> List[str]:
    """KOSPI/KOSDAQ 종목 코드 로드"""
    try:
        import FinanceDataReader as fdr
        kospi = fdr.StockListing('KOSPI')
        kosdaq = fdr.StockListing('KOSDAQ')
        
        symbols = []
        for df in [kospi, kosdaq]:
            if 'Code' in df.columns:
                symbols.extend(df['Code'].tolist())
        
        # 중복 제거 및 정렬
        symbols = list(set(symbols))
        symbols.sort()
        
        return symbols
    except Exception as e:
        print(f"⚠️ 종목 리스트 로드 실패: {e}")
        # 기본 대형주 리스트 반환
        return [
            '005930', '000660', '051910', '005380', '035720',
            '068270', '207940', '006400', '000270', '012330',
            '005490', '028260', '105560', '018260', '032830'
        ]


def main():
    """메인 실행"""
    # 명령행 인자 파싱
    parser = argparse.ArgumentParser(description='V-Series Scanner - Value + Fibonacci + ATR 기반 종목 스캐너')
    parser.add_argument('--date', type=str, help='스캔 기준일 (YYYY-MM-DD 형식). 미지정 시 오늘 날짜')
    args = parser.parse_args()
    
    # 스캔 날짜 설정
    if args.date:
        scan_date = datetime.strptime(args.date, '%Y-%m-%d')
    else:
        scan_date = datetime.now()
    
    # 종목 리스트 로드
    print("📊 종목 리스트 로드 중...")
    
    # 테스트용 대형주 리스트 (빠른 실행)
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
    
    print(f"   테스트용 {len(symbols)}개 종목")
    print(f"   스캔 기준일: {scan_date.strftime('%Y-%m-%d')}")
    
    # 스캐너 초기화
    scanner = ValueFibATRScanner(
        value_score_threshold=65.0,
        risk_reward_ratio=1.5,
        atr_multiplier=1.5,
        fib_entry_tolerance=0.05
    )
    
    # 스캔 실행
    results = scanner.scan(symbols, scan_date)
    
    # TOP 20 선택
    top_stocks = results[:20]
    
    # 결과 출력
    print(f"\n{'='*70}")
    print(f"📈 V-Series 선정 종목 TOP {len(top_stocks)} ({scan_date.strftime('%Y-%m-%d')})")
    print(f"{'='*70}")
    
    for i, stock in enumerate(top_stocks, 1):
        print(f"\n{i}. {stock['symbol']} ({stock['strategy_type']})")
        print(f"   가치점수: {stock['value_score']:.1f}")
        print(f"   현재가: ₩{stock['current_price']:,.0f}")
        print(f"   진입가: ₩{stock['entry_price']:,.0f}")
        print(f"   목표가: ₩{stock['target_price']:,.0f} (+{stock['expected_return']:.1f}%)")
        print(f"   손절가: ₩{stock['stop_loss']:,.0f} ({stock['expected_loss']:.1f}%)")
        print(f"   손익비: 1:{stock['rr_ratio']:.2f}")
        print(f"   Fibonacci: {stock['fib_level']} (High: ₩{stock['fib_high']:,.0f}, Low: ₩{stock['fib_low']:,.0f})")
    
    # JSON 저장
    output_dir = './reports/v_series'
    os.makedirs(output_dir, exist_ok=True)
    
    timestamp = scan_date.strftime('%Y%m%d')
    filename = f'{output_dir}/v_series_scan_{timestamp}.json'
    
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
                'value_score_threshold': scanner.value_score_threshold,
                'risk_reward_ratio': scanner.risk_reward_ratio,
                'atr_multiplier': scanner.atr_multiplier
            },
            'top_stocks': top_stocks_native
        }, f, ensure_ascii=False, indent=2)
    
    print(f"\n💾 결과 저장: {filename}")
    
    return top_stocks


if __name__ == '__main__':
    main()
