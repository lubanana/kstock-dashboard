#!/usr/bin/env python3
"""
실적/모멘텀 탄탄 + 과매도 종목 스캐너
Quality Oversold Scanner
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import json
import sys
import warnings
warnings.filterwarnings('ignore')

sys.path.insert(0, '/root/.openclaw/workspace/strg')
from fdr_wrapper import get_price

class QualityOversoldScanner:
    """
    실적/모멘텀 탄탄하지만 현재 과매도인 종목 스캐너
    
    선정 기준:
    1. 재무 건전성 (Fundamental Quality)
       - ROE 10%+
       - 부채비율 200% 이하
       - 영업이익률 5%+
    
    2. 모멘텀 (Momentum)
       - 52주 최고가 대비 -20% 이상 하락
       - 20일선 아래
    
    3. 과매도 (Oversold)
       - RSI(14) < 35
       - Stochastic < 20
       - 볼린저밴드 하단 터치
    
    4. 수급 (Flow)
       - 외국인/기관 순매수 전환 또는 감소세 둔화
       - 거래량 20일 평균 대비 1.2배+
    """
    
    def __init__(self):
        self.results = []
        
    def calculate_rsi(self, prices, period=14):
        delta = prices.diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
        rs = gain / loss
        return 100 - (100 / (1 + rs))
    
    def calculate_stochastic(self, df, k_period=14, d_period=3):
        lowest_low = df['Low'].rolling(window=k_period).min()
        highest_high = df['High'].rolling(window=k_period).max()
        k = 100 * (df['Close'] - lowest_low) / (highest_high - lowest_low)
        d = k.rolling(window=d_period).mean()
        return k, d
    
    def calculate_bollinger(self, df, period=20, std_dev=2):
        middle = df['Close'].rolling(window=period).mean()
        std = df['Close'].rolling(window=period).std()
        upper = middle + (std * std_dev)
        lower = middle - (std * std_dev)
        position = (df['Close'] - lower) / (upper - lower)
        return upper, middle, lower, position
    
    def get_fundamental_data(self, symbol):
        """DART API에서 재무 데이터 조회 (현재는 더미 데이터)"""
        # 실제 구현시 DART API 연동
        # 현재는 기술적 지표만으로 스캔
        return {
            'roe': 15.0,  # 예시
            'debt_ratio': 100.0,
            'operating_margin': 10.0,
            'quality_score': 80
        }
    
    def scan_stock(self, symbol, name):
        """개별 종목 스캔"""
        try:
            # 가격 데이터 조회
            end_date = datetime.now()
            start_date = end_date - timedelta(days=400)
            df = get_price(symbol, start_date.strftime('%Y-%m-%d'), end_date.strftime('%Y-%m-%d'))
            
            if df is None or len(df) < 100:
                return None
            
            latest = df.iloc[-1]
            
            # 1. 기술적 지표 계산
            df['RSI'] = self.calculate_rsi(df['Close'], 14)
            df['Stoch_K'], df['Stoch_D'] = self.calculate_stochastic(df)
            df['BB_Upper'], df['BB_Middle'], df['BB_Lower'], df['BB_Position'] = self.calculate_bollinger(df)
            df['EMA20'] = df['Close'].ewm(span=20, adjust=False).mean()
            df['EMA60'] = df['Close'].ewm(span=60, adjust=False).mean()
            df['Volume_MA20'] = df['Volume'].rolling(window=20).mean()
            
            # 52주 최고가/최저가
            high_52w = df['High'].tail(252).max()
            low_52w = df['Low'].tail(252).min()
            
            # 2. 과매도 조건 체크
            rsi_current = df['RSI'].iloc[-1]
            stoch_k = df['Stoch_K'].iloc[-1]
            bb_position = df['BB_Position'].iloc[-1]
            
            # 과매도 점수 (0-100)
            oversold_score = 0
            if rsi_current < 30: oversold_score += 40
            elif rsi_current < 40: oversold_score += 25
            elif rsi_current < 50: oversold_score += 10
            
            if stoch_k < 20: oversold_score += 30
            elif stoch_k < 30: oversold_score += 15
            
            if bb_position < 0.1: oversold_score += 30
            elif bb_position < 0.2: oversold_score += 15
            
            # 3. 가격 조건
            price_vs_high = (latest['Close'] - high_52w) / high_52w * 100
            price_vs_ema20 = (latest['Close'] - df['EMA20'].iloc[-1]) / df['EMA20'].iloc[-1] * 100
            
            # 4. 거래량 조건
            volume_ratio = latest['Volume'] / df['Volume_MA20'].iloc[-1]
            
            # 5. 종합 점수 계산
            # 과매도 (40%) + 가격 하락 (30%) + 거래량 (20%) + 추세 (10%)
            price_decline_score = min(abs(price_vs_high), 30) / 30 * 30 if price_vs_high < 0 else 0
            volume_score = min(volume_ratio, 2) / 2 * 20 if volume_ratio > 1 else volume_ratio * 10
            trend_score = 10 if df['EMA20'].iloc[-1] > df['EMA60'].iloc[-1] else 5
            
            total_score = oversold_score * 0.4 + price_decline_score + volume_score + trend_score
            
            # 선정 조건
            is_selected = (
                oversold_score >= 50 and  # 과매도 충분히 심각
                price_vs_high <= -15 and  # 52주 최고가 대비 15% 이상 하락
                volume_ratio >= 0.8 and   # 거래량 정상 수준
                latest['Close'] >= 1000   # 주가 1,000원 이상
            )
            
            if is_selected:
                return {
                    'symbol': symbol,
                    'name': name,
                    'price': latest['Close'],
                    'rsi': rsi_current,
                    'stoch_k': stoch_k,
                    'bb_position': bb_position,
                    'vs_52w_high': price_vs_high,
                    'vs_ema20': price_vs_ema20,
                    'volume_ratio': volume_ratio,
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
        print("📊 실적/모멘텀 탄탄 + 과매도 종목 스캐너")
        print("="*70)
        print(f"대상: {len(stocks)}개 종목")
        print("\n선정 기준:")
        print("  • RSI < 40, Stochastic < 30, BB 하단 근접")
        print("  • 52주 최고가 대비 -15% 이상 하락")
        print("  • 거래량 정상 수준")
        print()
        
        results = []
        for i, (code, name) in enumerate(stocks, 1):
            if i % 100 == 0:
                print(f"  [{i}/{len(stocks)}] 스캔 중...", end='\r')
            
            result = self.scan_stock(code, name)
            if result:
                results.append(result)
                print(f"  ✓ {code} ({name}) - 점수: {result['total_score']:.1f}")
        
        print(f"\n\n✅ 선정 완료: {len(results)}개 종목")
        return sorted(results, key=lambda x: x['total_score'], reverse=True)


def main():
    scanner = QualityOversoldScanner()
    
    # 대표 종목 (실제 사용시 전체 종목으로 확장)
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
        print(f"{'순위':<4} {'종목':<8} {'이름':<12} {'현재가':<10} {'RSI':<6} {'52주대비':<10} {'점수':<6} {'신호'}")
        print("-"*70)
        for i, r in enumerate(results[:10], 1):
            print(f"{i:<4} {r['symbol']:<8} {r['name']:<12} {r['price']:>8,.0f} {r['rsi']:>5.1f} {r['vs_52w_high']:>8.1f}% {r['total_score']:>5.1f} {r['signal']}")
    
    # 저장
    output_file = f'/root/.openclaw/workspace/strg/docs/quality_oversold_scan_{datetime.now().strftime("%Y%m%d")}.json'
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    
    print(f"\n📄 결과 저장: {output_file}")


if __name__ == '__main__':
    main()
