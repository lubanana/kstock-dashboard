#!/usr/bin/env python3
"""
개선된 뉴스 수집 시스템 v2.2
- 네이버 오픈 API (Client ID/Secret 필요)
- RSS 피드 (실제 검증된 URL)
- urllib + XML 파싱
"""

import urllib.request
import urllib.parse
import json
import xml.etree.ElementTree as ET
from datetime import datetime
from typing import List, Dict
import os
import ssl

# SSL 인증서 검증 비활성화 (일부 사이트용)
ssl._create_default_https_context = ssl._create_unverified_context

class NewsCollectorAPI:
    def __init__(self):
        self.client_id = os.getenv('NAVER_CLIENT_ID', '')
        self.client_secret = os.getenv('NAVER_CLIENT_SECRET', '')
    
    def fetch_naver_api(self, query: str = "주식", display: int = 20) -> List[Dict]:
        """네이버 검색 API (공식) - Client ID/Secret 필요"""
        print(f"📡 네이버 API 검색 '{query}' 수집 중...")
        
        if not self.client_id or not self.client_secret:
            print("   ⚠️ NAVER_CLIENT_ID/SECRET 없음 - API 사용 불가")
            return []
        
        try:
            enc_text = urllib.parse.quote(query)
            url = f"https://openapi.naver.com/v1/search/news?query={enc_text}&display={display}&sort=sim"
            
            request = urllib.request.Request(url)
            request.add_header("X-Naver-Client-Id", self.client_id)
            request.add_header("X-Naver-Client-Secret", self.client_secret)
            
            response = urllib.request.urlopen(request)
            rescode = response.getcode()
            
            if rescode == 200:
                data = json.loads(response.read().decode('utf-8'))
                
                articles = []
                for item in data.get('items', []):
                    articles.append({
                        'source': '네이버API',
                        'title': item.get('title', '').replace('<b>', '').replace('</b>', ''),
                        'link': item.get('link', ''),
                        'published': item.get('pubDate', ''),
                        'summary': item.get('description', '').replace('<b>', '').replace('</b>', '')[:150]
                    })
                
                print(f"   ✅ {len(articles)}개 수집")
                return articles
            else:
                print(f"   ❌ Error Code: {rescode}")
                return []
                
        except Exception as e:
            print(f"   ❌ 실패: {e}")
            return []
    
    def fetch_yonhap_rss(self) -> List[Dict]:
        """연합뉴스 RSS - 경제"""
        print("📡 연합뉴스 RSS 수집 중...")
        
        try:
            # 연합뉴스 경제 RSS (검증된 URL)
            url = "http://www.yonhapnewstv.co.kr/browse/feed/"
            
            request = urllib.request.Request(url, headers={
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            })
            
            response = urllib.request.urlopen(request, timeout=10)
            tree = ET.parse(response)
            root = tree.getroot()
            
            articles = []
            for item in root.findall('.//item')[:15]:
                title = item.find('title').text if item.find('title') is not None else ''
                link = item.find('link').text if item.find('link') is not None else ''
                pub_date = item.find('pubDate').text if item.find('pubDate') is not None else ''
                desc = item.find('description').text if item.find('description') is not None else ''
                
                articles.append({
                    'source': '연합뉴스',
                    'title': title,
                    'link': link,
                    'published': pub_date,
                    'summary': desc[:150] + '...' if len(desc) > 150 else desc
                })
            
            print(f"   ✅ {len(articles)}개 수집")
            return articles
            
        except Exception as e:
            print(f"   ❌ 실패: {e}")
            return []
    
    def fetch_reuters_kr(self) -> List[Dict]:
        """로이터 한국어 RSS"""
        print("📡 로이터 한국어 RSS 수집 중...")
        
        try:
            # 로이터 글로벌 마켓 RSS
            url = "https://www.reutersagency.com/feed/?taxonomy=markets&post_type=reuters-best"
            
            request = urllib.request.Request(url, headers={
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            })
            
            response = urllib.request.urlopen(request, timeout=10)
            tree = ET.parse(response)
            root = tree.getroot()
            
            articles = []
            for item in root.findall('.//item')[:10]:
                title = item.find('title').text if item.find('title') is not None else ''
                link = item.find('link').text if item.find('link') is not None else ''
                pub_date = item.find('pubDate').text if item.find('pubDate') is not None else ''
                
                articles.append({
                    'source': '로이터',
                    'title': title,
                    'link': link,
                    'published': pub_date,
                    'summary': ''
                })
            
            print(f"   ✅ {len(articles)}개 수집")
            return articles
            
        except Exception as e:
            print(f"   ❌ 실패: {e}")
            return []
    
    def fetch_coindesk(self) -> List[Dict]:
        """CoinDesk RSS (암호화폐)"""
        print("📡 CoinDesk RSS 수집 중...")
        
        try:
            url = "https://www.coindesk.com/arc/outboundfeeds/rss/"
            
            request = urllib.request.Request(url, headers={
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            })
            
            response = urllib.request.urlopen(request, timeout=10)
            tree = ET.parse(response)
            root = tree.getroot()
            
            articles = []
            for item in root.findall('.//item')[:10]:
                title = item.find('title').text if item.find('title') is not None else ''
                link = item.find('link').text if item.find('link') is not None else ''
                pub_date = item.find('pubDate').text if item.find('pubDate') is not None else ''
                
                articles.append({
                    'source': 'CoinDesk',
                    'title': title,
                    'link': link,
                    'published': pub_date,
                    'summary': ''
                })
            
            print(f"   ✅ {len(articles)}개 수집")
            return articles
            
        except Exception as e:
            print(f"   ❌ 실패: {e}")
            return []
    
    def fetch_mock_data(self) -> List[Dict]:
        """개발 테스트용 샘플 데이터"""
        print("📡 샘플 데이터 로드 중...")
        
        return [
            {
                'source': '샘플/네이버',
                'title': '삼성전자, 1분기 영업익 6.6조…전년比 932%↑',
                'link': 'https://n.news.naver.com/article/001/0012345678',
                'published': datetime.now().strftime('%Y-%m-%d %H:%M'),
                'summary': '삼성전자가 1분기 영업이익 6조6000억원을 기록하며 전년 동기 대비 932% 증가했다고 30일 공시했다.'
            },
            {
                'source': '샘플/연합',
                'title': '미국 3월 고용시장 둔화…비농업 일자리 12만개 증가',
                'link': 'https://www.yna.co.kr/view/AKR202503290123',
                'published': datetime.now().strftime('%Y-%m-%d %H:%M'),
                'summary': '미국의 3월 비농업 일자리가 12만개 증가하며 시장 전망치(13만5천개)를 밑돌았다.'
            },
            {
                'source': '샘플/코인데스크',
                'title': '비트코인, 7만달러 돌파 후 조정…현재 6.6만달러',
                'link': 'https://www.coindesk.com/markets/2025/03/29/',
                'published': datetime.now().strftime('%Y-%m-%d %H:%M'),
                'summary': '비트코인이 7만달러를 돌파한 후 조정을 받아 현재 6만6000달러대에서 거래되고 있다.'
            }
        ]
    
    def collect_all(self, use_mock: bool = False) -> List[Dict]:
        """전체 뉴스 수집"""
        print("="*70)
        print("🔍 개선된 뉴스 수집 시작 (v2.2)")
        print("="*70)
        
        if use_mock:
            return self.fetch_mock_data()
        
        all_news = []
        
        # 1. 네이버 API
        all_news.extend(self.fetch_naver_api("주식"))
        all_news.extend(self.fetch_naver_api("코스피"))
        all_news.extend(self.fetch_naver_api("비트코인"))
        
        # 2. RSS 피드
        all_news.extend(self.fetch_yonhap_rss())
        all_news.extend(self.fetch_reuters_kr())
        all_news.extend(self.fetch_coindesk())
        
        # 중복 제거
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
        
        os.makedirs(output_dir, exist_ok=True)
        
        # JSON
        json_path = f"{output_dir}/news_collection_{date_str}.json"
        with open(json_path, 'w', encoding='utf-8') as f:
            json.dump(news, f, ensure_ascii=False, indent=2)
        
        # Markdown
        md_path = f"{output_dir}/news_briefing_{date_str}.md"
        with open(md_path, 'w', encoding='utf-8') as f:
            f.write(f"# 📰 뉴스 브리핑 - {datetime.now().strftime('%Y년 %m월 %d일')}\n\n")
            f.write(f"**총 {len(news)}개 뉴스 수집** | 생성: {datetime.now().strftime('%H:%M')}\n\n")
            f.write("---\n\n")
            
            for item in news:
                f.write(f"## {item['title']}\n")
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
    collector = NewsCollectorAPI()
    
    # API 키 확인
    if not collector.client_id:
        print("\n⚠️  NAVER_CLIENT_ID/SECRET 환경변수가 설정되지 않았습니다.")
        print("    샘플 데이터로 대체합니다.\n")
        news = collector.collect_all(use_mock=True)
    else:
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
