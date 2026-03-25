#!/usr/bin/env python3
"""
네이버 증권 종목 분석 데이터 스크래퍼 v2
- main.naver 페이지에서 PER, PBR 추출
- 재무상태표 페이지에서 부채비율 추출
"""

import requests
from bs4 import BeautifulSoup
import pandas as pd
import time
import json
import sqlite3
import re
from concurrent.futures import ThreadPoolExecutor, as_completed
import os

class NaverFinanceScraperV2:
    """
    네이버 증권 종목 데이터 스크래퍼
    """
    
    def __init__(self, delay=0.5):
        self.delay = delay
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept-Language': 'ko-KR,ko;q=0.9',
        }
        self.results = []
        
    def get_stock_data(self, stock_code):
        """
        종목별 재무 데이터 수집
        """
        try:
            result = {
                'symbol': stock_code,
                'success': False,
                'name': None,
                'per': None,
                'pbr': None,
                'debt_ratio': None,
                'sector': None,
                'error': None
            }
            
            # 1. 종합정보 페이지 (PER, PBR, 종목명, 업종)
            main_url = f"https://finance.naver.com/item/main.naver?code={stock_code}"
            response = requests.get(main_url, headers=self.headers, timeout=10)
            response.encoding = 'euc-kr'
            
            if response.status_code != 200:
                result['error'] = f'HTTP {response.status_code}'
                return result
            
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # 종목명 추출
            name_elem = soup.select_one('.wrap_company h2 a')
            if not name_elem:
                name_elem = soup.select_one('.wrap_company h2')
            result['name'] = name_elem.text.strip() if name_elem else stock_code
            
            # 업종 추출
            sector_elem = soup.select_one('.wrap_company .description img')
            if sector_elem:
                result['sector'] = sector_elem.get('alt', '')
            
            # PER 추출 (PER/EPS 테이블)
            for table in soup.select('table'):
                caption = table.select_one('caption')
                if caption and 'PER' in caption.text and 'PER/EPS' in caption.text:
                    per_td = table.select_one('td')
                    if per_td:
                        per_text = per_td.get_text(strip=True)
                        per_match = re.search(r'([\d.]+)', per_text.replace(',', ''))
                        if per_match:
                            result['per'] = float(per_match.group(1))
                    break
            
            # PBR 추출 - 페이지 전체에서 PBR(배) 패턴 찾기
            page_text = soup.get_text()
            pbr_match = re.search(r'PBR\([^)]*\)\s*([\d.]+)', page_text)
            if pbr_match:
                result['pbr'] = float(pbr_match.group(1))
            
            # 2. 재무상태표 페이지 (부채비율)
            debt_ratio = self._get_debt_ratio(stock_code)
            result['debt_ratio'] = debt_ratio
            
            # 성공 여부 확인
            if result['pbr'] is not None or result['per'] is not None:
                result['success'] = True
            else:
                result['error'] = '재무 데이터 없음'
            
            time.sleep(self.delay)
            return result
            
        except Exception as e:
            return {
                'symbol': stock_code,
                'success': False,
                'error': str(e)
            }
    
    def _get_debt_ratio(self, stock_code):
        """
        재무상태표에서 부채비율 추출
        """
        try:
            # 재무상태표 페이지
            url = f"https://finance.naver.com/item/coinfo.naver?code={stock_code}"
            response = requests.get(url, headers=self.headers, timeout=10)
            response.encoding = 'euc-kr'
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # 손익/재무 정보 탭으로 이동
            # iframe에서 데이터 로드
            iframe = soup.select_one('iframe#coinfo_cp')
            if iframe:
                iframe_url = iframe.get('src')
                if iframe_url:
                    if iframe_url.startswith('//'):
                        iframe_url = 'https:' + iframe_url
                    elif iframe_url.startswith('/'):
                        iframe_url = 'https://finance.naver.com' + iframe_url
                    
                    iframe_resp = requests.get(iframe_url, headers=self.headers, timeout=10)
                    iframe_resp.encoding = 'euc-kr'
                    iframe_soup = BeautifulSoup(iframe_resp.text, 'html.parser')
                    
                    # 재무상태표에서 부채비율 찾기
                    tables = iframe_soup.select('table')
                    for table in tables:
                        rows = table.select('tr')
                        for row in rows:
                            th = row.select_one('th')
                            if th and '부채비율' in th.text:
                                tds = row.select('td')
                                if tds:
                                    value_text = tds[0].text.strip().replace(',', '').replace('%', '')
                                    try:
                                        return float(value_text)
                                    except:
                                        pass
            
            # iframe 없으면 현재 페이지에서 검색
            for table in soup.select('table'):
                rows = table.select('tr')
                for row in rows:
                    th = row.select_one('th, td')
                    if th and '부채비율' in th.text:
                        tds = row.select('td')
                        if len(tds) >= 1:
                            value_text = tds[0].text.strip().replace(',', '').replace('%', '')
                            try:
                                return float(value_text)
                            except:
                                pass
            
            return None
            
        except Exception as e:
            return None
    
    def get_all_stocks_from_db(self, db_path='data/pivot_strategy.db'):
        """DB에서 모든 종목 코드 가져오기"""
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
    
    def scrape_all(self, max_workers=3, limit=None):
        """
        전체 종목 스크래핑
        """
        symbols = self.get_all_stocks_from_db()
        
        if limit:
            symbols = symbols[:limit]
        
        print(f"🔍 총 {len(symbols)}개 종목 스크래핑 시작...")
        print(f"   필터 조건: PBR ≤ 0.6, 부채비율 < 50%")
        print("-" * 70)
        
        self.results = []
        success_count = 0
        filtered_count = 0
        
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            future_to_symbol = {
                executor.submit(self.get_stock_data, symbol): symbol 
                for symbol in symbols
            }
            
            for i, future in enumerate(as_completed(future_to_symbol), 1):
                result = future.result()
                self.results.append(result)
                
                if result.get('success'):
                    success_count += 1
                    
                    # 필터 조건 확인
                    pbr = result.get('pbr')
                    debt = result.get('debt_ratio')
                    
                    if pbr and debt and pbr <= 0.6 and debt < 50:
                        filtered_count += 1
                        print(f"✅ [{i}/{len(symbols)}] {result['symbol']} {result.get('name', '')}")
                        print(f"      PBR: {pbr:.2f}, 부채비율: {debt:.1f}%")
                
                if i % 50 == 0:
                    print(f"   진행 중... {i}/{len(symbols)} (성공: {success_count}, 필터통과: {filtered_count})")
        
        print("-" * 70)
        print(f"✅ 스크래핑 완료")
        print(f"   성공: {success_count}/{len(symbols)}")
        print(f"   필터통과 (PBR≤0.6, 부채비율<50%): {filtered_count}")
        
        return self.results
    
    def filter_stocks(self, max_pbr=0.6, max_debt_ratio=50):
        """
        필터 조건 적용
        """
        filtered = []
        
        for result in self.results:
            if not result.get('success'):
                continue
            
            pbr = result.get('pbr')
            debt_ratio = result.get('debt_ratio')
            
            if (pbr is not None and debt_ratio is not None and 
                pbr <= max_pbr and debt_ratio < max_debt_ratio):
                filtered.append(result)
        
        # PBR 낮은 순으로 정렬
        filtered.sort(key=lambda x: x['pbr'])
        
        return filtered
    
    def save_results(self, filtered_stocks, output_dir='reports/naver_finance'):
        """결과 저장"""
        os.makedirs(output_dir, exist_ok=True)
        
        timestamp = datetime.now().strftime('%Y%m%d_%H%M')
        
        # JSON 저장
        json_path = f"{output_dir}/pbr_debt_filtered_{timestamp}.json"
        with open(json_path, 'w', encoding='utf-8') as f:
            json.dump(filtered_stocks, f, ensure_ascii=False, indent=2)
        
        # CSV 저장
        csv_path = f"{output_dir}/pbr_debt_filtered_{timestamp}.csv"
        df = pd.DataFrame(filtered_stocks)
        df.to_csv(csv_path, index=False, encoding='utf-8-sig')
        
        # 전체 결과도 저장
        all_json_path = f"{output_dir}/all_fundamentals_{timestamp}.json"
        with open(all_json_path, 'w', encoding='utf-8') as f:
            json.dump(self.results, f, ensure_ascii=False, indent=2)
        
        print(f"\n💾 결과 저장:")
        print(f"   필터링: {json_path}")
        print(f"   CSV: {csv_path}")
        
        return json_path, csv_path

def main():
    """메인 실행"""
    scraper = NaverFinanceScraperV2(delay=0.5)
    
    # 테스트: 30개 종목
    print("🧪 테스트 모드: 30개 종목")
    results = scraper.scrape_all(max_workers=2, limit=30)
    
    # 필터링
    filtered = scraper.filter_stocks(max_pbr=0.6, max_debt_ratio=50)
    
    print(f"\n🎯 필터 결과 (PBR ≤ 0.6, 부채비율 < 50%)")
    print(f"   선정: {len(filtered)}개")
    print("-" * 70)
    
    for i, stock in enumerate(filtered, 1):
        print(f"{i}. {stock['symbol']} {stock.get('name', '')}")
        print(f"   PBR: {stock['pbr']:.2f}, 부채비율: {stock['debt_ratio']:.1f}%")
        if stock.get('per'):
            print(f"   PER: {stock['per']:.2f}")
        if stock.get('sector'):
            print(f"   업종: {stock['sector']}")
    
    # 결과 저장
    if filtered:
        scraper.save_results(filtered)
    
    print("\n✅ 테스트 완료!")

if __name__ == "__main__":
    from datetime import datetime
    main()
