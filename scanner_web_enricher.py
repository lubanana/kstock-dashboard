#!/usr/bin/env python3
"""
스캐너용 웹 정보 수집 모듈
- 네이버 증권 정보 수집
- 웹 검색을 통한 추가 정보 수집
"""

import json
from datetime import datetime
from dart_realtime_scanner_enhanced import WebInfoCollector, collect_web_search_info
import sys

def enrich_scan_results_with_web_info(results, top_n=20):
    """
    스캔 결과에 웹 정보를 추가
    
    Args:
        results: 스캐너 결과 리스트
        top_n: 웹 정보를 수집할 상위 종목 수
    """
    print("\n" + "="*70)
    print("🌐 웹 정보 수집 시작")
    print("="*70)
    
    collector = WebInfoCollector()
    
    enriched_results = []
    for i, stock in enumerate(results[:top_n], 1):
        symbol = stock['symbol']
        name = stock['name']
        
        print(f"\n[{i}/{top_n}] {name} ({symbol}) 정보 수집 중...")
        
        # 네이버 증권 정보
        naver_info = collector.get_naver_stock_info(symbol)
        stock['naver'] = naver_info
        
        # 웹 검색 정보 (구조만 준비)
        web_info = collect_web_search_info(name, symbol)
        stock['web_search'] = web_info
        
        # 출력
        if naver_info.get('per'):
            print(f"   PER: {naver_info['per']:.2f}배")
        if naver_info.get('pbr'):
            print(f"   PBR: {naver_info['pbr']:.2f}배")
        if naver_info.get('foreign_ownership'):
            print(f"   외국인: {naver_info['foreign_ownership']}")
        if naver_info.get('recent_news') and len(naver_info['recent_news']) > 0:
            print(f"   📰 {naver_info['recent_news'][0][:40]}...")
        
        enriched_results.append(stock)
    
    # 나머지 결과는 그대로 추가
    enriched_results.extend(results[top_n:])
    
    return enriched_results


def print_enriched_report(results, top_n=20):
    """웹 정보가 포함된 상세 리포트 출력"""
    print("\n" + "="*70)
    print("📊 웹 정보 포함 상세 리포트")
    print("="*70)
    
    for i, r in enumerate(results[:top_n], 1):
        print(f"\n{'─'*70}")
        print(f"{i}. {r['symbol']} {r['name']}")
        print(f"{'─'*70}")
        
        # 기본 정보
        print(f"   💰 현재가: {r['price']:,.0f}원 | RSI: {r['rsi']:.1f} | 52주대비: {r['vs_52w_high']:.1f}%")
        print(f"   📈 재무점수: {r['quality_score']:.0f}/100 | ROE: {r['roe']:.1f}% | 부채비율: {r['debt_ratio']:.1f}%")
        
        # 네이버 정보
        if 'naver' in r and r['naver']:
            naver = r['naver']
            print(f"\n   📱 네이버증권 정보:")
            
            metrics = []
            if naver.get('market_cap'):
                metrics.append(f"시총: {naver['market_cap']:,.0f}억")
            if naver.get('per'):
                metrics.append(f"PER: {naver['per']:.2f}배")
            if naver.get('pbr'):
                metrics.append(f"PBR: {naver['pbr']:.2f}배")
            if naver.get('foreign_ownership'):
                metrics.append(f"외국인: {naver['foreign_ownership']}")
            
            if metrics:
                print(f"      {' | '.join(metrics)}")
            
            if naver.get('recent_news') and len(naver['recent_news']) > 0:
                print(f"\n      📰 최신 뉴스:")
                for j, news in enumerate(naver['recent_news'][:2], 1):
                    print(f"         {j}. {news[:60]}...")


if __name__ == '__main__':
    # 테스트
    import sys
    sys.path.insert(0, '/root/.openclaw/workspace/strg')
    
    # 샘플 데이터로 테스트
    sample_results = [
        {
            'symbol': '031980',
            'name': '피에스케이홀딩스',
            'price': 97800,
            'rsi': 34.1,
            'vs_52w_high': -24.3,
            'quality_score': 100,
            'roe': 27.1,
            'debt_ratio': 19.0,
            'op_margin': 41.1,
            'year': '2024'
        },
        {
            'symbol': '042700',
            'name': '한미반도체',
            'price': 260500,
            'rsi': 19.9,
            'vs_52w_high': -22.4,
            'quality_score': 90,
            'roe': 36.7,
            'debt_ratio': 31.4,
            'op_margin': 45.7,
            'year': '2024'
        }
    ]
    
    enriched = enrich_scan_results_with_web_info(sample_results, top_n=2)
    print_enriched_report(enriched, top_n=2)
