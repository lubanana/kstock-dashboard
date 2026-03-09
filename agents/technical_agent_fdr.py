#!/usr/bin/env python3
"""
Technical Analysis Agent with FinanceDataReader
FDR 기반 기술적 분석 에이전트

Features:
- FinanceDataReader로 OHLCV 데이터 수집
- 이동평균, RSI, MACD 계산
- 한국 시장에 최적화
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, Optional

import FinanceDataReader as fdr


class TechnicalAnalysisAgentFDR:
    """FDR 기반 기술적 분석 에이전트"""
    
    def __init__(self, symbol: str, name: str):
        self.symbol = symbol
        self.name = name
        self.data = None
        
    def fetch_data(self, days: int = 120) -> Optional[pd.DataFrame]:
        """
        FDR로 가격 데이터 수집
        
        Returns:
            DataFrame with columns: Open, High, Low, Close, Volume, Change
        """
        try:
            end = datetime.now()
            start = end - timedelta(days=days)
            
            df = fdr.DataReader(
                self.symbol,
                start.strftime('%Y-%m-%d'),
                end.strftime('%Y-%m-%d')
            )
            
            if df is None or len(df) < 30:
                print(f"   ⚠️  Insufficient data for {self.symbol}")
                return None
            
            self.data = df
            return df
            
        except Exception as e:
            print(f"   ❌ FDR error for {self.symbol}: {e}")
            return None
    
    def calculate_ma(self, periods=[5, 20, 60]) -> Dict:
        """이동평균 계산"""
        if self.data is None:
            return {}
        
        mas = {}
        for period in periods:
            mas[f'MA{period}'] = self.data['Close'].rolling(period).mean().iloc[-1]
        return mas
    
    def calculate_rsi(self, period: int = 14) -> float:
        """RSI 계산"""
        if self.data is None or len(self.data) < period + 1:
            return 50.0
        
        delta = self.data['Close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
        
        rs = gain / loss
        rsi = 100 - (100 / (1 + rs))
        
        return rsi.iloc[-1] if not pd.isna(rsi.iloc[-1]) else 50.0
    
    def calculate_macd(self) -> Dict:
        """MACD 계산"""
        if self.data is None or len(self.data) < 35:
            return {'macd': 0, 'signal': 0, 'histogram': 0}
        
        exp1 = self.data['Close'].ewm(span=12, adjust=False).mean()
        exp2 = self.data['Close'].ewm(span=26, adjust=False).mean()
        macd = exp1 - exp2
        signal = macd.ewm(span=9, adjust=False).mean()
        histogram = macd - signal
        
        return {
            'macd': macd.iloc[-1],
            'signal': signal.iloc[-1],
            'histogram': histogram.iloc[-1]
        }
    
    def calculate_bollinger(self, period: int = 20) -> Dict:
        """볼린저 밴드 계산"""
        if self.data is None or len(self.data) < period:
            return {'upper': 0, 'middle': 0, 'lower': 0}
        
        middle = self.data['Close'].rolling(period).mean()
        std = self.data['Close'].rolling(period).std()
        
        upper = middle + (std * 2)
        lower = middle - (std * 2)
        
        return {
            'upper': upper.iloc[-1],
            'middle': middle.iloc[-1],
            'lower': lower.iloc[-1]
        }
    
    def analyze(self) -> Dict:
        """
        전체 기술적 분석 실행
        
        Returns:
            분석 결과 딕셔너리
        """
        # 데이터 수집
        df = self.fetch_data(days=120)
        if df is None:
            return {
                'total_score': 50,
                'recommendation': 'HOLD',
                'error': 'No data'
            }
        
        # 최신 가격 정보
        latest_price = df['Close'].iloc[-1]
        latest_change = df['Change'].iloc[-1] if 'Change' in df.columns else 0
        
        # 지표 계산
        ma = self.calculate_ma()
        rsi = self.calculate_rsi()
        macd = self.calculate_macd()
        bb = self.calculate_bollinger()
        
        # 점수 계산 (0-100)
        score = 50  # 기본값
        
        # 1. 이동평균 (30점)
        ma_score = 0
        if latest_price > ma.get('MA5', 0):
            ma_score += 10
        if latest_price > ma.get('MA20', 0):
            ma_score += 10
        if ma.get('MA5', 0) > ma.get('MA20', 0):
            ma_score += 10
        
        # 2. RSI (20점)
        rsi_score = 0
        if 30 <= rsi <= 70:
            rsi_score = 20
        elif rsi < 30:  # 과매도
            rsi_score = 15
        elif rsi > 70:  # 과매수
            rsi_score = 10
        
        # 3. MACD (20점)
        macd_score = 0
        if macd['histogram'] > 0:
            macd_score = 20
        elif macd['macd'] > macd['signal']:
            macd_score = 15
        
        # 4. 볼린저 밴드 (20점)
        bb_score = 0
        if latest_price < bb['lower']:  # 하단 돌파 (매수 신호)
            bb_score = 20
        elif latest_price > bb['upper']:  # 상단 돌파 (매도 신호)
            bb_score = 10
        else:
            bb_score = 15
        
        # 5. 추세 (10점)
        trend_score = 0
        if latest_change > 0:
            trend_score = 10
        
        total_score = ma_score + rsi_score + macd_score + bb_score + trend_score
        
        # 추천
        if total_score >= 70:
            recommendation = 'BUY'
        elif total_score >= 40:
            recommendation = 'HOLD'
        else:
            recommendation = 'SELL'
        
        return {
            'total_score': total_score,
            'recommendation': recommendation,
            'price': latest_price,
            'change_pct': latest_change,
            'indicators': {
                'ma': ma,
                'rsi': rsi,
                'macd': macd,
                'bollinger': bb
            },
            'breakdown': {
                'ma_score': ma_score,
                'rsi_score': rsi_score,
                'macd_score': macd_score,
                'bb_score': bb_score,
                'trend_score': trend_score
            }
        }


def test_agent():
    """테스트"""
    print("=" * 60)
    print("🧪 FDR Technical Analysis Agent Test")
    print("=" * 60)
    
    # 테스트 종목
    test_stocks = [
        ('005930', '삼성전자'),
        ('000660', 'SK하이닉스'),
        ('035420', 'NAVER')
    ]
    
    for code, name in test_stocks:
        print(f"\n📊 {name} ({code})")
        agent = TechnicalAnalysisAgentFDR(code, name)
        result = agent.analyze()
        
        print(f"   점수: {result['total_score']:.0f}pts")
        print(f"   추천: {result['recommendation']}")
        print(f"   현재가: {result.get('price', 0):,.0f}원")
        
        if 'indicators' in result:
            ind = result['indicators']
            print(f"   RSI: {ind['rsi']:.1f}")
            print(f"   MACD: {ind['macd']['histogram']:.2f}")
    
    print("\n" + "=" * 60)


if __name__ == '__main__':
    test_agent()
