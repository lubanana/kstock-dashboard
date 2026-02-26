#!/usr/bin/env python3
"""
Livermore New High Breakout Scanner
제시 리버모어 신고가 돌파 종목 발굴기

핵심 전략:
1. 52주 신고가 돌파 (New 52-week high)
2. 거래량 급증 (Volume spike)
3. 가격 압축 후 돌파 (Consolidation breakout)
4. 추세 확인 (Trend confirmation)
"""

import yfinance as yf
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import List, Dict, Optional
import json
import os

BASE_PATH = '/home/programs/kstock_analyzer'


class LivermoreScanner:
    """제시 리버모어 신고가 돌파 스캐너"""
    
    def __init__(self):
        self.watchlist = self._load_watchlist()
        self.results = []
    
    def _load_watchlist(self) -> List[str]:
        """관심 종목 리스트"""
        # KOSPI 대형주 + 유동성 좋은 종목
        return [
            # 대형주
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
            # 중형주
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
    
    def fetch_data(self, symbol: str, period: str = '1y') -> Optional[pd.DataFrame]:
        """종목 데이터 수집"""
        try:
            df = yf.download(symbol, period=period, progress=False)
            if df.empty or len(df) < 60:
                return None
            
            # 컬럼 정제
            df.columns = ['Close', 'High', 'Low', 'Open', 'Volume']
            return df
        except:
            return None
    
    def analyze_breakout(self, df: pd.DataFrame, symbol: str) -> Optional[Dict]:
        """신고가 돌파 분석"""
        if df is None or len(df) < 60:
            return None
        
        # 현재가 및 과거 데이터
        current = df.iloc[-1]
        prev = df.iloc[-2]
        
        # 52주 최고가
        high_52w = df['High'].tail(252).max()
        
        # 현재가가 52주 최고가 근접 또는 돌파
        price = current['Close']
        breakout_threshold = high_52w * 0.98  # 2% 이내
        
        if price < breakout_threshold:
            return None  # 신고가 근접 아님
        
        # 거래량 분석
        avg_volume = df['Volume'].tail(20).mean()
        current_volume = current['Volume']
        volume_ratio = current_volume / avg_volume if avg_volume > 0 else 0
        
        # 가격 압축 (Consolidation) 확인 - 볼린저 밴드 폭
        df['MA20'] = df['Close'].rolling(20).mean()
        df['STD20'] = df['Close'].rolling(20).std()
        df['BB_Width'] = (df['STD20'] * 2) / df['MA20']
        
        bb_width = df['BB_Width'].iloc[-1]
        bb_width_avg = df['BB_Width'].tail(20).mean()
        
        # 압축 후 돌파: BB 폭이 좁아졌다가 넓어짐
        compression = bb_width < bb_width_avg * 0.9
        expansion = bb_width > bb_width_avg * 1.1
        
        # 추세 확인
        df['MA20'] = df['Close'].rolling(20).mean()
        df['MA60'] = df['Close'].rolling(60).mean()
        
        trend_bullish = price > df['MA20'].iloc[-1] > df['MA60'].iloc[-1]
        
        # 점수 계산 (0-100)
        score = 0
        signals = []
        
        # 1. 신고가 돌파 (40점)
        if price >= high_52w:
            score += 40
            signals.append('52W_HIGH_BREAKOUT')
        elif price >= high_52w * 0.99:
            score += 30
            signals.append('NEAR_52W_HIGH')
        
        # 2. 거래량 급증 (30점)
        if volume_ratio >= 2.0:
            score += 30
            signals.append('VOLUME_SPIKE_2X')
        elif volume_ratio >= 1.5:
            score += 20
            signals.append('VOLUME_SPIKE_1.5X')
        elif volume_ratio >= 1.2:
            score += 10
            signals.append('VOLUME_INCREASE')
        
        # 3. 가격 압축 후 돌파 (20점)
        if compression:
            score += 10
            signals.append('CONSOLIDATION')
        if expansion:
            score += 10
            signals.append('BREAKOUT_EXPANSION')
        
        # 4. 추세 확인 (10점)
        if trend_bullish:
            score += 10
            signals.append('BULLISH_TREND')
        
        # 최소 점수 필터 (60점 이상만)
        if score < 60:
            return None
        
        # 종목명 매핑
        name_map = {
            '005930.KS': '삼성전자',
            '000660.KS': 'SK하이닉스',
            '035420.KS': 'NAVER',
            '005380.KS': '현대차',
            '051910.KS': 'LG화학',
            '035720.KS': '카카오',
            '006400.KS': '삼성SDI',
            '068270.KS': '셀트리온',
            '005490.KS': 'POSCO홀딩스',
            '028260.KS': '삼성물산',
            '012450.KS': '한화에어로스페이스',
            '247540.KS': '에코프로비엠',
            '086520.KS': '에코프로',
            '091990.KS': '셀트리온헬스케어',
            '196170.KS': '알테오젠',
            '352820.KS': '하이브',
            '259960.KS': '크래프톤',
            '161890.KS': '한국콜마',
            '214150.KS': '클래시스',
            '263750.KS': '펄어비스',
        }
        
        return {
            'symbol': symbol,
            'name': name_map.get(symbol, symbol),
            'price': round(price, 0),
            'change_pct': round((price - prev['Close']) / prev['Close'] * 100, 2),
            'high_52w': round(high_52w, 0),
            'breakout_pct': round((price / high_52w - 1) * 100, 2),
            'volume_ratio': round(volume_ratio, 2),
            'score': score,
            'signals': signals,
            'trend': 'BULLISH' if trend_bullish else 'NEUTRAL',
            'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        }
    
    def scan(self) -> List[Dict]:
        """전체 종목 스캔"""
        print(f"🔍 리버모어 신고가 돌파 스캔 시작...")
        print(f"대상 종목: {len(self.watchlist)}개\n")
        
        results = []
        for i, symbol in enumerate(self.watchlist, 1):
            print(f"  [{i}/{len(self.watchlist)}] {symbol} 분석 중...", end=' ')
            
            df = self.fetch_data(symbol)
            result = self.analyze_breakout(df, symbol)
            
            if result:
                results.append(result)
                print(f"✅ SCORE {result['score']}")
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
            'total_scanned': len(self.watchlist),
            'breakout_count': len(self.results),
            'stocks': self.results
        }
        
        json_file = f'{BASE_PATH}/data/livermore_breakouts.json'
        with open(json_file, 'w', encoding='utf-8') as f:
            json.dump(output, f, indent=2, ensure_ascii=False)
        
        # CSV 저장
        df = pd.DataFrame(self.results)
        csv_file = f'{BASE_PATH}/data/livermore_breakouts.csv'
        df.to_csv(csv_file, index=False, encoding='utf-8-sig')
        
        # 텍스트 리포트
        report_file = f'{BASE_PATH}/data/livermore_report.txt'
        with open(report_file, 'w', encoding='utf-8') as f:
            f.write("=" * 60 + "\n")
            f.write("📈 리버모어 신고가 돌파 리포트\n")
            f.write(f"스캔일: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write("=" * 60 + "\n\n")
            
            for i, stock in enumerate(self.results[:10], 1):
                f.write(f"{i}. {stock['name']} ({stock['symbol']})\n")
                f.write(f"   가격: {stock['price']:,.0f}원\n")
                f.write(f"   등락: {stock['change_pct']:+.2f}%\n")
                f.write(f"   52주 최고가 돌파: {stock['breakout_pct']:+.2f}%\n")
                f.write(f"   거래량 비율: {stock['volume_ratio']:.1f}x\n")
                f.write(f"   점수: {stock['score']}/100\n")
                f.write(f"   신호: {', '.join(stock['signals'])}\n")
                f.write(f"   추세: {stock['trend']}\n\n")
        
        print(f"\n✅ 결과 저장 완료:")
        print(f"  - JSON: livermore_breakouts.json")
        print(f"  - CSV: livermore_breakouts.csv")
        print(f"  - Report: livermore_report.txt")
    
    def print_summary(self):
        """요약 출력"""
        if not self.results:
            print("\n⚠️ 발굴된 종목이 없습니다.")
            return
        
        print(f"\n{'='*60}")
        print(f"📊 스캔 결과 요약")
        print(f"{'='*60}")
        print(f"스캔 종목: {len(self.watchlist)}개")
        print(f"돌파 종목: {len(self.results)}개")
        print(f"{'='*60}\n")
        
        print(f"{'순위':<4} {'종목':<12} {'현재가':<10} {'등락':<8} {'점수':<6} {'신호'}")
        print("-" * 70)
        
        for i, stock in enumerate(self.results[:10], 1):
            signals = ', '.join(stock['signals'][:2])
            print(f"{i:<4} {stock['name']:<12} {stock['price']:>9,.0f} "
                  f"{stock['change_pct']:>+6.1f}% {stock['score']:<6} {signals}")


def main():
    """메인 실행"""
    print("=" * 60)
    print("🎯 리버모어 신고가 돌파 스캐너")
    print(f"실행: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60 + "\n")
    
    scanner = LivermoreScanner()
    scanner.scan()
    scanner.save_results()
    scanner.print_summary()
    
    print(f"\n{'='*60}")
    print("✅ 스캔 완료!")
    print(f"{'='*60}\n")


if __name__ == "__main__":
    main()
