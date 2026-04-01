#!/usr/bin/env python3
"""
단기 급등 스캐너 백테스트
기간: 과거 6개월 데이터로 검증
"""

import sys
sys.path.insert(0, '/root/.openclaw/workspace/strg')

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import sqlite3
from fdr_wrapper import get_price
import json


class ShortTermMomentumBacktest:
    """단기 급등 스캐너 백테스트"""
    
    def __init__(self):
        self.price_conn = sqlite3.connect('/root/.openclaw/workspace/strg/data/pivot_strategy.db')
        self.results = []
        
    def calculate_indicators_for_date(self, df, target_idx):
        """특정 날짜의 기술적 지표 계산"""
        if df is None or len(df) < 30 or target_idx < 20:
            return None
            
        # target_idx까지의 데이터만 사용 (과거 데이터만)
        hist_df = df.iloc[:target_idx+1]
        latest = hist_df.iloc[-1]
        
        indicators = {}
        
        # 1. RSI (14일)
        delta = hist_df['Close'].diff()
        gain = delta.where(delta > 0, 0).rolling(14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
        rs = gain / loss
        rsi = 100 - (100 / (1 + rs))
        indicators['rsi'] = rsi.iloc[-1]
        indicators['rsi_prev'] = rsi.iloc[-2] if len(rsi) > 1 else None
        
        # 2. 볼린저 밴드
        sma20 = hist_df['Close'].rolling(20).mean()
        std20 = hist_df['Close'].rolling(20).std()
        bb_upper = sma20 + 2 * std20
        bb_lower = sma20 - 2 * std20
        indicators['bb_position'] = (latest['Close'] - bb_lower.iloc[-1]) / (bb_upper.iloc[-1] - bb_lower.iloc[-1])
        
        # 3. 거래량
        vol_sma20 = hist_df['Volume'].rolling(20).mean()
        indicators['volume_ratio'] = latest['Volume'] / vol_sma20.iloc[-1] if vol_sma20.iloc[-1] > 0 else 1
        
        # 4. 이평선
        indicators['ema5'] = hist_df['Close'].ewm(span=5).mean().iloc[-1]
        indicators['ema10'] = hist_df['Close'].ewm(span=10).mean().iloc[-1]
        indicators['ema20'] = hist_df['Close'].ewm(span=20).mean().iloc[-1]
        
        # 5. 캔들스틱
        prev = hist_df.iloc[-2]
        body = abs(latest['Close'] - latest['Open'])
        lower_shadow = min(latest['Close'], latest['Open']) - latest['Low']
        upper_shadow = latest['High'] - max(latest['Close'], latest['Open'])
        indicators['is_hammer'] = (lower_shadow > 2 * body) and (upper_shadow < body)
        indicators['is_bullish'] = latest['Close'] > latest['Open']
        
        # 6. 가격 위치
        high_20 = hist_df['High'].tail(20).max()
        low_20 = hist_df['Low'].tail(20).min()
        indicators['price_position'] = (latest['Close'] - low_20) / (high_20 - low_20) if high_20 != low_20 else 0.5
        
        # 7. 가격 데이터
        indicators['price'] = latest['Close']
        indicators['volume'] = latest['Volume']
        indicators['date'] = hist_df.index[-1]
        
        return indicators
    
    def calculate_momentum_score(self, indicators):
        """모멘텀 점수 계산"""
        if indicators is None:
            return 0, []
            
        score = 0
        signals = []
        
        # RSI 과매도
        if indicators['rsi'] < 30:
            score += 20
            signals.append("RSI 과매도")
        elif indicators['rsi'] < 40:
            score += 15
            signals.append("RSI 과열근접")
        
        # RSI 반전
        if indicators['rsi_prev'] and indicators['rsi'] > indicators['rsi_prev']:
            score += 10
            signals.append("RSI 상승 반전")
        
        # BB 하단
        if indicators['bb_position'] < 0.1:
            score += 15
            signals.append("BB 하단 근접")
        elif indicators['bb_position'] < 0.2:
            score += 10
            signals.append("BB 하단 접근")
        
        # 거래량
        if indicators['volume_ratio'] > 3:
            score += 20
            signals.append("거래량 폭발")
        elif indicators['volume_ratio'] > 2:
            score += 15
            signals.append("거래량 급증")
        elif indicators['volume_ratio'] > 1.5:
            score += 10
            signals.append("거래량 증가")
        
        # 캔들패턴
        if indicators['is_hammer']:
            score += 15
            signals.append("핸머 패턴")
        
        if indicators['is_bullish']:
            score += 5
            signals.append("양봉")
        
        # 이평선
        if indicators['ema5'] > indicators['ema10'] > indicators['ema20']:
            score += 10
            signals.append("정배열")
        elif indicators['ema5'] > indicators['ema10']:
            score += 5
            signals.append("단기 정배열")
        
        # 가격 위치
        if indicators['price_position'] < 0.2:
            score += 10
            signals.append("20일 저점 근접")
        elif indicators['price_position'] < 0.3:
            score += 5
            signals.append("20일 하단권")
        
        return min(score, 100), signals
    
    def calculate_future_returns(self, df, entry_idx, days=[1, 3, 5]):
        """미래 수익률 계산"""
        returns = {}
        entry_price = df.iloc[entry_idx]['Close']
        
        for day in days:
            future_idx = entry_idx + day
            if future_idx < len(df):
                future_price = df.iloc[future_idx]['Close']
                returns[f'return_{day}d'] = (future_price - entry_price) / entry_price * 100
                returns[f'high_{day}d'] = df.iloc[entry_idx:future_idx+1]['High'].max()
                returns[f'low_{day}d'] = df.iloc[entry_idx:future_idx+1]['Low'].min()
            else:
                returns[f'return_{day}d'] = None
                
        return returns
    
    def backtest_symbol(self, symbol, start_date='2025-10-01', end_date='2026-03-31', min_score=60):
        """개별 종목 백테스트"""
        try:
            df = get_price(symbol, start_date, end_date)
            if df is None or len(df) < 40:
                return []
            
            trades = []
            
            # 각 거래일마다 스캔
            for i in range(30, len(df) - 5):  # 30일 이후부터, 5일 버퍼
                indicators = self.calculate_indicators_for_date(df, i)
                if indicators is None:
                    continue
                
                # 필터
                if indicators['price'] < 1000:
                    continue
                if indicators['price'] * indicators['volume'] < 1000000000:
                    continue
                
                score, signals = self.calculate_momentum_score(indicators)
                
                if score >= min_score:
                    # 미래 수익률 계산
                    future_returns = self.calculate_future_returns(df, i)
                    
                    if future_returns.get('return_1d') is not None:
                        trades.append({
                            'symbol': symbol,
                            'date': indicators['date'].strftime('%Y-%m-%d'),
                            'entry_price': indicators['price'],
                            'score': score,
                            'signals': signals,
                            'rsi': indicators['rsi'],
                            'volume_ratio': indicators['volume_ratio'],
                            **future_returns
                        })
            
            return trades
            
        except Exception as e:
            return []
    
    def run_backtest(self, sample_size=100, min_score=60):
        """백테스트 실행"""
        print("="*70)
        print("📊 단기 급등 스캐너 백테스트")
        print("="*70)
        print(f"\n기간: 2025-10-01 ~ 2026-03-31 (6개월)")
        print(f"대상: {sample_size}개 종목 샘플")
        print(f"진입 조건: {min_score}점 이상")
        print("\n")
        
        # 샘플 종목 선택
        symbols = [r[0] for r in self.price_conn.execute(
            'SELECT symbol FROM stock_info ORDER BY RANDOM() LIMIT ?', (sample_size,)
        ).fetchall()]
        
        all_trades = []
        
        for i, symbol in enumerate(symbols, 1):
            print(f"[{i}/{len(symbols)}] {symbol} 분석중...", end='\r')
            trades = self.backtest_symbol(symbol, min_score=min_score)
            all_trades.extend(trades)
        
        print(f"\n\n✅ 백테스트 완료: 총 {len(all_trades)}개 거래 신호")
        
        return all_trades
    
    def analyze_results(self, trades):
        """결과 분석"""
        if not trades:
            print("분석할 거래가 없습니다.")
            return
        
        df = pd.DataFrame(trades)
        
        print("\n" + "="*70)
        print("📈 백테스트 결과 분석")
        print("="*70)
        
        # 기본 통계
        print(f"\n📊 전체 거래: {len(df)}건")
        
        # 점수별 분포
        print(f"\n📋 점수별 분포:")
        score_80_plus = len(df[df['score'] >= 80])
        score_70_79 = len(df[(df['score'] >= 70) & (df['score'] < 80)])
        score_60_69 = len(df[(df['score'] >= 60) & (df['score'] < 70)])
        print(f"   80점+: {score_80_plus}건 ({score_80_plus/len(df)*100:.1f}%)")
        print(f"   70-79점: {score_70_79}건 ({score_70_79/len(df)*100:.1f}%)")
        print(f"   60-69점: {score_60_69}건 ({score_60_69/len(df)*100:.1f}%)")
        
        # 1일 후 수익률
        print(f"\n📈 1일 후 수익률:")
        returns_1d = df['return_1d'].dropna()
        win_rate_1d = (returns_1d > 0).mean() * 100
        avg_return_1d = returns_1d.mean()
        max_profit_1d = returns_1d.max()
        max_loss_1d = returns_1d.min()
        
        print(f"   승률: {win_rate_1d:.1f}%")
        print(f"   평균 수익률: {avg_return_1d:+.2f}%")
        print(f"   최대 수익: {max_profit_1d:+.2f}%")
        print(f"   최대 손실: {max_loss_1d:+.2f}%")
        
        # 3일 후 수익률
        print(f"\n📈 3일 후 수익률:")
        returns_3d = df['return_3d'].dropna()
        win_rate_3d = (returns_3d > 0).mean() * 100
        avg_return_3d = returns_3d.mean()
        
        print(f"   승률: {win_rate_3d:.1f}%")
        print(f"   평균 수익률: {avg_return_3d:+.2f}%")
        print(f"   최대 수익: {returns_3d.max():+.2f}%")
        print(f"   최대 손실: {returns_3d.min():+.2f}%")
        
        # 5일 후 수익률
        print(f"\n📈 5일 후 수익률:")
        returns_5d = df['return_5d'].dropna()
        win_rate_5d = (returns_5d > 0).mean() * 100
        avg_return_5d = returns_5d.mean()
        
        print(f"   승률: {win_rate_5d:.1f}%")
        print(f"   평균 수익률: {avg_return_5d:+.2f}%")
        
        # 점수별 성과
        print(f"\n📊 점수별 1일 후 성과:")
        for min_s, max_s in [(80, 100), (70, 80), (60, 70)]:
            subset = df[(df['score'] >= min_s) & (df['score'] < max_s)]
            if len(subset) > 0:
                wr = (subset['return_1d'] > 0).mean() * 100
                avg = subset['return_1d'].mean()
                print(f"   {min_s}-{max_s-1}점: 승률 {wr:.1f}%, 평균 {avg:+.2f}% ({len(subset)}건)")
        
        # TOP 수익 거래
        print(f"\n🏆 TOP 5 수익 거래:")
        top_profits = df.nlargest(5, 'return_1d')[['symbol', 'date', 'score', 'return_1d']]
        for _, row in top_profits.iterrows():
            print(f"   {row['symbol']} ({row['date']}): {row['return_1d']:+.2f}% (점수: {row['score']})")
        
        # 최악 거래
        print(f"\n⚠️ 최악 5 거래:")
        worst = df.nsmallest(5, 'return_1d')[['symbol', 'date', 'score', 'return_1d']]
        for _, row in worst.iterrows():
            print(f"   {row['symbol']} ({row['date']}): {row['return_1d']:+.2f}% (점수: {row['score']})")
        
        return df
    
    def generate_report(self, trades):
        """리포트 생성"""
        df = pd.DataFrame(trades)
        
        report = {
            'backtest_date': datetime.now().strftime('%Y-%m-%d'),
            'period': '2025-10-01 ~ 2026-03-31',
            'total_trades': len(df),
            'win_rate_1d': (df['return_1d'] > 0).mean() * 100 if len(df) > 0 else 0,
            'avg_return_1d': df['return_1d'].mean() if len(df) > 0 else 0,
            'win_rate_3d': (df['return_3d'] > 0).mean() * 100 if len(df) > 0 else 0,
            'avg_return_3d': df['return_3d'].mean() if len(df) > 0 else 0,
            'trades': trades
        }
        
        with open('/root/.openclaw/workspace/strg/docs/momentum_backtest_report.json', 'w', encoding='utf-8') as f:
            json.dump(report, f, ensure_ascii=False, indent=2, default=str)
        
        return report


def main():
    backtest = ShortTermMomentumBacktest()
    
    # 백테스트 실행 (100개 종목 샘플)
    trades = backtest.run_backtest(sample_size=100, min_score=60)
    
    # 결과 분석
    if trades:
        df = backtest.analyze_results(trades)
        
        # 리포트 저장
        report = backtest.generate_report(trades)
        
        print("\n" + "="*70)
        print("💾 리포트 저장 완료")
        print("="*70)
        print("docs/momentum_backtest_report.json")


if __name__ == '__main__':
    main()
