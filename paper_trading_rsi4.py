#!/usr/bin/env python3
"""
RSI(4) 개선 전략 - 한국 주식 페이퍼 트레이딩
승률 61.7% 전략 실전 적용
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import json
import os
import sys

sys.path.insert(0, '/root/.openclaw/workspace/strg')
from fdr_wrapper import get_price

def calculate_rsi(prices, period=4):
    delta = prices.diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
    rs = gain / loss
    return 100 - (100 / (1 + rs))

class RSI4PaperTrader:
    """RSI(4) 페이퍼 트레이딩 시스템"""
    
    def __init__(self, initial_capital=10000000):
        self.initial_capital = initial_capital
        self.cash = initial_capital
        self.positions = {}
        
        # 파라미터
        self.fee_rate = 0.00015
        self.sl_rate = 0.02
        self.tp_rate = 0.03
        self.max_hold_days = 2
        self.position_ratio = 0.5
        
        self.trades = []
        self.daily_logs = []
        self.state_file = '/root/.openclaw/workspace/strg/paper_trading_rsi4_state.json'
        self.load_state()
    
    def load_state(self):
        if os.path.exists(self.state_file):
            with open(self.state_file, 'r') as f:
                state = json.load(f)
                self.cash = state.get('cash', self.initial_capital)
                self.positions = state.get('positions', {})
                self.trades = state.get('trades', [])
                print(f"📂 상태 로드: 현금 {self.cash:,.0f}원, 보유 {len(self.positions)}종목")
    
    def save_state(self):
        state = {
            'cash': self.cash,
            'positions': self.positions,
            'trades': self.trades,
            'last_updated': datetime.now().isoformat()
        }
        with open(self.state_file, 'w') as f:
            json.dump(state, f, indent=2)
    
    def check_buy_signal(self, df):
        """RSI(4) 매수 신호 체크"""
        if len(df) < 10:
            return False, None
        
        df = df.copy()
        df['RSI'] = calculate_rsi(df['Close'], 4)
        df['Volume_MA'] = df['Volume'].rolling(window=20).mean()
        df['Volume_Ratio'] = df['Volume'] / df['Volume_MA']
        df['Return_5d'] = df['Close'].pct_change(5) * 100
        
        latest = df.iloc[-1]
        
        signal = {
            'rsi': latest['RSI'],
            'price': latest['Close'],
            'volume_ratio': latest['Volume_Ratio'],
            'return_5d': latest['Return_5d']
        }
        
        # RSI(4) < 20 + 거래량 1.5배 + 5일 수익률 < -5%
        is_signal = (
            latest['RSI'] < 20 and
            latest['Volume_Ratio'] >= 1.5 and
            latest['Return_5d'] < -5
        )
        
        return is_signal, signal
    
    def check_sell_signals(self, ticker, current_price, current_date):
        if ticker not in self.positions:
            return None
        
        pos = self.positions[ticker]
        entry_price = pos['entry_price']
        entry_date = datetime.strptime(pos['entry_date'], '%Y-%m-%d')
        current_dt = datetime.strptime(current_date, '%Y-%m-%d')
        
        holding_days = (current_dt - entry_date).days
        pnl_rate = (current_price - entry_price) / entry_price
        
        if pnl_rate <= -self.sl_rate:
            return {'reason': 'STOP_LOSS', 'pnl_rate': pnl_rate}
        elif pnl_rate >= self.tp_rate:
            return {'reason': 'TAKE_PROFIT', 'pnl_rate': pnl_rate}
        elif holding_days >= self.max_hold_days:
            return {'reason': 'TIME_EXIT', 'pnl_rate': pnl_rate}
        
        return None
    
    def enter_position(self, ticker, name, signal):
        if ticker in self.positions:
            return False
        
        price = signal['price']
        invest_amount = self.cash * self.position_ratio
        quantity = int(invest_amount / price)
        
        if quantity < 1:
            return False
        
        fee = price * quantity * self.fee_rate
        total_cost = price * quantity + fee
        
        if total_cost > self.cash:
            return False
        
        self.positions[ticker] = {
            'name': name,
            'entry_price': price,
            'entry_date': datetime.now().strftime('%Y-%m-%d'),
            'quantity': quantity,
            'entry_rsi': signal['rsi']
        }
        self.cash -= total_cost
        
        print(f"✅ 매수: {ticker} ({name})")
        print(f"   RSI(4): {signal['rsi']:.1f} | 가격: {price:,.0f}원 | 수량: {quantity}주")
        return True
    
    def exit_position(self, ticker, exit_info):
        if ticker not in self.positions:
            return False
        
        pos = self.positions[ticker]
        df = get_price(ticker, (datetime.now() - timedelta(days=7)).strftime('%Y-%m-%d'), datetime.now().strftime('%Y-%m-%d'))
        if df is None or len(df) == 0:
            return False
        
        exit_price = df['Close'].iloc[-1]
        quantity = pos['quantity']
        pnl_rate = exit_info['pnl_rate']
        
        gross_pnl = (exit_price - pos['entry_price']) * quantity
        fee = (pos['entry_price'] + exit_price) * quantity * self.fee_rate
        net_pnl = gross_pnl - fee
        
        proceeds = exit_price * quantity - fee
        self.cash += proceeds
        
        trade = {
            'ticker': ticker, 'name': pos['name'],
            'entry_date': pos['entry_date'],
            'exit_date': datetime.now().strftime('%Y-%m-%d'),
            'entry_price': pos['entry_price'], 'exit_price': exit_price,
            'quantity': quantity, 'entry_rsi': pos['entry_rsi'],
            'exit_reason': exit_info['reason'],
            'net_pnl': net_pnl, 'result': 'WIN' if net_pnl > 0 else 'LOSS'
        }
        self.trades.append(trade)
        del self.positions[ticker]
        
        emoji = "🟢" if net_pnl > 0 else "🔴"
        print(f"{emoji} 청산: {ticker} | 수익률: {pnl_rate*100:+.1f}% | {exit_info['reason']}")
        return True
    
    def scan_and_trade(self, stocks):
        today = datetime.now().strftime('%Y-%m-%d')
        
        print(f"\n{'='*70}")
        print(f"📊 RSI(4) 페이퍼 트레이딩 - {today}")
        print(f"{'='*70}")
        print(f"💰 초기자본: {self.initial_capital:,.0f}원 | 현금: {self.cash:,.0f}원")
        print(f"📈 보유포지션: {len(self.positions)}종목")
        
        # 청산 체크
        print(f"\n[1] 포지션 청산 체크")
        for ticker in list(self.positions.keys()):
            try:
                df = get_price(ticker, (datetime.now() - timedelta(days=7)).strftime('%Y-%m-%d'), today)
                if df is not None and len(df) > 0:
                    current_price = df['Close'].iloc[-1]
                    exit_info = self.check_sell_signals(ticker, current_price, today)
                    if exit_info:
                        self.exit_position(ticker, exit_info)
            except:
                pass
        
        # 신규 매수
        print(f"\n[2] 신규 매수 스캔 (RSI(4) < 20)")
        signals_found = 0
        
        for stock in stocks:
            if signals_found >= 3:
                break
            if stock['code'] in self.positions:
                continue
            
            try:
                df = get_price(stock['code'], (datetime.now() - timedelta(days=30)).strftime('%Y-%m-%d'), today)
                if df is None or len(df) < 10:
                    continue
                
                is_signal, signal = self.check_buy_signal(df)
                if is_signal:
                    signals_found += 1
                    print(f"\n🎯 신호: {stock['code']} ({stock['name']})")
                    print(f"   RSI(4): {signal['rsi']:.1f} | 5일수익률: {signal['return_5d']:.1f}%")
                    self.enter_position(stock['code'], stock['name'], signal)
            except:
                continue
        
        if signals_found == 0:
            print("   매수 신호 없음")
        
        # 통계
        total_value = self.cash
        for ticker, pos in self.positions.items():
            total_value += pos['entry_price'] * pos['quantity']
        
        print(f"\n📊 포트폴리오 현황")
        print(f"   총 자산: {total_value:,.0f}원 (수익률: {(total_value/self.initial_capital-1)*100:+.1f}%)")
        
        if self.trades:
            wins = sum(1 for t in self.trades if t['result'] == 'WIN')
            print(f"   거래 통계: {len(self.trades)}거래 | 승률 {wins/len(self.trades)*100:.1f}%")
        
        self.save_state()


def main():
    trader = RSI4PaperTrader(initial_capital=10000000)
    
    stocks = [
        {'code': '005930', 'name': '삼성전자'}, {'code': '000660', 'name': 'SK하이닉스'},
        {'code': '005380', 'name': '현대차'}, {'code': '035420', 'name': 'NAVER'},
        {'code': '035720', 'name': '카카오'}, {'code': '051910', 'name': 'LG화학'},
        {'code': '006400', 'name': '삼성SDI'}, {'code': '028260', 'name': '삼성물산'},
        {'code': '068270', 'name': '셀트리온'}, {'code': '207940', 'name': '삼성바이오'},
        {'code': '012330', 'name': '현대모비스'}, {'code': '005490', 'name': 'POSCO'},
        {'code': '105560', 'name': 'KB금융'}, {'code': '055550', 'name': '신한지주'},
        {'code': '032830', 'name': '삼성생명'}, {'code': '009150', 'name': '삼성전기'},
        {'code': '003670', 'name': '포스코퓨처엤'}, {'code': '086790', 'name': '하나금융'},
        {'code': '033780', 'name': 'KT&G'}, {'code': '000270', 'name': '기아'},
    ]
    
    print("="*70)
    print("🚀 RSI(4) 개선 전략 페이퍼 트레이딩 시작")
    print("   조건: RSI(4) < 20 + 거래량 1.5배 + 5일 수익률 < -5%")
    print("   예상 승률: 61.7%")
    print("="*70)
    
    trader.scan_and_trade(stocks)
    
    print("\n✅ 페이퍼 트레이딩 완료!")
    print(f"   상태 파일: {trader.state_file}")


if __name__ == '__main__':
    main()
