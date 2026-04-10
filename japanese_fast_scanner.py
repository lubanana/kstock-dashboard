#!/usr/bin/env python3
"""
Japanese Pattern Scanner - Performance Optimized
================================================
고성능 버전: 거래대금 상위 종목만 대상
"""

import sqlite3
import pandas as pd
import numpy as np
from datetime import datetime
from typing import List, Dict, Optional
import json
import os


class FastIchimoku:
    """빠른 일목균형표 계산"""
    
    @staticmethod
    def calculate(df: pd.DataFrame) -> Dict:
        """핵심 신호만 계산"""
        if len(df) < 60:
            return {}
        
        # 최근 60일 데이터
        recent = df.tail(60).copy()
        
        # 전환선 (9일)
        high_9 = recent['high'].rolling(9).max()
        low_9 = recent['low'].rolling(9).min()
        recent['tenkan'] = (high_9 + low_9) / 2
        
        # 기준선 (26일)
        high_26 = recent['high'].rolling(26).max()
        low_26 = recent['low'].rolling(26).min()
        recent['kijun'] = (high_26 + low_26) / 2
        
        # 신호 생성
        latest = recent.iloc[-1]
        prev = recent.iloc[-2]
        
        signals = []
        
        # 골든/데드 크로스
        if prev['tenkan'] <= prev['kijun'] and latest['tenkan'] > latest['kijun']:
            signals.append('TK_CROSS_BULLISH')
        elif prev['tenkan'] >= prev['kijun'] and latest['tenkan'] < latest['kijun']:
            signals.append('TK_CROSS_BEARISH')
        
        # 가격 vs 구름 (간략화)
        recent['senkou_a'] = ((recent['tenkan'] + recent['kijun']) / 2).shift(-26)
        recent['senkou_b'] = ((recent['high'].rolling(52).max() + recent['low'].rolling(52).min()) / 2).shift(-26)
        
        latest = recent.iloc[-1]
        kumo_top = max(latest['senkou_a'], latest['senkou_b']) if pd.notna(latest['senkou_a']) else latest['close']
        kumo_bottom = min(latest['senkou_a'], latest['senkou_b']) if pd.notna(latest['senkou_b']) else latest['close']
        
        if latest['close'] > kumo_top:
            signals.append('PRICE_ABOVE_CLOUD')
        elif latest['close'] < kumo_bottom:
            signals.append('PRICE_BELOW_CLOUD')
        
        return {
            'signals': signals,
            'tenkan': latest['tenkan'],
            'kijun': latest['kijun'],
        }


class FastSakata:
    """빠른 사카타 5법"""
    
    @staticmethod
    def detect_triple_bottom(prices: pd.Series, lows: pd.Series, lookback: int = 15) -> bool:
        """삼천 (Triple Bottom) - 단순화 버전"""
        if len(prices) < lookback:
            return False
        
        recent_lows = lows.tail(lookback).values
        
        # 3개 저점 탐색 (간략화)
        min_indices = recent_lows.argsort()[:3]
        if len(min_indices) < 3:
            return False
        
        # 저점들이 유사한지 확인
        lowest_3 = recent_lows[min_indices]
        if len(lowest_3) >= 3:
            diff = np.std(lowest_3) / np.mean(lowest_3)
            return diff < 0.05  # 5% 이내 차이
        
        return False
    
    @staticmethod
    def detect_triple_top(prices: pd.Series, highs: pd.Series, lookback: int = 15) -> bool:
        """삼산 (Triple Top) - 단순화 버전"""
        if len(prices) < lookback:
            return False
        
        recent_highs = highs.tail(lookback).values
        
        # 3개 고점 탐색
        max_indices = recent_highs.argsort()[-3:]
        if len(max_indices) < 3:
            return False
        
        # 고점들이 유사한지 확인
        highest_3 = recent_highs[max_indices]
        if len(highest_3) >= 3:
            diff = np.std(highest_3) / np.mean(highest_3)
            return diff < 0.05
        
        return False


