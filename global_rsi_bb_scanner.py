#!/usr/bin/env python3
"""
RSI + 볼린저밴드 단타 전략 - 미국 주식 & 가상화폐 스캐너
동일 조건: RSI 20~40, BB 하단, 거래량 1.3배+
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import json
import sys

def calculate_rsi(prices, period=14):
    """RSI 계산"""
    delta = prices.diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
    rs = gain / loss
    return 100 - (100 / (1 + rs))

def calculate_bollinger(df, period=20, std_dev=2):
    """볼린저밴드 계산"""
    df['BB_Middle'] = df['Close'].rolling(window=period).mean()
    df['BB_Std'] = df['Close'].rolling(window=period).std()
    df['BB_Upper'] = df['BB_Middle'] + (df['BB_Std'] * std_dev)
    df['BB_Lower'] = df['BB_Middle'] - (df['BB_Std'] * std_dev)
    return df

def check_signal(df, rsi_lower=20, rsi_upper=40, volume_threshold=1.3):
    """매수 신호 체크"""
    if len(df) < 35:
        return False, None
    
    df = df.copy()
    
    # RSI
    df['RSI'] = calculate_rsi(df['Close'], 14)
    
    # 볼린저밴드
    df = calculate_bollinger(df, 20, 2)
    
    # 거래량
    df['Volume_MA'] = df['Volume'].rolling(window=20).mean()
    df['Volume_Ratio'] = df['Volume'] / df['Volume_MA']
    
    latest = df.iloc[-1]
    
    signal = {
        'rsi': latest['RSI'],
        'price': latest['Close'],
        'bb_lower': latest['BB_Lower'],
        'bb_upper': latest['BB_Upper'],
        'volume_ratio': latest['Volume_Ratio'],
        'is_bullish': latest['Close'] > latest['Open'],
        'date': df.index[-1].strftime('%Y-%m-%d %H:%M') if hasattr(df.index[-1], 'strftime') else str(df.index[-1])
    }
    
    # 매수 조건
    is_signal = (
        rsi_lower <= latest['RSI'] <= rsi_upper and
        latest['Close'] <= latest['BB_Lower'] * 1.02 and
        latest['Volume_Ratio'] >= volume_threshold and
        latest['Close'] > latest['Open']  # 양봉
    )
    
    return is_signal, signal


class USStockScanner:
    """미국 주식 스캐너 (yfinance 사용)"""
    
    def __init__(self):
        self.watchlist = [
            # 대형 기술주
            {'symbol': 'AAPL', 'name': 'Apple'},
            {'symbol': 'MSFT', 'name': 'Microsoft'},
            {'symbol': 'GOOGL', 'name': 'Alphabet'},
            {'symbol': 'AMZN', 'name': 'Amazon'},
            {'symbol': 'META', 'name': 'Meta'},
            {'symbol': 'TSLA', 'name': 'Tesla'},
            {'symbol': 'NVDA', 'name': 'NVIDIA'},
            {'symbol': 'AMD', 'name': 'AMD'},
            {'symbol': 'INTC', 'name': 'Intel'},
            {'symbol': 'NFLX', 'name': 'Netflix'},
            # 금융
            {'symbol': 'JPM', 'name': 'JPMorgan'},
            {'symbol': 'BAC', 'name': 'Bank of America'},
            {'symbol': 'GS', 'name': 'Goldman Sachs'},
            # ETF
            {'symbol': 'SPY', 'name': 'S&P 500 ETF'},
            {'symbol': 'QQQ', 'name': 'Nasdaq 100 ETF'},
            {'symbol': 'IWM', 'name': 'Russell 2000 ETF'},
            {'symbol': 'VIX', 'name': 'Volatility Index'},
            # 기타
            {'symbol': 'COIN', 'name': 'Coinbase'},
            {'symbol': 'MSTR', 'name': 'MicroStrategy'},
            {'symbol': 'PLTR', 'name': 'Palantir'},
            {'symbol': 'ARKK', 'name': 'ARK Innovation ETF'},
        ]
    
    def get_data(self, symbol, days=60):
        """yfinance로 데이터 조회"""
        try:
            import yfinance as yf
            end = datetime.now()
            start = end - timedelta(days=days)
            df = yf.download(symbol, start=start, end=end, progress=False)
            if len(df) < 35:
                return None
            # 컬럼명 정리
            df.columns = ['Close', 'High', 'Low', 'Open', 'Volume'] if len(df.columns) == 5 else df.columns
            return df
        except Exception as e:
            return None
    
    def scan(self):
        """스캔 실행"""
        print("="*70)
        print("📊 미국 주식 RSI+BB 스캔")
        print(f"   기준: RSI 20~40, BB 하단, 거래량 1.3배+")
        print(f"   대상: {len(self.watchlist)}개 종목")
        print("="*70)
        
        signals = []
        
        for stock in self.watchlist:
            symbol = stock['symbol']
            name = stock['name']
            
            try:
                df = self.get_data(symbol)
                if df is None:
                    continue
                
                is_signal, signal_data = check_signal(df)
                current_price = df['Close'].iloc[-1]
                
                if is_signal:
                    signals.append({
                        'symbol': symbol,
                        'name': name,
                        'type': 'US Stock',
                        **signal_data
                    })
                    print(f"\n🎯 신호: {symbol} ({name})")
                    print(f"   RSI: {signal_data['rsi']:.1f} | 가격: ${current_price:.2f}")
                    print(f"   BB Lower: ${signal_data['bb_lower']:.2f} | 거래량: {signal_data['volume_ratio']:.1f}배")
                else:
                    # 디버그용 RSI 출력
                    rsi = signal_data['rsi'] if signal_data else 0
                    print(f"   {symbol:6s} ({name:15s}): RSI {rsi:.1f} | ${current_price:.2f}")
                    
            except Exception as e:
                print(f"   ⚠️ {symbol}: {str(e)[:30]}")
        
        return signals


class CryptoScanner:
    """가상화폐 스캐너 (ccxt 사용)"""
    
    def __init__(self):
        self.watchlist = [
            {'symbol': 'BTC/USDT', 'name': 'Bitcoin'},
            {'symbol': 'ETH/USDT', 'name': 'Ethereum'},
            {'symbol': 'SOL/USDT', 'name': 'Solana'},
            {'symbol': 'XRP/USDT', 'name': 'Ripple'},
            {'symbol': 'BNB/USDT', 'name': 'Binance Coin'},
            {'symbol': 'DOGE/USDT', 'name': 'Dogecoin'},
            {'symbol': 'ADA/USDT', 'name': 'Cardano'},
            {'symbol': 'AVAX/USDT', 'name': 'Avalanche'},
            {'symbol': 'LINK/USDT', 'name': 'Chainlink'},
            {'symbol': 'MATIC/USDT', 'name': 'Polygon'},
        ]
    
    def get_data(self, symbol, days=60):
        """Binance 데이터 조회"""
        try:
            import ccxt
            exchange = ccxt.binance({'enableRateLimit': True})
            
            # 1일 봉 데이터
            timeframe = '1d'
            since = exchange.parse8601((datetime.now() - timedelta(days=days)).isoformat())
            ohlcv = exchange.fetch_ohlcv(symbol, timeframe, since)
            
            if len(ohlcv) < 35:
                return None
            
            df = pd.DataFrame(ohlcv, columns=['timestamp', 'Open', 'High', 'Low', 'Close', 'Volume'])
            df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
            df.set_index('timestamp', inplace=True)
            
            return df
        except Exception as e:
            return None
    
    def scan(self):
        """스캔 실행"""
        print("\n" + "="*70)
        print("📊 가상화폐 RSI+BB 스캔 (Binance)")
        print(f"   기준: RSI 20~40, BB 하단, 거래량 1.3배+")
        print(f"   대상: {len(self.watchlist)}개 종목")
        print("="*70)
        
        signals = []
        
        for coin in self.watchlist:
            symbol = coin['symbol']
            name = coin['name']
            
            try:
                df = self.get_data(symbol)
                if df is None:
                    continue
                
                is_signal, signal_data = check_signal(df)
                current_price = df['Close'].iloc[-1]
                
                if is_signal:
                    signals.append({
                        'symbol': symbol,
                        'name': name,
                        'type': 'Crypto',
                        **signal_data
                    })
                    print(f"\n🎯 신호: {symbol} ({name})")
                    print(f"   RSI: {signal_data['rsi']:.1f} | 가격: ${current_price:,.2f}")
                    print(f"   BB Lower: ${signal_data['bb_lower']:,.2f} | 거래량: {signal_data['volume_ratio']:.1f}배")
                else:
                    rsi = signal_data['rsi'] if signal_data else 0
                    print(f"   {symbol:12s} ({name:12s}): RSI {rsi:.1f} | ${current_price:,.2f}")
                    
            except Exception as e:
                print(f"   ⚠️ {symbol}: {str(e)[:30]}")
        
        return signals


def main():
    print("="*70)
    print("🌍 RSI+BB 글로벌 스캐너")
    print(f"   실행시간: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print("="*70)
    
    all_signals = []
    
    # 미국 주식 스캔
    try:
        us_scanner = USStockScanner()
        us_signals = us_scanner.scan()
        all_signals.extend(us_signals)
    except Exception as e:
        print(f"\n⚠️ 미국 주식 스캔 오류: {e}")
    
    # 가상화폐 스캔
    try:
        crypto_scanner = CryptoScanner()
        crypto_signals = crypto_scanner.scan()
        all_signals.extend(crypto_signals)
    except Exception as e:
        print(f"\n⚠️ 가상화폐 스캔 오류: {e}")
    
    # 종합 리포트
    print("\n" + "="*70)
    print("📊 스캔 결과 종합")
    print("="*70)
    
    if all_signals:
        print(f"\n✅ 총 {len(all_signals)}개 매수 신호 발견!\n")
        
        for sig in all_signals:
            print(f"🎯 {sig['type']} | {sig['symbol']} ({sig['name']})")
            print(f"   RSI: {sig['rsi']:.1f} | 가격: ${sig['price']:,.2f}")
            print(f"   BB하단: ${sig['bb_lower']:,.2f} | 거래량: {sig['volume_ratio']:.1f}배")
            print()
        
        # 파일 저장
        output_file = f'/root/.openclaw/workspace/strg/docs/global_rsi_bb_signals_{datetime.now().strftime("%Y%m%d")}.json'
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump({
                'scan_time': datetime.now().isoformat(),
                'criteria': {'rsi_range': '20-40', 'bb_threshold': 'lower_band', 'volume': '1.3x'},
                'signals': all_signals
            }, f, ensure_ascii=False, indent=2)
        
        print(f"📄 신호 저장: {output_file}")
    else:
        print("\n⚠️ 매수 신호 없음")
        print("   현재 RSI 20~40 구간 + BB 하단 조건을 만족하는 종목이 없습니다.")
    
    print("="*70)


if __name__ == '__main__':
    main()
