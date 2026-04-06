#!/usr/bin/env python3
"""
Double Signal Scanner - 2가지 이상 신호 발생 종목 검색
리버모어 + 오닐 + 미너비니 중 2가지 이상 신호
"""

import yfinance as yf
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import List, Dict, Optional
import json

BASE_PATH = '/home/programs/kstock_analyzer'


class DoubleSignalScanner:
    """2가지 이상 신호 스캐너"""
    
    def __init__(self):
        self.watchlist = [
            '005930.KS', '000660.KS', '035420.KS', '005380.KS', '051910.KS',
            '035720.KS', '006400.KS', '068270.KS', '005490.KS', '028260.KS',
            '012450.KS', '055550.KS', '105560.KS', '138040.KS', '032830.KS',
            '015760.KS', '003670.KS', '009150.KS', '018260.KS', '033780.KS',
            # KOSDAQ 추가
            '247540.KS', '086520.KS', '196170.KS', '352820.KS', '259960.KS',
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
            '247540.KS': '에코프로비엠', '086520.KS': '에코프로',
            '196170.KS': '알테오젠', '352820.KS': '하이브',
            '259960.KS': '크래프톤',
        }
        
        self.results = []
    
    def fetch_data(self, symbol: str) -> Optional[pd.DataFrame]:
        """1년치 데이터 수집"""
        try:
            df = yf.download(symbol, period='1y', progress=False)
            if df.empty or len(df) < 100:
                return None
            df.columns = ['Close', 'High', 'Low', 'Open', 'Volume']
            return df.dropna()
        except:
            return None
    
    def check_signals(self, df: pd.DataFrame) -> Dict:
        """3가지 신호 모두 확인"""
        signals = {
            'livermore': [],
            'oneil': [],
            'minervini': []
        }
        
        # 리버모어: 52주 신고가 돌파
        if len(df) >= 252:
            high_52w = df['High'].rolling(252).max()
            recent = df.tail(60)  # 최근 60일
            
            for i in range(len(recent)):
                idx = recent.index[i]
                high = recent['High'].iloc[i]
                current_high = high_52w.loc[:idx].iloc[-1]
                
                if high >= current_high * 0.99:
                    signals['livermore'].append({
                        'date': idx.strftime('%Y-%m-%d'),
                        'price': recent['Close'].iloc[i]
                    })
        
        # 오닐: 거래량 폭발 + 상승
        if len(df) >= 60:
            for i in range(50, len(df)):
                idx = df.index[i]
                price = df['Close'].iloc[i]
                prev_price = df['Close'].iloc[i-1]
                volume = df['Volume'].iloc[i]
                avg_volume = df['Volume'].iloc[i-50:i].mean()
                
                volume_ratio = volume / avg_volume if avg_volume > 0 else 0
                price_change = (price - prev_price) / prev_price * 100
                
                if volume_ratio >= 2.0 and price_change >= 3:
                    signals['oneil'].append({
                        'date': idx.strftime('%Y-%m-%d'),
                        'price': price,
                        'volume_ratio': volume_ratio,
                        'change': price_change
                    })
        
        # 미너비니: VCP
        if len(df) >= 30:
            high_low = df['High'] - df['Low']
            high_close = (df['High'] - df['Close'].shift()).abs()
            low_close = (df['Low'] - df['Close'].shift()).abs()
            ranges = pd.concat([high_low, high_close, low_close], axis=1)
            true_range = ranges.max(axis=1)
            df['ATR'] = true_range.rolling(14).mean()
            df['ATR_Pct'] = df['ATR'] / df['Close'] * 100
            
            for i in range(30, len(df)):
                idx = df.index[i]
                
                current = df.iloc[i-10:i]
                prev = df.iloc[i-20:i-10]
                before = df.iloc[i-30:i-20]
                
                atr_current = current['ATR_Pct'].mean()
                atr_prev = prev['ATR_Pct'].mean()
                atr_before = before['ATR_Pct'].mean()
                
                if (atr_before > atr_prev > atr_current) and (atr_current < atr_before * 0.8):
                    price_range = current['High'].max() - current['Low'].min()
                    price_range_pct = price_range / current['Low'].min() * 100
                    
                    if price_range_pct < 15:
                        signals['minervini'].append({
                            'date': idx.strftime('%Y-%m-%d'),
                            'price': df['Close'].iloc[i],
                            'atr': f"{atr_before:.1f}→{atr_prev:.1f}→{atr_current:.1f}"
                        })
        
        return signals
    
    def scan_stock(self, symbol: str) -> Optional[Dict]:
        """개별 종목 스캔"""
        print(f"  {self.name_map.get(symbol, symbol)} ({symbol})...", end=' ')
        
        df = self.fetch_data(symbol)
        if df is None:
            print("❌")
            return None
        
        signals = self.check_signals(df)
        
        # 신호 개수 계산
        livermore_count = len(signals['livermore'])
        oneil_count = len(signals['oneil'])
        minervini_count = len(signals['minervini'])
        total_signals = sum([1 for s in [livermore_count, oneil_count, minervini_count] if s > 0])
        
        print(f"L:{livermore_count} O:{oneil_count} M:{minervini_count}", end=' ')
        
        # 2가지 이상 신호가 있는 경우만 반환
        if total_signals >= 2:
            print(f"✅ ({total_signals}가지)")
            
            # 최신 신호 날짜
            latest_dates = []
            if signals['livermore']:
                latest_dates.append(signals['livermore'][-1]['date'])
            if signals['oneil']:
                latest_dates.append(signals['oneil'][-1]['date'])
            if signals['minervini']:
                latest_dates.append(signals['minervini'][-1]['date'])
            
            return {
                'symbol': symbol,
                'name': self.name_map.get(symbol, symbol),
                'signals': signals,
                'signal_types': total_signals,
                'livermore_count': livermore_count,
                'oneil_count': oneil_count,
                'minervini_count': minervini_count,
                'current_price': df['Close'].iloc[-1],
                'latest_signal_dates': latest_dates
            }
        else:
            print("❌")
            return None
    
    def scan_all(self):
        """전체 종목 스캔"""
        print("=" * 70)
        print("🎯 Double Signal Scanner - 2가지 이상 신호 발생 종목 검색")
        print("=" * 70)
        print(f"\n대상 종목: {len(self.watchlist)}개")
        print("검색 기간: 최근 1년\n")
        
        for symbol in self.watchlist:
            result = self.scan_stock(symbol)
            if result:
                self.results.append(result)
        
        # 신호 많은 순 정렬
        self.results.sort(key=lambda x: x['signal_types'], reverse=True)
        
        print("\n" + "=" * 70)
        print(f"✅ 스캔 완료! {len(self.results)}개 종목에서 2가지 이상 신호 발생")
        print("=" * 70)
    
    def generate_report(self):
        """리포트 생성"""
        if not self.results:
            print("\n⚠️ 2가지 이상 신호가 발생한 종목이 없습니다.")
            return
        
        print("\n📊 상세 결과:\n")
        
        for i, result in enumerate(self.results, 1):
            print(f"{i}. {result['name']} ({result['symbol']})")
            print(f"   현재가: {result['current_price']:,.0f}원")
            print(f"   신호 종류: {result['signal_types']}가지")
            
            if result['livermore_count'] > 0:
                latest = result['signals']['livermore'][-1]
                print(f"   🎯 리버모어: {result['livermore_count']}회 (최신: {latest['date']}, {latest['price']:,.0f}원)")
            
            if result['oneil_count'] > 0:
                latest = result['signals']['oneil'][-1]
                print(f"   📈 오닐: {result['oneil_count']}회 (최신: {latest['date']}, {latest['change']:+.1f}%, 거래량{latest['volume_ratio']:.1f}x)")
            
            if result['minervini_count'] > 0:
                latest = result['signals']['minervini'][-1]
                print(f"   📉 미너비니: {result['minervini_count']}회 (최신: {latest['date']}, ATR: {latest['atr']})")
            
            print()
        
        # JSON 저장
        output = {
            'scan_date': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'criteria': 'Double Signal: 2+ of (Livermore, O\'Neil, Minervini)',
            'period': '1 year',
            'total_stocks': len(self.watchlist),
            'double_signal_stocks': len(self.results),
            'results': self.results
        }
        
        with open(f'{BASE_PATH}/data/double_signal_results.json', 'w', encoding='utf-8') as f:
            json.dump(output, f, indent=2, ensure_ascii=False)
        
        print(f"💾 결과 저장: data/double_signal_results.json")


def main():
    scanner = DoubleSignalScanner()
    scanner.scan_all()
    scanner.generate_report()


if __name__ == "__main__":
    main()
