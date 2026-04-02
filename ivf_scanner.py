#!/usr/bin/env python3
"""
ICT + Volume Profile + Fibonacci + 수급 통합 스캐너
ICT Volume Fib Scanner (IVF Scanner)
"""

import sys
sys.path.insert(0, '/root/.openclaw/workspace/strg')

import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from dataclasses import dataclass
from typing import List, Dict, Optional, Tuple
from fdr_wrapper import get_price


@dataclass
class ICTSignals:
    """ICT 신호 데이터"""
    order_block_bullish: Optional[Dict] = None
    order_block_bearish: Optional[Dict] = None
    fvg_bullish: Optional[Dict] = None
    fvg_bearish: Optional[Dict] = None
    bos_up: bool = False
    bos_down: bool = False
    choch_up: bool = False
    choch_down: bool = False
    structure: str = 'neutral'


@dataclass
class VolumeProfile:
    """볼륨 프로파일 데이터"""
    poc: float = 0.0
    vah: float = 0.0
    val: float = 0.0
    hvn_levels: List[float] = None
    lvn_levels: List[float] = None
    price_vs_poc: str = 'neutral'


@dataclass
class FibonacciLevels:
    """피볼나치 레벨"""
    retracements: Dict[str, float] = None
    extensions: Dict[str, float] = None
    current_retracement: float = 0.0
    ote_zone: Tuple[float, float] = (0.0, 0.0)
    wave_count: str = 'unknown'


@dataclass
class CapitalFlow:
    """수급 데이터"""
    rvol: float = 1.0
    vir: float = 0.0
    accumulation: bool = False
    distribution: bool = False
    smart_money_sign: str = 'neutral'


