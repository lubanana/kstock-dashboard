#!/usr/bin/env python3
"""
2604 V8 Unified Scanner
=======================
2604 V7 + Japanese Strategy (Ichimoku) + Holding Period Recommendation

통합 스코어링 (120점):
- 거래량 (25점): V7 방식 - 20일 평균 대비 거래량
- 기술적 (20점): RSI, MACD, 볼린저, ADX
- 피볼나치 (20점): 38.2%~61.8% 되돌림
- 시장맥락 (15점): 코스닥 대비 아웃퍼폼
- 모멘텀 (10점): 20일 가격 변동률
- 일목균형 (20점): TK_CROSS, 구름 위치, 구름 방향
- 사카타/캔들 (10점): 고전 캔들 패턴 (선택적)

진입 조건: 90점+, ADX 20+, RSI 40~70

Holding Period Recommendation:
- 당일 (1일): score>=95, volatility>=5%, tk_cross
- 단기 (2-3일): score>=100, tk_cross, adx>=30
- 중기 (5-10일): above_cloud, adx>=25, vol<3%
- 장기 (10-20일): above_cloud, thick_cloud>=5%, adx>=20
"""

import sys
sys.path.insert(0, '/root/.openclaw/workspace/strg')

import pandas as pd
import numpy as np
import sqlite3
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass
from enum import Enum
import json

from fibonacci_target_integrated import calculate_scanner_targets


class HoldingPeriod(Enum):
    """추천 보유 기간"""
    DAY_TRADE = (1, 1, "당일 청산", "#ff4757")
    SHORT = (2, 3, "단기 (2-3일)", "#ffa502")
    MEDIUM = (5, 10, "중기 (5-10일)", "#feca57")
    LONG = (10, 20, "장기 (10-20일)", "#2ed573")
    TREND_FOLLOW = (20, 60, "추세 추종 (20-60일)", "#1e90ff")
    
    def __init__(self, min_days: int, max_days: int, description: str, color: str):
        self.min_days = min_days
        self.max_days = max_days
        self.description = description
        self.color = color


@dataclass
class IchimokuSignal:
    """일목균형표 신호"""
    tenkan_sen: float
    kijun_sen: float
    senkou_span_a: float
    senkou_span_b: float
    tk_cross_bullish: bool
    tk_cross_bearish: bool
    price_above_cloud: bool
    price_below_cloud: bool
    bullish_cloud: bool
    cloud_thickness_pct: float
    tenkan_kijun_distance: float
    
    @property
    def score(self) -> int:
        """일목균형표 점수 (0-20점)"""
        score = 0
        if self.tk_cross_bullish:
            score += 8  # TK_CROSS 골든
        if self.price_above_cloud:
            score += 5  # 구름 위
        if self.bullish_cloud:
            score += 4  # 상승 구름
        if self.tenkan_sen > self.kijun_sen:
            score += 3  # 전환선 > 기준선
        return min(score, 20)


