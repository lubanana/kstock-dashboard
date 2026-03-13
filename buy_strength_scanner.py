#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Buy Strength Score Scanner
===========================
추세, 모멘텀, 거래량을 기반으로 한 매수 강도 점수 산출 스캐너

Score Breakdown (100점 만점):
- 추세 점수 (40점):
  * 정배열 (주가 > 20일 EMA > 60일 EMA): +20점
  * 눌림목 (주가가 20일선 대비 0~3% 근접): +20점
- 모멘텀 점수 (30점):
  * RSI(14) 50~70: +15점
  * MACD Histogram 증가: +15점
- 거래량 점수 (30점):
  * 거래량 200% 돌파: +30점
  * 거래량 150% 돌파: +20점
  * 거래량 100% 돌파: +10점

Hard Filters:
- 거래대금 100억 이상
- 주가 1,000원 이상
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from datetime import datetime
import json

from fdr_wrapper import FDRWrapper


@dataclass
class BuyScoreResult:
    """매수 강도 점수 결과"""
    symbol: str
    name: str
    market: str
    current_price: float
    volume: int
    amount: float  # 거래대금
    
    # 세부 점수
    trend_score: int
    momentum_score: int
    volume_score: int
    total_score: int
    
    # 세부 지표
    ema20: float
    ema60: float
    rsi14: float
    macd_hist: float
    macd_hist_prev: float
    volume_ratio: float
    price_vs_ema20: float  # 주가/20일선 비율
    
    # 등급
    grade: str
    
    def to_dict(self) -> Dict:
        return {
            '종목코드': self.symbol,
            '종목명': self.name,
            '시장': self.market,
            '현재가': self.current_price,
            '거래대금(억)': round(self.amount / 1e8, 1),
            '총점': self.total_score,
            '추세점수': self.trend_score,
            '모멘텀점수': self.momentum_score,
            '거래량점수': self.volume_score,
            'RSI': round(self.rsi14, 1),
            '거래량비율': round(self.volume_ratio, 1),
            '추천등급': self.grade
        }


