#!/usr/bin/env python3
"""
Mark Minervini SEPA Strategy Scanner
마크 미니버니 SEPA 전략 스캐너 (전체 종목 대상)

SEPA (Specific Entry Point Analysis) 기준:
1. Trend Template (추세 템플릿)
   - 주가 > 150일선 > 200일선
   - 150일선 > 200일선 (골든크로스)
   - 50일선 > 150일선 > 200일선
   
2. VCP (Volatility Contraction Pattern)
   - 변동성 수축 패턴
   - 거래량 감소 후 증가
   
3. consolidation Breakout
   - 박스권 돌파
   - 신고가 + 거래량 급증
"""

import os
import json
import sqlite3
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Tuple
import FinanceDataReader as fdr


class MinerviniScanner:
    """미니버니 SEPA 스캐너"""
    
    def __init__(self, db_path: str = 'data/minervini_signals.db'):
        self.db_path = db_path
        self.results = []
        self.init_db()
    
    def init_db(self):
        """DB 초기화"""
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS minervini_signals (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                code TEXT,
                name TEXT,
                market TEXT,
                date TEXT,
                current_price REAL,
                trend_template_pass INTEGER,
                stage TEXT,
                vcp_score REAL,
                consolidation_tightness REAL,
                volume_contraction REAL,
                relative_strength REAL,
                composite_score REAL,
                signal_type TEXT,
                entry_trigger TEXT,
                stop_loss REAL,
                target_price REAL,
                risk_reward_ratio REAL,
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
    
    def check_trend_template(self, df: pd.DataFrame) -> Tuple[bool, str]:
        """
        미니버니 추세 템플릿 확인
        
        기준:
        1. 주가 > 150일선
        2. 주가 > 200일선
        3. 150일선 > 200일선
        4. 50일선 > 150일선
        5. 200일선 상승 추세
        """
        close = df['Close']
        
        # 이동평균선
        ma50 = close.rolling(50).mean().iloc[-1]
        ma150 = close.rolling(150).mean().iloc[-1]
        ma200 = close.rolling(200).mean().iloc[-1]
        current = close.iloc[-1]
        
        # 조건 확인
        cond1 = current > ma150
        cond2 = current > ma200
        cond3 = ma150 > ma200
        cond4 = ma50 > ma150
        
        # 200일선 추세 (최근 20일)
        ma200_series = close.rolling(200).mean()
        ma200_trend = (ma200_series.iloc[-1] - ma200_series.iloc[-20]) / ma200_series.iloc[-20] * 100
        cond5 = ma200_trend > 0
        
        passed = sum([cond1, cond2, cond3, cond4, cond5])
        
        # Stage 결정
        if passed == 5:
            stage = "STAGE_2"  # 강력한 상승 추세
        elif passed >= 3:
            stage = "STAGE_1"  # 상승 초기
        elif passed >= 2:
            stage = "STAGE_3"  # 하띜거/횡보
        else:
            stage = "STAGE_4"  # 하띜세
        
        return passed >= 4, stage
    
    def calculate_vcp(self, df: pd.DataFrame, lookback: int = 20) -> float:
        """
        VCP (Volatility Contraction Pattern) 점수 계산
        
        변동성이 점차 수축하는 패턴 감지
        """
        close = df['Close']
        
        if len(close) < lookback * 3:
            return 0
        
        # 3개 구간으로 나누어 변동성 비교
        period1 = close.iloc[-lookback*3:-lookback*2]
        period2 = close.iloc[-lookback*2:-lookback]
        period3 = close.iloc[-lookback:]
        
        # 각 구간의 변동성 (표준편수/평균)
        vol1 = period1.std() / period1.mean() * 100
        vol2 = period2.std() / period2.mean() * 100
        vol3 = period3.std() / period3.mean() * 100
        
        # 변동성 수축 확인 (vol1 > vol2 > vol3)
        if vol1 > vol2 > vol3:
            # 수축 강도 (0-100)
            contraction = (1 - vol3/vol1) * 100
            return min(100, contraction)
        
        return 0
    
    def calculate_consolidation_tightness(self, df: pd.DataFrame, period: int = 20) -> float:
        """박스권 수축 정도 계산"""
        close = df['Close'].iloc[-period:]
        
        high = close.max()
        low = close.min()
        avg = close.mean()
        
        # 변동폭 비율
        range_pct = (high - low) / avg * 100
        
        # 수축 정도 (좁을수록 높은 점수)
        tightness = max(0, 100 - range_pct * 5)
        
        return tightness
    
    def calculate_volume_contraction(self, df: pd.DataFrame) -> float:
        """거래량 수축/확대 분석"""
        volume = df['Volume']
        
        # 최근 5일 vs 이전 20일 평균
        recent_vol = volume.iloc[-5:].mean()
        avg_vol = volume.iloc[-25:-5].mean()
        
        if avg_vol == 0:
            return 0
        
        ratio = recent_vol / avg_vol
        
        # 거래량 감소 후 급증이 이상적
        if ratio < 0.8:  # 수축
            return 50  # 관망
        elif ratio > 1.5:  # 확대
            return 100  # 돌파 신호
        else:
            return 30
    
    def calculate_relative_strength(self, df: pd.DataFrame) -> float:
        """상대강도 계산"""
        close = df['Close']
        
        # 3개월, 6개월 수익률
        if len(close) < 126:
            return 0
        
        ret_3m = (close.iloc[-1] - close.iloc[-63]) / close.iloc[-63] * 100
        ret_6m = (close.iloc[-1] - close.iloc[-126]) / close.iloc[-126] * 100
        
        # 가중 평균
        rs = (ret_3m * 0.4 + ret_6m * 0.6)
        
        # 0-100 스케일로 변환
        rs_score = min(100, max(0, 50 + rs))
        
        return rs_score
    
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
            
            # 1. 추세 템플릿 확인
            trend_pass, stage = self.check_trend_template(df)
            
            # 2. VCP 점수
            vcp_score = self.calculate_vcp(df)
            
            # 3. 박스권 수축
            tightness = self.calculate_consolidation_tightness(df)
            
            # 4. 거래량 분석
            vol_score = self.calculate_volume_contraction(df)
            
            # 5. 상대강도
            rs = self.calculate_relative_strength(df)
            
            # 종합 점수
            if trend_pass:
                base_score = 40
            else:
                base_score = 0
            
            composite = base_score + (vcp_score * 0.25) + (tightness * 0.15) + (vol_score * 0.10) + (rs * 0.10)
            
            # 신호 유형
            if trend_pass and vcp_score >= 60 and tightness >= 70:
                signal_type = "BREAKOUT"
                trigger = "VCP + Trend"
            elif trend_pass and vcp_score >= 40:
                signal_type = "WATCHLIST"
                trigger = "VCP forming"
            elif trend_pass:
                signal_type = "TREND"
                trigger = "Trend only"
            else:
                signal_type = "NEUTRAL"
                trigger = "No setup"
            
            # 진입/손절/목표
            current = df['Close'].iloc[-1]
            stop = current * 0.93
            target = current * 1.15
            rr = (target - current) / (current - stop)
            
            result = {
                'code': code,
                'name': name,
                'market': market,
                'date': datetime.now().strftime('%Y-%m-%d'),
                'current_price': current,
                'trend_template_pass': 1 if trend_pass else 0,
                'stage': stage,
                'vcp_score': vcp_score,
                'consolidation_tightness': tightness,
                'volume_contraction': vol_score,
                'relative_strength': rs,
                'composite_score': composite,
                'signal_type': signal_type,
                'entry_trigger': trigger,
                'stop_loss': stop,
                'target_price': target,
                'risk_reward_ratio': rr,
                'status': 'active'
            }
            
            return result
            
        except Exception as e:
            return None
    
    def scan_all(self, min_score: float = 60.0) -> List[Dict]:
        """전체 종목 스캔"""
        stocks = self.load_stock_list()
        total = len(stocks)
        
        print("\n" + "="*70)
        print("🚀 Mark Minervini SEPA Scanner")
        print(f"   Target: {total} stocks | Min Score: {min_score}")
        print("="*70)
        
        results = []
        
        for i, stock in enumerate(stocks, 1):
            result = self.scan_stock(stock)
            
            if result and result['composite_score'] >= min_score:
                results.append(result)
                print(f"   [{i}/{total}] ✅ {stock['name']}: {result['composite_score']:.1f}pts ({result['signal_type']})")
                
                # DB 저장
                conn = sqlite3.connect(self.db_path)
                cursor = conn.cursor()
                cursor.execute('''
                    INSERT OR REPLACE INTO minervini_signals
                    (code, name, market, date, current_price, trend_template_pass, stage,
                     vcp_score, consolidation_tightness, volume_contraction, relative_strength,
                     composite_score, signal_type, entry_trigger, stop_loss, target_price,
                     risk_reward_ratio, status)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', tuple(result.get(k) for k in ['code', 'name', 'market', 'date', 'current_price',
                    'trend_template_pass', 'stage', 'vcp_score', 'consolidation_tightness',
                    'volume_contraction', 'relative_strength', 'composite_score', 'signal_type',
                    'entry_trigger', 'stop_loss', 'target_price', 'risk_reward_ratio', 'status']))
                conn.commit()
                conn.close()
            
            if i % 100 == 0:
                print(f"   📊 Progress: {i}/{total} ({i/total*100:.1f}%) | Signals: {len(results)}")
        
        # 점수순 정렬
        results = sorted(results, key=lambda x: x['composite_score'], reverse=True)
        
        print("\n" + "="*70)
        print("✅ Minervini Scan Complete!")
        print(f"   Total Signals: {len(results)}")
        print(f"   Breakout (≥80): {len([r for r in results if r['composite_score'] >= 80])}")
        print(f"   Watchlist (60-79): {len([r for r in results if 60 <= r['composite_score'] < 80])}")
        print("="*70)
        
        # JSON 저장
        with open('data/minervini_scan_results.json', 'w', encoding='utf-8') as f:
            json.dump({
                'date': datetime.now().strftime('%Y-%m-%d'),
                'total_scanned': total,
                'signals_found': len(results),
                'stocks': results[:50]
            }, f, ensure_ascii=False, indent=2, default=str)
        
        return results
    
    def print_top10(self, results: List[Dict]):
        """상위 10개 출력"""
        print("\n🏆 TOP 10 Minervini SEPA Signals:")
        print("-" * 90)
        print(f"{'순위':<5}{'종목':<15}{'점수':<8}{'Stage':<10}{'VCP':<8}{'신호':<12}{'R/R':<8}")
        print("-" * 90)
        
        for i, r in enumerate(results[:10], 1):
            print(f"{i:<5}{r['name']:<15}{r['composite_score']:.1f<8}{r['stage']:<10}"
                  f"{r['vcp_score']:.0f<8}{r['signal_type']:<12}{r['risk_reward_ratio']:.1f<8}")


if __name__ == '__main__':
    import sys
    min_score = float(sys.argv[1]) if len(sys.argv) > 1 else 60.0
    
    scanner = MinerviniScanner()
    results = scanner.scan_all(min_score=min_score)
    scanner.print_top10(results)
