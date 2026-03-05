#!/usr/bin/env python3
"""
Naver Stock Scraper using Scrapling
네이버 주식 스크래핑 모듈

Target: https://m.stock.naver.com/
"""

import json
from datetime import datetime
from typing import Dict, List, Optional
from scrapling import Fetcher


class NaverStockScraper:
    """네이버 주식 스크래퍼"""
    
    BASE_URL = "https://m.stock.naver.com"
    
    def __init__(self):
        self.fetcher = Fetcher()
    
    def get_stock_quote(self, stock_code: str) -> Dict:
        """
        개별 종목 시세 정보 수집
        
        Args:
            stock_code: 종목코드 (예: '005930')
        
        Returns:
            시세 정보 딕셔너리
        """
        url = f"{self.BASE_URL}/domestic/stock/{stock_code}/quote"
        
        try:
            page = self.fetcher.fetch(url)
            
            # 주요 데이터 추출
            data = {
                'stock_code': stock_code,
                'scraped_at': datetime.now().isoformat(),
                'url': url,
                'status': 'success'
            }
            
            # 종목명
            try:
                name_elem = page.css_first('h1[class*="name"]')
                data['name'] = name_elem.text.strip() if name_elem else None
            except:
                data['name'] = None
            
            # 현재가
            try:
                price_elem = page.css_first('strong[class*="price"]')
                if price_elem:
                    price_text = price_elem.text.strip().replace(',', '')
                    data['current_price'] = int(price_text)
                else:
                    data['current_price'] = None
            except:
                data['current_price'] = None
            
            # 등띠/등띠률
            try:
                change_elem = page.css_first('span[class*="change"]')
                if change_elem:
                    change_text = change_elem.text.strip()
                    data['change'] = change_text
                else:
                    data['change'] = None
            except:
                data['change'] = None
            
            # 거래량
            try:
                volume_elem = page.css_first('td:has-text("거래량") + td')
                if volume_elem:
                    volume_text = volume_elem.text.strip().replace(',', '')
                    data['volume'] = int(volume_text)
                else:
                    data['volume'] = None
            except:
                data['volume'] = None
            
            # 시가총액
            try:
                market_cap_elem = page.css_first('td:has-text("시총") + td')
                if market_cap_elem:
                    data['market_cap'] = market_cap_elem.text.strip()
                else:
                    data['market_cap'] = None
            except:
                data['market_cap'] = None
            
            # PER, PBR, EPS, BPS, 배당수익률
            try:
                # 재무제표 테이블에서 추출
                table_rows = page.css('table[class*="finance"] tr')
                for row in table_rows:
                    th = row.css_first('th')
                    td = row.css_first('td')
                    if th and td:
                        label = th.text.strip()
                        value = td.text.strip()
                        
                        if 'PER' in label:
                            data['per'] = float(value.replace(',', '')) if value != '-' else None
                        elif 'PBR' in label:
                            data['pbr'] = float(value.replace(',', '')) if value != '-' else None
                        elif 'EPS' in label:
                            data['eps'] = int(value.replace(',', '')) if value != '-' else None
                        elif 'BPS' in label:
                            data['bps'] = int(value.replace(',', '')) if value != '-' else None
                        elif '배당수익률' in label:
                            data['dividend_yield'] = float(value.replace('%', '')) if value != '-' else None
            except Exception as e:
                data['financial_error'] = str(e)
            
            return data
            
        except Exception as e:
            return {
                'stock_code': stock_code,
                'status': 'error',
                'error': str(e),
                'scraped_at': datetime.now().isoformat()
            }
    
    def get_market_indices(self) -> Dict:
        """
        시장 지수 수집 (KOSPI, KOSDAQ)
        
        Returns:
            지수 정보 딕셔너리
        """
        url = f"{self.BASE_URL}/domestic/index"
        
        try:
            page = self.fetcher.fetch(url)
            
            data = {
                'scraped_at': datetime.now().isoformat(),
                'url': url,
                'status': 'success',
                'indices': []
            }
            
            # KOSPI, KOSDAQ 지수 추출
            index_items = page.css('a[class*="index_item"]')
            
            for item in index_items:
                try:
                    name_elem = item.css_first('span[class*="name"]')
                    price_elem = item.css_first('span[class*="price"]')
                    change_elem = item.css_first('span[class*="change"]')
                    
                    if name_elem and price_elem:
                        index_data = {
                            'name': name_elem.text.strip(),
                            'price': price_elem.text.strip().replace(',', ''),
                            'change': change_elem.text.strip() if change_elem else None
                        }
                        data['indices'].append(index_data)
                except:
                    continue
            
            return data
            
        except Exception as e:
            return {
                'status': 'error',
                'error': str(e),
                'scraped_at': datetime.now().isoformat()
            }
    
    def get_top_stocks(self, market: str = 'kospi', sort: str = 'market_cap') -> List[Dict]:
        """
        상위 종목 리스트 수집
        
        Args:
            market: 'kospi' 또는 'kosdaq'
            sort: 'market_cap' (시총), 'volume' (거래량), 'change' (등띠률)
        
        Returns:
            종목 리스트
        """
        sort_map = {
            'market_cap': 'marketValue',
            'volume': 'accTradeVolume',
            'change': 'changeRate'
        }
        
        sort_param = sort_map.get(sort, 'marketValue')
        url = f"{self.BASE_URL}/domestic/stock/{market}/ranking?sort={sort_param}"
        
        try:
            page = self.fetcher.fetch(url)
            
            stocks = []
            stock_rows = page.css('tr[class*="stock_item"]')
            
            for row in stock_rows[:30]:  # TOP 30
                try:
                    rank_elem = row.css_first('td[class*="rank"]')
                    name_elem = row.css_first('td[class*="name"] a')
                    price_elem = row.css_first('td[class*="price"]')
                    change_elem = row.css_first('td[class*="change"]')
                    
                    if name_elem:
                        stock_data = {
                            'rank': rank_elem.text.strip() if rank_elem else None,
                            'name': name_elem.text.strip(),
                            'code': name_elem.get('href', '').split('/')[-1] if name_elem.get('href') else None,
                            'price': price_elem.text.strip().replace(',', '') if price_elem else None,
                            'change': change_elem.text.strip() if change_elem else None
                        }
                        stocks.append(stock_data)
                except:
                    continue
            
            return {
                'market': market,
                'sort_by': sort,
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
    
    def get_sector_performance(self) -> List[Dict]:
        """
        업종별 등띠률 수집
        
        Returns:
            업종별 성과 리스트
        """
        url = f"{self.BASE_URL}/domestic/sector"
        
        try:
            page = self.fetcher.fetch(url)
            
            sectors = []
            sector_items = page.css('a[class*="sector_item"]')
            
            for item in sector_items:
                try:
                    name_elem = item.css_first('span[class*="name"]')
                    change_elem = item.css_first('span[class*="change"]')
                    
                    if name_elem:
                        sector_data = {
                            'name': name_elem.text.strip(),
                            'change': change_elem.text.strip() if change_elem else None
                        }
                        sectors.append(sector_data)
                except:
                    continue
            
            return {
                'scraped_at': datetime.now().isoformat(),
                'status': 'success',
                'count': len(sectors),
                'sectors': sectors
            }
            
        except Exception as e:
            return {
                'status': 'error',
                'error': str(e),
                'scraped_at': datetime.now().isoformat()
            }
    
    def get_news(self, stock_code: str) -> List[Dict]:
        """
        종목별 뉴스 수집
        
        Args:
            stock_code: 종목코드
        
        Returns:
            뉴스 리스트
        """
        url = f"{self.BASE_URL}/domestic/stock/{stock_code}/news"
        
        try:
            page = self.fetcher.fetch(url)
            
            news_list = []
            news_items = page.css('a[class*="news_item"]')
            
            for item in news_items[:10]:  # 최근 10개
                try:
                    title_elem = item.css_first('span[class*="title"]')
                    source_elem = item.css_first('span[class*="source"]')
                    time_elem = item.css_first('span[class*="time"]')
                    
                    if title_elem:
                        news_data = {
                            'title': title_elem.text.strip(),
                            'source': source_elem.text.strip() if source_elem else None,
                            'time': time_elem.text.strip() if time_elem else None,
                            'url': item.get('href')
                        }
                        news_list.append(news_data)
                except:
                    continue
            
            return {
                'stock_code': stock_code,
                'scraped_at': datetime.now().isoformat(),
                'status': 'success',
                'count': len(news_list),
                'news': news_list
            }
            
        except Exception as e:
            return {
                'stock_code': stock_code,
                'status': 'error',
                'error': str(e),
                'scraped_at': datetime.now().isoformat()
            }


def main():
    """테스트 실행"""
    print("=" * 60)
    print("🚀 Naver Stock Scraper Test (Scrapling)")
    print("=" * 60)
    
    scraper = NaverStockScraper()
    
    # 1. 시장 지수
    print("\n📊 Fetching market indices...")
    indices = scraper.get_market_indices()
    print(f"   Status: {indices.get('status')}")
    if indices.get('status') == 'success':
        for idx in indices.get('indices', []):
            print(f"   • {idx['name']}: {idx['price']}")
    
    # 2. 개별 종목 시세
    print("\n📈 Fetching Samsung Electronics (005930)...")
    quote = scraper.get_stock_quote('005930')
    print(f"   Status: {quote.get('status')}")
    if quote.get('status') == 'success':
        print(f"   • Name: {quote.get('name')}")
        print(f"   • Price: {quote.get('current_price'):,}원")
        print(f"   • Change: {quote.get('change')}")
        print(f"   • Volume: {quote.get('volume'):,}")
        print(f"   • Market Cap: {quote.get('market_cap')}")
        print(f"   • PER: {quote.get('per')}")
        print(f"   • PBR: {quote.get('pbr')}")
        print(f"   • EPS: {quote.get('eps')}")
        print(f"   • BPS: {quote.get('bps')}")
        print(f"   • Dividend Yield: {quote.get('dividend_yield')}%")
    
    # 3. 상위 종목 (시총)
    print("\n🏆 Fetching TOP 5 KOSPI stocks by market cap...")
    top_stocks = scraper.get_top_stocks('kospi', 'market_cap')
    if top_stocks.get('status') == 'success':
        for stock in top_stocks.get('stocks', [])[:5]:
            print(f"   {stock['rank']}. {stock['name']} ({stock['code']}): {stock['price']}원")
    
    # 4. 업종별 등띠
    print("\n📊 Fetching sector performance...")
    sectors = scraper.get_sector_performance()
    if sectors.get('status') == 'success':
        for sector in sectors.get('sectors', [])[:5]:
            print(f"   • {sector['name']}: {sector['change']}")
    
    # 5. 뉴스
    print("\n📰 Fetching news for Samsung Electronics...")
    news = scraper.get_news('005930')
    if news.get('status') == 'success':
        for item in news.get('news', [])[:3]:
            print(f"   • [{item['source']}] {item['title'][:40]}...")
    
    # 결과 저장
    output = {
        'scraped_at': datetime.now().isoformat(),
        'indices': indices,
        'samsung_quote': quote,
        'top_stocks': top_stocks,
        'sectors': sectors,
        'news': news
    }
    
    output_file = f'/home/programs/kstock_analyzer/data/naver_scrape_{datetime.now().strftime("%Y%m%d_%H%M")}.json'
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(output, f, indent=2, ensure_ascii=False)
    
    print(f"\n💾 Results saved: {output_file}")
    print("=" * 60)


if __name__ == '__main__':
    main()
