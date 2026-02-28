#!/usr/bin/env python3
"""
KStock Market Data Reader with FinanceDataReader
FinanceDataReader를 활용한 KOSPI/KOSDAQ 전체 종목 조회 및 Level 1 분석
"""

import json
import os
import sys
from datetime import datetime
from typing import List, Dict, Optional
import time

# FinanceDataReader 임포트
try:
    import FinanceDataReader as fdr
    FDR_AVAILABLE = True
except ImportError:
    print("Warning: FinanceDataReader not available. Using fallback list.")
    FDR_AVAILABLE = False

sys.path.insert(0, '/home/programs/kstock_analyzer/agents')

from technical_agent import TechnicalAnalysisAgent
from quant_agent import QuantAnalysisAgent
from qualitative_agent import QualitativeAnalysisAgent
from news_agent import NewsSentimentAgent

BASE_PATH = '/home/programs/kstock_analyzer'
OUTPUT_PATH = f'{BASE_PATH}/data/level1_daily'


class MarketDataReader:
    """시장 데이터 리더"""
    
    def __init__(self):
        self.stocks = []
        self.fdr_available = FDR_AVAILABLE
    
    def get_kospi_stocks(self, limit: int = 100) -> List[Dict]:
        """KOSPI 전체 종목 조회"""
        if not self.fdr_available:
            return self._get_fallback_kospi(limit)
        
        try:
            print("📊 Fetching KOSPI stock list from FinanceDataReader...")
            kospi = fdr.StockListing('KOSPI')
            
            stocks = []
            for _, row in kospi.head(limit).iterrows():
                symbol = row.get('Code', '')
                name = row.get('Name', '')
                if symbol and name:
                    stocks.append({
                        'symbol': f"{symbol}.KS",
                        'name': name,
                        'market': 'KOSPI',
                        'sector': row.get('Sector', 'Unknown')
                    })
            
            print(f"   ✅ Loaded {len(stocks)} KOSPI stocks")
            return stocks
            
        except Exception as e:
            print(f"   ❌ Error fetching KOSPI: {e}")
            return self._get_fallback_kospi(limit)
    
    def get_kosdaq_stocks(self, limit: int = 100) -> List[Dict]:
        """KOSDAQ 전체 종목 조회"""
        if not self.fdr_available:
            return self._get_fallback_kosdaq(limit)
        
        try:
            print("📊 Fetching KOSDAQ stock list from FinanceDataReader...")
            kosdaq = fdr.StockListing('KOSDAQ')
            
            stocks = []
            for _, row in kosdaq.head(limit).iterrows():
                symbol = row.get('Code', '')
                name = row.get('Name', '')
                if symbol and name:
                    stocks.append({
                        'symbol': f"{symbol}.KQ",
                        'name': name,
                        'market': 'KOSDAQ',
                        'sector': row.get('Sector', 'Unknown')
                    })
            
            print(f"   ✅ Loaded {len(stocks)} KOSDAQ stocks")
            return stocks
            
        except Exception as e:
            print(f"   ❌ Error fetching KOSDAQ: {e}")
            return self._get_fallback_kosdaq(limit)
    
    def _get_fallback_kospi(self, limit: int) -> List[Dict]:
        """KOSPI 폴리백 리스트"""
        fallback = [
            {'symbol': '005930.KS', 'name': '삼성전자', 'market': 'KOSPI'},
            {'symbol': '000660.KS', 'name': 'SK하이닉스', 'market': 'KOSPI'},
            {'symbol': '035420.KS', 'name': 'NAVER', 'market': 'KOSPI'},
            {'symbol': '005380.KS', 'name': '현대차', 'market': 'KOSPI'},
            {'symbol': '051910.KS', 'name': 'LG화학', 'market': 'KOSPI'},
            {'symbol': '035720.KS', 'name': '카카오', 'market': 'KOSPI'},
            {'symbol': '006400.KS', 'name': '삼성SDI', 'market': 'KOSPI'},
            {'symbol': '068270.KS', 'name': '셀트리온', 'market': 'KOSPI'},
            {'symbol': '005490.KS', 'name': 'POSCO홀딩스', 'market': 'KOSPI'},
            {'symbol': '028260.KS', 'name': '삼성물산', 'market': 'KOSPI'},
        ]
        return fallback[:limit]
    
    def _get_fallback_kosdaq(self, limit: int) -> List[Dict]:
        """KOSDAQ 폴리백 리스트"""
        fallback = [
            {'symbol': '247540.KS', 'name': '에코프로비엠', 'market': 'KOSDAQ'},
            {'symbol': '086520.KS', 'name': '에코프로', 'market': 'KOSDAQ'},
            {'symbol': '196170.KS', 'name': '알테오젠', 'market': 'KOSDAQ'},
            {'symbol': '352820.KS', 'name': '하이브', 'market': 'KOSDAQ'},
            {'symbol': '259960.KS', 'name': '크래프톤', 'market': 'KOSDAQ'},
        ]
        return fallback[:limit]
    
    def get_all_stocks(self, kospi_limit: int = 100, kosdaq_limit: int = 100) -> List[Dict]:
        """전체 종목 조회"""
        kospi = self.get_kospi_stocks(kospi_limit)
        kosdaq = self.get_kosdaq_stocks(kosdaq_limit)
        return kospi + kosdaq