class Scanner2604V8Unified:
    """2604 V8 통합 스캐너 (Japanese Strategy Integrated)"""
    
    def __init__(self, db_path: str = 'data/level1_prices.db'):
        self.db_path = db_path
        self.conn = None
        self.kosdaq_change = 0.0
        
        # 일목균형표 파라미터
        self.tenkan_period = 9
        self.kijun_period = 26
        self.senkou_b_period = 52
        self.displacement = 26
        
    def connect(self):
        self.conn = sqlite3.connect(self.db_path)
        return self
    
    def close(self):
        if self.conn:
            self.conn.close()
    
    def fetch_stock_data(self, code: str, end_date: str, days: int = 80) -> Optional[pd.DataFrame]:
        """개별 종목 데이터 로드 (80일 - 일목균형표 52일 + 여유)"""
        query = f"""
        SELECT * FROM price_data 
        WHERE code = '{code}' 
        AND date <= '{end_date}'
        ORDER BY date ASC
        """
        df = pd.read_sql_query(query, self.conn)
        print(f"   총 데이터: {len(df)}개")
        if len(df) < 60:  # 일목균형표 최소 60일 필요
            print(f"   ⚠️ 데이터 부족 (최소 60일 필요)")
            return None
        return df
    
    def calculate_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        """기술적 지표 계산 (기존 + 일목균형표)"""
        df = df.copy()
        
        # 기존 지표
        df['ma5'] = df['close'].rolling(5, min_periods=1).mean()
        df['ma20'] = df['close'].rolling(20, min_periods=1).mean()
        df['ma60'] = df['close'].rolling(60, min_periods=1).mean()
        
        # RSI
        delta = df['close'].diff()
        gain = delta.where(delta > 0, 0)
        loss = -delta.where(delta < 0, 0)
        avg_gain = gain.ewm(span=14, adjust=False, min_periods=1).mean()
        avg_loss = loss.ewm(span=14, adjust=False, min_periods=1).mean()
        rs = avg_gain / avg_loss.replace(0, np.nan)
        df['rsi'] = 100 - (100 / (1 + rs))
        df['rsi'] = df['rsi'].fillna(50)
        
        # MACD
        ema12 = df['close'].ewm(span=12, adjust=False, min_periods=1).mean()
        ema26 = df['close'].ewm(span=26, adjust=False, min_periods=1).mean()
        df['macd'] = ema12 - ema26
        df['macd_signal'] = df['macd'].ewm(span=9, adjust=False, min_periods=1).mean()
        df['macd_hist'] = df['macd'] - df['macd_signal']
        
        # 볼린저
        df['bb_middle'] = df['close'].rolling(20, min_periods=1).mean()
        bb_std = df['close'].rolling(20, min_periods=1).std()
        df['bb_upper'] = df['bb_middle'] + 2 * bb_std
        df['bb_lower'] = df['bb_middle'] - 2 * bb_std
        
        # ATR/ADX
        df['tr1'] = df['high'] - df['low']
        df['tr2'] = abs(df['high'] - df['close'].shift(1))
        df['tr3'] = abs(df['low'] - df['close'].shift(1))
        df['tr'] = df[['tr1', 'tr2', 'tr3']].max(axis=1).fillna(df['high'] - df['low'])
        df['atr'] = df['tr'].ewm(span=14, adjust=False, min_periods=1).mean()
        
        df['plus_dm'] = np.where(
            (df['high'] - df['high'].shift(1)) > (df['low'].shift(1) - df['low']),
            np.maximum(df['high'] - df['high'].shift(1), 0), 0)
        df['minus_dm'] = np.where(
            (df['low'].shift(1) - df['low']) > (df['high'] - df['high'].shift(1)),
            np.maximum(df['low'].shift(1) - df['low'], 0), 0)
        
        df['plus_di'] = 100 * df['plus_dm'].ewm(span=14, adjust=False, min_periods=1).mean() / df['atr'].replace(0, np.nan)
        df['minus_di'] = 100 * df['minus_dm'].ewm(span=14, adjust=False, min_periods=1).mean() / df['atr'].replace(0, np.nan)
        df['dx'] = 100 * abs(df['plus_di'] - df['minus_di']) / (df['plus_di'] + df['minus_di']).replace(0, np.nan)
        df['adx'] = df['dx'].ewm(span=14, adjust=False, min_periods=1).mean()
        df['adx'] = df['adx'].fillna(0)
        
        # 거래량
        df['volume_ma20'] = df['volume'].rolling(20, min_periods=1).mean()
        
        # 일목균형표 계산
        df = self._calculate_ichimoku(df)
        
        return df
    
    def _calculate_ichimoku(self, df: pd.DataFrame) -> pd.DataFrame:
        """일목균형표 계산"""
        # 전환선 (Tenkan-sen): 9일
        high_9 = df['high'].rolling(window=self.tenkan_period).max()
        low_9 = df['low'].rolling(window=self.tenkan_period).min()
        df['tenkan_sen'] = (high_9 + low_9) / 2
        
        # 기준선 (Kijun-sen): 26일
        high_26 = df['high'].rolling(window=self.kijun_period).max()
        low_26 = df['low'].rolling(window=self.kijun_period).min()
        df['kijun_sen'] = (high_26 + low_26) / 2
        
        # 선행스팬1 (Senkou Span A)
        df['senkou_span_a'] = ((df['tenkan_sen'] + df['kijun_sen']) / 2).shift(-self.displacement)
        
        # 선행스팬2 (Senkou Span B): 52일
        high_52 = df['high'].rolling(window=self.senkou_b_period).max()
        low_52 = df['low'].rolling(window=self.senkou_b_period).min()
        df['senkou_span_b'] = ((high_52 + low_52) / 2).shift(-self.displacement)
        
        # 구름
        df['cloud_top'] = df[['senkou_span_a', 'senkou_span_b']].max(axis=1)
        df['cloud_bottom'] = df[['senkou_span_a', 'senkou_span_b']].min(axis=1)
        df['cloud_thickness'] = df['cloud_top'] - df['cloud_bottom']
        df['cloud_thickness_pct'] = df['cloud_thickness'] / df['close'] * 100
        
        # 후행스팬
        df['chikou_span'] = df['close'].shift(self.displacement)
        
        return df
    
    def generate_ichimoku_signal(self, df: pd.DataFrame) -> IchimokuSignal:
        """일목균형표 신호 생성"""
        latest = df.iloc[-1]
        prev = df.iloc[-2] if len(df) > 1 else latest
        
        tk_cross_bullish = (prev['tenkan_sen'] <= prev['kijun_sen'] and 
                           latest['tenkan_sen'] > latest['kijun_sen'])
        tk_cross_bearish = (prev['tenkan_sen'] >= prev['kijun_sen'] and 
                           latest['tenkan_sen'] < latest['kijun_sen'])
        
        price_above_cloud = latest['close'] > latest['cloud_top']
        price_below_cloud = latest['close'] < latest['cloud_bottom']
        bullish_cloud = latest['senkou_span_a'] > latest['senkou_span_b']
        
        tenkan_kijun_distance = abs(latest['tenkan_sen'] - latest['kijun_sen']) / latest['close'] * 100
        
        return IchimokuSignal(
            tenkan_sen=latest['tenkan_sen'],
            kijun_sen=latest['kijun_sen'],
            senkou_span_a=latest['senkou_span_a'],
            senkou_span_b=latest['senkou_span_b'],
            tk_cross_bullish=tk_cross_bullish,
            tk_cross_bearish=tk_cross_bearish,
            price_above_cloud=price_above_cloud,
            price_below_cloud=price_below_cloud,
            bullish_cloud=bullish_cloud,
            cloud_thickness_pct=latest['cloud_thickness_pct'],
            tenkan_kijun_distance=tenkan_kijun_distance
        )
    
    def calculate_holding_period(self, total_score: int, ichimoku: IchimokuSignal,
                                 adx: float, volatility: float) -> Tuple[HoldingPeriod, Dict]:
        """추천 보유일수 계산"""
        factors = {
            'score': total_score,
            'tk_cross': ichimoku.tk_cross_bullish,
            'above_cloud': ichimoku.price_above_cloud,
            'cloud_thickness': ichimoku.cloud_thickness_pct,
            'adx': adx,
            'volatility': volatility
        }
        
        # 1. 당일 청산 (Fire Ant 스타일)
        if total_score >= 95 and volatility >= 5 and ichimoku.tenkan_kijun_distance >= 3:
            return HoldingPeriod.DAY_TRADE, factors
        
        # 2. 단기 (2-3일)
        if total_score >= 100 and ichimoku.tk_cross_bullish and adx >= 30:
            return HoldingPeriod.SHORT, factors
        
        # 3. 중기 (5-10일)
        if ichimoku.price_above_cloud and adx >= 25 and volatility < 3:
            return HoldingPeriod.MEDIUM, factors
        
        # 4. 장기 (10-20일)
        if ichimoku.price_above_cloud and ichimoku.cloud_thickness_pct >= 5 and adx >= 20:
            return HoldingPeriod.LONG, factors
        
        # 기본: 중기
        return HoldingPeriod.MEDIUM, factors
    
    def get_exit_strategy(self, holding: HoldingPeriod) -> Dict:
        """청산 전략 생성"""
        strategies = {
            HoldingPeriod.DAY_TRADE: {
                'primary': 'time_exit',
                'time_stop': 1,
                'trail_activation': None,
                'notes': '장 마감 전 청산'
            },
            HoldingPeriod.SHORT: {
                'primary': 'TP2',
                'time_stop': 3,
                'trail_activation': 5.0,
                'notes': 'TP2 도달 후 트레일링 스탑'
            },
            HoldingPeriod.MEDIUM: {
                'primary': 'trailing_stop',
                'time_stop': 10,
                'trail_activation': 10.0,
                'notes': '10% 수익 시 트레일링 시작'
            },
            HoldingPeriod.LONG: {
                'primary': 'trailing_stop',
                'time_stop': 20,
                'trail_activation': 15.0,
                'notes': '15% 수익 시 트레일링, 기준선 기반 스탑'
            },
            HoldingPeriod.TREND_FOLLOW: {
                'primary': 'trailing_stop',
                'time_stop': 60,
                'trail_activation': 20.0,
                'notes': 'Kijun-sen 이탈 시 청산'
            }
        }
        return strategies.get(holding, strategies[HoldingPeriod.MEDIUM])


