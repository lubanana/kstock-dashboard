#!/usr/bin/env python3
"""
William O'Neil Volume Spike Pattern Scanner
윌리엄 오닐 거래량 폭발 패턴 발굴기

핵심 전략 (CAN SLIM의 V = Volume):
1. 거래량 폭발 (Volume Spike) - 평균의 2배 이상
2. 가격 상승 동반 (Price Increase) - +5% 이상
3. 돌파 패턴 (Breakout) - 저항선/신고가 돌파
4. 기관 매수 흔적 (Institutional Accumulation)
5. 상대강도 (RS) 상위 종목

오닐의 핵심 원칙:
- "큰 돈은 거래량 폭발과 함께 온다"
- "50일 평균 거래량의 2배 이상이 확인되어야 한다"
- "가격 상승 없는 거래량 증가는 의미 없다"
"""

import yfinance as yf
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import List, Dict, Optional
import json
import os

BASE_PATH = '/home/programs/kstock_analyzer'


class ONeilVolumeScanner:
    """윌리엄 오닐 거래량 폭발 패턴 스캐너"""
    
    def __init__(self):
        self.watchlist = self._load_watchlist()
        self.results = []
    
    def _load_watchlist(self) -> List[str]:
        """관심 종목 리스트 (리버모어와 동일)"""
        return [
            '005930.KS',   # 삼성전자
            '000660.KS',   # SK하이닉스
            '035420.KS',   # NAVER
            '005380.KS',   # 현대차
            '051910.KS',   # LG화학
            '035720.KS',   # 카카오
            '006400.KS',   # 삼성SDI
            '068270.KS',   # 셀트리온
            '005490.KS',   # POSCO홀딩스
            '028260.KS',   # 삼성물산
            '012450.KS',   # 한화에어로스페이스
            '247540.KS',   # 에코프로비엠
            '086520.KS',   # 에코프로
            '091990.KS',   # 셀트리온헬스케어
            '196170.KS',   # 알테오젠
            '352820.KS',   # 하이브
            '259960.KS',   # 크래프톤
            '161890.KS',   # 한국콜마
            '214150.KS',   # 클래시스
            '263750.KS',   # 펄어비스
        ]
    
    def fetch_data(self, symbol: str, period: str = '6mo') -> Optional[pd.DataFrame]:
        """종목 데이터 수집"""
        try:
            df = yf.download(symbol, period=period, progress=False)
            if df.empty or len(df) < 50:
                return None
            
            df.columns = ['Close', 'High', 'Low', 'Open', 'Volume']
            return df
        except:
            return None
    
    def analyze_volume_pattern(self, df: pd.DataFrame, symbol: str) -> Optional[Dict]:
        """오닐 거래량 폭발 패턴 분석"""
        if df is None or len(df) < 50:
            return None
        
        # 현재 및 과거 데이터
        current = df.iloc[-1]
        prev = df.iloc[-2]
        
        # 1. 거래량 분석 (핵심)
        avg_volume_50 = df['Volume'].tail(50).mean()
        avg_volume_20 = df['Volume'].tail(20).mean()
        current_volume = current['Volume']
        
        volume_ratio_50 = current_volume / avg_volume_50 if avg_volume_50 > 0 else 0
        volume_ratio_20 = current_volume / avg_volume_20 if avg_volume_20 > 0 else 0
        
        # 오닐 기준: 50일 평균의 2배 이상
        volume_spike = volume_ratio_50 >= 2.0
        volume_strong = volume_ratio_50 >= 1.5
        
        # 2. 가격 상승 분석 (필수 조건)
        price_change = (current['Close'] - prev['Close']) / prev['Close'] * 100
        price_surge = price_change >= 5.0  # 5% 이상 상승
        price_positive = price_change > 0
        
        # 거래량 폭발만으로는 부적 - 가격 상승 필요
        if not price_positive:
            return None
        
        # 3. 돌파 패턴 분석
        high_20 = df['High'].tail(20).max()
        high_50 = df['High'].tail(50).max()
        
        breakout_20 = current['Close'] >= high_20 * 0.98  # 20일 최고가 돌파
        breakout_50 = current['Close'] >= high_50 * 0.98  # 50일 최고가 돌파
        
        # 4. 누적/분배 분석 (Accumulation/Distribution)
        df['Price_Change'] = df['Close'].pct_change()
        df['Volume_MA'] = df['Volume'].rolling(20).mean()
        
        # 상승일 거래량 / 하띙일 거래량 비율
        up_days = df[df['Price_Change'] > 0]['Volume'].mean()
        down_days = df[df['Price_Change'] < 0]['Volume'].mean()
        accumulation_ratio = up_days / down_days if down_days > 0 else 1
        
        accumulation = accumulation_ratio > 1.2  # 기관 매수 흔적
        
        # 5. 상대강도 (RS) - KOSPI 대비
        try:
            kospi = yf.download('^KS11', period='6mo', progress=False)
            kospi_change = (kospi['Close'].iloc[-1] - kospi['Close'].iloc[-20]) / kospi['Close'].iloc[-20] * 100
            stock_change_20 = (current['Close'] - df['Close'].iloc[-20]) / df['Close'].iloc[-20] * 100
            rs_ratio = stock_change_20 / kospi_change if kospi_change != 0 else 0
            strong_rs = rs_ratio > 1.2  # 시장 대비 20% 이상 강함
        except:
            strong_rs = False
            rs_ratio = 0
        
        # 6. 기술적 패턴
        df['MA20'] = df['Close'].rolling(20).mean()
        df['MA50'] = df['Close'].rolling(50).mean()
        
        above_ma20 = current['Close'] > df['MA20'].iloc[-1]
        above_ma50 = current['Close'] > df['MA50'].iloc[-1]
        golden_cross = df['MA20'].iloc[-1] > df['MA50'].iloc[-1]
        
        # 점수 계산 (오닐 가중치)
        score = 0
        signals = []
        
        # 핵심: 거래량 폭발 (40점)
        if volume_ratio_50 >= 3.0:
            score += 40
            signals.append('VOLUME_SPIKE_3X')
        elif volume_ratio_50 >= 2.0:
            score += 35
            signals.append('VOLUME_SPIKE_2X')
        elif volume_ratio_50 >= 1.5:
            score += 25
            signals.append('VOLUME_SPIKE_1.5X')
        
        # 핵심: 가격 상승 (30점)
        if price_change >= 10:
            score += 30
            signals.append('PRICE_SURGE_10PCT')
        elif price_change >= 5:
            score += 25
            signals.append('PRICE_SURGE_5PCT')
        elif price_change >= 3:
            score += 15
            signals.append('PRICE_GAIN_3PCT')
        
        # 돌파 패턴 (15점)
        if breakout_50:
            score += 15
            signals.append('BREAKOUT_50DAY')
        elif breakout_20:
            score += 10
            signals.append('BREAKOUT_20DAY')
        
        # 기관 매수 (10점)
        if accumulation:
            score += 10
            signals.append('INSTITUTIONAL_ACCUM')
        
        # 상대강도 (5점)
        if strong_rs:
            score += 5
            signals.append('STRONG_RS')
        
        # 최소 점수 필터 (오닐 기준 엄격)
        if score < 50:
            return None
        
        # 종목명 매핑
        name_map = {
            '005930.KS': '삼성전자', '000660.KS': 'SK하이닉스',
            '035420.KS': 'NAVER', '005380.KS': '현대차',
            '051910.KS': 'LG화학', '035720.KS': '카카오',
            '006400.KS': '삼성SDI', '068270.KS': '셀트리온',
            '005490.KS': 'POSCO홀딩스', '028260.KS': '삼성물산',
            '012450.KS': '한화에어로스페이스', '247540.KS': '에코프로비엠',
            '086520.KS': '에코프로', '091990.KS': '셀트리온헬스케어',
            '196170.KS': '알테오젠', '352820.KS': '하이브',
            '259960.KS': '크래프톤', '161890.KS': '한국콜마',
            '214150.KS': '클래시스', '263750.KS': '펄어비스',
        }
        
        return {
            'symbol': symbol,
            'name': name_map.get(symbol, symbol),
            'price': round(current['Close'], 0),
            'price_change': round(price_change, 2),
            'volume': int(current_volume),
            'volume_ratio_50d': round(volume_ratio_50, 2),
            'volume_ratio_20d': round(volume_ratio_20, 2),
            'breakout_20d': bool(breakout_20),
            'breakout_50d': bool(breakout_50),
            'accumulation': bool(accumulation),
            'accumulation_ratio': round(accumulation_ratio, 2),
            'strong_rs': bool(strong_rs),
            'rs_ratio': round(rs_ratio, 2),
            'above_ma20': bool(above_ma20),
            'above_ma50': bool(above_ma50),
            'golden_cross': bool(golden_cross),
            'score': int(score),
            'signals': signals,
            'pattern': self._classify_pattern(signals),
            'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        }
    
    def _classify_pattern(self, signals: List[str]) -> str:
        """패턴 분류"""
        if 'VOLUME_SPIKE_3X' in signals and 'PRICE_SURGE_5PCT' in signals:
            if 'BREAKOUT_50DAY' in signals:
                return 'STRONG_BREAKOUT'
            return 'VOLUME_EXPLOSION'
        elif 'VOLUME_SPIKE_2X' in signals and 'INSTITUTIONAL_ACCUM' in signals:
            return 'ACCUMULATION_PHASE'
        elif 'VOLUME_SPIKE_1.5X' in signals and 'STRONG_RS' in signals:
            return 'RELATIVE_STRENGTH'
        return 'VOLUME_INCREASE'
    
    def scan(self) -> List[Dict]:
        """전체 종목 스캔"""
        print(f"🔍 오닐 거래량 폭발 패턴 스캔 시작...")
        print(f"대상 종목: {len(self.watchlist)}개")
        print(f"기준: 50일 평균 거래량 2배 + 가격 상승\n")
        
        results = []
        for i, symbol in enumerate(self.watchlist, 1):
            print(f"  [{i}/{len(self.watchlist)}] {symbol} 분석 중...", end=' ')
            
            df = self.fetch_data(symbol)
            result = self.analyze_volume_pattern(df, symbol)
            
            if result:
                results.append(result)
                print(f"✅ SCORE {result['score']} ({result['pattern']})")
            else:
                print("❌")
        
        # 점수 높은 순 정렬
        results.sort(key=lambda x: x['score'], reverse=True)
        self.results = results
        
        return results
    
    def save_results(self):
        """결과 저장"""
        if not self.results:
            print("\n⚠️ 발굴된 종목이 없습니다.")
            return
        
        # JSON 저장
        output = {
            'scan_date': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'scanner': "William O'Neil Volume Spike Pattern",
            'criteria': {
                'volume_spike': '50일 평균 2배 이상',
                'price_gain': '양봉 (가격 상승)',
                'breakout': '20일/50일 최고가 돌파',
                'accumulation': '기관 매수 흔적'
            },
            'total_scanned': len(self.watchlist),
            'breakout_count': len(self.results),
            'stocks': self.results
        }
        
        json_file = f'{BASE_PATH}/data/oneil_volume_breakouts.json'
        with open(json_file, 'w', encoding='utf-8') as f:
            json.dump(output, f, indent=2, ensure_ascii=False)
        
        # CSV 저장
        df = pd.DataFrame(self.results)
        csv_file = f'{BASE_PATH}/data/oneil_volume_breakouts.csv'
        df.to_csv(csv_file, index=False, encoding='utf-8-sig')
        
        # 텍스트 리포트
        report_file = f'{BASE_PATH}/data/oneil_report.txt'
        with open(report_file, 'w', encoding='utf-8') as f:
            f.write("=" * 70 + "\n")
            f.write("📈 윌리엄 오닐 거래량 폭발 패턴 리포트\n")
            f.write(f"스캔일: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write("=" * 70 + "\n\n")
            
            f.write("[오닐의 핵심 원칙]\n")
            f.write("- 큰 돈은 거래량 폭발과 함께 온다\n")
            f.write("- 50일 평균 거래량의 2배 이상 확인 필요\n")
            f.write("- 가격 상승 없는 거래량 증가는 의미 없다\n\n")
            
            for i, stock in enumerate(self.results[:10], 1):
                f.write(f"{i}. {stock['name']} ({stock['symbol']})\n")
                f.write(f"   패턴: {stock['pattern']}\n")
                f.write(f"   가격: {stock['price']:,.0f}원 ({stock['price_change']:+.2f}%)\n")
                f.write(f"   거래량: {stock['volume']:,} (평균대비 {stock['volume_ratio_50d']:.1f}x)\n")
                f.write(f"   20일 돌파: {'✓' if stock['breakout_20d'] else '✗'}\n")
                f.write(f"   50일 돌파: {'✓' if stock['breakout_50d'] else '✗'}\n")
                f.write(f"   기관매수: {'✓' if stock['accumulation'] else '✗'}\n")
                f.write(f"   상대강도: {'✓' if stock['strong_rs'] else '✗'}\n")
                f.write(f"   점수: {stock['score']}/100\n")
                f.write(f"   신호: {', '.join(stock['signals'])}\n\n")
        
        print(f"\n✅ 결과 저장 완료:")
        print(f"  - JSON: oneil_volume_breakouts.json")
        print(f"  - CSV: oneil_volume_breakouts.csv")
        print(f"  - Report: oneil_report.txt")
    
    def print_summary(self):
        """요약 출력"""
        if not self.results:
            print("\n⚠️ 발굴된 종목이 없습니다.")
            return
        
        print(f"\n{'='*70}")
        print(f"📊 오닐 거래량 폭발 패턴 스캔 결과")
        print(f"{'='*70}")
        print(f"스캔 종목: {len(self.watchlist)}개")
        print(f"발굴 종목: {len(self.results)}개")
        print(f"{'='*70}\n")
        
        print(f"{'순위':<4} {'종목':<12} {'현재가':<10} {'등락':<8} {'거래량':<8} {'점수':<6} {'패턴'}")
        print("-" * 80)
        
        for i, stock in enumerate(self.results[:10], 1):
            print(f"{i:<4} {stock['name']:<12} {stock['price']:>9,.0f} "
                  f"{stock['price_change']:>+6.1f}% {stock['volume_ratio_50d']:<7.1f}x "
                  f"{stock['score']:<6} {stock['pattern']}")


def main():
    """메인 실행"""
    print("=" * 70)
    print("🎯 윌리엄 오닐 거래량 폭발 패턴 스캐너")
    print(f"실행: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 70 + "\n")
    
    scanner = ONeilVolumeScanner()
    scanner.scan()
    scanner.save_results()
    scanner.print_summary()
    
    print(f"\n{'='*70}")
    print("✅ 스캔 완료!")
    print(f"{'='*70}\n")


if __name__ == "__main__":
    main()
