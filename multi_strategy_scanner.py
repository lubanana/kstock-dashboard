#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Multi-Strategy Stock Scanner
============================
5가지 전략을 종합적으로 활용하는 종목 발굴 스캐너

전략:
1. 당일 거래대금 TOP 20
2. 턴어라운드 (52주/역사적 신고가 돌파)
3. 새로운 모멘텀 (거래량 급증 + 가격 돌파)
4. 거래대금 2000억+ 첫 돌파
5. 200일선 우상향 (장기 추세 확인)
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Tuple
from datetime import datetime, timedelta
from dataclasses import dataclass
from pathlib import Path
import json

from fdr_wrapper import FDRWrapper
from local_db import LocalDB


@dataclass
class StrategySignal:
    """전략 신호 데이터"""
    symbol: str
    name: str
    market: str
    
    # 기본 정보
    current_price: float
    volume: int
    amount: float  # 거래대금
    
    # 전략별 플래그
    strategy_1_top20_amount: bool  # 거래대금 TOP 20
    strategy_2_turnaround: bool    # 턴어라운드
    strategy_3_new_momentum: bool  # 새로운 모멘텀
    strategy_4_amount_breakout: bool  # 2000억+ 첫 돌파
    strategy_5_ma200_up: bool      # 200일선 우상향
    
    # 세부 지표
    amount_rank: int               # 거래대금 순위
    from_52w_high: float           # 52주 고가 대비
    volume_ratio: float            # 거래량 비율
    ma200: float                   # 200일선
    ma200_slope: float             # 200일선 기울기
    
    # 종합 점수
    strategy_count: int            # 충족한 전략 수
    priority_score: float          # 우선순위 점수


