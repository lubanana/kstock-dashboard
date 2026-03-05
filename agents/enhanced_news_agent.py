#!/usr/bin/env python3
"""
Enhanced News Sentiment Agent (NEWS_001)
개선된 뉴스 센티먼트 분석 에이전트
- 네이버 뉴스 RSS
- 구글 뉴스 RSS
- yfinance 뉴스
- 종합 감성 분석
"""

import yfinance as yf
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Optional
import json
import sys
import re
import feedparser
import urllib.request
import urllib.parse
import ssl

# SSL 검증 비활성화 (일부 RSS 피드용)
ssl._create_default_https_context = ssl._create_unverified_context


class EnhancedNewsAgent:
    """개선된 뉴스 센티먼트 분석 에이전트"""

    def __init__(self, symbol: str, name: str = ""):
        self.symbol = symbol
        self.name = name or symbol
        self.ticker = None
        self.news_data = {
            'yfinance': [],
            'naver': [],
            'google': [],
            'trends24': [],
            'naver_stock': []
        }
        self.price_data = None

        # 감성 키워드 사전
        self.positive_keywords = [
            '상승', '호재', '성장', '돌파', '강세', '매수', 'upgrade', 'beat',
            'growth', 'surge', 'rally', 'strong', 'bullish', 'outperform',
            '급등', '신고가', '기대감', '호실적', '증가', '확대', '수주',
            'rise', 'gain', 'jump', 'soar', 'boost', 'positive', 'profit'
        ]

        self.negative_keywords = [
            '하락', '악재', '감소', '하락세', '매도', 'downgrade', 'miss',
            'decline', 'drop', 'weak', 'bearish', 'underperform',
            '급락', '신저가', '우려', '적자', '감소', '축소', '해지',
            'fall', 'loss', 'crash', 'plunge', 'tumble', 'negative', 'deficit'
        ]

    def fetch_yfinance_news(self) -> List[Dict]:
        """yfinance 뉴스 수집"""
        try:
            self.ticker = yf.Ticker(self.symbol)
            news = self.ticker.news or []
            self.price_data = self.ticker.history(period='30d')

            processed = []
            for item in news[:20]:  # 최근 20개
                processed.append({
                    'source': 'yfinance',
                    'title': item.get('title', ''),
                    'summary': item.get('summary', ''),
                    'publisher': item.get('publisher', ''),
                    'published': datetime.fromtimestamp(item.get('published', 0)).isoformat() if item.get('published') else '',
                    'url': item.get('link', '')
                })

            return processed
        except Exception as e:
            print(f"   ⚠️  yfinance news error: {e}")
            return []

    def fetch_naver_news(self) -> List[Dict]:
        """
        네이버 뉴스 RSS 수집
        """
        try:
            # 종목명으로 검색
            query = urllib.parse.quote(self.name)
            rss_url = f"https://news.google.com/rss/search?q={query}+stock&hl=ko&gl=KR&ceid=KR:ko"

            # 네이버는 직접 RSS 제공이 제한적이므로 구글 뉴스로 대체
            # 또는 네이버 검색 결과 파싱
            return self._fetch_google_news_rss(query)

        except Exception as e:
            print(f"   ⚠️  Naver news error: {e}")
            return []

    def fetch_google_news(self) -> List[Dict]:
        """
        구글 뉴스 RSS 수집
        """
        try:
            query = urllib.parse.quote(f"{self.name} stock")
            rss_url = f"https://news.google.com/rss/search?q={query}&hl=en-US&gl=US&ceid=US:en"

            return self._fetch_google_news_rss(query)

        except Exception as e:
            print(f"   ⚠️  Google news error: {e}")
            return []

    def _fetch_google_news_rss(self, query: str) -> List[Dict]:
        """구글 뉴스 RSS 파싱"""
        try:
            # 구글 뉴스 RSS URL
            encoded_query = urllib.parse.quote(query)
            rss_url = f"https://news.google.com/rss/search?q={encoded_query}&hl=ko&gl=KR&ceid=KR:ko"

            # RSS 피드 파싱
            feed = feedparser.parse(rss_url)

            processed = []
            for entry in feed.entries[:15]:  # 최근 15개
                processed.append({
                    'source': 'google_news',
                    'title': entry.get('title', ''),
                    'summary': entry.get('summary', ''),
                    'publisher': entry.get('source', {}).get('title', '') if isinstance(entry.get('source'), dict) else '',
                    'published': entry.get('published', ''),
                    'url': entry.get('link', '')
                })

            return processed

        except Exception as e:
            print(f"   ⚠️  RSS parse error: {e}")
            return []

    def fetch_trends24_news(self) -> List[Dict]:
        """
        trends24.in에서 뉴스 수집
        - 웹 페이지에서 주요 뉴스 헤드라인 스크래핑
        """
        try:
            from bs4 import BeautifulSoup
            
            # 종목명으로 검색어 생성 (영어로 변환 또는 인코딩)
            query = urllib.parse.quote(self.name.encode('utf-8'))
            
            # trends24.in URL
            url = f"https://trends24.in/?query={query}"
            
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            }
            
            req = urllib.request.Request(url, headers=headers)
            with urllib.request.urlopen(req, timeout=10) as response:
                html = response.read().decode('utf-8', errors='ignore')
            
            soup = BeautifulSoup(html, 'html.parser')
            
            # 뉴스 항목 파싱
            processed = []
            
            # article 태그나 특정 클래스에서 뉴스 추출
            articles = soup.find_all('article', limit=10)
            
            for article in articles:
                title_elem = article.find('h2') or article.find('h3') or article.find('a')
                if title_elem:
                    title = title_elem.get_text(strip=True)
                    link = title_elem.get('href', '')
                    
                    processed.append({
                        'source': 'trends24',
                        'title': title,
                        'summary': '',
                        'publisher': 'trends24.in',
                        'published': datetime.now().isoformat(),
                        'url': link if link.startswith('http') else f"https://trends24.in{link}"
                    })
            
            return processed
            
        except ImportError:
            print("   ⚠️  BeautifulSoup not available for trends24")
            return []
        except Exception as e:
            print(f"   ⚠️  trends24.in error: {e}")
            return []

    def fetch_naver_stock_news(self) -> List[Dict]:
        """
        네이버 주식 메인 뉴스 수집
        https://m.stock.naver.com/investment/news/mainnews
        """
        try:
            import subprocess
            import sys
            
            # 별도의 Python 스크립트 실행
            script_path = '/home/programs/kstock_analyzer/naver_news_scraper.py'
            result = subprocess.run(
                [sys.executable, script_path],
                capture_output=True, text=True, timeout=60
            )
            
            # 결과 파일 읽기
            import glob
            import os
            
            news_files = glob.glob('/home/programs/kstock_analyzer/data/naver_news_*.json')
            if news_files:
                latest_file = max(news_files, key=os.path.getctime)
                with open(latest_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    main_news = data.get('main_news', {})
                    if main_news.get('status') == 'success':
                        return main_news.get('news', [])
            
            return []
            
        except Exception as e:
            print(f"   ⚠️  Naver stock news error: {e}")
            return []

    def analyze_sentiment(self, text: str) -> Tuple[float, str]:
        """
        텍스트 감성 분석
        """
        text_lower = text.lower()

        pos_count = sum(1 for kw in self.positive_keywords if kw in text_lower)
        neg_count = sum(1 for kw in self.negative_keywords if kw in text_lower)

        total = pos_count + neg_count
        if total == 0:
            return 0.5, 'neutral'

        sentiment_score = pos_count / (pos_count + neg_count * 1.5)

        if sentiment_score >= 0.6:
            return sentiment_score, 'positive'
        elif sentiment_score <= 0.4:
            return sentiment_score, 'negative'
        else:
            return sentiment_score, 'neutral'

    def analyze_news_sentiment(self) -> Tuple[int, List[str], List[str]]:
        """
        통합 뉴스 감성 분석
        """
        score = 0
        signals = []
        risks = []

        # 모든 뉴스 소스 합치기
        all_news = (
            self.news_data['yfinance'] +
            self.news_data['naver'] +
            self.news_data['google'] +
            self.news_data['naver_stock']
        )

        if not all_news:
            return 12, ["뉴스 데이터 없음"], []

        # 감성 분석
        positive_count = 0
        negative_count = 0
        neutral_count = 0

        for news in all_news:
            text = f"{news.get('title', '')} {news.get('summary', '')}"
            sentiment_score, sentiment = self.analyze_sentiment(text)

            if sentiment == 'positive':
                positive_count += 1
            elif sentiment == 'negative':
                negative_count += 1
            else:
                neutral_count += 1

        total = len(all_news)

        # 1. 뉴스 감성 (0-10점)
        if total > 0:
            positive_ratio = positive_count / total
            if positive_ratio >= 0.5:
                score += 10
                signals.append(f"긍정 뉴스 우세 ({positive_ratio*100:.0f}%)")
            elif positive_ratio >= 0.3:
                score += 7
                signals.append(f"긍정 뉴스 다수 ({positive_ratio*100:.0f}%)")
            elif positive_ratio >= 0.2:
                score += 4
                signals.append(f"뉴스 중립-긍정 ({positive_ratio*100:.0f}%)")
            else:
                score += 2
                risks.append(f"부정 뉴스 우세 ({(negative_count/total)*100:.0f}%)")

        # 2. 뉴스 볼륨 (0-8점)
        if len(all_news) >= 15:
            score += 8
            signals.append(f"뉴스 활발 ({len(all_news)}개)")
        elif len(all_news) >= 8:
            score += 6
            signals.append(f"뉴스 적정 ({len(all_news)}개)")
        elif len(all_news) >= 3:
            score += 3
            signals.append(f"뉴스 있음 ({len(all_news)}개)")
        else:
            risks.append(f"뉴스 부족 ({len(all_news)}개)")

        # 3. 소스 다양성 (0-7점)
        sources = set()
        if self.news_data['yfinance']: sources.add('yfinance')
        if self.news_data['naver']: sources.add('naver')
        if self.news_data['google']: sources.add('google')

        score += len(sources) * 2 + 1

        return min(score, 25), signals, risks

    def analyze_social_media(self) -> Tuple[int, List[str], List[str]]:
        """
        소셜 미디어 분석 (거래량 기반 추정)
        """
        score = 0
        signals = []
        risks = []

        if self.price_data is None or len(self.price_data) < 5:
            return 12, ["소셜 데이터 없음"], []

        # 최근 5일 거래량 추이
        recent_volume = self.price_data['Volume'].tail(5).mean()
        avg_volume = self.price_data['Volume'].mean()
        volume_ratio = recent_volume / avg_volume if avg_volume > 0 else 1

        # 거래량 기반 관심도 추정
        if volume_ratio >= 2.0:
            score += 15
            signals.append(f"높은 관심도 (거래량 {volume_ratio:.1f}x)")
        elif volume_ratio >= 1.5:
            score += 12
            signals.append(f"관심 증가 (거래량 {volume_ratio:.1f}x)")
        elif volume_ratio >= 1.0:
            score += 8
            signals.append(f"평균 관심도 (거래량 {volume_ratio:.1f}x)")
        else:
            score += 4
            risks.append(f"관심 감소 (거래량 {volume_ratio:.1f}x)")

        # 변동성 (투자자 심리)
        recent_returns = self.price_data['Close'].pct_change().tail(5)
        volatility = recent_returns.std() * 100

        if volatility >= 5:
            score += 10
            signals.append(f"높은 변동성 ({volatility:.1f}%) - 활발한 논의")
        elif volatility >= 3:
            score += 7
            signals.append(f"증가된 변동성 ({volatility:.1f}%)")
        elif volatility >= 1:
            score += 5
            signals.append(f"정상 변동성 ({volatility:.1f}%)")
        else:
            score += 2
            risks.append(f"낮은 변동성 ({volatility:.1f}%) - 관심 저조")

        return min(score, 25), signals, risks

    def analyze_event_risk(self) -> Tuple[int, List[str], List[str]]:
        """
        이벤트 리스크 분석
        """
        score = 25
        signals = []
        risks = []

        # 뉴스에서 이벤트 키워드 검색
        all_news = (
            self.news_data['yfinance'] +
            self.news_data['naver'] +
            self.news_data['google'] +
            self.news_data['trends24'] +
            self.news_data['naver_stock']
        )

        event_keywords = {
            'earnings': ['실적', 'earnings', 'EPS', 'revenue', '분기', '연간'],
            'dividend': ['배당', 'dividend', '주주환원'],
            'meeting': ['주총', '주주총회', 'shareholder meeting'],
            'offering': ['유상증자', '무상증자', '공모', 'offering'],
            'lawsuit': ['소송', 'lawsuit', 'fine', 'penalty', '제재'],
            'executive': ['CEO', '임원', '퇴임', '취임', 'executive']
        }

        event_counts = {k: 0 for k in event_keywords}

        for news in all_news[:15]:
            title = news.get('title', '').lower()
            for event_type, keywords in event_keywords.items():
                if any(kw in title for kw in keywords):
                    event_counts[event_type] += 1

        # 실적 발표 임박
        if event_counts['earnings'] >= 2:
            score -= 3
            risks.append("실적 발표 임박")
        elif event_counts['earnings'] > 0:
            signals.append("실적 관련 뉴스")

        # 배당/주주총회
        if event_counts['dividend'] > 0:
            signals.append("배당 관련 소식")
        if event_counts['meeting'] > 0:
            signals.append("주주총회 일정")

        # 유상증자 (큰 리스크)
        if event_counts['offering'] >= 2:
            score -= 8
            risks.append("증자 가능성")
        elif event_counts['offering'] > 0:
            score -= 3
            risks.append("증자 관련 소문")

        # 소송/제재
        if event_counts['lawsuit'] >= 2:
            score -= 10
            risks.append("법적 리스크 다수")
        elif event_counts['lawsuit'] > 0:
            score -= 5
            risks.append("법적 리스크")

        # 임원 변경
        if event_counts['executive'] >= 2:
            score -= 4
            risks.append("임원 변동")
        elif event_counts['executive'] > 0:
            signals.append("경영진 소식")

        # 리스크가 없으면 긍정 신호
        if not risks:
            signals.append("특별한 이벤트 리스크 없음")

        return max(score, 0), signals, risks

    def analyze_momentum_signals(self) -> Tuple[int, List[str], List[str]]:
        """
        모멘텀 신호 분석
        """
        score = 0
        signals = []
        risks = []

        if self.price_data is None or len(self.price_data) < 10:
            return 12, ["데이터 부족"], []

        # 1. 가격 모멘텀 (0-10점)
        returns_5d = (self.price_data['Close'].iloc[-1] / self.price_data['Close'].iloc[-5] - 1) * 100
        returns_20d = (self.price_data['Close'].iloc[-1] / self.price_data['Close'].iloc[-20] - 1) * 100

        if returns_5d >= 10:
            score += 10
            signals.append(f"강한 단기 상승 ({returns_5d:+.1f}%)")
        elif returns_5d >= 5:
            score += 8
            signals.append(f"단기 상승 ({returns_5d:+.1f}%)")
        elif returns_5d >= 0:
            score += 5
            signals.append(f"단기 보합~상승 ({returns_5d:+.1f}%)")
        elif returns_5d >= -5:
            score += 2
            risks.append(f"단기 하락 ({returns_5d:+.1f}%)")
        else:
            risks.append(f"강한 단기 하락 ({returns_5d:+.1f}%)")

        # 2. 중기 추세 (0-8점)
        if returns_20d >= 20:
            score += 8
            signals.append(f"강한 중기 상승 ({returns_20d:+.1f}%)")
        elif returns_20d >= 10:
            score += 6
            signals.append(f"중기 상승 ({returns_20d:+.1f}%)")
        elif returns_20d >= 0:
            score += 4
            signals.append(f"중기 보합~상승 ({returns_20d:+.1f}%)")
        elif returns_20d >= -10:
            score += 2
            risks.append(f"중기 하락 ({returns_20d:+.1f}%)")
        else:
            risks.append(f"강한 중기 하락 ({returns_20d:+.1f}%)")

        # 3. 거래량 동반 (0-7점)
        recent_volume = self.price_data['Volume'].tail(5).mean()
        prev_volume = self.price_data['Volume'].iloc[-10:-5].mean()
        volume_change = (recent_volume / prev_volume - 1) * 100 if prev_volume > 0 else 0

        if volume_change >= 50 and returns_5d > 0:
            score += 7
            signals.append(f"거래량 동반 상승 ({volume_change:+.0f}%)")
        elif volume_change >= 20 and returns_5d > 0:
            score += 5
            signals.append(f"거래량 증가 상승 ({volume_change:+.0f}%)")
        elif volume_change >= 0:
            score += 3
        elif returns_5d < 0:
            score += 1
            risks.append(f"거래량 감소 하락 ({volume_change:+.0f}%)")

        return min(score, 25), signals, risks

    def get_sentiment_trend(self) -> str:
        """센티먼트 추세 판단"""
        if self.price_data is None or len(self.price_data) < 10:
            return "Unknown"

        returns_5d = self.price_data['Close'].iloc[-1] / self.price_data['Close'].iloc[-5] - 1
        returns_20d = self.price_data['Close'].iloc[-1] / self.price_data['Close'].iloc[-20] - 1

        if returns_5d > 0.05 and returns_20d > 0:
            return "Improving"
        elif returns_5d < -0.05 and returns_20d < 0:
            return "Declining"
        else:
            return "Stable"

    def analyze(self) -> Dict:
        """전체 뉴스 센티먼트 분석 실행"""
        print(f"\n{'='*60}")
        print(f"📰 Enhanced News Sentiment Agent (NEWS_001)")
        print(f"   Target: {self.name} ({self.symbol})")
        print('='*60)

        # 1. yfinance 뉴스
        print(f"\n   📡 Fetching yfinance news...")
        self.news_data['yfinance'] = self.fetch_yfinance_news()
        print(f"      ✓ {len(self.news_data['yfinance'])} articles")

        # 2. 네이버/구글 뉴스
        print(f"\n   📡 Fetching Google News (RSS)...")
        self.news_data['google'] = self.fetch_google_news()
        print(f"      ✓ {len(self.news_data['google'])} articles")

        # 3. trends24.in 뉴스
        print(f"\n   📡 Fetching trends24.in news...")
        self.news_data['trends24'] = self.fetch_trends24_news()
        print(f"      ✓ {len(self.news_data['trends24'])} articles")

        # 4. 네이버 주식 뉴스
        print(f"\n   📡 Fetching Naver Stock news...")
        self.news_data['naver_stock'] = self.fetch_naver_stock_news()
        print(f"      ✓ {len(self.news_data['naver_stock'])} articles")

        # 총 뉴스 수
        total_news = sum(len(v) for v in self.news_data.values())
        print(f"\n   📊 Total news collected: {total_news}")
        print(f"      - yfinance: {len(self.news_data['yfinance'])}")
        print(f"      - Google News: {len(self.news_data['google'])}")
        print(f"      - trends24.in: {len(self.news_data['trends24'])}")
        print(f"      - Naver Stock: {len(self.news_data['naver_stock'])}")

        # 각 영역 분석
        print(f"\n   Analyzing...")

        news_score, news_signals, news_risks = self.analyze_news_sentiment()
        print(f"   ✅ News Sentiment: {news_score}/25")

        social_score, social_signals, social_risks = self.analyze_social_media()
        print(f"   ✅ Social Media: {social_score}/25")

        event_score, event_signals, event_risks = self.analyze_event_risk()
        print(f"   ✅ Event Risk: {event_score}/25")

        momentum_score, momentum_signals, momentum_risks = self.analyze_momentum_signals()
        print(f"   ✅ Momentum: {momentum_score}/25")

        # 종합 점수
        total_score = news_score + social_score + event_score + momentum_score

        # 모든 신호와 리스크 합치기
        all_signals = news_signals + social_signals + event_signals + momentum_signals
        all_risks = news_risks + social_risks + event_risks + momentum_risks

        # 추천 결정
        if total_score >= 70:
            recommendation = "BUY"
        elif total_score >= 50:
            recommendation = "HOLD"
        else:
            recommendation = "SELL"

        # 센티먼트 추세
        sentiment_trend = self.get_sentiment_trend()

        # 결과 구성
        result = {
            'agent_id': 'NEWS_001',
            'agent_name': 'Enhanced News Sentiment Analyst',
            'symbol': self.symbol,
            'name': self.name,
            'analysis_date': datetime.now().isoformat(),
            'total_score': total_score,
            'breakdown': {
                'news_sentiment': news_score,
                'social_media': social_score,
                'event_risk': event_score,
                'momentum_signals': momentum_score
            },
            'news_sources': {
                'yfinance': len(self.news_data['yfinance']),
                'google_news': len(self.news_data['google']),
                'trends24': len(self.news_data['trends24']),
                'naver_stock': len(self.news_data['naver_stock']),
                'total': total_news
            },
            'sentiment_trend': sentiment_trend,
            'key_signals': all_signals[:5],
            'key_risks': all_risks[:3],
            'recommendation': recommendation
        }

        # 출력
        print(f"\n{'='*60}")
        print(f"📊 ANALYSIS COMPLETE")
        print('='*60)
        print(f"   Total Score: {total_score}/100")
        print(f"   Sentiment Trend: {sentiment_trend}")
        print(f"   News Articles: {total_news}")
        print(f"   Recommendation: {recommendation}")
        print(f"   Key Signals: {', '.join(all_signals[:3])}")
        if all_risks:
            print(f"   ⚠️  Key Risks: {', '.join(all_risks[:2])}")
        print('='*60)

        return result


def main():
    """메인 함수"""
    import argparse

    parser = argparse.ArgumentParser(description='Enhanced News Sentiment Agent')
    parser.add_argument('--symbol', required=True, help='Stock symbol (e.g., 005930.KS)')
    parser.add_argument('--name', help='Stock name')
    parser.add_argument('--output', help='Output JSON file')

    args = parser.parse_args()

    # 분석 실행
    agent = EnhancedNewsAgent(args.symbol, args.name or args.symbol)
    result = agent.analyze()

    # JSON 출력
    if args.output:
        with open(args.output, 'w', encoding='utf-8') as f:
            json.dump(result, f, indent=2, ensure_ascii=False)
        print(f"\n💾 Result saved: {args.output}")
    else:
        print("\n📋 JSON Output:")
        print(json.dumps(result, indent=2, ensure_ascii=False))


if __name__ == '__main__':
    main()
