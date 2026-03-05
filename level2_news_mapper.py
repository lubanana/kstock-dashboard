#!/usr/bin/env python3
"""
Level 2 News Mapper for Level 1 Stocks
Level 1 종목별 뉴스 매핑 및 정리 모듈

기존에 수집된 네이버 뉴스 데이터를 Level 1 종목과 매핑
"""

import json
import glob
import os
from datetime import datetime
from typing import Dict, List


class Level2NewsMapper:
    """Level 2 뉴스 매퍼 - Level 1 종목별 뉴스 정리"""
    
    def __init__(self):
        self.base_path = '/home/programs/kstock_analyzer'
    
    def load_level1_stocks(self) -> List[Dict]:
        """Level 1 분석 결과에서 종목 리스트 로드"""
        l1_files = glob.glob(f'{self.base_path}/data/level1_daily/level1_fullmarket_*.json')
        if not l1_files:
            return []
        
        latest_file = max(l1_files, key=os.path.getctime)
        
        with open(latest_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        # 성공적으로 분석된 종목만 추출
        stocks = []
        for result in data.get('results', []):
            if result.get('status') == 'success':
                stocks.append({
                    'symbol': result.get('symbol', ''),
                    'name': result.get('name', ''),
                    'market': result.get('market', ''),
                    'avg_score': result.get('avg_score', 0),
                    'recommendation': result.get('recommendation', 'HOLD'),
                    'breakdown': result.get('breakdown', {})
                })
        
        # 점수 순으로 정렬
        stocks.sort(key=lambda x: x['avg_score'], reverse=True)
        return stocks
    
    def load_latest_naver_news(self) -> Dict:
        """최신 네이버 뉴스 데이터 로드"""
        news_files = glob.glob(f'{self.base_path}/data/naver_news_*.json')
        if not news_files:
            return {}
        
        latest_file = max(news_files, key=os.path.getctime)
        
        with open(latest_file, 'r', encoding='utf-8') as f:
            return json.load(f)
    
    def analyze_sentiment(self, title: str) -> tuple:
        """뉴스 제목 감성 분석"""
        positive_keywords = [
            '상승', '호재', '성장', '돌파', '강세', '매수', 'upgrade', 'beat',
            'growth', 'surge', 'rally', 'strong', 'bullish', 'outperform',
            '급등', '신고가', '기대감', '호실적', '증가', '확대', '수주',
            'rise', 'gain', 'jump', 'soar', 'boost', 'positive', 'profit',
            '장난매수', '급등', '회복', '반등'
        ]
        
        negative_keywords = [
            '하락', '악재', '감소', '하락세', '매도', 'downgrade', 'miss',
            'decline', 'drop', 'weak', 'bearish', 'underperform',
            '급락', '신저가', '우려', '적자', '감소', '축소', '해지',
            'fall', 'loss', 'crash', 'plunge', 'tumble', 'negative', 'deficit',
            '손절', '폭락', '위헌', '논란'
        ]
        
        title_lower = title.lower()
        
        pos_score = sum(1 for kw in positive_keywords if kw in title_lower)
        neg_score = sum(1 for kw in negative_keywords if kw in title_lower)
        
        if pos_score > neg_score:
            return 'positive', pos_score
        elif neg_score > pos_score:
            return 'negative', neg_score
        else:
            return 'neutral', 0
    
    def find_related_news(self, stock: Dict, all_news: List[Dict]) -> List[Dict]:
        """종목과 관련된 뉴스 찾기"""
        name = stock['name']
        symbol = stock['symbol']
        
        # 종목명 키워드 (삼성전자 -> 삼성)
        keywords = [name]
        if len(name) >= 4:
            keywords.append(name[:2])  # 앞 2글자
            keywords.append(name[:4])  # 앞 4글자
        
        related = []
        for news in all_news:
            title = news.get('title', '')
            
            # 키워드 매칭
            for keyword in keywords:
                if keyword in title:
                    sentiment, score = self.analyze_sentiment(title)
                    related.append({
                        'title': title,
                        'source': news.get('source', 'N/A'),
                        'time': news.get('time', ''),
                        'sentiment': sentiment,
                        'sentiment_score': score,
                        'url': news.get('url', '')
                    })
                    break
        
        return related
    
    def map_news_to_stocks(self) -> Dict:
        """Level 1 종목에 뉴스 매핑"""
        print("=" * 60)
        print("📊 Level 2 News Mapping for Level 1 Stocks")
        print("=" * 60)
        
        # Level 1 종목 로드
        stocks = self.load_level1_stocks()
        print(f"\n📈 Level 1에서 {len(stocks)}개 종목 로드됨")
        
        if not stocks:
            return {'status': 'error', 'message': 'No Level 1 stocks found'}
        
        # 네이버 뉴스 로드
        naver_news = self.load_latest_naver_news()
        if not naver_news:
            return {'status': 'error', 'message': 'No Naver news data found'}
        
        # 모든 뉴스 합치기
        all_news = []
        main_news = naver_news.get('main_news', {})
        flash_news = naver_news.get('flash_news', {})
        
        if main_news.get('status') == 'success':
            all_news.extend(main_news.get('news', []))
        if flash_news.get('status') == 'success':
            all_news.extend(flash_news.get('news', []))
        
        print(f"📰 네이버 뉴스 {len(all_news)}개 로드됨")
        
        # 각 종목별 관련 뉴스 찾기
        mapped_results = []
        
        for stock in stocks:
            print(f"\n   🔍 {stock['name']} 관련 뉴스 검색...")
            
            related_news = self.find_related_news(stock, all_news)
            
            # 감성 통계
            positive = sum(1 for n in related_news if n['sentiment'] == 'positive')
            negative = sum(1 for n in related_news if n['sentiment'] == 'negative')
            neutral = sum(1 for n in related_news if n['sentiment'] == 'neutral')
            
            total = len(related_news)
            sentiment_score = (positive / total * 100) if total > 0 else 50
            
            result = {
                'stock': stock,
                'related_news': related_news,
                'news_count': total,
                'sentiment': {
                    'positive': positive,
                    'negative': negative,
                    'neutral': neutral,
                    'score': round(sentiment_score, 2),
                    'label': 'Bullish' if sentiment_score >= 60 else 'Bearish' if sentiment_score <= 40 else 'Neutral'
                }
            }
            
            mapped_results.append(result)
            print(f"      ✓ {total}개 뉴스 찾음 ({result['sentiment']['label']})")
        
        # 종합 분석
        summary = self.generate_summary(mapped_results)
        
        output = {
            'mapped_at': datetime.now().isoformat(),
            'status': 'success',
            'total_stocks': len(stocks),
            'total_news': len(all_news),
            'summary': summary,
            'stocks': mapped_results
        }
        
        return output
    
    def generate_summary(self, results: List[Dict]) -> Dict:
        """종합 분석"""
        # 뉴스가 있는 종목
        stocks_with_news = [r for r in results if r['news_count'] > 0]
        
        # 감성별 분류
        bullish = [r for r in stocks_with_news if r['sentiment']['label'] == 'Bullish']
        bearish = [r for r in stocks_with_news if r['sentiment']['label'] == 'Bearish']
        neutral = [r for r in stocks_with_news if r['sentiment']['label'] == 'Neutral']
        
        # 뉴스가 많은 종목 TOP 5
        top_news_stocks = sorted(stocks_with_news, key=lambda x: x['news_count'], reverse=True)[:5]
        
        # 긍정적 뉴스 종목 TOP 5
        top_positive = sorted(bullish, key=lambda x: x['sentiment']['score'], reverse=True)[:5]
        
        # 부정적 뉴스 종목 TOP 5
        top_negative = sorted(bearish, key=lambda x: x['sentiment']['score'])[:5]
        
        return {
            'stocks_with_news': len(stocks_with_news),
            'stocks_without_news': len(results) - len(stocks_with_news),
            'sentiment_distribution': {
                'bullish': len(bullish),
                'bearish': len(bearish),
                'neutral': len(neutral)
            },
            'top_news_stocks': [
                {
                    'name': s['stock']['name'],
                    'symbol': s['stock']['symbol'],
                    'news_count': s['news_count'],
                    'sentiment': s['sentiment']['label']
                } for s in top_news_stocks
            ],
            'top_positive_stocks': [
                {
                    'name': s['stock']['name'],
                    'symbol': s['stock']['symbol'],
                    'sentiment_score': s['sentiment']['score']
                } for s in top_positive
            ],
            'top_negative_stocks': [
                {
                    'name': s['stock']['name'],
                    'symbol': s['stock']['symbol'],
                    'sentiment_score': s['sentiment']['score']
                } for s in top_negative
            ]
        }
    
    def format_report(self, output: Dict) -> str:
        """리포트 포맷팅"""
        summary = output.get('summary', {})
        stocks = output.get('stocks', [])
        
        report = f"""
{'='*60}
📊 Level 2 News Mapping Report
{'='*60}

📈 종합 현황:
   • 분석 종목 수: {output.get('total_stocks', 0)}개
   • 총 뉴스 수: {output.get('total_news', 0)}개
   • 뉴스 있는 종목: {summary.get('stocks_with_news', 0)}개
   • 뉴스 없는 종목: {summary.get('stocks_without_news', 0)}개

📊 감성 분포:
   • 🟢 Bullish: {summary.get('sentiment_distribution', {}).get('bullish', 0)}개
   • 🔴 Bearish: {summary.get('sentiment_distribution', {}).get('bearish', 0)}개
   • ⚪ Neutral: {summary.get('sentiment_distribution', {}).get('neutral', 0)}개

📰 뉴스 많은 종목 TOP 5:
"""
        
        for i, stock in enumerate(summary.get('top_news_stocks', []), 1):
            emoji = "🟢" if stock['sentiment'] == 'Bullish' else "🔴" if stock['sentiment'] == 'Bearish' else "⚪"
            report += f"   {i}. {emoji} {stock['name']} ({stock['symbol']}): {stock['news_count']}개\n"
        
        report += f"\n🟢 긍정적 뉴스 종목:\n"
        for stock in summary.get('top_positive_stocks', []):
            report += f"   • {stock['name']}: {stock['sentiment_score']:.1f}pts\n"
        
        report += f"\n🔴 부정적 뉴스 종목:\n"
        for stock in summary.get('top_negative_stocks', []):
            report += f"   • {stock['name']}: {stock['sentiment_score']:.1f}pts\n"
        
        # 상세 종목별 뉴스
        report += f"\n{'='*60}\n📋 종목별 상세 뉴스\n{'='*60}\n"
        
        for result in stocks[:5]:  # 상위 5개 종목만 상세 표시
            stock = result['stock']
            sentiment = result['sentiment']
            news_list = result['related_news'][:3]  # 상위 3개 뉴스
            
            emoji = "🟢" if sentiment['label'] == 'Bullish' else "🔴" if sentiment['label'] == 'Bearish' else "⚪"
            report += f"\n{emoji} {stock['name']} ({stock['symbol']}) - {result['news_count']}개 뉴스\n"
            report += f"   Level 1 점수: {stock['avg_score']:.1f}pts | 뉴스 감성: {sentiment['label']} ({sentiment['score']:.1f}pts)\n"
            
            if news_list:
                for i, news in enumerate(news_list, 1):
                    news_emoji = "🟢" if news['sentiment'] == 'positive' else "🔴" if news['sentiment'] == 'negative' else "⚪"
                    report += f"   {news_emoji} {i}. {news['title'][:50]}...\n"
                    report += f"      [{news['source']}] {news['time']}\n"
            else:
                report += f"   관련 뉴스 없음\n"
        
        report += f"\n{'='*60}\n"
        
        return report


def main():
    """메인 실행"""
    mapper = Level2NewsMapper()
    
    # 뉴스 매핑
    output = mapper.map_news_to_stocks()
    
    if output.get('status') == 'success':
        # 리포트 출력
        report = mapper.format_report(output)
        print(report)
        
        # 파일 저장
        output_file = f'/home/programs/kstock_analyzer/data/level2_news_mapped_{datetime.now().strftime("%Y%m%d_%H%M")}.json'
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(output, f, indent=2, ensure_ascii=False)
        
        print(f"💾 Results saved: {output_file}")
    else:
        print(f"❌ Error: {output.get('message')}")


if __name__ == '__main__':
    main()
