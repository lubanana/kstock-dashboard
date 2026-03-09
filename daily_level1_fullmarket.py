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
        """섹터 매핑 로드 (확대版)"""
        return {
            # 반도체
            '005930': '반도체', '000660': '반도체', '042700': '반도체', '000990': '반도체',
            # 플랫폼/IT
            '035420': '플랫폼', '035720': '플랫폼', '018260': 'IT서비스', '122900': '플랫폼',
            # 자동차
            '005380': '자동차', '000270': '자동차', '005387': '자동차',
            # 화학
            '051910': '화학',
            # 금융
            '055550': '금융', '105560': '금융', '086790': '금융', '138040': '금융', '024110': '금융', '032830': '보험', '000810': '보험',
            # 통신
            '017670': '통신', '030200': '통신', '032640': '통신',
            # 에너지/유틸리티
            '015760': '전력', '096770': '에너지', '010950': '정유',
            # 철강/조선
            '005490': '철강', '009540': '조선', '042660': '철강', '010130': '비철금속',
            # 소비재/유통
            '028260': '무역', '051900': '생활용품', '033780': '담/유통',
            # 전자
            '066570': '전자', '009150': '전자부품', '011070': '전자부품',
            # 바이오/제약
            '068270': '바이오', '207940': '바이오', '128940': '제약', '302440': '제약',
            # 방산
            '012450': '방산',
            # 해운
            '011200': '해운',
            # 지주사
            '034730': '지주사', '003550': '지주사', '003600': '지주사',
            # KOSDAQ - 2차전지
            '247540': '2차전지', '086520': '2차전지', '278280': '2차전지', '123860': '2차전지', '140910': '2차전지',
            # KOSDAQ - 바이오
            '196170': '바이오', '036830': '바이오', '068760': '바이오', '028300': '바이오', '145020': '바이오', '293490': '바이오',
            # KOSDAQ - 엔터/게임
            '352820': '엔터', '259960': '게임', '207940': '바이오', '041140': '게임', '263750': '게임', '095660': '게임', '194480': '게임',
            # KOSDAQ - 반도체
            '357780': '반도체', '222800': '반도체', '240810': '반도체',
            # KOSDAQ - 화장품
            '214150': '화장품',
        }
    
    def get_kospi_stocks(self, limit: int = None) -> List[Dict]:
        """KOSPI 종목 JSON 파일에서 로드"""
        json_file = '/home/programs/kstock_analyzer/data/kospi_stocks.json'
        
        try:
            with open(json_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                stocks = data.get('stocks', [])
                
            # 섹터 매핑 추가
            for stock in stocks:
                stock['sector'] = self.sector_mapping.get(stock['code'], '기타')
            
            if limit:
                stocks = stocks[:limit]
            
            print(f"📊 Loaded {len(stocks)} KOSPI stocks from {json_file}")
            return stocks
            
        except Exception as e:
            print(f"   ❌ Error loading KOSPI: {e}")
            return self._get_fallback_kospi(limit or 40)
    
    def get_kosdaq_stocks(self, limit: int = None) -> List[Dict]:
        """KOSDAQ 종목 JSON 파일에서 로드"""
        json_file = '/home/programs/kstock_analyzer/data/kosdaq_stocks.json'
        
        try:
            with open(json_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                stocks = data.get('stocks', [])
                
            # 섹터 매핑 추가
            for stock in stocks:
                stock['sector'] = self.sector_mapping.get(stock['code'], '기타')
            
            if limit:
                stocks = stocks[:limit]
            
            print(f"📊 Loaded {len(stocks)} KOSDAQ stocks from {json_file}")
            return stocks
            
        except Exception as e:
            print(f"   ❌ Error loading KOSDAQ: {e}")
            return self._get_fallback_kosdaq(limit or 20)
            
        except Exception as e:
            print(f"   ❌ Error fetching KOSDAQ: {e}")
            return self._get_fallback_kosdaq(limit)
    
    def get_all_stocks(self, kospi_limit: int = 100, kosdaq_limit: int = 50) -> List[Dict]:
        """전체 종목 조회"""
        kospi = self.get_kospi_stocks(kospi_limit)
        kosdaq = self.get_kosdaq_stocks(kosdaq_limit)
        return kospi + kosdaq
    
    def _get_fallback_kospi(self, limit: int) -> List[Dict]:
        """KOSPI 폴리백 리스트 (확대版)"""
        fallback = [
            # 반도체
            {'symbol': '005930.KS', 'name': '삼성전자', 'market': 'KOSPI', 'sector': '반도체'},
            {'symbol': '000660.KS', 'name': 'SK하이닉스', 'market': 'KOSPI', 'sector': '반도체'},
            {'symbol': '005930.KS', 'name': '삼성전자우', 'market': 'KOSPI', 'sector': '반도체'},
            # 플랫폼/IT
            {'symbol': '035420.KS', 'name': 'NAVER', 'market': 'KOSPI', 'sector': '플랫폼'},
            {'symbol': '035720.KS', 'name': '카카오', 'market': 'KOSPI', 'sector': '플랫폼'},
            {'symbol': '018260.KS', 'name': '삼성에스디에스', 'market': 'KOSPI', 'sector': 'IT서비스'},
            # 자동차
            {'symbol': '005380.KS', 'name': '현대차', 'market': 'KOSPI', 'sector': '자동차'},
            {'symbol': '000270.KS', 'name': '기아', 'market': 'KOSPI', 'sector': '자동차'},
            {'symbol': '005387.KS', 'name': '현대차2우B', 'market': 'KOSPI', 'sector': '자동차'},
            # 화학
            {'symbol': '051910.KS', 'name': 'LG화학', 'market': 'KOSPI', 'sector': '화학'},
            {'symbol': '051910.KS', 'name': 'LG화학우', 'market': 'KOSPI', 'sector': '화학'},
            # 금융
            {'symbol': '055550.KS', 'name': '신한지주', 'market': 'KOSPI', 'sector': '금융'},
            {'symbol': '105560.KS', 'name': 'KB금융', 'market': 'KOSPI', 'sector': '금융'},
            {'symbol': '086790.KS', 'name': '하나금융지주', 'market': 'KOSPI', 'sector': '금융'},
            {'symbol': '138040.KS', 'name': '메리츠금융지주', 'market': 'KOSPI', 'sector': '금융'},
            {'symbol': '024110.KS', 'name': '기업은행', 'market': 'KOSPI', 'sector': '금융'},
            # 통신
            {'symbol': '017670.KS', 'name': 'SK텔레콤', 'market': 'KOSPI', 'sector': '통신'},
            {'symbol': '030200.KS', 'name': 'KT', 'market': 'KOSPI', 'sector': '통신'},
            # 에너지/유틸리티
            {'symbol': '015760.KS', 'name': '한국전력', 'market': 'KOSPI', 'sector': '전력'},
            {'symbol': '096770.KS', 'name': 'SK이노베이션', 'market': 'KOSPI', 'sector': '에너지'},
            {'symbol': '010950.KS', 'name': 'S-Oil', 'market': 'KOSPI', 'sector': '정유'},
            # 철강/조선
            {'symbol': '005490.KS', 'name': 'POSCO홀딩스', 'market': 'KOSPI', 'sector': '철강'},
            {'symbol': '009540.KS', 'name': '현대중공업', 'market': 'KOSPI', 'sector': '조선'},
            {'symbol': '042660.KS', 'name': '현대제철', 'market': 'KOSPI', 'sector': '철강'},
            # 소비재
            {'symbol': '028260.KS', 'name': '삼성물산', 'market': 'KOSPI', 'sector': '무역'},
            {'symbol': '051900.KS', 'name': 'LG생활건강', 'market': 'KOSPI', 'sector': '생활용품'},
            {'symbol': '033780.KS', 'name': 'KT&G', 'market': 'KOSPI', 'sector': '담/유통'},
            # 반도체 장비/소재
            {'symbol': '042700.KS', 'name': '한미반도체', 'market': 'KOSPI', 'sector': '반도체'},
            {'symbol': '000990.KS', 'name': 'DB하이텍', 'market': 'KOSPI', 'sector': '반도체'},
            # 전자
            {'symbol': '066570.KS', 'name': 'LG전자', 'market': 'KOSPI', 'sector': '전자'},
            {'symbol': '009150.KS', 'name': '삼성전기', 'market': 'KOSPI', 'sector': '전자부품'},
            {'symbol': '011070.KS', 'name': 'LG이노텍', 'market': 'KOSPI', 'sector': '전자부품'},
            # 바이오/제약
            {'symbol': '068270.KS', 'name': '셀트리온', 'market': 'KOSPI', 'sector': '바이오'},
            {'symbol': '207940.KS', 'name': '삼성바이오로직스', 'market': 'KOSPI', 'sector': '바이오'},
            # 방산
            {'symbol': '012450.KS', 'name': '한화에어로스페이스', 'market': 'KOSPI', 'sector': '방산'},
            # 해운
            {'symbol': '011200.KS', 'name': 'HMM', 'market': 'KOSPI', 'sector': '해운'},
        ]
        return fallback[:limit]
    
    def _get_fallback_kosdaq(self, limit: int) -> List[Dict]:
        """KOSDAQ 폴리백 리스트 (확대版)"""
        fallback = [
            # 2차전지
            {'symbol': '247540.KS', 'name': '에코프로비엠', 'market': 'KOSDAQ', 'sector': '2차전지'},
            {'symbol': '086520.KS', 'name': '에코프로', 'market': 'KOSDAQ', 'sector': '2차전지'},
            {'symbol': '123860.KS', 'name': '아이티엠반도체', 'market': 'KOSDAQ', 'sector': '2차전지'},
            {'symbol': '140910.KS', 'name': '에스에너지', 'market': 'KOSDAQ', 'sector': '2차전지'},
            {'symbol': '194480.KS', 'name': '데브시스터즈', 'market': 'KOSDAQ', 'sector': '게임'},
            # 바이오
            {'symbol': '196170.KS', 'name': '알테오젠', 'market': 'KOSDAQ', 'sector': '바이오'},
            {'symbol': '278280.KS', 'name': '천보', 'market': 'KOSDAQ', 'sector': '2차전지'},
            {'symbol': '145020.KS', 'name': '휴젤', 'market': 'KOSDAQ', 'sector': '바이오'},
            {'symbol': '036830.KS', 'name': '셀트리온제약', 'market': 'KOSDAQ', 'sector': '바이오'},
            {'symbol': '068760.KS', 'name': '셀트리온헬스케어', 'market': 'KOSDAQ', 'sector': '바이오'},
            {'symbol': '028300.KS', 'name': 'HLB', 'market': 'KOSDAQ', 'sector': '바이오'},
            {'symbol': '122900.KS', 'name': '아이마켓코리아', 'market': 'KOSDAQ', 'sector': '플랫폼'},
            # 엔터/게임
            {'symbol': '352820.KS', 'name': '하이브', 'market': 'KOSDAQ', 'sector': '엔터'},
            {'symbol': '259960.KS', 'name': '크래프톤', 'market': 'KOSDAQ', 'sector': '게임'},
            {'symbol': '041140.KS', 'name': '네오위즈', 'market': 'KOSDAQ', 'sector': '게임'},
            {'symbol': '263750.KS', 'name': '펄어비스', 'market': 'KOSDAQ', 'sector': '게임'},
            {'symbol': '095660.KS', 'name': '네오위즈홀딩스', 'market': 'KOSDAQ', 'sector': '게임'},
            # 반도체
            {'symbol': '357780.KS', 'name': '솔브레인홀딩스', 'market': 'KOSDAQ', 'sector': '반도체'},
            {'symbol': '222800.KS', 'name': '심텍', 'market': 'KOSDAQ', 'sector': '반도체'},
            {'symbol': '240810.KS', 'name': '원익IPS', 'market': 'KOSDAQ', 'sector': '반도체'},
            # 화장품
            {'symbol': '214150.KS', 'name': '클리오', 'market': 'KOSDAQ', 'sector': '화장품'},
            {'symbol': '293490.KS', 'name': '에이치엘비생명과학', 'market': 'KOSDAQ', 'sector': '바이오'},
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
    print(f"   Data Source: KOSPI/KOSDAQ Master Files")
    print(f"   Time: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print("=" * 70)
    
    # 종목 선택 (기본값: KOSPI 50개, KOSDAQ 30개)
    kospi_stocks = reader.get_kospi_stocks(kospi_count)
    kosdaq_stocks = reader.get_kosdaq_stocks(kosdaq_count)
    
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
