#!/usr/bin/env python3
"""
KStock Unified Pipeline - 자원 효율화 버전
Level 1 → Level 2 → Level 3 통합 자동화 파이프라인

사용법: python3 kstock_pipeline.py [--mode full|level1|level2|level3]
"""

import asyncio
import json
import os
import sys
import time
import argparse
from datetime import datetime
from concurrent.futures import ProcessPoolExecutor, ThreadPoolExecutor
from typing import Dict, List, Optional, Tuple
import multiprocessing as mp

# 경로 설정
sys.path.insert(0, '/home/programs/kstock_analyzer')
sys.path.insert(0, '/home/programs/kstock_analyzer/agents')

# 에이전트 임포트
from agents.technical_agent import TechnicalAnalysisAgent
from agents.quant_agent import QuantAnalysisAgent
from agents.qualitative_agent import QualitativeAnalysisAgent
from agents.enhanced_news_agent import EnhancedNewsAgent


class ResourceMonitor:
    """자원 모니터링 및 최적화"""
    
    def __init__(self):
        self.start_time = None
        self.memory_usage = []
        
    def start(self):
        self.start_time = time.time()
        
    def elapsed(self) -> float:
        return time.time() - self.start_time if self.start_time else 0
    
    def log_memory(self, label: str):
        try:
            import psutil
            process = psutil.Process()
            mem_mb = process.memory_info().rss / 1024 / 1024
            self.memory_usage.append((label, mem_mb))
            return mem_mb
        except:
            return 0


