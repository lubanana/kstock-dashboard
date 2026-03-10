#!/usr/bin/env python3
"""
Level 2 Macro Analysis Agent
매크로 분석 에이전트

Features:
- 환율, 금리, 유가 등 거시경제 지표 분석
- 시장 심리 지표 (VIX, 공포/탐욕 지수)
- 매크로 기반 섹터 조정
"""

import os
import json
import sqlite3
import pandas as pd
from datetime import datetime
from typing import Dict, List

import FinanceDataReader as fdr


class MacroAnalysisAgent:
    """매크로 분석 에이전트"""
    
    def __init__(self, db_path: str = 'data/level2_macro.db'):
        self.db_path = db_path
        self.init_db()
    
    def init_db(self):
        """DB 초기화"""
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS macro_analysis (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                date TEXT,
                kospi_index REAL,
                kospi_change REAL,
                kosdaq_index REAL,
                kosdaq_change REAL,
                usd_krw REAL,
                usd_change REAL,
                vix_index REAL,
                market_sentiment TEXT,
                macro_score INTEGER,
                risk_level TEXT,
                sector_adjustment TEXT,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(date)
            )
        ''')
        conn.commit()
        conn.close()
    
    def fetch_market_data(self) -> Dict:
        """시장 데이터 수집"""
        try:
            # KOSPI
            kospi = fdr.DataReader('KS11', datetime.now().strftime('%Y-%m-%d'))
            kospi_value = kospi['Close'].iloc[-1] if not kospi.empty else 0
            kospi_change = kospi['Change'].iloc[-1] if not kospi.empty else 0
            
            # KOSDAQ
            kosdaq = fdr.DataReader('KQ11', datetime.now().strftime('%Y-%m-%d'))
            kosdaq_value = kosdaq['Close'].iloc[-1] if not kosdaq.empty else 0
            kosdaq_change = kosdaq['Change'].iloc[-1] if not kosdaq.empty else 0
            
            # 원/달러 환율
            usdkrw = fdr.DataReader('USD/KRW', datetime.now().strftime('%Y-%m-%d'))
            usd_value = usdkrw['Close'].iloc[-1] if not usdkrw.empty else 0
            usd_change = ((usd_value - usdkrw['Close'].iloc[-2]) / usdkrw['Close'].iloc[-2] * 100) if len(usdkrw) > 1 else 0
            
            return {
                'kospi': kospi_value,
                'kospi_change': kospi_change,
                'kosdaq': kosdaq_value,
                'kosdaq_change': kosdaq_change,
                'usd_krw': usd_value,
                'usd_change': usd_change
            }
        except Exception as e:
            print(f"   ⚠️  데이터 수집 오류: {e}")
            return {}
    
    def analyze_macro(self, data: Dict) -> Dict:
        """매크로 분석"""
        score = 50  # 기본 점수
        adjustments = []
        
        # KOSPI 추세
        if data.get('kospi_change', 0) > 1:
            score += 10
            adjustments.append("코스피 강세(+)")
        elif data.get('kospi_change', 0) < -1:
            score -= 10
            adjustments.append("코스피 약세(-)")
        
        # 환율 (원화 강세 = 수출주 약세, 수입주 강세)
        if data.get('usd_change', 0) < -0.5:
            score += 5
            adjustments.append("원화 강세(+)")
        elif data.get('usd_change', 0) > 0.5:
            score -= 5
            adjustments.append("원화 약세(-)")
        
        # KOSDAQ vs KOSPI (성장주 vs 가치주)
        kosdaq_perf = data.get('kosdaq_change', 0)
        kospi_perf = data.get('kospi_change', 0)
        
        if kosdaq_perf > kospi_perf + 0.5:
            adjustments.append("성장주 선호")
        elif kospi_perf > kosdaq_perf + 0.5:
            adjustments.append("가치주 선호")
        
        # 리스크 레벨
        if score >= 60:
            risk = 'LOW'
            sentiment = 'RISK_ON'
        elif score >= 40:
            risk = 'MEDIUM'
            sentiment = 'NEUTRAL'
        else:
            risk = 'HIGH'
            sentiment = 'RISK_OFF'
        
        return {
            'score': max(0, min(100, score)),
            'risk_level': risk,
            'sentiment': sentiment,
            'adjustments': adjustments
        }
    
    def run_analysis(self):
        """분석 실행"""
        print("\n" + "="*70)
        print("🚀 Level 2-2: Macro Analysis")
        print("="*70)
        
        # 데이터 수집
        print("\n📊 시장 데이터 수집 중...")
        data = self.fetch_market_data()
        
        if not data:
            print("❌ 데이터 수집 실패")
            return None
        
        print(f"   KOSPI: {data.get('kospi', 0):,.0f} ({data.get('kospi_change', 0):+.2f}%)")
        print(f"   KOSDAQ: {data.get('kosdaq', 0):,.0f} ({data.get('kosdaq_change', 0):+.2f}%)")
        print(f"   USD/KRW: {data.get('usd_krw', 0):,.0f} ({data.get('usd_change', 0):+.2f}%)")
        
        # 분석
        analysis = self.analyze_macro(data)
        
        result = {
            'date': datetime.now().strftime('%Y-%m-%d'),
            'kospi_index': data.get('kospi', 0),
            'kospi_change': data.get('kospi_change', 0),
            'kosdaq_index': data.get('kosdaq', 0),
            'kosdaq_change': data.get('kosdaq_change', 0),
            'usd_krw': data.get('usd_krw', 0),
            'usd_change': data.get('usd_change', 0),
            'macro_score': analysis['score'],
            'risk_level': analysis['risk_level'],
            'market_sentiment': analysis['sentiment'],
            'adjustments': analysis['adjustments']
        }
        
        # DB 저장
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute('''
            INSERT OR REPLACE INTO macro_analysis
            (date, kospi_index, kospi_change, kosdaq_index, kosdaq_change,
             usd_krw, market_sentiment, macro_score, risk_level, sector_adjustment)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (result['date'], result['kospi_index'], result['kospi_change'],
              result['kosdaq_index'], result['kosdaq_change'], result['usd_krw'],
              result['market_sentiment'], result['macro_score'], result['risk_level'],
              ', '.join(analysis['adjustments'])))
        conn.commit()
        conn.close()
        
        print("\n📈 매크로 분석 결과:")
        print(f"   매크로 점수: {result['macro_score']}/100")
        print(f"   시장 심리: {result['market_sentiment']}")
        print(f"   리스크 레벨: {result['risk_level']}")
        print(f"   조정사항: {', '.join(analysis['adjustments'])}")
        
        # JSON 저장
        with open('data/level2_macro_analysis.json', 'w', encoding='utf-8') as f:
            json.dump(result, f, ensure_ascii=False, indent=2)
        
        print(f"\n✅ Macro Analysis Complete!")
        
        return result


if __name__ == '__main__':
    agent = MacroAnalysisAgent()
    agent.run_analysis()
