#!/usr/bin/env python3
"""
RSI + 볼린저밴드 - 글로벌 자산 심층 분석
미국 주식 + 가상화폐 현재 상태 분석 및 관망 종목 선별
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import json

def calculate_rsi(prices, period=14):
    delta = prices.diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
    rs = gain / loss
    return 100 - (100 / (1 + rs))

def calculate_bollinger(df, period=20, std_dev=2):
    df['BB_Middle'] = df['Close'].rolling(window=period).mean()
    df['BB_Std'] = df['Close'].rolling(window=period).std()
    df['BB_Upper'] = df['BB_Middle'] + (df['BB_Std'] * std_dev)
    df['BB_Lower'] = df['BB_Middle'] - (df['BB_Std'] * std_dev)
    df['BB_Width'] = (df['BB_Upper'] - df['BB_Lower']) / df['BB_Middle'] * 100
    df['BB_Position'] = (df['Close'] - df['BB_Lower']) / (df['BB_Upper'] - df['BB_Lower'])
    return df

def analyze_asset(df, symbol, name, asset_type):
    """개별 자산 심층 분석"""
    if df is None or len(df) < 35:
        return None
    
    df = df.copy()
    df['RSI'] = calculate_rsi(df['Close'], 14)
    df = calculate_bollinger(df, 20, 2)
    df['Volume_MA'] = df['Volume'].rolling(window=20).mean()
    df['Volume_Ratio'] = df['Volume'] / df['Volume_MA']
    
    latest = df.iloc[-1]
    
    # 현재 상태
    current_rsi = latest['RSI']
    current_price = latest['Close']
    bb_lower = latest['BB_Lower']
    bb_upper = latest['BB_Upper']
    bb_position = latest['BB_Position']
    volume_ratio = latest['Volume_Ratio']
    bb_width = latest['BB_Width']
    
    # 5일/20일 수익률
    ret_5d = (current_price - df['Close'].iloc[-6]) / df['Close'].iloc[-6] * 100 if len(df) >= 6 else 0
    ret_20d = (current_price - df['Close'].iloc[-21]) / df['Close'].iloc[-21] * 100 if len(df) >= 21 else 0
    
    # 신호 강도 계산
    signal_score = 0
    reasons = []
    
    # RSI 조건 (20~40)
    if 20 <= current_rsi <= 40:
        signal_score += 40
        reasons.append(f"RSI 과매도({current_rsi:.1f})")
    elif current_rsi < 20:
        signal_score += 30
        reasons.append(f"RSI 극과매도({current_rsi:.1f})")
    elif current_rsi < 45:
        signal_score += 20
        reasons.append(f"RSI 약과매도({current_rsi:.1f})")
    
    # BB 위치
    if bb_position <= 0.1:
        signal_score += 35
        reasons.append("BB하단 터치")
    elif bb_position <= 0.3:
        signal_score += 25
        reasons.append("BB하단 근접")
    elif bb_position <= 0.5:
        signal_score += 15
        reasons.append("BB하단 방향")
    
    # 거래량
    if volume_ratio >= 1.5:
        signal_score += 25
        reasons.append(f"거래량 급증({volume_ratio:.1f}배)")
    elif volume_ratio >= 1.3:
        signal_score += 15
        reasons.append(f"거래량 증가({volume_ratio:.1f}배)")
    elif volume_ratio >= 1.0:
        signal_score += 5
    
    # 양봉
    if latest['Close'] > latest['Open']:
        signal_score += 10
        reasons.append("양봉")
    
    return {
        'symbol': symbol,
        'name': name,
        'type': asset_type,
        'price': current_price,
        'rsi': current_rsi,
        'bb_lower': bb_lower,
        'bb_upper': bb_upper,
        'bb_position': bb_position,
        'volume_ratio': volume_ratio,
        'bb_width': bb_width,
        'ret_5d': ret_5d,
        'ret_20d': ret_20d,
        'signal_score': signal_score,
        'reasons': reasons
    }


class GlobalMarketAnalyzer:
    """글로벌 시장 종합 분석기"""
    
    def __init__(self):
        self.us_stocks = [
            {'symbol': 'AAPL', 'name': 'Apple', 'sector': 'Tech'},
            {'symbol': 'MSFT', 'name': 'Microsoft', 'sector': 'Tech'},
            {'symbol': 'GOOGL', 'name': 'Alphabet', 'sector': 'Tech'},
            {'symbol': 'AMZN', 'name': 'Amazon', 'sector': 'Tech'},
            {'symbol': 'META', 'name': 'Meta', 'sector': 'Tech'},
            {'symbol': 'TSLA', 'name': 'Tesla', 'sector': 'Tech'},
            {'symbol': 'NVDA', 'name': 'NVIDIA', 'sector': 'Tech'},
            {'symbol': 'AMD', 'name': 'AMD', 'sector': 'Tech'},
            {'symbol': 'NFLX', 'name': 'Netflix', 'sector': 'Tech'},
            {'symbol': 'JPM', 'name': 'JPMorgan', 'sector': 'Finance'},
            {'symbol': 'BAC', 'name': 'Bank of America', 'sector': 'Finance'},
            {'symbol': 'GS', 'name': 'Goldman Sachs', 'sector': 'Finance'},
            {'symbol': 'SPY', 'name': 'S&P 500 ETF', 'sector': 'Index'},
            {'symbol': 'QQQ', 'name': 'Nasdaq 100 ETF', 'sector': 'Index'},
            {'symbol': 'IWM', 'name': 'Russell 2000 ETF', 'sector': 'Index'},
            {'symbol': 'COIN', 'name': 'Coinbase', 'sector': 'Crypto'},
            {'symbol': 'MSTR', 'name': 'MicroStrategy', 'sector': 'Crypto'},
            {'symbol': 'PLTR', 'name': 'Palantir', 'sector': 'Tech'},
            {'symbol': 'ARKK', 'name': 'ARK Innovation ETF', 'sector': 'ETF'},
        ]
        
        self.cryptos = [
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
    
    def get_us_stock_data(self, symbol, days=60):
        """미국 주식 데이터"""
        try:
            import yfinance as yf
            end = datetime.now()
            start = end - timedelta(days=days)
            df = yf.download(symbol, start=start, end=end, progress=False)
            if len(df) < 35:
                return None
            df.columns = ['Close', 'High', 'Low', 'Open', 'Volume'] if len(df.columns) == 5 else df.columns
            return df
        except:
            return None
    
    def get_crypto_data(self, symbol, days=60):
        """가상화폐 데이터"""
        try:
            import ccxt
            exchange = ccxt.binance({'enableRateLimit': True})
            since = exchange.parse8601((datetime.now() - timedelta(days=days)).isoformat())
            ohlcv = exchange.fetch_ohlcv(symbol, '1d', since)
            if len(ohlcv) < 35:
                return None
            df = pd.DataFrame(ohlcv, columns=['timestamp', 'Open', 'High', 'Low', 'Close', 'Volume'])
            df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
            df.set_index('timestamp', inplace=True)
            return df
        except:
            return None
    
    def analyze_all(self):
        """전체 분석"""
        results = []
        
        print("="*80)
        print("🌍 글로벌 자산 RSI+BB 심층 분석")
        print(f"   실행시간: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
        print("="*80)
        
        # 미국 주식 분석
        print("\n📊 미국 주식 분석 중...")
        for stock in self.us_stocks:
            df = self.get_us_stock_data(stock['symbol'])
            result = analyze_asset(df, stock['symbol'], stock['name'], 'US Stock')
            if result:
                result['sector'] = stock.get('sector', '')
                results.append(result)
        
        # 가상화폐 분석
        print("📊 가상화폐 분석 중...")
        for coin in self.cryptos:
            df = self.get_crypto_data(coin['symbol'])
            result = analyze_asset(df, coin['symbol'], coin['name'], 'Crypto')
            if result:
                results.append(result)
        
        return results
    
    def generate_report(self, results):
        """리포트 생성"""
        print("\n" + "="*80)
        print("📈 분석 결과 종합")
        print("="*80)
        
        # 신호 강도별 분류
        strong_signals = [r for r in results if r['signal_score'] >= 80]
        watch_list = [r for r in results if 60 <= r['signal_score'] < 80]
        potential = [r for r in results if 40 <= r['signal_score'] < 60]
        
        # 강한 신호
        if strong_signals:
            print(f"\n🎯 강한 매수 신호 ({len(strong_signals)}개) - 즉시 관심")
            print("-"*80)
            for r in sorted(strong_signals, key=lambda x: x['signal_score'], reverse=True):
                price_str = f"${r['price']:,.2f}" if r['type'] == 'US Stock' else f"${r['price']:,.2f}"
                print(f"   {r['symbol']:<12} ({r['name']:<15}) | 점수: {r['signal_score']}점")
                print(f"      RSI: {r['rsi']:.1f} | 가격: {price_str} | 5일: {r['ret_5d']:+.1f}%")
                print(f"      BB위치: {r['bb_position']*100:.1f}% | 거래량: {r['volume_ratio']:.1f}배")
                print(f"      사유: {', '.join(r['reasons'])}")
                print()
        
        # 관망 리스트
        if watch_list:
            print(f"\n👀 관망 종목 ({len(watch_list)}개) - 조건 충족 임박")
            print("-"*80)
            print(f"{'종목':<12} {'이름':<15} {'점수':<6} {'RSI':<6} {'5일':<8} {'20일':<8} {'사유'}")
            print("-"*80)
            for r in sorted(watch_list, key=lambda x: x['signal_score'], reverse=True):
                print(f"{r['symbol']:<12} {r['name']:<15} {r['signal_score']:<6} {r['rsi']:.1f}  {r['ret_5d']:+6.1f}% {r['ret_20d']:+6.1f}% {', '.join(r['reasons'][:2])}")
        
        # 잠재적 후보
        if potential:
            print(f"\n📋 잠재적 후보 ({len(potential)}개) - 추적 필요")
            print("-"*80)
            print(f"{'종목':<12} {'이름':<15} {'점수':<6} {'RSI':<6} {'BB위치':<8} {'상태'}")
            print("-"*80)
            for r in sorted(potential, key=lambda x: x['signal_score'], reverse=True)[:10]:
                bb_pos_str = f"{r['bb_position']*100:.0f}%"
                status = "과매도" if r['rsi'] < 40 else "중립"
                print(f"{r['symbol']:<12} {r['name']:<15} {r['signal_score']:<6} {r['rsi']:.1f}  {bb_pos_str:<8} {status}")
        
        # RSI 과매도 종목 요약
        oversold = [r for r in results if r['rsi'] < 40]
        print(f"\n\n📊 RSI 과매도 현황 (RSI < 40): {len(oversold)}개 종목")
        print("-"*80)
        
        # 섹터별/타입별 분석
        us_oversold = [r for r in oversold if r['type'] == 'US Stock']
        crypto_oversold = [r for r in oversold if r['type'] == 'Crypto']
        
        print(f"\n   미국 주식: {len(us_oversold)}개")
        for r in sorted(us_oversold, key=lambda x: x['rsi'])[:5]:
            print(f"      {r['symbol']:<6} ({r['name']:<12}): RSI {r['rsi']:.1f} | {r['ret_5d']:+5.1f}% (5일)")
        
        print(f"\n   가상화폐: {len(crypto_oversold)}개")
        for r in sorted(crypto_oversold, key=lambda x: x['rsi'])[:5]:
            print(f"      {r['symbol']:<10}: RSI {r['rsi']:.1f} | {r['ret_5d']:+5.1f}% (5일)")
        
        # 종합 인사이트
        print("\n" + "="*80)
        print("💡 종합 인사이트")
        print("="*80)
        
        avg_rsi_us = np.mean([r['rsi'] for r in results if r['type'] == 'US Stock'])
        avg_rsi_crypto = np.mean([r['rsi'] for r in results if r['type'] == 'Crypto'])
        
        print(f"\n   미국 주식 평균 RSI: {avg_rsi_us:.1f} ({'과매도' if avg_rsi_us < 40 else '중립'})")
        print(f"   가상화폐 평균 RSI: {avg_rsi_crypto:.1f} ({'과매도' if avg_rsi_crypto < 40 else '중립'})")
        
        if avg_rsi_us < 35 or avg_rsi_crypto < 35:
            print("\n   ⚠️  시장 전반적으로 과매도 국면 - 반등 가능성 주시")
        elif avg_rsi_us < 45 and avg_rsi_crypto < 45:
            print("\n   🟡 약한 과매도 국면 - 선별적 매수 고려")
        else:
            print("\n   🟢 중립적 국면 - 신중한 접근")
        
        # 저장
        output_file = f'/root/.openclaw/workspace/strg/docs/global_market_analysis_{datetime.now().strftime("%Y%m%d")}.json'
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump({
                'scan_time': datetime.now().isoformat(),
                'summary': {
                    'total_analyzed': len(results),
                    'strong_signals': len(strong_signals),
                    'watch_list': len(watch_list),
                    'potential': len(potential),
                    'oversold': len(oversold)
                },
                'results': results
            }, f, ensure_ascii=False, indent=2)
        
        print(f"\n📄 데이터 저장: {output_file}")


def main():
    analyzer = GlobalMarketAnalyzer()
    
    print("="*80)
    print("🌍 RSI+BB 글로벌 자산 심층 분석기")
    print("="*80)
    
    results = analyzer.analyze_all()
    
    if results:
        analyzer.generate_report(results)
    else:
        print("\n⚠️ 분석 데이터 없음")
    
    print("\n" + "="*80)


if __name__ == '__main__':
    main()