class UnifiedKStockPipeline:
    """통합 KStock 파이프라인"""
    
    def __init__(self, max_workers: int = None):
        self.max_workers = max_workers or min(mp.cpu_count(), 4)
        self.monitor = ResourceMonitor()
        self.results = {
            'level1': {},
            'level2': {},
            'level3': {},
            'timing': {}
        }
        
    # ============================================================
    # Level 1: 병렬 종목 분석
    # ============================================================
    
    def analyze_single_stock(self, stock: Dict) -> Dict:
        """개별 종목 분석 (멀티프로세싱용)"""
        symbol = stock['symbol']
        name = stock['name']
        
        result = {
            'symbol': symbol,
            'name': name,
            'market': stock.get('market', 'KOSPI'),
            'agents': {},
            'status': 'running'
        }
        
        try:
            # 4개 에이전트 병렬 실행
            agents_start = time.time()
            
            # ThreadPool로 병렬 실행 (I/O 바운드)
            with ThreadPoolExecutor(max_workers=4) as executor:
                futures = {
                    'technical': executor.submit(self._run_technical, symbol, name),
                    'quant': executor.submit(self._run_quant, symbol, name),
                    'qualitative': executor.submit(self._run_qualitative, symbol, name),
                    'news': executor.submit(self._run_news, symbol, name)
                }
                
                for agent_type, future in futures.items():
                    try:
                        result['agents'][agent_type] = future.result(timeout=120)
                    except Exception as e:
                        result['agents'][agent_type] = {'error': str(e), 'score': 0}
            
            # 종합 점수 계산
            scores = []
            weights = {'technical': 0.25, 'quant': 0.25, 'qualitative': 0.25, 'news': 0.25}
            
            for agent_type, weight in weights.items():
                if agent_type in result['agents'] and 'score' in result['agents'][agent_type]:
                    scores.append(result['agents'][agent_type]['score'] * weight)
            
            result['avg_score'] = round(sum(scores), 2) if scores else 0
            result['recommendation'] = self._get_recommendation(result['avg_score'])
            result['status'] = 'success'
            result['timing'] = {'total': round(time.time() - agents_start, 2)}
            
        except Exception as e:
            result['status'] = 'error'
            result['error'] = str(e)
        
        return result
    
    def _run_technical(self, symbol: str, name: str) -> Dict:
        try:
            agent = TechnicalAnalysisAgent(symbol, name)
            result = agent.analyze()
            return {
                'score': result.get('total_score', 0),
                'recommendation': result.get('recommendation', 'HOLD'),
                'signals': result.get('key_signals', [])[:3]
            }
        except Exception as e:
            return {'score': 0, 'error': str(e)}
    
    def _run_quant(self, symbol: str, name: str) -> Dict:
        try:
            agent = QuantAnalysisAgent(symbol, name)
            result = agent.analyze()
            return {
                'score': result.get('total_score', 0),
                'recommendation': result.get('recommendation', 'HOLD'),
                'signals': result.get('key_signals', [])[:3]
            }
        except Exception as e:
            return {'score': 0, 'error': str(e)}
    
    def _run_qualitative(self, symbol: str, name: str) -> Dict:
        try:
            agent = QualitativeAnalysisAgent(symbol, name)
            result = agent.analyze()
            return {
                'score': result.get('total_score', 0),
                'recommendation': result.get('recommendation', 'HOLD'),
                'moat': result.get('moat_rating', 'None'),
                'signals': result.get('key_signals', [])[:3]
            }
        except Exception as e:
            return {'score': 0, 'error': str(e)}
    
    def _run_news(self, symbol: str, name: str) -> Dict:
        try:
            agent = EnhancedNewsAgent(symbol, name)
            result = agent.analyze()
            return {
                'score': result.get('total_score', 0),
                'recommendation': result.get('recommendation', 'HOLD'),
                'sentiment': result.get('sentiment_trend', 'Stable'),
                'signals': result.get('key_signals', [])[:3]
            }
        except Exception as e:
            return {'score': 0, 'error': str(e)}
    
    def _get_recommendation(self, score: float) -> str:
        if score >= 70: return 'BUY'
        elif score >= 50: return 'HOLD'
        else: return 'SELL'
    
    def run_level1(self, stocks: List[Dict]) -> Dict:
        """Level 1: 모든 종목 병렬 분석"""
        print(f"\n{'='*60}")
        print(f"📊 Level 1: Parallel Stock Analysis ({len(stocks)} stocks)")
        print(f"{'='*60}")
        print(f"Workers: {self.max_workers}")
        
        self.monitor.start()
        start_time = time.time()
        
        # ProcessPool로 병렬 실행 (CPU 바운드)
        results = []
        with ProcessPoolExecutor(max_workers=self.max_workers) as executor:
            futures = {executor.submit(self.analyze_single_stock, stock): stock for stock in stocks}
            
            for i, future in enumerate(futures, 1):
                stock = futures[future]
                try:
                    result = future.result(timeout=300)
                    results.append(result)
                    status = '✅' if result['status'] == 'success' else '❌'
                    print(f"   {status} [{i}/{len(stocks)}] {stock['name']}: {result.get('avg_score', 0):.1f}pts")
                except Exception as e:
                    print(f"   ❌ [{i}/{len(stocks)}] {stock['name']}: Error - {e}")
                    results.append({
                        'symbol': stock['symbol'],
                        'name': stock['name'],
                        'status': 'error',
                        'error': str(e)
                    })
        
        # 결과 정렬
        results.sort(key=lambda x: x.get('avg_score', 0), reverse=True)
        
        elapsed = time.time() - start_time
        
        output = {
            'analysis_date': datetime.now().isoformat(),
            'total_stocks': len(stocks),
            'success_count': sum(1 for r in results if r['status'] == 'success'),
            'elapsed_seconds': round(elapsed, 2),
            'results': results
        }
        
        print(f"\n   ⏱️  Total: {elapsed:.1f}s ({elapsed/len(stocks):.1f}s per stock)")
        
        return output
    
    # ============================================================
    # Level 2: 섹터 & 거시 분석
    # ============================================================
    
    def run_level2(self, level1_results: Dict) -> Dict:
        """Level 2: 섹터 및 거시 분석"""
        print(f"\n{'='*60}")
        print("🌍 Level 2: Sector & Macro Analysis")
        print(f"{'='*60}")
        
        start_time = time.time()
        
        # 섹터 분석
        sector_data = self._analyze_sectors(level1_results['results'])
        
        # 거시 분석 (간소화)
        macro_data = self._analyze_macro()
        
        elapsed = time.time() - start_time
        
        print(f"   ⏱️  Total: {elapsed:.1f}s")
        
        return {
            'analysis_date': datetime.now().isoformat(),
            'sectors': sector_data,
            'macro': macro_data,
            'elapsed_seconds': round(elapsed, 2)
        }
    
    def _analyze_sectors(self, results: List[Dict]) -> Dict:
        """섹터별 집계"""
        sectors = {}
        
        for r in results:
            if r['status'] != 'success':
                continue
            
            # 섹터 추정 (간단한 매핑)
            sector_map = {
                '삼성전자': '반도체', 'SK하이닉스': '반도체',
                '현대차': '자동차', '기아': '자동차',
                'NAVER': '플랫폼', '카카오': '플랫폼',
                'LG화학': '화학', 'POSCO': '철강',
                '에코프로': '2차전지', '에코프로비엠': '2차전지',
                '알테오젠': '바이오'
            }
            
            sector = sector_map.get(r['name'], '기타')
            
            if sector not in sectors:
                sectors[sector] = {'stocks': [], 'total_score': 0}
            
            sectors[sector]['stocks'].append(r)
            sectors[sector]['total_score'] += r['avg_score']
        
        # 평균 계산
        for sector, data in sectors.items():
            data['avg_score'] = round(data['total_score'] / len(data['stocks']), 2) if data['stocks'] else 0
            data['strength'] = 'STRONG' if data['avg_score'] >= 60 else 'MODERATE' if data['avg_score'] >= 40 else 'WEAK'
        
        return sectors
    
    def _analyze_macro(self) -> Dict:
        """거시 분석 (캐시된 데이터 활용)"""
        return {
            'usd_krw': 1484.78,
            'vix': 24.24,
            'us_treasury': 4.15,
            'kospi_trend': 'Sideways',
            'adjustment': -10,
            'market_condition': 'BEARISH'
        }
    
    # ============================================================
    # Level 3: 포트폴리오 구성
    # ============================================================
    
    def run_level3(self, level1_results: Dict, level2_results: Dict) -> Dict:
        """Level 3: 포트폴리오 구성"""
        print(f"\n{'='*60}")
        print("🎯 Level 3: Portfolio Construction")
        print(f"{'='*60}")
        
        start_time = time.time()
        
        # 매크로 조정
        macro_adj = level2_results['macro']['adjustment']
        
        # 종목별 최종 점수 계산
        rankings = []
        for r in level1_results['results']:
            if r['status'] != 'success':
                continue
            
            final_score = r['avg_score'] + macro_adj
            rankings.append({
                'symbol': r['symbol'],
                'name': r['name'],
                'level1_score': r['avg_score'],
                'macro_adj': macro_adj,
                'final_score': final_score,
                'market': r['market']
            })
        
        rankings.sort(key=lambda x: x['final_score'], reverse=True)
        
        # 포트폴리오 구성
        long_positions = []
        short_positions = []
        
        for r in rankings:
            if r['final_score'] >= 70:
                long_positions.append({**r, 'position_pct': 7})
            elif r['final_score'] < 40:
                short_positions.append(r)
        
        total_long = sum(p['position_pct'] for p in long_positions)
        cash_pct = 100 - total_long
        
        elapsed = time.time() - start_time
        
        print(f"   📈 Long: {len(long_positions)} positions ({total_long}%)")
        print(f"   📉 Short: {len(short_positions)} positions")
        print(f"   💰 Cash: {cash_pct}%")
        print(f"   ⏱️  Total: {elapsed:.1f}s")
        
        return {
            'analysis_date': datetime.now().isoformat(),
            'portfolio': {
                'long': long_positions,
                'short': short_positions
            },
            'portfolio_summary': {
                'long_pct': total_long,
                'short_pct': 0,
                'cash_pct': cash_pct
            },
            'all_rankings': rankings,
            'elapsed_seconds': round(elapsed, 2)
        }
    
    # ============================================================
    # 통합 실행
    # ============================================================
    
    def run_full_pipeline(self, stocks: List[Dict]) -> Dict:
        """전체 파이프라인 실행"""
        total_start = time.time()
        
        print(f"\n{'='*70}")
        print(f"🚀 KStock Unified Pipeline - {datetime.now().strftime('%Y-%m-%d %H:%M')}")
        print(f"{'='*70}")
        print(f"Workers: {self.max_workers} | CPU: {mp.cpu_count()} cores")
        
        # Level 1
        self.results['level1'] = self.run_level1(stocks)
        
        # Level 2
        self.results['level2'] = self.run_level2(self.results['level1'])
        
        # Level 3
        self.results['level3'] = self.run_level3(
            self.results['level1'],
            self.results['level2']
        )
        
        total_elapsed = time.time() - total_start
        
        print(f"\n{'='*70}")
        print(f"✅ Pipeline Complete - Total: {total_elapsed:.1f}s")
        print(f"{'='*70}")
        
        return self.results
    
    def save_results(self, output_dir: str = '/home/programs/kstock_analyzer/data'):
        """결과 저장"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M")
        
        # Level 1
        l1_file = f'{output_dir}/level1_daily/level1_fullmarket_{timestamp}.json'
        os.makedirs(os.path.dirname(l1_file), exist_ok=True)
        with open(l1_file, 'w', encoding='utf-8') as f:
            json.dump(self.results['level1'], f, indent=2, ensure_ascii=False)
        
        # Level 2
        l2_sector = f'{output_dir}/level2_daily/sector_analysis_{timestamp}.json'
        l2_macro = f'{output_dir}/level2_daily/macro_analysis_{timestamp}.json'
        os.makedirs(os.path.dirname(l2_sector), exist_ok=True)
        with open(l2_sector, 'w', encoding='utf-8') as f:
            json.dump(self.results['level2']['sectors'], f, indent=2, ensure_ascii=False)
        with open(l2_macro, 'w', encoding='utf-8') as f:
            json.dump(self.results['level2']['macro'], f, indent=2, ensure_ascii=False)
        
        # Level 3
        l3_file = f'{output_dir}/level3_daily/portfolio_report_{timestamp}.json'
        os.makedirs(os.path.dirname(l3_file), exist_ok=True)
        with open(l3_file, 'w', encoding='utf-8') as f:
            json.dump(self.results['level3'], f, indent=2, ensure_ascii=False)
        
        print(f"\n💾 Results saved:")
        print(f"   • Level 1: {l1_file}")
        print(f"   • Level 2: {l2_sector}")
        print(f"   • Level 3: {l3_file}")


def main():
    parser = argparse.ArgumentParser(description='KStock Unified Pipeline')
    parser.add_argument('--mode', choices=['full', 'level1', 'level2', 'level3'], default='full')
    parser.add_argument('--workers', type=int, default=None)
    args = parser.parse_args()
    
    # 테스트 종목
    stocks = [
        {'symbol': '005930.KS', 'name': '삼성전자', 'market': 'KOSPI'},
        {'symbol': '000660.KS', 'name': 'SK하이닉스', 'market': 'KOSPI'},
        {'symbol': '035420.KS', 'name': 'NAVER', 'market': 'KOSPI'},
        {'symbol': '005380.KS', 'name': '현대차', 'market': 'KOSPI'},
        {'symbol': '051910.KS', 'name': 'LG화학', 'market': 'KOSPI'},
        {'symbol': '247540.KS', 'name': '에코프로비엠', 'market': 'KOSDAQ'},
        {'symbol': '086520.KS', 'name': '에코프로', 'market': 'KOSDAQ'},
        {'symbol': '196170.KS', 'name': '알테오젠', 'market': 'KOSDAQ'}
    ]
    
    pipeline = UnifiedKStockPipeline(max_workers=args.workers)
    
    if args.mode == 'full':
        results = pipeline.run_full_pipeline(stocks)
        pipeline.save_results()
        
        # 요약 출력
        print(f"\n📊 Final Portfolio:")
        print(f"   Long: {len(results['level3']['portfolio']['long'])} stocks")
        print(f"   Cash: {results['level3']['portfolio_summary']['cash_pct']:.0f}%")
    
    elif args.mode == 'level1':
        result = pipeline.run_level1(stocks)
        print(f"\nTop 3: {[r['name'] for r in result['results'][:3]]}")
    
    print("\n✅ Done!")


if __name__ == '__main__':
    main()
