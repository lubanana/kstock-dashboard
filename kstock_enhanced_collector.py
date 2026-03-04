#!/usr/bin/env python3
"""
KStock Data Collector - Enhanced Version
PyKRX + yfinance 활용한 한국 주식 데이터 수집기
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import json
import os

# yfinance 임포트
try:
    import yfinance as yf
    YF_AVAILABLE = True
    print("✅ yfinance loaded")
except ImportError:
    YF_AVAILABLE = False
    print("⚠️  yfinance not available")

# PyKRX 임포트 (기술적 지표용)
try:
    from pykrx import stock
    PYKRX_AVAILABLE = True
    print("✅ PyKRX loaded")
except ImportError:
    PYKRX_AVAILABLE = False
    print("⚠️  PyKRX not available")


class KStockDataCollector:
    """KStock 데이터 수집기"""
    
    def __init__(self):
        self.yf_available = YF_AVAILABLE
        self.pykrx_available = PYKRX_AVAILABLE
        self.data_dir = '/home/programs/kstock_analyzer/data'
        os.makedirs(self.data_dir, exist_ok=True)
    
    def get_stock_info_yf(self, ticker: str) -> Dict:
        """
        yfinance로 종목 정보 수집
        """
        if not self.yf_available:
            return {'error': 'yfinance not available'}
        
        try:
            stock = yf.Ticker(ticker)
            info = stock.info
            
            return {
                'ticker': ticker,
                'name': info.get('longName', ''),
                'sector': info.get('sector', ''),
                'industry': info.get('industry', ''),
                'market_cap': info.get('marketCap', 0),
                'per': info.get('trailingPE', None),
                'forward_per': info.get('forwardPE', None),
                'pbr': info.get('priceToBook', None),
                'eps': info.get('trailingEps', None),
                'dividend_yield': info.get('dividendYield', 0) * 100 if info.get('dividendYield') else 0,
                '52w_high': info.get('fiftyTwoWeekHigh', None),
                '52w_low': info.get('fiftyTwoWeekLow', None),
                'data_source': 'yfinance'
            }
            
        except Exception as e:
            return {'error': str(e), 'ticker': ticker}
    
    def get_ohlcv_yf(self, ticker: str, days: int = 100) -> pd.DataFrame:
        """
        yfinance로 OHLCV 데이터 수집
        """
        if not self.yf_available:
            return pd.DataFrame()
        
        try:
            stock = yf.Ticker(ticker)
            df = stock.history(period=f'{days}d')
            return df
        except Exception as e:
            print(f"Error fetching OHLCV for {ticker}: {e}")
            return pd.DataFrame()
    
    def calculate_technical_indicators(self, df: pd.DataFrame) -> Dict:
        """
        기술적 지표 계산
        """
        if df.empty or len(df) < 20:
            return {'error': 'Insufficient data'}
        
        try:
            close = df['Close']
            high = df['High']
            low = df['Low']
            volume = df['Volume']
            
            # 1. RSI (14일)
            delta = close.diff()
            gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
            loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
            rs = gain / loss
            rsi = 100 - (100 / (1 + rs))
            
            # 2. 볼린저 밴드 (20일)
            ma20 = close.rolling(window=20).mean()
            std20 = close.rolling(window=20).std()
            bb_upper = ma20 + (std20 * 2)
            bb_lower = ma20 - (std20 * 2)
            bb_width = ((bb_upper - bb_lower) / ma20 * 100).fillna(0)
            bb_position = ((close - bb_lower) / (bb_upper - bb_lower)).fillna(0.5)
            
            # 3. MACD
            ema12 = close.ewm(span=12).mean()
            ema26 = close.ewm(span=26).mean()
            macd = ema12 - ema26
            macd_signal = macd.ewm(span=9).mean()
            macd_hist = macd - macd_signal
            
            # 4. 이동평균선
            ma5 = close.rolling(window=5).mean()
            ma20_line = close.rolling(window=20).mean()
            ma60 = close.rolling(window=60).mean()
            
            # 5. 거래량 지표
            vol_ma20 = volume.rolling(window=20).mean()
            vol_ratio = (volume / vol_ma20).fillna(1)
            
            # 최신값 추출
            latest = {
                'rsi': round(float(rsi.iloc[-1]), 2),
                'rsi_signal': '과매수' if rsi.iloc[-1] > 70 else '과매도' if rsi.iloc[-1] < 30 else '중립',
                
                'bb_upper': round(float(bb_upper.iloc[-1]), 2),
                'bb_lower': round(float(bb_lower.iloc[-1]), 2),
                'bb_width': round(float(bb_width.iloc[-1]), 2),
                'bb_position': round(float(bb_position.iloc[-1]), 2),
                'bb_signal': '상단돌파' if close.iloc[-1] > bb_upper.iloc[-1] else '하단이탈' if close.iloc[-1] < bb_lower.iloc[-1] else '밴드내',
                
                'macd': round(float(macd.iloc[-1]), 4),
                'macd_signal': round(float(macd_signal.iloc[-1]), 4),
                'macd_hist': round(float(macd_hist.iloc[-1]), 4),
                'macd_trend': '골든크로스' if macd.iloc[-1] > macd_signal.iloc[-1] else '데드크로스',
                
                'ma5': round(float(ma5.iloc[-1]), 2),
                'ma20': round(float(ma20_line.iloc[-1]), 2),
                'ma60': round(float(ma60.iloc[-1]), 2),
                'ma_trend': '정배열' if ma5.iloc[-1] > ma20_line.iloc[-1] > ma60.iloc[-1] else '역배열' if ma5.iloc[-1] < ma20_line.iloc[-1] < ma60.iloc[-1] else '혼조',
                
                'volume_ratio': round(float(vol_ratio.iloc[-1]), 2),
                'current_price': round(float(close.iloc[-1]), 2),
                'price_change_1d': round(float((close.iloc[-1] / close.iloc[-2] - 1) * 100), 2) if len(close) > 1 else 0,
                'price_change_5d': round(float((close.iloc[-1] / close.iloc[-5] - 1) * 100), 2) if len(close) > 5 else 0,
                'price_change_20d': round(float((close.iloc[-1] / close.iloc[-20] - 1) * 100), 2) if len(close) > 20 else 0,
            }
            
            return latest
            
        except Exception as e:
            return {'error': str(e)}
    
    def collect_all_data(self, ticker: str) -> Dict:
        """
        모든 데이터 수집
        """
        print(f"\n📊 Collecting data for {ticker}...")
        
        result = {
            'ticker': ticker,
            'timestamp': datetime.now().isoformat(),
            'fundamental': {},
            'technical': {},
            'status': 'success'
        }
        
        # 1. 기본적 분석 데이터 (yfinance)
        print("   📈 Fundamental data (PER, PBR, Dividend)...")
        fundamental = self.get_stock_info_yf(ticker)
        result['fundamental'] = fundamental
        
        if 'error' not in fundamental:
            print(f"      PER: {fundamental.get('per')}, PBR: {fundamental.get('pbr')}, DIV: {fundamental.get('dividend_yield', 0):.2f}%")
        
        # 2. OHLCV 데이터
        print("   📊 OHLCV data...")
        ohlcv = self.get_ohlcv_yf(ticker, days=100)
        
        # 3. 기술적 지표
        if not ohlcv.empty:
            print("   🔧 Technical indicators (RSI, Bollinger, MACD)...")
            technical = self.calculate_technical_indicators(ohlcv)
            result['technical'] = technical
            
            if 'error' not in technical:
                print(f"      RSI: {technical.get('rsi')} ({technical.get('rsi_signal')})")
                print(f"      BB Position: {technical.get('bb_position'):.2f} ({technical.get('bb_signal')})")
                print(f"      MACD: {technical.get('macd_trend')}")
                print(f"      MA Trend: {technical.get('ma_trend')}")
        
        return result


def main():
    """테스트 실행"""
    print("=" * 70)
    print("🚀 KStock Data Collector - Enhanced")
    print("=" * 70)
    
    collector = KStockDataCollector()
    
    # 테스트 종목
    test_stocks = ['005930.KS', '000660.KS', '035720.KS']
    
    results = []
    for ticker in test_stocks:
        data = collector.collect_all_data(ticker)
        results.append(data)
    
    # 결과 저장
    output_file = f'/home/programs/kstock_analyzer/data/enhanced_test_{datetime.now().strftime("%Y%m%d_%H%M")}.json'
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(results, f, indent=2, ensure_ascii=False)
    
    print(f"\n💾 Results saved: {output_file}")
    
    # 요약
    print("\n" + "=" * 70)
    print("📊 SUMMARY")
    print("=" * 70)
    for r in results:
        fund = r.get('fundamental', {})
        tech = r.get('technical', {})
        print(f"\n{r['ticker']} - {fund.get('name', '')}:")
        print(f"   Sector: {fund.get('sector')}")
        print(f"   PER: {fund.get('per')}, PBR: {fund.get('pbr')}, DIV: {fund.get('dividend_yield', 0):.2f}%")
        print(f"   RSI: {tech.get('rsi')}, BB: {tech.get('bb_signal')}, MACD: {tech.get('macd_trend')}")
        print(f"   MA: {tech.get('ma_trend')}, Price: {tech.get('current_price')}")


if __name__ == '__main__':
    main()
