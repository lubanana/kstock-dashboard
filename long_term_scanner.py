#!/usr/bin/env python3
"""
장기 고수익 종목 스캐너
- 가치투자 + 성장투자 + 추세 결합
- 3~10년 장기 보유 목적
"""

import sys
sys.path.insert(0, '/root/.openclaw/workspace/strg')

import sqlite3
import json
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from fdr_wrapper import get_price


class LongTermStockScanner:
    """장기투자 종목 스캐너"""
    
    def __init__(self):
        self.db_path = 'data/pivot_strategy.db'
        self.min_market_cap = 100_000_000_000  # 1000억원
        
    def get_financial_data(self, symbol):
        """재무 데이터 조회"""
        # 여기서는 기본 가격 데이터만 사용
        # 실제 구현에서는 DART API 등으로 재무제표 연동 필요
        try:
            end_date = datetime.now()
            start_date = end_date - timedelta(days=365*3)
            
            df = get_price(symbol, 
                          start_date.strftime('%Y-%m-%d'),
                          end_date.strftime('%Y-%m-%d'))
            
            if df is None or len(df) < 252:
                return None
            
            return df
        except:
            return None
    
    def calculate_metrics(self, symbol, df):
        """장기투자 지표 계산"""
        if df is None or len(df) < 252:
            return None
        
        closes = df['Close'].values
        volumes = df['Volume'].values
        highs = df['High'].values
        lows = df['Low'].values
        
        # 현재가
        current_price = closes[-1]
        
        # 이동평균
        ma_20 = np.mean(closes[-20:])
        ma_60 = np.mean(closes[-60:])
        ma_120 = np.mean(closes[-120:])
        ma_200 = np.mean(closes[-200:]) if len(closes) >= 200 else np.mean(closes)
        
        # 추세
        trend_short = current_price > ma_20
        trend_mid = current_price > ma_60
        trend_long = current_price > ma_200 if len(closes) >= 200 else trend_mid
        
        # 52주 최고/최저
        high_52w = np.max(closes[-252:]) if len(closes) >= 252 else np.max(closes)
        low_52w = np.min(closes[-252:]) if len(closes) >= 252 else np.min(closes)
        
        # 52주 최고가 대비 위치
        from_52w_high = ((current_price - high_52w) / high_52w) * 100
        from_52w_low = ((current_price - low_52w) / low_52w) * 100
        
        # 거래량
        avg_volume_20 = np.mean(volumes[-20:])
        avg_volume_60 = np.mean(volumes[-60:])
        volume_trend = avg_volume_20 / avg_volume_60 if avg_volume_60 > 0 else 1
        
        # 변동성 (ATR)
        tr_list = []
        for i in range(1, min(15, len(closes))):
            tr = max(highs[-i] - lows[-i], 
                     abs(highs[-i] - closes[-i-1]),
                     abs(lows[-i] - closes[-i-1]))
            tr_list.append(tr)
        atr_14 = np.mean(tr_list) if tr_list else 0
        
        # 1년 수익률
        returns_1y = ((closes[-1] - closes[-252]) / closes[-252] * 100) if len(closes) >= 252 else 0
        
        return {
            'symbol': symbol,
            'price': current_price,
            'ma_20': ma_20,
            'ma_60': ma_60,
            'ma_120': ma_120,
            'ma_200': ma_200,
            'trend_short': trend_short,
            'trend_mid': trend_mid,
            'trend_long': trend_long,
            'high_52w': high_52w,
            'low_52w': low_52w,
            'from_52w_high': from_52w_high,
            'from_52w_low': from_52w_low,
            'volume_trend': volume_trend,
            'atr_14': atr_14,
            'returns_1y': returns_1y,
        }
    
    def calculate_score(self, metrics):
        """장기투자 매력도 점수 (100점 만점)"""
        if metrics is None:
            return 0, {}
        
        score = 0
        details = {}
        
        # 1. 추세 점수 (30점)
        trend_score = 0
        if metrics['trend_long']:
            trend_score += 15
        if metrics['trend_mid']:
            trend_score += 10
        if metrics['trend_short']:
            trend_score += 5
        score += trend_score
        details['trend'] = trend_score
        
        # 2. 52주 최고가 근접 (20점)
        # -10% 이내 근접 시 고점 돌파 가능성
        if metrics['from_52w_high'] >= -5:
            high_score = 20
        elif metrics['from_52w_high'] >= -10:
            high_score = 15
        elif metrics['from_52w_high'] >= -20:
            high_score = 10
        else:
            high_score = 5
        score += high_score
        details['near_high'] = high_score
        
        # 3. 52주 저점 대비 상승 (15점)
        # 50% 이상 상승 = 추세 확인
        if metrics['from_52w_low'] >= 100:
            low_score = 15
        elif metrics['from_52w_low'] >= 50:
            low_score = 10
        elif metrics['from_52w_low'] >= 30:
            low_score = 7
        else:
            low_score = 3
        score += low_score
        details['from_low'] = low_score
        
        # 4. 거래량 추세 (15점)
        if metrics['volume_trend'] >= 1.5:
            vol_score = 15
        elif metrics['volume_trend'] >= 1.2:
            vol_score = 10
        elif metrics['volume_trend'] >= 1.0:
            vol_score = 7
        else:
            vol_score = 3
        score += vol_score
        details['volume'] = vol_score
        
        # 5. 1년 수익률 (20점)
        if metrics['returns_1y'] >= 50:
            ret_score = 20
        elif metrics['returns_1y'] >= 30:
            ret_score = 15
        elif metrics['returns_1y'] >= 10:
            ret_score = 10
        elif metrics['returns_1y'] >= 0:
            ret_score = 5
        else:
            ret_score = 0
        score += ret_score
        details['returns_1y'] = ret_score
        
        return score, details
    
    def scan_stock(self, symbol):
        """개별 종목 스캔"""
        df = self.get_financial_data(symbol)
        if df is None:
            return None
        
        metrics = self.calculate_metrics(symbol, df)
        if metrics is None:
            return None
        
        score, details = self.calculate_score(metrics)
        
        return {
            'symbol': symbol,
            'score': score,
            'price': metrics['price'],
            'trend': '상승' if metrics['trend_long'] else '하락',
            'from_52w_high': round(metrics['from_52w_high'], 1),
            'from_52w_low': round(metrics['from_52w_low'], 1),
            'returns_1y': round(metrics['returns_1y'], 1),
            'details': details,
            'metrics': metrics
        }
    
    def scan_all(self, limit=50):
        """전체 종목 스캔"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT DISTINCT symbol 
            FROM stock_info 
            ORDER BY RANDOM()
            LIMIT ?
        """, (limit,))
        
        symbols = [row[0] for row in cursor.fetchall()]
        conn.close()
        
        results = []
        print(f"\n📊 장기투자 종목 스캔 시작 ({len(symbols)}개 종목)")
        print("=" * 70)
        
        for i, symbol in enumerate(symbols, 1):
            result = self.scan_stock(symbol)
            if result and result['score'] >= 60:
                results.append(result)
                print(f"{i:3d}. {symbol}: {result['score']}점 (추세: {result['trend']}, 1년: {result['returns_1y']:+.1f}%)")
            elif i % 10 == 0:
                print(f"{i:3d}. 진행 중...")
        
        # 점수 기준 정렬
        results.sort(key=lambda x: x['score'], reverse=True)
        
        return results
    
    def print_report(self, results):
        """리포트 출력"""
        print("\n" + "=" * 70)
        print("📈 장기투자 대상 종목 리포트")
        print("=" * 70)
        
        if not results:
            print("\n⚠️ 조건을 만족하는 종목이 없습니다.")
            return
        
        print(f"\n총 {len(results)}개 종목 선정\n")
        print(f"{'순위':<4} {'종목':<10} {'점수':<6} {'추세':<8} {'52주고점':<10} {'52주저점':<10} {'1년수익':<10}")
        print("-" * 70)
        
        for i, r in enumerate(results[:20], 1):
            grade = '🥇' if r['score'] >= 80 else '🥈' if r['score'] >= 70 else '🥉'
            print(f"{grade} {i:<2} {r['symbol']:<10} {r['score']:<6} {r['trend']:<8} "
                  f"{r['from_52w_high']:+.1f}%<10 {r['from_52w_low']:+.1f}%<10 {r['returns_1y']:+.1f}%<10")
        
        # 등급별 분포
        a_grade = len([r for r in results if r['score'] >= 80])
        b_grade = len([r for r in results if 70 <= r['score'] < 80])
        c_grade = len([r for r in results if 60 <= r['score'] < 70])
        
        print("\n" + "=" * 70)
        print("📊 등급별 분포")
        print("=" * 70)
        print(f"A등급 (80+): {a_grade}개")
        print(f"B등급 (70~79): {b_grade}개")
        print(f"C등급 (60~69): {c_grade}개")


if __name__ == '__main__':
    scanner = LongTermStockScanner()
    results = scanner.scan_all(limit=100)
    scanner.print_report(results)
    
    # 저장
    if results:
        with open('docs/long_term_scan_results.json', 'w', encoding='utf-8') as f:
            json.dump(results, f, ensure_ascii=False, indent=2)
        print("\n✅ 결과 저장: docs/long_term_scan_results.json")
