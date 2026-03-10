#!/usr/bin/env python3
"""
DART 2024 Financial Data Collector
2024년 재무정보 추가 수집
"""

import os
import json
import sqlite3
import time
from datetime import datetime
from typing import List, Dict, Optional
import pandas as pd

import OpenDartReader


class Dart2024Collector:
    """DART 2024 재무정보 수집기"""
    
    def __init__(self, api_key: str = None, db_path: str = 'data/dart_financial.db'):
        if api_key is None:
            api_key = os.environ.get('DART_API_KEY')
        
        if not api_key:
            raise ValueError("DART_API_KEY 환경변수가 필요합니다!")
        
        self.api_key = api_key
        self.dart = OpenDartReader(api_key)
        self.db_path = db_path
        self.results = []
        self.errors = []
        
        print(f"✅ DART API initialized")
    
    def load_stock_list(self) -> List[Dict]:
        """종목 리스트 로드"""
        stocks = []
        
        try:
            with open('data/kospi_stocks.json', 'r', encoding='utf-8') as f:
                data = json.load(f)
                for s in data.get('stocks', []):
                    stocks.append({'code': s['code'], 'name': s['name'], 'market': 'KOSPI'})
        except Exception as e:
            print(f"   ⚠️  KOSPI load error: {e}")
        
        try:
            with open('data/kosdaq_stocks.json', 'r', encoding='utf-8') as f:
                data = json.load(f)
                for s in data.get('stocks', []):
                    stocks.append({'code': s['code'], 'name': s['name'], 'market': 'KOSDAQ'})
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
    
    def fetch_financial(self, stock: Dict, year: str = '2024', reprt_code: str = '11011') -> Optional[Dict]:
        """단일 종목 재무정보 수집"""
        stock_code = stock['code']
        name = stock['name']
        
        try:
            corp_code = self.get_corp_code(stock_code)
            if not corp_code:
                return {'stock_code': stock_code, 'corp_name': name, 'year': year, 'status': 'no_corp_code'}
            
            fs = self.dart.finstate(corp_code, year, reprt_code)
            
            if fs is None or len(fs) == 0:
                return {'corp_code': corp_code, 'stock_code': stock_code, 'corp_name': name, 'year': year, 'status': 'no_data'}
            
            result = {
                'corp_code': corp_code,
                'stock_code': stock_code,
                'corp_name': name,
                'year': year,
                'reprt_code': reprt_code,
                'status': 'success'
            }
            
            # 주요 항목 추출
            revenue_row = fs[fs['account_nm'].str.contains('매출액|수익', na=False, regex=True)]
            result['revenue'] = self._parse_amount(revenue_row.iloc[0]['thstrm_amount']) if len(revenue_row) > 0 else 0
            
            op_row = fs[fs['account_nm'].str.contains('영업이익', na=False)]
            result['operating_profit'] = self._parse_amount(op_row.iloc[0]['thstrm_amount']) if len(op_row) > 0 else 0
            
            net_row = fs[fs['account_nm'].str.contains('당기순이익|순이익', na=False)]
            result['net_income'] = self._parse_amount(net_row.iloc[0]['thstrm_amount']) if len(net_row) > 0 else 0
            
            asset_row = fs[fs['account_nm'].str.contains('자산총계|총자산', na=False)]
            result['total_assets'] = self._parse_amount(asset_row.iloc[0]['thstrm_amount']) if len(asset_row) > 0 else 0
            
            liab_row = fs[fs['account_nm'].str.contains('부채총계|총부채', na=False)]
            result['total_liabilities'] = self._parse_amount(liab_row.iloc[0]['thstrm_amount']) if len(liab_row) > 0 else 0
            
            equity_row = fs[fs['account_nm'].str.contains('자본총계|총자본', na=False)]
            result['total_equity'] = self._parse_amount(equity_row.iloc[0]['thstrm_amount']) if len(equity_row) > 0 else 0
            
            return result
            
        except Exception as e:
            self.errors.append({'stock_code': stock_code, 'year': year, 'error': str(e)})
            return {'stock_code': stock_code, 'corp_name': name, 'year': year, 'status': 'error', 'error_msg': str(e)}
    
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
        """결과를 SQLite에 저장 (기존 DB에 추가)"""
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
                result.get('corp_code'), result.get('stock_code'), result.get('corp_name'),
                result.get('year'), result.get('reprt_code', '11011'),
                result.get('revenue', 0), result.get('operating_profit', 0), result.get('net_income', 0),
                result.get('total_assets', 0), result.get('total_liabilities', 0), result.get('total_equity', 0),
                result.get('status'), result.get('error_msg')
            ))
            conn.commit()
        except Exception as e:
            print(f"   ❌ DB save error: {e}")
        finally:
            conn.close()
    
    def process_2024(self):
        """2024년 전체 종목 처리"""
        stocks = self.load_stock_list()
        total = len(stocks)
        year = '2024'
        
        print(f"\n{'=' * 70}")
        print(f"🚀 DART 2024 Financial Data Collection")
        print(f"   Stocks: {total} | Year: {year}")
        print(f"{'=' * 70}\n")
        
        success_count = 0
        start_time = time.time()
        
        for i, stock in enumerate(stocks, 1):
            result = self.fetch_financial(stock, year)
            
            if result:
                self.results.append(result)
                self.save_to_db(result)
                
                if result['status'] == 'success':
                    success_count += 1
                    revenue = result.get('revenue', 0)
                    print(f"   [{i}/{total}] ✅ {stock['name']}: {revenue:,.0f}원")
                else:
                    print(f"   [{i}/{total}] ⚠️  {stock['name']}: {result['status']}")
            
            # 진행률 출력 (100개마다)
            if i % 100 == 0 or i == total:
                elapsed = time.time() - start_time
                rate = i / elapsed if elapsed > 0 else 0
                eta = (total - i) / rate if rate > 0 else 0
                progress = i / total * 100
                print(f"   📊 Progress: {i}/{total} ({progress:.1f}%) | ETA: {eta/60:.1f}min")
            
            time.sleep(0.1)  # Rate limiting
        
        total_time = time.time() - start_time
        print(f"\n{'=' * 70}")
        print(f"✅ Complete!")
        print(f"   Total: {total}")
        print(f"   Success: {success_count}")
        print(f"   Errors: {len(self.errors)}")
        print(f"   Time: {total_time/60:.1f} minutes")
        print(f"{'=' * 70}\n")
        
        return {'total': total, 'success': success_count, 'errors': len(self.errors), 'time_seconds': total_time}
    
    def export_to_json(self, filepath: str = 'data/dart_2024_results.json'):
        """JSON으로 낳출"""
        output = {
            'date': datetime.now().isoformat(),
            'year': '2024',
            'total': len(self.results),
            'results': [r for r in self.results if r.get('status') == 'success']
        }
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(output, f, indent=2, ensure_ascii=False)
        print(f"💾 Exported to: {filepath}")


def main():
    api_key = os.environ.get('DART_API_KEY')
    if not api_key:
        print("❌ DART_API_KEY 환경변수가 필요합니다!")
        return
    
    collector = Dart2024Collector(api_key)
    stats = collector.process_2024()
    collector.export_to_json()
    
    # 샘플 출력
    print("\n📊 Sample Data (삼성전자):")
    samples = [r for r in collector.results if r.get('stock_code') == '005930' and r.get('status') == 'success']
    for s in samples:
        print(f"   {s['year']}: 매출 {s.get('revenue', 0):,.0f}원, 영업익 {s.get('operating_profit', 0):,.0f}원")


if __name__ == '__main__':
    main()
