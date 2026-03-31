#!/usr/bin/env python3
"""
실적/모멘텀 탄탄 + 과매도 종목 스캐너 (DART 재무 데이터 연동版)
Quality Oversold Scanner with DART Financial Data

Superpower 미설치 → 직접 SQLite 연동
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import json
import sqlite3
import sys
import warnings
warnings.filterwarnings('ignore')

sys.path.insert(0, '/root/.openclaw/workspace/strg')
from fdr_wrapper import get_price

class DARTQualityOversoldScanner:
    """
    실적/모멘텀 탄탄하지만 현재 과매도인 종목 스캐너
    DART 재무 데이터 활용
    """
    
    def __init__(self):
        self.results = []
        self.dart_conn = None
        self.connect_dart_db()
        
    def connect_dart_db(self):
        """DART DB 연결"""
        try:
            self.dart_conn = sqlite3.connect('/root/.openclaw/workspace/strg/data/dart_financial.db')
        except Exception as e:
            print(f"⚠️ DART DB 연결 실패: {e}")
            self.dart_conn = None
    
    def get_fundamental_data(self, stock_code):
        """DART에서 재무 데이터 조회"""
        if not self.dart_conn:
            return None
        
        try:
            cursor = self.dart_conn.cursor()
            
            # 최신 연간 재무 데이터 조회
            result = cursor.execute('''
                SELECT year, revenue, operating_profit, net_income, 
                       total_assets, total_liabilities, total_equity
                FROM financial_data 
                WHERE stock_code = ? AND reprt_code = '11011'
                ORDER BY year DESC 
                LIMIT 3
            ''', (stock_code,)).fetchall()
            
            if not result or len(result) < 2:
                return None
            
            # 최신 2년 데이터로 계산
            latest = result[0]
            prev = result[1] if len(result) > 1 else result[0]
            
            revenue = latest[1]
            operating_profit = latest[2]
            net_income = latest[3]
            total_assets = latest[4]
            total_liabilities = latest[5]
            total_equity = latest[6]
            
            if total_equity <= 0 or revenue <= 0:
                return None
            
            # 핵심 재무 지표 계산
            roe = (net_income / total_equity) * 100
            debt_ratio = (total_liabilities / total_equity) * 100
            op_margin = (operating_profit / revenue) * 100
            
            # 성장성
            revenue_growth = ((latest[1] - prev[1]) / prev[1] * 100) if prev[1] > 0 else 0
            profit_growth = ((latest[3] - prev[3]) / prev[3] * 100) if prev[3] > 0 else 0
            
            # 퀄리티 점수 계산
            quality_score = 0
            
            # ROE (0-30점)
            if roe >= 20: quality_score += 30
            elif roe >= 15: quality_score += 25
            elif roe >= 10: quality_score += 20
            elif roe >= 5: quality_score += 10
            
            # 부채비율 (0-25점)
            if debt_ratio <= 50: quality_score += 25
            elif debt_ratio <= 100: quality_score += 20
            elif debt_ratio <= 200: quality_score += 15
            elif debt_ratio <= 300: quality_score += 10
            
            # 영업이익률 (0-25점)
            if op_margin >= 20: quality_score += 25
            elif op_margin >= 15: quality_score += 20
            elif op_margin >= 10: quality_score += 15
            elif op_margin >= 5: quality_score += 10
            
            # 성장성 (0-20점)
            if revenue_growth >= 20: quality_score += 10
            elif revenue_growth >= 10: quality_score += 7
            elif revenue_growth >= 0: quality_score += 5
            
            if profit_growth >= 30: quality_score += 10
            elif profit_growth >= 10: quality_score += 7
            elif profit_growth >= 0: quality_score += 5
            
            return {
                'roe': roe,
                'debt_ratio': debt_ratio,
                'op_margin': op_margin,
                'revenue_growth': revenue_growth,
                'profit_growth': profit_growth,
                'quality_score': quality_score,
                'latest_year': latest[0]
            }
            
        except Exception as e:
            return None
    
    def calculate_rsi(self, prices, period=14):
        delta = prices.diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
        rs = gain / loss
        return 100 - (100 / (1 + rs))
    
    def scan_stock(self, symbol, name):
        """개별 종목 스캔"""
        try:
            # 1. DART 재무 데이터 조회
            fundamentals = self.get_fundamental_data(symbol)
            if not fundamentals:
                return None
            
            # 재무 퀄리티 필터 (60점 이상만)
            if fundamentals['quality_score'] < 60:
                return None
            
            # 2. 가격 데이터 조회
            end_date = datetime.now()
            start_date = end_date - timedelta(days=400)
            df = get_price(symbol, start_date.strftime('%Y-%m-%d'), end_date.strftime('%Y-%m-%d'))
            
            if df is None or len(df) < 100:
                return None
            
            latest = df.iloc[-1]
            
            # 3. 기술적 지표 계산
            df['RSI'] = self.calculate_rsi(df['Close'], 14)
            df['EMA20'] = df['Close'].ewm(span=20, adjust=False).mean()
            df['EMA60'] = df['Close'].ewm(span=60, adjust=False).mean()
            df['Volume_MA20'] = df['Volume'].rolling(window=20).mean()
            
            # 볼린저밴드
            df['BB_Middle'] = df['Close'].rolling(window=20).mean()
            df['BB_Std'] = df['Close'].rolling(window=20).std()
            df['BB_Lower'] = df['BB_Middle'] - (df['BB_Std'] * 2)
            df['BB_Position'] = (df['Close'] - df['BB_Lower']) / (df['BB_Middle'] - df['BB_Lower'])
            
            # 52주 최고가
            high_52w = df['High'].tail(252).max()
            
            # 4. 과매도 조건 체크
            rsi_current = df['RSI'].iloc[-1]
            bb_position = df['BB_Position'].iloc[-1]
            
            # 과매도 점수
            oversold_score = 0
            if rsi_current < 30: oversold_score += 40
            elif rsi_current < 40: oversold_score += 30
            elif rsi_current < 50: oversold_score += 15
            
            if bb_position < 0.1: oversold_score += 30
            elif bb_position < 0.2: oversold_score += 20
            elif bb_position < 0.3: oversold_score += 10
            
            # 5. 가격 조건
            price_vs_high = (latest['Close'] - high_52w) / high_52w * 100
            price_vs_ema20 = (latest['Close'] - df['EMA20'].iloc[-1]) / df['EMA20'].iloc[-1] * 100
            volume_ratio = latest['Volume'] / df['Volume_MA20'].iloc[-1]
            
            # 6. 종합 점수 계산
            # 재무 퀄리티 (35%) + 과매도 (30%) + 가격 하락 (25%) + 거래량 (10%)
            price_decline_score = min(abs(price_vs_high), 30) / 30 * 25 if price_vs_high < 0 else 0
            volume_score = min(volume_ratio, 2) / 2 * 10 if volume_ratio > 1 else volume_ratio * 5
            
            total_score = (
                fundamentals['quality_score'] * 0.35 +
                oversold_score * 0.30 +
                price_decline_score +
                volume_score
            )
            
            # 선정 조건
            is_selected = (
                fundamentals['quality_score'] >= 60 and  # 재무 우수
                oversold_score >= 40 and  # 과매도 상태
                price_vs_high <= -10 and  # 52주 고점 대비 10% 이상 하락
                latest['Close'] >= 1000   # 주가 1,000원 이상
            )
            
            if is_selected:
                return {
                    'symbol': symbol,
                    'name': name,
                    'price': latest['Close'],
                    'rsi': rsi_current,
                    'bb_position': bb_position,
                    'vs_52w_high': price_vs_high,
                    'vs_ema20': price_vs_ema20,
                    'volume_ratio': volume_ratio,
                    # 재무 데이터
                    'roe': fundamentals['roe'],
                    'debt_ratio': fundamentals['debt_ratio'],
                    'op_margin': fundamentals['op_margin'],
                    'revenue_growth': fundamentals['revenue_growth'],
                    'profit_growth': fundamentals['profit_growth'],
                    'quality_score': fundamentals['quality_score'],
                    'latest_year': fundamentals['latest_year'],
                    # 종합
                    'oversold_score': oversold_score,
                    'total_score': total_score,
                    'signal': 'STRONG_BUY' if total_score >= 70 else 'BUY'
                }
            
            return None
            
        except Exception as e:
            return None
    
    def run(self, stocks):
        """전체 종목 스캔"""
        print("="*70)
        print("📊 실적/모멘텀 탄탄 + 과매도 종목 스캐너 (DART版)")
        print("="*70)
        print(f"대상: {len(stocks)}개 종목")
        print("\n선정 기준:")
        print("  • 재무퀄리티 60점+ (ROE, 부채비율, 영업익률, 성장성)")
        print("  • RSI < 40, BB 하단 근접")
        print("  • 52주 최고가 대비 -10% 이상 하락")
        print()
        
        results = []
        for i, (code, name) in enumerate(stocks, 1):
            if i % 50 == 0:
                print(f"  [{i}/{len(stocks)}] 스캔 중...", end='\r')
            
            result = self.scan_stock(code, name)
            if result:
                results.append(result)
                print(f"  ✓ {code} ({name}) - 재무:{result['quality_score']:.0f}, 총점:{result['total_score']:.1f}")
        
        print(f"\n\n✅ 선정 완료: {len(results)}개 종목")
        return sorted(results, key=lambda x: x['total_score'], reverse=True)
    
    def __del__(self):
        """소멸자 - DB 연결 종료"""
        if self.dart_conn:
            self.dart_conn.close()


def main():
    scanner = DARTQualityOversoldScanner()
    
    # 대표 종목
    stocks = [
        ('005930', '삼성전자'), ('000660', 'SK하이닉스'), ('005380', '현대차'),
        ('035420', 'NAVER'), ('035720', '카카오'), ('051910', 'LG화학'),
        ('006400', '삼성SDI'), ('028260', '삼성물산'), ('068270', '셀트리온'),
        ('207940', '삼성바이오'), ('012330', '현대모비스'), ('005490', 'POSCO홀딩스'),
        ('105560', 'KB금융'), ('055550', '신한지주'), ('032830', '삼성생명'),
        ('009150', '삼성전기'), ('003670', '포스코퓨처엤'), ('086790', '하나금융'),
        ('033780', 'KT&G'), ('000270', '기아'), ('138040', '메리츠금융'),
        ('066570', 'LG전자'), ('051900', 'LG생활건강'), ('004020', '현대제철'),
        ('010130', '고려아연'), ('096770', 'SK이노베이션'), ('097950', 'CJ제일제당'),
        ('024110', '기업은행'), ('316140', '우리금융지주'), ('018260', '삼성에스디에스'),
    ]
    
    results = scanner.run(stocks)
    
    # 결과 출력
    if results:
        print("\n" + "="*70)
        print("📈 선정 종목 TOP")
        print("="*70)
        print(f"{'순위':<4} {'종목':<8} {'이름':<12} {'현재가':<10} {'ROE':<6} {'52주대비':<10} {'재무점수':<8} {'총점':<6} {'신호'}")
        print("-"*70)
        for i, r in enumerate(results[:10], 1):
            print(f"{i:<4} {r['symbol']:<8} {r['name']:<12} {r['price']:>8,.0f} {r['roe']:>5.1f}% {r['vs_52w_high']:>8.1f}% {r['quality_score']:>7.0f} {r['total_score']:>5.1f} {r['signal']}")
        
        # 상세 재무 정보 출력
        print("\n" + "="*70)
        print("📊 상세 재무 정보")
        print("="*70)
        for i, r in enumerate(results[:5], 1):
            print(f"\n{i}. {r['symbol']} ({r['name']}) - {r['latest_year']}년 기준")
            print(f"   재무점수: {r['quality_score']:.0f}/100")
            print(f"   • ROE: {r['roe']:.1f}% | 부채비율: {r['debt_ratio']:.1f}% | 영업익률: {r['op_margin']:.1f}%")
            print(f"   • 매출성장: {r['revenue_growth']:.1f}% | 순이익성장: {r['profit_growth']:.1f}%")
    
    # 저장
    output_file = f'/root/.openclaw/workspace/strg/docs/dart_quality_oversold_{datetime.now().strftime("%Y%m%d")}.json'
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    
    print(f"\n📄 결과 저장: {output_file}")


if __name__ == '__main__':
    main()
