#!/usr/bin/env python3
"""
Bithumb Trading Simulator - 빗썸 매매 시뮬레이션
Public API를 활용한 백테스트 및 시뮬레이션
"""

import sys
sys.path.insert(0, '.')
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
import json
import time

# python-bithumb 임포트 시도
try:
    from bithumb import Bithumb
    BITHUMB_AVAILABLE = True
except ImportError:
    BITHUMB_AVAILABLE = False
    print("⚠️ python-bithumb 미설치, HTTP API 직접 사용")

import requests


class BithumbPublicAPI:
    """빗썸 Public API 래퍼"""
    
    BASE_URL = "https://api.bithumb.com"
    
    def __init__(self):
        self.session = requests.Session()
        
    def get_ticker(self, order_currency: str = "ALL", payment_currency: str = "KRW") -> Dict:
        """현재가 조회"""
        url = f"{self.BASE_URL}/public/ticker/{order_currency}_{payment_currency}"
        try:
            response = self.session.get(url, timeout=10)
            data = response.json()
            return data if data.get('status') == '0000' else {}
        except Exception as e:
            print(f"⚠️ Ticker API 오류: {e}")
            return {}
    
    def get_ohlcv(self, order_currency: str, payment_currency: str = "KRW", 
                  chart_intervals: str = "24h", count: int = 200) -> pd.DataFrame:
        """캔들스틱 데이터 조회"""
        url = f"{self.BASE_URL}/public/candlestick/{order_currency}_{payment_currency}/{chart_intervals}"
        try:
            response = self.session.get(url, timeout=10)
            data = response.json()
            
            if data.get('status') != '0000':
                return pd.DataFrame()
            
            # 데이터 파싱 [timestamp, open, close, high, low, volume]
            raw_data = data.get('data', [])
            if not raw_data:
                return pd.DataFrame()
            
            df = pd.DataFrame(raw_data, columns=['timestamp', 'open', 'close', 'high', 'low', 'volume'])
            df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
            df.set_index('timestamp', inplace=True)
            df = df.astype(float)
            
            return df.sort_index()
        except Exception as e:
            print(f"⚠️ OHLCV API 오류: {e}")
            return pd.DataFrame()
    
    def get_orderbook(self, order_currency: str, payment_currency: str = "KRW") -> Dict:
        """호가 정보 조회"""
        url = f"{self.BASE_URL}/public/orderbook/{order_currency}_{payment_currency}"
        try:
            response = self.session.get(url, timeout=10)
            data = response.json()
            return data if data.get('status') == '0000' else {}
        except Exception as e:
            print(f"⚠️ Orderbook API 오류: {e}")
            return {}
    
    def get_market_all(self) -> List[str]:
        """전체 마켓 리스트"""
        url = f"{self.BASE_URL}/public/ticker/ALL_KRW"
        try:
            response = self.session.get(url, timeout=10)
            data = response.json()
            
            if data.get('status') == '0000' and 'data' in data:
                # BTC, ETH 등 코인 코드 추출
                return [k for k in data['data'].keys() if k not in ['date']]
            return []
        except Exception as e:
            print(f"⚠️ Market API 오류: {e}")
            return []


