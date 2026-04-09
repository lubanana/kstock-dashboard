#!/usr/bin/env python3
"""
고승률 매매 전략 구현 (High Win Rate Strategy)
승률 60%+ 목표의 실전 매매 시스템

Usage:
    python3 high_win_rate_trader.py --mode backtest --symbol BTC
    python3 high_win_rate_trader.py --mode live --duration 60
"""

import sys
sys.path.insert(0, '.')

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
import json
import requests
import time


class BithumbPublicAPI:
    """빗썸 Public API"""
    
    BASE_URL = "https://api.bithumb.com"
    
    def __init__(self):
        self.session = requests.Session()
    
    def get_ohlcv(self, order_currency: str, chart_intervals: str = "24h", count: int = 100) -> pd.DataFrame:
        """OHLCV 데이터 조회"""
        url = f"{self.BASE_URL}/public/candlestick/{order_currency}_KRW/{chart_intervals}"
        try:
            response = self.session.get(url, timeout=10)
            data = response.json()
            
            if data.get('status') != '0000':
                return pd.DataFrame()
            
            raw_data = data.get('data', [])
            if not raw_data:
                return pd.DataFrame()
            
            df = pd.DataFrame(raw_data, columns=['timestamp', 'open', 'close', 'high', 'low', 'volume'])
            df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
            df.set_index('timestamp', inplace=True)
            df = df.astype(float)
            return df.sort_index()
        except Exception as e:
            return pd.DataFrame()
    
    def get_ticker(self, order_currency: str) -> Dict:
        """현재가 조회"""
        url = f"{self.BASE_URL}/public/ticker/{order_currency}_KRW"
        try:
            response = self.session.get(url, timeout=10)
            data = response.json()
            return data if data.get('status') == '0000' else {}
        except:
            return {}


