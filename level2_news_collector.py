#!/usr/bin/env python3
"""
Level 2 News Collector for Level 1 Stocks
Level 1 종목별 뉴스 수집 및 정리 모듈
"""

import json
import asyncio
from datetime import datetime
from typing import Dict, List
from naver_news_scraper import NaverNewsScraper


class Level2NewsCollector:
    """Level 2 뉴스 수집기 - Level 1 종목별 뉴스 정리"""
    
    def __init__(self):
        self.scraper = NaverNewsScraper()
        self.base_path = '/home/programs/kstock_analyzer'
    
    def load_level1_stocks(self) -> List[Dict]:
        """Level 1 분석 결과에서 종목 리스트 로드"""
        import os
        import glob
        
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
                    'recommendation': result.get('recommendation', 'HOLD')
                })
        
        # 점수 순으로 정렬
        stocks.sort(key=lambda x: x['avg_score'], reverse=True)
        return stocks
    
    async def collect_news_for_stock(self, stock: Dict) -> Dict:
        """개별 종목 뉴스 수집"""
        symbol = stock['symbol']
        name = stock['name']
        
        print(f"\n   📰 {name} ({symbol}) 뉴스 수집 중...")
        
        # 종목 코드에서 .KS/.KQ 제거
        stock_code = symbol.replace('.KS', '').replace('.KQ', '')
        
        # 네이버 주식 뉴스 수집
        news_data = await self.scraper.get_stock_news(stock_code)
        
        # 감성 분석
        if news_data.get('status') == 'success':
            sentiment = self.scraper.analyze_sentiment(news_data.get('news', []))
            news_data['sentiment_analysis'] = sentiment
        
        # 종목 정보 추가
        news_data['stock_info'] = stock
        
        return news_data
    
    async def collect_all_news(self, top_n: int = 10) -> Dict:
        """상위 N개 종목 뉴스 수집"""
        print("=" * 60)
        print("📊 Level 2 News Collection for Level 1 Stocks")
        print("=" * 60)
        
        # Level 1 종목 로드
        stocks = self.load_level1_stocks()
        print(f"\n📈 Level 1에서 {len(stocks)}개 종목 로드됨")
        
        if not stocks:
            return {'status': 'error', 'message': 'No Level 1 stocks found'}
        
        # 상위 N개 종목 선택
        target_stocks = stocks[:top_n]
        print(f"\n🎯 상위 {len(target_stocks)}개 종목 뉴스 수집 시작")
        
        # 각 종목별 뉴스 수집
        results = []
        for stock in target_stocks:
            try:
                news_data = await self.collect_news_for_stock(stock)
                results.append(news_data)
                await asyncio.sleep(1)  # 서버 부하 방지
            except Exception as e:
                print(f"   ⚠️  Error collecting news for {stock['name']}: {e}")
                results.append({
                    'stock_info': stock,
                    'status': 'error',
                    'error': str(e)
                })
        
        # 종합 분석
        summary = self.generate_summary(results)
        
        output = {
            'collected_at': datetime.now().isoformat(),
            'status': 'success',
            'total_stocks': len(target_stocks),
            'summary': summary,
            'stocks_news': results
        }
        
        return output
    
    def generate_summary(self, results: List[Dict]) -> Dict:
        """뉴스 종합 분석"""
        total_news = 0
        total_positive = 0
        total_negative = 0
        total_neutral = 0
        
        stock_sentiments = []
        
        for result in results:
            if result.get('status') == 'success':
                sentiment = result.get('sentiment_analysis', {})
                stock_info = result.get('stock_info', {})
                
                total_news += sentiment.get('total_news', 0)
                total_positive += sentiment.get('positive', 0)
                total_negative += sentiment.get('negative', 0)
                total_neutral += sentiment.get('neutral', 0)
                
                stock_sentiments.append({
                    'name': stock_info.get('name', ''),
                    'symbol': stock_info.get('symbol', ''),
                    'score': stock_info.get('avg_score', 0),
                    'sentiment_score': sentiment.get('sentiment_score', 50),
                    'sentiment_label': sentiment.get('sentiment_label', 'Neutral'),
                    'news_count': sentiment.get('total_news', 0)
                })
        
        # 전체 감성 점수 계산
        if total_news > 0:
            overall_sentiment = (total_positive / total_news) * 100
        else:
            overall_sentiment = 50
        
        # 감성별 종목 분류
        bullish_stocks = [s for s in stock_sentiments if s['sentiment_label'] == 'Bullish']
        bearish_stocks = [s for s in stock_sentiments if s['sentiment_label'] == 'Bearish']
        neutral_stocks = [s for s in stock_sentiments if s['sentiment_label'] == 'Neutral']
        
        return {
            'total_news': total_news,
            'overall_sentiment_score': round(overall_sentiment, 2),
            'overall_sentiment_label': 'Bullish' if overall_sentiment >= 60 else 'Bearish' if overall_sentiment <= 40 else 'Neutral',
            'sentiment_breakdown': {
                'positive': total_positive,
                'negative': total_negative,
                'neutral': total_neutral
            },
            'stocks_by_sentiment': {
                'bullish': bullish_stocks,
                'bearish': bearish_stocks,
                'neutral': neutral_stocks
            },
            'top_positive_news': sorted(stock_sentiments, key=lambda x: x['sentiment_score'], reverse=True)[:5],
            'top_negative_news': sorted(stock_sentiments, key=lambda x: x['sentiment_score'])[:5]
        }
    
    def format_report(self, output: Dict) -> str:
        """리포트 포맷팅"""
        summary = output.get('summary', {})
        
        report = f"""
{'='*60}
📊 Level 2 News Analysis Report
{'='*60}

📈 전체 감성 분석:
   • 총 뉴스 수: {summary.get('total_news', 0)}개
   • 전체 감성 점수: {summary.get('overall_sentiment_score', 0):.1f}/100 ({summary.get('overall_sentiment_label', 'N/A')})
   • 긍정: {summary.get('sentiment_breakdown', {}).get('positive', 0)}개
   • 부정: {summary.get('sentiment_breakdown', {}).get('negative', 0)}개
   • 중립: {summary.get('sentiment_breakdown', {}).get('neutral', 0)}개

🟢 긍정적 뉴스 종목 (TOP 5):
"""
        
        for stock in summary.get('top_positive_news', [])[:5]:
            report += f"   • {stock['name']} ({stock['symbol']}): {stock['sentiment_score']:.1f}pts ({stock['news_count']}개 뉴스)\n"
        
        report += f"\n🔴 부정적 뉴스 종목 (TOP 5):\n"
        
        for stock in summary.get('top_negative_news', [])[:5]:
            report += f"   • {stock['name']} ({stock['symbol']}): {stock['sentiment_score']:.1f}pts ({stock['news_count']}개 뉴스)\n"
        
        report += f"\n{'='*60}\n"
        
        return report


async def main():
    """메인 실행"""
    collector = Level2NewsCollector()
    
    # 상위 10개 종목 뉴스 수집
    output = await collector.collect_all_news(top_n=10)
    
    if output.get('status') == 'success':
        # 리포트 출력
        report = collector.format_report(output)
        print(report)
        
        # 파일 저장
        output_file = f'/home/programs/kstock_analyzer/data/level2_news_{datetime.now().strftime("%Y%m%d_%H%M")}.json'
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(output, f, indent=2, ensure_ascii=False)
        
        print(f"💾 Results saved: {output_file}")
    else:
        print(f"❌ Error: {output.get('message')}")


if __name__ == '__main__':
    asyncio.run(main())
