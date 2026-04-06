#!/usr/bin/env python3
"""
단기 급등 가능성 스캐너 (Short-term Surge Scanner)
Breakout + Momentum + Volume Burst
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

class ShortTermSurgeScanner:
    """
    단기 급등 가능성이 높은 종목 스캐너
    
    선정 기준:
    1. 돌파 (Breakout)
       - 20일 고점 돌파
       - 볼린저밴드 상단 돌파
       - 저항선 돌파
    
    2. 모멘텀 (Momentum)
       - RSI 50~70 (과매수 아닌 강한 모멘텀)
       - MACD 골든크로스 또는 상승세
       - DMI ADX 25+ (강한 추세)
    
    3. 거래량 폭발 (Volume Burst)
       - 20일 평균 대비 2배+
       - 연속 거래량 증가 (3일)
    
    4. 캔들 패턴
       - 양봉 또는 도지 후 양봉
       - 장대양봉 (몸통이 긴 양봉)
       - 거래대금 10억+
    """
    
    def __init__(self):
        self.results = []
    
    def calculate_rsi(self, prices, period=14):
        delta = prices.diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
        rs = gain / loss
        return 100 - (100 / (1 + rs))
    
    def calculate_macd(self, prices, fast=12, slow=26, signal=9):
        exp1 = prices.ewm(span=fast, adjust=False).mean()
        exp2 = prices.ewm(span=slow, adjust=False).mean()
        macd = exp1 - exp2
        macd_signal = macd.ewm(span=signal, adjust=False).mean()
        macd_hist = macd - macd_signal
        return macd, macd_signal, macd_hist
    
    def calculate_adx(self, df, period=14):
        plus_dm = df['High'].diff()
        minus_dm = df['Low'].diff().abs() * -1
        
        plus_dm[plus_dm < 0] = 0
        minus_dm[minus_dm < 0] = 0
        
        tr = pd.concat([
            df['High'] - df['Low'],
            abs(df['High'] - df['Close'].shift(1)),
            abs(df['Low'] - df['Close'].shift(1))
        ], axis=1).max(axis=1)
        
        atr = tr.rolling(window=period).mean()
        plus_di = 100 * plus_dm.rolling(window=period).mean() / atr
        minus_di = 100 * minus_dm.rolling(window=period).mean() / atr
        dx = 100 * abs(plus_di - minus_di) / (plus_di + minus_di)
        adx = dx.rolling(window=period).mean()
        
        return adx, plus_di, minus_di
    
    def scan_stock(self, symbol, name):
        """개별 종목 스캔"""
        try:
            end_date = datetime.now()
            start_date = end_date - timedelta(days=100)
            df = get_price(symbol, start_date.strftime('%Y-%m-%d'), end_date.strftime('%Y-%m-%d'))
            
            if df is None or len(df) < 50:
                return None
            
            latest = df.iloc[-1]
            prev = df.iloc[-2] if len(df) > 1 else latest
            
            # 지표 계산
            df['RSI'] = self.calculate_rsi(df['Close'])
            df['MACD'], df['MACD_Signal'], df['MACD_Hist'] = self.calculate_macd(df['Close'])
            df['ADX'], df['Plus_DI'], df['Minus_DI'] = self.calculate_adx(df)
            df['EMA5'] = df['Close'].ewm(span=5, adjust=False).mean()
            df['EMA20'] = df['Close'].ewm(span=20, adjust=False).mean()
            df['Volume_MA20'] = df['Volume'].rolling(window=20).mean()
            
            # 20일 고점/저점
            high_20d = df['High'].tail(20).max()
            low_20d = df['Low'].tail(20).min()
            
            # 최근 3일 거래량 추세
            recent_volumes = df['Volume'].tail(3).values
            volume_increasing = recent_volumes[0] < recent_volumes[1] < recent_volumes[2]
            
            # 현재 값들
            rsi = df['RSI'].iloc[-1]
            macd = df['MACD'].iloc[-1]
            macd_signal = df['MACD_Signal'].iloc[-1]
            macd_hist = df['MACD_Hist'].iloc[-1]
            adx = df['ADX'].iloc[-1]
            plus_di = df['Plus_DI'].iloc[-1]
            minus_di = df['Minus_DI'].iloc[-1]
            volume_ratio = latest['Volume'] / df['Volume_MA20'].iloc[-1]
            
            # 돌파 점수
            breakout_score = 0
            if latest['Close'] > high_20d * 0.98: breakout_score += 30  # 20일 고점 근접/돌파
            if latest['Close'] > df['EMA20'].iloc[-1]: breakout_score += 20  # 20일선 위
            if df['EMA5'].iloc[-1] > df['EMA20'].iloc[-1]: breakout_score += 15  # 골든크로스
            
            # 모멘텀 점수
            momentum_score = 0
            if 50 <= rsi < 70: momentum_score += 25  # 건강한 모멘텀
            if macd > macd_signal: momentum_score += 25  # MACD 골든크로스
            if macd_hist > 0 and macd_hist > df['MACD_Hist'].iloc[-2]: momentum_score += 15  # MACD 히스토그램 증가
            if adx > 25: momentum_score += 15  # 강한 추세
            if plus_di > minus_di: momentum_score += 10  # 상승 DI 우세
            
            # 거래량 점수
            volume_score = 0
            if volume_ratio >= 2.0: volume_score += 35
            elif volume_ratio >= 1.5: volume_score += 25
            elif volume_ratio >= 1.2: volume_score += 15
            if volume_increasing: volume_score += 15
            
            # 캔들 점수
            candle_score = 0
            body = abs(latest['Close'] - latest['Open'])
            upper_shadow = latest['High'] - max(latest['Close'], latest['Open'])
            lower_shadow = min(latest['Close'], latest['Open']) - latest['Low']
            
            if latest['Close'] > latest['Open']:  # 양봉
                candle_score += 10
                if body > (latest['High'] - latest['Low']) * 0.6:  # 몸통이 긴 양봉
                    candle_score += 10
            if lower_shadow > body * 0.5:  # 아래꼬리 (지지 확인)
                candle_score += 5
            
            # 거래대금
            trading_value = latest['Close'] * latest['Volume']
            
            # 총점
            total_score = breakout_score + momentum_score + volume_score + candle_score
            
            # 선정 조건 (중요도 순)
            is_selected = (
                volume_ratio >= 1.5 and  # 거래량 필수
                trading_value >= 1000000000 and  # 거래대금 10억+
                latest['Close'] > latest['Open'] and  # 양봉
                rsi < 70 and  # 과매수 아님
                total_score >= 60  # 총점 60+
            )
            
            if is_selected:
                return {
                    'symbol': symbol,
                    'name': name,
                    'price': latest['Close'],
                    'change': (latest['Close'] - prev['Close']) / prev['Close'] * 100,
                    'rsi': rsi,
                    'volume_ratio': volume_ratio,
                    'adx': adx,
                    'vs_20d_high': (latest['Close'] - high_20d) / high_20d * 100,
                    'breakout_score': breakout_score,
                    'momentum_score': momentum_score,
                    'volume_score': volume_score,
                    'candle_score': candle_score,
                    'total_score': total_score,
                    'trading_value': trading_value,
                    'signal': 'STRONG_BUY' if total_score >= 80 else 'BUY'
                }
            
            return None
            
        except Exception as e:
            return None
    
    def run(self, stocks):
        """전체 종목 스캔"""
        print("="*70)
        print("🚀 단기 급등 가능성 스캐너")
        print("="*70)
        print(f"대상: {len(stocks)}개 종목")
        print("\n선정 기준:")
        print("  • 20일 고점 돌파 또는 근접")
        print("  • 거래량 1.5배+ 폭발")
        print("  • RSI 50-70 (건강한 모멘텀)")
        print("  • MACD 골든크로스 또는 상승세")
        print("  • 거래대금 10억+")
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
    scanner = ShortTermSurgeScanner()
    
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
        print(f"{'순위':<4} {'종목':<8} {'이름':<12} {'현재가':<10} {'등락':<8} {'V비율':<6} {'점수':<6} {'신호'}")
        print("-"*70)
        for i, r in enumerate(results[:10], 1):
            print(f"{i:<4} {r['symbol']:<8} {r['name']:<12} {r['price']:>8,.0f} {r['change']:>6.1f}% {r['volume_ratio']:>5.1f}x {r['total_score']:>5.1f} {r['signal']}")
    
    # 저장
    output_file = f'/root/.openclaw/workspace/strg/docs/surge_scan_{datetime.now().strftime("%Y%m%d")}.json'
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    
    print(f"\n📄 결과 저장: {output_file}")


if __name__ == '__main__':
    main()
