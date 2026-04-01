#!/usr/bin/env python3
"""
추세추종 전략 구현 모듈
- MA Crossover
- ATR Channel Breakout
- RSI2 Mean Reversion + MA200 Filter
"""

import sys
sys.path.insert(0, '/root/.openclaw/workspace/strg')

import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from fdr_wrapper import get_price


class MovingAverageCross:
    """전략 1: 이동평균선 크로스오버"""
    
    def __init__(self, short=50, long=200):
        self.short_period = short
        self.long_period = long
        self.name = f"MA_CROSS_{short}_{long}"
    
    def analyze(self, symbol, date_str):
        """분석 실행"""
        try:
            end_date = datetime.strptime(date_str, '%Y-%m-%d')
            start_date = end_date - timedelta(days=365)
            
            df = get_price(symbol, start_date.strftime('%Y-%m-%d'), date_str)
            if df is None or len(df) < self.long_period + 10:
                return None
            
            closes = df['Close'].values
            volumes = df['Volume'].values
            
            # 이동평균 계산
            ma_short = pd.Series(closes).rolling(self.short_period).mean().values
            ma_long = pd.Series(closes).rolling(self.long_period).mean().values
            
            # 현재값
            current_price = closes[-1]
            current_ma_short = ma_short[-1]
            current_ma_long = ma_long[-1]
            
            # 과거값 (크로스 확인용)
            prev_ma_short = ma_short[-2]
            prev_ma_long = ma_long[-2]
            
            # 추세 확인
            trend_up = current_ma_short > current_ma_long
            golden_cross = (prev_ma_short <= prev_ma_long) and (current_ma_short > current_ma_long)
            dead_cross = (prev_ma_short >= prev_ma_long) and (current_ma_short < current_ma_long)
            
            # 거래량 확인
            vol_ma20 = np.mean(volumes[-20:])
            volume_ok = volumes[-1] > vol_ma20 * 1.2
            
            # 신호 생성
            signal = 'HOLD'
            score = 0
            
            if golden_cross and volume_ok:
                signal = 'BUY'
                score = 70
            elif dead_cross:
                signal = 'SELL'
                score = 30
            elif trend_up:
                score = 60
            else:
                score = 40
            
            return {
                'symbol': symbol,
                'date': date_str,
                'strategy': self.name,
                'signal': signal,
                'score': score,
                'price': current_price,
                'ma_short': round(current_ma_short, 0),
                'ma_long': round(current_ma_long, 0),
                'trend_up': trend_up,
                'golden_cross': golden_cross,
                'dead_cross': dead_cross,
                'volume_ok': volume_ok
            }
            
        except Exception as e:
            return None
    
    def calculate_targets(self, entry_price, trend_up=True):
        """목표가/손절가 계산 (R:R 1:3)"""
        if trend_up:
            stop_loss = entry_price * 0.95  # -5%
            target = entry_price + (entry_price - stop_loss) * 3  # +15%
        else:
            stop_loss = entry_price * 1.05  # +5% (공매도)
            target = entry_price - (stop_loss - entry_price) * 3
        
        return {
            'entry': round(entry_price, 0),
            'stop_loss': round(stop_loss, 0),
            'target': round(target, 0),
            'rr_ratio': 3.0
        }


