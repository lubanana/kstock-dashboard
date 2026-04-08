#!/usr/bin/env python3
"""
KRX Hybrid Strategy - KRX 실시간 데이터 + 기술적 분석 하이브리드 스캐너
실시간 지수 + 당일 시세 활용한 고급 전략
"""

import sys
sys.path.insert(0, '/root/.openclaw/workspace/strg')

import pandas as pd
import numpy as np
from typing import List, Dict, Optional
from datetime import datetime, timedelta

from v2.core.strategy_base import StrategyBase, Signal, StrategyConfig
from v2.core.indicators import Indicators
from v2.core.data_manager import DataManager
from v2.core.krx_datasource import KRXDataSource


class KRXHybridStrategy(StrategyBase):
    """
    KRX 하이브리드 전략
    - 실시간 지수 데이터로 시장 맥락 파악
    - KRX 당일 시세로 가격 검증
    - 기존 기술적 지표와 결합한 종합 스코어링
    """
    
    def __init__(self, config: StrategyConfig = None):
        if config is None:
            config = StrategyConfig(
                name='KRX Hybrid',
                description='KRX 실시간 데이터 + 기술적 분석 하이브리드',
                min_score=70.0,
                stop_loss=-0.07,
                take_profit=0.25,
                max_holding_days=7
            )
        super().__init__(config)
        self.krx = KRXDataSource()
        self.dm = DataManager()
        
        # KRX 실시간 데이터 캐시
        self.today_data: Optional[pd.DataFrame] = None
        self.kospi_change: float = 0.0
        
    def _fetch_krx_data(self, date: str):
        """KRX 실시간 데이터 로드"""
        print(f"📡 KRX 실시간 데이터 수집 중... ({date})")
        self.today_data = self.krx.fetch_daily_prices(date)
        
        # 시장 지수
        kospi_index = self.krx.api.get_kospi_index(date)
        if kospi_index:
            for idx in kospi_index:
                if idx.get('IDX_NM') == '코스피':
                    self.kospi_change = float(idx.get('FLUC_RT', 0) or 0)
                    print(f"📊 KOSPI: {idx.get('CLSPRC_IDX')} ({self.kospi_change:+.2f}%)")
                    break
    
    def analyze(self, 
                df: pd.DataFrame, 
                code: str,
                date: str) -> Optional[Signal]:
        """
        개별 종목 분석 - DB 데이터 + KRX 실시간 데이터 결합
        """
        # KRX 데이터가 없으면 분석 불가
        if self.today_data is None or code not in self.today_data['code'].values:
            return None
        
        today_row = self.today_data[self.today_data['code'] == code].iloc[0]
        
        # 과거 데이터로 기술적 지표 계산
        closes = df['close'].values
        volumes = df['volume'].values
        
        # RSI
        rsi_series = Indicators.rsi(df['close'], period=14)
        current_rsi = rsi_series.iloc[-1] if len(rsi_series) > 0 else 50
        
        # MACD
        macd_line, signal_line, hist = Indicators.macd(df['close'])
        macd_bullish = hist.iloc[-1] > 0 and hist.iloc[-2] < 0 if len(hist) >= 2 else False
        
        # 볼린저 밴드
        upper, middle, lower = Indicators.bollinger_bands(df['close'])
        bb_position = (closes[-1] - lower.iloc[-1]) / (upper.iloc[-1] - lower.iloc[-1]) if upper.iloc[-1] != lower.iloc[-1] else 0.5
        
        # 거래량 비율
        avg_volume = np.mean(volumes[-20:])
        today_volume = today_row['volume']
        volume_ratio = today_volume / avg_volume if avg_volume > 0 else 1.0
        
        # KRX 실시간 데이터 기반 스코어링
        scores = {}
        reasons = []
        
        # 가격 변동 점수 (당일 등락률)
        change_pct = today_row['change_pct']
        if -3 <= change_pct <= 5:
            scores['price_momentum'] = min(20, max(0, 10 + change_pct * 2))
        else:
            scores['price_momentum'] = 0
        
        # RSI 점수
        if 35 <= current_rsi <= 65:
            scores['rsi'] = 20 - abs(current_rsi - 50) * 0.4
            reasons.append(f"RSI {current_rsi:.1f}")
        else:
            scores['rsi'] = 0
        
        # 거래량 점수
        if volume_ratio >= 1.2:
            scores['volume'] = min(20, volume_ratio * 10)
            reasons.append(f"거래량 {volume_ratio:.1f}x")
        else:
            scores['volume'] = 0
        
        # MACD 점수
        if macd_bullish:
            scores['macd'] = 15
            reasons.append("MACD 반전")
        elif hist.iloc[-1] > 0:
            scores['macd'] = 5
        else:
            scores['macd'] = 0
        
        # 볼린저 밴드 점수
        if bb_position < 0.3:
            scores['bollinger'] = 20
            reasons.append("볼린저 하단")
        elif bb_position < 0.5:
            scores['bollinger'] = 10
        else:
            scores['bollinger'] = 0
        
        # 시장 맥락 점수
        stock_vs_market = change_pct - self.kospi_change
        if stock_vs_market > 2:
            scores['market_context'] = 15
            reasons.append(f"시장대비 +{stock_vs_market:.1f}%")
        elif stock_vs_market > 0:
            scores['market_context'] = 10
        else:
            scores['market_context'] = 5
        
        # 종합 점수
        total_score = sum(scores.values())
        
        if total_score >= self.config.min_score:
            return Signal(
                code=code,
                name=today_row['name'],
                date=date,
                signal_type='buy',
                score=total_score,
                reason=reasons,
                metadata={
                    'krx': {
                        'price': today_row['close'],
                        'open': today_row['open'],
                        'high': today_row['high'],
                        'low': today_row['low'],
                        'volume': today_row['volume'],
                        'change_pct': change_pct,
                        'market_cap': today_row['market_cap'],
                        'market': today_row['market']
                    },
                    'technical': {
                        'rsi': round(current_rsi, 2),
                        'volume_ratio': round(volume_ratio, 2),
                        'bb_position': round(bb_position, 2),
                        'macd_bullish': macd_bullish
                    },
                    'market_context': {
                        'kospi_change': self.kospi_change,
                        'stock_vs_market': round(stock_vs_market, 2)
                    },
                    'scores': scores
                }
            )
        
        return None
    
    def run(self, 
           data_manager,
           date: str,
           codes: Optional[List[str]] = None) -> List[Signal]:
        """전략 실행 - KRX 데이터 로드 포함"""
        # KRX용 날짜 형식 (YYYYMMDD)
        if '-' in date:
            date_krx = date.replace('-', '')
        else:
            date_krx = date
        
        # KRX 데이터 먼저 로드
        self._fetch_krx_data(date_krx)
        
        if self.today_data is None or self.today_data.empty:
            print("❌ KRX 데이터 수집 실패")
            return []
        
        # KRX에 있는 종목만 분석
        if codes is None:
            codes = self.today_data['code'].tolist()
        else:
            # KRX 데이터 있는 종목만 필터
            krx_codes = set(self.today_data['code'].tolist())
            codes = [c for c in codes if c in krx_codes]
        
        print(f"📊 분석 대상: {len(codes)}개 종목")
        
        # 부모 클래스의 run 호출 (YYYY-MM-DD 형식)
        return super().run(data_manager, date, codes)