class BithumbTradingSimulator:
    """빗썸 매매 시뮬레이션 엔진"""
    
    def __init__(self, initial_balance: float = 10_000_000, fee_rate: float = 0.0005):
        """
        Parameters:
        -----------
        initial_balance : float
            초기 자본 (KRW), 기본 1,000만원
        fee_rate : float
            거래 수수료 (0.0005 = 0.05%)
        """
        self.api = BithumbPublicAPI()
        self.initial_balance = initial_balance
        self.fee_rate = fee_rate
        
        # 계좌 상태
        self.balance_krw = initial_balance
        self.positions = {}  # {coin: {'volume': 수량, 'avg_price': 평균매입가, 'entry_time': 진입시간}}
        self.trade_history = []
        
        # 전략 파라미터
        self.stop_loss_pct = 0.03  # 3% 손절
        self.take_profit_pct = 0.09  # 9% 익절
        
    def reset(self):
        """시뮬레이션 초기화"""
        self.balance_krw = self.initial_balance
        self.positions = {}
        self.trade_history = []
        
    def calculate_position_size(self, price: float, risk_pct: float = 0.02) -> float:
        """포지션 크기 계산 (2% 리스크)"""
        risk_amount = self.balance_krw * risk_pct
        position_value = risk_amount / self.stop_loss_pct
        volume = position_value / price
        return volume
    
    def buy(self, coin: str, price: float, volume: float, reason: str = "") -> bool:
        """매수 실행"""
        amount = price * volume
        fee = amount * self.fee_rate
        total_cost = amount + fee
        
        if total_cost > self.balance_krw:
            return False
        
        self.balance_krw -= total_cost
        
        if coin in self.positions:
            # 추가 매수 - 평균단가 조정
            old_volume = self.positions[coin]['volume']
            old_avg = self.positions[coin]['avg_price']
            new_volume = old_volume + volume
            new_avg = (old_volume * old_avg + volume * price) / new_volume
            self.positions[coin]['volume'] = new_volume
            self.positions[coin]['avg_price'] = new_avg
        else:
            self.positions[coin] = {
                'volume': volume,
                'avg_price': price,
                'entry_time': datetime.now(),
                'entry_reason': reason
            }
        
        self.trade_history.append({
            'type': 'BUY',
            'coin': coin,
            'price': price,
            'volume': volume,
            'amount': amount,
            'fee': fee,
            'timestamp': datetime.now(),
            'reason': reason
        })
        
        return True
    
    def sell(self, coin: str, price: float, reason: str = "") -> bool:
        """매도 실행"""
        if coin not in self.positions or self.positions[coin]['volume'] <= 0:
            return False
        
        volume = self.positions[coin]['volume']
        avg_price = self.positions[coin]['avg_price']
        
        amount = price * volume
        fee = amount * self.fee_rate
        net_proceeds = amount - fee
        
        # 손익 계산
        cost_basis = avg_price * volume
        pnl = amount - cost_basis - fee - (cost_basis * self.fee_rate)  # 매수+매도 수수료
        pnl_pct = (price - avg_price) / avg_price * 100
        
        self.balance_krw += net_proceeds
        
        del self.positions[coin]
        
        self.trade_history.append({
            'type': 'SELL',
            'coin': coin,
            'price': price,
            'volume': volume,
            'amount': amount,
            'fee': fee,
            'pnl': pnl,
            'pnl_pct': pnl_pct,
            'timestamp': datetime.now(),
            'reason': reason
        })
        
        return True
    
    def get_portfolio_value(self, current_prices: Dict[str, float]) -> float:
        """현재 포트폴리오 가치"""
        position_value = sum(
            current_prices.get(coin, 0) * pos['volume']
            for coin, pos in self.positions.items()
        )
        return self.balance_krw + position_value
    
    def run_backtest(self, coin: str, df: pd.DataFrame, 
                     strategy: str = "rsi_bollinger") -> Dict:
        """
        백테스트 실행
        
        Parameters:
        -----------
        coin : str
            대상 코인 (BTC, ETH 등)
        df : pd.DataFrame
            OHLCV 데이터
        strategy : str
            전략명 (rsi_bollinger, momentum, mean_reversion)
        """
        self.reset()
        
        # 기술적 지표 계산
        df = self._calculate_indicators(df)
        
        initial_price = df['close'].iloc[0]
        
        for i in range(50, len(df)):  # 50일부터 시작 (지표 계산 여유)
            row = df.iloc[i]
            date = df.index[i]
            price = row['close']
            
            # 현재 포지션 확인
            has_position = coin in self.positions
            
            if has_position:
                avg_price = self.positions[coin]['avg_price']
                
                # 손절/익절 체크
                change_pct = (price - avg_price) / avg_price
                
                if change_pct <= -self.stop_loss_pct:
                    self.sell(coin, price, f"STOP_LOSS ({change_pct*100:.1f}%)")
                elif change_pct >= self.take_profit_pct:
                    self.sell(coin, price, f"TAKE_PROFIT ({change_pct*100:.1f}%)")
                else:
                    # 전략 기반 매도 신호
                    if self._check_sell_signal(df, i, strategy):
                        self.sell(coin, price, f"SIGNAL_{strategy}")
            else:
                # 매수 신호 체크
                if self._check_buy_signal(df, i, strategy):
                    volume = self.calculate_position_size(price)
                    if volume > 0:
                        self.buy(coin, price, volume, f"SIGNAL_{strategy}")
        
        # 최종 평가
        final_price = df['close'].iloc[-1]
        final_value = self.get_portfolio_value({coin: final_price})
        
        # 보유중인 포지션 정산
        unrealized_pnl = 0
        if coin in self.positions:
            avg_price = self.positions[coin]['avg_price']
            volume = self.positions[coin]['volume']
            unrealized_pnl = (final_price - avg_price) * volume
        
        return {
            'coin': coin,
            'strategy': strategy,
            'period': f"{df.index[0].strftime('%Y-%m-%d')} ~ {df.index[-1].strftime('%Y-%m-%d')}",
            'initial_balance': self.initial_balance,
            'final_balance': final_value,
            'total_return_pct': (final_value - self.initial_balance) / self.initial_balance * 100,
            'total_trades': len([t for t in self.trade_history if t['type'] == 'SELL']),
            'winning_trades': len([t for t in self.trade_history if t['type'] == 'SELL' and t.get('pnl', 0) > 0]),
            'unrealized_pnl': unrealized_pnl,
            'positions': self.positions.copy(),
            'trade_history': self.trade_history.copy()
        }
    
    def _calculate_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        """기술적 지표 계산"""
        # RSI
        delta = df['close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
        rs = gain / loss
        df['rsi'] = 100 - (100 / (1 + rs))
        
        # 볼린저 밴드
        df['sma20'] = df['close'].rolling(window=20).mean()
        df['std20'] = df['close'].rolling(window=20).std()
        df['upper_band'] = df['sma20'] + (df['std20'] * 2)
        df['lower_band'] = df['sma20'] - (df['std20'] * 2)
        
        # MACD
        exp1 = df['close'].ewm(span=12, adjust=False).mean()
        exp2 = df['close'].ewm(span=26, adjust=False).mean()
        df['macd'] = exp1 - exp2
        df['macd_signal'] = df['macd'].ewm(span=9, adjust=False).mean()
        
        # 이동평균
        df['sma5'] = df['close'].rolling(window=5).mean()
        df['sma60'] = df['close'].rolling(window=60).mean()
        
        return df
    
    def _check_buy_signal(self, df: pd.DataFrame, idx: int, strategy: str) -> bool:
        """매수 신호 확인"""
        row = df.iloc[idx]
        prev = df.iloc[idx-1]
        
        if strategy == "rsi_bollinger":
            # RSI 과매도 + 볼린저 하단 접근
            return (row['rsi'] < 35 and 
                    row['close'] < row['lower_band'] * 1.02 and
                    row['volume'] > df['volume'].iloc[idx-20:idx].mean() * 1.2)
        
        elif strategy == "momentum":
            # 모멘텀 돌파
            return (row['close'] > row['sma5'] and
                    prev['close'] <= prev['sma5'] and
                    row['macd'] > row['macd_signal'] and
                    row['volume'] > df['volume'].iloc[idx-20:idx].mean())
        
        elif strategy == "mean_reversion":
            # 평균회귀
            deviation = (row['close'] - row['sma20']) / row['sma20']
            return deviation < -0.03 and row['rsi'] < 40
        
        return False
    
    def _check_sell_signal(self, df: pd.DataFrame, idx: int, strategy: str) -> bool:
        """매도 신호 확인"""
        row = df.iloc[idx]
        
        if strategy == "rsi_bollinger":
            # RSI 과매수 또는 볼린저 상단
            return row['rsi'] > 70 or row['close'] > row['upper_band']
        
        elif strategy == "momentum":
            # 모멘텀 약화
            return row['macd'] < row['macd_signal']
        
        elif strategy == "mean_reversion":
            # 평균 회복
            deviation = (row['close'] - row['sma20']) / row['sma20']
            return deviation > 0.05
        
        return False
    
    def run_live_simulation(self, coins: List[str], duration_minutes: int = 60):
        """
        실시간 시뮬레이션 (Paper Trading)
        
        Parameters:
        -----------
        coins : List[str]
            모니터링할 코인 리스트
        duration_minutes : int
            실행 시간 (분)
        """
        self.reset()
        print("="*70)
        print("🚀 빗썸 실시간 매매 시뮬레이션 시작")
        print("="*70)
        print(f"초기 자본: {self.initial_balance:,} KRW")
        print(f"모니터링: {', '.join(coins)}")
        print(f"전략: RSI + 볼린저 밴드")
        print("="*70)
        
        start_time = datetime.now()
        end_time = start_time + timedelta(minutes=duration_minutes)
        
        while datetime.now() < end_time:
            for coin in coins:
                try:
                    # 현재가 조회
                    ticker = self.api.get_ticker(coin)
                    if not ticker or 'data' not in ticker:
                        continue
                    
                    current_price = float(ticker['data'].get('closing_price', 0))
                    if current_price == 0:
                        continue
                    
                    # OHLCV 데이터 조회 (최근 100개)
                    df = self.api.get_ohlcv(coin, chart_intervals="24h", count=100)
                    if df.empty or len(df) < 50:
                        continue
                    
                    # 지표 계산
                    df = self._calculate_indicators(df)
                    latest = df.iloc[-1]
                    
                    has_position = coin in self.positions
                    
                    if has_position:
                        avg_price = self.positions[coin]['avg_price']
                        change_pct = (current_price - avg_price) / avg_price
                        
                        # 손절/익절
                        if change_pct <= -self.stop_loss_pct:
                            self.sell(coin, current_price, "STOP_LOSS")
                            print(f"🔴 [{coin}] 손절 매도 @ {current_price:,.0f} ({change_pct*100:.1f}%)")
                        elif change_pct >= self.take_profit_pct:
                            self.sell(coin, current_price, "TAKE_PROFIT")
                            print(f"🟢 [{coin}] 익절 매도 @ {current_price:,.0f} ({change_pct*100:.1f}%)")
                    else:
                        # 매수 신호
                        if latest['rsi'] < 35 and current_price < latest['lower_band'] * 1.02:
                            volume = self.calculate_position_size(current_price)
                            if self.buy(coin, current_price, volume, "RSI_OVERSOLD"):
                                print(f"🔵 [{coin}] 매수 @ {current_price:,.0f} (RSI: {latest['rsi']:.1f})")
                    
                except Exception as e:
                    continue
            
            # 1분 대기
            time.sleep(60)
            
            # 현재 상태 출력
            elapsed = datetime.now() - start_time
            portfolio = self.balance_krw + sum(
                self.positions[c]['volume'] * current_price 
                for c in self.positions
            )
            print(f"\n⏱️  {str(elapsed).split('.')[0]} | 잔고: {self.balance_krw:,.0f} | "
                  f"포지션: {len(self.positions)}개 | 총평가: {portfolio:,.0f}")
        
        # 최종 결과
        print("\n" + "="*70)
        print("📊 시뮬레이션 종료")
        print("="*70)
        self._print_summary()
    
    def _print_summary(self):
        """결과 요약 출력"""
        final_value = self.balance_krw
        for coin, pos in self.positions.items():
            # 현재가 조회
            try:
                ticker = self.api.get_ticker(coin)
                price = float(ticker['data'].get('closing_price', pos['avg_price']))
                final_value += pos['volume'] * price
            except:
                final_value += pos['volume'] * pos['avg_price']
        
        return_pct = (final_value - self.initial_balance) / self.initial_balance * 100
        
        print(f"\n💰 최종 평가액: {final_value:,.0f} KRW")
        print(f"📈 수익률: {return_pct:+.2f}%")
        print(f"🔄 총 거래: {len(self.trade_history)}회")
        
        sell_trades = [t for t in self.trade_history if t['type'] == 'SELL']
        if sell_trades:
            wins = len([t for t in sell_trades if t.get('pnl', 0) > 0])
            print(f"✅ 승률: {wins}/{len(sell_trades)} ({wins/len(sell_trades)*100:.1f}%)")
            
            total_pnl = sum(t.get('pnl', 0) for t in sell_trades)
            print(f"💵 실현손익: {total_pnl:,.0f} KRW")
        
        if self.positions:
            print(f"\n📊 미청산 포지션:")
            for coin, pos in self.positions.items():
                print(f"   {coin}: {pos['volume']:.6f} @ {pos['avg_price']:,.0f}")


def main():
    """메인 실행"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Bithumb Trading Simulator')
    parser.add_argument('--mode', choices=['backtest', 'live'], default='backtest',
                       help='실행 모드 (backtest: 백테스트, live: 실시간 시뮬레이션)')
    parser.add_argument('--coin', default='BTC', help='대상 코인 (예: BTC, ETH)')
    parser.add_argument('--strategy', default='rsi_bollinger',
                       choices=['rsi_bollinger', 'momentum', 'mean_reversion'],
                       help='전략 선택')
    parser.add_argument('--balance', type=float, default=10_000_000,
                       help='초기 자본 (KRW)')
    parser.add_argument('--days', type=int, default=200,
                       help='백테스트 일수')
    
    args = parser.parse_args()
    
    sim = BithumbTradingSimulator(initial_balance=args.balance)
    
    if args.mode == 'backtest':
        print(f"📊 {args.coin} 백테스트 시작...")
        print(f"   전략: {args.strategy}")
        print(f"   기간: 최근 {args.days}일")
        
        # 데이터 조회
        df = sim.api.get_ohlcv(args.coin, chart_intervals="24h", count=args.days)
        if df.empty:
            print("❌ 데이터 조회 실패")
            return
        
        print(f"   데이터: {len(df)}개 캔들")
        
        # 백테스트 실행
        result = sim.run_backtest(args.coin, df, args.strategy)
        
        # 결과 출력
        print("\n" + "="*70)
        print("📊 백테스트 결과")
        print("="*70)
        print(f"코인: {result['coin']}")
        print(f"전략: {result['strategy']}")
        print(f"기간: {result['period']}")
        print(f"초기 자본: {result['initial_balance']:,.0f} KRW")
        print(f"최종 평가: {result['final_balance']:,.0f} KRW")
        print(f"총 수익률: {result['total_return_pct']:+.2f}%")
        print(f"거래 횟수: {result['total_trades']}회")
        if result['total_trades'] > 0:
            print(f"승률: {result['winning_trades']}/{result['total_trades']} "
                  f"({result['winning_trades']/result['total_trades']*100:.1f}%)")
        
        # 거래 내역
        if result['trade_history']:
            print("\n📋 거래 내역:")
            for trade in result['trade_history'][-10:]:  # 최근 10개
                if trade['type'] == 'SELL':
                    pnl_str = f" ({trade.get('pnl_pct', 0):+.1f}%)"
                else:
                    pnl_str = ""
                print(f"   {trade['type']} {trade['coin']} @ {trade['price']:,.0f}{pnl_str}")
        
    else:  # live simulation
        sim.run_live_simulation([args.coin, 'ETH', 'XRP'], duration_minutes=60)


if __name__ == '__main__':
    main()
