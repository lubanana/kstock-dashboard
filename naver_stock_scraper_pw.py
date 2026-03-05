#!/usr/bin/env python3
"""
Naver Stock Scraper using Playwright
네이버 주식 스크래핑 모듈 (Playwright 직접 사용)

Target: https://m.stock.naver.com/
"""

import json
import asyncio
from datetime import datetime
from typing import Dict, List, Optional
from playwright.async_api import async_playwright


class NaverStockScraper:
    """네이버 주식 스크래퍼"""
    
    BASE_URL = "https://m.stock.naver.com"
    
    async def fetch_page(self, url: str, wait_selector: str = None, timeout: int = 30000):
        """Playwright로 페이지 가져오기"""
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            context = await browser.new_context(
                user_agent='Mozilla/5.0 (iPhone; CPU iPhone OS 16_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.0 Mobile/15E148 Safari/604.1',
                viewport={'width': 390, 'height': 844}
            )
            page = await context.new_page()
            
            try:
                # 페이지 로딩
                await page.goto(url, wait_until='domcontentloaded', timeout=timeout)
                
                # JavaScript 실행 대기
                await asyncio.sleep(3)
                
                if wait_selector:
                    try:
                        await page.wait_for_selector(wait_selector, timeout=timeout, state='visible')
                    except:
                        pass  # 선택자가 없어도 계속 진행
                
                # 추가 로딩 시간
                await asyncio.sleep(2)
                
                content = await page.content()
                await browser.close()
                return content
                
            except Exception as e:
                await browser.close()
                raise e
    
    def parse_stock_quote(self, html: str, stock_code: str) -> Dict:
        """HTML에서 종목 시세 파싱"""
        from bs4 import BeautifulSoup
        
        soup = BeautifulSoup(html, 'html.parser')
        
        data = {
            'stock_code': stock_code,
            'scraped_at': datetime.now().isoformat(),
            'status': 'success',
            'html_preview': html[:500]  # 디버깅용
        }
        
        try:
            # 종목명 - 다양한 선택자 시도
            name_selectors = [
                '.stock_name', '.name', 'h1[class*="name"]',
                '[class*="stockName"]', '[class*="stock_name"]',
                'h1', '.title'
            ]
            for selector in name_selectors:
                elem = soup.select_one(selector)
                if elem and elem.text.strip():
                    data['name'] = elem.text.strip()
                    break
            else:
                data['name'] = None
            
            # 현재가 - 다양한 선택자 시도
            price_selectors = [
                '.current_price', '.price strong', '[class*="price"]',
                '[class*="currentPrice"]', '[class*="stock_price"]',
                '.num', '.figure'
            ]
            for selector in price_selectors:
                elem = soup.select_one(selector)
                if elem:
                    price_text = elem.text.strip().replace(',', '').replace('원', '')
                    try:
                        data['current_price'] = int(price_text)
                        break
                    except:
                        continue
            else:
                data['current_price'] = None
            
            # 등띠
            change_selectors = [
                '.change_price', '.change', '[class*="change"]',
                '[class*="up"]', '[class*="down"]'
            ]
            for selector in change_selectors:
                elem = soup.select_one(selector)
                if elem and elem.text.strip():
                    data['change'] = elem.text.strip()
                    break
            else:
                data['change'] = None
            
            # 등띠률
            rate_selectors = [
                '.change_rate', '[class*="rate"]', '[class*="percent"]'
            ]
            for selector in rate_selectors:
                elem = soup.select_one(selector)
                if elem and elem.text.strip():
                    data['change_rate'] = elem.text.strip()
                    break
            else:
                data['change_rate'] = None
            
            return data
            
        except Exception as e:
            data['status'] = 'error'
            data['error'] = str(e)
            return data
    
    async def get_stock_quote(self, stock_code: str) -> Dict:
        """개별 종목 시세 정보 수집"""
        url = f"{self.BASE_URL}/domestic/stock/{stock_code}/quote"
        
        try:
            html = await self.fetch_page(url, wait_selector='[class*="price"], [class*="name"]')
            return self.parse_stock_quote(html, stock_code)
            
        except Exception as e:
            return {
                'stock_code': stock_code,
                'status': 'error',
                'error': str(e),
                'scraped_at': datetime.now().isoformat()
            }
    
    async def get_market_indices(self) -> Dict:
        """시장 지수 수집"""
        url = f"{self.BASE_URL}/domestic/index"
        
        try:
            html = await self.fetch_page(url)
            from bs4 import BeautifulSoup
            soup = BeautifulSoup(html, 'html.parser')
            
            indices = []
            
            # KOSPI/KOSDAQ 지수 추출
            index_items = soup.select('a[href*="/domestic/index/"], .index_item, .market_index')
            
            for item in index_items[:5]:
                try:
                    name_elem = item.select_one('.name, .index_name, span:first-child')
                    price_elem = item.select_one('.price, .index_price, .num')
                    change_elem = item.select_one('.change, .rate, .up, .down')
                    
                    if name_elem and price_elem:
                        indices.append({
                            'name': name_elem.text.strip(),
                            'price': price_elem.text.strip().replace(',', ''),
                            'change': change_elem.text.strip() if change_elem else None
                        })
                except:
                    continue
            
            return {
                'scraped_at': datetime.now().isoformat(),
                'status': 'success',
                'count': len(indices),
                'indices': indices
            }
            
        except Exception as e:
            return {
                'status': 'error',
                'error': str(e),
                'scraped_at': datetime.now().isoformat()
            }
    
    async def get_top_stocks(self, market: str = 'kospi') -> Dict:
        """상위 종목 리스트 수집"""
        url = f"{self.BASE_URL}/domestic/stock/{market}/ranking"
        
        try:
            html = await self.fetch_page(url, wait_selector='table, .stock_list')
            from bs4 import BeautifulSoup
            soup = BeautifulSoup(html, 'html.parser')
            
            stocks = []
            
            # 테이블에서 종목 추출
            rows = soup.select('table tr, .stock_item, .ranking_item')
            
            for row in rows[1:31]:  # 헤더 제외, TOP 30
                try:
                    tds = row.find_all(['td', 'th'])
                    if len(tds) >= 3:
                        rank = tds[0].text.strip()
                        name_elem = tds[1].select_one('a, .name')
                        price_elem = tds[2] if len(tds) > 2 else None
                        
                        if name_elem:
                            stocks.append({
                                'rank': rank,
                                'name': name_elem.text.strip(),
                                'price': price_elem.text.strip().replace(',', '') if price_elem else None
                            })
                except:
                    continue
            
            return {
                'market': market,
                'scraped_at': datetime.now().isoformat(),
                'status': 'success',
                'count': len(stocks),
                'stocks': stocks
            }
            
        except Exception as e:
            return {
                'market': market,
                'status': 'error',
                'error': str(e),
                'scraped_at': datetime.now().isoformat()
            }
    
    async def get_stock_detail(self, stock_code: str) -> Dict:
        """종목 상세 정보 수집 (PER, PBR 등)"""
        url = f"{self.BASE_URL}/domestic/stock/{stock_code}/finance"
        
        try:
            html = await self.fetch_page(url)
            from bs4 import BeautifulSoup
            soup = BeautifulSoup(html, 'html.parser')
            
            data = {
                'stock_code': stock_code,
                'scraped_at': datetime.now().isoformat(),
                'status': 'success'
            }
            
            # 재무 테이블에서 데이터 추출
            rows = soup.select('table tr, .finance_row')
            
            for row in rows:
                try:
                    th = row.select_one('th, .label')
                    td = row.select_one('td, .value')
                    
                    if th and td:
                        label = th.text.strip()
                        value = td.text.strip()
                        
                        if 'PER' in label:
                            data['per'] = value
                        elif 'PBR' in label:
                            data['pbr'] = value
                        elif 'EPS' in label:
                            data['eps'] = value
                        elif 'BPS' in label:
                            data['bps'] = value
                        elif '배당수익률' in label:
                            data['dividend_yield'] = value
                        elif '시가총액' in label:
                            data['market_cap'] = value
                except:
                    continue
            
            return data
            
        except Exception as e:
            return {
                'stock_code': stock_code,
                'status': 'error',
                'error': str(e),
                'scraped_at': datetime.now().isoformat()
            }