class ICTAnalyzer:
    """ICT 개념 분석기"""
    
    def find_order_blocks(self, df: pd.DataFrame) -> Dict:
        """Order Block 찾기"""
        highs = df['High'].values
        lows = df['Low'].values
        opens = df['Open'].values
        closes = df['Close'].values
        
        bullish_obs = []
        bearish_obs = []
        
        # 최소 3봉 이상 데이터 필요
        if len(df) < 5:
            return {'bullish': [], 'bearish': []}
        
        for i in range(3, len(df) - 1):
            # Bullish Order Block: 상승 전 마지막 음봉
            if (closes[i] > opens[i] * 1.02 and  # 현재 강한 양봉
                closes[i] > highs[i-1]):  # 전 고점 돌파
                
                # 전봉 확인 - 마지막 음봉 찾기
                for j in range(i-1, max(i-5, -1), -1):
                    if closes[j] < opens[j]:  # 음봉
                        bullish_obs.append({
                            'index': j,
                            'high': highs[j],
                            'low': lows[j],
                            'open': opens[j],
                            'close': closes[j]
                        })
                        break
            
            # Bearish Order Block: 하락 전 마지막 양봉
            if (closes[i] < opens[i] * 0.98 and  # 현재 강한 음봉
                closes[i] < lows[i-1]):  # 전 저점 돌파
                
                for j in range(i-1, max(i-5, -1), -1):
                    if closes[j] > opens[j]:  # 양봉
                        bearish_obs.append({
                            'index': j,
                            'high': highs[j],
                            'low': lows[j],
                            'open': opens[j],
                            'close': closes[j]
                        })
                        break
        
        return {
            'bullish': bullish_obs[-3:] if bullish_obs else [],  # 최근 3개
            'bearish': bearish_obs[-3:] if bearish_obs else []
        }
    
    def find_fvgs(self, df: pd.DataFrame) -> Dict:
        """Fair Value Gaps 찾기"""
        highs = df['High'].values
        lows = df['Low'].values
        
        bullish_fvgs = []
        bearish_fvgs = []
        
        for i in range(2, len(df)):
            # Bullish FVG: 현재 저가 > 전전 고가 (갭 상승)
            if lows[i] > highs[i-2]:
                bullish_fvgs.append({
                    'index': i,
                    'top': lows[i],
                    'bottom': highs[i-2],
                    'gap': lows[i] - highs[i-2]
                })
            
            # Bearish FVG: 현재 고가 < 전전 저가 (갭 하락)
            if highs[i] < lows[i-2]:
                bearish_fvgs.append({
                    'index': i,
                    'top': lows[i-2],
                    'bottom': highs[i],
                    'gap': lows[i-2] - highs[i]
                })
        
        return {
            'bullish': bullish_fvgs[-3:] if bullish_fvgs else [],
            'bearish': bearish_fvgs[-3:] if bearish_fvgs else []
        }
    
    def analyze_structure(self, df: pd.DataFrame) -> Dict:
        """시장 구조 분석 (BOS/CHoCH)"""
        highs = df['High'].values
        lows = df['Low'].values
        
        # 스윙 고점/저점 식별 (단순화)
        swing_highs = []
        swing_lows = []
        
        for i in range(2, len(df) - 2):
            if highs[i] > highs[i-1] and highs[i] > highs[i-2] and \
               highs[i] > highs[i+1] and highs[i] > highs[i+2]:
                swing_highs.append((i, highs[i]))
            
            if lows[i] < lows[i-1] and lows[i] < lows[i-2] and \
               lows[i] < lows[i+1] and lows[i] < lows[i+2]:
                swing_lows.append((i, lows[i]))
        
        # BOS/CHoCH 확인
        bos_up = False
        bos_down = False
        choch_up = False
        choch_down = False
        
        if len(swing_highs) >= 2 and len(swing_lows) >= 2:
            # BOS Up: 최근 고점이 이전 고점보다 높음
            if swing_highs[-1][1] > swing_highs[-2][1]:
                bos_up = True
            
            # BOS Down: 최근 저점이 이전 저점보다 낮음
            if swing_lows[-1][1] < swing_lows[-2][1]:
                bos_down = True
            
            # CHoCH는 추세 전환 확인 (간단화)
            if swing_lows[-1][1] > swing_lows[-2][1]:
                choch_up = True
            if swing_highs[-1][1] < swing_highs[-2][1]:
                choch_down = True
        
        # 구조 판정
        if bos_up and not bos_down:
            structure = 'bullish'
        elif bos_down and not bos_up:
            structure = 'bearish'
        else:
            structure = 'neutral'
        
        return {
            'bos_up': bos_up,
            'bos_down': bos_down,
            'choch_up': choch_up,
            'choch_down': choch_down,
            'structure': structure,
            'swing_highs': swing_highs[-3:],
            'swing_lows': swing_lows[-3:]
        }
    
    def analyze(self, symbol: str) -> ICTSignals:
        """종합 ICT 분석"""
        df = get_price(symbol, 
                       (datetime.now() - timedelta(days=60)).strftime('%Y-%m-%d'),
                       datetime.now().strftime('%Y-%m-%d'))
        
        if df is None or len(df) < 20:
            return ICTSignals()
        
        df = df.reset_index()
        
        obs = self.find_order_blocks(df)
        fvgs = self.find_fvgs(df)
        structure = self.analyze_structure(df)
        
        return ICTSignals(
            order_block_bullish=obs['bullish'][-1] if obs['bullish'] else None,
            order_block_bearish=obs['bearish'][-1] if obs['bearish'] else None,
            fvg_bullish=fvgs['bullish'][-1] if fvgs['bullish'] else None,
            fvg_bearish=fvgs['bearish'][-1] if fvgs['bearish'] else None,
            bos_up=structure['bos_up'],
            bos_down=structure['bos_down'],
            choch_up=structure['choch_up'],
            choch_down=structure['choch_down'],
            structure=structure['structure']
        )


