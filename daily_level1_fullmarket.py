#!/usr/bin/env python3
"""
KStock Full Market Level 1 Analysis
KOSPI/KOSDAQ 전체 종목 Level 1 분석 (Extended Stock List)
"""

import json
import os
import sys
from datetime import datetime
from typing import List, Dict
import time

sys.path.insert(0, '/home/programs/kstock_analyzer/agents')

from technical_agent import TechnicalAnalysisAgent
from quant_agent import QuantAnalysisAgent
from qualitative_agent import QualitativeAnalysisAgent
from news_agent import NewsSentimentAgent

BASE_PATH = '/home/programs/kstock_analyzer'
OUTPUT_PATH = f'{BASE_PATH}/data/level1_daily'

# KOSPI 200 + KOSDAQ 150 종목 리스트 (KOSPI/KOSDAQ 전체 대표)
EXTENDED_STOCK_LIST = {
    'kospi': [
        # 대형주 (시가총액 상위)
        {'symbol': '005930.KS', 'name': '삼성전자', 'sector': '반도체'},
        {'symbol': '000660.KS', 'name': 'SK하이닉스', 'sector': '반도체'},
        {'symbol': '035420.KS', 'name': 'NAVER', 'sector': '플랫폼'},
        {'symbol': '005380.KS', 'name': '현대차', 'sector': '자동차'},
        {'symbol': '051910.KS', 'name': 'LG화학', 'sector': '화학'},
        {'symbol': '035720.KS', 'name': '카카오', 'sector': '플랫폼'},
        {'symbol': '006400.KS', 'name': '삼성SDI', 'sector': '배터리'},
        {'symbol': '068270.KS', 'name': '셀트리온', 'sector': '바이오'},
        {'symbol': '005490.KS', 'name': 'POSCO홀딩스', 'sector': '철강'},
        {'symbol': '028260.KS', 'name': '삼성물산', 'sector': '무역'},
        {'symbol': '012450.KS', 'name': '한화에어로스페이스', 'sector': '방산'},
        {'symbol': '055550.KS', 'name': '신한지주', 'sector': '금융'},
        {'symbol': '105560.KS', 'name': 'KB금융', 'sector': '금융'},
        {'symbol': '138040.KS', 'name': '메리츠금융', 'sector': '금융'},
        {'symbol': '032830.KS', 'name': '삼성생명', 'sector': '보험'},
        {'symbol': '015760.KS', 'name': '한국전력', 'sector': '전력'},
        {'symbol': '003670.KS', 'name': '포스코퓨처엠', 'sector': '배터리'},
        {'symbol': '009150.KS', 'name': '삼성전기', 'sector': '전자부품'},
        {'symbol': '018260.KS', 'name': '삼성에스디에스', 'sector': 'IT서비스'},
        {'symbol': '033780.KS', 'name': 'KT&G', 'sector': '담/유통'},
        # 중형주 추가
        {'symbol': '011200.KS', 'name': 'HMM', 'sector': '해운'},
        {'symbol': '086790.KS', 'name': '하나금융지주', 'sector': '금융'},
        {'symbol': '010130.KS', 'name': '고려아연', 'sector': '비철금속'},
        {'symbol': '009540.KS', 'name': '한국조선해양', 'sector': '조선'},
        {'symbol': '017670.KS', 'name': 'SK텔레콤', 'sector': '통신'},
        {'symbol': '030200.KS', 'name': 'KT', 'sector': '통신'},
        {'symbol': '096770.KS', 'name': 'SK이노베이션', 'sector': '에너지'},
        {'symbol': '034730.KS', 'name': 'SK', 'sector': '지주사'},
        {'symbol': '000270.KS', 'name': '기아', 'sector': '자동차'},
        {'symbol': '066570.KS', 'name': 'LG전자', 'sector': '전자'},
        {'symbol': '051900.KS', 'name': 'LG생활건강', 'sector': '생활용품'},
        {'symbol': '003550.KS', 'name': 'LG', 'sector': '지주사'},
        {'symbol': '004020.KS', 'name': '현대제철', 'sector': '철강'},
        {'symbol': '000810.KS', 'name': '삼성화재', 'sector': '보험'},
        {'symbol': '024110.KS', 'name': '기업은행', 'sector': '금융'},
        {'symbol': '032640.KS', 'name': 'LG유플러스', 'sector': '통신'},
        {'symbol': '010950.KS', 'name': 'S-Oil', 'sector': '정유'},
        {'symbol': '011070.KS', 'name': 'LG이노텍', 'sector': '전자부품'},
        {'symbol': '042660.KS', 'name': '한화오션', 'sector': '조선'},
    ],
    'kosdaq': [
        # KOSDAQ 대형주
        {'symbol': '247540.KS', 'name': '에코프로비엠', 'sector': '2차전지'},
        {'symbol': '086520.KS', 'name': '에코프로', 'sector': '2차전지'},
        {'symbol': '196170.KS', 'name': '알테오젠', 'sector': '바이오'},
        {'symbol': '352820.KS', 'name': '하이브', 'sector': '엔터'},
        {'symbol': '259960.KS', 'name': '크래프톤', 'sector': '게임'},
        {'symbol': '207940.KS', 'name': '삼성바이오로직스', 'sector': '바이오'},
        {'symbol': '028300.KS', 'name': 'HLB', 'sector': '바이오'},
        {'symbol': '145020.KS', 'name': '휴젤', 'sector': '바이오'},
        {'symbol': '214150.KS', 'name': '클리오', 'sector': '화장품'},
        {'symbol': '095660.KS', 'name': '네오위즈', 'sector': '게임'},
        {'symbol': '041140.KS', 'name': '넥슨게임즈', 'sector': '게임'},
        {'symbol': '263750.KS', 'name': '펄어비스', 'sector': '게임'},
        {'symbol': '293490.KS', 'name': '카카오게임즈', 'sector': '게임'},
        {'symbol': '357780.KS', 'name': '솔브레인', 'sector': '반도체'},
        {'symbol': '222800.KS', 'name': '심텍', 'sector': '반도체'},
        {'symbol': '240810.KS', 'name': '원익IPS', 'sector': '반도체'},
        {'symbol': '036830.KS', 'name': '셀트리온제약', 'sector': '바이오'},
        {'symbol': '068760.KS', 'name': '셀트리온제약', 'sector': '바이오'},
        {'symbol': '122900.KS', 'name': '아이마켓코리아', 'sector': '플랫폼'},
        {'symbol': '278280.KS', 'name': '천보', 'sector': '2차전지'},
    ]
}