async def main():
    """테스트 실행"""
    print("=" * 60)
    print("🚀 Naver Stock Scraper Test (Playwright)")
    print("=" * 60)
    
    scraper = NaverStockScraper()
    
    # 1. 시장 지수
    print("\n📊 Fetching market indices...")
    indices = await scraper.get_market_indices()
    print(f"   Status: {indices.get('status')}")
    if indices.get('status') == 'success':
        for idx in indices.get('indices', []):
            print(f"   • {idx['name']}: {idx['price']}")
    else:
        print(f"   Error: {indices.get('error')}")
    
    # 2. 개별 종목 시세
    print("\n📈 Fetching Samsung Electronics (005930)...")
    quote = await scraper.get_stock_quote('005930')
    print(f"   Status: {quote.get('status')}")
    if quote.get('status') == 'success':
        print(f"   • Name: {quote.get('name')}")
        print(f"   • Price: {quote.get('current_price'):,}원" if quote.get('current_price') else "   • Price: N/A")
        print(f"   • Change: {quote.get('change')}")
        print(f"   • Change Rate: {quote.get('change_rate')}")
    else:
        print(f"   Error: {quote.get('error')}")
    
    # 3. 종목 상세 정보
    print("\n📋 Fetching Samsung Electronics detail info...")
    detail = await scraper.get_stock_detail('005930')
    if detail.get('status') == 'success':
        print(f"   • PER: {detail.get('per')}")
        print(f"   • PBR: {detail.get('pbr')}")
        print(f"   • EPS: {detail.get('eps')}")
        print(f"   • BPS: {detail.get('bps')}")
        print(f"   • Dividend Yield: {detail.get('dividend_yield')}")
        print(f"   • Market Cap: {detail.get('market_cap')}")
    else:
        print(f"   Error: {detail.get('error')}")
    
    # 4. 상위 종목
    print("\n🏆 Fetching TOP 10 KOSPI stocks...")
    top_stocks = await scraper.get_top_stocks('kospi')
    if top_stocks.get('status') == 'success':
        for stock in top_stocks.get('stocks', [])[:10]:
            print(f"   {stock['rank']}. {stock['name']}: {stock['price']}원")
    else:
        print(f"   Error: {top_stocks.get('error')}")
    
    # 결과 저장
    output = {
        'scraped_at': datetime.now().isoformat(),
        'indices': indices,
        'samsung_quote': quote,
        'samsung_detail': detail,
        'top_stocks': top_stocks
    }
    
    output_file = f'/home/programs/kstock_analyzer/data/naver_scrape_{datetime.now().strftime("%Y%m%d_%H%M")}.json'
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(output, f, indent=2, ensure_ascii=False)
    
    print(f"\n💾 Results saved: {output_file}")
    print("=" * 60)


if __name__ == '__main__':
    asyncio.run(main())