class VolumeProfileAnalyzer:
    """볼륨 프로파일 분석기"""
    
    def calculate(self, df: pd.DataFrame, rows: int = 30) -> VolumeProfile:
        """볼륨 프로파일 계산"""
        if df is None or len(df) < rows:
            return VolumeProfile()
        
        # 최근 데이터 사용
        recent_df = df.tail(rows)
        
        closes = recent_df['Close'].values
        volumes = recent_df['Volume'].values
        highs = recent_df['High'].values
        lows = recent_df['Low'].values
        
        # 가격 구간 설정
        price_min = np.min(lows)
        price_max = np.max(highs)
        price_range = price_max - price_min
        
        if price_range == 0:
            return VolumeProfile()
        
        # 10개 구간으로 분할
        num_bins = 10
        bin_size = price_range / num_bins
        
        volume_by_price = {}
        for i in range(num_bins):
            bin_low = price_min + i * bin_size
            bin_high = price_min + (i + 1) * bin_size
            bin_mid = (bin_low + bin_high) / 2
            
            # 해당 구간의 거래량 합산
            mask = (lows >= bin_low) & (highs <= bin_high)
            if np.any(mask):
                volume_by_price[bin_mid] = np.sum(volumes[mask])
            else:
                # 근접 구간 거래량 할당
                closest_idx = np.argmin(np.abs(closes - bin_mid))
                volume_by_price[bin_mid] = volumes[closest_idx]
        
        if not volume_by_price:
            return VolumeProfile()
        
        # POC (최다거래 가격)
        poc = max(volume_by_price, key=volume_by_price.get)
        
        # Value Area (거래량 70% 구간)
        total_volume = sum(volume_by_price.values())
        target_volume = total_volume * 0.7
        
        sorted_prices = sorted(volume_by_price.items(), key=lambda x: x[1], reverse=True)
        cumulative = 0
        va_prices = []
        
        for price, vol in sorted_prices:
            cumulative += vol
            va_prices.append(price)
            if cumulative >= target_volume:
                break
        
        vah = max(va_prices) if va_prices else price_max
        val = min(va_prices) if va_prices else price_min
        
        # 현재가 대비 POC 위치
        current_price = closes[-1]
        if current_price > poc * 1.02:
            price_vs_poc = 'above'
        elif current_price < poc * 0.98:
            price_vs_poc = 'below'
        else:
            price_vs_poc = 'at'
        
        return VolumeProfile(
            poc=poc,
            vah=vah,
            val=val,
            price_vs_poc=price_vs_poc
        )


class FibonacciWaveAnalyzer:
    """피볼나치 파동 분석기"""
    
    def calculate_retracements(self, high: float, low: float) -> Dict[str, float]:
        """되돌림 레벨 계산"""
        diff = high - low
        return {
            '23.6%': high - diff * 0.236,
            '38.2%': high - diff * 0.382,
            '50.0%': high - diff * 0.500,
            '61.8%': high - diff * 0.618,
            '78.6%': high - diff * 0.786
        }
    
    def calculate_extensions(self, wave1_start: float, wave1_end: float) -> Dict[str, float]:
        """확장 레벨 계산"""
        wave_length = wave1_end - wave1_start
        return {
            '100%': wave1_end + wave_length * 1.0,
            '138.2%': wave1_end + wave_length * 1.382,
            '161.8%': wave1_end + wave_length * 1.618,
            '200%': wave1_end + wave_length * 2.0,
            '261.8%': wave1_end + wave_length * 2.618
        }
    
    def analyze(self, df: pd.DataFrame) -> FibonacciLevels:
        """종합 피볼나치 분석"""
        if df is None or len(df) < 20:
            return FibonacciLevels()
        
        closes = df['Close'].values
        highs = df['High'].values
        lows = df['Low'].values
        
        # 최근 추세의 고점/저점
        recent_high = np.max(highs[-20:])
        recent_low = np.min(lows[-20:])
        current_price = closes[-1]
        
        # 되돌림 레벨
        retracements = self.calculate_retracements(recent_high, recent_low)
        
        # 현재 되돌림 위치 계산
        if recent_high > recent_low:
            current_retracement = ((recent_high - current_price) / (recent_high - recent_low)) * 100
        else:
            current_retracement = 0
        
        # OTE Zone (62~79%)
        ote_top = retracements.get('78.6%', 0)
        ote_bottom = retracements.get('61.8%', 0)
        
        return FibonacciLevels(
            retracements=retracements,
            current_retracement=current_retracement,
            ote_zone=(ote_bottom, ote_top)
        )


