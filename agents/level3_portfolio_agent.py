#!/usr/bin/env python3
"""
Level 3 Portfolio Manager Agent
포트폴리오 구성 에이전트

Features:
- Level 1 + Level 2 결과 취합
- 종합 점수 계산 (L1 50% + L2 Sector 30% + L2 Macro 20%)
- Long/Short 포지션 구성
- 리스크 관리 (최대 10개 종목)
"""

import os
import json
import sqlite3
import pandas as pd
from datetime import datetime
from typing import List, Dict, Optional


class PortfolioManagerAgent:
    """포트폴리오 관리 에이전트"""
    
    def __init__(self, db_path: str = 'data/level3_portfolio.db'):
        self.db_path = db_path
        self.init_db()
    
    def init_db(self):
        """DB 초기화"""
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS portfolio (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                date TEXT,
                code TEXT,
                name TEXT,
                sector TEXT,
                market TEXT,
                level1_score REAL,
                level2_score REAL,
                final_score REAL,
                position TEXT,
                allocation_pct REAL,
                recommendation TEXT,
                rank INTEGER,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS portfolio_summary (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                date TEXT,
                total_stocks INTEGER,
                long_count INTEGER,
                short_count INTEGER,
                cash_pct REAL,
                avg_score REAL,
                market_outlook TEXT,
                risk_level TEXT,
                UNIQUE(date)
            )
        ''')
        conn.commit()
        conn.close()
    
    def load_level1_data(self) -> pd.DataFrame:
        """Level 1 데이터 로드"""
        conn = sqlite3.connect('data/level1_final.db')
        df = pd.read_sql('SELECT * FROM consolidated_level1 WHERE total_score >= 70', conn)
        conn.close()
        return df
    
    def load_level2_sector(self) -> Dict:
        """Level 2 섹터 데이터 로드"""
        try:
            with open('data/level2_sector_analysis.json', 'r') as f:
                data = json.load(f)
                return {s['sector']: s for s in data.get('sectors', [])}
        except:
            return {}
    
    def calculate_final_score(self, l1_score: float, sector: str, sector_data: Dict) -> float:
        """최종 점수 계산"""
        # 기본 가중치
        l1_weight = 0.5
        l2_sector_weight = 0.3
        l2_macro_weight = 0.2
        
        # Level 1 점수 (50%)
        score_l1 = l1_score * l1_weight
        
        # Level 2 섹터 점수 (30%)
        sector_info = sector_data.get(sector, {})
        sector_score = sector_info.get('avg_score', 70) if sector_info else 70
        score_sector = sector_score * l2_sector_weight
        
        # Level 2 매크로 점수 (20%) - 기본값 사용
        macro_score = 70  # 중립적 매크로 환경 가정
        score_macro = macro_score * l2_macro_weight
        
        return score_l1 + score_sector + score_macro
    
    def build_portfolio(self, df: pd.DataFrame, sector_data: Dict) -> List[Dict]:
        """포트폴리오 구성"""
        results = []
        
        for _, row in df.iterrows():
            # 섹터 분류 (간단화)
            sector = self._classify_sector(row['code'], row['name'])
            
            # 최종 점수 계산
            final_score = self.calculate_final_score(
                row['total_score'], 
                sector, 
                sector_data
            )
            
            # 포지션 결정
            if final_score >= 85:
                position = 'LONG'
                allocation = 10.0  # 최대 10%
                rec = 'STRONG_BUY'
            elif final_score >= 75:
                position = 'LONG'
                allocation = 7.0
                rec = 'BUY'
            elif final_score < 50:
                position = 'SHORT'
                allocation = 5.0
                rec = 'SELL'
            else:
                position = 'NONE'
                allocation = 0.0
                rec = 'HOLD'
            
            result = {
                'date': datetime.now().strftime('%Y-%m-%d'),
                'code': row['code'],
                'name': row['name'],
                'sector': sector,
                'market': row['market'],
                'level1_score': row['total_score'],
                'level2_score': sector_data.get(sector, {}).get('avg_score', 70),
                'final_score': final_score,
                'position': position,
                'allocation_pct': allocation,
                'recommendation': rec
            }
            
            results.append(result)
        
        # 최종 점수순 정렬
        results = sorted(results, key=lambda x: x['final_score'], reverse=True)
        
        # 순위 부여
        for i, r in enumerate(results, 1):
            r['rank'] = i
        
        return results
    
    def _classify_sector(self, code: str, name: str) -> str:
        """섹터 분류"""
        keywords = {
            '반도체': ['반도체', '전자', '하이닉스', '삼성전자'],
            '바이오/제약': ['바이오', '제약', '셀트리온', '헬스케어'],
            '금융': ['은행', '증권', '보험', '금융'],
            '자동차': ['자동차', '타이어', '현대차', '기아'],
            '에너지': ['에너지', '전력', '발전'],
            '건설': ['건설', '인프라', '토목'],
        }
        
        for sector, words in keywords.items():
            for word in words:
                if word in name:
                    return sector
        return '기타'
    
    def run_portfolio_construction(self):
        """포트폴리오 구성 실행"""
        print("\n" + "="*70)
        print("🚀 Level 3: Portfolio Manager")
        print("="*70)
        
        # 데이터 로드
        print("\n📊 Level 1 + Level 2 데이터 로드 중...")
        df_l1 = self.load_level1_data()
        sector_data = self.load_level2_sector()
        
        print(f"   Level 1: {len(df_l1)}개 종목")
        print(f"   Level 2: {len(sector_data)}개 섹터")
        
        # 포트폴리오 구성
        print("\n📈 포트폴리오 구성 중...")
        portfolio = self.build_portfolio(df_l1, sector_data)
        
        # Long/Short 분리
        longs = [p for p in portfolio if p['position'] == 'LONG']
        shorts = [p for p in portfolio if p['position'] == 'SHORT']
        
        # 상위 10개 Long만 선택
        top_longs = longs[:10]
        
        # 비중 재조정 (총 100%)
        total_alloc = sum(p['allocation_pct'] for p in top_longs)
        if total_alloc > 0:
            for p in top_longs:
                p['allocation_pct'] = (p['allocation_pct'] / total_alloc) * 100
        
        # DB 저장
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        for p in top_longs + shorts[:5]:  # 상위 10 Long + 5 Short
            cursor.execute('''
                INSERT OR REPLACE INTO portfolio
                (date, code, name, sector, market, level1_score, level2_score,
                 final_score, position, allocation_pct, recommendation, rank)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (p['date'], p['code'], p['name'], p['sector'], p['market'],
                  p['level1_score'], p['level2_score'], p['final_score'],
                  p['position'], p['allocation_pct'], p['recommendation'], p['rank']))
        
        # 요약 저장
        summary = {
            'date': datetime.now().strftime('%Y-%m-%d'),
            'total_stocks': len(top_longs) + len(shorts[:5]),
            'long_count': len(top_longs),
            'short_count': len(shorts[:5]),
            'cash_pct': max(0, 100 - sum(p['allocation_pct'] for p in top_longs)),
            'avg_score': sum(p['final_score'] for p in top_longs) / len(top_longs) if top_longs else 0,
            'market_outlook': 'NEUTRAL',
            'risk_level': 'MEDIUM'
        }
        
        cursor.execute('''
            INSERT OR REPLACE INTO portfolio_summary
            (date, total_stocks, long_count, short_count, cash_pct, avg_score, market_outlook, risk_level)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (summary['date'], summary['total_stocks'], summary['long_count'],
              summary['short_count'], summary['cash_pct'], summary['avg_score'],
              summary['market_outlook'], summary['risk_level']))
        
        conn.commit()
        conn.close()
        
        # 결과 출력
        print("\n🏆 포트폴리오 구성 결과:")
        print("-" * 70)
        print(f"{'순위':<5}{'종목':<15}{'섹터':<12}{'최종점수':<10}{'포지션':<10}{'비중':<8}")
        print("-" * 70)
        
        for p in top_longs[:10]:
            print(f"{p['rank']:<5}{p['name']:<15}{p['sector']:<12}"
                  f"{p['final_score']:<10.1f}{p['position']:<10}{p['allocation_pct']:.1f}%")
        
        print("\n📊 포트폴리오 요약:")
        print(f"   Long: {summary['long_count']}개 종목")
        print(f"   Cash: {summary['cash_pct']:.1f}%")
        print(f"   평균점수: {summary['avg_score']:.1f}")
        
        # JSON 저장
        output = {
            'date': summary['date'],
            'summary': summary,
            'long_positions': top_longs[:10],
            'short_positions': shorts[:5]
        }
        
        with open('data/level3_portfolio.json', 'w', encoding='utf-8') as f:
            json.dump(output, f, ensure_ascii=False, indent=2, default=str)
        
        print(f"\n✅ Portfolio Construction Complete!")
        print(f"   파일: data/level3_portfolio.json")
        
        return top_longs[:10]


if __name__ == '__main__':
    agent = PortfolioManagerAgent()
    agent.run_portfolio_construction()
