#!/usr/bin/env python3
"""
SNS/커뮤니티 고승률 전략 백테스트
1. RSI(6) + Volume - 한국 주식
2. SuperTrend - 미국 주식/ETF
3. WaveTrend - 가상화폐
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import json
import warnings
warnings.filterwarnings('ignore')

import sys
sys.path.insert(0, '/root/.openclaw/workspace/strg')
from fdr_wrapper import get_price

# ============================================================================
# 공통 함수
# ============================================================================

def calculate_rsi(prices, period=14):
    delta = prices.diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
    rs = gain / loss
    return 100 - (100 / (1 + rs))

def backtest_summary(trades, strategy_name):
    """백테스트 결과 요약"""
    if not trades:
        return None
    
    df = pd.DataFrame(trades)
    total = len(df)
    wins = len(df[df['result'] == 'WIN'])
    win_rate = wins / total * 100
    
    total_return = ((1 + df['net_pnl_rate']/100).prod() - 1) * 100
    avg_pnl = df['net_pnl_rate'].mean()
    
    avg_win = df[df['result'] == 'WIN']['net_pnl_rate'].mean() if wins > 0 else 0
    avg_loss = df[df['result'] == 'LOSS']['net_pnl_rate'].mean() if (total - wins) > 0 else 0
    profit_factor = abs(avg_win / avg_loss) if avg_loss != 0 else 0
    
    return {
        'strategy': strategy_name,
        'total_trades': total,
        'wins': wins,
        'win_rate': win_rate,
        'total_return': total_return,
        'avg_pnl': avg_pnl,
        'profit_factor': profit_factor
    }

# ============================================================================
# 전략 1: RSI(6) + Volume - 한국 주식
# ============================================================================

class RSIVolumeKoreaBacktest:
    """RSI(6) + Volume 전략 - 한국 주식"""
    
    def __init__(self):
        self.fee_rate = 0.00015
        self.sl_rate = 0.02  # -2%
        self.tp_rate = 0.03  # +3%
        self.max_hold_days = 2
        
    def run(self, ticker, name, start_date='2024-01-01', end_date='2025-03-30'):
        """백테스트 실행"""
        try:
            df = get_price(ticker, start_date, end_date)
            if df is None or len(df) < 50:
                return []
            
            # 지표 계산
            df['RSI'] = calculate_rsi(df['Close'], 6)  # RSI(6)
            df['Volume_MA'] = df['Volume'].rolling(window=20).mean()
            df['Volume_Ratio'] = df['Volume'] / df['Volume_MA']
            df['Return_5d'] = df['Close'].pct_change(5) * 100
            
            # 매수 신호
            df['Signal'] = (
                (df['RSI'] < 25) &  # RSI 25 미만
                (df['Volume_Ratio'] >= 1.5) &  # 거래량 1.5배
                (df['Return_5d'] < -5)  # 5일 수익률 -5% 미만
            )
            
            trades = []
            position = None
            entry_price = entry_date = None
            
            for i in range(30, len(df)):
                date = df.index[i]
                row = df.iloc[i]
                
                # 매수
                if position is None and row['Signal']:
                    position = 'LONG'
                    entry_price = row['Close']
                    entry_date = date
                    entry_rsi = row['RSI']
                
                # 매도
                elif position == 'LONG':
                    current_price = row['Close']
                    holding_days = (pd.to_datetime(date) - pd.to_datetime(entry_date)).days
                    pnl_rate = (current_price - entry_price) / entry_price
                    
                    exit_reason = None
                    if pnl_rate <= -self.sl_rate:
                        exit_reason = 'STOP_LOSS'
                    elif pnl_rate >= self.tp_rate:
                        exit_reason = 'TAKE_PROFIT'
                    elif holding_days >= self.max_hold_days:
                        exit_reason = 'TIME_EXIT'
                    
                    if exit_reason:
                        net_pnl_rate = (pnl_rate - self.fee_rate * 2) * 100
                        trades.append({
                            'symbol': ticker,
                            'name': name,
                            'entry_date': str(entry_date)[:10],
                            'exit_date': str(date)[:10],
                            'entry_price': round(entry_price, 0),
                            'exit_price': round(current_price, 0),
                            'entry_rsi': round(entry_rsi, 1),
                            'net_pnl_rate': round(net_pnl_rate, 2),
                            'result': 'WIN' if net_pnl_rate > 0 else 'LOSS',
                            'exit_reason': exit_reason,
                            'strategy': 'RSI6+Volume'
                        })
                        position = None
            
            return trades
            
        except Exception as e:
            return []


# ============================================================================
# 전략 2: SuperTrend - 미국 주식/ETF
# ============================================================================

class SuperTrendBacktest:
    """SuperTrend 전략 - 미국 주식/ETF"""
    
    def __init__(self):
        self.fee_rate = 0.00015
        self.period = 10
        self.multiplier = 3
        
    def calculate_supertrend(self, df):
        """SuperTrend 계산"""
        df = df.copy()
        
        # ATR 계산
        df['TR'] = np.maximum(
            df['High'] - df['Low'],
            np.maximum(
                abs(df['High'] - df['Close'].shift(1)),
                abs(df['Low'] - df['Close'].shift(1))
            )
        )
        df['ATR'] = df['TR'].rolling(window=self.period).mean()
        
        # SuperTrend
        hl2 = (df['High'] + df['Low']) / 2
        df['Upper_Band'] = hl2 + (self.multiplier * df['ATR'])
        df['Lower_Band'] = hl2 - (self.multiplier * df['ATR'])
        
        df['SuperTrend'] = np.nan
        df['Trend'] = 1  # 1: 상승, -1: 하락
        
        for i in range(1, len(df)):
            if df['Close'].iloc[i] > df['Upper_Band'].iloc[i-1]:
                df.loc[df.index[i], 'Trend'] = 1
            elif df['Close'].iloc[i] < df['Lower_Band'].iloc[i-1]:
                df.loc[df.index[i], 'Trend'] = -1
            else:
                df.loc[df.index[i], 'Trend'] = df['Trend'].iloc[i-1]
            
            if df['Trend'].iloc[i] == 1:
                df.loc[df.index[i], 'SuperTrend'] = max(df['Lower_Band'].iloc[i], df['Lower_Band'].iloc[i-1])
            else:
                df.loc[df.index[i], 'SuperTrend'] = min(df['Upper_Band'].iloc[i], df['Upper_Band'].iloc[i-1])
        
        # 매수/매도 신호
        df['Buy_Signal'] = (df['Trend'] == 1) & (df['Trend'].shift(1) == -1)
        df['Sell_Signal'] = (df['Trend'] == -1) & (df['Trend'].shift(1) == 1)
        
        return df
    
    def get_data(self, symbol, start_date, end_date):
        try:
            import yfinance as yf
            df = yf.download(symbol, start=start_date, end=end_date, progress=False)
            if len(df) < 50:
                return None
            df.columns = ['Close', 'High', 'Low', 'Open', 'Volume'] if len(df.columns) == 5 else df.columns
            return df
        except:
            return None
    
    def run(self, symbol, name, start_date='2024-01-01', end_date='2025-03-30'):
        try:
            df = self.get_data(symbol, start_date, end_date)
            if df is None:
                return []
            
            df = self.calculate_supertrend(df)
            
            trades = []
            position = None
            entry_price = entry_date = None
            
            for i in range(1, len(df)):
                date = df.index[i]
                row = df.iloc[i]
                
                # 매수
                if position is None and row['Buy_Signal']:
                    position = 'LONG'
                    entry_price = row['Close']
                    entry_date = date
                
                # 매도
                elif position == 'LONG' and row['Sell_Signal']:
                    exit_price = row['Close']
                    pnl_rate = (exit_price - entry_price) / entry_price
                    net_pnl_rate = (pnl_rate - self.fee_rate * 2) * 100
                    
                    trades.append({
                        'symbol': symbol,
                        'name': name,
                        'entry_date': str(entry_date)[:10],
                        'exit_date': str(date)[:10],
                        'entry_price': round(entry_price, 2),
                        'exit_price': round(exit_price, 2),
                        'net_pnl_rate': round(net_pnl_rate, 2),
                        'result': 'WIN' if net_pnl_rate > 0 else 'LOSS',
                        'exit_reason': 'SUPERTREND_REVERSAL',
                        'strategy': 'SuperTrend'
                    })
                    position = None
            
            return trades
            
        except Exception as e:
            return []


# ============================================================================
# 전략 3: WaveTrend - 가상화폐
# ============================================================================

class WaveTrendBacktest:
    """WaveTrend 전략 - 가상화폐"""
    
    def __init__(self):
        self.fee_rate = 0.00015
        self.channel_len = 10
        self.avg_len = 21
        self.os_level = -53  # 과매도
        self.ob_level = 53   # 과매수
        
    def calculate_wavetrend(self, df):
        """WaveTrend (LazyBear) 계산"""
        df = df.copy()
        
        hlc3 = (df['High'] + df['Low'] + df['Close']) / 3
        
        # EMA
        esa = hlc3.ewm(span=self.channel_len, adjust=False).mean()
        de = abs(hlc3 - esa).ewm(span=self.channel_len, adjust=False).mean()
        
        # CI
        ci = (hlc3 - esa) / (0.015 * de)
        
        # WaveTrend
        df['WT1'] = ci.ewm(span=self.avg_len, adjust=False).mean()
        df['WT2'] = df['WT1'].rolling(window=4).mean()
        
        # 신호
        df['Buy_Signal'] = (df['WT1'] < self.os_level) & (df['WT1'] > df['WT2'])
        df['Sell_Signal'] = (df['WT1'] > self.ob_level) | ((df['WT1'] > 0) & (df['WT1'] < df['WT2']))
        
        return df
    
    def get_data(self, symbol, start_date, end_date):
        try:
            import ccxt
            exchange = ccxt.binance({'enableRateLimit': True})
            since = exchange.parse8601(f"{start_date}T00:00:00Z")
            ohlcv = exchange.fetch_ohlcv(symbol, '1d', since)
            
            if len(ohlcv) < 50:
                return None
            
            df = pd.DataFrame(ohlcv, columns=['timestamp', 'Open', 'High', 'Low', 'Close', 'Volume'])
            df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
            df.set_index('timestamp', inplace=True)
            df = df[df.index <= end_date]
            
            return df
        except:
            return None
    
    def run(self, symbol, name, start_date='2024-01-01', end_date='2025-03-30'):
        try:
            df = self.get_data(symbol, start_date, end_date)
            if df is None:
                return []
            
            df = self.calculate_wavetrend(df)
            
            trades = []
            position = None
            entry_price = entry_date = None
            
            for i in range(30, len(df)):
                date = df.index[i]
                row = df.iloc[i]
                
                # 매수
                if position is None and row['Buy_Signal']:
                    position = 'LONG'
                    entry_price = row['Close']
                    entry_date = date
                    entry_wt = row['WT1']
                
                # 매도
                elif position == 'LONG' and row['Sell_Signal']:
                    exit_price = row['Close']
                    pnl_rate = (exit_price - entry_price) / entry_price
                    net_pnl_rate = (pnl_rate - self.fee_rate * 2) * 100
                    
                    trades.append({
                        'symbol': symbol,
                        'name': name,
                        'entry_date': str(entry_date)[:10],
                        'exit_date': str(date)[:10],
                        'entry_price': round(entry_price, 2),
                        'exit_price': round(exit_price, 2),
                        'entry_wt': round(entry_wt, 1),
                        'net_pnl_rate': round(net_pnl_rate, 2),
                        'result': 'WIN' if net_pnl_rate > 0 else 'LOSS',
                        'exit_reason': 'WAVETREND_EXIT',
                        'strategy': 'WaveTrend'
                    })
                    position = None
            
            return trades
            
        except Exception as e:
            return []


# ============================================================================
# 메인 실행
# ============================================================================

def main():
    print("="*80)
    print("🌍 SNS/커뮤니티 고승률 전략 백테스트")
    print(f"   기간: 2024-01-01 ~ 2025-03-30")
    print("="*80)
    
    all_results = []
    
    # =========================================================================
    # 전략 1: RSI(6) + Volume - 한국 주식
    # =========================================================================
    print("\n" + "="*80)
    print("📊 전략 1: RSI(6) + Volume - 한국 주식")
    print("   조건: RSI(6) < 25, 거래량 1.5배, 5일 수익률 < -5%")
    print("   청산: -2% 손절 / +3% 익절 / 2일 시간청산")
    print("="*80)
    
    korea_stocks = [
        ('005930', '삼성전자'),
        ('000660', 'SK하이닉스'),
        ('005380', '현대차'),
        ('035420', 'NAVER'),
        ('035720', '카카오'),
        ('051910', 'LG화학'),
        ('006400', '삼성SDI'),
        ('028260', '삼성물산'),
        ('068270', '셀트리온'),
        ('207940', '삼성바이오'),
    ]
    
    rsi_volume_bt = RSIVolumeKoreaBacktest()
    korea_trades = []
    
    for i, (code, name) in enumerate(korea_stocks, 1):
        print(f"[{i:2d}/{len(korea_stocks)}] {code} ({name})", end=' ')
        trades = rsi_volume_bt.run(code, name)
        if trades:
            korea_trades.extend(trades)
            wins = sum(1 for t in trades if t['result'] == 'WIN')
            print(f"→ {len(trades)}거래 (승: {wins})")
        else:
            print("→ 신호 없음")
    
    result1 = backtest_summary(korea_trades, 'RSI6+Volume (Korea)')
    all_results.append(result1)
    
    # =========================================================================
    # 전략 2: SuperTrend - 미국 주식/ETF
    # =========================================================================
    print("\n" + "="*80)
    print("📊 전략 2: SuperTrend - 미국 주식/ETF")
    print("   설정: Period 10, Multiplier 3")
    print("   청산: 추세 전환 시")
    print("="*80)
    
    us_stocks = [
        ('SPY', 'S&P 500 ETF'),
        ('QQQ', 'Nasdaq 100 ETF'),
        ('AAPL', 'Apple'),
        ('MSFT', 'Microsoft'),
        ('TSLA', 'Tesla'),
        ('NVDA', 'NVIDIA'),
        ('META', 'Meta'),
        ('GOOGL', 'Alphabet'),
    ]
    
    supertrend_bt = SuperTrendBacktest()
    us_trades = []
    
    for i, (symbol, name) in enumerate(us_stocks, 1):
        print(f"[{i:2d}/{len(us_stocks)}] {symbol:<6} ({name:<15})", end=' ')
        trades = supertrend_bt.run(symbol, name)
        if trades:
            us_trades.extend(trades)
            wins = sum(1 for t in trades if t['result'] == 'WIN')
            print(f"→ {len(trades)}거래 (승: {wins})")
        else:
            print("→ 신호 없음")
    
    result2 = backtest_summary(us_trades, 'SuperTrend (US)')
    all_results.append(result2)
    
    # =========================================================================
    # 전략 3: WaveTrend - 가상화폐
    # =========================================================================
    print("\n" + "="*80)
    print("📊 전략 3: WaveTrend - 가상화폐")
    print("   설정: Channel Length 10, OS Level -53")
    print("   청산: 과매수 도달 또는 추세 반전")
    print("="*80)
    
    cryptos = [
        ('BTC/USDT', 'Bitcoin'),
        ('ETH/USDT', 'Ethereum'),
        ('SOL/USDT', 'Solana'),
        ('BNB/USDT', 'Binance Coin'),
        ('DOGE/USDT', 'Dogecoin'),
    ]
    
    wavetrend_bt = WaveTrendBacktest()
    crypto_trades = []
    
    for i, (symbol, name) in enumerate(cryptos, 1):
        print(f"[{i}/{len(cryptos)}] {symbol:<12} ({name:<12})", end=' ')
        trades = wavetrend_bt.run(symbol, name)
        if trades:
            crypto_trades.extend(trades)
            wins = sum(1 for t in trades if t['result'] == 'WIN')
            print(f"→ {len(trades)}거래 (승: {wins})")
        else:
            print("→ 신호 없음")
    
    result3 = backtest_summary(crypto_trades, 'WaveTrend (Crypto)')
    all_results.append(result3)
    
    # =========================================================================
    # 종합 결과
    # =========================================================================
    print("\n" + "="*80)
    print("📊 종합 결과 비교")
    print("="*80)
    
    print(f"\n{'전략':<25} {'거래수':<8} {'승률':<10} {'총수익률':<12} {'PF':<8}")
    print("-"*80)
    
    for r in all_results:
        if r:
            print(f"{r['strategy']:<25} {r['total_trades']:<8} {r['win_rate']:.1f}%     {r['total_return']:+.2f}%      {r['profit_factor']:.2f}")
    
    # 저장
    output_file = f'/root/.openclaw/workspace/strg/docs/strategy_comparison_{datetime.now().strftime("%Y%m%d")}.json'
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump({
            'results': all_results,
            'trades': {
                'rsi_volume': korea_trades,
                'supertrend': us_trades,
                'wavetrend': crypto_trades
            }
        }, f, ensure_ascii=False, indent=2)
    
    print(f"\n📄 결과 저장: {output_file}")
    print("="*80)


if __name__ == '__main__':
    main()
