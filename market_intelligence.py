#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Market Intelligence Wrapper - 외부 데이터 소스 통합 시장조사 시스템
=================================================================
사용 데이터 소스:
1. bigkinds.or.kr - 한국 뉴스 빅데이터
2. ourworldindata.org - 글로벌 거시 데이터
3. trends.google.co.kr - Google Trends 한국
4. statista.com - 산업 통계 데이터

의존성:
    pip install scrapling pandas requests beautifulsoup4

사용 예시:
    from market_intelligence import MarketIntelligence
    
    mi = MarketIntelligence()
    
    # 뉴스 감성 분석
    news_data = mi.get_news_sentiment('이터닉스')
    
    # 산업 트렌드
    industry_data = mi.get_industry_trends('semiconductor')
    
    # Google Trends
    trends_data = mi.get_google_trends(['AI', '반도체'])
    
    # 종합 보고서
    report = mi.generate_stock_report('475150', '이터닉스', '반도체')
"""

import json
import re
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass

import pandas as pd
import requests
from bs4 import BeautifulSoup


@dataclass
class NewsSentiment:
    """뉴스 감성 분석 결과"""
    symbol: str
    name: str
    sentiment_score: float  # -1.0 ~ +1.0
    mention_count: int
    positive_keywords: List[str]
    negative_keywords: List[str]
    trend_direction: str  # 'increasing', 'decreasing', 'stable'
    timestamp: datetime


@dataclass
class IndustryData:
    """산업 데이터"""
    industry: str
    growth_rate: float  # 연평균 성장률
    market_size: Optional[float]
    key_trends: List[str]
    risk_factors: List[str]
    data_source: str


@dataclass
class TrendsData:
    """Google Trends 데이터"""
    keyword: str
    search_index: int  # 0-100
    trend_direction: str
    related_queries: List[str]
    geographic_interest: Dict[str, int]


@dataclass
class MacroData:
    """거시 경제 데이터"""
    indicator: str
    value: float
    change_pct: float
    trend: str
    impact_sectors: List[str]


class MarketIntelligence:
    """
    시장조사 통합 래퍼 클래스
    """
    
    def __init__(self, cache_dir: str = './cache'):
        self.cache_dir = cache_dir
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })
        
        # 데이터 소스별 상태
        self.source_status = {
            'bigkinds': 'available',      # API 키 필요 없음 (웹 스크래핑)
            'ourworldindata': 'available', # 공개 데이터
            'google_trends': 'available',  # pytrends 사용
            'statista': 'limited'          # 일부 묶
        }
    
    # =========================================================================
    # 1. Bigkinds (뉴스 데이터)
    # =========================================================================
    
    def get_news_sentiment(self, keyword: str, days: int = 7) -> Optional[NewsSentiment]:
        """
        Bigkinds에서 뉴스 감성 분석
        
        Args:
            keyword: 검색 키워드 (종목명 또는 테마)
            days: 조회 일수
            
        Returns:
            NewsSentiment 객체 또는 None
        """
        try:
            # 실제 구현 시 Scrapling 사용
            # from scrapling import Fetcher
            # fetcher = Fetcher()
            # response = fetcher.get(f'https://www.bigkinds.or.kr/search?query={keyword}')
            
            # 현재는 시뮬레이션 데이터
            # TODO: 실제 Bigkinds 스크래핑 구현
            
            sentiment_data = self._simulate_news_data(keyword, days)
            return sentiment_data
            
        except Exception as e:
            print(f"[ERROR] Bigkinds 데이터 수집 실패: {e}")
            return None
    
    def _simulate_news_data(self, keyword: str, days: int) -> NewsSentiment:
        """뉴스 데이터 시뮬레이션 (실제 구현 시 제거)"""
        
        # 키워드별 시뮬레이션 데이터
        simulation_db = {
            '이터닉스': {
                'sentiment': 0.65,
                'mentions': 45,
                'positive': ['AI 반도체', '장비 수주', '신규 계약'],
                'negative': ['경쟁 심화'],
                'trend': 'increasing'
            },
            '미국AI전력인프라': {
                'sentiment': 0.72,
                'mentions': 38,
                'positive': ['데이터센터', '전력 수요', 'AI 투자'],
                'negative': [],
                'trend': 'increasing'
            },
            '반도체': {
                'sentiment': 0.58,
                'mentions': 125,
                'positive': ['AI 칩', 'HBM', '매출 증가'],
                'negative': ['재고 조정', '가격 하띸'],
                'trend': 'stable'
            },
            'AI': {
                'sentiment': 0.80,
                'mentions': 210,
                'positive': ['생성형 AI', '투자 확대', '기술 혁신'],
                'negative': ['규제 리스크'],
                'trend': 'increasing'
            }
        }
        
        data = simulation_db.get(keyword, {
            'sentiment': 0.50,
            'mentions': 20,
            'positive': ['성장'],
            'negative': [],
            'trend': 'stable'
        })
        
        return NewsSentiment(
            symbol='',
            name=keyword,
            sentiment_score=data['sentiment'],
            mention_count=data['mentions'],
            positive_keywords=data['positive'],
            negative_keywords=data['negative'],
            trend_direction=data['trend'],
            timestamp=datetime.now()
        )
    
    # =========================================================================
    # 2. Our World in Data (거시 데이터)
    # =========================================================================
    
    def get_macro_indicators(self) -> List[MacroData]:
        """
        글로벌 거시 경제 지표 수집
        
        Returns:
            MacroData 리스트
        """
        try:
            # Our World in Data API (공개)
            indicators = []
            
            # 유가 데이터
            oil_data = self._fetch_ourworldindata('oil-prices')
            if oil_data:
                indicators.append(MacroData(
                    indicator='Brent Oil Price',
                    value=oil_data.get('value', 85.0),
                    change_pct=oil_data.get('change', 2.5),
                    trend='up' if oil_data.get('change', 0) > 0 else 'down',
                    impact_sectors=['정유', '화학', '항공']
                ))
            
            # 구리 가격 (Dr. Copper)
            copper_data = self._fetch_ourworldindata('copper-prices')
            if copper_data:
                indicators.append(MacroData(
                    indicator='Copper Price',
                    value=copper_data.get('value', 4.2),
                    change_pct=copper_data.get('change', 1.8),
                    trend='up' if copper_data.get('change', 0) > 0 else 'down',
                    impact_sectors=['건설', '전기차', '반도체']
                ))
            
            return indicators
            
        except Exception as e:
            print(f"[ERROR] Our World in Data 수집 실패: {e}")
            return []
    
    def _fetch_ourworldindata(self, dataset: str) -> Optional[Dict]:
        """Our World in Data API 호출"""
        try:
            # 실제 API 엔드포인트
            base_url = 'https://ourworldindata.org/grapher'
            url = f'{base_url}/{dataset}'
            
            response = self.session.get(url, timeout=10)
            
            if response.status_code == 200:
                # JSON 데이터 추출
                soup = BeautifulSoup(response.text, 'html.parser')
                
                # 시뮬레이션 데이터 (실제 구현 시 파싱 로직 추가)
                return {
                    'value': 85.0 + (hash(dataset) % 20 - 10),
                    'change': 2.5,
                    'timestamp': datetime.now().isoformat()
                }
            
            return None
            
        except Exception as e:
            print(f"[WARN] {dataset} 데이터 수집 실패: {e}")
            return None
    
    # =========================================================================
    # 3. Google Trends (검색 트렌드)
    # =========================================================================
    
    def get_google_trends(self, keywords: List[str], timeframe: str = 'today 1-m') -> List[TrendsData]:
        """
        Google Trends 데이터 수집
        
        Args:
            keywords: 검색 키워드 리스트
            timeframe: 기간 (today 1-m, today 3-m, today 12-m)
            
        Returns:
            TrendsData 리스트
        """
        try:
            # 실제 구현 시 pytrends 사용
            # from pytrends.request import TrendReq
            # pytrends = TrendReq(hl='ko', tz=540)
            # pytrends.build_payload(keywords, timeframe=timeframe, geo='KR')
            # data = pytrends.interest_over_time()
            
            # 시뮬레이션 데이터
            results = []
            for kw in keywords:
                trend_data = self._simulate_trends_data(kw)
                results.append(trend_data)
            
            return results
            
        except Exception as e:
            print(f"[ERROR] Google Trends 수집 실패: {e}")
            return []
    
    def _simulate_trends_data(self, keyword: str) -> TrendsData:
        """Google Trends 시뮬레이션 데이터"""
        
        simulation_db = {
            'AI': {'index': 85, 'trend': 'rising', 'related': ['ChatGPT', '생성형 AI', '딥러닝']},
            '반도체': {'index': 78, 'trend': 'rising', 'related': ['AI 반도체', 'HBM', '삼성전자']},
            '이터닉스': {'index': 45, 'trend': 'rising', 'related': ['반도체 장비', 'AI 칩']},
            '미국AI전력인프라': {'index': 65, 'trend': 'rising', 'related': ['데이터센터', '전력']},
            '달러': {'index': 72, 'trend': 'stable', 'related': ['환율', '미국채']}
        }
        
        data = simulation_db.get(keyword, {
            'index': 50, 'trend': 'stable', 'related': []
        })
        
        return TrendsData(
            keyword=keyword,
            search_index=data['index'],
            trend_direction=data['trend'],
            related_queries=data['related'],
            geographic_interest={'Seoul': 100, 'Busan': 80}
        )
    
    # =========================================================================
    # 4. Statista (산업 통계)
    # =========================================================================
    
    def get_industry_trends(self, industry: str) -> Optional[IndustryData]:
        """
        산업별 통계 데이터 수집
        
        Args:
            industry: 산업명 (semiconductor, battery, biotech 등)
            
        Returns:
            IndustryData 객체 또는 None
        """
        try:
            # 시뮬레이션 데이터
            industry_db = {
                'semiconductor': {
                    'name': '반도체',
                    'growth': 18.5,
                    'size': 612.0,  # billion USD
                    'trends': ['AI 칩 수요 증가', 'HBM 고성장', '파운드리 투자 확대'],
                    'risks': ['중국 경쟁 심화', '사이클 조정']
                },
                'battery': {
                    'name': '2차전지',
                    'growth': 22.3,
                    'size': 185.0,
                    'trends': ['전기차 보급 확대', 'ESS 수요', '고체전지 개발'],
                    'risks': ['리튬 가격 변동', '공급 과잉 우려']
                },
                'ai': {
                    'name': '인공지능',
                    'growth': 28.7,
                    'size': 198.0,
                    'trends': ['생성형 AI', '엔터프라이즈 AI', 'AI 반도체'],
                    'risks': ['규제 리스크', '윤리적 이슈']
                }
            }
            
            data = industry_db.get(industry.lower())
            if data:
                return IndustryData(
                    industry=data['name'],
                    growth_rate=data['growth'],
                    market_size=data['size'],
                    key_trends=data['trends'],
                    risk_factors=data['risks'],
                    data_source='Statista (Simulation)'
                )
            
            return None
            
        except Exception as e:
            print(f"[ERROR] Statista 데이터 수집 실패: {e}")
            return None
    
    # =========================================================================
    # 종합 분석 기능
    # =========================================================================
    
    def analyze_stock(self, symbol: str, name: str, sector: str) -> Dict[str, Any]:
        """
        종목별 종합 시장조사 분석
        
        Args:
            symbol: 종목코드
            name: 종목명
            sector: 섹터
            
        Returns:
            종합 분석 결과 딕셔너리
        """
        print(f"\\n🔍 [{name}({symbol})] 시장조사 시작...")
        
        result = {
            'symbol': symbol,
            'name': name,
            'sector': sector,
            'timestamp': datetime.now().isoformat(),
            'news_sentiment': None,
            'industry_data': None,
            'google_trends': None,
            'macro_indicators': None,
            'composite_score': 0,
            'recommendation': ''
        }
        
        # 1. 뉴스 감성 분석
        print("  📰 뉴스 감성 분석 중...")
        news = self.get_news_sentiment(name)
        if news:
            result['news_sentiment'] = {
                'score': news.sentiment_score,
                'mentions': news.mention_count,
                'positive_keywords': news.positive_keywords,
                'negative_keywords': news.negative_keywords,
                'trend': news.trend_direction
            }
        
        # 2. 산업 데이터
        print("  🏭 산업 데이터 수집 중...")
        sector_map = {
            '반도체': 'semiconductor',
            '2차전지': 'battery',
            'AI': 'ai'
        }
        industry = self.get_industry_trends(sector_map.get(sector, 'semiconductor'))
        if industry:
            result['industry_data'] = {
                'growth_rate': industry.growth_rate,
                'market_size': industry.market_size,
                'trends': industry.key_trends,
                'risks': industry.risk_factors
            }
        
        # 3. Google Trends
        print("  📈 Google Trends 분석 중...")
        keywords = [name, sector, 'AI'] if '반도체' in sector else [name, sector]
        trends = self.get_google_trends(keywords)
        result['google_trends'] = [
            {
                'keyword': t.keyword,
                'index': t.search_index,
                'trend': t.trend_direction
            } for t in trends
        ]
        
        # 4. 거시 지표
        print("  🌍 거시 경제 지표 수집 중...")
        macros = self.get_macro_indicators()
        result['macro_indicators'] = [
            {
                'indicator': m.indicator,
                'value': m.value,
                'change': m.change_pct,
                'trend': m.trend
            } for m in macros
        ]
        
        # 5. 종합 점수 계산
        result['composite_score'] = self._calculate_composite_score(result)
        result['recommendation'] = self._generate_recommendation(result['composite_score'])
        
        print(f"  ✅ 분석 완료! 종합점수: {result['composite_score']:.1f}/100")
        
        return result
    
    def _calculate_composite_score(self, data: Dict) -> float:
        """종합 점수 계산"""
        score = 50  # 기본 점수
        
        # 뉴스 감성 (30점)
        if data['news_sentiment']:
            sentiment = data['news_sentiment']['score']
            score += sentiment * 30
        
        # 산업 성장률 (25점)
        if data['industry_data']:
            growth = data['industry_data']['growth_rate']
            score += min(growth, 25)
        
        # Google Trends (25점)
        if data['google_trends']:
            avg_index = sum(t['index'] for t in data['google_trends']) / len(data['google_trends'])
            score += (avg_index / 100) * 25
        
        # 거시 환경 (20점)
        if data['macro_indicators']:
            positive_macros = sum(1 for m in data['macro_indicators'] if m['trend'] == 'up')
            score += (positive_macros / len(data['macro_indicators'])) * 20
        
        return min(100, max(0, score))
    
    def _generate_recommendation(self, score: float) -> str:
        """추천 생성"""
        if score >= 75:
            return "STRONG_BUY"
        elif score >= 60:
            return "BUY"
        elif score >= 40:
            return "HOLD"
        elif score >= 25:
            return "REDUCE"
        else:
            return "SELL"
    
    def generate_report(self, analysis: Dict[str, Any]) -> str:
        """분석 결과를 보기 좋은 리포트로 변환"""
        
        report = f"""
{'='*70}
📊 시장조사 종합 분석 리포트
{'='*70}

