"""
V2 Core - Technical Indicators
공통 기술적 지표 모듈
"""
import pandas as pd
import numpy as np
from typing import Optional


class Indicators:
    """기술적 지표 계산 클래스"""
    
    @staticmethod
    def ma(series: pd.Series, period: int) -> pd.Series:
        """이동평균"""
        return series.rolling(window=period, min_periods=1).mean()
    
    @staticmethod
    def ema(series: pd.Series, period: int) -> pd.Series:
        """지수이동평균"""
        return series.ewm(span=period, adjust=False, min_periods=1).mean()
    
    @staticmethod
    def rsi(prices: pd.Series, period: int = 14) -> pd.Series:
        """RSI 계산"""
        delta = prices.diff()
        gain = delta.where(delta > 0, 0)
        loss = -delta.where(delta < 0, 0)
        
        avg_gain = gain.ewm(span=period, adjust=False, min_periods=1).mean()
        avg_loss = loss.ewm(span=period, adjust=False, min_periods=1).mean()
        
        rs = avg_gain / avg_loss.replace(0, np.nan)
        rsi = 100 - (100 / (1 + rs))
        return rsi.fillna(50)
    
    @staticmethod
    def adx(df: pd.DataFrame, period: int = 14) -> pd.Series:
        """ADX 계산"""
        df = df.copy()
        
        # True Range
        df['tr1'] = df['high'] - df['low']
        df['tr2'] = abs(df['high'] - df['close'].shift(1))
        df['tr3'] = abs(df['low'] - df['close'].shift(1))
        df['tr'] = df[['tr1', 'tr2', 'tr3']].max(axis=1)
        
        # Directional Movement
        df['plus_dm'] = np.where(
            (df['high'] - df['high'].shift(1)) > (df['low'].shift(1) - df['low']),
            np.maximum(df['high'] - df['high'].shift(1), 0),
            0
        )
        df['minus_dm'] = np.where(
            (df['low'].shift(1) - df['low']) > (df['high'] - df['high'].shift(1)),
            np.maximum(df['low'].shift(1) - df['low'], 0),
            0
        )
        
        # Smoothed
        df['atr'] = Indicators.ema(df['tr'], period)
        df['plus_di'] = 100 * Indicators.ema(df['plus_dm'], period) / df['atr'].replace(0, np.nan)
        df['minus_di'] = 100 * Indicators.ema(df['minus_dm'], period) / df['atr'].replace(0, np.nan)
        
        # DX and ADX
        df['dx'] = 100 * abs(df['plus_di'] - df['minus_di']) / (df['plus_di'] + df['minus_di']).replace(0, np.nan)
        df['adx'] = Indicators.ema(df['dx'], period)
        
        return df['adx'].fillna(0)
    
    @staticmethod
    def atr(df: pd.DataFrame, period: int = 14) -> pd.Series:
        """ATR (Average True Range)"""
        tr1 = df['high'] - df['low']
        tr2 = abs(df['high'] - df['close'].shift(1))
        tr3 = abs(df['low'] - df['close'].shift(1))
        tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
        return Indicators.ema(tr, period)
    
    @staticmethod
    def bollinger_bands(series: pd.Series, period: int = 20, std: int = 2):
        """볼린저 밴드"""
        ma = Indicators.ma(series, period)
        std_dev = series.rolling(window=period, min_periods=1).std()
        upper = ma + (std * std_dev)
        lower = ma - (std * std_dev)
        return upper, ma, lower
    
    @staticmethod
    def macd(series: pd.Series, fast: int = 12, slow: int = 26, signal: int = 9):
        """MACD"""
        fast_ema = Indicators.ema(series, fast)
        slow_ema = Indicators.ema(series, slow)
        macd_line = fast_ema - slow_ema
        signal_line = Indicators.ema(macd_line, signal)
        histogram = macd_line - signal_line
        return macd_line, signal_line, histogram
    
    @staticmethod
    def volume_ratio(volume: pd.Series, period: int = 20) -> pd.Series:
        """거래량 비율 (현재 / 평균)"""
        avg_volume = Indicators.ma(volume, period)
        return volume / avg_volume.replace(0, np.nan)
