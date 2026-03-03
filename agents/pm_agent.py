#!/usr/bin/env python3
"""
Portfolio Manager Agent (PM_001) - Level 3
포트폴리오 매니저 에이전트 - 최종 투자 결정 및 포트폴리오 구성

Features:
- 보수적 점수 커트라인 (Long: 75+, Short: 35-)
- Level 1/2 에이전트 자동 호출
- 최종 포트폴리오 리포트 생성
"""

import json
import os
import sys
import subprocess
from datetime import datetime
from typing import Dict, List, Tuple, Optional
from collections import defaultdict

BASE_PATH = '/home/programs/kstock_analyzer'
AGENTS_PATH = f'{BASE_PATH}/agents'
DATA_PATH = f'{BASE_PATH}/data'
OUTPUT_PATH = f'{BASE_PATH}/docs'

# 보수적 점수 커트라인 (완화)
SCORE_THRESHOLDS = {
    'STRONG_BUY': 75,    # 강력 매수
    'BUY': 70,           # 매수
    'HOLD': 50,          # 중립
    'SELL': 40,          # 매도
    'STRONG_SELL': 35    # 강력 매도
}

# 포지션 사이징 규칙
POSITION_SIZING = {
    'STRONG_BUY': 0.10,   # 10%
    'BUY': 0.07,          # 7%
    'HOLD': 0.03,         # 3%
    'SELL': 0.00,         # 0%
    'STRONG_SELL': 0.00   # 0%
}


