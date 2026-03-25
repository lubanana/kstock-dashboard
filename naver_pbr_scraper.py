#!/usr/bin/env python3
"""
네이버 증권 스크래퍼 - PBR 중심 필터링
PBR ≤ 0.6 종목 추출 후 부채비율은 DART/FNGUIDE API로 보완
"""

import requests
from bs4 import BeautifulSoup
import pandas as pd
import time
import json
import sqlite3
import re
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
import os

class NaverFinanceScraper:
    """네이버 증권 스크래퍼"""
    
    def __init__(self, delay=0.3):
        self.delay = delay
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Accept-Language': 'ko-KR,ko;q=0.9',
        }
        self.results = []
        
    def get_stock_fundamentals(self, stock_code):
        """종목 재무 데이터 추출"""
        try:
            result = {
                'symbol': stock_code,
                'success': False,
                'name': None,
                'per': None,
                'pbr': None,
                'bps': None,
                'sector': None,
            }
            
            # 종합정보 페이지
            url = f"https://finance.naver.com/item/main.naver?code={stock_code}"
            response = requests.get(url, headers=self.headers, timeout=10)
            response.encoding = 'euc-kr'
            
            if response.status_code != 200:
                return result
            
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # 종목명
            name_elem = soup.select_one('.wrap_company h2 a')
            if not name_elem:
                name_elem = soup.select_one('.wrap_company h2')
            result['name'] = name_elem.text.strip() if name_elem else stock_code
            
            # 업종
            sector_elem = soup.select_one('.wrap_company .description img')
            if sector_elem:
                result['sector'] = sector_elem.get('alt', '')
            
            # PER 추출
            for table in soup.select('table'):
                caption = table.select_one('caption')
                if caption and 'PER/EPS' in caption.text:
                    td = table.select_one('td')
                    if td:
                        text = td.get_text(strip=True)
                        match = re.search(r'([\d.]+)', text.replace(',', ''))
                        if match:
                            result['per'] = float(match.group(1))
                    break
            
            # PBR 추출 (페이지 전체에서)
            page_text = soup.get_text()
            pbr_match = re.search(r'PBR\([^)]*\)\s*([\d.]+)', page_text)
            if pbr_match:
                result['pbr'] = float(pbr_match.group(1))
            
            # BPS 추출
            bps_match = re.search(r'BPS[^\d]*(\d{3,})', page_text)
            if bps_match:
                result['bps'] = int(bps_match.group(1).replace(',', ''))
            
            result['success'] = result['pbr'] is not None or result['per'] is not None
            
            time.sleep(self.delay)
            return result
            
        except Exception as e:
            return {'symbol': stock_code, 'success': False, 'error': str(e)}
    
    def get_all_stocks_from_db(self, db_path='data/pivot_strategy.db'):
        """DB에서 종목 코드 로드"""
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute("""
            SELECT DISTINCT symbol 
            FROM stock_prices 
            WHERE date = '2026-03-25'
            ORDER BY symbol
        """)
        symbols = [row[0] for row in cursor.fetchall()]
        conn.close()
        return symbols
    
    def scrape_all(self, max_workers=5, limit=None):
        """전체 종목 스크래핑"""
        symbols = self.get_all_stocks_from_db()
        if limit:
            symbols = symbols[:limit]
        
        print(f"🔍 총 {len(symbols)}개 종목 스캐핑 시작...")
        print("-" * 70)
        
        self.results = []
        success = 0
        low_pbr = 0
        
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = {executor.submit(self.get_stock_fundamentals, s): s for s in symbols}
            
            for i, future in enumerate(as_completed(futures), 1):
                result = future.result()
                self.results.append(result)
                
                if result.get('success'):
                    success += 1
                    if result.get('pbr') and result['pbr'] <= 0.6:
                        low_pbr += 1
                        print(f"✅ [{i}/{len(symbols)}] {result['symbol']} {result.get('name', '')} - PBR: {result['pbr']:.2f}")
                
                if i % 100 == 0:
                    print(f"   진행: {i}/{len(symbols)} (성공: {success}, PBR≤0.6: {low_pbr})")
        
        print("-" * 70)
        print(f"✅ 완료: 성공 {success}/{len(symbols)}, PBR≤0.6: {low_pbr}")
        return self.results
    
    def filter_low_pbr(self, max_pbr=0.6):
        """PBR 필터링"""
        filtered = [r for r in self.results if r.get('success') and r.get('pbr') and r['pbr'] <= max_pbr]
        filtered.sort(key=lambda x: x['pbr'])
        return filtered
    
    def save_results(self, filtered, output_dir='reports/naver_finance'):
        """결과 저장"""
        os.makedirs(output_dir, exist_ok=True)
        ts = datetime.now().strftime('%Y%m%d_%H%M')
        
        json_path = f"{output_dir}/low_pbr_stocks_{ts}.json"
        with open(json_path, 'w', encoding='utf-8') as f:
            json.dump(filtered, f, ensure_ascii=False, indent=2)
        
        csv_path = f"{output_dir}/low_pbr_stocks_{ts}.csv"
        df = pd.DataFrame(filtered)
        df.to_csv(csv_path, index=False, encoding='utf-8-sig')
        
        print(f"💾 저장: {json_path}, {csv_path}")
        return json_path, csv_path

def main():
    scraper = NaverFinanceScraper(delay=0.2)
    
    # 전체 종목 스캔 (약 10~15분 소요 예상)
    print("🚀 전체 종목 PBR 스캔 시작 (약 10분 소요)")
    results = scraper.scrape_all(max_workers=5)
    
    # PBR ≤ 0.6 필터링
    low_pbr_stocks = scraper.filter_low_pbr(max_pbr=0.6)
    
    print(f"\\n🎯 PBR ≤ 0.6 종목: {len(low_pbr_stocks)}개")
    print("=" * 70)
    
    for i, stock in enumerate(low_pbr_stocks[:20], 1):
        print(f"{i:2d}. {stock['symbol']} {stock.get('name', '')}")
        print(f"     PBR: {stock['pbr']:.2f}", end='')
        if stock.get('per'):
            print(f" | PER: {stock['per']:.2f}", end='')
        if stock.get('sector'):
            print(f" | 업종: {stock['sector']}", end='')
        print()
    
    if low_pbr_stocks:
        scraper.save_results(low_pbr_stocks)
    
    print("\\n✅ 스캔 완료!")
    print("\\n💡 참고: 부채비율은 별도로 DART/FNGUIDE에서 확인 필요")

if __name__ == "__main__":
    main()