class ATRChannelBreakout:
    """전략 2: ATR 채널 브레이크아웃"""
    
    def __init__(self, ma_period=350, atr_period=14):
        self.ma_period = ma_period
        self.atr_period = atr_period
        self.name = f"ATR_BREAK_{ma_period}"
    
    def calculate_atr(self, high, low, close, period):
        """ATR 계산"""
        tr1 = high[1:] - low[1:]
        tr2 = np.abs(high[1:] - close[:-1])
        tr3 = np.abs(low[1:] - close[:-1])
        tr = np.maximum(np.maximum(tr1, tr2), tr3)
        atr = pd.Series(tr).rolling(period).mean().values
        return atr
    
    def analyze(self, symbol, date_str):
        """분석 실행"""
        try:
            end_date = datetime.strptime(date_str, '%Y-%m-%d')
            start_date = end_date - timedelta(days=500)
            
            df = get_price(symbol, start_date.strftime('%Y-%m-%d'), date_str)
            if df is None or len(df) < self.ma_period + 10:
                return None
            
            closes = df['Close'].values
            highs = df['High'].values
            lows = df['Low'].values
            
            # 이동평균
            ma = pd.Series(closes).rolling(self.ma_period).mean().values
            
            # ATR
            atr = self.calculate_atr(highs, lows, closes, self.atr_period)
            
            # 채널 계산
            upper_channel = ma + 7 * np.concatenate([[0], atr])
            lower_channel = ma - 3 * np.concatenate([[0], atr])
            
            current_price = closes[-1]
            current_ma = ma[-1]
            current_upper = upper_channel[-1]
            current_lower = lower_channel[-1]
            
            # 신호 확인
            breakout_up = current_price > current_upper
            breakout_down = current_price < current_lower
            
            signal = 'HOLD'
            score = 50
            
            if breakout_up:
                signal = 'BUY'
                score = 75
            elif breakout_down:
                signal = 'SELL'
                score = 25
            elif current_price > current_ma:
                score = 60
            else:
                score = 40
            
            return {
                'symbol': symbol,
                'date': date_str,
                'strategy': self.name,
                'signal': signal,
                'score': score,
                'price': current_price,
                'ma': round(current_ma, 0),
                'upper_channel': round(current_upper, 0),
                'lower_channel': round(current_lower, 0),
                'atr': round(atr[-1] if len(atr) > 0 else 0, 0),
                'breakout_up': breakout_up,
                'breakout_down': breakout_down
            }
            
        except Exception as e:
            return None
    
    def calculate_targets(self, entry_price, atr, is_long=True):
        """목표가/손절가 계산 (ATR 기반)"""
        if is_long:
            stop_loss = entry_price - 2 * atr
            target = entry_price + 6 * atr  # 1:3 R:R
        else:
            stop_loss = entry_price + 2 * atr
            target = entry_price - 6 * atr
        
        return {
            'entry': round(entry_price, 0),
            'stop_loss': round(stop_loss, 0),
            'target': round(target, 0),
            'rr_ratio': 3.0
        }


class RSI2MeanReversion:
    """전략 3: RSI(2) 평균회귀 + MA200 필터"""
    
    def __init__(self, rsi_period=2, ma_period=200):
        self.rsi_period = rsi_period
        self.ma_period = ma_period
        self.name = f"RSI{rsi_period}_MA{ma_period}"
    
    def calculate_rsi(self, prices, period):
        """RSI 계산"""
        if len(prices) < period + 1:
            return None
        
        deltas = np.diff(prices)
        gains = np.where(deltas > 0, deltas, 0)
        losses = np.where(deltas < 0, -deltas, 0)
        
        avg_gain = np.mean(gains[-period:])
        avg_loss = np.mean(losses[-period:])
        
        if avg_loss == 0:
            return 100
        
        rs = avg_gain / avg_loss
        return 100 - (100 / (1 + rs))
    
    def analyze(self, symbol, date_str):
        """분석 실행"""
        try:
            end_date = datetime.strptime(date_str, '%Y-%m-%d')
            start_date = end_date - timedelta(days=300)
            
            df = get_price(symbol, start_date.strftime('%Y-%m-%d'), date_str)
            if df is None or len(df) < self.ma_period + 10:
                return None
            
            closes = df['Close'].values
            highs = df['High'].values
            
            # MA200
            ma200 = pd.Series(closes).rolling(self.ma_period).mean().values[-1]
            
            # RSI(2)
            rsi = self.calculate_rsi(closes, self.rsi_period)
            
            # 추세 확인
            above_ma200 = closes[-1] > ma200
            
            # 과매도/과매수
            oversold = rsi < 25 if rsi else False
            overbought = rsi > 75 if rsi else False
            
            # 신호 생성
            signal = 'HOLD'
            score = 50
            
            if oversold and above_ma200:
                signal = 'BUY'
                score = 70  # 상승 추세 내 과매도 반등
            elif overbought:
                signal = 'SELL'
                score = 30
            elif above_ma200 and rsi and rsi < 50:
                score = 60
            elif not above_ma200:
                score = 35
            
            # 목표가 (최근 2일 고가)
            target_price = max(highs[-2:]) if len(highs) >= 2 else highs[-1]
            
            return {
                'symbol': symbol,
                'date': date_str,
                'strategy': self.name,
                'signal': signal,
                'score': score,
                'price': closes[-1],
                'rsi': round(rsi, 1) if rsi else None,
                'ma200': round(ma200, 0),
                'above_ma200': above_ma200,
                'oversold': oversold,
                'overbought': overbought,
                'target_price': round(target_price, 0)
            }
            
        except Exception as e:
            return None
    
    def calculate_targets(self, entry_price, target_price):
        """목표가/손절가 계산"""
        # RSI2 전략은 고정 목표가 사용
        stop_loss = entry_price * 0.97  # -3%
        
        return {
            'entry': round(entry_price, 0),
            'stop_loss': round(stop_loss, 0),
            'target': round(target_price, 0),
            'time_exit': 5  # 5일 청산
        }