class PortfolioManagerAgent:
    """포트폴리오 매니저 에이전트"""
    
    def __init__(self):
        self.level1_data = None
        self.level2_sector = None
        self.level2_macro = None
        self.portfolio = {
            'long': [],
            'short': [],
            'neutral': []
        }
        self.analysis_results = []
    
    def run_level1_agents(self) -> bool:
        """Level 1 에이전트 실행"""
        print("\n" + "=" * 70)
        print("🚀 Running Level 1 Agents...")
        print("=" * 70)
        
        try:
            result = subprocess.run(
                ['python3', f'{BASE_PATH}/daily_level1_fullmarket.py'],
                cwd=BASE_PATH,
                capture_output=True,
                text=True,
                timeout=3600
            )
            
            print(result.stdout)
            if result.returncode != 0:
                print(f"❌ Level 1 Error: {result.stderr}")
                return False
            
            print("✅ Level 1 Agents completed")
            return True
            
        except subprocess.TimeoutExpired:
            print("❌ Level 1 Timeout")
            return False
        except Exception as e:
            print(f"❌ Level 1 Error: {e}")
            return False
    
    def run_level2_agents(self) -> bool:
        """Level 2 에이전트 실행"""
        print("\n" + "=" * 70)
        print("🌍 Running Level 2 Agents...")
        print("=" * 70)
        
        try:
            # Sector Analysis
            print("\n📊 Running Sector Analysis...")
            result1 = subprocess.run(
                ['python3', f'{AGENTS_PATH}/sector_agent.py'],
                cwd=BASE_PATH,
                capture_output=True,
                text=True,
                timeout=300
            )
            print(result1.stdout)
            
            # Macro Analysis
            print("\n🌍 Running Macro Analysis...")
            result2 = subprocess.run(
                ['python3', f'{AGENTS_PATH}/macro_agent.py'],
                cwd=BASE_PATH,
                capture_output=True,
                text=True,
                timeout=300
            )
            print(result2.stdout)
            
            if result1.returncode != 0 or result2.returncode != 0:
                print("❌ Level 2 Error")
                return False
            
            print("✅ Level 2 Agents completed")
            return True
            
        except subprocess.TimeoutExpired:
            print("❌ Level 2 Timeout")
            return False
        except Exception as e:
            print(f"❌ Level 2 Error: {e}")
            return False
    
    def load_all_data(self) -> bool:
        """모든 Level 1/2 데이터 로드"""
        print("\n" + "=" * 70)
        print("📂 Loading Level 1 & 2 Data...")
        print("=" * 70)
        
        # Level 1 데이터
        level1_files = [f for f in os.listdir(f'{DATA_PATH}/level1_daily') 
                       if f.startswith('level1_fullmarket_') and f.endswith('.json')]
        if level1_files:
            latest = sorted(level1_files)[-1]
            with open(f'{DATA_PATH}/level1_daily/{latest}', 'r', encoding='utf-8') as f:
                self.level1_data = json.load(f)
            print(f"✅ Level 1 loaded: {latest}")
        else:
            print("❌ No Level 1 data found")
            return False
        
        # Level 2 Sector 데이터
        sector_files = [f for f in os.listdir(f'{DATA_PATH}/level2_daily')
                       if f.startswith('sector_analysis_') and f.endswith('.json')]
        if sector_files:
            latest = sorted(sector_files)[-1]
            with open(f'{DATA_PATH}/level2_daily/{latest}', 'r', encoding='utf-8') as f:
                self.level2_sector = json.load(f)
            print(f"✅ Level 2 Sector loaded: {latest}")
        else:
            print("❌ No Level 2 Sector data found")
            return False
        
        # Level 2 Macro 데이터
        macro_files = [f for f in os.listdir(f'{DATA_PATH}/level2_daily')
                      if f.startswith('macro_analysis_') and f.endswith('.json')]
        if macro_files:
            latest = sorted(macro_files)[-1]
            with open(f'{DATA_PATH}/level2_daily/{latest}', 'r', encoding='utf-8') as f:
                self.level2_macro = json.load(f)
            print(f"✅ Level 2 Macro loaded: {latest}")
        else:
            print("❌ No Level 2 Macro data found")
            return False
        
        return True
    
    def calculate_final_score(self, stock: Dict) -> Tuple[float, str, Dict]:
        """
        최종 점수 계산
        Level 1 (50%) + Level 2 Sector (30%) + Level 2 Macro (20%)
        """
        symbol = stock['symbol']
        name = stock['name']
        sector = stock.get('sector', 'Unknown')
        
        # Level 1 점수
        level1_score = stock.get('avg_score', 0)
        
        # Level 2 Sector 조정
        sector_adj = 0
        sector_reason = ""
        if self.level2_sector and 'adjustments' in self.level2_sector:
            adj = self.level2_sector['adjustments'].get(sector, {})
            sector_adj = adj.get('adjustment_pct', 0)
            sector_reason = adj.get('reason', '')
        
        # Level 2 Macro 조정
        macro_adj = 0
        macro_reason = ""
        if self.level2_macro and 'adjustment' in self.level2_macro:
            macro_adj = self.level2_macro['adjustment'].get('pct', 0)
            macro_reason = self.level2_macro['adjustment'].get('reason', '')
        
        # 가중 평균 계산
        # L1: 50%, L2 Sector: 30%, L2 Macro: 20%
        base_score = level1_score
        sector_adjusted = base_score * (1 + sector_adj / 100)
        macro_adjusted = base_score * (1 + macro_adj / 100)
        
        final_score = (base_score * 0.5) + (sector_adjusted * 0.3) + (macro_adjusted * 0.2)
        
        breakdown = {
            'level1_score': level1_score,
            'level1_weight': 0.5,
            'sector_adjustment': sector_adj,
            'sector_weight': 0.3,
            'macro_adjustment': macro_adj,
            'macro_weight': 0.2,
            'sector_reason': sector_reason,
            'macro_reason': macro_reason
        }
        
        return round(final_score, 1), self._get_rating(final_score), breakdown
    
    def _get_rating(self, score: float) -> str:
        """점수 기반 등급 산정"""
        if score >= SCORE_THRESHOLDS['STRONG_BUY']:
            return 'STRONG_BUY'
        elif score >= SCORE_THRESHOLDS['BUY']:
            return 'BUY'
        elif score >= SCORE_THRESHOLDS['HOLD']:
            return 'HOLD'
        elif score >= SCORE_THRESHOLDS['SELL']:
            return 'SELL'
        else:
            return 'STRONG_SELL'
    
    def _get_position_size(self, rating: str) -> float:
        """등급 기반 포지션 사이즈"""
        return POSITION_SIZING.get(rating, 0.0)
    
    def construct_portfolio(self):
        """포트폴리오 구성"""
        print("\n" + "=" * 70)
        print("🎯 Constructing Portfolio (Conservative Thresholds)")
        print("=" * 70)
        print(f"\nScore Thresholds:")
        print(f"   STRONG BUY: >= {SCORE_THRESHOLDS['STRONG_BUY']}")
        print(f"   BUY: >= {SCORE_THRESHOLDS['BUY']}")
        print(f"   HOLD: >= {SCORE_THRESHOLDS['HOLD']}")
        print(f"   SELL: >= {SCORE_THRESHOLDS['SELL']}")
        print(f"   STRONG SELL: < {SCORE_THRESHOLDS['STRONG_SELL']}")
        
        if not self.level1_data:
            print("❌ No Level 1 data available")
            return
        
        results = self.level1_data.get('results', [])
        
        for stock in results:
            if stock.get('status') != 'success':
                continue
            
            final_score, rating, breakdown = self.calculate_final_score(stock)
            
            position = {
                'symbol': stock['symbol'],
                'name': stock['name'],
                'sector': stock.get('sector', 'Unknown'),
                'market': stock.get('market', 'KOSPI'),
                'final_score': final_score,
                'rating': rating,
                'position_size': self._get_position_size(rating),
                'level1_score': breakdown['level1_score'],
                'breakdown': breakdown
            }
            
            self.analysis_results.append(position)
            
            # 포트폴리오 분류
            if rating in ['STRONG_BUY', 'BUY']:
                self.portfolio['long'].append(position)
            elif rating in ['STRONG_SELL', 'SELL']:
                self.portfolio['short'].append(position)
            else:
                self.portfolio['neutral'].append(position)
        
        # 점수순 정렬
        self.portfolio['long'].sort(key=lambda x: x['final_score'], reverse=True)
        self.portfolio['short'].sort(key=lambda x: x['final_score'])
        self.analysis_results.sort(key=lambda x: x['final_score'], reverse=True)
        
        # 출력
        print("\n" + "=" * 70)
        print("📊 PORTFOLIO CONSTRUCTION COMPLETE")
        print("=" * 70)
        
        total_long = len(self.portfolio['long'])
        total_short = len(self.portfolio['short'])
        total_neutral = len(self.portfolio['neutral'])
        
        print(f"\n📈 Long Positions: {total_long}")
        for p in self.portfolio['long'][:5]:
            print(f"   • {p['name']}: {p['final_score']} pts ({p['rating']}) - {p['position_size']*100:.0f}%")
        if total_long > 5:
            print(f"   ... and {total_long - 5} more")
        
        print(f"\n📉 Short Positions: {total_short}")
        for p in self.portfolio['short'][:5]:
            print(f"   • {p['name']}: {p['final_score']} pts ({p['rating']})")
        
        print(f"\n⚖️  Neutral: {total_neutral}")
        
        # 포트폴리오 비중 계산
        total_long_weight = sum(p['position_size'] for p in self.portfolio['long'])
        total_short_weight = sum(p['position_size'] for p in self.portfolio['short'])
        cash_weight = 1.0 - total_long_weight - total_short_weight
        
        print(f"\n💰 Portfolio Allocation:")
        print(f"   Long: {total_long_weight*100:.1f}%")
        print(f"   Short: {total_short_weight*100:.1f}%")
        print(f"   Cash: {cash_weight*100:.1f}%")
    
    def generate_report(self) -> Dict:
        """최종 리포트 생성"""
        print("\n" + "=" * 70)
        print("📋 Generating Final Report...")
        print("=" * 70)
        
        total_long_weight = sum(p['position_size'] for p in self.portfolio['long'])
        total_short_weight = sum(p['position_size'] for p in self.portfolio['short'])
        
        report = {
            'agent_id': 'PM_001',
            'agent_name': 'Portfolio Manager',
            'analysis_date': datetime.now().isoformat(),
            'methodology': {
                'score_weights': {
                    'level1': 0.5,
                    'level2_sector': 0.3,
                    'level2_macro': 0.2
                },
                'thresholds': SCORE_THRESHOLDS,
                'position_sizing': POSITION_SIZING
            },
            'market_outlook': {
                'macro_condition': self.level2_macro.get('adjustment', {}).get('market_condition', 'Unknown'),
                'macro_adjustment': self.level2_macro.get('adjustment', {}).get('pct', 0),
                'recommendation': self.level2_macro.get('recommendations', {})
            },
            'portfolio_summary': {
                'total_stocks': len(self.analysis_results),
                'long_count': len(self.portfolio['long']),
                'short_count': len(self.portfolio['short']),
                'neutral_count': len(self.portfolio['neutral']),
                'long_weight': round(total_long_weight, 3),
                'short_weight': round(total_short_weight, 3),
                'cash_weight': round(1.0 - total_long_weight - total_short_weight, 3)
            },
            'portfolio': self.portfolio,
            'all_rankings': self.analysis_results[:20]  # TOP 20만
        }
        
        # 저장
        output_path = f'{DATA_PATH}/level3_daily'
        os.makedirs(output_path, exist_ok=True)
        
        date_str = datetime.now().strftime('%Y%m%d_%H%M')
        output_file = f'{output_path}/portfolio_report_{date_str}.json'
        
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(report, f, indent=2, ensure_ascii=False)
        
        print(f"✅ Report saved: {output_file}")
        
        return report
    
    def run_full_pipeline(self, run_agents: bool = True):
        """전체 파이프라인 실행"""
        print("=" * 70)
        print("🚀 PM_001 FULL PIPELINE")
        print("=" * 70)
        print(f"Start Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        
        if run_agents:
            # Level 1 실행
            if not self.run_level1_agents():
                print("❌ Pipeline failed at Level 1")
                return None
            
            # Level 2 실행
            if not self.run_level2_agents():
                print("❌ Pipeline failed at Level 2")
                return None
        
        # 데이터 로드
        if not self.load_all_data():
            print("❌ Pipeline failed at Data Loading")
            return None
        
        # 포트폴리오 구성
        self.construct_portfolio()
        
        # 리포트 생성
        report = self.generate_report()
        
        print("\n" + "=" * 70)
        print("✅ FULL PIPELINE COMPLETE")
        print("=" * 70)
        print(f"End Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        
        return report


def main():
    """메인 함수"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Portfolio Manager Agent (PM_001)')
    parser.add_argument('--skip-agents', action='store_true', 
                       help='Skip running Level 1/2 agents, use existing data')
    
    args = parser.parse_args()
    
    pm = PortfolioManagerAgent()
    report = pm.run_full_pipeline(run_agents=not args.skip_agents)
    
    if report:
        print("\n📊 FINAL PORTFOLIO SUMMARY:")
        print(f"   Long: {report['portfolio_summary']['long_count']} stocks")
        print(f"   Short: {report['portfolio_summary']['short_count']} stocks")
        print(f"   Cash: {report['portfolio_summary']['cash_weight']*100:.1f}%")


if __name__ == '__main__':
    main()
