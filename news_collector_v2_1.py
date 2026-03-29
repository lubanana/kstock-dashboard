#!/usr/bin/env python3
"""
개선된 뉴스 수집 시스템 v2.1
- 네이버 검색 API 활용
- requests + BeautifulSoup
- 대체 소스 다변화
"""

import requests
import time
import random
from datetime import datetime
from typing import List, Dict
import os
import json
from bs4 import BeautifulSoup

class ImprovedNewsCollector:
    def __init__(self):
        self.results = []
        self.user_agents = [
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0',
        ]
        self.session = requests.Session()
    
    def get_headers(self):
        return {
            'User-Agent': random.choice(self.user_agents),
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'ko-KR,ko;q=0.9,en-US;q=0.8,en;q=0.7',
            'Accept-Encoding': 'gzip, deflate, br',
            'Connection': 'keep-alive',
        }
    
    def safe_request(self, url: str, max_retries: int = 3) -> requests.Response:
        """안전한 요청"""
        for attempt in range(max_retries):
            try:
                headers = self.get_headers()
                response = self.session.get(url, headers=headers, timeout=15)
                
                if response.status_code == 200:
                    return response
                elif response.status_code == 403:
                    print(f"   ⚠️ 403, 재시도 {attempt+1}/{max_retries}")
                    time.sleep(2 * (attempt + 1))
                else:
                    time.sleep(1)
                    
            except Exception as e:
                print(f"   ⚠️ 오류: {e}")
                time.sleep(2)
        
        return None
    
    def fetch_naver_news_section(self, section_id: str = '101') -> List[Dict]:
        """네이버 뉴스 섹션 (경제/IT)"""
        print(f"📡 네이버 뉴스 섹션 {section_id} 수집 중...")
        
        try:
            # 네이버 뉴스 RSS (섹션별)
            # 101: 경제, 105: IT/과학
            url = f"https://news.naver.com/main/rss/nnd.naver?where=section&oid={section_id}"
            
            response = self.safe_request(url)
            if not response:
                # 대안: 네이버 뉴스 검색 페이지
                return self.fetch_naver_news_search()
            
            soup = BeautifulSoup(response.text, 'xml')
            items = soup.find_all('item')[:20]
            
            articles = []
            for item in items:
                try:
                    title = item.find('title').text if item.find('title') else ''
                    link = item.find('link').text if item.find('link') else ''
                    pub_date = item.find('pubDate').text if item.find('pubDate') else ''
                    desc = item.find('description').text if item.find('description') else ''
                    
                    articles.append({
                        'source': '네이버뉴스',
                        'title': title,
                        'link': link,
                        'published': pub_date,
                        'summary': desc[:150] + '...' if len(desc) > 150 else desc
                    })
                except:
                    continue
            
            print(f"   ✅ {len(articles)}개 수집")
            return articles
            
        except Exception as e:
            print(f"   ❌ 실패: {e}")
            return self.fetch_naver_news_search()
    
    def fetch_naver_news_search(self, query: str = "주식") -> List[Dict]:
        """네이버 뉴스 검색 (대체 방법)"""
        print(f"📡 네이버 뉴스 검색 '{query}' 수집 중...")
        
        try:
            # 네이버 검색 (news only)
            url = f"https://search.naver.com/search.naver?where=news&query={query}&sort=1"  # sort=1: 최신순
            
            response = self.safe_request(url)
            if not response:
                return []
            
            soup = BeautifulSoup(response.text, 'html.parser')
            
            articles = []
            # 뉴스 아이템 선택자
            news_items = soup.select('.news_area, .list_news .bx')[:15]
            
            for item in news_items:
                try:
                    title_elem = item.select_one('.news_tit a, .tit a')
                    if not title_elem:
                        continue
                    
                    title = title_elem.get_text(strip=True)
                    link = title_elem.get('href', '')
                    
                    # 언론사
                    press_elem = item.select_one('.info.press, .press')
                    press = press_elem.get_text(strip=True) if press_elem else '네이버'
                    
                    # 요약
                    summary_elem = item.select_one('.dsc_wrap .dsc, .api_txt_lines')
                    summary = summary_elem.get_text(strip=True) if summary_elem else ''
                    
                    articles.append({
                        'source': f'네이버/{press}',
                        'title': title,
                        'link': link,
                        'published': datetime.now().strftime('%Y-%m-%d %H:%M'),
                        'summary': summary[:150] + '...' if len(summary) > 150 else summary
                    })
                    
                except Exception as e:
                    continue
            
            print(f"   ✅ {len(articles)}개 수집")
            return articles
            
        except Exception as e:
            print(f"   ❌ 실패: {e}")
            return []
    
    def fetch_naver_finance_news(self) -> List[Dict]:
        """네이버 금융 뉴스"""
        print("📡 네이버 금융 뉴스 수집 중...")
        
        try:
            url = "https://finance.naver.com/news/news_list.naver?mode=LSS2D&section_id=101&section_id2=258"
            
            response = self.safe_request(url)
            if not response:
                return []
            
            soup = BeautifulSoup(response.text, 'html.parser')
            
            articles = []
            news_items = soup.select('.realtimeNewsList dl, .newsList dl')[:15]
            
            for item in news_items:
                try:
                    # 제목
                    title_elem = item.select_one('dt a, dd.articleSubject a')
                    if not title_elem:
                        continue
                    
                    title = title_elem.get_text(strip=True)
                    link = title_elem.get('href', '')
                    if link.startswith('/'):
                        link = f"https://finance.naver.com{link}"
                    
                    # 언론사
                    press_elem = item.select_one('.press, .writing')
                    press = press_elem.get_text(strip=True) if press_elem else '네이버금융'
                    
                    # 요약
                    summary_elem = item.select_one('.articleSummary, dd:not(.articleSubject)')
                    summary = summary_elem.get_text(strip=True) if summary_elem else ''
                    
                    # 날짜
                    date_elem = item.select_one('.wdate, .date')
                    date = date_elem.get_text(strip=True) if date_elem else datetime.now().strftime('%Y-%m-%d')
                    
                    articles.append({
                        'source': f'네이버금융/{press}',
                        'title': title,
                        'link': link,
                        'published': date,
                        'summary': summary[:150] + '...' if len(summary) > 150 else summary
                    })
                    
                except:
                    continue
            
            print(f"   ✅ {len(articles)}개 수집")
            return articles
            
        except Exception as e:
            print(f"   ❌ 실패: {e}")
            return []
    
    def fetch_daum_finance_news(self) -> List[Dict]:
        """다음 금융 뉴스 (대체 소스)"""
        print("📡 다음 금융 뉴스 수집 중...")
        
        try:
            url = "https://finance.daum.net/news"
            
            response = self.safe_request(url)
            if not response:
                return []
            
            soup = BeautifulSoup(response.text, 'html.parser')
            
            articles = []
            news_items = soup.select('.list_news .item_news, .box_news')[:15]
            
            for item in news_items:
                try:
                    title_elem = item.select_one('.tit_news a, .link_txt')
                    if not title_elem:
                        continue
                    
                    title = title_elem.get_text(strip=True)
                    link = title_elem.get('href', '')
                    
                    press_elem = item.select_one('.info_news, .source')
                    press = press_elem.get_text(strip=True) if press_elem else '다음'
                    
                    articles.append({
                        'source': f'다음/{press}',
                        'title': title,
                        'link': link,
                        'published': datetime.now().strftime('%Y-%m-%d %H:%M'),
                        'summary': ''
                    })
                    
                except:
                    continue
            
            print(f"   ✅ {len(articles)}개 수집")
            return articles
            
        except Exception as e:
            print(f"   ❌ 실패: {e}")
            return []
    
    def fetch_bigkinds_trend(self) -> List[Dict]:
        """Bigkinds 금융 뉴스 트렌드"""
        print("📡 Bigkinds 트렌드 수집 중...")
        
        try:
            # Bigkinds API (간접 접근)
            url = "https://www.bigkinds.or.kr/v2/news/popularKeyword.do"
            
            response = self.safe_request(url)
            if not response:
                return []
            
            # 키워드 기반 뉴스 검색으로 대체
            keywords = ["삼성전자", "코스피", "코스닥", "기준금리", "주식시장"]
            articles = []
            
            for keyword in keywords[:3]:  # 상위 3개만
                time.sleep(1)
                news = self.fetch_naver_news_search(keyword)
                articles.extend(news[:3])  # 키워드당 3개
            
            print(f"   ✅ {len(articles)}개 수집")
            return articles
            
        except Exception as e:
            print(f"   ❌ 실패: {e}")
            return []
    
    def collect_all(self) -> List[Dict]:
        """전체 뉴스 수집"""
        print("="*70)
        print("🔍 개선된 뉴스 수집 시작 (v2.1)")
        print("="*70)
        
        all_news = []
        
        # 1. 네이버 뉴스 (RSS)
        all_news.extend(self.fetch_naver_news_section('101'))  # 경제
        time.sleep(1)
        
        # 2. 네이버 금융 (스크래핑)
        all_news.extend(self.fetch_naver_finance_news())
        time.sleep(2)
        
        # 3. 네이버 뉴스 검색 (대체)
        all_news.extend(self.fetch_naver_news_search("증시"))
        time.sleep(1)
        
        # 4. 다음 금융 (대체)
        all_news.extend(self.fetch_daum_finance_news())
        time.sleep(1)
        
        # 5. 키워드 기반 수집
        all_news.extend(self.fetch_bigkinds_trend())
        
        # 중복 제거
        seen = set()
        unique_news = []
        for news in all_news:
            if news['title'] not in seen and len(news['title']) > 10:
                seen.add(news['title'])
                unique_news.append(news)
        
        print("\n" + "="*70)
        print(f"✅ 총 {len(unique_news)}개 뉴스 수집 완료")
        print("="*70)
        
        return unique_news
    
    def save_report(self, news: List[Dict], output_dir: str = "/root/.openclaw/workspace/strg/docs"):
        """리포트 저장"""
        date_str = datetime.now().strftime('%Y%m%d')
        
        os.makedirs(output_dir, exist_ok=True)
        
        # JSON
        json_path = f"{output_dir}/news_collection_{date_str}.json"
        with open(json_path, 'w', encoding='utf-8') as f:
            json.dump(news, f, ensure_ascii=False, indent=2)
        
        # Markdown
        md_path = f"{output_dir}/news_briefing_{date_str}.md"
        with open(md_path, 'w', encoding='utf-8') as f:
            f.write(f"# 📰 뉴스 브리핑 - {datetime.now().strftime('%Y년 %m월 %d일')}\n\n")
            f.write(f"**총 {len(news)}개 뉴스 수집**\n\n")
            f.write("| 순번 | 출처 | 제목 | 시간 |\n")
            f.write("|:---:|:---|:---|:---|\n")
            
            for i, item in enumerate(news, 1):
                title_short = item['title'][:40] + "..." if len(item['title']) > 40 else item['title']
                f.write(f"| {i} | {item['source']} | [{title_short}]({item['link']}) | {item['published']} |\n")
            
            f.write("\n---\n\n## 상세 내용\n\n")
            for item in news[:20]:
                f.write(f"### {item['title']}\n")
                f.write(f"- **출처**: {item['source']}\n")
                f.write(f"- **시간**: {item['published']}\n")
                f.write(f"- **링크**: {item['link']}\n")
                if item['summary']:
                    f.write(f"- **요약**: {item['summary']}\n")
                f.write("\n")
        
        print(f"\n📄 리포트 저장:")
        print(f"   JSON: {json_path}")
        print(f"   Markdown: {md_path}")
        
        return json_path, md_path

def main():
    collector = ImprovedNewsCollector()
    news = collector.collect_all()
    
    if news:
        collector.save_report(news)
        
        print("\n📋 샘플 뉴스:")
        for i, item in enumerate(news[:5], 1):
            print(f"  {i}. [{item['source']}] {item['title'][:50]}...")
    else:
        print("\n⚠️ 수집된 뉴스 없음")

if __name__ == "__main__":
    main()
