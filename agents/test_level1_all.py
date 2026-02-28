#!/usr/bin/env python3
"""
Level 1 Agents Integration Test
Level 1 전체 에이전트 통합 테스트
"""

import sys
import json
from datetime import datetime

sys.path.insert(0, '/home/programs/kstock_analyzer/agents')

from technical_agent import TechnicalAnalysisAgent
from quant_agent import QuantAnalysisAgent
from qualitative_agent import QualitativeAnalysisAgent
from news_agent import NewsSentimentAgent


def run_all_level1_agents(symbol: str, name: str) -> dict:
    """Level 1 모든 에이전트 실행"""
    
    print("=" * 70)
    print(f"🚀 LEVEL 1 AGENTS INTEGRATION TEST")
    print(f"   Target: {name} ({symbol})")
    print(f"   Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 70)
    
    results = {
        'symbol': symbol,
        'name': name,
        'analysis_time': datetime.now().isoformat(),
        'agents': {}
    }
    
    # 1. Technical Agent
    print("\n" + "-" * 70)
    print("1️⃣  TECHNICAL ANALYST (TECH_001)")
    print("-" * 70)
    tech_agent = TechnicalAnalysisAgent(symbol, name)
    tech_result = tech_agent.analyze()
    results['agents']['TECH_001'] = {
        'name': 'Technical Analyst',
        'score': tech_result.get('total_score', 0),
        'recommendation': tech_result.get('recommendation', 'HOLD'),
        'key_signals': tech_result.get('key_signals', [])[:3]
    }
    
    # 2. Quant Agent
    print("\n" + "-" * 70)
    print("2️⃣  QUANT ANALYST (QUANT_001)")
    print("-" * 70)
    quant_agent = QuantAnalysisAgent(symbol, name)
    quant_result = quant_agent.analyze()
    results['agents']['QUANT_001'] = {
        'name': 'Quant Analyst',
        'score': quant_result.get('total_score', 0),
        'recommendation': quant_result.get('recommendation', 'HOLD'),
        'key_metrics': quant_result.get('key_metrics', {})
    }
    
    # 3. Qualitative Agent
    print("\n" + "-" * 70)
    print("3️⃣  QUALITATIVE ANALYST (QUAL_001)")
    print("-" * 70)
    qual_agent = QualitativeAnalysisAgent(symbol, name)
    qual_result = qual_agent.analyze()
    results['agents']['QUAL_001'] = {
        'name': 'Qualitative Analyst',
        'score': qual_result.get('total_score', 0),
        'recommendation': qual_result.get('recommendation', 'HOLD'),
        'moat_rating': qual_result.get('moat_rating', 'None')
    }
    
    # 4. News Agent
    print("\n" + "-" * 70)
    print("4️⃣  NEWS SENTIMENT ANALYST (NEWS_001)")
    print("-" * 70)
    news_agent = NewsSentimentAgent(symbol, name)
    news_result = news_agent.analyze()
    results['agents']['NEWS_001'] = {
        'name': 'News Sentiment Analyst',
        'score': news_result.get('total_score', 0),
        'recommendation': news_result.get('recommendation', 'HOLD'),
        'sentiment_trend': news_result.get('sentiment_trend', 'Unknown')
    }
    
    # 종합 결과 계산
    scores = [r['score'] for r in results['agents'].values()]
    avg_score = sum(scores) / len(scores) if scores else 0
    
    # 추천 집계
    recommendations = [r['recommendation'] for r in results['agents'].values()]
    buy_count = recommendations.count('BUY')
    hold_count = recommendations.count('HOLD')
    sell_count = recommendations.count('SELL')
    
    if buy_count >= 3:
        consensus = "STRONG BUY"
    elif buy_count >= 2:
        consensus = "BUY"
    elif sell_count >= 2:
        consensus = "SELL"
    else:
        consensus = "HOLD"
    
    results['summary'] = {
        'average_score': round(avg_score, 1),
        'consensus': consensus,
        'buy_votes': buy_count,
        'hold_votes': hold_count,
        'sell_votes': sell_count,
        'total_agents': 4
    }
    
    # 최종 출력
    print("\n" + "=" * 70)
    print("📊 LEVEL 1 ANALYSIS SUMMARY")
    print("=" * 70)
    print(f"\n{'Agent':<25} {'Score':<10} {'Recommendation':<15}")
    print("-" * 70)
    for agent_id, agent_data in results['agents'].items():
        print(f"{agent_data['name']:<25} {agent_data['score']}/100    {agent_data['recommendation']:<15}")
    
    print("\n" + "-" * 70)
    print(f"Average Score: {avg_score:.1f}/100")
    print(f"Consensus: {consensus} ({buy_count} BUY, {hold_count} HOLD, {sell_count} SELL)")
    print("=" * 70)
    
    return results


def main():
    import argparse
    
    parser = argparse.ArgumentParser(description='Level 1 Agents Integration Test')
    parser.add_argument('--symbol', default='005930.KS', help='Stock symbol')
    parser.add_argument('--name', default='삼성전자', help='Stock name')
    parser.add_argument('--output', help='Output JSON file')
    
    args = parser.parse_args()
    
    # 실행
    results = run_all_level1_agents(args.symbol, args.name)
    
    # 저장
    if args.output:
        with open(args.output, 'w', encoding='utf-8') as f:
            json.dump(results, f, indent=2, ensure_ascii=False)
        print(f"\n💾 Results saved: {args.output}")
    
    # JSON 출력
    print("\n📋 Full JSON Output:")
    print(json.dumps(results, indent=2, ensure_ascii=False))


if __name__ == '__main__':
    main()
