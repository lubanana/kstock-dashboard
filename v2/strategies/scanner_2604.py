#!/usr/bin/env python3
"""
2604 Scanner - Ultimate Hybrid Strategy
2026년 4월 최종 통합 스캐너

모든 전략의 장점 결합:
- KAGGRESSIVE 폭발적 상승 (거래량 + 기술적)
- IVF (피볼나치 + ICT + 수급)
- KRX Hybrid (실시간 데이터 + 시장 맥락)
- D+ 주도주 (섹터 모멘텀)

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
from datetime import datetime

from v2.core.strategy_base import StrategyBase, Signal, StrategyConfig
from v2.core.indicators import Indicators
from v2.core.data_manager import DataManager
from v2.core.krx_datasource import KRXDataSource


class Scanner2604(StrategyBase):
    """
    2604 통합 스캐너
    2026년 4월 최종 하이브리드 전략
    """
    
    def __init__(self, use_krx: bool = True):
        config = StrategyConfig(
            name="2604 통합 스캐너",
            description="KAGGRESSIVE + IVF + KRX Hybrid 통합",
            min_score=75.0,  # 75점 이상 진입
            position_size=0.15,
            stop_loss=-0.07,
            take_profit=0.25
        )
        super().__init__(config)
        
        self.use_krx = use_krx
        self.krx = KRXDataSource() if use_krx else None
        self.dm = DataManager()
        
        # KRX 데이터 캐시
        self.today_data: Optional[pd.DataFrame] = None
        self.kospi_change: float = 0.0
    
    def _fetch_krx_data(self, date: str):
        """KRX 실시간 데이터 로드"""
        if not self.use_krx or self.krx is None:
            return
        
        self.today_data = self.krx.fetch_daily_prices(date)
        
        # 시장 지수
        kospi_index = self.krx.api.get_kospi_index(date)
        if kospi_index:
            for idx in kospi_index:
                if idx.get('IDX_NM') == '코스피':
                    self.kospi_change = float(idx.get('FLUC_RT', 0) or 0)
                    break
    
    def analyze(self, df: pd.DataFrame, code: str, date: str) -> Optional[Signal]:
        """2604 통합 분석"""
        if len(df) < 60:
            return None
        
        # KRX 데이터 확인
        krx_row = None
        if self.today_data is not None and code in self.today_data['code'].values:
            krx_row = self.today_data[self.today_data['code'] == code].iloc[0]
        
        # 기술적 지표 계산
        df = self._calculate_indicators(df)
        latest = df.iloc[-1]
        
        # 점수 계산
        scores = {}
        reasons = []
        metadata = {}
        
        # 1. 거래량 분석 (25점)
        vol_score, vol_reasons, vol_meta = self._score_volume(df, krx_row)
        scores['volume'] = vol_score
        reasons.extend(vol_reasons)
        metadata['volume'] = vol_meta
        
        # 2. 기술적 지표 (25점)
        tech_score, tech_reasons, tech_meta = self._score_technical(df)
        scores['technical'] = tech_score
        reasons.extend(tech_reasons)
        metadata['technical'] = tech_meta
        
        # 3. 피볼나치 파동 (20점)
        fib_score, fib_reasons, fib_meta = self._score_fibonacci(df)
        scores['fibonacci'] = fib_score
        reasons.extend(fib_reasons)
        metadata['fibonacci'] = fib_meta
        
        # 4. 시장 맥락 (15점)
        market_score, market_reasons, market_meta = self._score_market_context(df, krx_row)
        scores['market'] = market_score
        reasons.extend(market_reasons)
        metadata['market'] = market_meta
        
        # 5. 모멘텀 (15점)
        mom_score, mom_reasons, mom_meta = self._score_momentum(df, krx_row)
        scores['momentum'] = mom_score
        reasons.extend(mom_reasons)
        metadata['momentum'] = mom_meta
        
        # 총점 계산
        total_score = sum(scores.values())
        metadata['scores'] = scores
        metadata['total_score'] = total_score
        
        # 진입 조건 체크
        if total_score < self.config.min_score:
            return None
        
        # 필수 조건: 거래량 + 기술적 둘 다 50% 이상
        if scores['volume'] < 12.5 or scores['technical'] < 12.5:
            return None
        
        # RSI 필터 (과매도/과매수 제외)
        rsi = tech_meta.get('rsi', 50)
        if rsi < 35 or rsi > 75:
            return None
        
        # ADX 필터 (추세 강도)
        adx = tech_meta.get('adx', 0)
        if adx < 15:
            return None
        
        # Signal 생성
        signal_type = 'strong_buy' if total_score >= 85 else 'buy'
        
        # 가격 정보
        if krx_row is not None:
            price = krx_row['close']
            name = krx_row['name']
            market_cap = krx_row['market_cap']
        else:
            price = latest['close']
            name = latest.get('name', code)
            market_cap = 0
        
        return Signal(
            code=code,
            name=name,
            date=date,
            signal_type=signal_type,
            score=total_score,
            reason=reasons[:5],  # 상위 5개 사유만
            metadata={
                'price': price,
                'market_cap': market_cap,
                'indicators': tech_meta,
                'scores': scores,
                **metadata
            }
        )
    
    def _calculate_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        """기술적 지표 계산"""
        df = df.copy()
        
        # 이동평균
        df['ma5'] = Indicators.ma(df['close'], 5)
        df['ma20'] = Indicators.ma(df['close'], 20)
        df['ma60'] = Indicators.ma(df['close'], 60)
        
        # RSI
        df['rsi'] = Indicators.rsi(df['close'], 14)
        
        # MACD
        df['macd'], df['macd_signal'], df['macd_hist'] = Indicators.macd(df['close'])
        
        # 볼린저 밴드
        df['bb_upper'], df['bb_middle'], df['bb_lower'] = Indicators.bollinger_bands(df['close'])
        df['bb_position'] = (df['close'] - df['bb_lower']) / (df['bb_upper'] - df['bb_lower'])
        
        # ADX
        df['adx'] = Indicators.adx(df, 14)
        
        # ATR
        df['atr'] = Indicators.atr(df, 14)
        
        # 거래량
        df['volume_ratio'] = Indicators.volume_ratio(df['volume'], 20)
        
        return df
    
    def _score_volume(self, df: pd.DataFrame, krx_row: Optional[pd.Series]) -> Tuple[float, List, Dict]:
        """거래량 분석 (25점)"""
        score = 0.0
        reasons = []
        meta = {}
        
        latest = df.iloc[-1]
        vol_ratio = latest['volume_ratio']
        
        # 거래량 급증 점수
        if vol_ratio >= 5.0:
            score += 25
            reasons.append(f"거래량 폭발 ({vol_ratio:.1f}x)")
        elif vol_ratio >= 3.0:
            score += 20
            reasons.append(f"거래량 급증 ({vol_ratio:.1f}x)")
        elif vol_ratio >= 2.0:
            score += 15
            reasons.append(f"거래량 증가 ({vol_ratio:.1f}x)")
        elif vol_ratio >= 1.5:
            score += 10
            reasons.append(f"거래량 확대 ({vol_ratio:.1f}x)")
        elif vol_ratio >= 1.2:
            score += 5
        
        # Volume Profile (POC 근접)
        recent = df.tail(20)
        poc_idx = recent['volume'].idxmax()
        poc_price = recent.loc[poc_idx, 'close']
        current_price = latest['close']
        poc_distance = abs(current_price - poc_price) / current_price
        
        if poc_distance <= 0.02:
            score += 5
            reasons.append("POC 근접")
        
        meta['volume_ratio'] = vol_ratio
        meta['poc_distance'] = poc_distance
        
        return min(score, 25), reasons, meta
    
    def _score_technical(self, df: pd.DataFrame) -> Tuple[float, List, Dict]:
        """기술적 지표 (25점)"""
        score = 0.0
        reasons = []
        meta = {}
        
        latest = df.iloc[-1]
        prev = df.iloc[-2] if len(df) > 1 else latest
        
        # RSI 점수 (35~65 선호)
        rsi = latest['rsi']
        if 40 <= rsi <= 60:
            score += 10
            reasons.append(f"RSI 적정 ({rsi:.1f})")
        elif 35 <= rsi < 40 or 60 < rsi <= 65:
            score += 5
        
        # MACD 반전
        macd_bullish = latest['macd_hist'] > 0 and prev['macd_hist'] <= 0
        if macd_bullish:
            score += 8
            reasons.append("MACD 반전")
        elif latest['macd_hist'] > 0:
            score += 4
        
        # 볼린저 밴드
        bb_pos = latest['bb_position']
        if bb_pos < 0.3:
            score += 7
            reasons.append("볼린저 하단")
        elif bb_pos < 0.5:
            score += 4
        
        # 정배열
        ma_aligned = latest['close'] > latest['ma20'] > latest['ma60']
        if ma_aligned:
            score += 5
            reasons.append("정배열")
        
        # ADX
        adx = latest['adx']
        if adx >= 25:
            score += 5
        
        meta['rsi'] = rsi
        meta['adx'] = adx
        meta['macd_bullish'] = macd_bullish
        meta['bb_position'] = bb_pos
        meta['ma_aligned'] = ma_aligned
        
        return min(score, 25), reasons, meta
    
    def _score_fibonacci(self, df: pd.DataFrame) -> Tuple[float, List, Dict]:
        """피볼나치 파동 (20점)"""
        score = 0.0
        reasons = []
        meta = {}
        
        # 최근 추세의 고점/저점
        recent = df.tail(40)
        swing_high = recent['high'].max()
        swing_low = recent['low'].min()
        
        if swing_high == swing_low:
            return 0, reasons, meta
        
        current_price = df.iloc[-1]['close']
        diff = swing_high - swing_low
        
        # 되돌림 레벨
        fib_382 = swing_high - diff * 0.382
        fib_500 = swing_high - diff * 0.5
        fib_618 = swing_high - diff * 0.618
        
        # 38.2%~61.8% 되돌림 구간
        in_retracement = fib_382 >= current_price >= fib_618
        
        if in_retracement:
            score += 15
            reasons.append("피볼나치 되돌림 구간")
            
            # 정확한 레벨 근접
            distances = [
                abs(current_price - fib_382) / current_price,
                abs(current_price - fib_500) / current_price,
                abs(current_price - fib_618) / current_price
            ]
            if min(distances) <= 0.01:
                score += 5
                reasons.append("피볼나치 레벨 정확히 적중")
        
        # 161.8% 확장 목표
        extension = swing_high + diff * 0.618
        if current_price > swing_high * 0.95:
            score += 5
            meta['near_breakout'] = True
        
        meta['swing_high'] = swing_high
        meta['swing_low'] = swing_low
        meta['fib_382'] = fib_382
        meta['fib_618'] = fib_618
        meta['extension_1618'] = extension
        
        return min(score, 20), reasons, meta
    
    def _score_market_context(self, df: pd.DataFrame, krx_row: Optional[pd.Series]) -> Tuple[float, List, Dict]:
        """시장 맥락 (15점)"""
        score = 0.0
        reasons = []
        meta = {}
        
        latest = df.iloc[-1]
        
        # 당일 등락률 (KRX 데이터 우선)
        if krx_row is not None:
            change_pct = krx_row['change_pct']
        else:
            change_pct = ((latest['close'] - latest['open']) / latest['open']) * 100
        
        # 적정 등락률 (-3%~+5% 선호)
        if -1 <= change_pct <= 3:
            score += 8
            reasons.append(f"안정적 상승 ({change_pct:+.1f}%)")
        elif -3 <= change_pct < -1:
            score += 6
            reasons.append(f"눌림목 ({change_pct:+.1f}%)")
        elif 3 < change_pct <= 5:
            score += 6
        
        # 시장 대비 아웃퍼폼
        if self.kospi_change != 0:
            vs_market = change_pct - self.kospi_change
            if vs_market > 3:
                score += 7
                reasons.append(f"시장대비 강세 (+{vs_market:.1f}%)")
            elif vs_market > 0:
                score += 4
            
            meta['vs_kospi'] = vs_market
        
        meta['change_pct'] = change_pct
        meta['kospi_change'] = self.kospi_change
        
        return min(score, 15), reasons, meta
    
    def _score_momentum(self, df: pd.DataFrame, krx_row: Optional[pd.Series]) -> Tuple[float, List, Dict]:
        """모멘텀 (15점)"""
        score = 0.0
        reasons = []
        meta = {}
        
        # 연속 상승일
        recent_changes = df.tail(5)['close'].pct_change().dropna()
        up_days = sum(1 for c in recent_changes if c > 0)
        
        if up_days >= 4:
            score += 8
            reasons.append(f"{up_days}일 연속 상승")
        elif up_days >= 3:
            score += 5
            reasons.append(f"3일 연속 상승")
        
        # 가격 위치 (52주 대비)
        high_52w = df.tail(252)['high'].max() if len(df) >= 252 else df['high'].max()
        low_52w = df.tail(252)['low'].min() if len(df) >= 252 else df['low'].min()
        current = df.iloc[-1]['close']
        
        if high_52w != low_52w:
            position = (current - low_52w) / (high_52w - low_52w)
            
            if 0.3 <= position <= 0.7:  # 중간 구간
                score += 7
                reasons.append("적정 가격대")
            elif position > 0.7:
                score += 3  # 고점 근처
            
            meta['position_52w'] = position
        
        meta['up_days'] = up_days
        
        return min(score, 15), reasons, meta
    
    def run(self, data_manager, date: str, codes: Optional[List[str]] = None) -> List[Signal]:
        """2604 스캐너 실행"""
        # KRX 데이터 로드
        if self.use_krx:
            date_krx = date.replace('-', '')
            self._fetch_krx_data(date_krx)
            
            if self.today_data is not None and not self.today_data.empty:
                if codes is None:
                    codes = self.today_data['code'].tolist()
                else:
                    krx_codes = set(self.today_data['code'].tolist())
                    codes = [c for c in codes if c in krx_codes]
        
        return super().run(data_manager, date, codes)


def run_2604_scan(date: str = None, min_score: float = 75.0, top_n: int = 20, use_krx: bool = True):
    """
    2604 스캐너 실행
    
    Args:
        date: YYYYMMDD or YYYY-MM-DD
        min_score: 최소 점수 (기본 75)
        top_n: 상위 N개 출력
        use_krx: KRX 데이터 사용 여부
    """
    print("=" * 80)
    print("🔥 2604 통합 스캐너 - Ultimate Hybrid Strategy")
    print("=" * 80)
    print("전략: KAGGRESSIVE + IVF + KRX Hybrid + D+ 통합")
    print("-" * 80)
    
    if date is None:
        date = datetime.now().strftime('%Y%m%d')
    
    # 날짜 형식 통일
    if len(date) == 8:
        date_formatted = f"{date[:4]}-{date[4:6]}-{date[6:]}"
    else:
        date_formatted = date
    
    # 스캐너 실행
    scanner = Scanner2604(use_krx=use_krx)
    dm = DataManager()
    
    signals = scanner.run(dm, date_formatted)
    signals = sorted(signals, key=lambda x: x.score, reverse=True)
    
    # 결과 출력
    print(f"\n📊 스캔 결과: {len(signals)}개 신호 발견 (점수 {min_score}+)")
    print("=" * 80)
    
    for i, signal in enumerate(signals[:top_n], 1):
        meta = signal.metadata
        scores = meta.get('scores', {})
        
        print(f"\n{i}. {signal.name} ({signal.code})")
        print(f"   💯 종합 점수: {signal.score:.1f}/100")
        print(f"   💰 현재가: {meta.get('price', 0):,.0f}원")
        print(f"   📊 세부 점수: 거래량 {scores.get('volume', 0):.0f} | 기술적 {scores.get('technical', 0):.0f} | 피볼 {scores.get('fibonacci', 0):.0f} | 시장 {scores.get('market', 0):.0f} | 모멘 {scores.get('momentum', 0):.0f}")
        print(f"   🎯 사유: {', '.join(signal.reason[:3])}")
    
    print("\n" + "=" * 80)
    print(f"✅ 2604 스캔 완료 - 총 {len(signals)}개 선정")
    print("=" * 80)
    
    return signals


if __name__ == '__main__':
    import sys
    
    date = sys.argv[1] if len(sys.argv) > 1 else None
    min_score = float(sys.argv[2]) if len(sys.argv) > 2 else 75.0
    
    run_2604_scan(date, min_score)