class CapitalFlowAnalyzer:
    """수급 분석기"""
    
    def analyze(self, df: pd.DataFrame) -> CapitalFlow:
        """수급 분석"""
        if df is None or len(df) < 25:
            return CapitalFlow()
        
        volumes = df['Volume'].values
        closes = df['Close'].values
        opens = df['Open'].values
        highs = df['High'].values
        lows = df['Low'].values
        
        # RVol (Relative Volume)
        current_vol = volumes[-1]
        avg_vol_20 = np.mean(volumes[-20:])
        rvol = current_vol / avg_vol_20 if avg_vol_20 > 0 else 1.0
        
        # VIR (Volume Increase Rate)
        vir = ((volumes[-1] - volumes[-2]) / volumes[-2] * 100) if volumes[-2] > 0 else 0
        
        # 누적/분배 확인 (간단 버전)
        # (종가 - 저가) / (고가 - 저가) > 0.7 → 누적
        # (종가 - 저가) / (고가 - 저가) < 0.3 → 분배
        if len(closes) >= 5:
            recent_range = highs[-5:] - lows[-5:]
            recent_close_pos = (closes[-5:] - lows[-5:]) / recent_range
            avg_close_pos = np.mean(recent_close_pos)
            
            accumulation = avg_close_pos > 0.6 and rvol > 1.5
            distribution = avg_close_pos < 0.4 and rvol > 1.5
        else:
            accumulation = False
            distribution = False
        
        # 스마트머니 신호
        if rvol >= 2.0 and accumulation:
            smart_sign = 'strong_buy'
        elif rvol >= 1.5 and accumulation:
            smart_sign = 'buy'
        elif rvol >= 2.0 and distribution:
            smart_sign = 'strong_sell'
        elif rvol >= 1.5 and distribution:
            smart_sign = 'sell'
        else:
            smart_sign = 'neutral'
        
        return CapitalFlow(
            rvol=round(rvol, 2),
            vir=round(vir, 1),
            accumulation=accumulation,
            distribution=distribution,
            smart_money_sign=smart_sign
        )


class IVFScanner:
    """
    ICT + Volume Profile + Fibonacci + 수급 통합 스캐너
    """
    
    def __init__(self):
        self.ict = ICTAnalyzer()
        self.vp = VolumeProfileAnalyzer()
        self.fib = FibonacciWaveAnalyzer()
        self.flow = CapitalFlowAnalyzer()
    
    def scan_symbol(self, symbol: str) -> Dict:
        """단일 종목 스캔"""
        try:
            # 데이터 로드
            df = get_price(symbol,
                          (datetime.now() - timedelta(days=90)).strftime('%Y-%m-%d'),
                          datetime.now().strftime('%Y-%m-%d'))
            
            if df is None or len(df) < 30:
                return None
            
            df = df.reset_index()
            
            # 각 모듈 분석
            ict_signals = self.ict.analyze(symbol)
            vp_data = self.vp.calculate(df)
            fib_data = self.fib.analyze(df)
            flow_data = self.flow.analyze(df)
            
            # 통합 신호 생성
            return self.generate_signal(
                symbol, ict_signals, vp_data, fib_data, flow_data, df
            )
            
        except Exception as e:
            return None
    
    def generate_signal(self, symbol: str, ict: ICTSignals, vp: VolumeProfile,
                       fib: FibonacciLevels, flow: CapitalFlow, df: pd.DataFrame) -> Dict:
        """통합 신호 생성"""
        
        score = 0
        confluence = []
        current_price = df['Close'].iloc[-1]
        
        # 1. ICT 점수 (35점)
        if ict.structure == 'bullish':
            score += 15
            confluence.append('Bullish_Structure')
        if ict.order_block_bullish:
            ob = ict.order_block_bullish
            # 현재가가 OB 근처인지 확인
            if ob['low'] * 0.98 <= current_price <= ob['high'] * 1.02:
                score += 20
                confluence.append('OB_Near')
        if ict.fvg_bullish:
            fvg = ict.fvg_bullish
            if fvg['bottom'] <= current_price <= fvg['top']:
                score += 10
                confluence.append('FVG')
        
        # 2. 볼륨 프로파일 점수 (20점)
        if vp.price_vs_poc == 'at':
            score += 20
            confluence.append('POC_Support')
        elif vp.price_vs_poc == 'above' and current_price <= vp.vah:
            score += 15
            confluence.append('In_VA')
        
        # 3. 피볼나치 점수 (25점)
        if 50 <= fib.current_retracement <= 79:
            score += 25
            confluence.append('OTE_Zone')
        elif 38 <= fib.current_retracement < 50:
            score += 15
            confluence.append('Fib_382')
        
        # 4. 수급 점수 (20점)
        if flow.rvol >= 2.0:
            score += 15
            confluence.append('High_RVol')
        elif flow.rvol >= 1.5:
            score += 10
            confluence.append('Volume_Up')
        
        if flow.accumulation:
            score += 10
            confluence.append('Accumulation')
        
        # 진입 구간 계산
        entry_zone = self.calculate_entry_zone(ict, fib, vp)
        
        # 손절가 계산
        stop_loss = self.calculate_stop_loss(ict, fib, current_price)
        
        # 목표가 계산
        targets = self.calculate_targets(fib, df)
        
        # 신호 등급
        if score >= 80:
            signal = 'STRONG_BUY'
        elif score >= 65:
            signal = 'BUY'
        elif score >= 50:
            signal = 'WATCH'
        else:
            signal = 'NEUTRAL'
        
        return {
            'symbol': symbol,
            'date': datetime.now().strftime('%Y-%m-%d'),
            'signal': signal,
            'score': score,
            'price': round(current_price, 0),
            'confluence': confluence,
            'ict_structure': ict.structure,
            'rvol': flow.rvol,
            'fib_retracement': round(fib.current_retracement, 1),
            'entry_zone': entry_zone,
            'stop_loss': round(stop_loss, 0),
            'targets': targets
        }
    
    def calculate_entry_zone(self, ict: ICTSignals, fib: FibonacciLevels, 
                            vp: VolumeProfile) -> Dict:
        """진입 구간 계산"""
        zone = {}
        
        # OTE Zone 우선
        if fib.ote_zone[0] > 0:
            zone['ote_top'] = round(fib.ote_zone[0], 0)
            zone['ote_bottom'] = round(fib.ote_zone[1], 0)
        
        # Order Block 추가
        if ict.order_block_bullish:
            ob = ict.order_block_bullish
            zone['ob_high'] = round(ob['high'], 0)
            zone['ob_low'] = round(ob['low'], 0)
        
        # POC 추가
        if vp.poc > 0:
            zone['poc'] = round(vp.poc, 0)
        
        return zone
    
    def calculate_stop_loss(self, ict: ICTSignals, fib: FibonacciLevels, 
                           current_price: float) -> float:
        """손절가 계산"""
        # OB 기준 손절
        if ict.order_block_bullish:
            return ict.order_block_bullish['low'] * 0.995
        
        # Fib 기준 손절
        if fib.retracements:
            return fib.retracements.get('78.6%', current_price * 0.97)
        
        return current_price * 0.95
    
    def calculate_targets(self, fib: FibonacciLevels, df: pd.DataFrame) -> Dict:
        """목표가 계산"""
        current_price = df['Close'].iloc[-1]
        recent_high = df['High'].iloc[-20:].max()
        
        # Fib Extension 기준
        targets = {
            'tp1': round(recent_high, 0),  # 스윙 고점
            'tp2': round(current_price * 1.15, 0),  # +15%
            'tp3': round(current_price * 1.25, 0),  # +25%
        }
        
        return targets


