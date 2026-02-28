#!/usr/bin/env python3
"""
News Sentiment Analysis Agent (NEWS_001)
뉴스 센티먼트 분석 에이전트 - 호재/악재 뉴스 및 감성 분석
"""

import yfinance as yf
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Optional
import json
import sys
import re


class NewsSentimentAgent:
    """뉴스 센티먼트 분석 에이전트"""
    
    def __init__(self, symbol: str, name: str = ""):
        self.symbol = symbol
        self.name = name or symbol
        self.ticker = None
        self.news = []
        self.info = {}
        self.scores = {}
        self.price_data = None
    
    def fetch_data(self) -> bool:
        """뉴스 및 주가 데이터 수집"""
        try:
            self.ticker = yf.Ticker(self.symbol)
            self.info = self.ticker.info or {}
            
            # 뉴스 수집
            self.news = self.ticker.news or []
            
            # 주가 데이터 (거래량 분석용)
            self.price_data = self.ticker.history(period='30d')
            
            return True
        except Exception as e:
            print(f"Error fetching data: {e}")
            return False
    
    def analyze_news_sentiment(self) -> Tuple[int, List[str], List[str]]:
        """
        뉴스 감성 분석 (0-25점)
        - 최근 30일 뉴스 긍정/부정 비율
        """
        score = 0
        signals = []
        risks = []
        
        if not self.news:
            return 12, ["뉴스 데이터 없음"], []
        
        # 뉴스 분석
        positive_keywords = ['상승', '호재', '성장', '돌파', '강세', '매수', 'upgrade', 'beat', 'growth', 'surge', 'rally', 'strong']
        negative_keywords = ['하락', '악재', '감소', '하락세', '매도', 'downgrade', 'miss', 'decline', 'drop', 'weak', 'concern']
        
        positive_count = 0
        negative_count = 0
        neutral_count = 0
        
        recent_news = self.news[:20]  # 최근 20개
        
        for item in recent_news:
            title = item.get('title', '').lower()
            content = item.get('summary', '').lower()
            text = title + ' ' + content
            
            pos_score = sum(1 for kw in positive_keywords if kw in text)
            neg_score = sum(1 for kw in negative_keywords if kw in text)
            
            if pos_score > neg_score:
                positive_count += 1
            elif neg_score > pos_score:
                negative_count += 1
            else:
                neutral_count += 1
        
        total = positive_count + negative_count + neutral_count
        if total > 0:
            positive_ratio = positive_count / total
            negative_ratio = negative_count / total
            
            # 점수 계산
            if positive_ratio >= 0.5:
                score += 25
                signals.append(f"긍정 뉴스 우세 ({positive_ratio*100:.0f}%)")
            elif positive_ratio >= 0.4:
                score += 20
                signals.append(f"긍정 뉴스 많음 ({positive_ratio*100:.0f}%)")
            elif positive_ratio >= 0.3:
                score += 15
                signals.append(f"뉴스 중립-긍정 ({positive_ratio*100:.0f}%)")
            elif positive_ratio >= 0.2:
                score += 8
                signals.append(f"부정 뉴스 우세 ({negative_ratio*100:.0f}%)")
            else:
                score += 3
                risks.append(f"부정 뉴스 다수 ({negative_ratio*100:.0f}%)")
        
        # 뉴스 볼륨
        if len(self.news) >= 10:
            signals.append(f"뉴스 활발 ({len(self.news)}개)")
        elif len(self.news) >= 5:
            signals.append(f"뉴스 적정 ({len(self.news)}개)")
        else:
            risks.append(f"뉴스 부족 ({len(self.news)}개)")
        
        return min(score, 25), signals, risks
    
    def analyze_social_media(self) -> Tuple[int, List[str], List[str]]:
        """
        소셜 미디어 분석 (0-25점)
        - 커뮤니티 센티먼트 (시뮬레이션)
        """
        score = 0
        signals = []
        risks = []
        
        # yfinance에서 직수 소셜 미디어 데이터는 제한적
        # 대신 거래량과 변동성으로 추정
        
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
        이벤트 리스크 분석 (0-25점)
        - 실적 발표, 주주총회, 공시 리스크
        """
        score = 25  # 만점에서 감점
        signals = []
        risks = []
        
        # 뉴스에서 이벤트 키워드 검색
        event_keywords = {
            'earnings': ['실적', 'earnings', 'EPS', 'revenue', '분기', '연간'],
            'dividend': ['배당', 'dividend', '주주환원'],
            'meeting': ['주총', '주주총회', 'shareholder meeting'],
            'offering': ['유상증자', '무상증자', '공모', 'offering'],
            'lawsuit': ['소송', 'lawsuit', 'fine', 'penalty', '제재'],
            'executive': ['CEO', '임원', '퇴임', '취임', 'executive']
        }
        
        event_counts = {k: 0 for k in event_keywords}
        
        for item in self.news[:15]:
            title = item.get('title', '').lower()
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
        모멘텀 신호 분석 (0-25점)
        - 뉴스 볼륨 추세, 센티먼트 변화, 거래량 동반
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
        print(f"📰 News Sentiment Agent (NEWS_001)")
        print(f"   Target: {self.name} ({self.symbol})")
        print('='*60)
        
        # 데이터 수집
        if not self.fetch_data():
            return {
                'error': 'Failed to fetch data',
                'symbol': self.symbol,
                'name': self.name
            }
        
        print(f"   📰 News fetched: {len(self.news)} articles")
        print(f"   📊 Price data: {len(self.price_data)} days")
        
        # 각 영역 분석
        print(f"\n   Analyzing...")
        
        news_score, news_signals, news_risks = self.analyze_news_sentiment()
        self.scores['news_sentiment'] = news_score
        print(f"   ✅ News Sentiment: {news_score}/25")
        
        social_score, social_signals, social_risks = self.analyze_social_media()
        self.scores['social_media'] = social_score
        print(f"   ✅ Social Media: {social_score}/25")
        
        event_score, event_signals, event_risks = self.analyze_event_risk()
        self.scores['event_risk'] = event_score
        print(f"   ✅ Event Risk: {event_score}/25")
        
        momentum_score, momentum_signals, momentum_risks = self.analyze_momentum_signals()
        self.scores['momentum_signals'] = momentum_score
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
            'agent_name': 'News Sentiment Analyst',
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
            'sentiment_trend': sentiment_trend,
            'news_count': len(self.news),
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
        print(f"   News Articles: {len(self.news)}")
        print(f"   Recommendation: {recommendation}")
        print(f"   Key Signals: {', '.join(all_signals[:3])}")
        if all_risks:
            print(f"   ⚠️  Key Risks: {', '.join(all_risks[:2])}")
        print('='*60)
        
        return result


def main():
    """메인 함수"""
    import argparse
    
    parser = argparse.ArgumentParser(description='News Sentiment Analysis Agent')
    parser.add_argument('--symbol', required=True, help='Stock symbol (e.g., 005930.KS)')
    parser.add_argument('--name', help='Stock name')
    parser.add_argument('--output', help='Output JSON file')
    
    args = parser.parse_args()
    
    # 분석 실행
    agent = NewsSentimentAgent(args.symbol, args.name or args.symbol)
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