class MultiStrategyScanner:
    """다중 전략 스캐너"""
    
    def __init__(self, db_path: str = './data/pivot_strategy.db'):
        self.db = LocalDB(db_path)
        self.fdr = FDRWrapper(db_path)
        self.today = datetime.now().strftime('%Y-%m-%d')
        
    def get_all_stocks(self) -> pd.DataFrame:
        """전체 종목 리스트 로드 (DB에서 직접 로드)"""
        query = "SELECT symbol, name, market FROM stock_info ORDER BY market, symbol"
        df = pd.read_sql_query(query, self.db.conn)
        df.columns = ['symbol', 'name', 'market']  # 컬럼명 통일
        print(f"📊 DB에서 종목 로드: {len(df)}개 (KOSPI {len(df[df['market']=='KOSPI'])}, KOSDAQ {len(df[df['market']=='KOSDAQ'])})")
        return df
    
    def calculate_ma(self, df: pd.DataFrame, period: int) -> pd.Series:
        """이동평균선 계산"""
        return df['close'].rolling(window=period).mean()
    
    def analyze_strategy_1_amount_rank(self, all_data: Dict[str, pd.DataFrame]) -> List[Tuple[str, float, int]]:
        """
        전략 1: 당일 거래대금 TOP 20
        
        Returns:
            [(종목코드, 거래대금, 순위), ...]
        """
        amounts = []
        
        for symbol, df in all_data.items():
            if df.empty or len(df) < 1:
                continue
            
            latest = df.iloc[-1]
            amount = latest['close'] * latest['volume']
            amounts.append((symbol, amount))
        
        # 정렬하여 순위 매기기
        amounts.sort(key=lambda x: x[1], reverse=True)
        
        # TOP 20 반환
        return [(symbol, amount, rank+1) for rank, (symbol, amount) in enumerate(amounts[:20])]
    
    def analyze_strategy_2_turnaround(self, df: pd.DataFrame, symbol: str) -> Tuple[bool, float]:
        """
        전략 2: 턴어라운드 (52주 신고가 또는 역사적 신고가 근접)
        
        Returns:
            (턴어라운드 여부, 52주 고가 대비 비율)
        """
        if len(df) < 252:
            return False, 0
        
        current_price = df['close'].iloc[-1]
        high_52w = df['high'].rolling(window=252).max().iloc[-1]
        
        # 52주 고가 대비 -10% 이내 (신고가 근접)
        from_52w_high = (current_price - high_52w) / high_52w
        
        # 역사적 고가 (전체 기간)
        hist_high = df['high'].max()
        from_hist_high = (current_price - hist_high) / hist_high
        
        # 52주 고가 -10% 이내 또는 역사적 고가 -5% 이내
        is_turnaround = (from_52w_high >= -0.10) or (from_hist_high >= -0.05)
        
        return is_turnaround, from_52w_high
    
    def analyze_strategy_3_new_momentum(self, df: pd.DataFrame) -> Tuple[bool, float]:
        """
        전략 3: 새로운 모멘텀
        - 거래량 20일 평균 대비 200% 이상
        - 주가 20일 고가 돌파 또는 5% 이상 상승
        
        Returns:
            (모멘텀 여부, 거래량 비율)
        """
        if len(df) < 20:
            return False, 0
        
        current = df.iloc[-1]
        prev = df.iloc[-2]
        
        # 거래량 비율
        avg_volume_20 = df['volume'].tail(20).mean()
        volume_ratio = current['volume'] / avg_volume_20 if avg_volume_20 > 0 else 0
        
        # 가격 조건
        high_20 = df['high'].tail(20).max()
        price_change = (current['close'] - prev['close']) / prev['close']
        
        # 조건: 거래량 200%+ AND (20일 고가 돌파 OR 5%+ 상승)
        has_momentum = (volume_ratio >= 2.0) and ((current['close'] >= high_20) or (price_change >= 0.05))
        
        return has_momentum, volume_ratio
    
    def analyze_strategy_4_amount_breakout(self, df: pd.DataFrame, symbol: str) -> Tuple[bool, float]:
        """
        전략 4: 거래대금 2000억+ 첫 돌파
        - 오늘 거래대금 2000억 이상
        - 과거 60일간 2000억 돌파 없었음
        
        Returns:
            (돌파 여부, 거래대금)
        """
        if len(df) < 60:
            return False, 0
        
        latest = df.iloc[-1]
        amount = latest['close'] * latest['volume']
        
        # 오늘 2000억 이상?
        if amount < 2000e8:  # 2000억
            return False, amount
        
        # 과거 60일간 2000억 이상 있었는지 확인
        df['amount'] = df['close'] * df['volume']
        past_60 = df.iloc[-61:-1]  # 오늘 제외 60일
        
        if len(past_60) > 0:
            max_past_amount = past_60['amount'].max()
            # 과거 최고 거래대금이 2000억 미만이면 첫 돌파
            is_first_breakout = max_past_amount < 2000e8
        else:
            is_first_breakout = True
        
        return is_first_breakout, amount
    
    def analyze_strategy_5_ma200_trend(self, df: pd.DataFrame) -> Tuple[bool, float, float]:
        """
        전략 5: 200일선 우상향
        
        Returns:
            (우상향 여부, MA200 값, 기울기)
        """
        if len(df) < 200:
            return False, 0, 0
        
        df['ma200'] = self.calculate_ma(df, 200)
        
        latest = df.iloc[-1]
        ma200 = latest['ma200']
        
        # 200일선 기울기 (20일 전 대비)
        ma200_20days_ago = df['ma200'].iloc[-20]
        slope = (ma200 - ma200_20days_ago) / ma200_20days_ago if ma200_20days_ago > 0 else 0
        
        # 우상향: 기울기 > 0 (1% 이상 상승)
        is_up = slope > 0.01
        
        return is_up, ma200, slope
    
    def scan_all(self, market: str = 'ALL') -> pd.DataFrame:
        """
        전체 전략 실행
        
        Returns:
            결과 DataFrame
        """
        print("🔥 Multi-Strategy Scanner")
        print("=" * 70)
        
        # 종목 리스트 로드
        stocks = self.get_all_stocks()
        if market != 'ALL':
            stocks = stocks[stocks['market'] == market]
        
        print(f"📊 대상 종목: {len(stocks)}개")
        print("📈 데이터 로드 중...\n")
        
        # 모든 종목 데이터 로드
        all_data = {}
        for _, row in stocks.iterrows():
            try:
                df = self.fdr.get_price(row['symbol'], min_days=252)
                if not df.empty and len(df) >= 200:
                    df.columns = [c.lower() for c in df.columns]
                    all_data[row['symbol']] = df
            except:
                continue
        
        print(f"✅ 데이터 로드 완료: {len(all_data)}개 종목\n")
        
        # 전략 1: 거래대금 TOP 20 계산
        print("📊 전략 1: 거래대금 TOP 20 분석 중...")
        top20_amount = self.analyze_strategy_1_amount_rank(all_data)
        top20_symbols = {s[0] for s in top20_amount}
        amount_rank_map = {s[0]: (s[1], s[2]) for s in top20_amount}
        print(f"   TOP 20 계산 완료\n")
        
        # 각 종목별 전략 분석
        print("📊 전체 전략 분석 중...")
        results = []
        
        for idx, (symbol, df) in enumerate(all_data.items(), 1):
            if idx % 100 == 0:
                print(f"   진행: {idx}/{len(all_data)}")
            
            try:
                stock_info = stocks[stocks['symbol'] == symbol].iloc[0]
                
                # 전략별 분석
                is_top20 = symbol in top20_symbols
                amount, rank = amount_rank_map.get(symbol, (0, 999))
                
                is_turnaround, from_52w_high = self.analyze_strategy_2_turnaround(df, symbol)
                has_momentum, volume_ratio = self.analyze_strategy_3_new_momentum(df)
                is_amount_breakout, amount_val = self.analyze_strategy_4_amount_breakout(df, symbol)
                ma200_up, ma200, ma200_slope = self.analyze_strategy_5_ma200_trend(df)
                
                # 종목이 하나 이상의 전략을 충족하는 경우만 기록
                strategy_count = sum([is_top20, is_turnaround, has_momentum, is_amount_breakout, ma200_up])
                
                if strategy_count >= 1:
                    latest = df.iloc[-1]
                    
                    # 우선순위 점수 계산
                    # 전략 1: TOP 20 (5점)
                    # 전략 2: 턴어라운드 (4점)
                    # 전략 3: 모멘텀 (3점)
                    # 전략 4: 거래대금 돌파 (5점)
                    # 전략 5: MA200 우상향 (2점)
                    priority = 0
                    if is_top20: priority += 5
                    if is_turnaround: priority += 4
                    if has_momentum: priority += 3
                    if is_amount_breakout: priority += 5
                    if ma200_up: priority += 2
                    
                    results.append({
                        '종목코드': symbol,
                        '종목명': stock_info['name'],
                        '시장': stock_info['market'],
                        '현재가': latest['close'],
                        '거래대금(억)': amount / 1e8,
                        '충족전략수': strategy_count,
                        '우선순위': priority,
                        '전략1_거래대금TOP20': '✅' if is_top20 else '',
                        '순위': rank if is_top20 else '',
                        '전략2_턴어라운드': '✅' if is_turnaround else '',
                        '52주고가대비': f"{from_52w_high*100:.1f}%",
                        '전략3_모멘텀': '✅' if has_momentum else '',
                        '거래량비율': f"{volume_ratio:.1f}x",
                        '전략4_2000억돌파': '✅' if is_amount_breakout else '',
                        '전략5_MA200우상향': '✅' if ma200_up else '',
                        'MA200기울기': f"{ma200_slope*100:.1f}%"
                    })
                    
            except Exception as e:
                continue
        
        # DataFrame 생성 및 정렬
        df_results = pd.DataFrame(results)
        if not df_results.empty:
            df_results = df_results.sort_values(['우선순위', '충족전략수'], ascending=[False, False])
        
        return df_results
    
    def generate_report(self, df: pd.DataFrame, output_path: str = './reports/multi_strategy_scan.csv'):
        """리포트 생성 및 저장"""
        if df.empty:
            print("⚠️ 결과 없음")
            return
        
        # 저장
        Path(output_path).parent.mkdir(parents=True, exist_ok=True)
        df.to_csv(output_path, index=False, encoding='utf-8-sig')
        
        # 출력
        print("\n" + "=" * 70)
        print("📊 스캔 결과")
        print("=" * 70)
        print(f"총 {len(df)}개 종목 발굴\n")
        
        print("🏆 TOP 20 종목:")
        display_cols = ['종목코드', '종목명', '현재가', '거래대금(억)', '충족전략수', '우선순위']
        print(df.head(20)[display_cols].to_string(index=False))
        
        # 전략별 통계
        print("\n📈 전략별 발굴 종목 수:")
        print(f"   전략1 (거래대금 TOP20): {df['전략1_거래대금TOP20'].value_counts().get('✅', 0)}개")
        print(f"   전략2 (턴어라운드): {df['전략2_턴어라운드'].value_counts().get('✅', 0)}개")
        print(f"   전략3 (모멘텀): {df['전략3_모멘텀'].value_counts().get('✅', 0)}개")
        print(f"   전략4 (2000억돌파): {df['전략4_2000억돌파'].value_counts().get('✅', 0)}개")
        print(f"   전략5 (MA200우상향): {df['전략5_MA200우상향'].value_counts().get('✅', 0)}개")
        
        print(f"\n💾 리포트 저장: {output_path}")


# 실행
if __name__ == "__main__":
    scanner = MultiStrategyScanner()
    results = scanner.scan_all(market='ALL')
    scanner.generate_report(results)
    print("\n✅ 완료!")
