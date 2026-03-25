#!/usr/bin/env python3
"""
네이버 증권 종목 분석 데이터 스크래퍼
- PBR (Price-to-Book Ratio)
- 부채비율 (Debt Ratio)
- PER, ROE 등 추가 재무 지표
"""

import requests
from bs4 import BeautifulSoup
import pandas as pd
import time
import json
import sqlite3
from datetime import datetime
import re
from concurrent.futures import ThreadPoolExecutor, as_completed
import os

class NaverFinanceScraper:
    """
    네이버 증권 종목 분석 페이지 스크래퍼
    URL: https://finance.naver.com/item/coinfo.naver?code={stock_code}
    """
    
    def __init__(self, delay=0.5):
        self.delay = delay
        self.base_url = "https://finance.naver.com/item/coinfo.naver"
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'ko-KR,ko;q=0.9,en-US;q=0.8,en;q=0.7',
        }
        self.results = []
        
    def get_stock_fundamentals(self, stock_code):
        """
        개별 종목의 재무 지표 수집
        
        Returns:
            dict: {
                'symbol': 종목코드,
                'name': 종목명,
                'pbr': PBR,
                'debt_ratio': 부채비율,
                'per': PER,
                'roe': ROE,
                'eps': EPS,
                'bps': BPS,
                'sector': 업종,
                'success': 성공여부
            }
        """
        try:
            url = f"{self.base_url}?code={stock_code}"
            response = requests.get(url, headers=self.headers, timeout=10)
            response.encoding = 'euc-kr'
            
            if response.status_code != 200:
                return {'symbol': stock_code, 'success': False, 'error': f'HTTP {response.status_code}'}
            
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # 종목명 추출
            name_elem = soup.select_one('.wrap_company h2')
            name = name_elem.text.strip() if name_elem else stock_code
            
            # 테이블 데이터 추출 (PER, EPS, PBR, BPS, 배당수익률 등)
            data = {'symbol': stock_code, 'name': name, 'success': True}
            
            # 기본 정보 테이블
            info_table = soup.select_one('#tab_con1')
            if info_table:
                rows = info_table.select('tr')
                for row in rows:
                    th = row.select_one('th')
                    td = row.select_one('td')
                    if th and td:
                        label = th.text.strip()
                        value = td.text.strip().replace(',', '')
                        
                        if 'PER' in label and 'PER(배)' in label:
                            try:
                                data['per'] = float(value.split()[0]) if value and value != 'N/A' else None
                            except:
                                data['per'] = None
                                
                        elif 'PBR' in label:
                            try:
                                data['pbr'] = float(value.split()[0]) if value and value != 'N/A' else None
                            except:
                                data['pbr'] = None
                                
                        elif 'EPS' in label:
                            try:
                                data['eps'] = float(value.split()[0]) if value and value != 'N/A' else None
                            except:
                                data['eps'] = None
                                
                        elif 'BPS' in label:
                            try:
                                data['bps'] = float(value.split()[0]) if value and value != 'N/A' else None
                            except:
                                data['bps'] = None
                                
                        elif '배당수익률' in label:
                            try:
                                data['dividend_yield'] = float(value.replace('%', '')) if value and '%' in value else None
                            except:
                                data['dividend_yield'] = None
            
            # 재무 상태 (부채비율 등) - 다른 탭에서 가져와야 함
            # 종합정보 탭의 재무제표 정보
            debt_ratio = self._extract_debt_ratio(soup)
            data['debt_ratio'] = debt_ratio
            
            # 업종 정보
            sector_elem = soup.select_one('.wrap_company .summary_info .item')
            if sector_elem:
                data['sector'] = sector_elem.text.strip()
            else:
                data['sector'] = None
                
            # 시가총액
            market_cap_elem = soup.select_one('.first .line .strong')
            if market_cap_elem:
                try:
                    cap_text = market_cap_elem.text.strip().replace(',', '').replace('억원', '')
                    data['market_cap'] = float(cap_text) if cap_text else None
                except:
                    data['market_cap'] = None
            
            time.sleep(self.delay)
            return data
            
        except Exception as e:
            return {'symbol': stock_code, 'success': False, 'error': str(e)}
    
    def _extract_debt_ratio(self, soup):
        """
        부채비율 추출 (재무상태표에서)
        """
        try:
            # 재무제표 탭 링크 찾기
            # 간단한 방법: 현재 페이지에서 재무정보 테이블 찾기
            tables = soup.select('table')
            
            for table in tables:
                rows = table.select('tr')
                for row in rows:
                    th = row.select_one('th, td')
                    if th and '부채비율' in th.text:
                        td = row.select('td')
                        if len(td) >= 2:
                            value = td[0].text.strip().replace(',', '').replace('%', '')
                            try:
                                return float(value)
                            except:
                                return None
            return None
        except:
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
    
    def scrape_all_stocks(self, max_workers=3, limit=None):
        """
        전체 종목 스크래핑 (멀티스레드)
        
        Args:
            max_workers: 동시 실행 스레드 수
            limit: 테스트용 제한 (None = 전체)
        """
        symbols = self.get_all_stocks_from_db()
        
        if limit:
            symbols = symbols[:limit]
            
        print(f"🔍 총 {len(symbols)}개 종목 스크래핑 시작...")
        print(f"   필터 조건: PBR ≤ 0.6, 부채비율 < 50%")
        print("-" * 60)
        
        self.results = []
        success_count = 0
        fail_count = 0
        
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            future_to_symbol = {
                executor.submit(self.get_stock_fundamentals, symbol): symbol 
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
                        print(f"✅ [{i}/{len(symbols)}] {result['symbol']} {result.get('name', '')}")
                        print(f"      PBR: {pbr:.2f}, 부채비율: {debt:.1f}%")
                else:
                    fail_count += 1
                
                if i % 100 == 0:
                    print(f"   진행 중... {i}/{len(symbols)} (성공: {success_count}, 실패: {fail_count})")
        
        print("-" * 60)
        print(f"✅ 스크래핑 완료: 성공 {success_count}, 실패 {fail_count}")
        
        return self.results
    
    def filter_stocks(self, max_pbr=0.6, max_debt_ratio=50):
        """
        필터 조건 적용
        
        Args:
            max_pbr: 최대 PBR (기본 0.6)
            max_debt_ratio: 최대 부채비율 (기본 50%)
        
        Returns:
            list: 필터링된 종목 리스트
        """
        filtered = []
        
        for result in self.results:
            if not result.get('success'):
                continue
                
            pbr = result.get('pbr')
            debt_ratio = result.get('debt_ratio')
            
            # PBR과 부채비율이 모두 있고 조건 충족
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
        print(f"   전체: {all_json_path}")
        
        return json_path, csv_path

def main():
    """메인 실행"""
    scraper = NaverFinanceScraper(delay=0.3)
    
    # 테스트: 50개 종목만 먼저
    print("🧪 테스트 모드: 50개 종목")
    results = scraper.scrape_all_stocks(max_workers=2, limit=50)
    
    # 필터링
    filtered = scraper.filter_stocks(max_pbr=0.6, max_debt_ratio=50)
    
    print(f"\n🎯 필터 결과 (PBR ≤ 0.6, 부채비율 < 50%)")
    print(f"   선정: {len(filtered)}개")
    print("-" * 60)
    
    for i, stock in enumerate(filtered[:10], 1):
        print(f"{i}. {stock['symbol']} {stock.get('name', '')}")
        print(f"   PBR: {stock['pbr']:.2f}, 부채비율: {stock['debt_ratio']:.1f}%")
        if stock.get('per'):
            print(f"   PER: {stock['per']:.2f}")
    
    # 결과 저장
    if filtered:
        scraper.save_results(filtered)
    
    print("\n✅ 테스트 완료!")
    print("전체 종목 스캔을 원하면 limit=None으로 실행하세요.")

if __name__ == "__main__":
    main()
