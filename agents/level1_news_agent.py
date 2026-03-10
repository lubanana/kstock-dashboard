#!/usr/bin/env python3
"""
Level 1 News Analysis Agent
뉴스 분석 에이전트 (조걸 실행)

Features:
- 70점 이상 종목만 분석
- 네이버 뉴스 크롤링
- 감성 분석 (긍정/부정)
- 뉴스 점수 반영
"""

import os
import json
import sqlite3
import requests
from datetime import datetime, timedelta
from bs4 import BeautifulSoup
from typing import List, Dict, Optional
import time


class NewsAnalysisAgent:
    """뉴스 분석 에이전트"""
    
    def __init__(self, db_path: str = 'data/level1_news.db'):
        self.db_path = db_path
        self.init_db()
        
    def init_db(self):
        """DB 초기화"""
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS news_analysis (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                code TEXT,
                name TEXT,
                date TEXT,
                news_count INTEGER,
                positive_count INTEGER,
                negative_count INTEGER,
                neutral_count INTEGER,
                sentiment_score REAL,
                news_score REAL,
                top_keywords TEXT,
                status TEXT,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(code, date)
            )
        ''')
        conn.commit()
        conn.close()
    
    def fetch_naver_news(self, keyword: str, max_count: int = 10) -> List[Dict]:
        """네이버 뉴스 검색"""
        try:
            url = f"https://search.naver.com/search.naver?where=news&query={keyword}"
            headers = {'User-Agent': 'Mozilla/5.0'}
            response = requests.get(url, headers=headers, timeout=10)
            soup = BeautifulSoup(response.text, 'html.parser')
            
            articles = []
            items = soup.select('.news_area')[:max_count]
            
            for item in items:
                title = item.select_one('.news_tit')
                if title:
                    articles.append({
                        'title': title.get_text(),
                        'link': title.get('href', '')
                    })
            
            return articles
        except Exception as e:
            print(f"   ⚠️  뉴스 수집 오류: {e}")
            return []
    
    def analyze_sentiment(self, text: str) -> str:
        """간단한 감성 분석"""
        positive_words = ['상승', '호재', '급등', '강세', '돌파', '↑', '플러스', '성장', '호실적', '매수']
        negative_words = ['하락', '악재', '급락', '약세', '↓', '마이너스', '감소', '부진', '악실적', '매도']
        
        text = text.lower()
        pos_count = sum(1 for word in positive_words if word in text)
        neg_count = sum(1 for word in negative_words if word in text)
        
        if pos_count > neg_count:
            return 'positive'
        elif neg_count > pos_count:
            return 'negative'
        else:
            return 'neutral'
    
    def analyze_stock(self, code: str, name: str) -> Optional[Dict]:
        """단일 종목 뉴스 분석"""
        try:
            # 뉴스 수집
            news_list = self.fetch_naver_news(name, max_count=10)
            
            if not news_list:
                return {
                    'code': code,
                    'name': name,
                    'date': datetime.now().strftime('%Y-%m-%d'),
                    'news_count': 0,
                    'sentiment_score': 0,
                    'news_score': 50,
                    'status': 'no_news'
                }
            
            # 감성 분석
            sentiments = {'positive': 0, 'negative': 0, 'neutral': 0}
            for news in news_list:
                sentiment = self.analyze_sentiment(news['title'])
                sentiments[sentiment] += 1
            
            total = len(news_list)
            sentiment_score = (sentiments['positive'] - sentiments['negative']) / total * 100
            
            # 뉴스 점수 계산 (50점 기준)
            news_score = 50 + sentiment_score
            
            return {
                'code': code,
                'name': name,
                'date': datetime.now().strftime('%Y-%m-%d'),
                'news_count': total,
                'positive_count': sentiments['positive'],
                'negative_count': sentiments['negative'],
                'neutral_count': sentiments['neutral'],
                'sentiment_score': sentiment_score,
                'news_score': news_score,
                'top_keywords': '',
                'status': 'success'
            }
            
        except Exception as e:
            return {
                'code': code,
                'name': name,
                'date': datetime.now().strftime('%Y-%m-%d'),
                'status': 'error',
                'error_msg': str(e)
            }
    
    def analyze_high_score_stocks(self, min_score: float = 70.0):
        """고점수 종목만 뉴스 분석"""
        # 가격 데이터에서 고점수 종목 로드
        price_db = 'data/level1_daily.db'
        if not os.path.exists(price_db):
            print("❌ 가격 데이터 DB 없음")
            return []
        
        conn = sqlite3.connect(price_db)
        cursor = conn.cursor()
        cursor.execute('''
            SELECT code, name, score FROM price_analysis 
            WHERE date = (SELECT MAX(date) FROM price_analysis)
            AND score >= ?
            ORDER BY score DESC
        ''', (min_score,))
        
        stocks = cursor.fetchall()
        conn.close()
        
        print(f"\n🚀 News Analysis Agent")
        print(f"   Target: {len(stocks)} stocks (score ≥ {min_score})")
        print("=" * 60)
        
        results = []
        for i, (code, name, score) in enumerate(stocks, 1):
            result = self.analyze_stock(code, name)
            if result:
                results.append(result)
                
                # DB 저장
                conn = sqlite3.connect(self.db_path)
                cursor = conn.cursor()
                cursor.execute('''
                    INSERT OR REPLACE INTO news_analysis
                    (code, name, date, news_count, positive_count, negative_count, 
                     neutral_count, sentiment_score, news_score, top_keywords, status)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', tuple(result.get(k) for k in ['code', 'name', 'date', 'news_count',
                    'positive_count', 'negative_count', 'neutral_count', 'sentiment_score',
                    'news_score', 'top_keywords', 'status']))
                conn.commit()
                conn.close()
                
                status_emoji = "✅" if result['status'] == 'success' else "⚠️"
                print(f"   [{i}/{len(stocks)}] {status_emoji} {name}: 뉴스점수 {result.get('news_score', 0):.1f}")
                
            time.sleep(0.5)  # Rate limiting
        
        print(f"\n✅ News Analysis Complete! ({len(results)} stocks)")
        return results


if __name__ == '__main__':
    agent = NewsAnalysisAgent()
    agent.analyze_high_score_stocks(min_score=70.0)
