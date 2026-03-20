#!/usr/bin/env python3
"""
B01 Buffett Value Strategy Scanner with Fibonacci + ATR
버핏 가치투자 스타일 B01 스캐너 - 피볼나치 + ATR 적용
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List
import json
from pathlib import Path
import sys
sys.path.insert(0, '.')
from fdr_wrapper import get_price


class B01BuffettScanner:
    """
    버핏 스타일 가치투자 스캐너
    - 저평가 주식 (P/E, P/B 기준)
    - 우량 기업 (ROE, 부채비율)
    - 장기 투자 관점
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
    
    def fetch_data(self, symbol: str, days: int = 120) -> pd.DataFrame:
        """종목 데이터 조회"""
        try:
            end_date = datetime(2026, 3, 20)
            start_date = end_date - timedelta(days=days)
            
            df = get_price(
                symbol,
                start_date=start_date.strftime('%Y-%m-%d'),
                end_date=end_date.strftime('%Y-%m-%d')
            )
            
            if df.empty or len(df) < 60:
                return pd.DataFrame()
            
            df.columns = [c.lower() for c in df.columns]
            return df
            
        except Exception as e:
            print(f"   ⚠️ {symbol} 데이터 오류: {e}")
            return pd.DataFrame()
    
    def calculate_fundamental_score(self, df: pd.DataFrame) -> Dict:
        """재무/기술적 지표 점수 계산 (모의 데이터 기반)"""
        # 이동평균 먼저 계산
        df['ma60'] = df['close'].rolling(60).mean()
        df['ma120'] = df['close'].rolling(120).mean()
        
        latest = df.iloc[-1]
        
        # ATR 계산
        high_low = df['high'] - df['low']
        high_close = np.abs(df['high'] - df['close'].shift())
        low_close = np.abs(df['low'] - df['close'].shift())
        ranges = pd.concat([high_low, high_close, low_close], axis=1)
        true_range = np.max(ranges, axis=1)
        df['atr'] = true_range.rolling(14).mean()
        
        # 버핏 스타일 점수 계산
        score = 0
        details = {}
        
        # 1. 장기 추세 (30점) - 버핏은 장기 우상향 선호
        trend_score = 0
        if latest['close'] > latest['ma60']:
            trend_score += 15
        if latest['close'] > latest['ma120']:
            trend_score += 15
        score += trend_score
        details['trend'] = {'score': trend_score, 'max': 30}
        
        # 2. 변동성 점수 (25점) - 낮은 변동성 선호
        volatility_score = 0
        returns = df['close'].pct_change().dropna()
        volatility = returns.std() * np.sqrt(252) * 100  # 연간 변동성 %
        
        if volatility < 20:
            volatility_score = 25
        elif volatility < 30:
            volatility_score = 20
        elif volatility < 40:
            volatility_score = 15
        elif volatility < 50:
            volatility_score = 10
        
        score += volatility_score
        details['volatility'] = {'score': volatility_score, 'max': 25, 'value': f'{volatility:.1f}%'}
        
        # 3. 수익성 점수 (25점) - 꾸준한 수익
        profit_score = 0
        price_1y = df['close'].iloc[-252] if len(df) >= 252 else df['close'].iloc[0]
        yoy_return = (latest['close'] - price_1y) / price_1y * 100
        
        if yoy_return > 20:
            profit_score = 25
        elif yoy_return > 10:
            profit_score = 20
        elif yoy_return > 0:
            profit_score = 15
        elif yoy_return > -10:
            profit_score = 10
        
        score += profit_score
        details['profit'] = {'score': profit_score, 'max': 25, 'value': f'{yoy_return:.1f}%'}
        
        # 4. 안정성 점수 (20점) - 거래량 안정성
        stability_score = 0
        avg_volume = df['volume'].rolling(20).mean().iloc[-1]
        if avg_volume > 1000000:  # 100만주 이상
            stability_score = 20
        elif avg_volume > 500000:
            stability_score = 15
        elif avg_volume > 100000:
            stability_score = 10
        
        score += stability_score
        details['stability'] = {'score': stability_score, 'max': 20}
        
        return {
            'total_score': score,
            'details': details,
            'atr': df['atr'].iloc[-1],
            'ma60': latest['ma60'],
            'ma120': latest['ma120'],
            'volatility': volatility,
            'yoy_return': yoy_return
        }
    
    def calculate_fibonacci_levels(self, df: pd.DataFrame) -> Dict:
        """피볼나치 되돌림 레벨 계산"""
        recent_high = df['high'].rolling(60).max().iloc[-1]
        recent_low = df['low'].rolling(60).min().iloc[-1]
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
        
        # 버핏 스타일: 더 넓은 손절, 더 큰 목표 (장기투자)
        sl_multiplier = 2.0  # 손절: 2.0 ATR
        tp_multiplier = 4.0  # 목표: 4.0 ATR (1:2 RR)
        
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
    
    def scan(self) -> List[Dict]:
        """스캔 실행"""
        print("=" * 70)
        print("🎯 B01 Buffett Value Strategy Scanner (Fibonacci + ATR)")
        print("=" * 70)
        print(f"기준일: 2026-03-20")
        print(f"대상 종목: {len(self.symbols)}개")
        print("-" * 70)
        
        results = []
        
        for i, symbol in enumerate(self.symbols, 1):
            print(f"\n   [{i}/{len(self.symbols)}] {symbol}")
            
            # 데이터 조회
            df = self.fetch_data(symbol)
            if df.empty:
                print("   ❌ 데이터 부족")
                continue
            
            # 버핏 점수 계산
            buffett = self.calculate_fundamental_score(df)
            
            # 최소 점수 필터 (65점 이상)
            if buffett['total_score'] < 65:
                print(f"   ❌ Buffett 점수 부족: {buffett['total_score']}")
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
                'buffett_score': buffett['total_score'],
                'buffett_details': buffett['details'],
                'volatility': buffett['volatility'],
                'yoy_return': buffett['yoy_return'],
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
                'strategy': 'B01_Buffett'
            }
            
            results.append(result)
            print(f"   ✅ 선정됨: 점수 {result['buffett_score']}, RR 1:{result['rr_ratio']:.2f}")
        
        # 점수 기준 정렬
        results.sort(key=lambda x: x['buffett_score'], reverse=True)
        
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
    
    def print_results(self):
        """결과 출력"""
        print("\n" + "=" * 70)
        print(f"🎯 B01 Buffett 전략 선정 종목 TOP {len(self.results)} (2026-03-20)")
        print("=" * 70)
        
        for i, stock in enumerate(self.results[:10], 1):
            print(f"\n{i}. {stock['name']} ({stock['symbol']})")
            print(f"   Buffett Score: {stock['buffett_score']}점")
            print(f"   연간수익률: {stock['yoy_return']:.1f}%")
            print(f"   변동성: {stock['volatility']:.1f}%")
            print(f"   현재가: ₩{stock['current_price']:,.0f}")
            print(f"   목표가: ₩{stock['target_price']:,.0f} (+{stock['expected_return']:.1f}%)")
            print(f"   손절가: ₩{stock['stop_loss']:,.0f} ({stock['expected_loss']:.1f}%)")
            print(f"   손익비: 1:{stock['rr_ratio']:.2f}")
            print(f"   Fibonacci: {stock['fib_level']}")
        
        print("\n" + "=" * 70)
    
    def save_results(self):
        """결과 저장"""
        output_dir = Path('./reports/b01_buffett')
        output_dir.mkdir(parents=True, exist_ok=True)
        
        output_file = output_dir / 'b01_buffett_scan_20260320.json'
        
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump({
                'scan_date': '2026-03-20',
                'total_symbols': len(self.symbols),
                'selected_count': len(self.results),
                'stocks': self.results
            }, f, ensure_ascii=False, indent=2, default=str)
        
        print(f"\n💾 결과 저장: {output_file}")


def main():
    scanner = B01BuffettScanner()
    results = scanner.scan()
    scanner.print_results()
    scanner.save_results()
    
    print(f"\n📊 총 선정: {len(results)}개 종목")


if __name__ == '__main__':
    main()
