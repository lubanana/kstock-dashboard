#!/usr/bin/env python3
"""
KStock Data Loader - 내가 쉽게 활용할 수 있는 데이터 로더
"""

import json
import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, Optional, List


class KStockData:
    """KStock 데이터 관리자"""
    
    BASE_PATH = '/home/programs/kstock_analyzer'
    
    def __init__(self):
        self.index = self._load_index()
        self._kospi_cache = None
        self._kosdaq_cache = None
    
    def _load_index(self) -> dict:
        """데이터 인덱스 로드"""
        try:
            with open(f'{self.BASE_PATH}/market_data_index.json', 'r') as f:
                return json.load(f)
        except:
            return {}
    
    # ========== KOSPI ==========
    def kospi(self, days: int = 30) -> pd.DataFrame:
        """KOSPI 데이터 로드"""
        if self._kospi_cache is None:
            df = pd.read_csv(f'{self.BASE_PATH}/data/kospi_history.csv', skiprows=2)
            df.columns = ['Date', 'Close', 'High', 'Low', 'Open', 'Volume']
            df['Date'] = pd.to_datetime(df['Date'])
            df = df.set_index('Date').sort_index()
            for col in ['Close', 'High', 'Low', 'Open', 'Volume']:
                df[col] = pd.to_numeric(df[col], errors='coerce')
            self._kospi_cache = df
        return self._kospi_cache.tail(days)
    
    def kospi_summary(self) -> dict:
        """KOSPI 요약 정보"""
        idx = self.index.get('indices', {}).get('kospi', {})
        return {
            'price': idx.get('last_price'),
            'change_pct': idx.get('change_percent'),
            'trend': idx.get('trend'),
            'rsi': idx.get('rsi'),
            'alert': idx.get('alert')
        }
    
    def kospi_signal(self) -> str:
        """KOSPI 매매 신호"""
        summary = self.kospi_summary()
        rsi = summary.get('rsi', 50)
        trend = summary.get('trend', 'NEUTRAL')
        
        if rsi > 80 and trend == 'BULLISH':
            return 'CAUTION: 과매수, 익절 고려'
        elif rsi < 30 and trend == 'BEARISH':
            return 'OPPORTUNITY: 과매도, 매수 고려'
        elif trend == 'BULLISH':
            return 'HOLD: 상승 추세 유지'
        else:
            return 'NEUTRAL: 관망'
    
    # ========== KOSDAQ ==========
    def kosdaq(self, days: int = 30) -> pd.DataFrame:
        """KOSDAQ 데이터 로드"""
        if self._kosdaq_cache is None:
            df = pd.read_csv(f'{self.BASE_PATH}/data/kosdaq_history.csv', skiprows=2)
            df.columns = ['Date', 'Close', 'High', 'Low', 'Open', 'Volume']
            df['Date'] = pd.to_datetime(df['Date'])
            df = df.set_index('Date').sort_index()
            for col in ['Close', 'High', 'Low', 'Open', 'Volume']:
                df[col] = pd.to_numeric(df[col], errors='coerce')
            self._kosdaq_cache = df
        return self._kosdaq_cache.tail(days)
    
    # ========== 개별 종목 ==========
    def stock(self, name: str) -> Optional[pd.DataFrame]:
        """개별 종목 데이터 로드"""
        stock_map = {
            'samsung': 'samsung.csv',
            'skhynix': 'skhynix.csv',
            '삼성전자': 'samsung.csv',
            'SK하이닉스': 'skhynix.csv'
        }
        
        filename = stock_map.get(name.lower())
        if not filename:
            return None
        
        try:
            df = pd.read_csv(f'{self.BASE_PATH}/data/{filename}', skiprows=2)
            df.columns = ['Date', 'Close', 'High', 'Low', 'Open', 'Volume']
            df['Date'] = pd.to_datetime(df['Date'])
            df = df.set_index('Date').sort_index()
            for col in ['Close', 'High', 'Low', 'Open', 'Volume']:
                df[col] = pd.to_numeric(df[col], errors='coerce')
            return df
        except:
            return None
    
    # ========== 유틸리티 ==========
    def is_bullish(self, symbol: str = 'kospi') -> bool:
        """상승 추세 여부 확인"""
        if symbol == 'kospi':
            summary = self.kospi_summary()
            return summary.get('trend') == 'BULLISH'
        return False
    
    def is_overbought(self, symbol: str = 'kospi') -> bool:
        """과매수 여부 확인"""
        if symbol == 'kospi':
            summary = self.kospi_summary()
            rsi = summary.get('rsi', 50)
            return rsi > 70
        return False
    
    def market_status(self) -> str:
        """시장 상태 한줄 요약"""
        summary = self.kospi_summary()
        price = summary.get('price', 0)
        change = summary.get('change_pct', 0)
        trend = summary.get('trend', 'NEUTRAL')
        alert = summary.get('alert', '')
        
        status = f"KOSPI: {price:,.0f} ({change:+.2f}%) | {trend}"
        if alert:
            status += f" | {alert}"
        return status
    
    def refresh(self):
        """데이터 새로고침"""
        self.index = self._load_index()
        self._kospi_cache = None
        self._kosdaq_cache = None


# 전역 인스턴스 (바로 사용 가능)
data = KStockData()


# 간단한 사용 예시
if __name__ == "__main__":
    print("📊 KStock 데이터 로더 테스트\n")
    
    # 시장 상태
    print(data.market_status())
    print()
    
    # KOSPI 최근 5일
    print("📈 KOSPI 최근 5일:")
    print(data.kospi(5)[['Close', 'Volume']])
    print()
    
    # 매매 신호
    print(f"🎯 신호: {data.kospi_signal()}")
    print()
    
    # 삼성전자
    samsung = data.stock('samsung')
    if samsung is not None:
        print(f"📱 삼성전자 최근 종가: {samsung['Close'].iloc[-1]:,.0f}")