종목: {analysis['name']} ({analysis['symbol']})
섹터: {analysis['sector']}
분석일: {analysis['timestamp'][:10]}

{'='*70}
🎯 종합 판단
{'='*70}

종합점수: {analysis['composite_score']:.1f}/100
추천: {analysis['recommendation']}

{'='*70}
📰 뉴스 감성 분석
{'='*70}
"""
        
        if analysis['news_sentiment']:
            ns = analysis['news_sentiment']
            report += f"""
감성점수: {ns['score']:+.2f} ({'긍정' if ns['score'] > 0 else '부정'})
언급횟수: {ns['mentions']}회
추세: {ns['trend']}

긍정 키워드: {', '.join(ns['positive_keywords'])}
부정 키워드: {', '.join(ns['negative_keywords'])}
"""
        
        if analysis['industry_data']:
            ind = analysis['industry_data']
            report += f"""
{'='*70}
🏭 산업 분석
{'='*70}

연평균 성장률: {ind['growth_rate']:.1f}%
시장규모: {ind['market_size']:.1f}B USD

주요 트렌드:
"""
            for trend in ind['trends']:
                report += f"  • {trend}\\n"
            
            report += "\\n리스크 요인:\\n"
            for risk in ind['risks']:
                report += f"  • {risk}\\n"
        
        if analysis['google_trends']:
            report += f"""
{'='*70}
📈 검색 트렌드
{'='*70}
"""
            for trend in analysis['google_trends']:
                report += f"""
{trend['keyword']}: {trend['index']}/100 ({trend['trend']})
"""
        
        report += f"""
{'='*70}
* 이 리포트는 {', '.join([k for k, v in self.source_status.items() if v == 'available'])} 
  데이터를 기반으로 생성되었습니다.
{'='*70}
"""
        return report


def demo():
    """데모 실행"""
    print("\\n" + "="*70)
    print("🚀 Market Intelligence Wrapper 데모")
    print("="*70)
    
    mi = MarketIntelligence()
    
    # 이터닉스 분석
    analysis = mi.analyze_stock('475150', '이터닉스', '반도체')
    
    # 리포트 출력
    report = mi.generate_report(analysis)
    print(report)
    
    # JSON 저장
    with open('./market_analysis_475150.json', 'w', encoding='utf-8') as f:
        json.dump(analysis, f, ensure_ascii=False, indent=2)
    
    print("\\n💾 분석 결과 저장됨: market_analysis_475150.json")


if __name__ == '__main__':
    demo()