class FastJapaneseScanner:
    """고속 일본 패턴 스캐너"""
    
    def __init__(self, db_path: str = 'data/level1_prices.db'):
        self.db_path = db_path
    
    def get_liquid_stocks(self, date: str, limit: int = 500) -> List[Dict]:
        """거래대금 상위 종목만 선택"""
        conn = sqlite3.connect(self.db_path)
        
        query = """
        SELECT code, name, close, volume, (close * volume) as value
        FROM price_data
        WHERE date = ? AND close >= 2000
        ORDER BY value DESC
        LIMIT ?
        """
        
        df = pd.read_sql(query, conn, params=(date, limit))
        conn.close()
        
        return df.to_dict('records')
    
    def get_stock_data(self, code: str, date: str, days: int = 60) -> pd.DataFrame:
        """종목 데이터 조회"""
        conn = sqlite3.connect(self.db_path)
        
        query = """
        SELECT date, open, high, low, close, volume
        FROM price_data
        WHERE code = ? AND date <= ?
        ORDER BY date DESC
        LIMIT ?
        """
        
        df = pd.read_sql(query, conn, params=(code, date, days))
        conn.close()
        
        return df.sort_values('date').reset_index(drop=True)
    
    def scan_stock(self, stock: Dict, date: str) -> Optional[Dict]:
        """단일 종목 스캔"""
        df = self.get_stock_data(stock['code'], date)
        
        if len(df) < 60:
            return None
        
        signals = []
        
        # 1. 일목균형표
        ichi = FastIchimoku.calculate(df)
        if ichi and 'signals' in ichi:
            signals.extend(ichi['signals'])
        
        # 2. 사카타 패턴
        if FastSakata.detect_triple_bottom(df['close'], df['low']):
            signals.append('TRIPLE_BOTTOM')
        
        if FastSakata.detect_triple_top(df['close'], df['high']):
            signals.append('TRIPLE_TOP')
        
        if not signals:
            return None
        
        return {
            'code': stock['code'],
            'name': stock['name'],
            'date': date,
            'close': stock['close'],
            'value': stock['value'],
            'signals': signals,
            'signal_count': len(signals),
            'ichimoku': ichi,
        }
    
    def scan_date(self, date: str, top_n: int = 500) -> List[Dict]:
        """특정 날짜 스캔"""
        print(f"🔍 {date} - 거래대금 상위 {top_n}종목 스캔")
        
        stocks = self.get_liquid_stocks(date, top_n)
        results = []
        
        for i, stock in enumerate(stocks):
            if i % 100 == 0:
                print(f"  진행: {i}/{len(stocks)}")
            
            result = self.scan_stock(stock, date)
            if result and result['signal_count'] >= 1:
                results.append(result)
        
        print(f"  ✅ {len(results)} 종목 발견")
        return sorted(results, key=lambda x: x['signal_count'], reverse=True)


def main():
    scanner = FastJapaneseScanner()
    
    # 최근 5거래일만 테스트
    test_dates = ['2026-04-01', '2026-04-02', '2026-04-03', '2026-04-07', '2026-04-08']
    
    all_results = []
    for date in test_dates:
        results = scanner.scan_date(date, top_n=500)
        all_results.extend(results)
        
        # 상위 결과 출력
        print(f"\n  📊 상위 결과:")
        for r in results[:5]:
            print(f"    {r['name']}: {r['signals']}")
    
    # 결과 저장
    print(f"\n{'='*70}")
    print(f"📊 총 신호: {len(all_results)}개")
    
    os.makedirs('reports', exist_ok=True)
    with open('reports/japanese_fast_scan_sample.json', 'w', encoding='utf-8') as f:
        json.dump(all_results, f, ensure_ascii=False, indent=2)
    
    print(f"💾 저장: reports/japanese_fast_scan_sample.json")


if __name__ == '__main__':
    main()
