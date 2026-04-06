#!/usr/bin/env python3
"""
KOSDAQ Stock Scanners
KOSDAQ 종목 대상 전략별 스캐너

전략:
1. Livermore: 52주 신고가 돌파
2. O'Neil: 거래량 폭발
3. Minervini: VCP (변동성 축소)
"""

import yfinance as yf
import pandas as pd
import numpy as np
from datetime import datetime
from typing import List, Dict, Optional
import json
import os

BASE_PATH = '/home/programs/kstock_analyzer'


class KOSDAQScanner:
    """KOSDAQ 종목 스캐너"""
    
    def __init__(self):
        # KOSDAQ 대표 종목 (유동성 좋은 종목 위주)
        self.watchlist = [
            '247540.KS',   # 에코프로비엠
            '086520.KS',   # 에코프로
            '196170.KS',   # 알테오젠
            '352820.KS',   # 하이브
            '259960.KS',   # 크래프톤
            '161890.KS',   # 한국콜마
            '214150.KS',   # 클래시스
            '263750.KS',   # 펄어비스
            '293490.KS',   # 카카오게임즈
            '112040.KS',   # 위메이드
            '036830.KS',   # 솔브레인
            '122870.KS',   # 와이지엔터테인먼트
            '900140.KS',   #엘브이엠씨홀딩스
            '950140.KS',   # 잉글우드랩
            '141080.KS',   # 레고켐바이오
            '195940.KS',   # 휴젤
            '200130.KS',   # 바이젠셀
            '215600.KS',   # 신라젬백화점
            '225190.KS',   # 삼양옵틱스
            '240810.KS',   # 원익IPS
        ]
        
        self.name_map = {
            '247540.KS': '에코프로비엠', '086520.KS': '에코프로',
            '196170.KS': '알테오젠', '352820.KS': '하이브',
            '259960.KS': '크래프톤', '161890.KS': '한국콜마',
            '214150.KS': '클리시스', '263750.KS': '펄어비스',
            '293490.KS': '카카오게임즈', '112040.KS': '위메이드',
            '036830.KS': '솔브레인', '122870.KS': '와이지엔터',
            '900140.KS': '엘브이엠씨', '950140.KS': '잉글우드랩',
            '141080.KS': '레고켐바이오', '195940.KS': '휴젤',
            '200130.KS': '바이젠셀', '215600.KS': '신라젬백화점',
            '225190.KS': '삼양옵틱스', '240810.KS': '원익IPS',
        }
        
        self.results = {
            'livermore': [],
            'oneil': [],
            'minervini': []
        }
    
    def fetch_data(self, symbol: str, period: str = '6mo') -> Optional[pd.DataFrame]:
        """종목 데이터 수집"""
        try:
            df = yf.download(symbol, period=period, progress=False)
            if df.empty or len(df) < 30:
                return None
            df.columns = ['Close', 'High', 'Low', 'Open', 'Volume']
            return df
        except:
            return None
    
    def scan_livermore(self, df: pd.DataFrame, symbol: str) -> Optional[Dict]:
        """리버모어 52주 신고가 돌파"""
        if df is None or len(df) < 60:
            return None
        
        current = df.iloc[-1]
        prev = df.iloc[-2]
        
        # 52주 최고가
        high_52w = df['High'].tail(252).max() if len(df) >= 252 else df['High'].max()
        
        # 현재가가 52주 최고가 근접
        price = current['Close']
        breakout_threshold = high_52w * 0.98
        
        if price < breakout_threshold:
            return None
        
        # 거래량
        avg_volume = df['Volume'].tail(20).mean()
        volume_ratio = current['Volume'] / avg_volume if avg_volume > 0 else 0
        
        # 점수
        score = 0
        signals = []
        
        if price >= high_52w:
            score += 40
            signals.append('52W_HIGH_BREAKOUT')
        elif price >= high_52w * 0.99:
            score += 30
            signals.append('NEAR_52W_HIGH')
        
        if volume_ratio >= 2.0:
            score += 30
            signals.append('VOLUME_SPIKE_2X')
        elif volume_ratio >= 1.5:
            score += 20
            signals.append('VOLUME_SPIKE_1.5X')
        
        # 이동평균
        df['MA20'] = df['Close'].rolling(20).mean()
        df['MA60'] = df['Close'].rolling(60).mean()
        
        if price > df['MA20'].iloc[-1] > df['MA60'].iloc[-1]:
            score += 10
            signals.append('BULLISH_TREND')
        
        if score < 60:
            return None
        
        return {
            'symbol': symbol,
            'name': self.name_map.get(symbol, symbol),
            'strategy': 'Livermore',
            'price': round(price, 0),
            'change_pct': round((price - prev['Close']) / prev['Close'] * 100, 2),
            'high_52w': round(high_52w, 0),
            'volume_ratio': round(volume_ratio, 2),
            'score': score,
            'signals': signals
        }
    
    def scan_oneil(self, df: pd.DataFrame, symbol: str) -> Optional[Dict]:
        """오닐 거래량 폭발"""
        if df is None or len(df) < 50:
            return None
        
        current = df.iloc[-1]
        prev = df.iloc[-2]
        
        # 가격 상승 필수
        price_change = (current['Close'] - prev['Close']) / prev['Close'] * 100
        if price_change <= 0:
            return None
        
        # 거래량 분석
        avg_volume_50 = df['Volume'].tail(50).mean()
        volume_ratio = current['Volume'] / avg_volume_50 if avg_volume_50 > 0 else 0
        
        if volume_ratio < 1.5:  # 최소 1.5배
            return None
        
        # 점수
        score = 0
        signals = []
        
        if volume_ratio >= 3.0:
            score += 40
            signals.append('VOLUME_SPIKE_3X')
        elif volume_ratio >= 2.0:
            score += 35
            signals.append('VOLUME_SPIKE_2X')
        elif volume_ratio >= 1.5:
            score += 25
            signals.append('VOLUME_SPIKE_1.5X')
        
        if price_change >= 10:
            score += 30
            signals.append('PRICE_SURGE_10PCT')
        elif price_change >= 5:
            score += 25
            signals.append('PRICE_SURGE_5PCT')
        elif price_change >= 3:
            score += 15
            signals.append('PRICE_GAIN_3PCT')
        
        # 돌파
        high_20 = df['High'].tail(20).max()
        if current['Close'] >= high_20 * 0.98:
            score += 15
            signals.append('BREAKOUT_20DAY')
        
        if score < 50:
            return None
        
        return {
            'symbol': symbol,
            'name': self.name_map.get(symbol, symbol),
            'strategy': 'O\'Neil',
            'price': round(current['Close'], 0),
            'price_change': round(price_change, 2),
            'volume_ratio': round(volume_ratio, 2),
            'score': score,
            'signals': signals
        }
    
    def scan_minervini(self, df: pd.DataFrame, symbol: str) -> Optional[Dict]:
        """미너비니 VCP"""
        if df is None or len(df) < 50:
            return None
        
        # 이동평균 먼저 계산
        df['MA20'] = df['Close'].rolling(20).mean()
        df['MA50'] = df['Close'].rolling(50).mean()
        
        # ATR 계산
        high_low = df['High'] - df['Low']
        high_close = (df['High'] - df['Close'].shift()).abs()
        low_close = (df['Low'] - df['Close'].shift()).abs()
        ranges = pd.concat([high_low, high_close, low_close], axis=1)
        true_range = ranges.max(axis=1)
        df['ATR'] = true_range.rolling(14).mean()
        df['ATR_Pct'] = df['ATR'] / df['Close'] * 100
        
        recent = df.tail(30)
        
        # 추세 확인
        price = recent['Close'].iloc[-1]
        if len(recent) < 10 or recent['MA50'].isna().iloc[-1]:
            return None
            
        if not (price > recent['MA50'].iloc[-1] and recent['MA50'].iloc[-1] > recent['MA50'].iloc[-10]):
            return None
        
        # 변동성 축소
        seg1 = recent.head(10)
        seg2 = recent.iloc[10:20]
        seg3 = recent.tail(10)
        
        atr1 = seg1['ATR_Pct'].mean()
        atr2 = seg2['ATR_Pct'].mean()
        atr3 = seg3['ATR_Pct'].mean()
        
        volatility_contraction = (atr1 > atr2 > atr3) and (atr3 < atr1 * 0.7)
        
        # 가격 압축
        recent_high = recent['High'].max()
        recent_low = recent['Low'].min()
        consolidation_range = (recent_high - recent_low) / recent_low * 100
        
        if not volatility_contraction and consolidation_range > 15:
            return None
        
        # 점수
        score = 0
        signals = []
        vcp_stage = 0
        
        if volatility_contraction and atr3 < atr1 * 0.5:
            score += 30
            signals.append('STRONG_VCP')
            vcp_stage = 3
        elif volatility_contraction:
            score += 25
            signals.append('VCP_PATTERN')
            vcp_stage = 2
        
        if consolidation_range < 10:
            score += 20
            signals.append('TIGHT_CONSOLIDATION')
        elif consolidation_range < 15:
            score += 15
            signals.append('PRICE_COMPRESSION')
        
        if score < 50:
            return None
        
        return {
            'symbol': symbol,
            'name': self.name_map.get(symbol, symbol),
            'strategy': 'Minervini VCP',
            'price': round(price, 0),
            'vcp_stage': vcp_stage,
            'atr_contraction': round(atr1 - atr3, 2),
            'consolidation_range': round(consolidation_range, 2),
            'score': score,
            'signals': signals
        }
    
    def scan_all(self):
        """전체 종목 전략별 스캔"""
        print(f"🔍 KOSDAQ 종목 스캔 시작...")
        print(f"대상 종목: {len(self.watchlist)}개\n")
        
        for i, symbol in enumerate(self.watchlist, 1):
            print(f"  [{i}/{len(self.watchlist)}] {symbol} 분석 중...", end=' ')
            
            df = self.fetch_data(symbol)
            if df is None:
                print("❌ 데이터 없음")
                continue
            
            results_found = []
            
            # 리버모어
            result = self.scan_livermore(df, symbol)
            if result:
                self.results['livermore'].append(result)
                results_found.append(f"Livermore({result['score']})")
            
            # 오닐
            result = self.scan_oneil(df, symbol)
            if result:
                self.results['oneil'].append(result)
                results_found.append(f"O'Neil({result['score']})")
            
            # 미너비니
            result = self.scan_minervini(df, symbol)
            if result:
                self.results['minervini'].append(result)
                results_found.append(f"VCP({result['score']})")
            
            if results_found:
                print(f"✅ {' | '.join(results_found)}")
            else:
                print("❌")
        
        # 정렬
        for key in self.results:
            self.results[key].sort(key=lambda x: x['score'], reverse=True)
    
    def save_results(self):
        """결과 저장"""
        # JSON 저장
        output = {
            'scan_date': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'market': 'KOSDAQ',
            'total_scanned': len(self.watchlist),
            'results': self.results
        }
        
        json_file = f'{BASE_PATH}/data/kosdaq_scan_results.json'
        with open(json_file, 'w', encoding='utf-8') as f:
            json.dump(output, f, indent=2, ensure_ascii=False)
        
        # 텍스트 리포트
        report_file = f'{BASE_PATH}/data/kosdaq_report.txt'
        with open(report_file, 'w', encoding='utf-8') as f:
            f.write("=" * 70 + "\n")
            f.write("📈 KOSDAQ 전략별 스캔 리포트\n")
            f.write(f"스캔일: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write("=" * 70 + "\n\n")
            
            for strategy, stocks in self.results.items():
                f.write(f"\n{'='*70}\n")
                f.write(f"🎯 {strategy.upper()} 전략 ({len(stocks)}개)\n")
                f.write(f"{'='*70}\n\n")
                
                for i, stock in enumerate(stocks[:10], 1):
                    f.write(f"{i}. {stock['name']} ({stock['symbol']})\n")
                    f.write(f"   가격: {stock['price']:,.0f}원\n")
                    f.write(f"   점수: {stock['score']}/100\n")
                    f.write(f"   신호: {', '.join(stock['signals'])}\n\n")
        
        print(f"\n✅ 결과 저장 완료:")
        print(f"  - JSON: kosdaq_scan_results.json")
        print(f"  - Report: kosdaq_report.txt")
    
    def print_summary(self):
        """요약 출력"""
        print(f"\n{'='*70}")
        print(f"📊 KOSDAQ 스캔 결과 요약")
        print(f"{'='*70}")
        print(f"스캔 종목: {len(self.watchlist)}개")
        print(f"{'='*70}\n")
        
        for strategy, stocks in self.results.items():
            print(f"\n🎯 {strategy.upper()}: {len(stocks)}개")
            if stocks:
                print("-" * 50)
                for s in stocks[:5]:
                    print(f"  • {s['name']}: {s['price']:,.0f}원 (점수: {s['score']})")


def main():
    """메인 실행"""
    print("=" * 70)
    print("🎯 KOSDAQ 전략별 스캐너")
    print(f"실행: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 70 + "\n")
    
    scanner = KOSDAQScanner()
    scanner.scan_all()
    scanner.save_results()
    scanner.print_summary()
    
    print(f"\n{'='*70}")
    print("✅ 스캔 완료!")
    print(f"{'='*70}\n")


if __name__ == "__main__":
    main()