def run_krx_hybrid_scan(date: str = None, min_score: float = 70.0, top_n: int = 20):
    """
    KRX 하이브리드 스캐너 실행
    
    Args:
        date: YYYYMMDD 형식, None이면 오늘
        min_score: 최소 점수
        top_n: 상위 N개 출력
    """
    print("=" * 70)
    print("🚀 KRX Hybrid Strategy Scanner")
    print("=" * 70)
    
    if date is None:
        date = datetime.now().strftime('%Y%m%d')
    
    # 날짜 형식 변환 (YYYYMMDD -> YYYY-MM-DD for DataManager)
    if len(date) == 8:
        date_formatted = f"{date[:4]}-{date[4:6]}-{date[6:]}"
    else:
        date_formatted = date
    
    # 전략 설정
    config = StrategyConfig(
        name='KRX Hybrid',
        description='KRX 실시간 + 기술적 분석',
        min_score=min_score
    )
    
    strategy = KRXHybridStrategy(config)
    dm = DataManager()
    
    # 스캔 실행
    signals = strategy.run(dm, date_formatted)
    
    # 결과 정렬
    signals = sorted(signals, key=lambda x: x.score, reverse=True)
    
    # 결과 출력
    print("\n" + "=" * 70)
    print(f"📈 스캔 결과 (Top {top_n})")
    print("=" * 70)
    
    for i, signal in enumerate(signals[:top_n], 1):
        meta = signal.metadata
        krx = meta.get('krx', {})
        tech = meta.get('technical', {})
        
        print(f"\n{i}. {signal.name} ({signal.code})")
        print(f"   💯 종합 점수: {signal.score:.1f}/100")
        print(f"   💰 현재가: {krx.get('price', 0):,}원 ({krx.get('change_pct', 0):+.2f}%)")
        print(f"   📊 시총: {krx.get('market_cap', 0)/1e8:.0f}억")
        print(f"   📈 RSI: {tech.get('rsi', 'N/A')} | 거래량: {tech.get('volume_ratio', 'N/A')}x")
        print(f"   🎯 사유: {', '.join(signal.reason)}")
    
    print("\n" + "=" * 70)
    print(f"✅ 총 {len(signals)}개 신호 발견 (점수 {min_score}+)")
    print("=" * 70)
    
    return signals


if __name__ == '__main__':
    import sys
    
    date = sys.argv[1] if len(sys.argv) > 1 else None
    min_score = float(sys.argv[2]) if len(sys.argv) > 2 else 70.0
    
    run_krx_hybrid_scan(date, min_score)
