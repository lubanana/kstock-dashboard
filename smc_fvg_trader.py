#!/usr/bin/env python3
"""
SMC FVG (Smart Money Concepts - Fair Value Gap) Trading Strategy
SMC FVG 스마트 머니 컨셉트 전략 트레이딩 봇

Features:
- MSB (Market Structure Break) 감지
- FVG (Fair Value Gap) 자동 식별
- Retest 진입 조건 확인
- Order Block 기반 SL 설정
- R:R 1:2.5+ 익절 관리
- 멀티 타임프레임 (15m/1h/4h)

Data Source: Binance Futures (CCXT)
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
import ccxt
import time
import json
import warnings
warnings.filterwarnings('ignore')


class SMCFVGStrategy:
    """
    SMC FVG 전략 엔진
    """
    
    def __init__(self, 
                 timeframe: str = '1h',
                 min_rr_ratio: float = 2.5,
                 fvg_min_size: float = 0.001,  # 최소 FVG 크기 (0.1%)
                 msb_strength: float = 0.005,   # MSB 강도 (0.5% 이상 돌파)
                 test_mode: bool = True):
        
        self.timeframe = timeframe
        self.min_rr_ratio = min_rr_ratio
        self.fvg_min_size = fvg_min_size
        self.msb_strength = msb_strength
        self.test_mode = test_mode
        
        # 거래소 연결 (테스트넷)
        self.exchange = ccxt.binance({
            'enableRateLimit': True,
            'options': {
                'defaultType': 'future',
                'adjustForTimeDifference': True
            }
        })
        
        if test_mode:
            self.exchange.set_sandbox_mode(True)
            print("🧪 테스트넷 모드로 실행중...")
    
    def fetch_ohlcv(self, symbol: str, limit: int = 200) -> pd.DataFrame:
        """
        OHLCV 데이터 조회
        """
        try:
            ohlcv = self.exchange.fetch_ohlcv(symbol, self.timeframe, limit=limit)
            df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
            df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
            df.set_index('timestamp', inplace=True)
            return df
        except Exception as e:
            print(f"❌ 데이터 조회 오류: {e}")
            return pd.DataFrame()
    
    def identify_swing_points(self, df: pd.DataFrame, window: int = 5) -> Tuple[List[int], List[int]]:
        """
        스윙 하이/로우 포인트 식별
        
        Returns:
            (swing_highs_idx, swing_lows_idx)
        """
        highs = df['high'].values
        lows = df['low'].values
        
        swing_highs = []
        swing_lows = []
        
        for i in range(window, len(df) - window):
            # 스윙 하이: 주변 window 개 봉 중 최고
            if highs[i] == max(highs[i-window:i+window+1]):
                swing_highs.append(i)
            # 스윙 로우: 주변 window 개 봉 중 최저
            if lows[i] == min(lows[i-window:i+window+1]):
                swing_lows.append(i)
        
        return swing_highs, swing_lows
    
    def detect_msb_long(self, df: pd.DataFrame, swing_highs: List[int]) -> Optional[Dict]:
        """
        롱 MSB (Market Structure Break) 감지
        
        조건:
        - 하락 추세 (Lower High, Lower Low 패턴)
        - 이전 스윙 하이를 강하게 돌파
        """
        if len(swing_highs) < 2:
            return None
        
        closes = df['close'].values
        highs = df['high'].values
        
        # 최근 2개 스윙 하이
        last_swing_idx = swing_highs[-1]
        prev_swing_idx = swing_highs[-2]
        
        prev_swing_high = highs[prev_swing_idx]
        last_swing_high = highs[last_swing_idx]
        current_close = closes[-1]
        
        # 하락 추세 확인 (이전 고점보다 낮은 고점)
        is_downtrend = last_swing_high < prev_swing_high
        
        # MSB 확인: 현재가가 이전 스윙 하이를 돌파
        breakout_threshold = prev_swing_high * (1 + self.msb_strength)
        is_breakout = current_close > breakout_threshold
        
        if is_downtrend and is_breakout:
            return {
                'type': 'MSB_LONG',
                'prev_swing_high': float(prev_swing_high),
                'last_swing_high': float(last_swing_high),
                'breakout_price': float(current_close),
                'strength': float((current_close - prev_swing_high) / prev_swing_high * 100),
                'prev_swing_idx': prev_swing_idx,
                'last_swing_idx': last_swing_idx
            }
        
        return None
    
    def detect_fvg(self, df: pd.DataFrame, lookback: int = 10) -> List[Dict]:
        """
        FVG (Fair Value Gap) 감지
        
        불리쉬 FVG: 캔들1 고가 < 캔들3 저가 (갭업)
        베리쉬 FVG: 캔들1 저가 > 캔들3 고가 (갭다운)
        
        Returns:
            List of FVG dictionaries
        """
        fvgs = []
        highs = df['high'].values
        lows = df['low'].values
        
        # 최근 N개 캔들에서 FVG 검색
        for i in range(max(0, len(df) - lookback - 3), len(df) - 3):
            # 3개 캔들 패턴 분석
            candle1_high = highs[i]
            candle1_low = lows[i]
            candle2_high = highs[i+1]  # 중간 캔들 (impulse)
            candle2_low = lows[i+1]
            candle3_high = highs[i+2]
            candle3_low = lows[i+2]
            
            # 불리쉬 FVG: 캔들1 고가 < 캔들3 저가
            if candle1_high < candle3_low:
                fvg_size = (candle3_low - candle1_high) / candle1_high
                if fvg_size >= self.fvg_min_size:
                    fvgs.append({
                        'type': 'BULLISH',
                        'idx': i+1,
                        'top': float(candle3_low),
                        'bottom': float(candle1_high),
                        'size': float(fvg_size * 100),
                        'candle1_idx': i,
                        'candle3_idx': i+2,
                        'ob_low': float(candle2_low)  # 오더블록 하단
                    })
            
            # 베리쉬 FVG: 캔들1 저가 > 캔들3 고가
            elif candle1_low > candle3_high:
                fvg_size = (candle1_low - candle3_high) / candle3_high
                if fvg_size >= self.fvg_min_size:
                    fvgs.append({
                        'type': 'BEARISH',
                        'idx': i+1,
                        'top': float(candle1_low),
                        'bottom': float(candle3_high),
                        'size': float(fvg_size * 100),
                        'candle1_idx': i,
                        'candle3_idx': i+2,
                        'ob_high': float(candle2_high)
                    })
        
        return fvgs
    
    def check_retest(self, df: pd.DataFrame, fvg: Dict) -> Optional[Dict]:
        """
        FVG Retest 확인
        
        현재 가격이 FVG 구간 내에 있는지 확인
        """
        if not fvg:
            return None
        
        current_low = df['low'].iloc[-1]
        current_high = df['high'].iloc[-1]
        current_close = df['close'].iloc[-1]
        
        fvg_top = fvg['top']
        fvg_bottom = fvg['bottom']
        
        # 현재 가격이 FVG 구간 내에 있거나 하단 근처
        in_fvg = (current_low <= fvg_top) and (current_high >= fvg_bottom)
        near_bottom = abs(current_close - fvg_bottom) / fvg_bottom < 0.002
        
        if in_fvg or near_bottom:
            return {
                'fvg': fvg,
                'current_price': float(current_close),
                'in_fvg': in_fvg,
                'entry_zone': (fvg_bottom, fvg_top),
                'timestamp': df.index[-1]
            }
        
        return None
    
    def find_nearest_resistance(self, df: pd.DataFrame, current_price: float, 
                                 swing_highs: List[int], lookforward: int = 10) -> float:
        """
        다음 주요 저항대 찾기 (익절 목표)
        """
        if not swing_highs:
            return current_price * 1.05
        
        highs = df['high'].values
        resistances = [highs[idx] for idx in swing_highs if highs[idx] > current_price]
        
        if resistances:
            return min(resistances)  # 가장 가까운 저항
        
        return current_price * 1.05
    
    def calculate_trade_levels(self, retest: Dict, msb: Optional[Dict], 
                               df: pd.DataFrame, swing_highs: List[int]) -> Optional[Dict]:
        """
        진입가, 손절가, 익절가 계산
        """
        fvg = retest['fvg']
        entry_price = retest['current_price']
        
        # SL: FVG를 만든 오더블록 하단 (불리쉬) 또는 FVG 하단
        if 'ob_low' in fvg:
            sl_price = fvg['ob_low']
        else:
            sl_price = fvg['bottom'] * 0.998  # FVG 하단 아래 0.2%
        
        # TP: 다음 저항대 또는 1:2.5 R/R
        tp_price = self.find_nearest_resistance(df, entry_price, swing_highs)
        
        # R/R 계산
        risk = entry_price - sl_price
        reward = tp_price - entry_price
        
        if risk <= 0:
            return None
        
        rr_ratio = reward / risk
        
        # 최소 R/R 미달 시 TP 조정
        if rr_ratio < self.min_rr_ratio:
            tp_price = entry_price + (risk * self.min_rr_ratio)
            reward = tp_price - entry_price
            rr_ratio = self.min_rr_ratio
        
        return {
            'entry_price': float(entry_price),
            'sl_price': float(sl_price),
            'tp_price': float(tp_price),
            'risk': float(risk),
            'reward': float(reward),
            'rr_ratio': float(rr_ratio),
            'position_size': None  # 추후 계산
        }
    
    def scan(self, symbol: str = 'BTC/USDT') -> Optional[Dict]:
        """
        완전한 스캔 수행
        """
        print(f"\n🔍 [{self.timeframe}] {symbol} 스캔 중...")
        
        # 1. 데이터 조회
        df = self.fetch_ohlcv(symbol)
        if df.empty or len(df) < 50:
            print("❌ 데이터 부족")
            return None
        
        current_price = df['close'].iloc[-1]
        print(f"   현재가: ${current_price:,.2f}")
        
        # 2. 스윙 포인트 식별
        swing_highs, swing_lows = self.identify_swing_points(df)
        print(f"   스윙 하이: {len(swing_highs)}개, 스윙 로우: {len(swing_lows)}개")
        
        # 3. MSB 감지
        msb = self.detect_msb_long(df, swing_highs)
        if msb:
            print(f"   ✅ MSB 감지: 이전 고점 ${msb['prev_swing_high']:,.2f} 돌파 (강도: {msb['strength']:.2f}%)")
        else:
            print("   ⚠️ MSB 미감지")
        
        # 4. FVG 감지
        fvgs = self.detect_fvg(df)
        bullish_fvgs = [f for f in fvgs if f['type'] == 'BULLISH']
        print(f"   FVG 발견: {len(fvgs)}개 (불리쉬: {len(bullish_fvgs)}개)")
        
        # 5. Retest 확인 (가장 최근 불리쉬 FVG)
        retest = None
        if bullish_fvgs:
            # MSB와 관련된 FVG 우선 (시간적으로 가까운 것)
            target_fvg = bullish_fvgs[-1]
            retest = self.check_retest(df, target_fvg)
            
            if retest:
                print(f"   ✅ FVG Retest 감지: ${retest['entry_zone'][0]:,.2f} ~ ${retest['entry_zone'][1]:,.2f}")
            else:
                print(f"   ⏳ FVG 대기중... (${target_fvg['bottom']:,.2f} ~ ${target_fvg['top']:,.2f})")
        
        # 6. 진입 조건 확인
        if not msb or not retest:
            print("   ❌ 진입 조건 미충족")
            return None
        
        # 7. 진입 레벨 계산
        levels = self.calculate_trade_levels(retest, msb, df, swing_highs)
        if not levels:
            print("   ❌ 레벨 계산 실패")
            return None
        
        # 8. 최종 결과
        signal = {
            'symbol': symbol,
            'timeframe': self.timeframe,
            'timestamp': datetime.now().isoformat(),
            'type': 'LONG',
            'msb': msb,
            'fvg': retest['fvg'],
            'retest': retest,
            'entry_price': levels['entry_price'],
            'sl_price': levels['sl_price'],
            'tp_price': levels['tp_price'],
            'risk': levels['risk'],
            'reward': levels['reward'],
            'rr_ratio': levels['rr_ratio'],
            'expected_return': (levels['tp_price'] - levels['entry_price']) / levels['entry_price'] * 100
        }
        
        self.print_signal(signal)
        return signal
    
    def print_signal(self, signal: Dict):
        """
        신호 출력
        """
        print("\n" + "="*60)
        print(f"🎯 진입 신호 발생 ({signal['timeframe']})")
        print("="*60)
        print(f"종목: {signal['symbol']}")
        print(f"시간: {signal['timestamp']}")
        print(f"\n📊 분석:")
        print(f"   MSB: ${signal['msb']['prev_swing_high']:,.2f} 돌파")
        print(f"   FVG: ${signal['fvg']['bottom']:,.2f} ~ ${signal['fvg']['top']:,.2f} (크기: {signal['fvg']['size']:.2f}%)")
        print(f"\n💰 진입 레벨:")
        print(f"   진입가: ${signal['entry_price']:,.2f}")
        print(f"   손절가: ${signal['sl_price']:,.2f} (-{signal['risk']/signal['entry_price']*100:.2f}%)")
        print(f"   익절가: ${signal['tp_price']:,.2f} (+{signal['expected_return']:.2f}%)")
        print(f"\n⚖️  손익비: 1:{signal['rr_ratio']:.2f}")
        print("="*60)


class SMCFVGTrader:
    """
    SMC FVG 자동 트레이더
    """
    
    def __init__(self, api_key: str = None, api_secret: str = None, test_mode: bool = True):
        self.strategy_15m = SMCFVGStrategy(timeframe='15m', test_mode=test_mode)
        self.strategy_1h = SMCFVGStrategy(timeframe='1h', test_mode=test_mode)
        self.strategy_4h = SMCFVGStrategy(timeframe='4h', test_mode=test_mode)
        
        self.active_signals = []
        
    def run_multi_timeframe(self, symbol: str = 'BTC/USDT'):
        """
        멀티 타임프레임 스캔
        """
        print("\n" + "🔄"*30)
        print(f"멀티 타임프레임 스캔: {symbol}")
        print("🔄"*30)
        
        results = {}
        
        # 15분봉
        print("\n" + "─"*60)
        results['15m'] = self.strategy_15m.scan(symbol)
        
        # 1시간봉
        print("\n" + "─"*60)
        results['1h'] = self.strategy_1h.scan(symbol)
        
        # 4시간봉
        print("\n" + "─"*60)
        results['4h'] = self.strategy_4h.scan(symbol)
        
        # 결과 종합
        print("\n" + "="*60)
        print("📊 스캔 결과 종합")
        print("="*60)
        
        for tf, signal in results.items():
            status = "🟢 신호" if signal else "⚪ 대기"
            print(f"   {tf}: {status}")
            if signal:
                self.active_signals.append(signal)
        
        return results
    
    def save_signals(self, filename: str = 'smc_signals.json'):
        """
        신호 저장
        """
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(self.active_signals, f, ensure_ascii=False, indent=2)
        print(f"\n💾 신호 저장: {filename}")


def main():
    """
    메인 실행
    """
    print("\n" + "="*70)
    print("🚀 SMC FVG 트레이딩 전략 봇")
    print("   Smart Money Concepts - Fair Value Gap Strategy")
    print("="*70)
    
    # 트레이더 초기화 (테스트넷)
    trader = SMCFVGTrader(test_mode=True)
    
    # 멀티 타임프레임 스캔
    symbols = ['BTC/USDT', 'ETH/USDT']
    
    for symbol in symbols:
        results = trader.run_multi_timeframe(symbol)
        time.sleep(1)  # API rate limit
    
    # 결과 저장
    trader.save_signals()
    
    print("\n✅ 스캔 완료!")


if __name__ == '__main__':
    main()
