#!/usr/bin/env python3
"""
Naver Stock Real-time Price Fetcher
네이버증권 실시간 주가/지수 수집 모듈
"""

import asyncio
import json
from datetime import datetime
from playwright.async_api import async_playwright
from bs4 import BeautifulSoup


class NaverPriceFetcher:
    """네이버증권 실시간 가격 수집기"""
    
    BASE_URL = "https://m.stock.naver.com"
    
    async def fetch_page(self, url: str, timeout: int = 30000):
        """Playwright로 페이지 가져오기"""
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            context = await browser.new_context(
                user_agent='Mozilla/5.0 (iPhone; CPU iPhone OS 16_0 like Mac OS X)',
                viewport={'width': 390, 'height': 844}
            )
            page = await context.new_page()
            
            try:
                await page.goto(url, wait_until='domcontentloaded', timeout=timeout)
                await asyncio.sleep(2)
                content = await page.content()
                await browser.close()
                return content
            except Exception as e:
                await browser.close()
                raise e
    
    async def get_stock_price(self, stock_code: str) -> dict:
        """
        개별 종목 현재가/전일종가 수집
        
        Returns:
            {
                'current_price': 현재가,
                'prev_close': 전일종가,
                'change': 등띠,
                'change_rate': 등띠률,
                'volume': 거래량
            }
        """
        url = f"{self.BASE_URL}/domestic/stock/{stock_code}/quote"
        
        try:
            html = await self.fetch_page(url)
            soup = BeautifulSoup(html, 'html.parser')
            
            data = {
                'stock_code': stock_code,
                'fetched_at': datetime.now().isoformat(),
                'status': 'success'
            }
            
            # 현재가 - 다양한 선택자 시도
            price_selectors = [
                '.current_price',
                '.stock_price',
                '[class*="price"] strong',
                '.num',
                'span[class*="current"]'
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
            
            # 전일종가
            prev_selectors = [
                '.prev_close',
                '.yesterday',
                '[class*="prev"]',
                'td:contains("전일") + td'
            ]
            
            for selector in prev_selectors:
                elem = soup.select_one(selector)
                if elem:
                    prev_text = elem.text.strip().replace(',', '')
                    try:
                        data['prev_close'] = int(prev_text)
                        break
                    except:
                        continue
            
            # 등띠/등띠률
            change_selectors = [
                '.change_price',
                '.change_rate',
                '[class*="change"]'
            ]
            
            for selector in change_selectors:
                elem = soup.select_one(selector)
                if elem:
                    data['change'] = elem.text.strip()
                    break
            
            # 거래량
            volume_selectors = [
                '.volume',
                '[class*="volume"]',
                'td:contains("거래량") + td'
            ]
            
            for selector in volume_selectors:
                elem = soup.select_one(selector)
                if elem:
                    data['volume'] = elem.text.strip()
                    break
            
            return data
            
        except Exception as e:
            return {
                'stock_code': stock_code,
                'status': 'error',
                'error': str(e),
                'fetched_at': datetime.now().isoformat()
            }
    
    async def get_market_indices(self) -> dict:
        """
        코스피/코스닥 지수 수집
        
        Returns:
            {
                'kospi': {'current': 현재지수, 'change': 등띠, 'change_rate': 등띠률},
                'kosdaq': {'current': 현재지수, 'change': 등띠, 'change_rate': 등띠률}
            }
        """
        url = f"{self.BASE_URL}/domestic/index"
        
        try:
            html = await self.fetch_page(url)
            soup = BeautifulSoup(html, 'html.parser')
            
            data = {
                'fetched_at': datetime.now().isoformat(),
                'status': 'success',
                'indices': {}
            }
            
            # 지수 항목 찾기
            index_items = soup.select('.index_item, [class*="index"], a[href*="/domestic/index/"]')
            
            for item in index_items:
                try:
                    name_elem = item.select_one('.name, .index_name, .title')
                    price_elem = item.select_one('.price, .index_price, .num')
                    change_elem = item.select_one('.change, .rate, .up, .down')
                    
                    if name_elem and price_elem:
                        name = name_elem.text.strip()
                        price = price_elem.text.strip().replace(',', '')
                        change = change_elem.text.strip() if change_elem else ''
                        
                        if '코스피' in name or 'KOSPI' in name:
                            data['indices']['kospi'] = {
                                'current': price,
                                'change': change,
                                'name': 'KOSPI'
                            }
                        elif '코스닥' in name or 'KOSDAQ' in name:
                            data['indices']['kosdaq'] = {
                                'current': price,
                                'change': change,
                                'name': 'KOSDAQ'
                            }
                except:
                    continue
            
            return data
            
        except Exception as e:
            return {
                'status': 'error',
                'error': str(e),
                'fetched_at': datetime.now().isoformat()
            }
    
    async def get_multiple_prices(self, stock_codes: list) -> dict:
        """여러 종목 가격 동시 수집"""
        results = {}
        
        # 순차 실행 (네이버는 너무 빠른 요청 시 차단 가능)
        for code in stock_codes:
            try:
                result = await self.get_stock_price(code)
                results[code] = result
                await asyncio.sleep(0.5)  # 요청 간격
            except Exception as e:
                results[code] = {'status': 'error', 'error': str(e)}
        
        return results


async def main():
    """테스트 실행"""
    fetcher = NaverPriceFetcher()
    
    print("=" * 60)
    print("📊 Naver Stock Price Fetcher Test")
    print("=" * 60)
    
    # 1. 개별 종목
    print("\n📈 삼성전자 (005930) 주가:")
    price = await fetcher.get_stock_price('005930')
    print(json.dumps(price, indent=2, ensure_ascii=False))
    
    # 2. 시장 지수
    print("\n📊 시장 지수:")
    indices = await fetcher.get_market_indices()
    print(json.dumps(indices, indent=2, ensure_ascii=False))
    
    # 3. 여러 종목
    print("\n📈 여러 종목 동시 조회:")
    codes = ['005930', '000660', '035420']
    prices = await fetcher.get_multiple_prices(codes)
    for code, data in prices.items():
        if data.get('status') == 'success':
            print(f"   {code}: {data.get('current_price', 'N/A')}원")
        else:
            print(f"   {code}: Error - {data.get('error', 'Unknown')}")
    
    print("\n" + "=" * 60)


if __name__ == '__main__':
    asyncio.run(main())
