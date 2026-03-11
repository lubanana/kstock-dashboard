#!/usr/bin/env python3
"""
William O'Neil CANSLIM Strategy Scanner
오닐 CANSLIM 전략 스캐너 (전체 종목 대상)

CANSLIM 기준:
- C: Current Quarterly EPS (분기 EPS 성장)
- A: Annual Earnings Growth (연간 이익 성장)
- N: New Products/Management/Highs (신제품/신고가)
- S: Supply and Demand (공급/수급)
- L: Leader or Laggard (업종 내 리더)
- I: Institutional Sponsorship (기관 투자)
- M: Market Direction (시장 방향)

실제 적용 가능 지표 (가격 데이터 기반):
- 52주 신고가 돌파
- 거래량 급증 (평소의 150% 이상)
- 상대강도 (RS) 상위 10%
- 가격 추세 (20일 > 50일 > 200일 이평선)
- 변동성 확대 후 수축
"""

import os
import json
import sqlite3
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Tuple
import FinanceDataReader as fdr


class ONeilScanner:
    """오닐 CANSLIM 스캐너"""
    
    def __init__(self, db_path: str = 'data/oneil_signals.db'):
        self.db_path = db_path
        self.results = []
        self.init_db()
    
    def init_db(self):
        """DB 초기화"""
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS oneil_signals (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                code TEXT,
                name TEXT,
                market TEXT,
                date TEXT,
                current_price REAL,
                high_52w REAL,
                price_vs_high_pct REAL,
                volume_ratio REAL,
                rs_rating REAL,
                ma_alignment TEXT,
                trend_strength REAL,
                setup_quality INTEGER,
                signal_type TEXT,
                entry_price REAL,
                stop_loss REAL,
                target_price REAL,
                status TEXT,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(code, date)
            )
        ''')
        conn.commit()
        conn.close()
    
    def load_stock_list(self) -> List[Dict]:
        """전체 종목 리스트 로드"""
        stocks = []
        
        try:
            with open('data/kospi_stocks.json', 'r', encoding='utf-8') as f:
                data = json.load(f)
                for s in data.get('stocks', []):
                    stocks.append({'code': s['code'], 'name': s['name'], 'market': 'KOSPI'})
        except Exception as e:
            print(f"   ⚠️  KOSPI 로드 오류: {e}")
        
        try:
            with open('data/kosdaq_stocks.json', 'r', encoding='utf-8') as f:
                data = json.load(f)
                for s in data.get('stocks', []):
                    stocks.append({'code': s['code'], 'name': s['name'], 'market': 'KOSDAQ'})
        except Exception as e:
            print(f"   ⚠️  KOSDAQ 로드 오류: {e}")
        
        print(f"📋 총 {len(stocks)}개 종목 로드")
        return stocks
    
    def fetch_price_data(self, code: str, days: int = 300) -> Optional[pd.DataFrame]:
        """가격 데이터 수집"""
        try:
            end = datetime.now()
            start = end - timedelta(days=days)
            df = fdr.DataReader(code, start.strftime('%Y-%m-%d'), end.strftime('%Y-%m-%d'))
            
            if df is None or len(df) < 200:
                return None
            
            return df
        except Exception as e:
            return None
    
    def calculate_indicators(self, df: pd.DataFrame) -> Dict:
        """오닐 전략 지표 계산"""
        close = df['Close']
        volume = df['Volume']
        
        # 1. 52주 최고가 대비 위치 (N - New Highs)
        high_52w = close.rolling(252).max().iloc[-1]
        current = close.iloc[-1]
        pct_from_high = (current / high_52w) * 100
        
        # 2. 거래량 급증 (S - Supply/Demand)
        avg_volume = volume.rolling(20).mean().iloc[-1]
        current_volume = volume.iloc[-1]
        volume_ratio = (current_volume / avg_volume) if avg_volume > 0 else 0
        
        # 3. 이동평균선 정렬 (M - Market Direction, 추세 확인)
        ma20 = close.rolling(20).mean().iloc[-1]
        ma50 = close.rolling(50).mean().iloc[-1]
        ma200 = close.rolling(200).mean().iloc[-1]
        
        # 정렬 확인 (20 > 50 > 200)
        alignment = "BULLISH" if current > ma20 > ma50 > ma200 else \
                   "NEUTRAL" if current > ma50 > ma200 else "BEARISH"
        
        # 4. 추세 강도 (RS Rating 대안)
        returns_3m = (current - close.iloc[-63]) / close.iloc[-63] * 100 if len(close) >= 63 else 0
        returns_6m = (current - close.iloc[-126]) / close.iloc[-126] * 100 if len(close) >= 126 else 0
        trend_strength = (returns_3m + returns_6m) / 2
        
        # 5. 변동성 수축 (VCP - Volatility Contraction Pattern)
        atr = self._calculate_atr(df)
        atr_ratio = (atr / close.iloc[-1]) * 100
        
        return {
            'current_price': current,
            'high_52w': high_52w,
            'pct_from_high': pct_from_high,
            'volume_ratio': volume_ratio,
            'ma20': ma20,
            'ma50': ma50,
            'ma200': ma200,
            'ma_alignment': alignment,
            'trend_strength': trend_strength,
            'atr_ratio': atr_ratio,
            'returns_3m': returns_3m,
            'returns_6m': returns_6m
        }
    
    def _calculate_atr(self, df: pd.DataFrame, period: int = 14) -> float:
        """ATR (Average True Range) 계산"""
        high = df['High']
        low = df['Low']
        close = df['Close']
        
        tr1 = high - low
        tr2 = abs(high - close.shift())
        tr3 = abs(low - close.shift())
        
        tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
        atr = tr.rolling(period).mean().iloc[-1]
        
        return atr
    
    def evaluate_setup(self, indicators: Dict) -> Tuple[int, str, Dict]:
        """
        오닐 셋업 품질 평가 (0-100)
        
        Returns:
            (점수, 신호유형, 추가정보)
        """
        score = 0
        checks = []
        
        # 1. 52주 최고가 근접 (New Highs) - 25점
        if indicators['pct_from_high'] >= 95:
            score += 25
            checks.append("52주 최고가 근접")
        elif indicators['pct_from_high'] >= 90:
            score += 15
            checks.append("52주 최고가 10% 이내")
        
        # 2. 거래량 급증 (Supply/Demand) - 25점
        if indicators['volume_ratio'] >= 2.0:
            score += 25
            checks.append("거래량 200% 급증")
        elif indicators['volume_ratio'] >= 1.5:
            score += 15
            checks.append("거래량 150% 증가")
        
        # 3. 이동평균선 정렬 (Trend) - 25점
        if indicators['ma_alignment'] == "BULLISH":
            score += 25
            checks.append("완벽한 추세 정렬")
        elif indicators['ma_alignment'] == "NEUTRAL":
            score += 10
        
        # 4. 추세 강도 (RS Rating 대안) - 25점
        if indicators['trend_strength'] >= 20:
            score += 25
            checks.append("강력한 상대강도")
        elif indicators['trend_strength'] >= 10:
            score += 15
            checks.append("양호한 상대강도")
        
        # 신호 유형 결정
        if score >= 80:
            signal_type = "STRONG_BUY"
        elif score >= 60:
            signal_type = "BUY"
        elif score >= 40:
            signal_type = "WATCH"
        else:
            signal_type = "NEUTRAL"
        
        # 진입/손절/목표가 계산
        entry = indicators['current_price']
        stop_loss = entry * 0.93  # 7% 손절
        target = entry * 1.20     # 20% 목표
        
        info = {
            'checks': checks,
            'entry_price': entry,
            'stop_loss': stop_loss,
            'target_price': target
        }
        
        return score, signal_type, info
    
    def scan_stock(self, stock: Dict) -> Optional[Dict]:
        """단일 종목 스캔"""
        code = stock['code']
        name = stock['name']
        market = stock['market']
        
        try:
            # 데이터 수집
            df = self.fetch_price_data(code)
            if df is None:
                return None
            
            # 지표 계산
            indicators = self.calculate_indicators(df)
            
            # 셋업 평가
            score, signal_type, info = self.evaluate_setup(indicators)
            
            # 결과 생성
            result = {
                'code': code,
                'name': name,
                'market': market,
                'date': datetime.now().strftime('%Y-%m-%d'),
                'current_price': indicators['current_price'],
                'high_52w': indicators['high_52w'],
                'price_vs_high_pct': indicators['pct_from_high'],
                'volume_ratio': indicators['volume_ratio'],
                'rs_rating': indicators['trend_strength'],
                'ma_alignment': indicators['ma_alignment'],
                'trend_strength': indicators['trend_strength'],
                'setup_quality': score,
                'signal_type': signal_type,
                'entry_price': info['entry_price'],
                'stop_loss': info['stop_loss'],
                'target_price': info['target_price'],
                'status': 'active',
                'checks': info['checks']
            }
            
            return result
            
        except Exception as e:
            return None
    
    def scan_all(self, min_score: int = 60) -> List[Dict]:
        """
        전체 종목 스캔
        
        Args:
            min_score: 최소 셋업 품질 점수 (기본 60)
        """
        stocks = self.load_stock_list()
        total = len(stocks)
        
        print("\n" + "="*70)
        print("🚀 William O'Neil CANSLIM Scanner")
        print(f"   Target: {total} stocks | Min Score: {min_score}")
        print("="*70)
        
        results = []
        
        for i, stock in enumerate(stocks, 1):
            result = self.scan_stock(stock)
            
            if result and result['setup_quality'] >= min_score:
                results.append(result)
                print(f"   [{i}/{total}] ✅ {stock['name']}: {result['setup_quality']}pts ({result['signal_type']})")
                
                # DB 저장
                conn = sqlite3.connect(self.db_path)
                cursor = conn.cursor()
                cursor.execute('''
                    INSERT OR REPLACE INTO oneil_signals
                    (code, name, market, date, current_price, high_52w, price_vs_high_pct,
                     volume_ratio, rs_rating, ma_alignment, trend_strength, setup_quality,
                     signal_type, entry_price, stop_loss, target_price, status)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', tuple(result.get(k) for k in ['code', 'name', 'market', 'date', 'current_price',
                    'high_52w', 'price_vs_high_pct', 'volume_ratio', 'rs_rating', 'ma_alignment',
                    'trend_strength', 'setup_quality', 'signal_type', 'entry_price', 'stop_loss',
                    'target_price', 'status']))
                conn.commit()
                conn.close()
            
            if i % 100 == 0:
                print(f"   📊 Progress: {i}/{total} ({i/total*100:.1f}%) | Signals: {len(results)}")
        
        # 점수순 정렬
        results = sorted(results, key=lambda x: x['setup_quality'], reverse=True)
        
        print("\n" + "="*70)
        print("✅ O'Neil Scan Complete!")
        print(f"   Total Signals: {len(results)}")
        print(f"   Strong Buy (≥80): {len([r for r in results if r['setup_quality'] >= 80])}")
        print(f"   Buy (60-79): {len([r for r in results if 60 <= r['setup_quality'] < 80])}")
        print("="*70)
        
        # JSON 저장
        with open('data/oneil_scan_results.json', 'w', encoding='utf-8') as f:
            json.dump({
                'date': datetime.now().strftime('%Y-%m-%d'),
                'total_scanned': total,
                'signals_found': len(results),
                'stocks': results[:50]  # 상위 50개만
            }, f, ensure_ascii=False, indent=2, default=str)
        
        return results
    
    def print_top10(self, results: List[Dict]):
        """상위 10개 출력"""
        print("\n🏆 TOP 10 O'Neil Signals:")
        print("-" * 80)
        print(f"{'순위':<5}{'종목':<15}{'점수':<8}{'신호':<12}{'현재가':<12}{'목표가':<12}")
        print("-" * 80)
        
        for i, r in enumerate(results[:10], 1):
            print(f"{i:<5}{r['name']:<15}{r['setup_quality']:<8}{r['signal_type']:<12}"
                  f"{r['current_price']:,<12.0f}{r['target_price']:,<12.0f}")


if __name__ == '__main__':
    import sys
    min_score = int(sys.argv[1]) if len(sys.argv) > 1 else 60
    
    scanner = ONeilScanner()
    results = scanner.scan_all(min_score=min_score)
    scanner.print_top10(results)