class Level1BatchRunnerFDR:
    """FinanceDataReader 기반 Level 1 배치 실행기"""
    
    def __init__(self):
        self.reader = MarketDataReader()
        self.results = []
        os.makedirs(OUTPUT_PATH, exist_ok=True)
    
    def analyze_stock(self, stock: Dict) -> Dict:
        """단일 종목 Level 1 전체 분석"""
        symbol = stock['symbol']
        name = stock['name']
        market = stock.get('market', 'UNKNOWN')
        
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
            result['agents']['TECH'] = {
                'score': r.get('total_score', 0),
                'rec': r.get('recommendation', 'HOLD')
            }
            print(f"{r.get('total_score', 0)} pts")
            
            # 2. Quant
            print("   📊 QUANT...", end=' ', flush=True)
            quant = QuantAnalysisAgent(symbol, name)
            r = quant.analyze()
            result['agents']['QUANT'] = {
                'score': r.get('total_score', 0),
                'rec': r.get('recommendation', 'HOLD')
            }
            print(f"{r.get('total_score', 0)} pts")
            
            # 3. Qualitative
            print("   🏢 QUAL...", end=' ', flush=True)
            qual = QualitativeAnalysisAgent(symbol, name)
            r = qual.analyze()
            result['agents']['QUAL'] = {
                'score': r.get('total_score', 0),
                'rec': r.get('recommendation', 'HOLD')
            }
            print(f"{r.get('total_score', 0)} pts")
            
            # 4. News
            print("   📰 NEWS...", end=' ', flush=True)
            news = NewsSentimentAgent(symbol, name)
            r = news.analyze()
            result['agents']['NEWS'] = {
                'score': r.get('total_score', 0),
                'rec': r.get('recommendation', 'HOLD')
            }
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
    
    def run_batch(self, kospi_limit: int = 50, kosdaq_limit: int = 30):
        """배치 실행"""
        print("=" * 70)
        print("🚀 LEVEL 1 BATCH WITH FinanceDataReader")
        print(f"   Time: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
        print("=" * 70)
        
        # 종목 조회
        stocks = self.reader.get_all_stocks(kospi_limit, kosdaq_limit)
        
        print(f"\n📋 Total stocks to analyze: {len(stocks)}")
        print("-" * 70)
        
        # 분석 실행
        results = []
        for i, stock in enumerate(stocks, 1):
            print(f"\n[{i}/{len(stocks)}]", end=' ')
            result = self.analyze_stock(stock)
            results.append(result)
            time.sleep(0.5)
        
        # 결과 저장
        date_str = datetime.now().strftime('%Y%m%d_%H%M')
        output_file = f"{OUTPUT_PATH}/level1_fdr_{date_str}.json"
        
        final = {
            'date': datetime.now().isoformat(),
            'fdr_available': FDR_AVAILABLE,
            'total': len(stocks),
            'success': len([r for r in results if r.get('status') == 'success']),
            'kospi_count': len([r for r in results if r.get('market') == 'KOSPI']),
            'kosdaq_count': len([r for r in results if r.get('market') == 'KOSDAQ']),
            'results': results
        }
        
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(final, f, indent=2, ensure_ascii=False)
        
        # 요약
        print("\n" + "=" * 70)
        print("📊 BATCH COMPLETE")
        print("=" * 70)
        print(f"   Total: {len(stocks)} | Success: {final['success']}")
        print(f"   KOSPI: {final['kospi_count']} | KOSDAQ: {final['kosdaq_count']}")
        print(f"   Output: {output_file}")
        
        # TOP 10
        sorted_results = sorted(
            [r for r in results if r.get('status') == 'success'],
            key=lambda x: x.get('avg_score', 0),
            reverse=True
        )[:10]
        
        print("\n   🏆 TOP 10:")
        for i, r in enumerate(sorted_results, 1):
            print(f"      {i}. {r['name']} ({r['market']}): {r['avg_score']} pts - {r['consensus']}")
        
        print("=" * 70)
        return final


def main():
    import argparse
    
    parser = argparse.ArgumentParser(description='Level 1 Batch with FinanceDataReader')
    parser.add_argument('--kospi', type=int, default=50, help='Number of KOSPI stocks')
    parser.add_argument('--kosdaq', type=int, default=30, help='Number of KOSDAQ stocks')
    
    args = parser.parse_args()
    
    runner = Level1BatchRunnerFDR()
    runner.run_batch(args.kospi, args.kosdaq)


if __name__ == '__main__':
    main()
