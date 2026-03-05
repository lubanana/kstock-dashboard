#!/usr/bin/env python3
"""
Naver Stock News Scraper
네이버 주식 뉴스 스크래퍼

Target: https://m.stock.naver.com/investment/news/mainnews
"""

import json
import asyncio
from datetime import datetime
from typing import Dict, List
from playwright.async_api import async_playwright
from bs4 import BeautifulSoup


class NaverNewsScraper:
    """네이버 주식 뉴스 스크래퍼"""
    
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
                await page.goto(url, wait_until='domcontentloaded', timeout=timeout)
                await asyncio.sleep(3)
                
                if wait_selector:
                    try:
                        await page.wait_for_selector(wait_selector, timeout=timeout, state='visible')
                    except:
                        pass
                
                await asyncio.sleep(2)
                content = await page.content()
                await browser.close()
                return content
                
            except Exception as e:
                await browser.close()
                raise e
    
    async def get_main_news(self) -> Dict:
        """
        네이버 주식 메인 뉴스 수집
        https://m.stock.naver.com/investment/news/mainnews
        """
        url = f"{self.BASE_URL}/investment/news/mainnews"
        
        try:
            html = await self.fetch_page(url, wait_selector='[class*="news"], [class*="list"]')
            soup = BeautifulSoup(html, 'html.parser')
            
            news_list = []
            
            # 뉴스 아이템 선택자들
            news_selectors = [
                'a[href*="/news/article/"]',
                '[class*="news_item"]',
                '[class*="NewsItem"]',
                'li a[href*="news"]',
                '.list_item'
            ]
            
            for selector in news_selectors:
                items = soup.select(selector)
                if items:
                    for item in items[:20]:  # 최근 20개
                        try:
                            # 제목
                            title = None
                            title_selectors = ['.title', '[class*="title"]', 'strong', 'h3', 'span']
                            for ts in title_selectors:
                                title_elem = item.select_one(ts)
                                if title_elem and title_elem.text.strip():
                                    title = title_elem.text.strip()
                                    break
                            
                            if not title:
                                title = item.get_text(strip=True)[:100]
                            
                            # 언론사
                            source = None
                            source_selectors = ['.source', '[class*="source"]', '[class*="press"]', '.info']
                            for ss in source_selectors:
                                source_elem = item.select_one(ss)
                                if source_elem:
                                    source = source_elem.text.strip()
                                    break
                            
                            # 시간
                            time_str = None
                            time_selectors = ['.time', '[class*="time"]', '[class*="date"]', '.info']
                            for tms in time_selectors:
                                time_elem = item.select_one(tms)
                                if time_elem:
                                    time_str = time_elem.text.strip()
                                    break
                            
                            # URL
                            news_url = item.get('href')
                            if news_url and not news_url.startswith('http'):
                                news_url = self.BASE_URL + news_url
                            
                            if title and title not in [n['title'] for n in news_list]:
                                news_list.append({
                                    'title': title,
                                    'source': source or '네이버증권',
                                    'time': time_str,
                                    'url': news_url or url,
                                    'scraped_at': datetime.now().isoformat()
                                })
                        except:
                            continue
                    break  # 선택자가 작동하면 중단
            
            return {
                'source': 'naver_stock_main_news',
                'url': url,
                'scraped_at': datetime.now().isoformat(),
                'status': 'success',
                'count': len(news_list),
                'news': news_list
            }
            
        except Exception as e:
            return {
                'source': 'naver_stock_main_news',
                'url': url,
                'status': 'error',
                'error': str(e),
                'scraped_at': datetime.now().isoformat()
            }
    
    async def get_stock_news(self, stock_code: str) -> Dict:
        """
        특정 종목 관련 뉴스 수집
        """
        url = f"{self.BASE_URL}/domestic/stock/{stock_code}/news"
        
        try:
            html = await self.fetch_page(url, wait_selector='[class*="news"]')
            soup = BeautifulSoup(html, 'html.parser')
            
            news_list = []
            items = soup.select('a[href*="/news/article/"], [class*="news_item"]')[:10]
            
            for item in items:
                try:
                    title_elem = item.select_one('.title, [class*="title"], strong')
                    source_elem = item.select_one('.source, [class*="source"]')
                    time_elem = item.select_one('.time, [class*="time"]')
                    
                    if title_elem:
                        news_list.append({
                            'title': title_elem.text.strip(),
                            'source': source_elem.text.strip() if source_elem else '네이버증권',
                            'time': time_elem.text.strip() if time_elem else None,
                            'url': item.get('href') if item.get('href') else url,
                            'scraped_at': datetime.now().isoformat()
                        })
                except:
                    continue
            
            return {
                'stock_code': stock_code,
                'source': 'naver_stock_news',
                'url': url,
                'scraped_at': datetime.now().isoformat(),
                'status': 'success',
                'count': len(news_list),
                'news': news_list
            }
            
        except Exception as e:
            return {
                'stock_code': stock_code,
                'source': 'naver_stock_news',
                'url': url,
                'status': 'error',
                'error': str(e),
                'scraped_at': datetime.now().isoformat()
            }
    
    def analyze_sentiment(self, news_list: List[Dict]) -> Dict:
        """
        뉴스 감성 분석
        """
        positive_keywords = [
            '상승', '호재', '성장', '돌파', '강세', '매수', 'upgrade', 'beat',
            'growth', 'surge', 'rally', 'strong', 'bullish', 'outperform',
            '급등', '신고가', '기대감', '호실적', '증가', '확대', '수주',
            'rise', 'gain', 'jump', 'soar', 'boost', 'positive', 'profit'
        ]
        
        negative_keywords = [
            '하락', '악재', '감소', '하락세', '매도', 'downgrade', 'miss',
            'decline', 'drop', 'weak', 'bearish', 'underperform',
            '급락', '신저가', '우려', '적자', '감소', '축소', '해지',
            'fall', 'loss', 'crash', 'plunge', 'tumble', 'negative', 'deficit'
        ]
        
        positive_count = 0
        negative_count = 0
        neutral_count = 0
        
        for news in news_list:
            title = news.get('title', '').lower()
            
            pos_score = sum(1 for kw in positive_keywords if kw in title)
            neg_score = sum(1 for kw in negative_keywords if kw in title)
            
            if pos_score > neg_score:
                positive_count += 1
                news['sentiment'] = 'positive'
            elif neg_score > pos_score:
                negative_count += 1
                news['sentiment'] = 'negative'
            else:
                neutral_count += 1
                news['sentiment'] = 'neutral'
        
        total = len(news_list)
        if total > 0:
            sentiment_score = (positive_count / total) * 100
        else:
            sentiment_score = 50
        
        return {
            'total_news': total,
            'positive': positive_count,
            'negative': negative_count,
            'neutral': neutral_count,
            'sentiment_score': round(sentiment_score, 2),
            'sentiment_label': 'Bullish' if sentiment_score >= 60 else 'Bearish' if sentiment_score <= 40 else 'Neutral'
        }


