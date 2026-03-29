#!/usr/bin/env python3
"""
개선된 뉴스 수집 시스템 v2.0
- RSS 피드 활용
- User-Agent 로테이션
- 대체 소스 통합
- 재시도 로직 강화
"""

import feedparser
import requests
import time
import random
from datetime import datetime, timedelta
from typing import List, Dict
import os
import json

class NewsCollector:
    def __init__(self):
        self.results = []
        self.user_agents = [
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.0',
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0',
            'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2.1 Safari/605.1.15'
        ]
        self.session = requests.Session()
    
    def get_headers(self):
        """랜덤 User-Agent 헤더 반환"""
        return {
            'User-Agent': random.choice(self.user_agents),
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'ko-KR,ko;q=0.9,en-US;q=0.8,en;q=0.7',
            'Accept-Encoding': 'gzip, deflate, br',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1'
        }
    
    def safe_request(self, url: str, max_retries: int = 3, delay: float = 1.0) -> requests.Response:
        """안전한 요청 (재시도 로직 포함)"""
        for attempt in range(max_retries):
            try:
                headers = self.get_headers()
                response = self.session.get(url, headers=headers, timeout=15)
                
                if response.status_code == 200:
                    return response
                elif response.status_code == 403:
                    print(f"   ⚠️ 403 Forbidden, 재시도 {attempt+1}/{max_retries}")
                    time.sleep(delay * (attempt + 1) + random.uniform(0.5, 1.5))
                else:
                    print(f"   ⚠️ 상태 {response.status_code}, 재시도 {attempt+1}/{max_retries}")
                    time.sleep(delay)
                    
            except Exception as e:
                print(f"   ⚠️ 요청 실패: {e}, 재시도 {attempt+1}/{max_retries}")
                time.sleep(delay * (attempt + 1))
        
        return None
    
    def fetch_rss(self, name: str, url: str) -> List[Dict]:
        """RSS 피드 수집"""
        print(f"📡 {name} RSS 수집 중...")
        
        try:
            # RSS 파싱
            feed = feedparser.parse(url)
            
            if feed.bozo:
                print(f"   ⚠️ RSS 파싱 경고: {feed.bozo_exception}")
            
            articles = []
            for entry in feed.entries[:20]:  # 최근 20개
                article = {
                    'source': name,
                    'title': entry.get('title', ''),
                    'link': entry.get('link', ''),
                    'published': entry.get('published', ''),
                    'summary': entry.get('summary', '')[:200] + '...' if len(entry.get('summary', '')) > 200 else entry.get('summary', '')
                }
                articles.append(article)
            
            print(f"   ✅ {len(articles)}개 수집")
            return articles
            
        except Exception as e:
            print(f"   ❌ RSS 수집 실패: {e}")
            return []
    
    def fetch_edaily(self) -> List[Dict]:
        """이데일리 RSS (경제/증권)"""
        # 이데일리 주요뉴스 RSS
        url = "https://www.edaily.co.kr/rss/"
        return self.fetch_rss("이데일리", url)
    
    def fetch_yonhap(self) -> List[Dict]:
        """연합뉴스 RSS (경제)"""
        # 연합뉴스 경제 RSS
        url = "http://www.yonhapnews.co.kr/rss/economy.xml"
        return self.fetch_rss("연합뉴스", url)
    
    def fetch_newsis(self) -> List[Dict]:
        """뉴시스 RSS (증권)"""
        # 뉴시스 증권 RSS
        url = "http://www.newsis.com/rss/stock.xml"
        return self.fetch_rss("뉴시스", url)
    
    def fetch_naver_finance_news(self) -> List[Dict]:
        """네이버 금융 뉴스 (Scrapling 사용)"""
        print("📡 네이버 금융 뉴스 수집 중...")
        
        try:
            from scrapling import Fetcher
            
            fetcher = Fetcher()
            url = "https://finance.naver.com/news/news_list.naver?mode=LSS2D&section_id=101&section_id2=258"
            
            time.sleep(random.uniform(1, 2))  # 요청 간 지연
            
            page = fetcher.get(url, stealth=True)
            
            articles = []
            news_items = page.css('dl')
            
            for item in news_items[:15]:
                try:
                    title_elem = item.css('dt.photo a, dd.articleSubject a')
                    if not title_elem:
                        continue
                    
                    title = title_elem.text(strip=True)
                    link = title_elem.attrs.get('href', '')
                    if link.startswith('/'):
                        link = f"https://finance.naver.com{link}"
                    
                    # 요약 추출
                    summary_elem = item.css('dd.articleSummary')
                    summary = summary_elem.text(strip=True) if summary_elem else ''
                    
                    # 언론사 추출
                    press_elem = item.css('span.press, span.writing')
                    press = press_elem.text(strip=True) if press_elem else '네이버금융'
                    
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
            print(f"   ❌ 네이버 금융 수집 실패: {e}")
            return []
    
    def fetch_dart_disclosure(self) -> List[Dict]:
        """DART 공시 정보 (OpenDartReader)"""
        print("📡 DART 공시 수집 중...")
        
        try:
            import OpenDartReader
            
            # API 키는 환경변수에서 로드
            api_key = os.getenv('DART_API_KEY', '')
            if not api_key:
                print("   ⚠️ DART_API_KEY 없음, 건설된 공시만 수집")
                return []
            
            dart = OpenDartReader(api_key)
            
            # 오늘 공시 조회
            today = datetime.now().strftime('%Y%m%d')
            disclosures = dart.list(start=today, end=today)
            
            if disclosures.empty:
                print("   ℹ️ 오늘 공시 없음")
                return []
            
            articles = []
            for _, row in disclosures.head(20).iterrows():
                articles.append({
                    'source': 'DART',
                    'title': f"[{row['corp_name']}] {row['report_nm']}",
                    'link': f"https://dart.fss.or.kr/dsaf001/main.do?rcpNo={row['rcept_no']}",
                    'published': row['rcept_dt'],
                    'summary': f"공시유형: {row.get('flr_nm', 'N/A')}"
                })
            
            print(f"   ✅ {len(articles)}개 수집")
            return articles
            
        except Exception as e:
            print(f"   ❌ DART 수집 실패: {e}")
            return []
    
    def fetch_krx_market(self) -> List[Dict]:
        """KRX 시장동향"""
        print("📡 KRX 시장동향 수집 중...")
        
        try:
            url = "http://www.krx.co.kr/main/main.jsp"
            response = self.safe_request(url)
            
            if not response:
                return []
            
            from bs4 import BeautifulSoup
            soup = BeautifulSoup(response.text, 'html.parser')
            
            articles = []
            # KRX 시장 뉴스 (구조에 따라 조정 필요)
            news_items = soup.select('.news-list li, .market-news li')[:10]
            
            for item in news_items:
                try:
                    title_elem = item.select_one('a')
                    if not title_elem:
                        continue
                    
                    articles.append({
                        'source': 'KRX',
                        'title': title_elem.text.strip(),
                        'link': title_elem.get('href', ''),
                        'published': datetime.now().strftime('%Y-%m-%d'),
                        'summary': ''
                    })
                except:
                    continue
            
            print(f"   ✅ {len(articles)}개 수집")
            return articles
            
        except Exception as e:
            print(f"   ❌ KRX 수집 실패: {e}")
            return []
    
    def collect_all(self) -> List[Dict]:
        """전체 뉴스 수집"""
        print("="*70)
        print("🔍 개선된 뉴스 수집 시작 (v2.0)")
        print("="*70)
        
        all_news = []
        
        # 1. RSS 피드 (안정적)
        all_news.extend(self.fetch_edaily())
        time.sleep(1)
        
        all_news.extend(self.fetch_yonhap())
        time.sleep(1)
        
        all_news.extend(self.fetch_newsis())
        time.sleep(1)
        
        # 2. 스크래핑 (주의 필요)
        all_news.extend(self.fetch_naver_finance_news())
        time.sleep(2)
        
        # 3. 공식 API
        all_news.extend(self.fetch_dart_disclosure())
        time.sleep(1)
        
        # 4. 대체 소스
        all_news.extend(self.fetch_krx_market())
        
        # 중복 제거 (제목 기준)
        seen = set()
        unique_news = []
        for news in all_news:
            if news['title'] not in seen:
                seen.add(news['title'])
                unique_news.append(news)
        
        print("\n" + "="*70)
        print(f"✅ 총 {len(unique_news)}개 뉴스 수집 완료")
        print("="*70)
        
        return unique_news
    
    def save_report(self, news: List[Dict], output_dir: str = "/root/.openclaw/workspace/strg/docs"):
        """리포트 저장"""
        date_str = datetime.now().strftime('%Y%m%d')
        
        # JSON 저장
        json_path = f"{output_dir}/news_collection_{date_str}.json"
        with open(json_path, 'w', encoding='utf-8') as f:
            json.dump(news, f, ensure_ascii=False, indent=2)
        
        # Markdown 저장
        md_path = f"{output_dir}/news_briefing_{date_str}.md"
        with open(md_path, 'w', encoding='utf-8') as f:
            f.write(f"# 📰 뉴스 브리핑 - {datetime.now().strftime('%Y년 %m월 %d일')}\n\n")
            f.write(f"**총 {len(news)}개 뉴스 수집**\n\n")
            f.write("---\n\n")
            
            # 소스별 분류
            sources = {}
            for item in news:
                src = item['source'].split('/')[0]
                sources.setdefault(src, []).append(item)
            
            for source, items in sources.items():
                f.write(f"## {source} ({len(items)}개)\n\n")
                for item in items[:10]:  # 소스당 최대 10개
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
    """메인 실행"""
    collector = NewsCollector()
    
    # 뉴스 수집
    news = collector.collect_all()
    
    # 리포트 저장
    if news:
        os.makedirs("/root/.openclaw/workspace/strg/docs", exist_ok=True)
        collector.save_report(news)
        
        # 샘플 출력
        print("\n📋 샘플 뉴스 (최근 5개):")
        for i, item in enumerate(news[:5], 1):
            print(f"  {i}. [{item['source']}] {item['title'][:50]}...")
    else:
        print("\n⚠️ 수집된 뉴스 없음")

if __name__ == "__main__":
    main()