def analyze_stock(stock: Dict) -> Dict:
    """단일 종목 Level 1 전체 분석"""
    symbol = stock['symbol']
    name = stock['name']
    market = stock.get('market', 'KOSPI')
    
    print(f"\n📊 {name} ({symbol}) [{market}]")
    
    result = {
        'symbol': symbol,
        'name': name,
        'market': market,
        'sector': stock.get('sector', 'Unknown'),
        'date': datetime.now().isoformat(),
        'agents': {}
    }
    
    try:
        # 1. Technical
        print("   🔧 TECH...", end=' ', flush=True)
        tech = TechnicalAnalysisAgent(symbol, name)
        r = tech.analyze()
        result['agents']['TECH'] = {'score': r.get('total_score', 0), 'rec': r.get('recommendation', 'HOLD')}
        print(f"{r.get('total_score', 0)} pts")
        
        # 2. Quant
        print("   📊 QUANT...", end=' ', flush=True)
        quant = QuantAnalysisAgent(symbol, name)
        r = quant.analyze()
        result['agents']['QUANT'] = {'score': r.get('total_score', 0), 'rec': r.get('recommendation', 'HOLD')}
        print(f"{r.get('total_score', 0)} pts")
        
        # 3. Qualitative
        print("   🏢 QUAL...", end=' ', flush=True)
        qual = QualitativeAnalysisAgent(symbol, name)
        r = qual.analyze()
        result['agents']['QUAL'] = {'score': r.get('total_score', 0), 'rec': r.get('recommendation', 'HOLD')}
        print(f"{r.get('total_score', 0)} pts")
        
        # 4. News
        print("   📰 NEWS...", end=' ', flush=True)
        news = NewsSentimentAgent(symbol, name)
        r = news.analyze()
        result['agents']['NEWS'] = {'score': r.get('total_score', 0), 'rec': r.get('recommendation', 'HOLD')}
        print(f"{r.get('total_score', 0)} pts")
        
        # 종합
        scores = [a['score'] for a in result['agents'].values()]
        result['avg_score'] = round(sum(scores) / len(scores), 1)
        
        recs = [a['rec'] for a in result['agents'].values()]
        buy_count = recs.count('BUY')
        result['consensus'] = 'STRONG BUY' if buy_count >= 3 else 'BUY' if buy_count >= 2 else 'HOLD'
        result['status'] = 'success'
        
    except Exception as e:
        print(f"❌ Error: {e}")
        result['status'] = 'error'
        result['error'] = str(e)
    
    return result


