#!/usr/bin/env python3
"""
Technical Analysis Agent
기술적 분석 에이전트 - 가격, 모멘텀, 볼린저 밴드, 거래량 분석
"""

import yfinance as yf
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Tuple
import json
import sys


class TechnicalAnalysisAgent:
    """기술적 분석 에이전트"""
    
    def __init__(self, symbol: str, name: str = ""):
        self.symbol = symbol
        self.name = name or symbol
        self.data = None
        self.scores = {}
        self.signals = []
        self.risks = []
    
    def fetch_data(self, period: str = "6mo") -> bool:
        """주가 데이터 수집"""
        try:
            ticker = yf.Ticker(self.symbol)
            self.data = ticker.history(period=period)
            
            if self.data.empty:
                return False
            
            # 컬럼명 정리
            self.data.columns = ['Open', 'High', 'Low', 'Close', 'Volume', 'Dividends', 'Stock Splits']
            self.data = self.data.drop(['Dividends', 'Stock Splits'], axis=1, errors='ignore')
            
            return True
        except Exception as e:
            print(f"Error fetching data: {e}")
            return False
    
    def calculate_indicators(self):
        """기술적 지표 계산"""
        df = self.data.copy()
        
        # 이동평균선
        df['MA5'] = df['Close'].rolling(5).mean()
        df['MA20'] = df['Close'].rolling(20).mean()
        df['MA60'] = df['Close'].rolling(60).mean()
        
        # RSI
        delta = df['Close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
        rs = gain / loss
        df['RSI'] = 100 - (100 / (1 + rs))
        
        # MACD
        exp1 = df['Close'].ewm(span=12).mean()
        exp2 = df['Close'].ewm(span=26).mean()
        df['MACD'] = exp1 - exp2
        df['MACD_Signal'] = df['MACD'].ewm(span=9).mean()
        df['MACD_Hist'] = df['MACD'] - df['MACD_Signal']
        
        # 볼린저 밴드
        df['BB_Middle'] = df['Close'].rolling(20).mean()
        bb_std = df['Close'].rolling(20).std()
        df['BB_Upper'] = df['BB_Middle'] + (bb_std * 2)
        df['BB_Lower'] = df['BB_Middle'] - (bb_std * 2)
        df['BB_Width'] = (df['BB_Upper'] - df['BB_Lower']) / df['BB_Middle']
        df['BB_Position'] = (df['Close'] - df['BB_Lower']) / (df['BB_Upper'] - df['BB_Lower'])
        
        # 거래량
        df['Volume_MA20'] = df['Volume'].rolling(20).mean()
        df['Volume_Ratio'] = df['Volume'] / df['Volume_MA20']
        
        # OBV
        df['OBV'] = (np.sign(df['Close'].diff()) * df['Volume']).cumsum()
        
        self.data = df
    
    def analyze_price_trend(self) -> Tuple[int, List[str], List[str]]:
        """
        가격 추세 분석 (0-25점)
        - 이동평균선 배열
        - 현재가 vs 이동평균선 위치
        """
        score = 0
        signals = []
        risks = []
        
        df = self.data.dropna()
        if len(df) < 60:
            return 12, ["데이터 부족"], ["충분한 거래일 데이터 없음"]
        
        latest = df.iloc[-1]
        
        # 1. 이동평균선 배열 (0-10점)
        ma_aligned = latest['MA5'] > latest['MA20'] > latest['MA60']
        ma_golden = latest['MA5'] > latest['MA20'] and df.iloc[-2]['MA5'] <= df.iloc[-2]['MA20']
        
        if ma_aligned:
            score += 10
            signals.append("정배열 (5>20>60)")
        elif latest['MA5'] > latest['MA20']:
            score += 6
            signals.append("단기 정배열 (5>20)")
        elif latest['MA5'] < latest['MA20'] < latest['MA60']:
            score += 2
            risks.append("역배열 (5<20<60)")
        else:
            risks.append("이동평균선 혼조")
        
        if ma_golden:
            score += 3
            signals.append("골든크로스 발생")
        
        # 2. 현재가 vs 이동평균선 (0-8점)
        price = latest['Close']
        if price > latest['MA5']:
            score += 3
            signals.append("현재가 > 5일선")
        if price > latest['MA20']:
            score += 3
            signals.append("현재가 > 20일선")
        if price > latest['MA60']:
            score += 2
            signals.append("현재가 > 60일선")
        
        if price < latest['MA60']:
            risks.append("현재가 60일선 아래")
        
        # 3. 추세 강도 (0-7점)
        ma20_slope = (latest['MA20'] - df.iloc[-5]['MA20']) / latest['MA20'] * 100
        if ma20_slope > 2:
            score += 7
            signals.append(f"강한 상승추세 ({ma20_slope:.1f}%)")
        elif ma20_slope > 0.5:
            score += 4
            signals.append(f"상승추세 ({ma20_slope:.1f}%)")
        elif ma20_slope > -0.5:
            score += 2
            signals.append("횡보")
        else:
            risks.append(f"하락추세 ({ma20_slope:.1f}%)")
        
        return min(score, 25), signals, risks
    
    def analyze_momentum(self) -> Tuple[int, List[str], List[str]]:
        """
        모멘텀 분석 (0-25점)
        - RSI
        - MACD
        - 스토캐스틱
        """
        score = 0
        signals = []
        risks = []
        
        df = self.data.dropna()
        if len(df) < 26:
            return 12, ["데이터 부족"], ["충분한 거래일 데이터 없음"]
        
        latest = df.iloc[-1]
        prev = df.iloc[-2]
        
        # 1. RSI (0-8점)
        rsi = latest['RSI']
        if 50 < rsi < 70:
            score += 8
            signals.append(f"RSI 양호 ({rsi:.1f})")
        elif rsi >= 70:
            score += 4
            signals.append(f"RSI 과매수 ({rsi:.1f})")
            risks.append("RSI 과매수 구간")
        elif rsi > 30:
            score += 4
            signals.append(f"RSI 회복중 ({rsi:.1f})")
        else:
            risks.append(f"RSI 과매도 ({rsi:.1f})")
        
        # 2. MACD (0-10점)
        macd_bull = latest['MACD'] > latest['MACD_Signal']
        macd_cross = macd_bull and prev['MACD'] <= prev['MACD_Signal']
        macd_positive = latest['MACD'] > 0
        
        if macd_cross:
            score += 10
            signals.append("MACD 골든크로스")
        elif macd_bull and macd_positive:
            score += 8
            signals.append("MACD 상승세")
        elif macd_bull:
            score += 5
            signals.append("MACD 매수신호")
        elif macd_positive:
            score += 3
            signals.append("MACD 0선 위")
        else:
            risks.append("MACD 약세")
        
        # 3. MACD 히스토그램 (0-7점)
        hist_growing = latest['MACD_Hist'] > prev['MACD_Hist']
        if hist_growing and latest['MACD_Hist'] > 0:
            score += 7
            signals.append("MACD 모멘텀 강화")
        elif hist_growing:
            score += 4
            signals.append("MACD 모멘텀 개선")
        elif latest['MACD_Hist'] > 0:
            score += 3
            signals.append("MACD 양수")
        
        return min(score, 25), signals, risks
    
    def analyze_bollinger(self) -> Tuple[int, List[str], List[str]]:
        """
        볼린저 밴드 분석 (0-25점)
        - 밴드 위치 (%B)
        - 밴드폭 (squeeze 여부)
        - 밴드 돌파 방향
        """
        score = 0
        signals = []
        risks = []
        
        df = self.data.dropna()
        if len(df) < 20:
            return 12, ["데이터 부족"], ["충분한 거래일 데이터 없음"]
        
        latest = df.iloc[-1]
        prev = df.iloc[-2]
        
        bb_pos = latest['BB_Position']
        bb_width = latest['BB_Width']
        avg_width = df['BB_Width'].mean()
        
        # 1. 밴드 위치 (0-10점)
        if 0.4 <= bb_pos <= 0.6:
            score += 10
            signals.append(f"중립구간 (%B: {bb_pos:.2f})")
        elif 0.2 <= bb_pos < 0.4:
            score += 8
            signals.append(f"하단접근 (%B: {bb_pos:.2f})")
        elif 0.6 < bb_pos <= 0.8:
            score += 7
            signals.append(f"상단접근 (%B: {bb_pos:.2f})")
        elif bb_pos > 0.8:
            score += 4
            signals.append(f"상단돌파 (%B: {bb_pos:.2f})")
            risks.append("상단 밴드 돌파")
        else:
            score += 3
            signals.append(f"하단아래 (%B: {bb_pos:.2f})")
            risks.append("하단 밴드 이탈")
        
        # 2. 밴드폭 (squeeze) (0-8점)
        is_squeeze = bb_width < avg_width * 0.6
        was_squeeze = prev['BB_Width'] < avg_width * 0.6
        
        if is_squeeze and not was_squeeze:
            score += 8
            signals.append("볼린저 스퀴즈 진입 (폭발예고)")
        elif is_squeeze:
            score += 6
            signals.append("볼린저 스퀴즈 지속")
        elif bb_width > avg_width * 1.5:
            score += 4
            signals.append("밴드 확장중")
        else:
            score += 5
            signals.append("정상 밴드폭")
        
        # 3. 밴드 방향 (0-7점)
        bb_trend = latest['BB_Middle'] > prev['BB_Middle']
        if bb_trend and bb_pos > 0.5:
            score += 7
            signals.append("상승밴드 + 상단")
        elif bb_trend:
            score += 5
            signals.append("상승밴드")
        elif bb_pos > 0.5:
            score += 3
            signals.append("하락밴드 + 상단")
        else:
            risks.append("하락밴드 + 하단")
        
        return min(score, 25), signals, risks
    
    def analyze_volume(self) -> Tuple[int, List[str], List[str]]:
        """
        거래량 분석 (0-25점)
        - 평균 대비 거래량 비율
        - 거래량 추세
        - OBV 방향
        """
        score = 0
        signals = []
        risks = []
        
        df = self.data.dropna()
        if len(df) < 20:
            return 12, ["데이터 부족"], ["충분한 거래일 데이터 없음"]
        
        latest = df.iloc[-1]
        recent = df.tail(5)
        
        vol_ratio = latest['Volume_Ratio']
        
        # 1. 거래량 비율 (0-10점)
        if vol_ratio >= 2.0:
            score += 10
            signals.append(f"거래량 폭발 ({vol_ratio:.1f}x)")
        elif vol_ratio >= 1.5:
            score += 8
            signals.append(f"거래량 증가 ({vol_ratio:.1f}x)")
        elif vol_ratio >= 1.0:
            score += 6
            signals.append(f"평균 이상 ({vol_ratio:.1f}x)")
        elif vol_ratio >= 0.7:
            score += 3
            signals.append(f"평균 미만 ({vol_ratio:.1f}x)")
        else:
            risks.append(f"거래량 부진 ({vol_ratio:.1f}x)")
        
        # 2. 거래량 추세 (0-8점)
        vol_trend = recent['Volume'].mean() / df['Volume'].tail(20).mean()
        if vol_trend > 1.3:
            score += 8
            signals.append("거래량 증가추세")
        elif vol_trend > 1.1:
            score += 5
            signals.append("거래량 양호")
        elif vol_trend > 0.9:
            score += 3
            signals.append("거래량 유지")
        else:
            risks.append("거래량 감소추세")
        
        # 3. OBV (0-7점)
        obv_trend = latest['OBV'] > df.iloc[-5]['OBV']
        price_trend = latest['Close'] > df.iloc[-5]['Close']
        
        if obv_trend and price_trend:
            score += 7
            signals.append("OBV + 가격 동반상승")
        elif obv_trend:
            score += 5
            signals.append("OBV 상승 (가격선행)")
        elif price_trend:
            score += 3
            signals.append("가격상승 (OBV 미확인)")
            risks.append("OBV 다이버전스 의심")
        else:
            risks.append("OBV 하락")
        
        return min(score, 25), signals, risks
    
    def analyze(self) -> Dict:
        """전체 기술적 분석 실행"""
        print(f"\n{'='*60}")
        print(f"🔧 Technical Analysis Agent")
        print(f"   Target: {self.name} ({self.symbol})")
        print('='*60)
        
        # 데이터 수집
        if not self.fetch_data():
            return {
                'error': 'Failed to fetch data',
                'symbol': self.symbol,
                'name': self.name
            }
        
        print(f"   📊 Data fetched: {len(self.data)} days")
        
        # 지표 계산
        self.calculate_indicators()
        print(f"   📈 Indicators calculated")
        
        # 각 영역 분석
        print(f"\n   Analyzing...")
        
        price_score, price_signals, price_risks = self.analyze_price_trend()
        print(f"   ✅ Price Trend: {price_score}/25")
        
        momentum_score, momentum_signals, momentum_risks = self.analyze_momentum()
        print(f"   ✅ Momentum: {momentum_score}/25")
        
        bollinger_score, bollinger_signals, bollinger_risks = self.analyze_bollinger()
        print(f"   ✅ Bollinger: {bollinger_score}/25")
        
        volume_score, volume_signals, volume_risks = self.analyze_volume()
        print(f"   ✅ Volume: {volume_score}/25")
        
        # 종합 점수
        total_score = price_score + momentum_score + bollinger_score + volume_score
        
        # 모든 신호와 리스크 합치기
        all_signals = price_signals + momentum_signals + bollinger_signals + volume_signals
        all_risks = price_risks + momentum_risks + bollinger_risks + volume_risks
        
        # 추천 결정
        if total_score >= 70:
            recommendation = "BUY"
        elif total_score >= 50:
            recommendation = "HOLD"
        else:
            recommendation = "SELL"
        
        # 결과 구성
        result = {
            'agent_id': 'TECH_001',
            'agent_name': 'Technical Analyst',
            'symbol': self.symbol,
            'name': self.name,
            'analysis_date': datetime.now().isoformat(),
            'total_score': total_score,
            'breakdown': {
                'price_trend': price_score,
                'momentum': momentum_score,
                'bollinger': bollinger_score,
                'volume': volume_score
            },
            'key_signals': all_signals[:5],  # 상위 5개
            'risk_flags': all_risks[:3],     # 상위 3개
            'recommendation': recommendation,
            'current_price': float(self.data['Close'].iloc[-1]),
            'current_indicators': {
                'rsi': float(self.data['RSI'].iloc[-1]),
                'macd': float(self.data['MACD'].iloc[-1]),
                'bb_position': float(self.data['BB_Position'].iloc[-1]),
                'volume_ratio': float(self.data['Volume_Ratio'].iloc[-1])
            }
        }
        
        # 출력
        print(f"\n{'='*60}")
        print(f"📊 ANALYSIS COMPLETE")
        print('='*60)
        print(f"   Total Score: {total_score}/100")
        print(f"   Recommendation: {recommendation}")
        print(f"   Key Signals: {', '.join(all_signals[:3])}")
        if all_risks:
            print(f"   ⚠️  Risks: {', '.join(all_risks[:2])}")
        print('='*60)
        
        return result


def main():
    """메인 함수"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Technical Analysis Agent')
    parser.add_argument('--symbol', required=True, help='Stock symbol (e.g., 005930.KS)')
    parser.add_argument('--name', help='Stock name')
    parser.add_argument('--output', help='Output JSON file')
    
    args = parser.parse_args()
    
    # 분석 실행
    agent = TechnicalAnalysisAgent(args.symbol, args.name or args.symbol)
    result = agent.analyze()
    
    # JSON 출력
    if args.output:
        with open(args.output, 'w', encoding='utf-8') as f:
            json.dump(result, f, indent=2, ensure_ascii=False)
        print(f"\n💾 Result saved: {args.output}")
    else:
        print("\n📋 JSON Output:")
        print(json.dumps(result, indent=2, ensure_ascii=False))


if __name__ == '__main__':
    main()
