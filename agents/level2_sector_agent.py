#!/usr/bin/env python3
"""
Level 2 Sector Analysis Agent
섹터 분석 에이전트

Features:
- Level 1 선정 종목의 섹터별 그룹화
- 섹터별 평균 점수, 추세 분석
- 섹터 오버워이트/언더워이트 판단
"""

import os
import json
import sqlite3
import pandas as pd
from datetime import datetime
from typing import List, Dict, Optional, Tuple
from collections import defaultdict


class SectorAnalysisAgent:
    """섹터 분석 에이전트"""
    
    # 섹터 분류 매핑 (간소화된 버전)
    SECTOR_MAP = {
        # 반도체/전자
        '005930': '반도체', '000660': '반도체', '005380': '자동차', '207940': '바이오',
        '068270': '바이오', '051910': '화학', '028260': '건설', '006400': '반도체',
        '035420': 'IT/플랫폼', '035720': 'IT/플랫폼', '012330': '자동차부품',
        '105560': '금융', '055550': '금융', '086790': '금융', '003550': '화학/전자',
        # KOSDAQ 주요 종목
        '182400': '바이오', '195940': '바이오', '151910': '바이오', '048260': 'IT',
        '086520': '반도체장비', '095340': 'IT', '141080': '게임/엔터', '078340': 'IT',
    }
    
    # 업종별 섹터 매핑 (이름 기반)
    SECTOR_KEYWORDS = {
        '반도체': ['반도체', '전자', '디스플레이', '반도체장비', '하이닉스', '삼성전자', 'LG전자'],
        '바이오/제약': ['바이오', '제약', '헬스케어', '셀트리온', '삼성바이오', '유한양행'],
        'IT/플랫폼': ['IT', '플랫폼', '소프트웨어', '네이버', '카카오', '게임'],
        '자동차': ['자동차', '모빌리티', '타이어', '현대차', '기아'],
        '화학/소재': ['화학', '소재', '철강', '비철금속', 'POSCO', 'LG화학'],
        '건설/인프라': ['건설', '인프라', '토목', '플랜트', '현대건설', '삼성엔지니어링'],
        '금융': ['은행', '증권', '보험', '금융', '카드', '신한', 'KB'],
        '에너지': ['에너지', '전력', '발전', '풍력', '태양광', '두산에너빌리티'],
        '유통/서비스': ['유통', '백화점', '마트', '항공', '물류', '호텔'],
        '기계/장비': ['기계', '장비', '로봇', '자동화', '공작기계'],
    }
    
    def __init__(self, db_path: str = 'data/level2_sector.db'):
        self.db_path = db_path
        self.init_db()
    
    def init_db(self):
        """DB 초기화"""
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS sector_analysis (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                sector TEXT,
                date TEXT,
                stock_count INTEGER,
                avg_score REAL,
                avg_price_score REAL,
                avg_financial_score REAL,
                top_stock TEXT,
                sector_momentum TEXT,
                recommendation TEXT,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(sector, date)
            )
        ''')
        conn.commit()
        conn.close()
    
    def load_level1_data(self, min_score: float = 70.0) -> pd.DataFrame:
        """Level 1 데이터 로드"""
        conn = sqlite3.connect('data/level1_final.db')
        query = f'''
            SELECT * FROM consolidated_level1 
            WHERE total_score >= {min_score}
            ORDER BY total_score DESC
        '''
        df = pd.read_sql(query, conn)
        conn.close()
        return df
    
    def classify_sector(self, code: str, name: str) -> str:
        """종목 섹터 분류"""
        # 코드 기반 매핑
        if code in self.SECTOR_MAP:
            return self.SECTOR_MAP[code]
        
        # 이름 기반 키워드 매칭
        name_lower = name.lower()
        for sector, keywords in self.SECTOR_KEYWORDS.items():
            for keyword in keywords:
                if keyword in name or keyword in name_lower:
                    return sector
        
        return '기타'
    
    def analyze_sectors(self, df: pd.DataFrame) -> List[Dict]:
        """섹터별 분석"""
        # 섹터 분류
        df['sector'] = df.apply(lambda x: self.classify_sector(x['code'], x['name']), axis=1)
        
        results = []
        
        for sector in df['sector'].unique():
            sector_df = df[df['sector'] == sector]
            
            if len(sector_df) == 0:
                continue
            
            # 섹터 통계
            avg_score = sector_df['total_score'].mean()
            avg_price = sector_df['price_score'].mean()
            avg_fin = sector_df['financial_score'].mean()
            
            # 상위 종목
            top_stock = sector_df.iloc[0]
            
            # 모멘텀 판단
            if avg_score >= 90:
                momentum = 'STRONG'
                rec = 'OVERWEIGHT'
            elif avg_score >= 80:
                momentum = 'POSITIVE'
                rec = 'OVERWEIGHT'
            elif avg_score >= 70:
                momentum = 'NEUTRAL'
                rec = 'MARKET_WEIGHT'
            else:
                momentum = 'WEAK'
                rec = 'UNDERWEIGHT'
            
            result = {
                'sector': sector,
                'date': datetime.now().strftime('%Y-%m-%d'),
                'stock_count': len(sector_df),
                'avg_score': avg_score,
                'avg_price_score': avg_price,
                'avg_financial_score': avg_fin,
                'top_stock': f"{top_stock['name']}({top_stock['code']})",
                'top_score': top_stock['total_score'],
                'sector_momentum': momentum,
                'recommendation': rec,
                'stocks': sector_df[['code', 'name', 'total_score']].to_dict('records')
            }
            
            results.append(result)
        
        # 평균 점수순 정렬
        results = sorted(results, key=lambda x: x['avg_score'], reverse=True)
        
        return results
    
    def run_analysis(self, min_score: float = 70.0):
        """분석 실행"""
        print("\n" + "="*70)
        print("🚀 Level 2-1: Sector Analysis")
        print("="*70)
        
        # Level 1 데이터 로드
        df = self.load_level1_data(min_score)
        print(f"\n📊 Level 1 선정 종목: {len(df)}개")
        
        # 섹터 분석
        results = self.analyze_sectors(df)
        
        print(f"\n📈 섹터 분류: {len(results)}개 섹터")
        
        # DB 저장
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        for r in results:
            cursor.execute('''
                INSERT OR REPLACE INTO sector_analysis
                (sector, date, stock_count, avg_score, avg_price_score, avg_financial_score,
                 top_stock, sector_momentum, recommendation)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (r['sector'], r['date'], r['stock_count'], r['avg_score'],
                  r['avg_price_score'], r['avg_financial_score'], r['top_stock'],
                  r['sector_momentum'], r['recommendation']))
        
        conn.commit()
        conn.close()
        
        # 결과 출력
        print("\n🏆 섹터별 분석 결과:")
        print("-" * 70)
        print(f"{'순위':<5}{'섹터':<15}{'종목수':<8}{'평균점수':<10}{'모멘텀':<12}{'추천':<10}")
        print("-" * 70)
        
        for i, r in enumerate(results[:10], 1):
            print(f"{i:<5}{r['sector']:<15}{r['stock_count']:<8}{r['avg_score']:<10.1f}"
                  f"{r['sector_momentum']:<12}{r['recommendation']:<10}")
        
        # JSON 저장
        with open('data/level2_sector_analysis.json', 'w', encoding='utf-8') as f:
            json.dump({'date': datetime.now().strftime('%Y-%m-%d'), 'sectors': results}, 
                     f, ensure_ascii=False, indent=2, default=str)
        
        print(f"\n✅ Sector Analysis Complete!")
        print(f"   파일: data/level2_sector_analysis.json")
        
        return results


if __name__ == '__main__':
    agent = SectorAnalysisAgent()
    agent.run_analysis(min_score=70.0)
