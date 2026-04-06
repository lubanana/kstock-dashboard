#!/usr/bin/env python3
"""
Triple Signal Scanner - 3가지 신호 동시 발생 종목 검색
리버모어(52주 신고가) + 오닐(거래량 폭발) + 미너비니(VCP) 동시 충족 종목
"""

import yfinance as yf
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Tuple
import json

BASE_PATH = '/home/programs/kstock_analyzer'


class TripleSignalScanner:
    """3가지 신호 동시 스캐너"""
    
    def __init__(self):
        # KOSPI 대형주 + 유동성 좋은 중형주
        self.watchlist = [
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
            '055550.KS',   # 신한지주
            '105560.KS',   # KB금융
            '138040.KS',   # 메리츠금융
            '032830.KS',   # 삼성생명
            '015760.KS',   # 한국전력
            '003670.KS',   # 포스코퓨처엠
            '009150.KS',   # 삼성전기
            '018260.KS',   # 삼성에스디에스
            '033780.KS',   # KT&G
        ]
        
        self.name_map = {
            '005930.KS': '삼성전자', '000660.KS': 'SK하이닉스',
            '035420.KS': 'NAVER', '005380.KS': '현대차',
            '051910.KS': 'LG화학', '035720.KS': '카카오',
            '006400.KS': '삼성SDI', '068270.KS': '셀트리온',
            '005490.KS': 'POSCO홀딩스', '028260.KS': '삼성물산',
            '012450.KS': '한화에어로스페이스', '055550.KS': '신한지주',
            '105560.KS': 'KB금융', '138040.KS': '메리츠금융',
            '032830.KS': '삼성생명', '015760.KS': '한국전력',
            '003670.KS': '포스코퓨처엠', '009150.KS': '삼성전기',
            '018260.KS': '삼성에스디에스', '033780.KS': 'KT&G',
        }
        
        self.results = []
    
    def fetch_data(self, symbol: str) -> Optional[pd.DataFrame]:
        """1년치 데이터 수집"""
        try:
            df = yf.download(symbol, period='1y', progress=False)
            if df.empty or len(df) < 100:
                return None
            df.columns = ['Close', 'High', 'Low', 'Open', 'Volume']
            df = df.dropna()
            return df
        except:
            return None
    
    def check_livermore_signal(self, df: pd.DataFrame, lookback_days: int = 20) -> List[Dict]:
        """
        리버모어 신호: 52주 신고가 돌파
        최근 N일 이내에 발생한 신호 반환
        """
        signals = []
        
        if len(df) < 252:
            return signals
        
        # 52주 최고가
        high_52w = df['High'].rolling(252).max()
        
        # 최근 lookback_days 동안 신고가 돌파 확인
        recent = df.tail(lookback_days)
        
        for i in range(len(recent)):
            idx = recent.index[i]
            price = recent['Close'].iloc[i]
            high = recent['High'].iloc[i]
            
            # 해당 시점의 52주 최고가
            current_high_52w = high_52w.loc[:idx].iloc[-1]
            
            # 신고가 돌파 또는 1% 이내 근접
            if high >= current_high_52w * 0.99:
                # 거래량 확인
                avg_volume = df['Volume'].loc[:idx].tail(20).mean()
                current_volume = recent['Volume'].iloc[i]
                volume_ratio = current_volume / avg_volume if avg_volume > 0 else 0
                
                signals.append({
                    'date': idx.strftime('%Y-%m-%d'),
                    'price': price,
                    'high_52w': current_high_52w,
                    'breakout_pct': (high / current_high_52w - 1) * 100,
                    'volume_ratio': volume_ratio,
                    'type': '52W_HIGH_BREAKOUT'
                })
        
        return signals
    
    def check_oneil_signal(self, df: pd.DataFrame, lookback_days: int = 20) -> List[Dict]:
        """
        오닐 신호: 거래량 폭발 + 가격 상승
        50일 평균 거래량 2배 이상 + 5% 이상 상승
        """
        signals = []
        
        recent = df.tail(lookback_days + 50)  # 50일 평균 계산용 여유
        
        for i in range(50, len(recent)):
            idx = recent.index[i]
            price = recent['Close'].iloc[i]
            prev_price = recent['Close'].iloc[i-1]
            volume = recent['Volume'].iloc[i]
            
            # 50일 평균 거래량
            avg_volume = recent['Volume'].iloc[i-50:i].mean()
            volume_ratio = volume / avg_volume if avg_volume > 0 else 0
            
            # 가격 변화
            price_change = (price - prev_price) / prev_price * 100
            
            # 조건: 거래량 2배 이상 AND 3% 이상 상승
            if volume_ratio >= 2.0 and price_change >= 3:
                signals.append({
                    'date': idx.strftime('%Y-%m-%d'),
                    'price': price,
                    'price_change': price_change,
                    'volume_ratio': volume_ratio,
                    'type': 'VOLUME_SPIKE'
                })
        
        return signals
    
    def check_minervini_signal(self, df: pd.DataFrame, lookback_days: int = 20) -> List[Dict]:
        """
        미너비니 신호: VCP (변동성 축소 패턴)
        ATR이 점점 감소 + 가격 압축
        """
        signals = []
        
        if len(df) < 30:
            return signals
        
        # ATR 계산
        high_low = df['High'] - df['Low']
        high_close = (df['High'] - df['Close'].shift()).abs()
        low_close = (df['Low'] - df['Close'].shift()).abs()
        ranges = pd.concat([high_low, high_close, low_close], axis=1)
        true_range = ranges.max(axis=1)
        df['ATR'] = true_range.rolling(14).mean()
        df['ATR_Pct'] = df['ATR'] / df['Close'] * 100
        
        # 이동평균
        df['MA20'] = df['Close'].rolling(20).mean()
        df['MA50'] = df['Close'].rolling(50).mean()
        
        recent = df.tail(lookback_days + 30)
        
        for i in range(30, len(recent)):
            idx = recent.index[i]
            
            # 현재 구간 (10일)
            current = recent.iloc[i-10:i]
            # 이전 구간 (10일)
            prev = recent.iloc[i-20:i-10]
            # 그 이전 (10일)
            before = recent.iloc[i-30:i-20]
            
            # ATR 비교
            atr_current = current['ATR_Pct'].mean()
            atr_prev = prev['ATR_Pct'].mean()
            atr_before = before['ATR_Pct'].mean()
            
            # 변동성 축소: A > B > C
            volatility_contraction = (atr_before > atr_prev > atr_current) and (atr_current < atr_before * 0.8)
            
            # 가격 압축 (20일 고점-저점 범위)
            price_range = current['High'].max() - current['Low'].min()
            price_range_pct = price_range / current['Low'].min() * 100
            tight_range = price_range_pct < 12  # 12% 이내 압축
            
            # 추세 확인
            price = recent['Close'].iloc[i]
            ma20 = recent['MA20'].iloc[i]
            ma50 = recent['MA50'].iloc[i]
            bullish_trend = price > ma20 > ma50
            
            if volatility_contraction and tight_range and bullish_trend:
                signals.append({
                    'date': idx.strftime('%Y-%m-%d'),
                    'price': price,
                    'atr_contraction': f"{atr_before:.2f}→{atr_prev:.2f}→{atr_current:.2f}",
                    'price_range_pct': price_range_pct,
                    'type': 'VCP_PATTERN'
                })
        
        return signals
    
    def find_overlapping_signals(self, livermore: List[Dict], oneil: List[Dict], 
                                  minervini: List[Dict], window_days: int = 5) -> List[Dict]:
        """
        3가지 신호가 window_days 이내에 동시 발생한 경우 찾기
        """
        triple_signals = []
        
        for liv_sig in livermore:
            liv_date = datetime.strptime(liv_sig['date'], '%Y-%m-%d')
            
            # 오닐 신호와 날짜 비교
            for one_sig in oneil:
                one_date = datetime.strptime(one_sig['date'], '%Y-%m-%d')
                date_diff_one = abs((liv_date - one_date).days)
                
                if date_diff_one <= window_days:
                    # 미너비니 신호와도 비교
                    for min_sig in minervini:
                        min_date = datetime.strptime(min_sig['date'], '%Y-%m-%d')
                        date_diff_min = abs((liv_date - min_date).days)
                        
                        if date_diff_min <= window_days:
                            # 3가지 신호 모두 충족!
                            triple_signals.append({
                                'livermore': liv_sig,
                                'oneil': one_sig,
                                'minervini': min_sig,
                                'date_span': max(date_diff_one, date_diff_min),
                                'center_date': liv_sig['date']
                            })
        
        return triple_signals
    
    def scan_stock(self, symbol: str) -> Optional[Dict]:
        """개별 종목 스캔"""
        print(f"  {symbol} 분석 중...", end=' ')
        
        df = self.fetch_data(symbol)
        if df is None:
            print("❌ 데이터 없음")
            return None
        
        # 3가지 신호 확인
        livermore_signals = self.check_livermore_signal(df)
        oneil_signals = self.check_oneil_signal(df)
        minervini_signals = self.check_minervini_signal(df)
        
        # 신호 개수 출력
        print(f"L:{len(livermore_signals)} O:{len(oneil_signals)} M:{len(minervini_signals)}", end=' ')
        
        # 3가지 신호 동시 발생 확인
        triple_signals = self.find_overlapping_signals(
            livermore_signals, oneil_signals, minervini_signals
        )
        
        if triple_signals:
            print(f"✅ TRIPLE! ({len(triple_signals)}개)")
            
            # 최신 신호 선택
            latest = triple_signals[-1]
            
            return {
                'symbol': symbol,
                'name': self.name_map.get(symbol, symbol),
                'triple_signals': triple_signals,
                'latest_signal': latest,
                'signal_count': len(triple_signals),
                'livermore_count': len(livermore_signals),
                'oneil_count': len(oneil_signals),
                'minervini_count': len(minervini_signals),
                'current_price': df['Close'].iloc[-1]
            }
        else:
            print("❌")
            return None
    
    def scan_all(self):
        """전체 종목 스캔"""
        print("=" * 70)
        print("🎯 Triple Signal Scanner - 3가지 신호 동시 발생 종목 검색")
        print("조건: 리버모어(52주 신고가) + 오닐(거래량 폭발) + 미너비니(VCP)")
        print("=" * 70)
        print(f"\n대상 종목: {len(self.watchlist)}개")
        print("검색 기간: 최근 1년\n")
        
        for symbol in self.watchlist:
            result = self.scan_stock(symbol)
            if result:
                self.results.append(result)
        
        print("\n" + "=" * 70)
        print(f"✅ 스캔 완료! {len(self.results)}개 종목에서 3가지 신호 동시 발생")
        print("=" * 70)
    
    def generate_report(self):
        """리포트 생성"""
        if not self.results:
            print("\n⚠️ 3가지 신호가 동시에 발생한 종목이 없습니다.")
            return
        
        print("\n📊 상세 결과:\n")
        
        for i, result in enumerate(self.results, 1):
            print(f"{i}. {result['name']} ({result['symbol']})")
            print(f"   현재가: {result['current_price']:,.0f}원")
            print(f"   3중 신호 발생 횟수: {result['signal_count']}회")
            print(f"   - 리버모어 신호: {result['livermore_count']}회")
            print(f"   - 오닐 신호: {result['oneil_count']}회")
            print(f"   - 미너비니 신호: {result['minervini_count']}회")
            
            latest = result['latest_signal']
            print(f"\n   📅 최신 3중 신호 발생일: {latest['center_date']}")
            print(f"   - 52주 신고가 돌파: {latest['livermore']['price']:,.0f}원")
            print(f"   - 거래량 폭발: {latest['oneil']['volume_ratio']:.1f}x")
            print(f"   - VCP 패턴: {latest['minervini']['atr_contraction']}")
            print()
        
        # JSON 저장
        output = {
            'scan_date': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'criteria': 'Triple Signal: Livermore + O\'Neil + Minervini',
            'period': '1 year',
            'total_stocks': len(self.watchlist),
            'triple_signal_stocks': len(self.results),
            'results': self.results
        }
        
        with open(f'{BASE_PATH}/data/triple_signal_results.json', 'w', encoding='utf-8') as f:
            json.dump(output, f, indent=2, ensure_ascii=False)
        
        print(f"\n💾 결과 저장: data/triple_signal_results.json")


def main():
    scanner = TripleSignalScanner()
    scanner.scan_all()
    scanner.generate_report()


if __name__ == "__main__":
    main()
