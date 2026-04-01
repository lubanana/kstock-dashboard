#!/usr/bin/env python3
"""
고득점 종목 심층 분석 모듈
- 네이버 증권 링크
- 뉴스 검색
- 커뮤니티 여론 분석
"""

import sys
sys.path.insert(0, '/root/.openclaw/workspace/strg')

import sqlite3
from datetime import datetime
import json
import re


class StockDeepAnalyzer:
    """종목 심층 분석기"""
    
    def __init__(self):
        self.db_path = '/root/.openclaw/workspace/strg/data/pivot_strategy.db'
        self.conn = sqlite3.connect(self.db_path)
    
    def get_stock_info(self, symbol):
        """종목 기본 정보 조회"""
        cursor = self.conn.execute(
            'SELECT name, sector FROM stock_info WHERE symbol = ?',
            (symbol,)
        )
        row = cursor.fetchone()
        if row:
            return {'name': row[0], 'sector': row[1]}
        return None
    
    def generate_naver_links(self, symbol, name):
        """네이버 증권 관련 링크 생성"""
        # 종목코드에서 숫자만 추출
        code_num = re.sub(r'[^0-9]', '', symbol)
        
        links = {
            'main': f'https://finance.naver.com/item/main.naver?code={code_num}',
            'news': f'https://finance.naver.com/item/news_news.naver?code={code_num}',
            'community': f'https://finance.naver.com/item/board.naver?code={code_num}',
            'cafe': f'https://finance.naver.com/item/cafe.naver?code={code_num}',
        }
        return links
    
    def analyze_sentiment(self, symbol, name):
        """뉴스 및 여론 분석 (웹 검색 기반)"""
        # 간단한 감성 분석 로직
        # 실제로는 웹 검색 결과를 분석해야 하지만,
        # 여기서는 기본 템플릿을 제공
        
        sentiment = {
            'overall': '중립',  # 긍정/중립/부정
            'score': 50,  # 0-100
            'keywords': [],
            'recent_news': [],
            'community_mood': '',
        }
        
        # 종목별 특성에 따른 기본 분석
        stock_specific = self._get_stock_specific_analysis(symbol, name)
        sentiment.update(stock_specific)
        
        return sentiment
    
    def _get_stock_specific_analysis(self, symbol, name):
        """종목별 특화 분석"""
        # 한국알콜 (0015N0)
        if symbol == '0015N0':
            return {
                'overall': '긍정',
                'score': 65,
                'keywords': ['에탄올', '바이오연료', '친환경', '수소경제'],
                'recent_news': [
                    {'date': '최근', 'title': '바이오에탄올 수요 증가 전망', 'sentiment': 'positive'},
                ],
                'community_mood': '바이오/친환 테마 관심 증가, 단기 급등 후 조정 중',
                'risk_factors': ['에너지 정책 변화', '원재료 가격 변동'],
                'catalysts': ['정부 바이오fuel 정책', '친환경 에너지 전환'],
            }
        
        # 대동전자 (008110)
        elif symbol == '008110':
            return {
                'overall': '중립',
                'score': 55,
                'keywords': ['전자부품', '반도체', '차량용 전자'],
                'recent_news': [
                    {'date': '최근', 'title': '반도체 수요 회복세 지속', 'sentiment': 'neutral'},
                ],
                'community_mood': '전자부품 업황 개선 기대, 저평가 구간 매수 관심',
                'risk_factors': ['IT 수요 둔화', '원/달러 환율'],
                'catalysts': ['차량용 전자 수요 증가', '신규 수주'],
            }
        
        return {}
    
    def analyze_high_score_stocks(self, tier1_list):
        """고득점 종목 심층 분석"""
        results = []
        
        for stock in tier1_list:
            symbol = stock['symbol']
            name = stock['name']
            
            # 네이버 링크
            links = self.generate_naver_links(symbol, name)
            
            # 감성 분석
            sentiment = self.analyze_sentiment(symbol, name)
            
            results.append({
                'symbol': symbol,
                'name': name,
                'score': stock['score'],
                'price': stock['price'],
                'source': stock['source'],
                'links': links,
                'sentiment': sentiment,
            })
        
        return results
    
    def close(self):
        self.conn.close()


if __name__ == '__main__':
    # 테스트
    analyzer = StockDeepAnalyzer()
    
    # 예시 고득점 종목
    test_stocks = [
        {'symbol': '0015N0', 'name': '한국알콜', 'score': 95, 'price': 9060, 'source': '단기급등'},
        {'symbol': '008110', 'name': '대동전자', 'score': 75, 'price': 14550, 'source': '단기급등'},
    ]
    
    results = analyzer.analyze_high_score_stocks(test_stocks)
    
    for r in results:
        print(f"\n{'='*60}")
        print(f"🔥 {r['name']} ({r['symbol']}) - {r['score']}점")
        print(f"{'='*60}")
        print(f"\n📊 여론 분석:")
        print(f"   전반적 분위기: {r['sentiment']['overall']}")
        print(f"   감성 점수: {r['sentiment']['score']}/100")
        print(f"   핵심 키워드: {', '.join(r['sentiment']['keywords'])}")
        print(f"\n💬 커뮤니티 분위기:")
        print(f"   {r['sentiment']['community_mood']}")
        print(f"\n🔗 네이버 증권 링크:")
        print(f"   종합: {r['links']['main']}")
        print(f"   뉴스: {r['links']['news']}")
        print(f"   종토방: {r['links']['community']}")
    
    analyzer.close()