class BuyStrengthScanner:
    """매수 강도 점수 스캐너"""
    
    def __init__(self, 
                 db_path: str = './data/pivot_strategy.db',
                 min_amount: float = 1e9,  # 10억
                 min_price: float = 1000):  # 1,000원
        
        self.fdr = FDRWrapper(db_path)
        self.min_amount = min_amount
        self.min_price = min_price
        
    def calculate_ema(self, series: pd.Series, period: int) -> pd.Series:
        """EMA 계산"""
        return series.ewm(span=period, adjust=False).mean()
    
    def calculate_rsi(self, series: pd.Series, period: int = 14) -> pd.Series:
        """RSI 계산"""
        delta = series.diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
        rs = gain / loss
        return 100 - (100 / (1 + rs))
    
    def calculate_macd(self, series: pd.Series) -> Tuple[pd.Series, pd.Series, pd.Series]:
        """MACD 계산 (MACD, Signal, Histogram)"""
        ema12 = series.ewm(span=12, adjust=False).mean()
        ema26 = series.ewm(span=26, adjust=False).mean()
        macd = ema12 - ema26
        signal = macd.ewm(span=9, adjust=False).mean()
        hist = macd - signal
        return macd, signal, hist
    
    def calculate_trend_score(self, df: pd.DataFrame) -> Tuple[int, Dict]:
        """
        추세 점수 계산 (40점 만점)
        
        Returns:
            (점수, 지표_dict)
        """
        score = 0
        metrics = {}
        
        if len(df) < 60:
            return 0, metrics
        
        # EMA 계산
        df = df.copy()
        df['ema20'] = self.calculate_ema(df['close'], 20)
        df['ema60'] = self.calculate_ema(df['close'], 60)
        
        current = df.iloc[-1]
        
        # 1. 정배열 체크 (주가 > 20일 EMA > 60일 EMA): +20점
        if current['close'] > current['ema20'] > current['ema60']:
            score += 20
            metrics['alignment'] = True
        else:
            metrics['alignment'] = False
        
        # 2. 눌림목 체크 (주가가 20일선 대비 0~3% 근접): +20점
        price_vs_ema20 = (current['close'] / current['ema20'] - 1) * 100
        metrics['price_vs_ema20'] = price_vs_ema20
        
        if 0 <= price_vs_ema20 <= 3:
            score += 20
            metrics['pullback'] = True
        else:
            metrics['pullback'] = False
        
        metrics['ema20'] = current['ema20']
        metrics['ema60'] = current['ema60']
        
        return score, metrics
    
    def calculate_momentum_score(self, df: pd.DataFrame) -> Tuple[int, Dict]:
        """
        모멘텀 점수 계산 (30점 만점)
        
        Returns:
            (점수, 지표_dict)
        """
        score = 0
        metrics = {}
        
        if len(df) < 26:
            return 0, metrics
        
        df = df.copy()
        
        # RSI 계산
        df['rsi14'] = self.calculate_rsi(df['close'], 14)
        current_rsi = df['rsi14'].iloc[-1]
        metrics['rsi14'] = current_rsi
        
        # 1. RSI 50~70: +15점
        if 50 <= current_rsi <= 70:
            score += 15
            metrics['rsi_ok'] = True
        else:
            metrics['rsi_ok'] = False
        
        # MACD 계산
        macd, signal, hist = self.calculate_macd(df['close'])
        df['macd_hist'] = hist
        
        current_hist = df['macd_hist'].iloc[-1]
        prev_hist = df['macd_hist'].iloc[-2]
        
        metrics['macd_hist'] = current_hist
        metrics['macd_hist_prev'] = prev_hist
        
        # 2. MACD Histogram 증가: +15점
        if current_hist > prev_hist:
            score += 15
            metrics['macd_increasing'] = True
        else:
            metrics['macd_increasing'] = False
        
        return score, metrics
    
    def calculate_volume_score(self, df: pd.DataFrame) -> Tuple[int, Dict]:
        """
        거래량 점수 계산 (30점 만점)
        
        Returns:
            (점수, 지표_dict)
        """
        score = 0
        metrics = {}
        
        if len(df) < 20:
            return 0, metrics
        
        current_volume = df['volume'].iloc[-1]
        avg_volume_20 = df['volume'].tail(20).mean()
        
        volume_ratio = current_volume / avg_volume_20 if avg_volume_20 > 0 else 0
        metrics['volume_ratio'] = volume_ratio
        metrics['current_volume'] = current_volume
        metrics['avg_volume_20'] = avg_volume_20
        
        # 거래량 점수
        if volume_ratio >= 2.0:  # 200% 돌파
            score = 30
        elif volume_ratio >= 1.5:  # 150% 돌파
            score = 20
        elif volume_ratio >= 1.0:  # 100% 돌파
            score = 10
        else:
            score = 0
        
        return score, metrics
    
    def analyze_symbol(self, symbol: str, name: str = '', market: str = '') -> Optional[BuyScoreResult]:
        """
        단일 종목 분석
        
        Args:
            symbol: 종목코드
            name: 종목명
            market: 시장
        
        Returns:
            BuyScoreResult 또는 None
        """
        try:
            # 데이터 로드
            df = self.fdr.get_price(symbol, min_days=60)
            
            if df.empty or len(df) < 60:
                return None
            
            # 컬럼명 소문자로 변환
            df.columns = [c.lower() for c in df.columns]
            
            current = df.iloc[-1]
            current_price = current['close']
            current_volume = current['volume']
            
            # 하드 필터링
            amount = current_price * current_volume
            
            if amount < self.min_amount:  # 거래대금 10억 미만
                return None
            
            if current_price < self.min_price:  # 주가 1,000원 미만
                return None
            
            # 점수 계산
            trend_score, trend_metrics = self.calculate_trend_score(df)
            momentum_score, momentum_metrics = self.calculate_momentum_score(df)
            volume_score, volume_metrics = self.calculate_volume_score(df)
            
            total_score = trend_score + momentum_score + volume_score
            
            # 등급 산정
            if total_score >= 80:
                grade = 'A'
            elif total_score >= 60:
                grade = 'B'
            elif total_score >= 40:
                grade = 'C'
            else:
                grade = 'D'
            
            return BuyScoreResult(
                symbol=symbol,
                name=name,
                market=market,
                current_price=current_price,
                volume=current_volume,
                amount=amount,
                trend_score=trend_score,
                momentum_score=momentum_score,
                volume_score=volume_score,
                total_score=total_score,
                ema20=trend_metrics.get('ema20', 0),
                ema60=trend_metrics.get('ema60', 0),
                rsi14=momentum_metrics.get('rsi14', 0),
                macd_hist=momentum_metrics.get('macd_hist', 0),
                macd_hist_prev=momentum_metrics.get('macd_hist_prev', 0),
                volume_ratio=volume_metrics.get('volume_ratio', 0),
                price_vs_ema20=trend_metrics.get('price_vs_ema20', 0),
                grade=grade
            )
            
        except Exception as e:
            print(f"❌ {symbol} 분석 오류: {e}")
            return None
    
    def scan_all(self, market: str = 'ALL', top_n: int = 50) -> pd.DataFrame:
        """
        전 종목 스캔
        
        Args:
            market: 'ALL', 'KOSPI', 'KOSDAQ'
            top_n: 상위 N개 반환
        
        Returns:
            결과 DataFrame
        """
        # 종목 리스트 로드
        with open('./data/stock_list.json', 'r') as f:
            stocks_data = json.load(f)
        stocks = pd.DataFrame(stocks_data['stocks'])
        
        if market != 'ALL':
            stocks = stocks[stocks['market'] == market]
        
        print(f"🔍 총 {len(stocks)}개 종목 스캔 시작...")
        print(f"   필터: 거래대금 {self.min_amount/1e8:.0f}억+, 주가 {self.min_price:,}원+")
        print("=" * 70)
        
        results = []
        passed = 0
        skipped = 0
        
        for idx, row in stocks.iterrows():
            if idx % 100 == 0:
                print(f"   진행: {idx}/{len(stocks)} (통과: {passed}, 스킵: {skipped})")
            
            result = self.analyze_symbol(
                row['symbol'], 
                row.get('name', ''), 
                row.get('market', '')
            )
            
            if result:
                results.append(result)
                passed += 1
                if result.total_score >= 80:
                    print(f"   🎯 {result.symbol} ({result.name}): {result.total_score}점")
            else:
                skipped += 1
        
        print("=" * 70)
        print(f"✅ 스캔 완료: {len(results)}개 종목 통과 (전체 {len(stocks)}개 중)")
        
        # DataFrame 생성
        if not results:
            return pd.DataFrame()
        
        df_results = pd.DataFrame([r.to_dict() for r in results])
        df_results = df_results.sort_values('총점', ascending=False)
        
        # A등급 필터링 (80점 이상)
        df_a_grade = df_results[df_results['추천등급'] == 'A']
        
        print(f"\n📊 A등급 종목: {len(df_a_grade)}개")
        
        return df_results.head(top_n)
    
    def visualize_top3(self, df: pd.DataFrame):
        """
        상위 3개 종목 시각화
        
        Args:
            df: 결과 DataFrame
        """
        try:
            import matplotlib.pyplot as plt
            
            top3 = df.head(3)
            
            fig, axes = plt.subplots(3, 1, figsize=(14, 10))
            fig.suptitle('Top 3 Buy Strength Score Stocks', fontsize=16, fontweight='bold')
            
            for idx, (_, row) in enumerate(top3.iterrows()):
                symbol = row['종목코드']
                name = row['종목명']
                
                # 데이터 로드
                df_stock = self.fdr.get_price(symbol, min_days=60)
                df_stock.columns = [c.lower() for c in df_stock.columns]
                
                # 지표 계산
                df_stock['ema20'] = self.calculate_ema(df_stock['close'], 20)
                df_stock['rsi14'] = self.calculate_rsi(df_stock['close'], 14)
                
                ax1 = axes[idx]
                ax2 = ax1.twinx()
                
                # 종가와 EMA20
                ax1.plot(df_stock.index, df_stock['close'], label='Close', color='black', linewidth=1.5)
                ax1.plot(df_stock.index, df_stock['ema20'], label='EMA20', color='blue', linewidth=1, alpha=0.7)
                ax1.set_ylabel('Price', color='black')
                ax1.tick_params(axis='y', labelcolor='black')
                ax1.legend(loc='upper left')
                ax1.grid(True, alpha=0.3)
                
                # RSI
                ax2.plot(df_stock.index, df_stock['rsi14'], label='RSI14', color='red', linewidth=1)
                ax2.axhline(y=70, color='red', linestyle='--', alpha=0.5)
                ax2.axhline(y=50, color='gray', linestyle='--', alpha=0.5)
                ax2.axhline(y=30, color='green', linestyle='--', alpha=0.5)
                ax2.set_ylabel('RSI', color='red')
                ax2.tick_params(axis='y', labelcolor='red')
                ax2.set_ylim(0, 100)
                
                score = row['총점']
                grade = row['추천등급']
                ax1.set_title(f'{idx+1}. {symbol} ({name}) - Score: {score} ({grade} Grade)', 
                            fontweight='bold')
            
            plt.tight_layout()
            plt.savefig('./reports/buy_strength_top3.png', dpi=150, bbox_inches='tight')
            print("\n📊 차트 저장: ./reports/buy_strength_top3.png")
            plt.close()
            
        except Exception as e:
            print(f"⚠️ 차트 생성 오류: {e}")


# 실행 예시
if __name__ == "__main__":
    print("🚀 Buy Strength Score Scanner")
    print("=" * 70)
    
    scanner = BuyStrengthScanner(min_amount=1e9, min_price=1000)
    
    # 전 종목 스캔
    results = scanner.scan_all(market='ALL', top_n=50)
    
    if not results.empty:
        print("\n📈 TOP 20 Results:")
        print(results.head(20).to_string(index=False))
        
        # A등급 종목만 출력
        a_grade = results[results['추천등급'] == 'A']
        if not a_grade.empty:
            print(f"\n🎯 A등급 종목 ({len(a_grade)}개):")
            print(a_grade.to_string(index=False))
        
        # 차트 생성
        scanner.visualize_top3(results)
    else:
        print("⚠️ 결과 없음")
    
    print("\n✅ 완료!")