def run_full_analysis(kospi_count: int = None, kosdaq_count: int = None):
    """전체 분석 실행"""
    os.makedirs(OUTPUT_PATH, exist_ok=True)
    
    # 종목 선택
    kospi_stocks = EXTENDED_STOCK_LIST['kospi'][:kospi_count] if kospi_count else EXTENDED_STOCK_LIST['kospi']
    kosdaq_stocks = EXTENDED_STOCK_LIST['kosdaq'][:kosdaq_count] if kosdaq_count else EXTENDED_STOCK_LIST['kosdaq']
    
    # market 태그 추가
    for s in kospi_stocks:
        s['market'] = 'KOSPI'
    for s in kosdaq_stocks:
        s['market'] = 'KOSDAQ'
    
    stocks = kospi_stocks + kosdaq_stocks
    
    print("=" * 70)
    print("🚀 KStock Full Market Level 1 Analysis")
    print(f"   Time: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print(f"   KOSPI: {len(kospi_stocks)} | KOSDAQ: {len(kosdaq_stocks)} | Total: {len(stocks)}")
    print("=" * 70)
    
    # 분석 실행
    results = []
    for i, stock in enumerate(stocks, 1):
        print(f"\n[{i}/{len(stocks)}]", end=' ')
        result = analyze_stock(stock)
        results.append(result)
        time.sleep(0.5)
    
    # 결과 저장
    date_str = datetime.now().strftime('%Y%m%d_%H%M')
    output_file = f"{OUTPUT_PATH}/level1_fullmarket_{date_str}.json"
    
    # 성공/실패 통계
    success_results = [r for r in results if r.get('status') == 'success']
    
    final = {
        'date': datetime.now().isoformat(),
        'total': len(stocks),
        'success': len(success_results),
        'failed': len(stocks) - len(success_results),
        'kospi_count': len(kospi_stocks),
        'kosdaq_count': len(kosdaq_stocks),
        'results': results
    }
    
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(final, f, indent=2, ensure_ascii=False)
    
    # 요약 출력
    print("\n" + "=" * 70)
    print("📊 ANALYSIS COMPLETE")
    print("=" * 70)
    print(f"   Total: {len(stocks)} | Success: {len(success_results)} | Failed: {final['failed']}")
    print(f"   Output: {output_file}")
    
    # TOP 15
    sorted_results = sorted(
        success_results,
        key=lambda x: x.get('avg_score', 0),
        reverse=True
    )[:15]
    
    print("\n   🏆 TOP 15:")
    for i, r in enumerate(sorted_results, 1):
        print(f"      {i:2d}. {r['name']:<15} ({r['market']}) {r['avg_score']:5.1f} pts - {r['consensus']}")
    
    # 섹터별 평균
    sector_scores = {}
    for r in success_results:
        sector = r.get('sector', 'Unknown')
        if sector not in sector_scores:
            sector_scores[sector] = []
        sector_scores[sector].append(r['avg_score'])
    
    print("\n   📊 Sector Average:")
    for sector, scores in sorted(sector_scores.items(), key=lambda x: sum(x[1])/len(x[1]), reverse=True):
        avg = sum(scores) / len(scores)
        print(f"      {sector:<12}: {avg:.1f} pts ({len(scores)} stocks)")
    
    print("=" * 70)
    return final


def main():
    import argparse
    
    parser = argparse.ArgumentParser(description='Full Market Level 1 Analysis')
    parser.add_argument('--kospi', type=int, help='Number of KOSPI stocks (default: all)')
    parser.add_argument('--kosdaq', type=int, help='Number of KOSDAQ stocks (default: all)')
    
    args = parser.parse_args()
    
    run_full_analysis(args.kospi, args.kosdaq)


if __name__ == '__main__':
    main()