if __name__ == '__main__':
    # 테스트
    scanner = IVFScanner()
    
    test_symbols = ['005930', '042700', '033100', '348210']
    
    print("=" * 80)
    print("🔥 ICT + Volume Profile + Fibonacci + 수급 통합 스캐너")
    print("=" * 80)
    
    results = []
    for symbol in test_symbols:
        result = scanner.scan_symbol(symbol)
        if result:
            results.append(result)
            
            emoji = '📈' if result['signal'] in ['BUY', 'STRONG_BUY'] else '➖'
            print(f"\n{emoji} {result['symbol']}")
            print(f"   신호: {result['signal']} ({result['score']}점)")
            print(f"   현재가: {result['price']:,}원")
            print(f"   수급: RVol {result['rvol']}")
            print(f"   피볼나치: {result['fib_retracement']:.1f}%")
            print(f"   합치: {', '.join(result['confluence'])}")
            print(f"   손절가: {result['stop_loss']:,}원")
            print(f"   목표: TP1 {result['targets']['tp1']:,} / "
                  f"TP2 {result['targets']['tp2']:,} / "
                  f"TP3 {result['targets']['tp3']:,}")
    
    # 정렬
    results.sort(key=lambda x: x['score'], reverse=True)
    
    print("\n" + "=" * 80)
    print("📊 종합 랭킹")
    print("=" * 80)
    print(f"{'순위':<4} {'종목':<10} {'신호':<12} {'점수':<6} {'RVol':<6} {'OTE%':<6}")
    print("-" * 80)
    
    for i, r in enumerate(results[:10], 1):
        print(f"{i:<4} {r['symbol']:<10} {r['signal']:<12} {r['score']:<6} "
              f"{r['rvol']:<6.1f} {r['fib_retracement']:<6.1f}")
