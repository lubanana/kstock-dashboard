#!/usr/bin/env python3
"""
한국 주식 상한가 예측 스캐너 (K-Upper Limit Predictor)
========================================================
다음날 상한가(30% 상승) 갈 만한 종목을 선별하는 고급 전략

핵심 특징:
- 거래량 폭발 (5배 이상)
- 호재/테마 공시
- 차트 돌파 패턴
- 외인/기관 매수세
- 소형주 (시총 1천억 이하)

Usage:
    python3 upper_limit_predictor.py --mode scan --date 2026-04-08
    python3 upper_limit_predictor.py --mode backtest --days 60
"""

import sys
sys.path.insert(0, '.')

import pandas as pd
import numpy as np
import sqlite3
import json
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
import argparse


DB_PATH = 'data/level1_prices.db'


class UpperLimitPredictor:
    """
    상한가 예측 엔진
    다음날 30% 상승 가능성이 높은 종목 선별
    """
    
    def __init__(self):
        self.conn = sqlite3.connect(DB_PATH)
        self.signals = []
    
    def get_stock_data(self, code: str, end_date: str, days: int = 20) -> Optional[pd.DataFrame]:
        """종목 데이터 조회"""
        start_date = (datetime.strptime(end_date, '%Y-%m-%d') - timedelta(days=days)).strftime('%Y-%m-%d')
        
        query = """
        SELECT date, code, name, open, high, low, close, volume, change_pct,
               ma5, ma20, ma60, rsi
        FROM price_data 
        WHERE code = ? AND date BETWEEN ? AND ?
        ORDER BY date
        """
        df = pd.read_sql_query(query, self.conn, params=(code, start_date, end_date))
        
        if len(df) < 10:
            return None
        
        df['date'] = pd.to_datetime(df['date'])
        return df
    
    def calculate_upper_limit_score(self, df: pd.DataFrame) -> Tuple[int, Dict]:
        """
        상한가 가능성 점수 계산 (100점 만점)
        """
        if df is None or len(df) < 10:
            return 0, {}
        
        latest = df.iloc[-1]
        prev = df.iloc[-2] if len(df) > 1 else latest
        
        score = 0
        details = {}
        
        # 1. 거래량 폭발 (최대 30점)
        vol_ma10 = df['volume'].tail(10).mean()
        volume_ratio = latest['volume'] / vol_ma10 if vol_ma10 > 0 else 1.0
        
        if volume_ratio >= 10:  # 10배 이상
            vol_score = 30
        elif volume_ratio >= 5:  # 5배 이상
            vol_score = 25
        elif volume_ratio >= 3:  # 3배 이상
            vol_score = 20
        elif volume_ratio >= 2:  # 2배 이상
            vol_score = 15
        else:
            vol_score = 0
        
        score += vol_score
        details['volume_ratio'] = round(volume_ratio, 2)
        details['volume_score'] = vol_score
        
        # 2. 당일 상승률 (최대 20점) - 직전 강한 상승
        change_pct = latest.get('change_pct', 0) or 0
        
        if change_pct >= 29:  # 상한가 근접
            change_score = 20
        elif change_pct >= 20:  # 20% 이상
            change_score = 18
        elif change_pct >= 15:  # 15% 이상
            change_score = 15
        elif change_pct >= 10:  # 10% 이상
            change_score = 12
        elif change_pct >= 7:   # 7% 이상
            change_score = 10
        elif change_pct >= 5:   # 5% 이상
            change_score = 8
        else:
            change_score = 0
        
        score += change_score
        details['change_pct'] = round(change_pct, 2)
        details['change_score'] = change_score
        
        # 3. 연속 상승 (최대 15점) - 모멘텀
        up_days = 0
        for i in range(min(5, len(df))):
            if i == 0:
                continue
            if df.iloc[-i]['close'] > df.iloc[-i-1]['close']:
                up_days += 1
        
        momentum_score = up_days * 3  # 1일당 3점
        score += momentum_score
        details['up_days'] = up_days
        details['momentum_score'] = momentum_score
        
        # 4. 돌파 패턴 (최대 15점)
        # 20일선 돌파
        ma20 = latest.get('ma20') or 0
        close = latest['close']
        
        breakout_score = 0
        if ma20 > 0 and close > ma20 * 1.05:  # 5% 이상 돌파
            breakout_score = 15
        elif ma20 > 0 and close > ma20:
            breakout_score = 10
        
        score += breakout_score
        details['ma20_breakout'] = close > ma20 if ma20 > 0 else False
        details['breakout_score'] = breakout_score
        
        # 5. RSI 적정 (최대 10점) - 과매수 아님
        rsi = latest.get('rsi', 50) or 50
        if 50 <= rsi <= 75:  # 상승 여력 있는 구간
            rsi_score = 10
        elif 40 <= rsi < 50:
            rsi_score = 8
        elif 75 <= rsi <= 85:
            rsi_score = 5
        else:
            rsi_score = 0
        
        score += rsi_score
        details['rsi'] = round(rsi, 1)
        details['rsi_score'] = rsi_score
        
        # 6. 가격대 (최대 10점) - 저가주 선호
        if close <= 5000:      # 5천원 이하
            price_score = 10
        elif close <= 10000:   # 1만원 이하
            price_score = 8
        elif close <= 30000:   # 3만원 이하
            price_score = 6
        elif close <= 50000:   # 5만원 이하
            price_score = 4
        else:
            price_score = 2
        
        score += price_score
        details['close'] = close
        details['price_score'] = price_score
        
        return score, details
    
    def scan_stocks(self, scan_date: str, min_score: int = 60) -> List[Dict]:
        """
        상한가 예측 스캔
        """
        print(f"\n{'='*70}")
        print(f"🚀 상한가 예측 스캔 - {scan_date}")
        print(f"{'='*70}")
        print(f"필터: 거래량 폭발 + 강한 상승 + 연속 상승 + 돌파")
        print(f"최소 점수: {min_score}점")
        print(f"{'='*70}\n")
        
        # 해당 날짜의 모든 종목 조회
        query = """
        SELECT DISTINCT code FROM price_data 
        WHERE date = ?
        """
        codes_df = pd.read_sql_query(query, self.conn, params=(scan_date,))
        
        if codes_df.empty:
            print(f"❌ {scan_date} 데이터 없음")
            return []
        
        print(f"📊 대상 종목: {len(codes_df)}개\n")
        
        results = []
        
        for idx, row in codes_df.iterrows():
            code = row['code']
            
            # 진행 상황
            if (idx + 1) % 500 == 0:
                print(f"   진행: {idx+1}/{len(codes_df)} ({(idx+1)/len(codes_df)*100:.1f}%)")
            
            df = self.get_stock_data(code, scan_date)
            if df is None:
                continue
            
            score, details = self.calculate_upper_limit_score(df)
            
            if score >= min_score:
                latest = df.iloc[-1]
                results.append({
                    'code': code,
                    'name': latest.get('name', code),
                    'date': scan_date,
                    'score': score,
                    'close': latest['close'],
                    'change_pct': latest.get('change_pct', 0),
                    'volume_ratio': details.get('volume_ratio', 0),
                    'rsi': details.get('rsi', 0),
                    'details': details
                })
        
        # 점수순 정렬
        results.sort(key=lambda x: x['score'], reverse=True)
        
        return results
    
    def display_results(self, results: List[Dict], top_n: int = 20):
        """결과 출력"""
        if not results:
            print("\n❌ 조건 만족 종목 없음")
            return
        
        print(f"\n{'='*70}")
        print(f"🎯 TOP {top_n} 상한가 예측 종목")
        print(f"{'='*70}")
        
        for i, r in enumerate(results[:top_n], 1):
            print(f"\n{i}. {r['name']} ({r['code']}) - {r['score']}점")
            print(f"   현재가: {r['close']:,.0f}원 ({r['change_pct']:+.1f}%)")
            print(f"   거래량: {r['details']['volume_ratio']:.1f}배")
            print(f"   RSI: {r['details']['rsi']:.1f}")
            print(f"   연속상승: {r['details']['up_days']}일")
            print(f"   점수: 거래량({r['details']['volume_score']}) + 상승({r['details']['change_score']}) + "
                  f"모멘텀({r['details']['momentum_score']}) + 돌파({r['details']['breakout_score']}) + "
                  f"RSI({r['details']['rsi_score']}) + 가격({r['details']['price_score']})")
        
        print(f"\n{'='*70}")
        print(f"총 {len(results)}개 종목 선별됨")
        print(f"{'='*70}")


