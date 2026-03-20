#!/usr/bin/env python3
"""
Integrated Multi-Strategy Scanner
V-Strategy + B01 + NPS 통합 스캐너
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


class IntegratedMultiStrategyScanner:
    """
    4가지 전략 통합 스캐너:
    1. V-Strategy (Value + Fibonacci + ATR)
    2. B01 (Buffett Value)
    3. NPS (Net Purchase Strength)
    4. Multi-Strategy (Composite Score)
    """
    
    def __init__(self, symbols: List[str] = None):
        # 전체 코스피/코스닥 대형주
        self.symbols = symbols or self._load_all_symbols()
        self.results = {
            'V': [],
            'B01': [],
            'NPS': [],
            'Multi': []
        }
    
    def _load_all_symbols(self) -> List[str]:
        """전체 종목 리스트"""
        return [
            # 코스피 대형주 50개
            '005930', '000660', '051910', '005380', '035720', '068270', '207940',
            '006400', '000270', '012330', '005490', '028260', '105560', '018260',
            '032830', '034730', '000150', '016360', '009830', '003490', '004170',
            '000100', '011200', '030200', '010950', '034220', '086790', '055550',
            '047050', '032640', '009540', '030000', '018880', '000810', '024110',
            '005940', '010140', '001040', '003550', '008770', '007310', '006800',
            '000120', '001120', '010130', '002790', '001800', '003000', '005420',
            # 코스닥 대형주 50개
            '247540', '086520', '091990', '035900', '293490', '263750', '151860',
            '196170', '214150', '221840', '183490', '095340', '100090', '137310',
            '058470', '048260', '042000', '041140', '025980', '014990', '039030',
            '008500', '004560', '004100', '002100', '001500', '000500', '000400',
            '000300', '000210', '000180', '000140', '000080', '000070', '000050',
        ]
    
    def fetch_data(self, symbol: str, days: int = 60) -> pd.DataFrame:
        """종목 데이터 조회"""
        try:
            end_date = datetime(2026, 3, 20)
            start_date = end_date - timedelta(days=days)
            
            df = get_price(
                symbol,
                start_date=start_date.strftime('%Y-%m-%d'),
                end_date=end_date.strftime('%Y-%m-%d')
            )
            
            if df.empty or len(df) < 20:
                return pd.DataFrame()
            
            df.columns = [c.lower() for c in df.columns]
            return df
            
        except Exception as e:
            return pd.DataFrame()
    
    def calculate_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        """공통 기술적 지표 계산"""
        # 이동평균
        df['ema20'] = df['close'].ewm(span=20, adjust=False).mean()
        df['ema60'] = df['close'].ewm(span=60, adjust=False).mean()
        
        # RSI
        delta = df['close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
        rs = gain / loss
        df['rsi'] = 100 - (100 / (1 + rs))
        
        # ATR
        high_low = df['high'] - df['low']
        high_close = np.abs(df['high'] - df['close'].shift())
        low_close = np.abs(df['low'] - df['close'].shift())
        ranges = pd.concat([high_low, high_close, low_close], axis=1)
        true_range = np.max(ranges, axis=1)
        df['atr'] = true_range.rolling(14).mean()
        
        return df
    
    def calculate_v_score(self, df: pd.DataFrame) -> Dict:
        """V-Strategy 점수 계산"""
        latest = df.iloc[-1]
        
        # 가치 점수 (Fibonacci 기반)
        fib_high = df['high'].rolling(20).max().iloc[-1]
        fib_low = df['low'].rolling(20).min().iloc[-1]
        current = latest['close']
        
        # 38.2% ~ 50% retracement zone이 진입 영역
        fib_382 = fib_high - 0.382 * (fib_high - fib_low)
        fib_50 = fib_high - 0.5 * (fib_high - fib_low)
        
        score = 0
        if fib_50 <= current <= fib_382:
            score = 70 + (fib_382 - current) / (fib_382 - fib_50) * 15
        elif current < fib_50:
            score = 50 + (current - fib_low) / (fib_50 - fib_low) * 20
        else:
            score = 40 + (fib_high - current) / (fib_high - fib_382) * 30
        
        return {
            'score': min(100, max(0, score)),
            'fib_level': 'fib_50' if current < fib_50 else 'fib_382',
            'fib_high': fib_high,
            'fib_low': fib_low,
            'atr': latest['atr']
        }
    
    def calculate_b01_score(self, df: pd.DataFrame) -> Dict:
        """B01 Buffett 점수 계산"""
        # 장기 추세 먼저 계산
        df['ma60'] = df['close'].rolling(60).mean()
        df['ma120'] = df['close'].rolling(120).mean()
        
        latest = df.iloc[-1]
        
        score = 0
        if latest['close'] > latest['ma60']:
            score += 30
        if latest['close'] > df['ma120'].iloc[-1]:
            score += 20
        
        # 변동성
        returns = df['close'].pct_change().dropna()
        volatility = returns.std() * np.sqrt(252) * 100
        if volatility < 30:
            score += 25
        elif volatility < 40:
            score += 15
        
        # 수익성
        if len(df) >= 60:
            yoy = (latest['close'] - df['close'].iloc[-60]) / df['close'].iloc[-60] * 100
            if yoy > 10:
                score += 25
            elif yoy > 0:
                score += 15
        
        return {
            'score': score,
            'volatility': volatility,
            'yoy_return': yoy if len(df) >= 60 else 0,
            'atr': latest['atr']
        }
    
    def calculate_nps_score(self, df: pd.DataFrame) -> Dict:
        """NPS 점수 계산"""
        latest = df.iloc[-1]
        
        score = 0
        
        # 추세
        if latest['close'] > latest['ema20']:
            score += 25
        if latest['ema20'] > df['ema60'].iloc[-1]:
            score += 15
        
        # RSI
        if 45 <= latest['rsi'] <= 65:
            score += 30
        elif 40 <= latest['rsi'] < 45:
            score += 20
        
        # 거래량
        avg_vol = df['volume'].rolling(20).mean().iloc[-1]
        if avg_vol > 0 and latest['volume'] / avg_vol > 1.2:
            score += 30
        elif avg_vol > 0 and latest['volume'] / avg_vol > 1.0:
            score += 20
        
        return {
            'score': score,
            'rsi': latest['rsi'],
            'volume_ratio': latest['volume'] / avg_vol if avg_vol > 0 else 0,
            'atr': latest['atr']
        }
    
    def calculate_atr_targets(self, current_price: float, atr: float, rr: float = 2.0) -> Dict:
        """ATR 기반 목표가/손절가 계산"""
        sl_multiplier = 1.5
        tp_multiplier = sl_multiplier * rr
        
        stop_loss = current_price - (atr * sl_multiplier)
        target_price = current_price + (atr * tp_multiplier)
        
        return {
            'entry': current_price,
            'stop_loss': stop_loss,
            'target': target_price,
            'rr_ratio': rr,
            'atr': atr
        }
    
    def scan(self) -> Dict:
        """전체 스캔 실행"""
        print("=" * 70)
        print("🔍 통합 멀티 전략 스캐너")
        print("=" * 70)
        print(f"대상 종목: {len(self.symbols)}개")
        print("-" * 70)
        
        for i, symbol in enumerate(self.symbols, 1):
            if i % 10 == 0:
                print(f"   진행: {i}/{len(self.symbols)}")
            
            df = self.fetch_data(symbol)
            if df.empty:
                continue
            
            df = self.calculate_indicators(df)
            latest = df.iloc[-1]
            current_price = latest['close']
            
            # V-Strategy
            v_result = self.calculate_v_score(df)
            if v_result['score'] >= 60:
                targets = self.calculate_atr_targets(current_price, v_result['atr'])
                self.results['V'].append({
                    'symbol': symbol,
                    'name': self._get_name(symbol),
                    'score': v_result['score'],
                    'current_price': current_price,
                    'target_price': targets['target'],
                    'stop_loss': targets['stop_loss'],
                    'rr_ratio': targets['rr_ratio'],
                    'atr': v_result['atr'],
                    'fib_level': v_result['fib_level'],
                    'strategy': 'V-Strategy'
                })
            
            # B01
            b01_result = self.calculate_b01_score(df)
            if b01_result['score'] >= 60:
                targets = self.calculate_atr_targets(current_price, b01_result['atr'])
                self.results['B01'].append({
                    'symbol': symbol,
                    'name': self._get_name(symbol),
                    'score': b01_result['score'],
                    'current_price': current_price,
                    'target_price': targets['target'],
                    'stop_loss': targets['stop_loss'],
                    'rr_ratio': targets['rr_ratio'],
                    'atr': b01_result['atr'],
                    'volatility': b01_result['volatility'],
                    'strategy': 'B01'
                })
            
            # NPS
            nps_result = self.calculate_nps_score(df)
            if nps_result['score'] >= 60:
                targets = self.calculate_atr_targets(current_price, nps_result['atr'])
                self.results['NPS'].append({
                    'symbol': symbol,
                    'name': self._get_name(symbol),
                    'score': nps_result['score'],
                    'current_price': current_price,
                    'target_price': targets['target'],
                    'stop_loss': targets['stop_loss'],
                    'rr_ratio': targets['rr_ratio'],
                    'atr': nps_result['atr'],
                    'rsi': nps_result['rsi'],
                    'strategy': 'NPS'
                })
            
            # Multi-Strategy (평균 점수)
            multi_score = (v_result['score'] + b01_result['score'] + nps_result['score']) / 3
            if multi_score >= 55:
                targets = self.calculate_atr_targets(current_price, latest['atr'])
                self.results['Multi'].append({
                    'symbol': symbol,
                    'name': self._get_name(symbol),
                    'score': multi_score,
                    'v_score': v_result['score'],
                    'b01_score': b01_result['score'],
                    'nps_score': nps_result['score'],
                    'current_price': current_price,
                    'target_price': targets['target'],
                    'stop_loss': targets['stop_loss'],
                    'rr_ratio': targets['rr_ratio'],
                    'atr': latest['atr'],
                    'strategy': 'Multi'
                })
        
        # 정렬
        for key in self.results:
            self.results[key].sort(key=lambda x: x['score'], reverse=True)
        
        return self.results
    
    def _get_name(self, symbol: str) -> str:
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
            '055550': '신한지주', '047050': '포스코DX', '032640': 'LG유플러스',
        }
        return names.get(symbol, symbol)
    
    def save_results(self):
        """결과 저장"""
        output_dir = Path('./reports/multi_strategy')
        output_dir.mkdir(parents=True, exist_ok=True)
        
        for strategy, stocks in self.results.items():
            output_file = output_dir / f'{strategy.lower()}_scan_20260320.json'
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump({
                    'scan_date': '2026-03-20',
                    'strategy': strategy,
                    'selected_count': len(stocks),
                    'stocks': stocks
                }, f, ensure_ascii=False, indent=2, default=str)
        
        print(f"\n💾 결과 저장 완료")
        print(f"   V-Strategy: {len(self.results['V'])}개")
        print(f"   B01: {len(self.results['B01'])}개")
        print(f"   NPS: {len(self.results['NPS'])}개")
        print(f"   Multi: {len(self.results['Multi'])}개")


def main():
    scanner = IntegratedMultiStrategyScanner()
    results = scanner.scan()
    scanner.save_results()
    
    print("\n" + "=" * 70)
    print("📊 스캔 완료 요약")
    print("=" * 70)
    for strategy, stocks in results.items():
        print(f"   {strategy}: {len(stocks)}개 종목")
        if stocks:
            print(f"      TOP: {stocks[0]['name']} ({stocks[0]['score']:.1f}점)")


if __name__ == '__main__':
    main()