async def main():
    """테스트 실행"""
    print("=" * 60)
    print("📰 Naver Stock News Scraper Test")
    print("=" * 60)
    
    scraper = NaverNewsScraper()
    
    # 1. 메인 뉴스
    print("\n📰 Fetching main news...")
    main_news = await scraper.get_main_news()
    print(f"   Status: {main_news.get('status')}")
    
    if main_news.get('status') == 'success':
        print(f"   Count: {main_news.get('count')} articles")
        
        # 감성 분석
        sentiment = scraper.analyze_sentiment(main_news.get('news', []))
        print(f"\n   📊 Sentiment Analysis:")
        print(f"      Score: {sentiment['sentiment_score']:.1f}/100 ({sentiment['sentiment_label']})")
        print(f"      Positive: {sentiment['positive']}, Negative: {sentiment['negative']}, Neutral: {sentiment['neutral']}")
        
        print(f"\n   📰 Top 5 News:")
        for i, news in enumerate(main_news.get('news', [])[:5], 1):
            emoji = "🟢" if news.get('sentiment') == 'positive' else "🔴" if news.get('sentiment') == 'negative' else "⚪"
            print(f"      {emoji} {i}. {news['title'][:50]}...")
            print(f"         [{news.get('source', 'N/A')}] {news.get('time', '')}")
    else:
        print(f"   Error: {main_news.get('error')}")
    
    # 2. 삼성전자 뉴스
    print("\n📰 Fetching Samsung Electronics news...")
    stock_news = await scraper.get_stock_news('005930')
    if stock_news.get('status') == 'success':
        print(f"   Count: {stock_news.get('count')} articles")
        for i, news in enumerate(stock_news.get('news', [])[:3], 1):
            print(f"      {i}. {news['title'][:40]}...")
    else:
        print(f"   Error: {stock_news.get('error')}")
    
    # 결과 저장
    output = {
        'scraped_at': datetime.now().isoformat(),
        'main_news': main_news,
        'stock_news': stock_news
    }
    
    output_file = f'/home/programs/kstock_analyzer/data/naver_news_{datetime.now().strftime("%Y%m%d_%H%M")}.json'
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(output, f, indent=2, ensure_ascii=False)
    
    print(f"\n💾 Results saved: {output_file}")
    print("=" * 60)
    
    return main_news


if __name__ == '__main__':
    result = asyncio.run(main())
