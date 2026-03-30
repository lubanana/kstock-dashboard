#!/usr/bin/env python3
"""
WaveTrend 전략 - 가상화폐 확대 백테스트
대상: TOP 20 가상화폐
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import json
import warnings
warnings.filterwarnings('ignore')

class WaveTrendCryptoBacktest:
    """WaveTrend 전략 - 확대된 가상화폐 종목"""
    
    def __init__(self):
        self.fee_rate = 0.00015
        self.channel_len = 10
        self.avg_len = 21
        self.os_level = -53
        self.ob_level = 53
        
        # 확대된 종목 리스트 (TOP 20)
        self.coins = [
            # 메이저 코인
            {'symbol': 'BTC/USDT', 'name': 'Bitcoin', 'tier': 'Major'},
            {'symbol': 'ETH/USDT', 'name': 'Ethereum', 'tier': 'Major'},
            {'symbol': 'BNB/USDT', 'name': 'Binance Coin', 'tier': 'Major'},
            {'symbol': 'SOL/USDT', 'name': 'Solana', 'tier': 'Major'},
            {'symbol': 'XRP/USDT', 'name': 'Ripple', 'tier': 'Major'},
            
            # 대형 알트코인
            {'symbol': 'DOGE/USDT', 'name': 'Dogecoin', 'tier': 'Large'},
            {'symbol': 'ADA/USDT', 'name': 'Cardano', 'tier': 'Large'},
            {'symbol': 'AVAX/USDT', 'name': 'Avalanche', 'tier': 'Large'},
            {'symbol': 'LINK/USDT', 'name': 'Chainlink', 'tier': 'Large'},
            {'symbol': 'DOT/USDT', 'name': 'Polkadot', 'tier': 'Large'},
            {'symbol': 'MATIC/USDT', 'name': 'Polygon', 'tier': 'Large'},
            {'symbol': 'LTC/USDT', 'name': 'Litecoin', 'tier': 'Large'},
            {'symbol': 'BCH/USDT', 'name': 'Bitcoin Cash', 'tier': 'Large'},
            
            # 중형 알트코인
            {'symbol': 'UNI/USDT', 'name': 'Uniswap', 'tier': 'Mid'},
            {'symbol': 'ATOM/USDT', 'name': 'Cosmos', 'tier': 'Mid'},
            {'symbol': 'ETC/USDT', 'name': 'Ethereum Classic', 'tier': 'Mid'},
            {'symbol': 'XLM/USDT', 'name': 'Stellar', 'tier': 'Mid'},
            {'symbol': 'HBAR/USDT', 'name': 'Hedera', 'tier': 'Mid'},
            {'symbol': 'ICP/USDT', 'name': 'Internet Computer', 'tier': 'Mid'},
            {'symbol': 'VET/USDT', 'name': 'VeChain', 'tier': 'Mid'},
            {'symbol': 'FIL/USDT', 'name': 'Filecoin', 'tier': 'Mid'},
        ]
    
    def calculate_wavetrend(self, df):
        """WaveTrend (LazyBear) 계산"""
        df = df.copy()
        
        hlc3 = (df['High'] + df['Low'] + df['Close']) / 3
        esa = hlc3.ewm(span=self.channel_len, adjust=False).mean()
        de = abs(hlc3 - esa).ewm(span=self.channel_len, adjust=False).mean()
        ci = (hlc3 - esa) / (0.015 * de)
        
        df['WT1'] = ci.ewm(span=self.avg_len, adjust=False).mean()
        df['WT2'] = df['WT1'].rolling(window=4).mean()
        
        # 크로스오버 신호
        df['Buy_Signal'] = (df['WT1'] < self.os_level) & (df['WT1'] > df['WT2'])
        df['Sell_Signal'] = (df['WT1'] > self.ob_level) | ((df['WT1'].shift(1) > df['WT2'].shift(1)) & (df['WT1'] <= df['WT2']))
        
        return df
    
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
            df = df[df.index <= end_date]
            
            return df
        except Exception as e:
            return None
    
    def backtest_coin(self, coin, start_date='2024-01-01', end_date='2025-03-30'):
        """단일 코인 백테스트"""
        symbol = coin['symbol']
        name = coin['name']
        
        df = self.get_data(symbol, start_date, end_date)
        if df is None:
            return None, "데이터 없음"
        
        df = self.calculate_wavetrend(df)
        
        trades = []
        position = None
        entry_price = entry_date = entry_wt = None
        
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
                
                holding_days = (pd.to_datetime(date) - pd.to_datetime(entry_date)).days
                
                trades.append({
                    'symbol': symbol,
                    'name': name,
                    'tier': coin['tier'],
                    'entry_date': str(entry_date)[:10],
                    'exit_date': str(date)[:10],
                    'entry_price': round(entry_price, 2),
                    'exit_price': round(exit_price, 2),
                    'entry_wt': round(entry_wt, 1),
                    'exit_wt': round(row['WT1'], 1),
                    'holding_days': holding_days,
                    'net_pnl_rate': round(net_pnl_rate, 2),
                    'result': 'WIN' if net_pnl_rate > 0 else 'LOSS'
                })
                position = None
        
        return trades, None
    
    def run(self, start_date='2024-01-01', end_date='2025-03-30'):
        """전체 백테스트 실행"""
        print("="*70)
        print("📊 WaveTrend 가상화폐 백테스트 (확대版)")
        print(f"   기간: {start_date} ~ {end_date}")
        print(f"   대상: {len(self.coins)}개 종목")
        print("="*70)
        
        all_trades = []
        results_by_tier = {'Major': [], 'Large': [], 'Mid': []}
        coin_results = []
        
        for i, coin in enumerate(self.coins, 1):
            print(f"[{i:2d}/{len(self.coins)}] {coin['symbol']:<12} ({coin['name']:<18}) [{coin['tier']}]", end=' ')
            
            trades, error = self.backtest_coin(coin, start_date, end_date)
            
            if trades:
                all_trades.extend(trades)
                results_by_tier[coin['tier']].extend(trades)
                wins = sum(1 for t in trades if t['result'] == 'WIN')
                win_rate = wins / len(trades) * 100
                avg_pnl = np.mean([t['net_pnl_rate'] for t in trades])
                
                coin_results.append({
                    'symbol': coin['symbol'],
                    'name': coin['name'],
                    'tier': coin['tier'],
                    'trades': len(trades),
                    'wins': wins,
                    'win_rate': win_rate,
                    'avg_pnl': avg_pnl
                })
                
                print(f"→ {len(trades)}거래 (승: {wins}, {win_rate:.0f}%, 평균 {avg_pnl:+.1f}%)")
            elif error:
                print(f"→ {error}")
            else:
                print("→ 신호 없음")
        
        return all_trades, results_by_tier, coin_results
    
    def generate_report(self, all_trades, results_by_tier, coin_results):
        """리포트 생성"""
        print("\n" + "="*70)
        print("📈 백테스트 결과 종합")
        print("="*70)
        
        if not all_trades:
            print("\n⚠️ 거래 내역 없음")
            return
        
        # 전체 통계
        df = pd.DataFrame(all_trades)
        total = len(df)
        wins = len(df[df['result'] == 'WIN'])
        win_rate = wins / total * 100
        total_return = ((1 + df['net_pnl_rate']/100).prod() - 1) * 100
        avg_pnl = df['net_pnl_rate'].mean()
        
        avg_win = df[df['result'] == 'WIN']['net_pnl_rate'].mean() if wins > 0 else 0
        avg_loss = df[df['result'] == 'LOSS']['net_pnl_rate'].mean() if (total - wins) > 0 else 0
        profit_factor = abs(avg_win / avg_loss) if avg_loss != 0 else 0
        
        print(f"\n📊 전체 통계")
        print(f"   총 거래: {total}회")
        print(f"   승 / 패: {wins}승 / {total-wins}패")
        print(f"   승률: {win_rate:.1f}%")
        print(f"   총 수익률: {total_return:+.2f}%")
        print(f"   평균 수익/거래: {avg_pnl:.2f}%")
        print(f"   Profit Factor: {profit_factor:.2f}")
        
        # 티어별 통계
        print(f"\n📊 티어별 성과")
        print("-"*70)
        for tier in ['Major', 'Large', 'Mid']:
            if results_by_tier[tier]:
                tier_df = pd.DataFrame(results_by_tier[tier])
                t_total = len(tier_df)
                t_wins = len(tier_df[tier_df['result'] == 'WIN'])
                t_win_rate = t_wins / t_total * 100
                t_return = ((1 + tier_df['net_pnl_rate']/100).prod() - 1) * 100
                print(f"   {tier:<6}: {t_total}거래 | 승률 {t_win_rate:.1f}% | 수익률 {t_return:+.2f}%")
        
        # 종목별 TOP
        print(f"\n🏆 종목별 성과 TOP 10")
        print("-"*70)
        top_coins = sorted(coin_results, key=lambda x: x['win_rate'], reverse=True)[:10]
        print(f"{'순위':<4} {'종목':<12} {'이름':<18} {'거래':<6} {'승률':<8} {'평균수익'}")
        print("-"*70)
        for i, c in enumerate(top_coins, 1):
            print(f"{i:<4} {c['symbol']:<12} {c['name']:<18} {c['trades']:<6} {c['win_rate']:.0f}%    {c['avg_pnl']:+.1f}%")
        
        # 보유기간 분석
        print(f"\n📊 보유기간 분석")
        avg_hold = df['holding_days'].mean()
        print(f"   평균 보유기간: {avg_hold:.1f}일")
        
        # 저장
        output = {
            'summary': {
                'total_trades': total,
                'win_rate': win_rate,
                'total_return': total_return,
                'profit_factor': profit_factor,
                'avg_holding_days': avg_hold
            },
            'by_tier': {
                tier: {
                    'trades': len(results_by_tier[tier]),
                    'wins': sum(1 for t in results_by_tier[tier] if t['result'] == 'WIN'),
                    'win_rate': sum(1 for t in results_by_tier[tier] if t['result'] == 'WIN') / len(results_by_tier[tier]) * 100 if results_by_tier[tier] else 0
                } for tier in ['Major', 'Large', 'Mid']
            },
            'coin_results': coin_results,
            'trades': all_trades
        }
        
        output_file = f'/root/.openclaw/workspace/strg/docs/wavetrend_crypto_extended_{datetime.now().strftime("%Y%m%d")}.json'
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(output, f, ensure_ascii=False, indent=2)
        
        print(f"\n📄 결과 저장: {output_file}")


def main():
    bt = WaveTrendCryptoBacktest()
    all_trades, results_by_tier, coin_results = bt.run()
    bt.generate_report(all_trades, results_by_tier, coin_results)
    
    print("\n" + "="*70)
    print("✅ 가상화폐 확대 백테스트 완료!")
    print("="*70)


if __name__ == '__main__':
    main()
