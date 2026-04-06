#!/usr/bin/env python3
"""
Mark Minervini Volatility Contraction Pattern (VCP) Scanner
마크 미너비니 변동성 축소 패턴 발굴기

핵심 전략 (SEPA의 VCP):
1. 변동성 축소 (Volatility Contraction) - A < B < C
2. 거래량 감소 (Volume Contraction)
3. 가격 압축 (Price Consolidation)
4. 돌파 준비 (Breakout Setup)
5. 상대강도 상위 (RS Leader)

미너비니의 핵심 원칙:
- "변동성은 돌파 전에 반드시 축소되어야 한다"
- "A-B-C 패턴: 각 후퇴가 점점 작아져야 한다"
- "거래량은 압축 기간 동안 줄어들어야 한다"
- "돌파는 거래량 폭발과 함께 와야 한다"
"""

import yfinance as yf
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Tuple
import json
import os

BASE_PATH = '/home/programs/kstock_analyzer'


class MinerviniVCPScanner:
    """마크 미너비니 VCP 스캐너"""
    
    def __init__(self):
        self.watchlist = self._load_watchlist()
        self.results = []
    
    def _load_watchlist(self) -> List[str]:
        """관심 종목 리스트"""
        return [
            '005930.KS', '000660.KS', '035420.KS', '005380.KS', '051910.KS',
            '035720.KS', '006400.KS', '068270.KS', '005490.KS', '028260.KS',
            '012450.KS', '247540.KS', '086520.KS', '091990.KS', '196170.KS',
            '352820.KS', '259960.KS', '161890.KS', '214150.KS', '263750.KS',
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
    
    def calculate_atr(self, df: pd.DataFrame, period: int = 14) -> pd.Series:
        """ATR (Average True Range) 계산"""
        high_low = df['High'] - df['Low']
        high_close = np.abs(df['High'] - df['Close'].shift())
        low_close = np.abs(df['Low'] - df['Close'].shift())
        ranges = pd.concat([high_low, high_close, low_close], axis=1)
        true_range = ranges.max(axis=1)
        atr = true_range.rolling(period).mean()
        return atr
    
    def find_vcp_pattern(self, df: pd.DataFrame, symbol: str) -> Optional[Dict]:
        """VCP 패턴 분석"""
        if df is None or len(df) < 50:
            return None
        
        # 기술적 지표 계산
        df['ATR'] = self.calculate_atr(df)
        df['ATR_Pct'] = df['ATR'] / df['Close'] * 100  # ATR %
        df['MA20'] = df['Close'].rolling(20).mean()
        df['MA50'] = df['Close'].rolling(50).mean()
        df['Volume_MA20'] = df['Volume'].rolling(20).mean()
        
        # 최근 30일 데이터로 VCP 분석
        recent = df.tail(30).copy()
        
        # 1. 추세 확인 (Stage 2)
        price_above_ma50 = recent['Close'].iloc[-1] > recent['MA50'].iloc[-1]
        ma50_rising = recent['MA50'].iloc[-1] > recent['MA50'].iloc[-10]
        
        if not (price_above_ma50 and ma50_rising):
            return None  # 상승 추세 아님
        
        # 2. 변동성 축소 (Volatility Contraction)
        # 3개 구간으로 나누어 ATR 비교
        seg1 = recent.head(10)  # 첫 10일
        seg2 = recent.iloc[10:20]  # 중간 10일
        seg3 = recent.tail(10)  # 마지막 10일
        
        atr1 = seg1['ATR_Pct'].mean()
        atr2 = seg2['ATR_Pct'].mean()
        atr3 = seg3['ATR_Pct'].mean()
        
        # 변동성 축소: A > B > C
        volatility_contraction = (atr1 > atr2 > atr3) and (atr3 < atr1 * 0.7)
        
        # 3. 거래량 축소 (Volume Contraction)
        vol1 = seg1['Volume'].mean()
        vol2 = seg2['Volume'].mean()
        vol3 = seg3['Volume'].mean()
        
        volume_contraction = (vol1 > vol2 > vol3) or (vol3 < vol1 * 0.8)
        
        # 4. 가격 압축 (Price Consolidation)
        # 최근 고점 - 저점 범위
        recent_high = recent['High'].max()
        recent_low = recent['Low'].min()
        consolidation_range = (recent_high - recent_low) / recent_low * 100
        
        tight_consolidation = consolidation_range < 15  # 15% 이내 압축
        
        # 5. 후퇴 깊이 (Pullback Depth) - A-B-C
        # Swing highs and lows
        highs = recent['High'].nlargest(3).sort_index()
        lows = recent['Low'].nsmallest(3).sort_index()
        
        if len(highs) >= 3 and len(lows) >= 3:
            # A, B, C 후퇴 계산
            peak1 = highs.iloc[-1]  # 최근 고점
            trough1 = lows.iloc[-1]  # 최근 저점
            
            pullback_a = (peak1 - trough1) / peak1 * 100
            
            # 이전 스윙
            if len(highs) >= 2 and len(lows) >= 2:
                peak2 = highs.iloc[-2]
                trough2 = lows.iloc[-2]
                pullback_b = (peak2 - trough2) / peak2 * 100
                
                # 후퇴 축소: B < A
                contraction_improving = pullback_a < pullback_b * 1.2
            else:
                contraction_improving = True
                pullback_a = 10
        else:
            contraction_improving = True
            pullback_a = 10
        
        # 6. 돌파 준비 (Breakout Setup)
        current_price = recent['Close'].iloc[-1]
        resistance = recent['High'].tail(10).max()  # 최근 10일 최고가
        near_resistance = current_price >= resistance * 0.97  # 3% 이내
        
        # 7. 상대강도 (Relative Strength)
        try:
            kospi = yf.download('^KS11', period='3mo', progress=False)
            stock_return = (recent['Close'].iloc[-1] - recent['Close'].iloc[0]) / recent['Close'].iloc[0]
            kospi_return = (kospi['Close'].iloc[-1] - kospi['Close'].iloc[0]) / kospi['Close'].iloc[0]
            rs_ratio = stock_return / kospi_return if kospi_return != 0 else 1
            strong_rs = rs_ratio > 1.0
        except:
            strong_rs = True
            rs_ratio = 1.0
        
        # VCP 점수 계산
        score = 0
        signals = []
        vcp_stage = 0
        
        # 핵심: 변동성 축소 (30점)
        if volatility_contraction and atr3 < atr1 * 0.5:
            score += 30
            signals.append('STRONG_VCP')
            vcp_stage = 3
        elif volatility_contraction:
            score += 25
            signals.append('VCP_PATTERN')
            vcp_stage = 2
        elif atr3 < atr1 * 0.8:
            score += 15
            signals.append('VOLATILITY_DECLINING')
            vcp_stage = 1
        
        # 거래량 축소 (25점)
        if volume_contraction and vol3 < vol1 * 0.6:
            score += 25
            signals.append('VOLUME_DRY_UP')
        elif volume_contraction:
            score += 20
            signals.append('VOLUME_CONTRACTION')
        
        # 가격 압축 (20점)
        if tight_consolidation and consolidation_range < 10:
            score += 20
            signals.append('TIGHT_CONSOLIDATION')
        elif tight_consolidation:
            score += 15
            signals.append('PRICE_COMPRESSION')
        
        # 후퇴 축소 (15점)
        if contraction_improving and pullback_a < 10:
            score += 15
            signals.append('SHALLOW_PULLBACK')
        elif contraction_improving:
            score += 10
            signals.append('IMPROVING_CONTRACTION')
        
        # 돌파 준비 (10점)
        if near_resistance:
            score += 10
            signals.append('BREAKOUT_SETUP')
        
        # 최소 조건: 변동성 축소 + 가격 압축
        if not (volatility_contraction or tight_consolidation):
            return None
        
        # 최소 점수
        if score < 50:
            return None
        
        # 종목명
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
            'price': round(current_price, 0),
            'vcp_stage': vcp_stage,
            'atr_a': round(atr1, 2),
            'atr_b': round(atr2, 2),
            'atr_c': round(atr3, 2),
            'atr_contraction': round(atr1 - atr3, 2),
            'consolidation_range': round(consolidation_range, 2),
            'pullback_depth': round(pullback_a, 2),
            'near_resistance': bool(near_resistance),
            'resistance_level': round(resistance, 0),
            'breakout_potential': round((resistance - current_price) / current_price * 100, 2),
            'volume_dry_up': bool(volume_contraction),
            'strong_rs': bool(strong_rs),
            'rs_ratio': round(float(rs_ratio), 2),
            'score': int(score),
            'signals': signals,
            'setup_quality': self._classify_setup(score, vcp_stage),
            'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        }
    
    def _classify_setup(self, score: int, vcp_stage: int) -> str:
        """셋업 품질 분류"""
        if score >= 80 and vcp_stage >= 3:
            return 'PERFECT_VCP'
        elif score >= 70 and vcp_stage >= 2:
            return 'HIGH_QUALITY'
        elif score >= 60:
            return 'GOOD_SETUP'
        else:
            return 'EARLY_STAGE'
    
    def scan(self) -> List[Dict]:
        """전체 종목 스캔"""
        print(f"🔍 미너비니 VCP 패턴 스캔 시작...")
        print(f"대상 종목: {len(self.watchlist)}개")
        print(f"기준: 변동성 축소 A>B>C + 거래량 감소 + 가격 압축\n")
        
        results = []
        for i, symbol in enumerate(self.watchlist, 1):
            print(f"  [{i}/{len(self.watchlist)}] {symbol} 분석 중...", end=' ')
            
            df = self.fetch_data(symbol)
            result = self.find_vcp_pattern(df, symbol)
            
            if result:
                results.append(result)
                print(f"✅ SCORE {result['score']} ({result['setup_quality']})")
            else:
                print("❌")
        
        results.sort(key=lambda x: x['score'], reverse=True)
        self.results = results
        return results
    
    def save_results(self):
        """결과 저장"""
        if not self.results:
            print("\n⚠️ 발굴된 종목이 없습니다.")
            return
        
        output = {
            'scan_date': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'scanner': "Mark Minervini VCP Pattern",
            'criteria': {
                'volatility_contraction': 'ATR A > B > C',
                'volume_dry_up': '거래량 감소',
                'price_compression': '15% 이내 압축',
                'breakout_setup': '저항선 근접'
            },
            'total_scanned': len(self.watchlist),
            'vcp_count': len(self.results),
            'stocks': self.results
        }
        
        json_file = f'{BASE_PATH}/data/minervini_vcp.json'
        with open(json_file, 'w', encoding='utf-8') as f:
            json.dump(output, f, indent=2, ensure_ascii=False)
        
        df = pd.DataFrame(self.results)
        csv_file = f'{BASE_PATH}/data/minervini_vcp.csv'
        df.to_csv(csv_file, index=False, encoding='utf-8-sig')
        
        report_file = f'{BASE_PATH}/data/minervini_report.txt'
        with open(report_file, 'w', encoding='utf-8') as f:
            f.write("=" * 70 + "\n")
            f.write("📈 마크 미너비니 VCP (변동성 축소 패턴) 리포트\n")
            f.write(f"스캔일: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write("=" * 70 + "\n\n")
            
            f.write("[미너비니의 핵심 원칙]\n")
            f.write("- 변동성은 돌파 전에 반드시 축소되어야 한다\n")
            f.write("- A-B-C 패턴: 각 후퇴가 점점 작아져야 한다\n")
            f.write("- 거래량은 압축 기간 동안 줄어들어야 한다\n")
            f.write("- 돌파는 거래량 폭발과 함께 와야 한다\n\n")
            
            for i, stock in enumerate(self.results[:10], 1):
                f.write(f"{i}. {stock['name']} ({stock['symbol']})\n")
                f.write(f"   품질: {stock['setup_quality']}\n")
                f.write(f"   가격: {stock['price']:,.0f}원\n")
                f.write(f"   VCP 단계: {stock['vcp_stage']}\n")
                f.write(f"   ATR 축소: {stock['atr_a']:.2f} → {stock['atr_c']:.2f}\n")
                f.write(f"   압축폭: {stock['consolidation_range']:.1f}%\n")
                f.write(f"   후퇴깊이: {stock['pullback_depth']:.1f}%\n")
                f.write(f"   돌파잠재력: {stock['breakout_potential']:.1f}%\n")
                f.write(f"   점수: {stock['score']}/100\n")
                f.write(f"   신호: {', '.join(stock['signals'])}\n\n")
        
        print(f"\n✅ 결과 저장 완료:")
        print(f"  - JSON: minervini_vcp.json")
        print(f"  - CSV: minervini_vcp.csv")
        print(f"  - Report: minervini_report.txt")
    
    def print_summary(self):
        """요약 출력"""
        if not self.results:
            print("\n⚠️ 발굴된 종목이 없습니다.")
            return
        
        print(f"\n{'='*70}")
        print(f"📊 미너비니 VCP 패턴 스캔 결과")
        print(f"{'='*70}")
        print(f"스캔 종목: {len(self.watchlist)}개")
        print(f"VCP 발굴: {len(self.results)}개")
        print(f"{'='*70}\n")
        
        print(f"{'순위':<4} {'종목':<12} {'현재가':<10} {'VCP':<5} {'ATR축소':<10} {'점수':<6} {'품질'}")
        print("-" * 80)
        
        for i, stock in enumerate(self.results[:10], 1):
            atr_drop = f"{stock['atr_a']:.1f}→{stock['atr_c']:.1f}"
            print(f"{i:<4} {stock['name']:<12} {stock['price']:>9,.0f} "
                  f"{stock['vcp_stage']:<5} {atr_drop:<10} {stock['score']:<6} {stock['setup_quality']}")


def main():
    """메인 실행"""
    print("=" * 70)
    print("🎯 마크 미너비니 VCP (변동성 축소 패턴) 스캐너")
    print(f"실행: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 70 + "\n")
    
    scanner = MinerviniVCPScanner()
    scanner.scan()
    scanner.save_results()
    scanner.print_summary()
    
    print(f"\n{'='*70}")
    print("✅ 스캔 완료!")
    print(f"{'='*70}\n")


if __name__ == "__main__":
    main()
