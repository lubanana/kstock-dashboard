#!/usr/bin/env python3
"""
NPS (Net Purchase Strength) Strategy Scanner with Fibonacci + ATR
NPS 외국인/기관 매수세 스캐너 - 피볼나치 + ATR 적용

Usage:
    python nps_value_scanner.py                    # 오늘 날짜로 스캔
    python nps_value_scanner.py --date 2026-03-24  # 지정 날짜로 스캔
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List
import json
from pathlib import Path
import sys
import argparse
sys.path.insert(0, '.')
from fdr_wrapper import get_price


class NPSValueScanner:
    """
    NPS (Net Purchase Strength) 가치 스타일 스캐너
    - 외국인/기관 수급 분석
    - 가치평가 기반 진입
    - 모멘텀 + 가치 결합
    """
    
    def __init__(self, symbols: List[str] = None):
        self.symbols = symbols or self._load_default_symbols()
        self.results = []
        
    def _load_default_symbols(self) -> List[str]:
        """기본 대형주 리스트"""
        return [
            '005930', '000660', '051910', '005380', '035720', '068270', '207940',
            '006400', '000270', '012330', '005490', '028260', '105560', '018260',
            '032830', '034730', '000150', '016360', '009830', '003490', '004170',
            '000100', '011200', '030200', '010950', '034220', '086790', '055550'
        ]
    
    def fetch_data(self, symbol: str, end_date: datetime = None, days: int = 90) -> pd.DataFrame:
        """종목 데이터 조회"""
        try:
            if end_date is None:
                end_date = datetime.now()
            start_date = end_date - timedelta(days=days)
            
            df = get_price(
                symbol,
                start_date=start_date.strftime('%Y-%m-%d'),
                end_date=end_date.strftime('%Y-%m-%d')
            )
            
            if df.empty or len(df) < 40:
                return pd.DataFrame()
            
            df.columns = [c.lower() for c in df.columns]
            return df
            
        except Exception as e:
            print(f"   ⚠️ {symbol} 데이터 오류: {e}")
            return pd.DataFrame()
    
    def calculate_nps_score(self, df: pd.DataFrame) -> Dict:
        """NPS 점수 계산 (Net Purchase Strength)"""
        # 이동평균 먼저 계산
        df['ema20'] = df['close'].ewm(span=20, adjust=False).mean()
        df['ema60'] = df['close'].ewm(span=60, adjust=False).mean()
        
        # RSI
        delta = df['close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
        rs = gain / loss
        df['rsi'] = 100 - (100 / (1 + rs))
        
        # ATR 계산
        high_low = df['high'] - df['low']
        high_close = np.abs(df['high'] - df['close'].shift())
        low_close = np.abs(df['low'] - df['close'].shift())
        ranges = pd.concat([high_low, high_close, low_close], axis=1)
        true_range = np.max(ranges, axis=1)
        df['atr'] = true_range.rolling(14).mean()
        
        # 모든 지표 계산 후 latest 가져오기
        latest = df.iloc[-1]
        
        # NPS 점수 계산
        score = 0
        details = {}
        
        # 1. 추세 점수 (35점)
        trend_score = 0
        if latest['close'] > latest['ema20']:
            trend_score += 15
        if latest['ema20'] > latest['ema60']:
            trend_score += 15
        if latest['close'] > df['close'].shift(20).mean():
            trend_score += 5
        
        score += trend_score
        details['trend'] = {'score': trend_score, 'max': 35}
        
        # 2. 모멘텀 점수 (35점)
        momentum_score = 0
        rsi = latest['rsi']
        
        if 50 <= rsi <= 70:
            momentum_score += 20
        elif 40 <= rsi < 50:
            momentum_score += 15
        
        # 가격 모멘텀
        returns_20d = (latest['close'] - df['close'].shift(20).iloc[-1]) / df['close'].shift(20).iloc[-1] * 100
        if returns_20d > 10:
            momentum_score += 15
        elif returns_20d > 5:
            momentum_score += 10
        elif returns_20d > 0:
            momentum_score += 5
        
        score += momentum_score
        details['momentum'] = {'score': momentum_score, 'max': 35, 'rsi': rsi, 'return_20d': returns_20d}
        
        # 3. 거래량 점수 (30점) - 수급 강도
        volume_score = 0
        avg_volume = df['volume'].rolling(20).mean().iloc[-1]
        current_volume = latest['volume']
        
        if avg_volume > 0:
            volume_ratio = current_volume / avg_volume
            if volume_ratio >= 2.0:
                volume_score = 30
            elif volume_ratio >= 1.5:
                volume_score = 25
            elif volume_ratio >= 1.2:
                volume_score = 20
            elif volume_ratio >= 1.0:
                volume_score = 15
        
        score += volume_score
        details['volume'] = {'score': volume_score, 'max': 30}
        
        return {
            'total_score': score,
            'details': details,
            'atr': df['atr'].iloc[-1],
            'rsi': rsi,
            'ema20': latest['ema20'],
            'ema60': latest['ema60'],
            'return_20d': returns_20d
        }
    
    def calculate_fibonacci_levels(self, df: pd.DataFrame) -> Dict:
        """피볼나치 되돌림 레벨 계산"""
        recent_high = df['high'].rolling(40).max().iloc[-1]
        recent_low = df['low'].rolling(40).min().iloc[-1]
        current_price = df['close'].iloc[-1]
        
        diff = recent_high - recent_low
        
        levels = {
            'fib_0': recent_high,
            'fib_382': recent_high - 0.382 * diff,
            'fib_50': recent_high - 0.5 * diff,
            'fib_618': recent_high - 0.618 * diff,
            'fib_786': recent_high - 0.786 * diff,
            'fib_100': recent_low
        }
        
        # 현재 가격이 어떤 피볼나치 레벨에 있는지 확인
        fib_level = None
        if current_price >= levels['fib_382']:
            fib_level = 'fib_382'
        elif current_price >= levels['fib_50']:
            fib_level = 'fib_50'
        elif current_price >= levels['fib_618']:
            fib_level = 'fib_618'
        else:
            fib_level = 'below_618'
        
        return {
            'levels': levels,
            'current_level': fib_level,
            'high': recent_high,
            'low': recent_low
        }
    
    def calculate_atr_targets(self, df: pd.DataFrame, entry_price: float) -> Dict:
        """ATR 기반 목표가/손절가 계산"""
        atr = df['atr'].iloc[-1]
        
        # NPS 스타일: 중간 리스크
        sl_multiplier = 1.8  # 손절: 1.8 ATR
        tp_multiplier = 3.6  # 목표: 3.6 ATR (1:2 RR)
        
        stop_loss = entry_price - (atr * sl_multiplier)
        target_price = entry_price + (atr * tp_multiplier)
        
        risk = entry_price - stop_loss
        reward = target_price - entry_price
        rr_ratio = reward / risk if risk > 0 else 0
        
        return {
            'entry': entry_price,
            'stop_loss': stop_loss,
            'target': target_price,
            'rr_ratio': rr_ratio,
            'atr': atr,
            'risk_amount': risk,
            'reward_amount': reward
        }
    
    def scan(self, scan_date: datetime = None) -> List[Dict]:
        """스캔 실행"""
        if scan_date is None:
            scan_date = datetime.now()
            
        print("=" * 70)
        print("📊 NPS (Net Purchase Strength) Strategy Scanner (Fibonacci + ATR)")
        print("=" * 70)
        print(f"기준일: {scan_date.strftime('%Y-%m-%d')}")
        print(f"대상 종목: {len(self.symbols)}개")
        print("-" * 70)
        
        results = []
        
        for i, symbol in enumerate(self.symbols, 1):
            print(f"\n   [{i}/{len(self.symbols)}] {symbol}")
            
            # 데이터 조회
            df = self.fetch_data(symbol, end_date=scan_date)
            if df.empty:
                print("   ❌ 데이터 부족")
                continue
            
            # NPS 점수 계산
            nps = self.calculate_nps_score(df)
            
            # 최소 점수 필터 (65점 이상)
            if nps['total_score'] < 65:
                print(f"   ❌ NPS 점수 부족: {nps['total_score']}")
                continue
            
            # 피볼나치 계산
            fib = self.calculate_fibonacci_levels(df)
            
            # ATR 기반 목표가/손절가
            current_price = df['close'].iloc[-1]
            atr_targets = self.calculate_atr_targets(df, current_price)
            
            # 최소 손익비 필터 (1:1.5)
            if atr_targets['rr_ratio'] < 1.5:
                print(f"   ❌ 손익비 부족: 1:{atr_targets['rr_ratio']:.2f}")
                continue
            
            result = {
                'symbol': symbol,
                'name': self._get_stock_name(symbol),
                'nps_score': nps['total_score'],
                'nps_details': nps['details'],
                'rsi': nps['rsi'],
                'return_20d': nps['return_20d'],
                'current_price': current_price,
                'entry_price': current_price,
                'target_price': atr_targets['target'],
                'stop_loss': atr_targets['stop_loss'],
                'rr_ratio': atr_targets['rr_ratio'],
                'atr': atr_targets['atr'],
                'fib_level': fib['current_level'],
                'fib_high': fib['high'],
                'fib_low': fib['low'],
                'expected_return': (atr_targets['target'] - current_price) / current_price * 100,
                'expected_loss': (atr_targets['stop_loss'] - current_price) / current_price * 100,
                'strategy': 'NPS'
            }
            
            results.append(result)
            print(f"   ✅ 선정됨: 점수 {result['nps_score']}, RR 1:{result['rr_ratio']:.2f}")
        
        # 점수 기준 정렬
        results.sort(key=lambda x: x['nps_score'], reverse=True)
        
        self.results = results
        return results
    
    def _get_stock_name(self, symbol: str) -> str:
        """종목명 조회"""
        names = {
            '005930': '삼성전자', '000660': 'SK하이닉스', '051910': 'LG화학',
            '005380': '현대차', '035720': '카카오', '068270': '셀트리온',
            '207940': '삼성바이오로직스', '006400': '삼성SDI', '000270': '기아',
            '012330': '현대모비스', '005490': 'POSCO홀딩스', '028260': '삼성물산',
            '105560': 'KB금융', '018260': '삼성에스디에스', '032830': '삼성생명',
            '034730': 'SK', '000150': '두산', '016360': '삼성증권',
            '009830': '한화솔루션', '003490': '대한항공', '004170': '신세계',
            '000100': '유한양행', '011200': 'HMM', '030200': 'KT',
            '010950': 'S-Oil', '034220': 'LG디스플레이', '086790': '하나금융지주',
            '055550': '신한지주'
        }
        return names.get(symbol, symbol)
    
    def print_results(self, scan_date: datetime = None):
        """결과 출력"""
        if scan_date is None:
            scan_date = datetime.now()
            
        print("\n" + "=" * 70)
        print(f"📊 NPS 전략 선정 종목 TOP {len(self.results)} ({scan_date.strftime('%Y-%m-%d')})")
        print("=" * 70)
        
        for i, stock in enumerate(self.results[:10], 1):
            print(f"\n{i}. {stock['name']} ({stock['symbol']})")
            print(f"   NPS Score: {stock['nps_score']}점")
            print(f"   RSI: {stock['rsi']:.1f}")
            print(f"   20일 수익률: {stock['return_20d']:.1f}%")
            print(f"   현재가: ₩{stock['current_price']:,.0f}")
            print(f"   목표가: ₩{stock['target_price']:,.0f} (+{stock['expected_return']:.1f}%)")
            print(f"   손절가: ₩{stock['stop_loss']:,.0f} ({stock['expected_loss']:.1f}%)")
            print(f"   손익비: 1:{stock['rr_ratio']:.2f}")
            print(f"   Fibonacci: {stock['fib_level']}")
        
        print("\n" + "=" * 70)
    
    def save_results(self, scan_date: datetime = None):
        """결과 저장"""
        if scan_date is None:
            scan_date = datetime.now()
            
        output_dir = Path('./reports/nps')
        output_dir.mkdir(parents=True, exist_ok=True)
        
        timestamp = scan_date.strftime('%Y%m%d')
        output_file = output_dir / f'nps_scan_{timestamp}.json'
        
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump({
                'scan_date': scan_date.strftime('%Y-%m-%d'),
                'total_symbols': len(self.symbols),
                'selected_count': len(self.results),
                'stocks': self.results
            }, f, ensure_ascii=False, indent=2, default=str)
        
        print(f"\n💾 결과 저장: {output_file}")


def main():
    # 명령행 인자 파싱
    parser = argparse.ArgumentParser(description='NPS Scanner - Net Purchase Strength 기반 종목 스캐너')
    parser.add_argument('--date', type=str, help='스캔 기준일 (YYYY-MM-DD 형식). 미지정 시 오늘 날짜')
    args = parser.parse_args()
    
    # 스캔 날짜 설정
    if args.date:
        scan_date = datetime.strptime(args.date, '%Y-%m-%d')
    else:
        scan_date = datetime.now()
    
    scanner = NPSValueScanner()
    results = scanner.scan(scan_date)
    scanner.print_results(scan_date)
    scanner.save_results(scan_date)
    
    print(f"\n📊 총 선정: {len(results)}개 종목")


if __name__ == '__main__':
    main()
