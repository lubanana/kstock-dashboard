#!/usr/bin/env python3
"""
KStock Data Collector with PyKRX
PyKRX를 활용한 한국 주식 데이터 수집기
- PER, PBR, 배당수익률 등 가치 지표
- RSI, 볼린저밴드 등 기술적 지표
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
import json
import os

# PyKRX 임포트
try:
    from pykrx import stock
    PYKRX_AVAILABLE = True
    print("✅ PyKRX loaded successfully")
except ImportError:
    print("⚠️  PyKRX not available")
    PYKRX_AVAILABLE = False

# yfinance 임포트 (기술적 지표용)
try:
    import yfinance as yf
    YF_AVAILABLE = True
except ImportError:
    YF_AVAILABLE = False


class KStockDataCollector:
    """KStock 데이터 수집기"""
    
    def __init__(self):
        self.pykrx_available = PYKRX_AVAILABLE
        self.yf_available = YF_AVAILABLE
        self.cache_dir = '/home/programs/kstock_analyzer/data/cache'
        os.makedirs(self.cache_dir, exist_ok=True)
    
    def get_fundamental_data(self, ticker: str) -> Dict:
        """
        PyKRX로 기본적 분석 데이터 수집
        - PER, PBR, EPS, BPS, 배당수익률
        """
        if not self.pykrx_available:
            return {'error': 'PyKRX not available'}
        
        try:
            # 티커에서 코드 추출 (005930.KS → 005930)
            code = ticker.replace('.KS', '').replace('.KQ', '')
            
            # 최근 거래일 찾기
            today = datetime.now()
            for i in range(7):  # 최근 7일 내 거래일 찾기
                date_str = (today - timedelta(days=i)).strftime('%Y%m%d')
                try:
                    df_ratio = stock.get_market_fundamental_by_ticker(date_str)
                    if not df_ratio.empty and code in df_ratio.index:
                        break
                except:
                    continue
            
            if code not in df_ratio.index:
                return {'error': f'No fundamental data for {ticker}'}
            
            row = df_ratio.loc[code]
            
            result = {
                'ticker': ticker,
                'date': date_str,
                'per': float(row.get('PER', 0)) if pd.notna(row.get('PER')) else None,
                'pbr': float(row.get('PBR', 0)) if pd.notna(row.get('PBR')) else None,
                'eps': float(row.get('EPS', 0)) if pd.notna(row.get('EPS')) else None,
                'bps': float(row.get('BPS', 0)) if pd.notna(row.get('BPS')) else None,
                'dividend_yield': float(row.get('DIV', 0)) if pd.notna(row.get('DIV')) else 0,
                'data_source': 'PyKRX'
            }
            
            return result
            
        except Exception as e:
            return {'error': str(e), 'ticker': ticker}
    
    def get_ohlcv_data(self, ticker: str, days: int = 100) -> pd.DataFrame:
        """
        PyKRX로 OHLCV 데이터 수집
        """
        if not self.pykrx_available:
            return pd.DataFrame()
        
        try:
            code = ticker.replace('.KS', '').replace('.KQ', '')
            
            # 날짜 범위 계산
            end_date = datetime.now()
            start_date = end_date - timedelta(days=days)
            
            # OHLCV 데이터
            df = stock.get_market_ohlcv_by_date(
                fromdate=start_date.strftime('%Y%m%d'),
                todate=end_date.strftime('%Y%m%d'),
                ticker=code
            )
            
            return df
            
        except Exception as e:
            print(f"Error fetching OHLCV for {ticker}: {e}")
            return pd.DataFrame()
    
    def calculate_technical_indicators(self, df: pd.DataFrame) -> Dict:
        """
        기술적 지표 계산
        - RSI, 볼린저밴드, MACD, 이동평균선
        """
        if df.empty or len(df) < 20:
            return {'error': 'Insufficient data'}
        
        try:
            close = df['종가'] if '종가' in df.columns else df['Close']
            high = df['고가'] if '고가' in df.columns else df['High']
            low = df['저가'] if '저가' in df.columns else df['Low']
            volume = df['거래량'] if '거래량' in df.columns else df['Volume']
            
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
            bb_width = (bb_upper - bb_lower) / ma20 * 100
            bb_position = (close - bb_lower) / (bb_upper - bb_lower)
            
            # 3. MACD
            ema12 = close.ewm(span=12).mean()
            ema26 = close.ewm(span=26).mean()
            macd = ema12 - ema26
            macd_signal = macd.ewm(span=9).mean()
            macd_hist = macd - macd_signal
            
            # 4. 이동평균선
            ma5 = close.rolling(window=5).mean()
            ma20 = close.rolling(window=20).mean()
            ma60 = close.rolling(window=60).mean()
            
            # 5. 거래량 지표
            vol_ma20 = volume.rolling(window=20).mean()
            vol_ratio = volume / vol_ma20
            
            # 최신값 추출 (numpy 타입을 Python 타입으로 변환)
            latest = {
                'rsi': float(rsi.iloc[-1]),
                'rsi_signal': '과매수' if rsi.iloc[-1] > 70 else '과매도' if rsi.iloc[-1] < 30 else '중립',
                
                'bb_upper': float(bb_upper.iloc[-1]),
                'bb_lower': float(bb_lower.iloc[-1]),
                'bb_width': float(bb_width.iloc[-1]),
                'bb_position': float(bb_position.iloc[-1]),
                'bb_signal': '상단돌파' if close.iloc[-1] > bb_upper.iloc[-1] else '하단이탈' if close.iloc[-1] < bb_lower.iloc[-1] else '밴드내',
                
                'macd': float(macd.iloc[-1]),
                'macd_signal': float(macd_signal.iloc[-1]),
                'macd_hist': float(macd_hist.iloc[-1]),
                'macd_trend': '골든크로스' if macd.iloc[-1] > macd_signal.iloc[-1] else '데드크로스',
                
                'ma5': float(ma5.iloc[-1]),
                'ma20': float(ma20.iloc[-1]),
                'ma60': float(ma60.iloc[-1]),
                'ma_trend': '정배열' if ma5.iloc[-1] > ma20.iloc[-1] > ma60.iloc[-1] else '역배열' if ma5.iloc[-1] < ma20.iloc[-1] < ma60.iloc[-1] else '혼조',
                
                'volume_ratio': float(vol_ratio.iloc[-1]),
                'current_price': float(close.iloc[-1]),
            }
            
            return latest
            
        except Exception as e:
            return {'error': str(e)}
    
    def get_stock_list(self, market: str = 'KOSPI') -> List[Dict]:
        """
        PyKRX로 종목 리스트 조회
        """
        if not self.pykrx_available:
            return []
        
        try:
            if market == 'KOSPI':
                df = stock.get_market_ticker_list(market="KOSPI")
            else:
                df = stock.get_market_ticker_list(market="KOSDAQ")
            
            stocks = []
            for code in df[:100]:  # 상위 100개
                name = stock.get_market_ticker_name(code)
                stocks.append({
                    'code': code,
                    'name': name,
                    'symbol': f"{code}.KS",
                    'market': market
                })
            
            return stocks
            
        except Exception as e:
            print(f"Error fetching stock list: {e}")
            return []
    
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
        
        # 1. 기본적 분석 데이터
        print("   📈 Fundamental data (PER, PBR, Dividend)...")
        fundamental = self.get_fundamental_data(ticker)
        result['fundamental'] = fundamental
        
        if 'error' not in fundamental:
            print(f"      PER: {fundamental.get('per')}, PBR: {fundamental.get('pbr')}, DIV: {fundamental.get('dividend_yield')}%")
        
        # 2. OHLCV 데이터
        print("   📊 OHLCV data...")
        ohlcv = self.get_ohlcv_data(ticker, days=100)
        
        # 3. 기술적 지표
        if not ohlcv.empty:
            print("   🔧 Technical indicators (RSI, Bollinger, MACD)...")
            technical = self.calculate_technical_indicators(ohlcv)
            result['technical'] = technical
            
            if 'error' not in technical:
                print(f"      RSI: {technical.get('rsi')} ({technical.get('rsi_signal')})")
                print(f"      BB Position: {technical.get('bb_position'):.2f}")
                print(f"      MACD: {technical.get('macd_trend')}")
                print(f"      MA Trend: {technical.get('ma_trend')}")
        
        return result


def main():
    """테스트 실행"""
    print("=" * 70)
    print("🚀 KStock Data Collector with PyKRX")
    print("=" * 70)
    
    collector = KStockDataCollector()
    
    if not collector.pykrx_available:
        print("❌ PyKRX not available")
        return
    
    # 테스트 종목
    test_stocks = ['005930.KS', '000660.KS', '035720.KS']
    
    results = []
    for ticker in test_stocks:
        data = collector.collect_all_data(ticker)
        results.append(data)
    
    # 결과 저장
    output_file = f'/home/programs/kstock_analyzer/data/pykrx_test_{datetime.now().strftime("%Y%m%d_%H%M")}.json'
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
        print(f"\n{r['ticker']}:")
        print(f"   PER: {fund.get('per')}, PBR: {fund.get('pbr')}, DIV: {fund.get('dividend_yield')}%")
        print(f"   RSI: {tech.get('rsi')}, BB: {tech.get('bb_signal')}, MACD: {tech.get('macd_trend')}")


if __name__ == '__main__':
    main()