class TrendFollowingScanner:
    """통합 추세추종 스캐너"""
    
    def __init__(self):
        self.strategies = {
            'MA_CROSS': MovingAverageCross(50, 200),
            'ATR_BREAK': ATRChannelBreakout(350, 14),
            'RSI2_MA200': RSI2MeanReversion(2, 200),
        }
    
    def scan(self, symbol, date_str):
        """모든 전략 스캔"""
        results = {}
        
        for name, strategy in self.strategies.items():
            result = strategy.analyze(symbol, date_str)
            if result:
                results[name] = result
        
        return results
    
    def get_composite_signal(self, symbol, date_str):
        """통합 신호 생성"""
        results = self.scan(symbol, date_str)
        
        if not results:
            return None
        
        # 점수 평균
        avg_score = np.mean([r['score'] for r in results.values()])
        
        # BUY 신호 개수
        buy_count = sum(1 for r in results.values() if r['signal'] == 'BUY')
        sell_count = sum(1 for r in results.values() if r['signal'] == 'SELL')
        
        # 통합 신호
        if buy_count >= 2:
            composite_signal = 'STRONG_BUY'
        elif buy_count == 1:
            composite_signal = 'BUY'
        elif sell_count >= 2:
            composite_signal = 'STRONG_SELL'
        elif sell_count == 1:
            composite_signal = 'SELL'
        else:
            composite_signal = 'NEUTRAL'
        
        return {
            'symbol': symbol,
            'date': date_str,
            'composite_signal': composite_signal,
            'composite_score': round(avg_score, 1),
            'strategy_count': len(results),
            'buy_signals': buy_count,
            'sell_signals': sell_count,
            'details': results
        }


if __name__ == '__main__':
    # 테스트
    scanner = TrendFollowingScanner()
    
    # 삼성전자 테스트
    print("=" * 70)
    print("📊 추세추종 전략 테스트")
    print("=" * 70)
    
    symbols = [
        ('005930', '삼성전자'),
        ('042700', '한미반도체'),
        ('033100', '제룡전기'),
    ]
    
    today = '2026-03-03'
    
    for code, name in symbols:
        print(f"\n📈 {name} ({code}) - {today}")
        result = scanner.get_composite_signal(code, today)
        
        if result:
            print(f"   통합 신호: {result['composite_signal']}")
            print(f"   통합 점수: {result['composite_score']}")
            print(f"   BUY 신호: {result['buy_signals']} / SELL 신호: {result['sell_signals']}")
            print("   개별 전략:")
            for strategy_name, detail in result['details'].items():
                print(f"      {strategy_name}: {detail['signal']} ({detail['score']}점)")
        else:
            print("   데이터 없음")