class HighWinRateStrategy:
    """
    고승률 매매 전략 엔진
    - 추세추종 + 눌림목
    - 목표 승률: 60%+
    """
    
    def __init__(self, initial_balance: float = 10_000_000):
        self.api = BithumbPublicAPI()
        self.initial_balance = initial_balance
        self.balance = initial_balance
        self.positions = {}
        self.trade_history = []
        
        # 전략 파라미터
        self.stop_loss_pct = 0.07      # 7% 손절
        self.take_profit_pct = 0.15    # 15% 익절
        self.hold_days = 7             # 7일 보유
        self.risk_per_trade = 0.02     # 계좌 2% 리스크
    
    def calculate_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        """기술적 지표 계산"""
        df = df.copy()
        
        # EMA
        df['ema20'] = df['close'].ewm(span=20, adjust=False).mean()
        df['ema60'] = df['close'].ewm(span=60, adjust=False).mean()
        
        # RSI
        delta = df['close'].diff()
        gain = delta.where(delta > 0, 0)
        loss = -delta.where(delta < 0, 0)
        avg_gain = gain.ewm(span=14, adjust=False).mean()
        avg_loss = loss.ewm(span=14, adjust=False).mean()
        rs = avg_gain / avg_loss.replace(0, np.nan)
        df['rsi'] = 100 - (100 / (1 + rs))
        df['rsi'] = df['rsi'].fillna(50)
        
        # 거래량 이동평균
        df['vol_ma20'] = df['volume'].rolling(20).mean()
        
        return df
    
    def check_entry_signal(self, df: pd.DataFrame) -> Tuple[bool, Dict]:
        """
        진입 신호 확인
        
        Returns:
            (signal_bool, signal_info)
        """
        if len(df) < 60:
            return False, {}
        
        latest = df.iloc[-1]
        
        # 조건 1: 상승 추세 (20EMA > 60EMA)
        trend_up = latest['ema20'] > latest['ema60']
        
        # 조건 2: RSI 중립 구간 (40~60)
        rsi_ok = 40 <= latest['rsi'] <= 60
        
        # 조건 3: 거래량 증가
        volume_ok = latest['volume'] > latest['vol_ma20'] * 1.2
        
        # 조건 4: 눌림목 (EMA20 근처)
        near_ema = latest['close'] > latest['ema20'] * 0.98
        
        signal = trend_up and rsi_ok and volume_ok and near_ema
        
        info = {
            'price': latest['close'],
            'ema20': latest['ema20'],
            'ema60': latest['ema60'],
            'rsi': latest['rsi'],
            'volume_ratio': latest['volume'] / latest['vol_ma20'] if latest['vol_ma20'] > 0 else 0,
            'trend_up': trend_up,
            'rsi_ok': rsi_ok,
            'volume_ok': volume_ok,
            'near_ema': near_ema
        }
        
        return signal, info
    
    def calculate_position_size(self, entry_price: float, stop_price: float) -> float:
        """포지션 크기 계산 (2% 리스크)"""
        risk_amount = self.balance * self.risk_per_trade
        risk_per_unit = entry_price - stop_price
        
        if risk_per_unit <= 0:
            return 0
        
        position_value = risk_amount / (risk_per_unit / entry_price)
        volume = position_value / entry_price
        
        return volume
    
    def backtest(self, coin: str, days: int = 200) -> Dict:
        """
        백테스트 실행
        
        Returns:
            backtest results dict
        """
        print(f"\n{'='*70}")
        print(f"🔥 고승률 전략 백테스트: {coin}")
        print(f"{'='*70}")
        print(f"전략: 추세추종 + 눌림목 (승률 목표 60%+)")
        print(f"진입: 20EMA>60EMA, RSI 40~60, 거래량 1.2x+, 눌림목")
        print(f"청산: +15% 익절 / -7% 손절 / 7일 보유")
        print(f"{'='*70}\n")
        
        # 데이터 로드
        df = self.api.get_ohlcv(coin, count=days)
        if df.empty or len(df) < 60:
            print(f"❌ 데이터 부족")
            return {}
        
        df = self.calculate_indicators(df)
        
        trades = []
        in_position = False
        entry_price = 0
        entry_idx = 0
        
        for i in range(60, len(df) - self.hold_days):
            if not in_position:
                # 진입 신호 확인
                signal, info = self.check_entry_signal(df.iloc[:i+1])
                
                if signal:
                    entry_price = df['close'].iloc[i]
                    entry_idx = i
                    in_position = True
                    
                    # 손절가/목표가 설정
                    stop_loss = entry_price * (1 - self.stop_loss_pct)
                    take_profit = entry_price * (1 + self.take_profit_pct)
                    
                    trades.append({
                        'entry_date': df.index[i],
                        'entry_price': entry_price,
                        'stop_loss': stop_loss,
                        'take_profit': take_profit,
                        'info': info
                    })
            else:
                # 청산 확인
                current_price = df['close'].iloc[i]
                hold_count = i - entry_idx
                
                exit_price = None
                exit_reason = None
                
                # 손절 체크
                if df['low'].iloc[i] <= stop_loss:
                    exit_price = stop_loss
                    exit_reason = 'STOP_LOSS'
                # 익절 체크
                elif df['high'].iloc[i] >= take_profit:
                    exit_price = take_profit
                    exit_reason = 'TAKE_PROFIT'
                # 보유 만기
                elif hold_count >= self.hold_days:
                    exit_price = current_price
                    exit_reason = 'TIME_EXIT'
                
                if exit_price:
                    pnl_pct = (exit_price - entry_price) / entry_price * 100
                    trades[-1].update({
                        'exit_date': df.index[i],
                        'exit_price': exit_price,
                        'pnl_pct': pnl_pct,
                        'exit_reason': exit_reason,
                        'hold_days': hold_count
                    })
                    in_position = False
        
        # 결과 계산
        if not trades:
            print("❌ 거래 없음")
            return {}
        
        completed_trades = [t for t in trades if 'pnl_pct' in t]
        if not completed_trades:
            print("❌ 완료된 거래 없음")
            return {}
        
        wins = len([t for t in completed_trades if t['pnl_pct'] > 0])
        losses = len(completed_trades) - wins
        win_rate = wins / len(completed_trades) * 100
        
        avg_return = np.mean([t['pnl_pct'] for t in completed_trades])
        max_profit = max([t['pnl_pct'] for t in completed_trades])
        max_loss = min([t['pnl_pct'] for t in completed_trades])
        
        # 누적 수익률 계산
        total_return = 1
        for t in completed_trades:
            total_return *= (1 + t['pnl_pct'] / 100)
        total_return_pct = (total_return - 1) * 100
        
        # 결과 출력
        print(f"📊 백테스트 결과")
        print(f"{'='*70}")
        print(f"총 거래: {len(completed_trades)}회")
        print(f"승률: {wins}/{len(completed_trades)} ({win_rate:.1f}%)")
        print(f"평균 수익률: {avg_return:+.2f}%")
        print(f"총 수익률: {total_return_pct:+.2f}%")
        print(f"최대 수익: {max_profit:+.2f}%")
        print(f"최대 손실: {max_loss:+.2f}%")
        print(f"\n📋 청산 사유:")
        reasons = {}
        for t in completed_trades:
            r = t['exit_reason']
            reasons[r] = reasons.get(r, 0) + 1
        for reason, count in reasons.items():
            print(f"   {reason}: {count}회")
        
        print(f"\n📋 최근 10개 거래:")
        for t in completed_trades[-10:]:
            emoji = '🟢' if t['pnl_pct'] > 0 else '🔴'
            print(f"   {emoji} {t['entry_date'].strftime('%Y-%m-%d')} ~ "
                  f"{t['exit_date'].strftime('%Y-%m-%d')}: "
                  f"{t['pnl_pct']:+.1f}% ({t['exit_reason']})")
        
        return {
            'coin': coin,
            'total_trades': len(completed_trades),
            'wins': wins,
            'losses': losses,
            'win_rate': win_rate,
            'avg_return': avg_return,
            'total_return_pct': total_return_pct,
            'trades': completed_trades
        }


def main():
    """메인 실행"""
    import argparse
    
    parser = argparse.ArgumentParser(description='고승률 매매 전략')
    parser.add_argument('--mode', choices=['backtest', 'scan'], default='backtest',
                       help='실행 모드')
    parser.add_argument('--coin', default='BTC', help='대상 코인')
    parser.add_argument('--days', type=int, default=200, help='백테스트 일수')
    
    args = parser.parse_args()
    
    trader = HighWinRateStrategy()
    
    if args.mode == 'backtest':
        result = trader.backtest(args.coin, args.days)
        
        # JSON 저장
        if result:
            filename = f"high_win_rate_backtest_{args.coin}_{datetime.now().strftime('%Y%m%d')}.json"
            with open(filename, 'w', encoding='utf-8') as f:
                # trades 제외하고 저장
                save_result = {k: v for k, v in result.items() if k != 'trades'}
                json.dump(save_result, f, ensure_ascii=False, indent=2)
            print(f"\n💾 결과 저장: {filename}")
    
    elif args.mode == 'scan':
        print("스캔 모드는 개발 중...")


if __name__ == '__main__':
    main()
