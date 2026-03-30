#!/usr/bin/env python3
"""
RSI + 볼린저밴드 단타 전략 - 미국 주식 & 가상화폐 백테스트
기간: 2024-01-01 ~ 2025-03-30
파라미터: RSI 20~40, BB 하단, 거래량 1.3배+, 손절 -3%, 익절 +3%
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import json
import warnings
warnings.filterwarnings('ignore')

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
    return df

class RSIBBBacktestGlobal:
    def __init__(self):
        self.initial_capital = 10000  # $10,000
        self.fee_rate = 0.00015  # 0.015%
        self.sl_rate = 0.03  # 손절 -3%
        self.tp_rate = 0.03  # 익절 +3%
        self.tp_rate_ext = 0.05  # 확장 익절 +5%
        self.max_hold_days = 2
        
        # 기술적 지표
        self.rsi_lower = 20
        self.rsi_upper = 40
        self.volume_threshold = 1.3
        
    def prepare_data(self, df):
        """데이터 전처리 및 지표 계산"""
        if df is None or len(df) < 50:
            return None
        
        df = df.copy()
        df['RSI'] = calculate_rsi(df['Close'], 14)
        df = calculate_bollinger(df, 20, 2)
        df['Volume_MA'] = df['Volume'].rolling(window=20).mean()
        df['Volume_Ratio'] = df['Volume'] / df['Volume_MA']
        
        # 매수 신호
        df['Buy_Signal'] = (
            (df['RSI'] >= self.rsi_lower) & 
            (df['RSI'] <= self.rsi_upper) &
            (df['Close'] <= df['BB_Lower'] * 1.02) &
            (df['Volume_Ratio'] >= self.volume_threshold) &
            (df['Close'] > df['Open'])
        )
        
        return df
    
    def backtest_asset(self, symbol, name, asset_type, df):
        """단일 자산 백테스트"""
        df = self.prepare_data(df)
        if df is None:
            return [], "데이터 부족"
        
        trades = []
        position = None
        entry_price = entry_date = None
        
        for i in range(35, len(df)):
            date = df.index[i]
            row = df.iloc[i]
            
            # 매수
            if position is None and row['Buy_Signal']:
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
                elif pnl_rate >= self.tp_rate_ext:
                    exit_reason = 'TP_EXT'
                elif pnl_rate >= self.tp_rate:
                    exit_reason = 'TAKE_PROFIT'
                elif holding_days >= self.max_hold_days:
                    exit_reason = 'TIME_EXIT'
                
                if exit_reason:
                    fee = (entry_price + current_price) * self.fee_rate
                    net_pnl_rate = (pnl_rate - self.fee_rate * 2) * 100
                    
                    trades.append({
                        'symbol': symbol,
                        'name': name,
                        'type': asset_type,
                        'entry_date': str(entry_date)[:10],
                        'exit_date': str(date)[:10],
                        'entry_price': round(entry_price, 2),
                        'exit_price': round(current_price, 2),
                        'entry_rsi': round(entry_rsi, 1),
                        'holding_days': holding_days,
                        'net_pnl_rate': round(net_pnl_rate, 2),
                        'result': 'WIN' if net_pnl_rate > 0 else 'LOSS',
                        'exit_reason': exit_reason
                    })
                    position = None
        
        return trades, f"✅ {len(trades)}거래"


class USStockBacktest:
    """미국 주식 백테스트"""
    
    def __init__(self):
        self.backtest = RSIBBBacktestGlobal()
        self.stocks = [
            {'symbol': 'AAPL', 'name': 'Apple'},
            {'symbol': 'MSFT', 'name': 'Microsoft'},
            {'symbol': 'GOOGL', 'name': 'Alphabet'},
            {'symbol': 'AMZN', 'name': 'Amazon'},
            {'symbol': 'META', 'name': 'Meta'},
            {'symbol': 'TSLA', 'name': 'Tesla'},
            {'symbol': 'NVDA', 'name': 'NVIDIA'},
            {'symbol': 'AMD', 'name': 'AMD'},
            {'symbol': 'NFLX', 'name': 'Netflix'},
            {'symbol': 'JPM', 'name': 'JPMorgan'},
            {'symbol': 'BAC', 'name': 'Bank of America'},
            {'symbol': 'GS', 'name': 'Goldman Sachs'},
            {'symbol': 'SPY', 'name': 'S&P 500 ETF'},
            {'symbol': 'QQQ', 'name': 'Nasdaq 100 ETF'},
            {'symbol': 'IWM', 'name': 'Russell 2000 ETF'},
            {'symbol': 'COIN', 'name': 'Coinbase'},
            {'symbol': 'MSTR', 'name': 'MicroStrategy'},
            {'symbol': 'PLTR', 'name': 'Palantir'},
        ]
    
    def get_data(self, symbol, start_date, end_date):
        """yfinance로 데이터 조회"""
        try:
            import yfinance as yf
            df = yf.download(symbol, start=start_date, end=end_date, progress=False)
            if len(df) < 50:
                return None
            df.columns = ['Close', 'High', 'Low', 'Open', 'Volume'] if len(df.columns) == 5 else df.columns
            return df
        except:
            return None
    
    def run(self, start_date='2024-01-01', end_date='2025-03-30'):
        """백테스트 실행"""
        print("="*70)
        print("📊 미국 주식 RSI+BB 백테스트")
        print(f"   기간: {start_date} ~ {end_date}")
        print(f"   파라미터: RSI {self.backtest.rsi_lower}~{self.backtest.rsi_upper}, BB 하단, 거래량 {self.backtest.volume_threshold}배")
        print(f"   청산: -{self.backtest.sl_rate*100:.0f}% 손절 / +{self.backtest.tp_rate*100:.0f}% 익절")
        print("="*70)
        
        all_trades = []
        
        for i, stock in enumerate(self.stocks, 1):
            print(f"[{i:2d}/{len(self.stocks)}] {stock['symbol']:<6} ({stock['name']:<15})", end=' ')
            
            df = self.get_data(stock['symbol'], start_date, end_date)
            trades, msg = self.backtest.backtest_asset(
                stock['symbol'], stock['name'], 'US Stock', df
            )
            
            if trades:
                all_trades.extend(trades)
                wins = sum(1 for t in trades if t['result'] == 'WIN')
                print(f"→ {len(trades)}거래 (승: {wins})")
            else:
                print(f"→ {msg}")
        
        return all_trades


class CryptoBacktest:
    """가상화폐 백테스트"""
    
    def __init__(self):
        self.backtest = RSIBBBacktestGlobal()
        self.coins = [
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
    
    def get_data(self, symbol, start_date, end_date):
        """Binance 데이터 조회"""
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
            
            # 종료일 필터링
            df = df[df.index <= end_date]
            
            return df
        except:
            return None
    
    def run(self, start_date='2024-01-01', end_date='2025-03-30'):
        """백테스트 실행"""
        print("\n" + "="*70)
        print("📊 가상화폐 RSI+BB 백테스트")
        print(f"   기간: {start_date} ~ {end_date}")
        print(f"   파라미터: RSI {self.backtest.rsi_lower}~{self.backtest.rsi_upper}, BB 하단, 거래량 {self.backtest.volume_threshold}배")
        print(f"   청산: -{self.backtest.sl_rate*100:.0f}% 손절 / +{self.backtest.tp_rate*100:.0f}% 익절")
        print("="*70)
        
        all_trades = []
        
        for i, coin in enumerate(self.coins, 1):
            print(f"[{i:2d}/{len(self.coins)}] {coin['symbol']:<12} ({coin['name']:<12})", end=' ')
            
            df = self.get_data(coin['symbol'], start_date, end_date)
            trades, msg = self.backtest.backtest_asset(
                coin['symbol'], coin['name'], 'Crypto', df
            )
            
            if trades:
                all_trades.extend(trades)
                wins = sum(1 for t in trades if t['result'] == 'WIN')
                print(f"→ {len(trades)}거래 (승: {wins})")
            else:
                print(f"→ {msg}")
        
        return all_trades


def generate_report(all_trades, output_path):
    """백테스트 리포트 생성"""
    if not all_trades:
        print("\n⚠️ 거래 내역 없음")
        return
    
    df = pd.DataFrame(all_trades)
    
    # 기본 통계
    total = len(df)
    wins = len(df[df['result'] == 'WIN'])
    win_rate = wins / total * 100
    
    avg_pnl = df['net_pnl_rate'].mean()
    total_return = ((1 + df['net_pnl_rate']/100).prod() - 1) * 100
    
    avg_win = df[df['result'] == 'WIN']['net_pnl_rate'].mean() if wins > 0 else 0
    avg_loss = df[df['result'] == 'LOSS']['net_pnl_rate'].mean() if (total - wins) > 0 else 0
    
    profit_factor = abs(avg_win / avg_loss) if avg_loss != 0 else 0
    
    # 종목별 통계
    by_symbol = df.groupby(['symbol', 'name', 'type']).agg({
        'result': ['count', lambda x: (x == 'WIN').sum() / len(x) * 100],
        'net_pnl_rate': 'mean'
    }).round(2)
    by_symbol.columns = ['trades', 'win_rate', 'avg_pnl']
    by_symbol = by_symbol.reset_index()
    
    # 종류별 분리
    us_trades = df[df['type'] == 'US Stock']
    crypto_trades = df[df['type'] == 'Crypto']
    
    print("\n" + "="*70)
    print("📈 백테스트 결과 종합")
    print("="*70)
    
    print(f"\n📊 전체 통계")
    print(f"   총 거래: {total}회")
    print(f"   승률: {win_rate:.1f}% ({wins}승 / {total-wins}패)")
    print(f"   총 수익률 (복리): +{total_return:.2f}%")
    print(f"   평균 수익/거래: {avg_pnl:.2f}%")
    print(f"   평균 수익 (승): {avg_win:.2f}%")
    print(f"   평균 손실 (패): {avg_loss:.2f}%")
    print(f"   손익비: 1:{abs(avg_win/avg_loss):.1f}")
    print(f"   Profit Factor: {profit_factor:.2f}")
    
    # 종류별 통계
    print(f"\n📊 종류별 성과")
    print("-"*70)
    
    if len(us_trades) > 0:
        us_wins = len(us_trades[us_trades['result'] == 'WIN'])
        us_return = ((1 + us_trades['net_pnl_rate']/100).prod() - 1) * 100
        print(f"   미국 주식: {len(us_trades)}거래 | 승률 {us_wins/len(us_trades)*100:.1f}% | 수익률 {us_return:+.2f}%")
    
    if len(crypto_trades) > 0:
        crypto_wins = len(crypto_trades[crypto_trades['result'] == 'WIN'])
        crypto_return = ((1 + crypto_trades['net_pnl_rate']/100).prod() - 1) * 100
        print(f"   가상화폐: {len(crypto_trades)}거래 | 승률 {crypto_wins/len(crypto_trades)*100:.1f}% | 수익률 {crypto_return:+.2f}%")
    
    # 종목별 TOP
    print(f"\n🏆 종목별 성과 TOP 10")
    print("-"*70)
    print(f"{'종목':<12} {'이름':<15} {'거래수':<8} {'승률':<8} {'평균수익':<10}")
    print("-"*70)
    top_symbols = by_symbol.sort_values('win_rate', ascending=False).head(10)
    for _, row in top_symbols.iterrows():
        print(f"{row['symbol']:<12} {row['name']:<15} {int(row['trades']):<8} {row['win_rate']:.0f}%    {row['avg_pnl']:+.2f}%")
    
    # 거래 내역 샘플
    print(f"\n📋 최근 거래 내역 (최근 20개)")
    print("-"*70)
    print(f"{'종목':<10} {'진입일':<12} {'청산일':<12} {'수익률':<10} {'결과':<6} {'사유'}")
    print("-"*70)
    recent_trades = sorted(all_trades, key=lambda x: x['entry_date'], reverse=True)[:20]
    for t in recent_trades:
        print(f"{t['symbol']:<10} {t['entry_date']:<12} {t['exit_date']:<12} {t['net_pnl_rate']:+.2f}%    {t['result']:<6} {t['exit_reason']}")
    
    # 파일 저장
    report_md = output_path.replace('.json', '.md')
    with open(report_md, 'w', encoding='utf-8') as f:
        f.write("# RSI+BB 미국 주식/가상화폐 백테스트 리포트\n\n")
        f.write(f"**생성일:** {datetime.now().strftime('%Y-%m-%d %H:%M')}\n\n")
        f.write(f"**기간:** 2024-01-01 ~ 2025-03-30\n\n")
        f.write("## 전체 통계\n\n")
        f.write(f"- 총 거래: {total}회\n")
        f.write(f"- 승률: {win_rate:.1f}%\n")
        f.write(f"- 총 수익률: +{total_return:.2f}%\n")
        f.write(f"- 평균 수익/거래: {avg_pnl:.2f}%\n")
        f.write(f"- 손익비: 1:{abs(avg_win/avg_loss):.1f}\n\n")
        
        f.write("## 종목별 성과\n\n")
        f.write("| 종목 | 이름 | 거래수 | 승률 | 평균수익률 |\n")
        f.write("|:---|:---|---:|---:|---:|\n")
        for _, row in by_symbol.iterrows():
            f.write(f"| {row['symbol']} | {row['name']} | {int(row['trades'])} | {row['win_rate']:.0f}% | {row['avg_pnl']:+.2f}% |\n")
        
        f.write("\n## 거래 내역\n\n")
        f.write("| 종목 | 진입일 | 청산일 | 진입가 | 청산가 | 수익률 | 결과 |\n")
        f.write("|:---|:---|:---|---:|---:|---:|:---:|\n")
        for t in all_trades[:50]:
            f.write(f"| {t['symbol']} | {t['entry_date']} | {t['exit_date']} | {t['entry_price']} | {t['exit_price']} | {t['net_pnl_rate']:+.2f}% | {t['result']} |\n")
    
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump({
            'summary': {
                'total_trades': total,
                'win_rate': win_rate,
                'total_return': total_return,
                'avg_pnl': avg_pnl,
                'profit_factor': profit_factor
            },
            'by_type': {
                'us_stocks': {'count': len(us_trades), 'return': ((1 + us_trades['net_pnl_rate']/100).prod() - 1) * 100 if len(us_trades) > 0 else 0},
                'crypto': {'count': len(crypto_trades), 'return': ((1 + crypto_trades['net_pnl_rate']/100).prod() - 1) * 100 if len(crypto_trades) > 0 else 0}
            },
            'trades': all_trades
        }, f, ensure_ascii=False, indent=2)
    
    print(f"\n📄 리포트 저장:")
    print(f"   Markdown: {report_md}")
    print(f"   JSON: {output_path}")


def main():
    print("="*70)
    print("🌍 RSI+BB 글로벌 백테스트")
    print(f"   실행시간: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print("="*70)
    
    all_trades = []
    
    # 미국 주식 백테스트
    try:
        us_backtest = USStockBacktest()
        us_trades = us_backtest.run()
        all_trades.extend(us_trades)
    except Exception as e:
        print(f"\n⚠️ 미국 주식 백테스트 오류: {e}")
    
    # 가상화폐 백테스트
    try:
        crypto_backtest = CryptoBacktest()
        crypto_trades = crypto_backtest.run()
        all_trades.extend(crypto_trades)
    except Exception as e:
        print(f"\n⚠️ 가상화폐 백테스트 오류: {e}")
    
    # 리포트 생성
    if all_trades:
        output_path = f'/root/.openclaw/workspace/strg/docs/global_backtest_{datetime.now().strftime("%Y%m%d")}.json'
        generate_report(all_trades, output_path)
    else:
        print("\n⚠️ 백테스트 결과 없음")
    
    print("\n" + "="*70)
    print("✅ 백테스트 완료!")
    print("="*70)


if __name__ == '__main__':
    main()
