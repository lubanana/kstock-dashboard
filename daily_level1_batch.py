#!/usr/bin/env python3
import json
import os
import sys
from datetime import datetime
import time

sys.path.insert(0, '/home/programs/kstock_analyzer/agents')

from technical_agent import TechnicalAnalysisAgent
from quant_agent import QuantAnalysisAgent
from qualitative_agent import QualitativeAnalysisAgent
from news_agent import NewsSentimentAgent

BASE_PATH = '/home/programs/kstock_analyzer'
OUTPUT_PATH = f'{BASE_PATH}/data/level1_daily'

KOREAN_STOCKS = [
    {'symbol': '005930.KS', 'name': '삼성전자'},
    {'symbol': '000660.KS', 'name': 'SK하이닉스'},
    {'symbol': '035420.KS', 'name': 'NAVER'},
    {'symbol': '005380.KS', 'name': '현대차'},
    {'symbol': '051910.KS', 'name': 'LG화학'},
    {'symbol': '035720.KS', 'name': '카카오'},
    {'symbol': '006400.KS', 'name': '삼성SDI'},
    {'symbol': '068270.KS', 'name': '셀트리온'},
    {'symbol': '005490.KS', 'name': 'POSCO홀딩스'},
    {'symbol': '028260.KS', 'name': '삼성물산'},
    {'symbol': '012450.KS', 'name': '한화에어로스페이스'},
    {'symbol': '055550.KS', 'name': '신한지주'},
    {'symbol': '105560.KS', 'name': 'KB금융'},
    {'symbol': '138040.KS', 'name': '메리츠금융'},
    {'symbol': '032830.KS', 'name': '삼성생명'},
    {'symbol': '015760.KS', 'name': '한국전력'},
    {'symbol': '003670.KS', 'name': '포스코퓨처엠'},
    {'symbol': '009150.KS', 'name': '삼성전기'},
    {'symbol': '018260.KS', 'name': '삼성에스디에스'},
    {'symbol': '033780.KS', 'name': 'KT&G'},
    {'symbol': '247540.KS', 'name': '에코프로비엠'},
    {'symbol': '086520.KS', 'name': '에코프로'},
    {'symbol': '196170.KS', 'name': '알테오젠'},
    {'symbol': '352820.KS', 'name': '하이브'},
    {'symbol': '259960.KS', 'name': '크래프톤'},
]

def analyze_stock(stock):
    symbol = stock['symbol']
    name = stock['name']
    print(f"\n📊 {name} ({symbol})")
    
    result = {'symbol': symbol, 'name': name, 'date': datetime.now().isoformat(), 'agents': {}}
    
    try:
        tech = TechnicalAnalysisAgent(symbol, name)
        r = tech.analyze()
        result['agents']['TECH'] = {'score': r.get('total_score', 0), 'rec': r.get('recommendation', 'HOLD')}
        print(f"   TECH: {r.get('total_score', 0)} pts")
        
        quant = QuantAnalysisAgent(symbol, name)
        r = quant.analyze()
        result['agents']['QUANT'] = {'score': r.get('total_score', 0), 'rec': r.get('recommendation', 'HOLD')}
        print(f"   QUANT: {r.get('total_score', 0)} pts")
        
        qual = QualitativeAnalysisAgent(symbol, name)
        r = qual.analyze()
        result['agents']['QUAL'] = {'score': r.get('total_score', 0), 'rec': r.get('recommendation', 'HOLD')}
        print(f"   QUAL: {r.get('total_score', 0)} pts")
        
        news = NewsSentimentAgent(symbol, name)
        r = news.analyze()
        result['agents']['NEWS'] = {'score': r.get('total_score', 0), 'rec': r.get('recommendation', 'HOLD')}
        print(f"   NEWS: {r.get('total_score', 0)} pts")
        
        scores = [a['score'] for a in result['agents'].values()]
        result['avg_score'] = round(sum(scores) / len(scores), 1)
        result['status'] = 'success'
        
    except Exception as e:
        print(f"   ❌ Error: {e}")
        result['status'] = 'error'
        result['error'] = str(e)
    
    return result

def main():
    os.makedirs(OUTPUT_PATH, exist_ok=True)
    stocks = KOREAN_STOCKS
    
    print("=" * 70)
    print(f"🚀 LEVEL 1 DAILY BATCH - {len(stocks)} stocks")
    print(f"   Time: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print("=" * 70)
    
    results = []
    for i, stock in enumerate(stocks, 1):
        print(f"\n[{i}/{len(stocks)}]", end=' ')
        result = analyze_stock(stock)
        results.append(result)
        time.sleep(1)
    
    date_str = datetime.now().strftime('%Y%m%d')
    output_file = f"{OUTPUT_PATH}/level1_batch_{date_str}.json"
    
    final = {
        'date': datetime.now().isoformat(),
        'total': len(stocks),
        'success': len([r for r in results if r.get('status') == 'success']),
        'results': results
    }
    
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(final, f, indent=2, ensure_ascii=False)
    
    print("\n" + "=" * 70)
    print("📊 BATCH COMPLETE")
    print(f"   Output: {output_file}")
    print("=" * 70)

if __name__ == '__main__':
    main()
