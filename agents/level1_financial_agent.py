#!/usr/bin/env python3
"""
Level 1 Quarterly Financial Collector
분기별 재무정보 수집 에이전트

Features:
- DART 기반 분기별 재무제표 수집
- 1Q, 2Q, 3Q, 4Q (사업보고서)
- SQLite 저장
"""

import os
import json
import sqlite3
import pandas as pd
from datetime import datetime
from typing import List, Dict, Optional
import time

import OpenDartReader


class QuarterlyFinancialCollector:
    """분기별 재무정보 수집기"""
    
    def __init__(self, api_key: str = None, db_path: str = 'data/level1_quarterly.db'):
        self.api_key = api_key or os.environ.get('DART_API_KEY')
        if not self.api_key:
            raise ValueError("DART_API_KEY 필요")
        
        self.dart = OpenDartReader(self.api_key)
        self.db_path = db_path
        self.init_db()
    
    def init_db(self):
        """DB 초기화"""
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS quarterly_financial (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                corp_code TEXT,
                stock_code TEXT,
                corp_name TEXT,
                year TEXT,
                quarter TEXT,
                reprt_code TEXT,
                revenue INTEGER,
                operating_profit INTEGER,
                net_income INTEGER,
                total_assets INTEGER,
                total_liabilities INTEGER,
                total_equity INTEGER,
                status TEXT,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(stock_code, year, quarter)
            )
        ''')
        conn.commit()
        conn.close()
    
    def load_stocks(self) -> List[Dict]:
        """종목 리스트"""
        stocks = []
        try:
            with open('data/kospi_stocks.json', 'r') as f:
                data = json.load(f)
                for s in data.get('stocks', []):
                    stocks.append({'code': s['code'], 'name': s['name']})
        except: pass
        
        try:
            with open('data/kosdaq_stocks.json', 'r') as f:
                data = json.load(f)
                for s in data.get('stocks', []):
                    stocks.append({'code': s['code'], 'name': s['name']})
        except: pass
        
        return stocks
    
    def get_corp_code(self, stock_code: str) -> Optional[str]:
        """고유번호 조회"""
        try:
            return self.dart.find_corp_code(stock_code)
        except:
            return None
    
    def fetch_quarterly(self, stock: Dict, year: str, quarter: str) -> Optional[Dict]:
        """분기별 재무정보 수집"""
        code = stock['code']
        name = stock['name']
        
        # 분기 코드
        quarter_codes = {
            'Q1': '11013',  # 1분기
            'Q2': '11012',  # 반기
            'Q3': '11014',  # 3분기
            'Q4': '11011'   # 사업보고서
        }
        reprt_code = quarter_codes.get(quarter, '11011')
        
        try:
            corp_code = self.get_corp_code(code)
            if not corp_code:
                return {'stock_code': code, 'corp_name': name, 'year': year, 
                       'quarter': quarter, 'status': 'no_corp_code'}
            
            fs = self.dart.finstate(corp_code, year, reprt_code)
            if fs is None or len(fs) == 0:
                return {'corp_code': corp_code, 'stock_code': code, 'corp_name': name,
                       'year': year, 'quarter': quarter, 'status': 'no_data'}
            
            result = {
                'corp_code': corp_code,
                'stock_code': code,
                'corp_name': name,
                'year': year,
                'quarter': quarter,
                'reprt_code': reprt_code,
                'status': 'success'
            }
            
            # 주요 항목 추출
            def get_amount(keyword):
                row = fs[fs['account_nm'].str.contains(keyword, na=False)]
                if len(row) > 0:
                    val = str(row.iloc[0]['thstrm_amount']).replace(',', '').replace(' ', '')
                    if '(' in val: val = val.replace('(', '-').replace(')', '')
                    try: return int(float(val))
                    except: return 0
                return 0
            
            result['revenue'] = get_amount('매출액|수익')
            result['operating_profit'] = get_amount('영업이익')
            result['net_income'] = get_amount('당기순이익|순이익')
            result['total_assets'] = get_amount('자산총계|총자산')
            result['total_liabilities'] = get_amount('부채총계|총부채')
            result['total_equity'] = get_amount('자본총계|총자본')
            
            return result
            
        except Exception as e:
            return {'stock_code': code, 'corp_name': name, 'year': year, 
                   'quarter': quarter, 'status': 'error', 'error_msg': str(e)}
    
    def collect_year(self, year: str = '2024'):
        """특정 연도 전체 분기 수집"""
        stocks = self.load_stocks()
        quarters = ['Q1', 'Q2', 'Q3', 'Q4']
        
        print(f"\n🚀 Quarterly Financial Collection - {year}")
        print(f"   Stocks: {len(stocks)} x 4 quarters = {len(stocks)*4} tasks")
        
        total_results = []
        
        for quarter in quarters:
            print(f"\n📊 {quarter} 수집 중...")
            for i, stock in enumerate(stocks, 1):
                result = self.fetch_quarterly(stock, year, quarter)
                if result:
                    total_results.append(result)
                    
                    # DB 저장
                    conn = sqlite3.connect(self.db_path)
                    cursor = conn.cursor()
                    cursor.execute('''
                        INSERT OR REPLACE INTO quarterly_financial
                        (corp_code, stock_code, corp_name, year, quarter, reprt_code,
                         revenue, operating_profit, net_income, total_assets,
                         total_liabilities, total_equity, status)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ''', tuple(result.get(k) for k in ['corp_code', 'stock_code', 'corp_name', 
                        'year', 'quarter', 'reprt_code', 'revenue', 'operating_profit', 
                        'net_income', 'total_assets', 'total_liabilities', 'total_equity', 'status']))
                    conn.commit()
                    conn.close()
                
                if i % 100 == 0:
                    print(f"   {quarter}: {i}/{len(stocks)}")
                time.sleep(0.1)
        
        success = len([r for r in total_results if r.get('status') == 'success'])
        print(f"\n✅ Complete! Success: {success}/{len(total_results)}")
        return total_results


if __name__ == '__main__':
    import sys
    year = sys.argv[1] if len(sys.argv) > 1 else '2024'
    collector = QuarterlyFinancialCollector()
    collector.collect_year(year)
