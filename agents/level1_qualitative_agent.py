#!/usr/bin/env python3
"""
Level 1 Qualitative Analysis Agent
정성적 분석 에이전트 (조걸 실행)

Features:
- 70점 이상 종목만 분석
- 기업 개황 정보 분석
- 산업/경쟁력 평가
- 정성적 점수 반영
"""

import os
import json
import sqlite3
from datetime import datetime
from typing import List, Dict, Optional

import OpenDartReader


class QualitativeAnalysisAgent:
    """정성적 분석 에이전트"""
    
    def __init__(self, api_key: str = None, db_path: str = 'data/level1_qualitative.db'):
        self.api_key = api_key or os.environ.get('DART_API_KEY')
        self.db_path = db_path
        self.init_db()
        
        if self.api_key:
            self.dart = OpenDartReader(self.api_key)
        else:
            self.dart = None
    
    def init_db(self):
        """DB 초기화"""
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS qualitative_analysis (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                code TEXT,
                name TEXT,
                date TEXT,
                corp_size TEXT,
                industry TEXT,
                biz_risk TEXT,
                audit_opinion TEXT,
                qual_score REAL,
                factors TEXT,
                status TEXT,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(code, date)
            )
        ''')
        conn.commit()
        conn.close()
    
    def get_corp_code(self, stock_code: str) -> Optional[str]:
        """고유번호 조회"""
        if not self.dart:
            return None
        try:
            return self.dart.find_corp_code(stock_code)
        except:
            return None
    
    def analyze_stock(self, code: str, name: str) -> Optional[Dict]:
        """단일 종목 정성적 분석"""
        try:
            if not self.dart:
                return {'code': code, 'name': name, 'status': 'no_api'}
            
            # 기업 개황 조회
            corp_info = self.dart.company(code)
            
            if not corp_info:
                return {'code': code, 'name': name, 'status': 'no_data'}
            
            # 정성적 평가
            score = 50.0  # 기본점수
            factors = []
            
            # 1. 기업 규모
            corp_size = '대기업' if '대기업' in str(corp_info.get('corp_cls', '')) else '중소기업'
            if corp_size == '대기업':
                score += 15
                factors.append('대기업(규모)')
            
            # 2. 업종 평가
            industry = corp_info.get('induty_code', '')
            growth_industries = ['264', '2612', '63120', '26410']  # 반도체, IT, 바이오 등
            if any(ind in industry for ind in growth_industries):
                score += 10
                factors.append('성장산업')
            
            # 3. 감사의견
            audit = str(corp_info.get('audt_opn', ''))
            if '적정' in audit or '합격' in audit:
                score += 10
                factors.append('적정감사')
            
            # 4. 사업 리스크
            risk = str(corp_info.get('biz_risk', ''))
            if '해당없음' in risk or '없음' in risk:
                score += 10
                factors.append('리스크낮음')
            
            return {
                'code': code,
                'name': name,
                'date': datetime.now().strftime('%Y-%m-%d'),
                'corp_size': corp_size,
                'industry': industry,
                'biz_risk': risk,
                'audit_opinion': audit,
                'qual_score': score,
                'factors': ', '.join(factors),
                'status': 'success'
            }
            
        except Exception as e:
            return {
                'code': code,
                'name': name,
                'date': datetime.now().strftime('%Y-%m-%d'),
                'status': 'error',
                'error_msg': str(e)
            }
    
    def analyze_high_score_stocks(self, min_score: float = 70.0):
        """고점수 종목만 정성적 분석"""
        # 가격 데이터에서 고점수 종목 로드
        price_db = 'data/level1_daily.db'
        if not os.path.exists(price_db):
            print("❌ 가격 데이터 DB 없음")
            return []
        
        conn = sqlite3.connect(price_db)
        cursor = conn.cursor()
        cursor.execute('''
            SELECT code, name, score FROM price_analysis 
            WHERE date = (SELECT MAX(date) FROM price_analysis)
            AND score >= ?
            ORDER BY score DESC
        ''', (min_score,))
        
        stocks = cursor.fetchall()
        conn.close()
        
        print(f"\n🚀 Qualitative Analysis Agent")
        print(f"   Target: {len(stocks)} stocks (score ≥ {min_score})")
        print("=" * 60)
        
        results = []
        for i, (code, name, score) in enumerate(stocks, 1):
            result = self.analyze_stock(code, name)
            if result:
                results.append(result)
                
                # DB 저장
                conn = sqlite3.connect(self.db_path)
                cursor = conn.cursor()
                cursor.execute('''
                    INSERT OR REPLACE INTO qualitative_analysis
                    (code, name, date, corp_size, industry, biz_risk, 
                     audit_opinion, qual_score, factors, status)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', tuple(result.get(k) for k in ['code', 'name', 'date', 'corp_size',
                    'industry', 'biz_risk', 'audit_opinion', 'qual_score', 'factors', 'status']))
                conn.commit()
                conn.close()
                
                status_emoji = "✅" if result['status'] == 'success' else "⚠️"
                print(f"   [{i}/{len(stocks)}] {status_emoji} {name}: 정성점수 {result.get('qual_score', 0):.1f}")
        
        print(f"\n✅ Qualitative Analysis Complete! ({len(results)} stocks)")
        return results


if __name__ == '__main__':
    import sys
    api_key = os.environ.get('DART_API_KEY')
    if not api_key:
        print("⚠️  DART_API_KEY 없음 - DART API 사용 불가")
    
    agent = QualitativeAnalysisAgent(api_key=api_key)
    agent.analyze_high_score_stocks(min_score=70.0)
