#!/usr/bin/env python3
"""
Technical Analysis Module
기술적 지표 계산 및 분석
"""

import pandas as pd
import numpy as np


class TechnicalAnalyzer:
    """기술적 분석 엔진"""
    
    @staticmethod
    def add_moving_averages(df: pd.DataFrame, 
                           periods: list = [5, 20, 60, 120]) -> pd.DataFrame:
        """이동평균선 추가"""
        df = df.copy()
        for period in periods:
            df[f'MA{period}'] = df['Close'].rolling(window=period).mean()
        return df
    
    @staticmethod
    def add_rsi(df: pd.DataFrame, period: int = 14) -> pd.DataFrame:
        """RSI 계산"""
        df = df.copy()
        delta = df['Close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
        rs = gain / loss
        df['RSI'] = 100 - (100 / (1 + rs))
        return df
    
    @staticmethod
    def add_macd(df: pd.DataFrame, 
                 fast: int = 12, 
                 slow: int = 26, 
                 signal: int = 9) -> pd.DataFrame:
        """MACD 계산"""
        df = df.copy()
        ema_fast = df['Close'].ewm(span=fast).mean()
        ema_slow = df['Close'].ewm(span=slow).mean()
        df['MACD'] = ema_fast - ema_slow
        df['MACD_Signal'] = df['MACD'].ewm(span=signal).mean()
        df['MACD_Hist'] = df['MACD'] - df['MACD_Signal']
        return df
    
    @staticmethod
    def add_bollinger_bands(df: pd.DataFrame, 
                           period: int = 20, 
                           std: int = 2) -> pd.DataFrame:
        """볼린저밴드 계산"""
        df = df.copy()
        df['BB_Middle'] = df['Close'].rolling(window=period).mean()
        bb_std = df['Close'].rolling(window=period).std()
        df['BB_Upper'] = df['BB_Middle'] + (bb_std * std)
        df['BB_Lower'] = df['BB_Middle'] - (bb_std * std)
        df['BB_Position'] = (df['Close'] - df['BB_Lower']) / (df['BB_Upper'] - df['BB_Lower'])
        return df
    
    def full_analysis(self, df: pd.DataFrame) -> pd.DataFrame:
        """전체 기술적 분석"""
        df = self.add_moving_averages(df)
        df = self.add_rsi(df)
        df = self.add_macd(df)
        df = self.add_bollinger_bands(df)
        return df
    
    @staticmethod
    def generate_signals(df: pd.DataFrame) -> dict:
        """매매 신호 생성"""
        latest = df.iloc[-1]
        prev = df.iloc[-2] if len(df) > 1 else latest
        signals = {}
        
        # 추세 판단
        if latest['Close'] > latest.get('MA20', 0) > latest.get('MA60', 0):
            signals['trend'] = 'BULLISH 📈'
        elif latest['Close'] < latest.get('MA20', 999999999) < latest.get('MA60', 0):
            signals['trend'] = 'BEARISH 📉'
        else:
            signals['trend'] = 'NEUTRAL ➡️'
        
        # RSI 신호
        rsi = latest.get('RSI', 50)
        if rsi > 70:
            signals['rsi_signal'] = 'OVERBOUGHT ⚠️'
        elif rsi < 30:
            signals['rsi_signal'] = 'OVERSOLD ✅'
        else:
            signals['rsi_signal'] = 'NEUTRAL'
        
        # MACD 신호
        macd = latest.get('MACD', 0)
        macd_signal = latest.get('MACD_Signal', 0)
        prev_macd = prev.get('MACD', 0)
        prev_signal = prev.get('MACD_Signal', 0)
        
        if macd > macd_signal and prev_macd <= prev_signal:
            signals['macd_signal'] = 'GOLDEN_CROSS 🌟'
        elif macd < macd_signal and prev_macd >= prev_signal:
            signals['macd_signal'] = 'DEAD_CROSS 💀'
        else:
            signals['macd_signal'] = 'NEUTRAL'
        
        # 종합 신호
        score = 0
        if 'BULLISH' in signals['trend']: score += 1
        if 'OVERSOLD' in signals['rsi_signal']: score += 1
        if 'GOLDEN_CROSS' in signals['macd_signal']: score += 1
        if 'BEARISH' in signals['trend']: score -= 1
        if 'OVERBOUGHT' in signals['rsi_signal']: score -= 1
        if 'DEAD_CROSS' in signals['macd_signal']: score -= 1
        
        if score >= 2:
            signals['overall'] = 'BUY 🟢'
        elif score <= -2:
            signals['overall'] = 'SELL 🔴'
        else:
            signals['overall'] = 'HOLD 🟡'
        
        return signals


if __name__ == "__main__":
    # 테스트
    import sys
    sys.path.append('/home/programs/kstock_analyzer')
    from data.fetcher import StockDataFetcher
    
    fetcher = StockDataFetcher()
    analyzer = TechnicalAnalyzer()
    
    df = fetcher.get_price('005930', period=60)
    df = analyzer.full_analysis(df)
    signals = analyzer.generate_signals(df)
    
    print("\n🎯 신호:")
    for k, v in signals.items():
        print(f"  {k}: {v}")
