#!/usr/bin/env python3
"""
2604 Scanner V2 - 개선된 통합 스캐너
2026년 4월 8일 개선판

개선사항:
1. 데이터 품질 필터 강화 (open > 0, volume > 0)
2. 로컬DB 우선 사용, KRX 보조
3. 영업일 기준 처리
4. 성능 최적화 (배치 처리)
5. 필수 필터 개선 (RSI 35-70, ADX 15+)

스코어링 (100점 만점):
- 거래량 분석: 25점
- 기술적 지표: 25점 (RSI, MACD, 볼린저, ADX)
- 피볼나치 파동: 20점
- 시장 맥락: 15점
- 모멘텀: 15점
"""

import sys
sys.path.insert(0, '/root/.openclaw/workspace/strg')

import pandas as pd
import numpy as np
from typing import List, Dict, Optional, Tuple
from datetime import datetime, timedelta

from v2.core.strategy_base import StrategyBase, Signal, StrategyConfig
from v2.core.indicators import Indicators
from v2.core.data_manager import DataManager
from v2.core.krx_datasource import KRXDataSource


class Scanner2604V2(StrategyBase):
    """
    2604 통합 스캐너 V2 (개선판)
    """
    
    def __init__(self, use_krx: bool = False):
        config = StrategyConfig(
            name="2604 통합 스캐너 V2",
            description="개선된 KAGGRESSIVE + IVF + 기술적 통합",
            min_score=75.0,
            position_size=0.15,
            stop_loss=-0.07,
            take_profit=0.25
        )
        super().__init__(config)
        
        self.use_krx = use_krx
        self.dm = DataManager()
        self.krx = KRXDataSource() if use_krx else None
        self.market_index_change = 0.0
        self.kosdaq_index_change = 0.0
    
    def _validate_data(self, df: pd.DataFrame) -> bool:
        """데이터 품질 검증"""
        if df.empty or len(df) < 60:
            return False
        
        latest = df.iloc[-1]
        
        # 필수 컬럼 확인
        required_cols = ['open', 'high', 'low', 'close', 'volume']
        if not all(col in df.columns for col in required_cols):
            return False
        
        # 가격 데이터 유효성
        if latest['open'] <= 0 or latest['close'] <= 0:
            return False
        
        # 거래량 확인
        if latest['volume'] <= 0:
            return False
        
        # 이상치 확인 (open/close 비율)
        price_ratio = latest['close'] / latest['open']
        if price_ratio < 0.7 or price_ratio > 1.3:  # ±30% 이상 변동 제외
            return False
        
        return True
    
    def _calculate_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        """기술적 지표 계산 (최적화)"""
        df = df.copy()
        
        # 이동평균
        df['ma5'] = df['close'].rolling(5).mean()
        df['ma20'] = df['close'].rolling(20).mean()
        df['ma60'] = df['close'].rolling(60).mean()
        
        # RSI
        df['rsi'] = Indicators.rsi(df['close'], 14)
        
        # MACD
        df['macd'], df['macd_signal'], df['macd_hist'] = Indicators.macd(df['close'])
        
        # 볼린저 밴드
        df['bb_upper'], df['bb_middle'], df['bb_lower'] = Indicators.bollinger_bands(df['close'])
        
        # ADX
        df['adx'] = Indicators.adx(df, 14)
        
        # 거래량
        df['volume_ma20'] = df['volume'].rolling(20).mean()
        df['volume_ratio'] = df['volume'] / df['volume_ma20']
        
        return df
    
    def analyze(self, df: pd.DataFrame, code: str, date: str) -> Optional[Signal]:
        """2604 V2 분석"""
        # 데이터 품질 검증
        if not self._validate_data(df):
            return None
        
        # 기술적 지표 계산
        try:
            df = self._calculate_indicators(df)
        except Exception as e:
            return None
        
        latest = df.iloc[-1]
        prev = df.iloc[-2] if len(df) > 1 else latest
        
        # ===== 필수 필터 (하드 컷) =====
        
        # 1. RSI 필터 (35~70)
        rsi = latest['rsi']
        if pd.isna(rsi) or rsi < 35 or rsi > 70:
            return None
        
        # 2. ADX 필터 (15+)
        adx = latest['adx']
        if pd.isna(adx) or adx < 15:
            return None
        
        # 3. 거래량 필터 (1.2x 이상)
        vol_ratio = latest['volume_ratio']
        if pd.isna(vol_ratio) or vol_ratio < 1.2:
            return None
        
        # ===== 점수 계산 =====
        scores = {}
        reasons = []
        metadata = {}
        
        # 1. 거래량 분석 (25점)
        vol_score = 0
        if vol_ratio >= 5.0:
            vol_score = 25
            reasons.append(f"거래량 폭발 ({vol_ratio:.1f}x)")
        elif vol_ratio >= 3.0:
            vol_score = 20
            reasons.append(f"거래량 급증 ({vol_ratio:.1f}x)")
        elif vol_ratio >= 2.0:
            vol_score = 15
            reasons.append(f"거래량 증가 ({vol_ratio:.1f}x)")
        elif vol_ratio >= 1.5:
            vol_score = 10
            reasons.append(f"거래량 확대 ({vol_ratio:.1f}x)")
        else:
            vol_score = 5
        
        scores['volume'] = vol_score
        metadata['volume_ratio'] = vol_ratio
        
        # 2. 기술적 지표 (25점)
        tech_score = 0
        
        # RSI 적정 (40~60)
        if 40 <= rsi <= 60:
            tech_score += 10
            reasons.append(f"RSI 적정 ({rsi:.1f})")
        elif 35 <= rsi < 40 or 60 < rsi <= 65:
            tech_score += 5
        
        # MACD 반전 또는 양수
        macd_bullish = latest['macd_hist'] > 0 and prev['macd_hist'] <= 0
        if macd_bullish:
            tech_score += 8
            reasons.append("MACD 반전")
        elif latest['macd_hist'] > 0:
            tech_score += 4
        
        # 볼린저 밴드 위치
        bb_pos = (latest['close'] - latest['bb_lower']) / (latest['bb_upper'] - latest['bb_lower'])
        if bb_pos < 0.3:
            tech_score += 7
            reasons.append("볼린저 하단")
        elif bb_pos < 0.5:
            tech_score += 4
        
        # 정배열
        ma_aligned = latest['close'] > latest['ma20'] > latest['ma60']
        if ma_aligned:
            tech_score += 5
            reasons.append("정배열")
        
        # ADX 강도
        if adx >= 25:
            tech_score += 5
        
        scores['technical'] = min(tech_score, 25)
        metadata['rsi'] = rsi
        metadata['adx'] = adx
        metadata['macd_bullish'] = macd_bullish
        metadata['bb_position'] = bb_pos
        metadata['ma_aligned'] = ma_aligned
        
        # 3. 피볼나치 파동 (20점)
        fib_score = 0
        recent = df.tail(40)
        swing_high = recent['high'].max()
        swing_low = recent['low'].min()
        
        if swing_high != swing_low:
            diff = swing_high - swing_low
            fib_382 = swing_high - diff * 0.382
            fib_618 = swing_high - diff * 0.618
            current_price = latest['close']
            
            # 되돌림 구간
            if fib_382 >= current_price >= fib_618:
                fib_score += 15
                reasons.append("피볼나치 되돌림")
        
        scores['fibonacci'] = min(fib_score, 20)
        
        # 4. 시장 맥락 (15점)
        market_score = 0
        change_pct = ((latest['close'] - latest['open']) / latest['open']) * 100
        
        if -1 <= change_pct <= 3:
            market_score += 8
            reasons.append(f"안정적 상승 ({change_pct:+.1f}%)")
        elif -3 <= change_pct < -1:
            market_score += 6
            reasons.append(f"눌림목 ({change_pct:+.1f}%)")
        
        # 코스닥 대비 아웃퍼폼 (KRX 사용 시)
        if self.use_krx and self.kosdaq_index_change != 0:
            vs_kosdaq = change_pct - self.kosdaq_index_change
            if vs_kosdaq > 3:
                market_score += 7
                reasons.append(f"코스닥대비 강세 (+{vs_kosdaq:.1f}%)")
            elif vs_kosdaq > 0:
                market_score += 3
            metadata['vs_kosdaq'] = vs_kosdaq
        
        scores['market'] = min(market_score, 15)
        metadata['change_pct'] = change_pct
        
        # 5. 모멘텀 (15점)
        mom_score = 0
        recent_changes = df.tail(5)['close'].pct_change().dropna()
        up_days = sum(1 for c in recent_changes if c > 0)
        
        if up_days >= 4:
            mom_score += 8
            reasons.append(f"{up_days}일 연속 상승")
        elif up_days >= 3:
            mom_score += 5
            reasons.append("3일 연속 상승")
        
        # 52주 위치
        high_52w = df.tail(252)['high'].max() if len(df) >= 252 else df['high'].max()
        low_52w = df.tail(252)['low'].min() if len(df) >= 252 else df['low'].min()
        
        if high_52w != low_52w:
            position_52w = (latest['close'] - low_52w) / (high_52w - low_52w)
            if 0.3 <= position_52w <= 0.7:
                mom_score += 7
                reasons.append("적정 가격대")
            metadata['position_52w'] = position_52w
        
        scores['momentum'] = min(mom_score, 15)
        metadata['up_days'] = up_days
        
        # 총점 계산
        total_score = sum(scores.values())
        metadata['scores'] = scores
        metadata['total_score'] = total_score
        
        # 진입 조건
        if total_score < self.config.min_score:
            return None
        
        # 필수 조건: 거래량 + 기술적 각각 50% 이상
        if scores['volume'] < 12.5 or scores['technical'] < 12.5:
            return None
        
        # Signal 생성
        signal_type = 'strong_buy' if total_score >= 85 else 'buy'
        
        # 종목명 조회 (DB에서)
        name = self.dm.get_stock_name(code)
        if not name or name == 'Stock' or pd.isna(name):
            name = code
        
        return Signal(
            code=code,
            name=name,
            date=date,
            signal_type=signal_type,
            score=total_score,
            reason=reasons[:5],
            metadata={
                'price': latest['close'],
                'indicators': metadata
            }
        )
    
    def run(self, data_manager, date: str, codes: Optional[List[str]] = None) -> List[Signal]:
        """2604 V2 스캐너 실행"""
        # KRX 데이터 로드 (코스닥 지수 포함)
        if self.use_krx and self.krx:
            date_krx = date.replace('-', '')
            market_status = self.krx.get_market_status(date_krx)
            self.market_index_change = market_status.get('kospi', 0.0)
            self.kosdaq_index_change = market_status.get('kosdaq', 0.0)
            print(f"📈 시장 상태: 코스피 {self.market_index_change:+.2f}%, 코스닥 {self.kosdaq_index_change:+.2f}%")
        
        # DB에서 사용 가능한 종목 로드
        conn = data_manager._get_connection()
        available_codes = pd.read_sql_query(
            f"SELECT DISTINCT code FROM price_data WHERE date='{date}'",
            conn
        )['code'].tolist()
        conn.close()
        
        if codes is None:
            codes = available_codes
        else:
            codes = [c for c in codes if c in available_codes]
        
        print(f"📊 대상 종목: {len(codes)}개 (DB 기준)")
        
        signals = []
        for code in codes:
            df = data_manager.load_stock_data(code, date)
            if df is not None and not df.empty:
                signal = self.analyze(df, code, date)
                if signal:
                    signals.append(signal)
        
        return sorted(signals, key=lambda x: x.score, reverse=True)