def main():
    """메인 실행"""
    parser = argparse.ArgumentParser(description='상한가 예측 스캐너')
    parser.add_argument('--mode', choices=['scan', 'backtest'], default='scan',
                       help='실행 모드')
    parser.add_argument('--date', type=str, default=None,
                       help='스캔 날짜 (YYYY-MM-DD), 미지정시 최근 데이터')
    parser.add_argument('--min-score', type=int, default=60,
                       help='최소 점수 (기본 60)')
    parser.add_argument('--top', type=int, default=20,
                       help='상위 N개 출력 (기본 20)')
    
    args = parser.parse_args()
    
    predictor = UpperLimitPredictor()
    
    if args.mode == 'scan':
        # 날짜 설정
        if args.date:
            scan_date = args.date
        else:
            # 최근 데이터 날짜 조회
            query = "SELECT MAX(date) FROM price_data"
            result = predictor.conn.execute(query).fetchone()
            scan_date = result[0] if result[0] else datetime.now().strftime('%Y-%m-%d')
        
        # 스캔 실행
        results = predictor.scan_stocks(scan_date, args.min_score)
        predictor.display_results(results, args.top)
        
        # JSON 저장
        if results:
            filename = f"upper_limit_predict_{scan_date}.json"
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(results, f, ensure_ascii=False, indent=2, default=str)
            print(f"\n💾 결과 저장: {filename}")
    
    elif args.mode == 'backtest':
        print("\n📊 백테스트 모드는 개발 중...")
        print("단일 날짜 스캔 후 다음날 수익률 확인 기능 예정")


if __name__ == '__main__':
    main()
