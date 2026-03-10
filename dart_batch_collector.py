#!/usr/bin/env python3
"""
DART Financial Data Batch Collector
DART 기반 3년치 재무정보 수집기 (2021-2023)

Features:
- 3,286개 종목 전체 처리
- 3년치 재무정보 (2021, 2022, 2023)
- SQLite 저장
- 진행률 표시 + 오류 복구
- Rate limiting (DART API 제한 고려)
"""

import os
import json
import sqlite3
import time
from datetime import datetime
from typing import List, Dict, Optional
import pandas as pd

import OpenDartReader


class DartBatchCollector:
    """DART 배치 재무정보 수집기"""
    
    def __init__(self, api_key: str = None, db_path: str = 'data/dart_financial.db'):
        """
        초기화
        
        Args:
            api_key: DART API 키
            db_path: SQLite DB 경로
        """
        if api_key is None:
            api_key = os.environ.get('DART_API_KEY')
        
        if not api_key:
            raise ValueError("DART_API_KEY 환경변수가 필요합니다!")
        
        self.api_key = api_key
        self.dart = OpenDartReader(api_key)
        self.db_path = db_path
        self.results = []
        self.errors = []
        
        self.init_db()
        print(f"✅ DART API initialized")
    
    def init_db(self):
        """SQLite DB 초기화"""
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS financial_data (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                corp_code TEXT,
                stock_code TEXT,
                corp_name TEXT,
                year TEXT,
                reprt_code TEXT,
                revenue INTEGER,
                operating_profit INTEGER,
                net_income INTEGER,
                total_assets INTEGER,
                total_liabilities INTEGER,
                total_equity INTEGER,
                status TEXT,
                error_msg TEXT,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(corp_code, year, reprt_code)
            )
        ''')
        
        conn.commit()
        conn.close()
        print(f"✅ DB initialized: {self.db_path}")
    
    def load_stock_list(self) -> List[Dict]:
        """종목 리스트 로드"""
        stocks = []
        
        # KOSPI
        try:
            with open('data/kospi_stocks.json', 'r', encoding='utf-8') as f:
                data = json.load(f)
                for s in data.get('stocks', []):
                    stocks.append({
                        'code': s['code'],
                        'name': s['name'],
                        'market': 'KOSPI'
                    })
        except Exception as e:
            print(f"   ⚠️  KOSPI load error: {e}")
        
        # KOSDAQ
        try:
            with open('data/kosdaq_stocks.json', 'r', encoding='utf-8') as f:
                data = json.load(f)
                for s in data.get('stocks', []):
                    stocks.append({
                        'code': s['code'],
                        'name': s['name'],
                        'market': 'KOSDAQ'
                    })
        except Exception as e:
            print(f"   ⚠️  KOSDAQ load error: {e}")
        
        print(f"📋 Loaded {len(stocks)} stocks")
        return stocks
    
    def get_corp_code(self, stock_code: str) -> Optional[str]:
        """종목코드로 고유번호 조회"""
        try:
            return self.dart.find_corp_code(stock_code)
        except:
            return None
    
    def fetch_financial(self, stock: Dict, year: str, reprt_code: str = '11011') -> Optional[Dict]:
        """
        단일 종목-연도 재무정보 수집
        
        Args:
            stock: {'code': '005930', 'name': '삼성전자', 'market': 'KOSPI'}
            year: '2023'
            reprt_code: '11011' (사업보고서)
        """
        stock_code = stock['code']
        name = stock['name']
        
        try:
            # 고유번호 조회
            corp_code = self.get_corp_code(stock_code)
            if not corp_code:
                return {
                    'stock_code': stock_code,
                    'corp_name': name,
                    'year': year,
                    'status': 'no_corp_code'
                }
            
            # 재무제표 조회
            fs = self.dart.finstate(corp_code, year, reprt_code)
            
            if fs is None or len(fs) == 0:
                return {
                    'corp_code': corp_code,
                    'stock_code': stock_code,
                    'corp_name': name,
                    'year': year,
                    'status': 'no_data'
                }
            
            # 주요 항목 추출
            result = {
                'corp_code': corp_code,
                'stock_code': stock_code,
                'corp_name': name,
                'year': year,
                'reprt_code': reprt_code,
                'status': 'success'
            }
            
            # 매출액
            revenue_row = fs[fs['account_nm'].str.contains('매출액|수익', na=False, regex=True)]
            if len(revenue_row) > 0:
                result['revenue'] = self._parse_amount(revenue_row.iloc[0]['thstrm_amount'])
            else:
                result['revenue'] = 0
            
            # 영업이익
            op_row = fs[fs['account_nm'].str.contains('영업이익', na=False)]
            if len(op_row) > 0:
                result['operating_profit'] = self._parse_amount(op_row.iloc[0]['thstrm_amount'])
            else:
                result['operating_profit'] = 0
            
            # 당기순이익
            net_row = fs[fs['account_nm'].str.contains('당기순이익|순이익', na=False)]
            if len(net_row) > 0:
                result['net_income'] = self._parse_amount(net_row.iloc[0]['thstrm_amount'])
            else:
                result['net_income'] = 0
            
            # 총자산
            asset_row = fs[fs['account_nm'].str.contains('자산총계|총자산', na=False)]
            if len(asset_row) > 0:
                result['total_assets'] = self._parse_amount(asset_row.iloc[0]['thstrm_amount'])
            else:
                result['total_assets'] = 0
            
            # 총부채
            liab_row = fs[fs['account_nm'].str.contains('부채총계|총부채', na=False)]
            if len(liab_row) > 0:
                result['total_liabilities'] = self._parse_amount(liab_row.iloc[0]['thstrm_amount'])
            else:
                result['total_liabilities'] = 0
            
            # 총자본
            equity_row = fs[fs['account_nm'].str.contains('자본총계|총자본', na=False)]
            if len(equity_row) > 0:
                result['total_equity'] = self._parse_amount(equity_row.iloc[0]['thstrm_amount'])
            else:
                result['total_equity'] = 0
            
            return result
            
        except Exception as e:
            self.errors.append({
                'stock_code': stock_code,
                'year': year,
                'error': str(e)
            })
            return {
                'stock_code': stock_code,
                'corp_name': name,
                'year': year,
                'status': 'error',
                'error_msg': str(e)
            }
    
    def _parse_amount(self, amount_str) -> int:
        """금액 문자열을 정수로 변환"""
        if pd.isna(amount_str):
            return 0
        
        amount_str = str(amount_str).replace(',', '').replace(' ', '')
        
        if '(' in amount_str and ')' in amount_str:
            amount_str = amount_str.replace('(', '-').replace(')', '')
        
        try:
            return int(float(amount_str))
        except:
            return 0
    
    def save_to_db(self, result: Dict):
        """결과를 SQLite에 저장"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            cursor.execute('''
                INSERT OR REPLACE INTO financial_data
                (corp_code, stock_code, corp_name, year, reprt_code,
                 revenue, operating_profit, net_income, total_assets, 
                 total_liabilities, total_equity, status, error_msg)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                result.get('corp_code'),
                result.get('stock_code'),
                result.get('corp_name'),
                result.get('year'),
                result.get('reprt_code', '11011'),
                result.get('revenue', 0),
                result.get('operating_profit', 0),
                result.get('net_income', 0),
                result.get('total_assets', 0),
                result.get('total_liabilities', 0),
                result.get('total_equity', 0),
                result.get('status'),
                result.get('error_msg')
            ))
            
            conn.commit()
        except Exception as e:
            print(f"   ❌ DB save error: {e}")
        finally:
            conn.close()
    
    def process_all(self, years: List[str] = None, batch_size: int = 50):
        """
        전체 종목-연도 처리
        
        Args:
            years: 수집할 연도 리스트 ['2021', '2022', '2023']
            batch_size: 배치 크기
        """
        if years is None:
            years = ['2021', '2022', '2023']
        
        stocks = self.load_stock_list()
        total_stocks = len(stocks)
        total_years = len(years)
        total_tasks = total_stocks * total_years
        
        print(f"\n{'=' * 70}")
        print(f"🚀 DART Financial Data Collection")
        print(f"   Stocks: {total_stocks} | Years: {years}")
        print(f"   Total tasks: {total_tasks}")
        print(f"{'=' * 70}\n")
        
        completed = 0
        success_count = 0
        start_time = time.time()
        
        for year in years:
            print(f"\n📅 Year: {year}")
            print(f"{'-' * 70}")
            
            for i, stock in enumerate(stocks, 1):
                # 진행률
                completed += 1
                progress = completed / total_tasks * 100
                elapsed = time.time() - start_time
                rate = completed / elapsed if elapsed > 0 else 0
                eta = (total_tasks - completed) / rate if rate > 0 else 0
                
                # 데이터 수집
                result = self.fetch_financial(stock, year)
                
                if result:
                    self.results.append(result)
                    self.save_to_db(result)
                    
                    if result['status'] == 'success':
                        success_count += 1
                        revenue = result.get('revenue', 0)
                        print(f"   [{i}/{total_stocks}] ✅ {stock['name']}: {revenue:,.0f}원")
                    else:
                        print(f"   [{i}/{total_stocks}] ⚠️  {stock['name']}: {result['status']}")
                
                # 진행률 출력 (100개마다)
                if i % 100 == 0 or i == total_stocks:
                    print(f"   📊 Total: {completed}/{total_tasks} ({progress:.1f}%) | "
                          f"ETA: {eta/60:.1f}min")
                
                # Rate limiting (DART API: 초당 20건 제한 고려)
                time.sleep(0.1)
        
        # 최종 통계
        total_time = time.time() - start_time
        print(f"\n{'=' * 70}")
        print(f"✅ Complete!")
        print(f"   Total: {completed}")
        print(f"   Success: {success_count}")
        print(f"   Errors: {len(self.errors)}")
        print(f"   Time: {total_time/60:.1f} minutes")
        print(f"   DB: {self.db_path}")
        print(f"{'=' * 70}\n")
        
        return {
            'total': completed,
            'success': success_count,
            'errors': len(self.errors),
            'time_seconds': total_time
        }
    
    def export_to_json(self, filepath: str = 'data/dart_financial_results.json'):
        """JSON으로 낳출"""
        output = {
            'date': datetime.now().isoformat(),
            'total': len(self.results),
            'data_source': 'dart_opendart',
            'results': [r for r in self.results if r.get('status') == 'success']
        }
        
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(output, f, indent=2, ensure_ascii=False)
        
        print(f"💾 Exported to: {filepath}")


def main():
    """메인 실행"""
    api_key = os.environ.get('DART_API_KEY')
    
    if not api_key:
        print("❌ DART_API_KEY 환경변수가 필요합니다!")
        return
    
    collector = DartBatchCollector(api_key)
    
    # 3년치 수집 (2021, 2022, 2023)
    stats = collector.process_all(years=['2021', '2022', '2023'])
    
    # JSON 저장
    collector.export_to_json()
    
    # 샘플 출력
    print("\n📊 Sample Data (삼성전자):")
    samples = [r for r in collector.results 
               if r.get('stock_code') == '005930' and r.get('status') == 'success']
    for s in sorted(samples, key=lambda x: x.get('year', '')):
        print(f"   {s['year']}: 매출 {s.get('revenue', 0):,.0f}원, "
              f"영업익 {s.get('operating_profit', 0):,.0f}원")


if __name__ == '__main__':
    main()