def run_2604_v2_scan(date: str = None, min_score: float = 75.0, top_n: int = 20):
    """2604 V2 스캐너 실행"""
    print("=" * 80)
    print("🔥 2604 통합 스캐너 V2 - 개선판")
    print("=" * 80)
    print("개선: 데이터 품질 필터, 로컬DB 우선, 성능 최적화")
    print("-" * 80)
    
    if date is None:
        date = datetime.now().strftime('%Y-%m-%d')
    
    if len(date) == 8:
        date = f"{date[:4]}-{date[4:6]}-{date[6:]}"
    
    scanner = Scanner2604V2(use_krx=False)
    dm = DataManager()
    
    signals = scanner.run(dm, date)
    
    print(f"\n📊 스캔 결과: {len(signals)}개 신호 발견 (점수 {min_score}+)")
    print("=" * 80)
    
    for i, signal in enumerate(signals[:top_n], 1):
        meta = signal.metadata
        scores = meta.get('indicators', {}).get('scores', {})
        
        print(f"\n{i}. {signal.name} ({signal.code})")
        print(f"   💯 종합 점수: {signal.score:.1f}/100")
        print(f"   💰 현재가: {meta.get('price', 0):,.0f}원")
        print(f"   📊 세부 점수: 거래량 {scores.get('volume', 0):.0f} | 기술적 {scores.get('technical', 0):.0f} | 피볼 {scores.get('fibonacci', 0):.0f} | 시장 {scores.get('market', 0):.0f} | 모멘 {scores.get('momentum', 0):.0f}")
        print(f"   🎯 사유: {', '.join(signal.reason[:3])}")
    
    print("\n" + "=" * 80)
    print(f"✅ 2604 V2 스캔 완료 - 총 {len(signals)}개 선정")
    print("=" * 80)
    
    return signals


if __name__ == '__main__':
    import sys
    
    date = sys.argv[1] if len(sys.argv) > 1 else None
    min_score = float(sys.argv[2]) if len(sys.argv) > 2 else 75.0
    
    run_2604_v2_scan(date, min_score)