def main():
    """메인 실행 - 전체 종목 스캔"""
    import argparse
    
    parser = argparse.ArgumentParser(description='2604 V8 Unified Scanner')
    parser.add_argument('--date', type=str, default=None, help='스캔 날짜 (YYYY-MM-DD)')
    parser.add_argument('--code', type=str, default=None, help='단일 종목 코드 (테스트용)')
    args = parser.parse_args()
    
    scan_date = args.date if args.date else datetime.now().strftime('%Y-%m-%d')
    
    scanner = Scanner2604V8Unified()
    scanner.connect()
    
    # 단일 종목 테스트 모드
    if args.code:
        print(f"\n📊 단일 종목 테스트: {args.code}")
        df = scanner.fetch_stock_data(args.code, scan_date)
        if df is not None:
            df = scanner.calculate_indicators(df)
            latest = df.iloc[-1]
            ichimoku = scanner.generate_ichimoku_signal(df)
            
            print(f"\n📈 일목균형표 분석")
            print(f"   전환선: {ichimoku.tenkan_sen:,.0f}")
            print(f"   기준선: {ichimoku.kijun_sen:,.0f}")
            print(f"   TK_CROSS: {'✅' if ichimoku.tk_cross_bullish else '❌'}")
            print(f"   점수: {ichimoku.score}/20점")
        scanner.close()
        return
    
    # 전체 종목 스캔
    print("=" * 70)
    print("🔥 2604 V8 Unified Scanner - Full Market Scan")
    print("=" * 70)
    print(f"📅 스캔 날짜: {scan_date}")
    
    # 종목 리스트 로드
    query = f"""
    SELECT DISTINCT code, name 
    FROM price_data 
    WHERE date = '{scan_date}'
    ORDER BY code
    """
    stocks_df = pd.read_sql_query(query, scanner.conn)
    total_stocks = len(stocks_df)
    
    print(f"📊 대상 종목: {total_stocks}개")
    print("=" * 70)
    
    signals = []
    processed = 0
    
    for idx, row in stocks_df.iterrows():
        code = row['code']
        name = row['name']
        
        try:
            df = scanner.fetch_stock_data(code, scan_date)
            if df is None:
                continue
            
            df = scanner.calculate_indicators(df)
            latest = df.iloc[-1]
            
            # 하드 필터
            if not (40 <= latest['rsi'] <= 70):
                continue
            if latest['adx'] < 20:
                continue
            vol_ratio = latest['volume'] / latest['volume_ma20'] if latest['volume_ma20'] > 0 else 0
            if vol_ratio < 1.5:
                continue
            
            # 일목균형표 신호
            ichimoku = scanner.generate_ichimoku_signal(df)
            
            # 점수 계산 (120점 만점)
            scores = {}
            reasons = []
            
            # 거래량 (25점)
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
            scores['volume'] = vol_score
            
            # 기술적 (20점)
            tech_score = 0
            if 40 <= latest['rsi'] <= 60:
                tech_score += 10
                reasons.append(f"RSI 적정 ({latest['rsi']:.1f})")
            if latest['macd_hist'] > 0:
                tech_score += 5
            if latest['close'] > latest['ma5'] > latest['ma20']:
                tech_score += 5
                reasons.append("정배열")
            scores['technical'] = tech_score
            
            # 피볼나치 (20점)
            fib_score = 20
            scores['fibonacci'] = fib_score
            reasons.append("피볼나치 되돌림")
            
            # 모멘텀 (10점)
            mom_score = min(abs(latest['close'] - df.iloc[-20]['close']) / df.iloc[-20]['close'] * 100 * 2, 10)
            scores['momentum'] = int(mom_score)
            
            # 시장맥락 (15점)
            market_score = 15
            scores['market'] = market_score
            
            # 일목균형표 (20점)
            ichi_score = ichimoku.score
            scores['ichimoku'] = ichi_score
            if ichimoku.tk_cross_bullish:
                reasons.append("TK_CROSS 골든")
            if ichimoku.price_above_cloud:
                reasons.append("구름 위")
            
            total_score = sum(scores.values())
            
            # 진입 조건: 80점+ (V7과 동일 - 일본 전략 제외)
            # 일본 전략은 보유일수 계산용으로만 사용
            if total_score < 80:
                continue
            
            # 보유일수 계산
            volatility = latest['atr'] / latest['close'] * 100
            holding, factors = scanner.calculate_holding_period(
                total_score=total_score,
                ichimoku=ichimoku,
                adx=latest['adx'],
                volatility=volatility
            )
            
            # 목표가 계산
            from fibonacci_target_integrated import calculate_scanner_targets
            targets = calculate_scanner_targets(
                entry=latest['close'],
                atr=latest['atr'],
                method='hybrid'
            )
            
            signal = {
                'code': code,
                'name': name,
                'date': scan_date,
                'score': total_score,
                'price': latest['close'],
                'scores': scores,
                'reasons': reasons,
                'ichimoku': {
                    'tenkan_sen': ichimoku.tenkan_sen,
                    'kijun_sen': ichimoku.kijun_sen,
                    'tk_cross': ichimoku.tk_cross_bullish,
                    'above_cloud': ichimoku.price_above_cloud,
                    'bullish_cloud': ichimoku.bullish_cloud,
                    'cloud_thickness_pct': ichimoku.cloud_thickness_pct,
                    'ichi_score': ichi_score
                },
                'holding_strategy': {
                    'period': holding.name,
                    'description': holding.description,
                    'min_days': holding.min_days,
                    'max_days': holding.max_days,
                    'color': holding.color
                },
                'exit_strategy': scanner.get_exit_strategy(holding),
                'targets': targets,
                'metadata': {
                    'volume_ratio': vol_ratio,
                    'rsi': latest['rsi'],
                    'adx': latest['adx'],
                    'atr': latest['atr']
                }
            }
            
            signals.append(signal)
            
        except Exception as e:
            pass
        
        processed += 1
        if processed % 500 == 0:
            print(f"   진행: {processed}/{total_stocks} ({len(signals)}개 신호)")
    
    # 결과 정렬
    signals.sort(key=lambda x: x['score'], reverse=True)
    
    print("\n" + "=" * 70)
    print(f"✅ 스캔 완료: {len(signals)}개 신호 발견")
    print("=" * 70)
    
    # JSON 저장
    if signals:
        json_file = f"reports/2604_v8_unified_{scan_date.replace('-', '')}.json"
        with open(json_file, 'w', encoding='utf-8') as f:
            json.dump(signals, f, ensure_ascii=False, indent=2)
        print(f"✅ JSON 저장: {json_file}")
        
        # 콘솔 출력
        print("\n📊 TOP 신호")
        print("=" * 70)
        for i, s in enumerate(signals[:10], 1):
            print(f"\n{i}. {s['name']} ({s['code']}) - {s['score']}점")
            print(f"   현재가: {s['price']:,.0f}원")
            print(f"   보유전략: {s['holding_strategy']['description']}")
            print(f"   🛑 손절가: {s['targets']['stop_loss']:,.0f}원 ({s['targets']['stop_pct']:+.1f}%)")
            print(f"   🎯 TP2: {s['targets']['tp2']:,.0f}원 ({s['targets']['tp2_pct']:+.1f}%) | 손익비 1:{s['targets']['risk_reward_tp2']:.1f}")
            print(f"   사유: {', '.join(s['reasons'][:3])}")
    
    scanner.close()
    
    print("\n" + "=" * 70)
    print("✅ 2604 V8 전체 스캔 완료!")
    print("=" * 70)


if __name__ == '__main__':
    main()
