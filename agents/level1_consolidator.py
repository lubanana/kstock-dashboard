#!/usr/bin/env python3
"""
Level 1 Consolidator
Level 1 에이전트 결과 취합 및 고점수 종목 필터링

Features:
- 가격 데이터 (Price Agent) + 재무정보 (Financial Agent) 통합
- 가중 점수 계산
- 일정 점수(≥70) 이상 종목만 추출
- JSON/CSV/DB 저장
"""

import os
import json
import sqlite3
import pandas as pd
from datetime import datetime
from typing import List, Dict, Optional


class Level1Consolidator:
    """Level 1 결과 취합기"""
    
    def __init__(self, 
                 price_db: str = 'data/level1_daily.db',
                 financial_db: str = 'data/level1_quarterly.db',
                 output_db: str = 'data/level1_consolidated.db',
                 score_threshold: float = 70.0):
        self.price_db = price_db
        self.financial_db = financial_db
        self.output_db = output_db
        self.score_threshold = score_threshold
        self.init_db()
    
    def init_db(self):
        """출력 DB 초기화"""
        os.makedirs(os.path.dirname(self.output_db), exist_ok=True)
        conn = sqlite3.connect(self.output_db)
        cursor = conn.cursor()
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS consolidated_level1 (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                code TEXT,
                name TEXT,
                market TEXT,
                date TEXT,
                price_score REAL,
                financial_score REAL,
                total_score REAL,
                price_close REAL,
                price_change_pct REAL,
                price_ma5 REAL,
                price_ma20 REAL,
                price_rsi REAL,
                price_macd REAL,
                fin_revenue INTEGER,
                fin_operating_profit INTEGER,
                fin_net_income INTEGER,
                fin_total_assets INTEGER,
                fin_roe REAL,
                recommendation TEXT,
                rank INTEGER,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(code, date)
            )
        ''')
        conn.commit()
        conn.close()
    
    def load_price_data(self, date: str = None) -> pd.DataFrame:
        """가격 데이터 로드"""
        if not os.path.exists(self.price_db):
            return pd.DataFrame()
        
        conn = sqlite3.connect(self.price_db)
        if date:
            query = f"SELECT * FROM price_analysis WHERE date='{date}' AND status='success'"
        else:
            query = "SELECT * FROM price_analysis WHERE status='success' ORDER BY date DESC"
        
        df = pd.read_sql(query, conn)
        conn.close()
        return df
    
    def load_financial_data(self, year: str = '2024') -> pd.DataFrame:
        """재무 데이터 로드 (기존 DB 구조에 맞게 수정)"""
        if not os.path.exists(self.financial_db):
            return pd.DataFrame()
        
        conn = sqlite3.connect(self.financial_db)
        # 기존 dart_financial.db 구조: financial_data 테이블
        query = f"""
            SELECT * FROM financial_data 
            WHERE year='{year}' AND status='success'
        """
        df = pd.read_sql(query, conn)
        conn.close()
        
        # stock_code 컬럼명 통일
        if 'stock_code' not in df.columns and 'code' in df.columns:
            df = df.rename(columns={'code': 'stock_code'})
        
        return df
    
    def calculate_financial_score(self, row: pd.Series) -> float:
        """재무 점수 계산 (0-100)"""
        score = 50.0  # 기본점수
        
        # 매출 성장률 (가상 계산 - 작년 대비)
        revenue = row.get('revenue', 0)
        if revenue > 1000000000000:  # 1조 이상
            score += 15
        elif revenue > 100000000000:  # 1천억 이상
            score += 10
        
        # 영업이익
        op = row.get('operating_profit', 0)
        if op > 0:
            score += 15  # 흑자
        
        # 당기순이익
        net = row.get('net_income', 0)
        if net > 0:
            score += 10  # 순이익 흑자
        
        # ROE 계산
        equity = row.get('total_equity', 0)
        if equity > 0:
            roe = (net / equity) * 100
            if roe > 10: score += 10
            elif roe > 5: score += 5
        
        return min(score, 100)
    
    def consolidate(self, date: str = None) -> List[Dict]:
        """데이터 취합"""
        today = date or datetime.now().strftime('%Y-%m-%d')
        
        print(f"\n🚀 Level 1 Consolidation - {today}")
        print("=" * 60)
        
        # 1. 가격 데이터 로드
        print("\n📊 Loading price data...")
        price_df = self.load_price_data(today)
        print(f"   Loaded: {len(price_df)} records")
        
        # 2. 재무 데이터 로드
        print("\n📊 Loading financial data...")
        fin_df = self.load_financial_data('2024')
        print(f"   Loaded: {len(fin_df)} records")
        
        # 3. 데이터 병합
        print("\n🔗 Merging data...")
        
        # 가격 데이터에서 최신 시간대만 선택
        if not price_df.empty and 'time_slot' in price_df.columns:
            latest_slot = price_df['time_slot'].iloc[0]
            price_df = price_df[price_df['time_slot'] == latest_slot]
        
        results = []
        
        for _, price_row in price_df.iterrows():
            code = price_row.get('code')
            name = price_row.get('name')
            market = price_row.get('market')
            
            # 가격 점수
            price_score = price_row.get('score', 0)
            
            # 재무 데이터 찾기
            fin_row = fin_df[fin_df['stock_code'] == code]
            fin_score = 0
            fin_data = {}
            
            if not fin_row.empty:
                fin_score = self.calculate_financial_score(fin_row.iloc[0])
                fin_data = {
                    'revenue': fin_row.iloc[0].get('revenue', 0),
                    'operating_profit': fin_row.iloc[0].get('operating_profit', 0),
                    'net_income': fin_row.iloc[0].get('net_income', 0),
                    'total_assets': fin_row.iloc[0].get('total_assets', 0),
                }
                # ROE 계산
                equity = fin_row.iloc[0].get('total_equity', 0)
                net = fin_data['net_income']
                fin_data['roe'] = (net / equity * 100) if equity > 0 else 0
            
            # 총점 계산 (가격 60%, 재무 40%)
            total_score = (price_score * 0.6) + (fin_score * 0.4)
            
            result = {
                'code': code,
                'name': name,
                'market': market,
                'date': today,
                'price_score': price_score,
                'financial_score': fin_score,
                'total_score': total_score,
                'price_close': price_row.get('close', 0),
                'price_change_pct': price_row.get('change_pct', 0),
                'price_ma5': price_row.get('ma5', 0),
                'price_ma20': price_row.get('ma20', 0),
                'price_rsi': price_row.get('rsi', 0),
                'price_macd': price_row.get('macd', 0),
                'fin_revenue': fin_data.get('revenue', 0),
                'fin_operating_profit': fin_data.get('operating_profit', 0),
                'fin_net_income': fin_data.get('net_income', 0),
                'fin_total_assets': fin_data.get('total_assets', 0),
                'fin_roe': fin_data.get('roe', 0),
                'recommendation': 'STRONG_BUY' if total_score >= 80 else 'BUY' if total_score >= 70 else 'HOLD' if total_score >= 50 else 'SELL'
            }
            
            results.append(result)
        
        # 점수순 정렬
        results = sorted(results, key=lambda x: x['total_score'], reverse=True)
        
        # 순위 부여
        for i, r in enumerate(results, 1):
            r['rank'] = i
        
        # 임계값 필터링
        filtered = [r for r in results if r['total_score'] >= self.score_threshold]
        
        print(f"\n✅ Consolidation Complete!")
        print(f"   Total processed: {len(results)}")
        print(f"   High score (≥{self.score_threshold}): {len(filtered)}")
        
        # DB 저장
        self._save_to_db(results)
        
        # JSON 저장
        self._export_json(filtered, today)
        
        return filtered
    
    def _save_to_db(self, results: List[Dict]):
        """DB 저장"""
        conn = sqlite3.connect(self.output_db)
        cursor = conn.cursor()
        
        for r in results:
            cursor.execute('''
                INSERT OR REPLACE INTO consolidated_level1
                (code, name, market, date, price_score, financial_score, total_score,
                 price_close, price_change_pct, price_ma5, price_ma20, price_rsi, price_macd,
                 fin_revenue, fin_operating_profit, fin_net_income, fin_total_assets, fin_roe,
                 recommendation, rank)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', tuple(r.get(k) for k in ['code', 'name', 'market', 'date', 'price_score', 
                'financial_score', 'total_score', 'price_close', 'price_change_pct', 'price_ma5',
                'price_ma20', 'price_rsi', 'price_macd', 'fin_revenue', 'fin_operating_profit',
                'fin_net_income', 'fin_total_assets', 'fin_roe', 'recommendation', 'rank']))
        
        conn.commit()
        conn.close()
    
    def _export_json(self, results: List[Dict], date: str):
        """JSON 낳출 (모든 타입 변환)"""
        import json
        
        def convert_value(v):
            """값을 JSON 직렬화 가능한 형태로 변환"""
            if v is None:
                return None
            elif isinstance(v, (int, float, str, bool)):
                return v
            elif hasattr(v, 'item'):  # numpy 타입
                return v.item()
            elif isinstance(v, bytes):
                return v.decode('utf-8', errors='ignore')
            elif isinstance(v, (list, tuple)):
                return [convert_value(x) for x in v]
            elif isinstance(v, dict):
                return {k: convert_value(val) for k, val in v.items()}
            else:
                return str(v)
        
        # 모든 결과 정리
        clean_results = []
        for r in results[:100]:
            clean_r = {k: convert_value(v) for k, v in r.items()}
            clean_results.append(clean_r)
        
        output = {
            'date': date,
            'threshold': float(self.score_threshold),
            'total_count': int(len(results)),
            'stocks': clean_results
        }
        
        filepath = f"data/level1_top100_{date}.json"
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(output, f, indent=2, ensure_ascii=False)
        
        print(f"💾 Saved: {filepath}")
    
    def print_top10(self, results: List[Dict]):
        """상위 10개 출력"""
        print("\n🏆 Top 10 Level 1 Stocks:")
        print("-" * 80)
        print(f"{'Rank':<6}{'Code':<10}{'Name':<20}{'Price':<10}{'Fin':<10}{'Total':<10}{'Rec':<10}")
        print("-" * 80)
        
        for r in results[:10]:
            print(f"{r['rank']:<6}{r['code']:<10}{r['name'][:18]:<20}{r['price_score']:<10.1f}{r['financial_score']:<10.1f}{r['total_score']:<10.1f}{r['recommendation']:<10}")


if __name__ == '__main__':
    import sys
    threshold = float(sys.argv[1]) if len(sys.argv) > 1 else 70.0
    
    consolidator = Level1Consolidator(score_threshold=threshold)
    results = consolidator.consolidate()
    consolidator.print_top10(results)
