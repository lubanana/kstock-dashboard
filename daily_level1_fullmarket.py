#!/usr/bin/env python3
"""
KStock Full Market Level 1 Analysis with FinanceDataReader
KOSPI/KOSDAQ 전체 종목 Level 1 분석 (FinanceDataReader 활용)
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

# FinanceDataReader 임포트
try:
    import FinanceDataReader as fdr
    FDR_AVAILABLE = True
    print("✅ FinanceDataReader loaded successfully")
except ImportError:
    print("⚠️  FinanceDataReader not available, using fallback list")
    FDR_AVAILABLE = False


class StockDataReader:
    """FinanceDataReader 기반 종목 데이터 리더"""
    
    def __init__(self):
        self.fdr_available = FDR_AVAILABLE
        self.sector_mapping = self._load_sector_mapping()
    
    def _load_sector_mapping(self) -> Dict:
        """섹터 매핑 로드 (캐시 또는 기본값)"""
        # 기본 섹터 매핑 (주요 종목)
        return {
            '005930': '반도체', '000660': '반도체', '035420': '플랫폼',
            '005380': '자동차', '051910': '화학', '035720': '플랫폼',
            '006400': '배터리', '068270': '바이오', '005490': '철강',
            '028260': '무역', '012450': '방산', '055550': '금융',
            '105560': '금융', '138040': '금융', '032830': '보험',
            '015760': '전력', '003670': '배터리', '009150': '전자부품',
            '018260': 'IT서비스', '033780': '담/유통', '011200': '해운',
            '086790': '금융', '010130': '비철금속', '009540': '조선',
            '017670': '통신', '030200': '통신', '096770': '에너지',
            '034730': '지주사', '000270': '자동차', '066570': '전자',
            '051900': '생활용품', '003550': '지주사', '004020': '철강',
            '000810': '보험', '024110': '금융', '032640': '통신',
            '010950': '정유', '011070': '전자부품', '042660': '조선',
            '247540': '2차전지', '086520': '2차전지', '196170': '바이오',
            '352820': '엔터', '259960': '게임', '207940': '바이오',
            '028300': '바이오', '145020': '바이오', '214150': '화장품',
            '095660': '게임', '041140': '게임', '263750': '게임',
            '293490': '게임', '357780': '반도체', '222800': '반도체',
            '240810': '반도체', '036830': '바이오', '068760': '바이오',
            '122900': '플랫폼', '278280': '2차전지',
        }
    
    def get_kospi_stocks(self, limit: int = 100) -> List[Dict]:
        """KOSPI 종목 동적 조회"""
        if not self.fdr_available:
            return self._get_fallback_kospi(limit)
        
        try:
            print("📊 Fetching KOSPI stock list from FinanceDataReader...")
            kospi = fdr.StockListing('KOSPI')
            
            stocks = []
            for _, row in kospi.head(limit).iterrows():
                code = str(row.get('Code', '')).zfill(6)
                name = row.get('Name', '')
                if code and name:
                    stocks.append({
                        'symbol': f"{code}.KS",
                        'name': name,
                        'market': 'KOSPI',
                        'sector': self.sector_mapping.get(code, '기타')
                    })
            
            print(f"   ✅ Loaded {len(stocks)} KOSPI stocks")
            return stocks
            
        except Exception as e:
            print(f"   ❌ Error fetching KOSPI: {e}")
            return self._get_fallback_kospi(limit)
    
    def get_kosdaq_stocks(self, limit: int = 100) -> List[Dict]:
        """KOSDAQ 종목 동적 조회"""
        if not self.fdr_available:
            return self._get_fallback_kosdaq(limit)
        
        try:
            print("📊 Fetching KOSDAQ stock list from FinanceDataReader...")
            kosdaq = fdr.StockListing('KOSDAQ')
            
            stocks = []
            for _, row in kosdaq.head(limit).iterrows():
                code = str(row.get('Code', '')).zfill(6)
                name = row.get('Name', '')
                if code and name:
                    stocks.append({
                        'symbol': f"{code}.KS",
                        'name': name,
                        'market': 'KOSDAQ',
                        'sector': self.sector_mapping.get(code, '기타')
                    })
            
            print(f"   ✅ Loaded {len(stocks)} KOSDAQ stocks")
            return stocks
            
        except Exception as e:
            print(f"   ❌ Error fetching KOSDAQ: {e}")
            return self._get_fallback_kosdaq(limit)
    
    def get_all_stocks(self, kospi_limit: int = 100, kosdaq_limit: int = 50) -> List[Dict]:
        """전체 종목 조회"""
        kospi = self.get_kospi_stocks(kospi_limit)
        kosdaq = self.get_kosdaq_stocks(kosdaq_limit)
        return kospi + kosdaq
    
    def _get_fallback_kospi(self, limit: int) -> List[Dict]:
        """KOSPI 폴리백 리스트"""
        fallback = [
            {'symbol': '005930.KS', 'name': '삼성전자', 'market': 'KOSPI', 'sector': '반도체'},
            {'symbol': '000660.KS', 'name': 'SK하이닉스', 'market': 'KOSPI', 'sector': '반도체'},
            {'symbol': '035420.KS', 'name': 'NAVER', 'market': 'KOSPI', 'sector': '플랫폼'},
            {'symbol': '005380.KS', 'name': '현대차', 'market': 'KOSPI', 'sector': '자동차'},
            {'symbol': '051910.KS', 'name': 'LG화학', 'market': 'KOSPI', 'sector': '화학'},
        ]
        return fallback[:limit]
    
    def _get_fallback_kosdaq(self, limit: int) -> List[Dict]:
        """KOSDAQ 폴리백 리스트"""
        fallback = [
            {'symbol': '247540.KS', 'name': '에코프로비엠', 'market': 'KOSDAQ', 'sector': '2차전지'},
            {'symbol': '086520.KS', 'name': '에코프로', 'market': 'KOSDAQ', 'sector': '2차전지'},
            {'symbol': '196170.KS', 'name': '알테오젠', 'market': 'KOSDAQ', 'sector': '바이오'},
        ]
        return fallback[:limit]


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
    
    # FinanceDataReader로 종목 조회
    reader = StockDataReader()
    
    print("=" * 70)
    print("🚀 KStock Full Market Level 1 Analysis")
    print(f"   Data Source: {'FinanceDataReader' if FDR_AVAILABLE else 'Fallback List'}")
    print(f"   Time: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print("=" * 70)
    
    # 종목 선택
    kospi_stocks = reader.get_kospi_stocks(kospi_count or 100)
    kosdaq_stocks = reader.get_kosdaq_stocks(kosdaq_count or 50)
    
    stocks = kospi_stocks + kosdaq_stocks
    
    print(f"\n📋 Total stocks to analyze: {len(stocks)}")
    print(f"   - KOSPI: {len(kospi_stocks)}")
    print(f"   - KOSDAQ: {len(kosdaq_stocks)}")
    print("-" * 70)
    
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
    
    final = {
        'date': datetime.now().isoformat(),
        'data_source': 'FinanceDataReader' if FDR_AVAILABLE else 'Fallback',
        'total': len(stocks),
        'success': len([r for r in results if r.get('status') == 'success']),
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
    print(f"   Total: {len(stocks)} | Success: {final['success']}")
    print(f"   KOSPI: {final['kospi_count']} | KOSDAQ: {final['kosdaq_count']}")
    print(f"   Output: {output_file}")
    
    # TOP 15
    sorted_results = sorted(
        [r for r in results if r.get('status') == 'success'],
        key=lambda x: x.get('avg_score', 0),
        reverse=True
    )[:15]
    
    print("\n   🏆 TOP 15:")
    for i, r in enumerate(sorted_results, 1):
        print(f"      {i:2d}. {r['name']:<15} ({r['market']}) {r['avg_score']:5.1f} pts - {r['consensus']}")
    
    # 섹터별 평균
    sector_scores = {}
    for r in [r for r in results if r.get('status') == 'success']:
        sector = r.get('sector', 'Unknown')
        if sector not in sector_scores:
            sector_scores[sector] = []
        sector_scores[sector].append(r['avg_score'])
    
    print("\n   📊 Sector Average:")
    for sector, scores in sorted(sector_scores.items(), key=lambda x: sum(x[1])/len(x[1]), reverse=True)[:10]:
        avg = sum(scores) / len(scores)
        print(f"      {sector:<12}: {avg:.1f} pts ({len(scores)} stocks)")
    
    print("=" * 70)
    return final


def main():
    import argparse
    
    parser = argparse.ArgumentParser(description='Full Market Level 1 Analysis with FinanceDataReader')
    parser.add_argument('--kospi', type=int, default=100, help='Number of KOSPI stocks (default: 100)')
    parser.add_argument('--kosdaq', type=int, default=50, help='Number of KOSDAQ stocks (default: 50)')
    
    args = parser.parse_args()
    
    run_full_analysis(args.kospi, args.kosdaq)


if __name__ == '__main__':
    main()
