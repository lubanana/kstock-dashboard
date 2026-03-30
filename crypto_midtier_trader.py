#!/usr/bin/env python3
"""
Mid-tier 가상화폐 WaveTrend 자동매매 시스템
백테스트 승률 50%+, 수익률 +55% 종목 대상
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import json
import os
import sys

class WaveTrendMidCryptoTrader:
    """WaveTrend Mid-tier 가상화폐 트레이더"""
    
    def __init__(self, initial_capital=10000):  # $10,000
        self.initial_capital = initial_capital
        self.cash = initial_capital
        self.positions = {}
        
        # 파라미터
        self.fee_rate = 0.0006  # 바이낸스 수수료
        self.channel_len = 10
        self.avg_len = 21
        self.os_level = -53  # 과매도
        self.ob_level = 53   # 과매수
        
        # Mid-tier 종목만 (백테스트 우수 종목)
        self.coins = [
            {'symbol': 'UNI/USDT', 'name': 'Uniswap'},
            {'symbol': 'ATOM/USDT', 'name': 'Cosmos'},
            {'symbol': 'ICP/USDT', 'name': 'Internet Computer'},
            {'symbol': 'FIL/USDT', 'name': 'Filecoin'},
            {'symbol': 'XLM/USDT', 'name': 'Stellar'},
        ]
        
        self.trades = []
        self.state_file = '/root/.openclaw/workspace/strg/crypto_midtier_state.json'
        self.load_state()
    
    def load_state(self):
        if os.path.exists(self.state_file):
            with open(self.state_file, 'r') as f:
                state = json.load(f)
                self.cash = state.get('cash', self.initial_capital)
                self.positions = state.get('positions', {})
                self.trades = state.get('trades', [])
                print(f"📂 상태 로드: ${self.cash:,.2f}, 보유 {len(self.positions)}종목")
    
    def save_state(self):
        state = {
            'cash': self.cash,
            'positions': self.positions,
            'trades': self.trades,
            'last_updated': datetime.now().isoformat()
        }
        with open(self.state_file, 'w') as f:
            json.dump(state, f, indent=2)
    
    def calculate_wavetrend(self, df):
        hlc3 = (df['High'] + df['Low'] + df['Close']) / 3
        esa = hlc3.ewm(span=self.channel_len, adjust=False).mean()
        de = abs(hlc3 - esa).ewm(span=self.channel_len, adjust=False).mean()
        ci = (hlc3 - esa) / (0.015 * de)
        wt1 = ci.ewm(span=self.avg_len, adjust=False).mean()
        wt2 = wt1.rolling(window=4).mean()
        return wt1, wt2
    
    def get_data(self, symbol):
        try:
            import ccxt
            exchange = ccxt.binance({'enableRateLimit': True})
            since = exchange.parse8601((datetime.now() - timedelta(days=60)).isoformat())
            ohlcv = exchange.fetch_ohlcv(symbol, '1d', since)
            
            if len(ohlcv) < 30:
                return None
            
            df = pd.DataFrame(ohlcv, columns=['timestamp', 'Open', 'High', 'Low', 'Close', 'Volume'])
            df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
            df.set_index('timestamp', inplace=True)
            return df
        except:
            return None
    
    def check_signals(self, df):
        if len(df) < 30:
            return False, False, None, None
        
        wt1, wt2 = self.calculate_wavetrend(df)
        latest_wt1 = wt1.iloc[-1]
        latest_wt2 = wt2.iloc[-1]
        prev_wt1 = wt1.iloc[-2] if len(wt1) > 1 else latest_wt1
        prev_wt2 = wt2.iloc[-2] if len(wt2) > 1 else latest_wt2
        
        # 매수: WT1 < -53 (과매도) & WT1 > WT2 (상향 돌파)
        buy_signal = (latest_wt1 < self.os_level) and (latest_wt1 > latest_wt2)
        
        # 매도: WT1 > 53 (과매수) 또는 WT1 < WT2 (하향 돌파)
        sell_signal = (latest_wt1 > self.ob_level) or ((prev_wt1 > prev_wt2) and (latest_wt1 <= latest_wt2))
        
        return buy_signal, sell_signal, latest_wt1, latest_wt2
    
    def scan_and_trade(self):
        today = datetime.now().strftime('%Y-%m-%d')
        
        print(f"\n{'='*70}")
        print(f"🪙 Mid-tier 가상화폐 WaveTrend 트레이딩 - {today}")
        print(f"{'='*70}")
        print(f"💰 초기: ${self.initial_capital:,.2f} | 현금: ${self.cash:,.2f}")
        print(f"📈 보유: {len(self.positions)}종목")
        print(f"   대상: UNI, ATOM, ICP, FIL, XLM (백테스트 승률 50%+)")
        
        # 청산 체크
        print(f"\n[1] 기존 포지션 청산 체크")
        for symbol in list(self.positions.keys()):
            try:
                df = self.get_data(symbol)
                if df is None:
                    continue
                
                buy_sig, sell_sig, wt1, wt2 = self.check_signals(df)
                current_price = df['Close'].iloc[-1]
                
                if sell_sig:
                    pos = self.positions[symbol]
                    pnl_rate = (current_price - pos['entry_price']) / pos['entry_price']
                    net_pnl = pnl_rate * pos['amount'] * (1 - self.fee_rate * 2)
                    
                    self.cash += pos['amount'] * current_price * (1 - self.fee_rate)
                    
                    self.trades.append({
                        'symbol': symbol, 'entry': pos['entry_date'], 'exit': today,
                        'entry_price': pos['entry_price'], 'exit_price': current_price,
                        'pnl_rate': pnl_rate * 100, 'result': 'WIN' if pnl_rate > 0 else 'LOSS'
                    })
                    
                    del self.positions[symbol]
                    emoji = "🟢" if pnl_rate > 0 else "🔴"
                    print(f"{emoji} 청산: {symbol} @ ${current_price:.2f} ({pnl_rate*100:+.1f}%)")
            except Exception as e:
                print(f"   ⚠️ {symbol}: {str(e)[:30]}")
        
        # 신규 매수
        print(f"\n[2] 신규 매수 스캔 (WT < -53)")
        signals_found = 0
        
        for coin in self.coins:
            if signals_found >= 2:
                break
            if coin['symbol'] in self.positions:
                continue
            
            try:
                df = self.get_data(coin['symbol'])
                if df is None:
                    continue
                
                buy_sig, sell_sig, wt1, wt2 = self.check_signals(df)
                current_price = df['Close'].iloc[-1]
                
                if buy_sig:
                    signals_found += 1
                    invest = self.cash * 0.3  # 30%씩 투자
                    amount = invest / current_price
                    
                    self.positions[coin['symbol']] = {
                        'name': coin['name'],
                        'entry_price': current_price,
                        'entry_date': today,
                        'amount': amount,
                        'wt1': wt1
                    }
                    self.cash -= invest
                    
                    print(f"\n✅ 매수: {coin['symbol']} ({coin['name']})")
                    print(f"   WT1: {wt1:.1f} | 가격: ${current_price:.2f} | 수량: {amount:.4f}")
            except:
                continue
        
        if signals_found == 0:
            print("   매수 신호 없음")
        
        # 통계
        total_value = self.cash
        for symbol, pos in self.positions.items():
            try:
                df = self.get_data(symbol)
                if df is not None:
                    total_value += pos['amount'] * df['Close'].iloc[-1]
            except:
                total_value += pos['amount'] * pos['entry_price']
        
        print(f"\n📊 포트폴리오")
        print(f"   총 자산: ${total_value:,.2f} ({(total_value/self.initial_capital-1)*100:+.1f}%)")
        
        if self.trades:
            wins = sum(1 for t in self.trades if t['result'] == 'WIN')
            print(f"   거래: {len(self.trades)}회 | 승률 {wins/len(self.trades)*100:.1f}%")
        
        self.save_state()


def main():
    trader = WaveTrendMidCryptoTrader(initial_capital=10000)
    
    print("="*70)
    print("🚀 Mid-tier 가상화폐 WaveTrend 자동매매")
    print("   대상: UNI, ATOM, ICP, FIL, XLM")
    print("   백테스트: 승률 50%+, 수익률 +55%")
    print("="*70)
    
    trader.scan_and_trade()
    
    print("\n✅ 완료!")
    print(f"   상태: {trader.state_file}")


if __name__ == '__main__':
    main()
