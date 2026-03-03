#!/usr/bin/env python3
"""
Sector Analysis Agent (SECTOR_001)
섹터 분석 에이전트 - 동종 업계 평균 비교 및 섹터 로테이션
"""

import json
import os
from datetime import datetime
from typing import Dict, List, Tuple
from collections import defaultdict

BASE_PATH = '/home/programs/kstock_analyzer'
DATA_PATH = f'{BASE_PATH}/data/level1_daily'


class SectorAnalysisAgent:
    """섹터 분석 에이전트"""
    
    def __init__(self):
        self.level1_data = None
        self.sector_stats = {}
        self.adjustments = {}
    
    def load_latest_level1(self) -> Dict:
        """최신 Level 1 데이터 로드"""
        files = [f for f in os.listdir(DATA_PATH) if f.startswith('level1_fullmarket_') and f.endswith('.json')]
        if not files:
            return {}
        
        latest = sorted(files)[-1]
        with open(f'{DATA_PATH}/{latest}', 'r', encoding='utf-8') as f:
            return json.load(f)
    
    def calculate_sector_stats(self, results: List[Dict]) -> Dict:
        """섹터별 통계 계산"""
        sector_data = defaultdict(lambda: {'scores': [], 'stocks': []})
        
        for stock in results:
            if stock.get('status') != 'success':
                continue
            
            sector = stock.get('sector', 'Unknown')
            score = stock.get('avg_score', 0)
            
            sector_data[sector]['scores'].append(score)
            sector_data[sector]['stocks'].append({
                'symbol': stock['symbol'],
                'name': stock['name'],
                'score': score,
                'consensus': stock.get('consensus', 'HOLD'),
                'market': stock.get('market', 'KOSPI')
            })
        
        # 섹터별 평균 및 순위 계산
        sector_stats = {}
        for sector, data in sector_data.items():
            scores = data['scores']
            if not scores:
                continue
            
            avg_score = sum(scores) / len(scores)
            
            # 섹터 강도 판정
            if avg_score >= 60:
                strength = 'STRONG'
                rotation_signal = 'Overweight'
            elif avg_score >= 50:
                strength = 'MODERATE'
                rotation_signal = 'Neutral'
            else:
                strength = 'WEAK'
                rotation_signal = 'Underweight'
            
            # 상대 강도 (vs 전체 평균)
            all_scores = [s for s in [r.get('avg_score', 0) for r in results if r.get('status') == 'success']]
            overall_avg = sum(all_scores) / len(all_scores) if all_scores else 0
            relative_strength = (avg_score / overall_avg - 1) * 100 if overall_avg > 0 else 0
            
            sector_stats[sector] = {
                'average_score': round(avg_score, 1),
                'stock_count': len(scores),
                'strength': strength,
                'rotation_signal': rotation_signal,
                'relative_strength_pct': round(relative_strength, 1),
                'top_performer': max(data['stocks'], key=lambda x: x['score']),
                'bottom_performer': min(data['stocks'], key=lambda x: x['score']),
                'all_stocks': sorted(data['stocks'], key=lambda x: x['score'], reverse=True)
            }
        
        return sector_stats
    
    def calculate_sector_adjustments(self, sector_stats: Dict) -> Dict:
        """섹터별 조정 계수 계산"""
        adjustments = {}
        
        for sector, stats in sector_stats.items():
            avg_score = stats['average_score']
            strength = stats['strength']
            relative = stats['relative_strength_pct']
            
            # 조정 계수 계산 (-15% ~ +15%)
            if strength == 'STRONG' and relative > 10:
                adjustment = 15
                reason = "강세 섹터 + 상대강도 우수"
            elif strength == 'STRONG':
                adjustment = 10
                reason = "강세 섹터"
            elif strength == 'MODERATE' and relative > 0:
                adjustment = 5
                reason = "중립-상 섹터"
            elif strength == 'MODERATE':
                adjustment = 0
                reason = "중립 섹터"
            elif relative < -10:
                adjustment = -15
                reason = "약세 섹터 + 상대약도"
            else:
                adjustment = -10
                reason = "약세 섹터"
            
            adjustments[sector] = {
                'adjustment_pct': adjustment,
                'reason': reason,
                'original_avg': avg_score,
                'adjusted_avg': round(avg_score * (1 + adjustment/100), 1)
            }
        
        return adjustments
    
    def analyze(self) -> Dict:
        """섹터 분석 실행"""
        print("=" * 70)
        print("📊 Sector Analysis Agent (SECTOR_001)")
        print("=" * 70)
        
        # 데이터 로드
        self.level1_data = self.load_latest_level1()
        if not self.level1_data:
            print("❌ No Level 1 data found!")
            return {}
        
        results = self.level1_data.get('results', [])
        print(f"\n📈 Loaded {len(results)} stocks from Level 1 analysis")
        
        # 섹터별 통계
        print("\n🔍 Calculating sector statistics...")
        self.sector_stats = self.calculate_sector_stats(results)
        
        # 섹터별 조정 계수
        print("📊 Calculating sector adjustments...")
        self.adjustments = self.calculate_sector_adjustments(self.sector_stats)
        
        # 출력
        print("\n" + "=" * 70)
        print("📋 SECTOR ANALYSIS RESULTS")
        print("=" * 70)
        
        # 섹터별 결과 출력
        sorted_sectors = sorted(self.sector_stats.items(), 
                               key=lambda x: x[1]['average_score'], 
                               reverse=True)
        
        print(f"\n{'Rank':<5} {'Sector':<15} {'Avg':<8} {'Strength':<10} {'Rel.Str':<10} {'Adj':<8}")
        print("-" * 70)
        
        for i, (sector, stats) in enumerate(sorted_sectors, 1):
            adj = self.adjustments[sector]['adjustment_pct']
            print(f"{i:<5} {sector:<15} {stats['average_score']:<8.1f} "
                  f"{stats['strength']:<10} {stats['relative_strength_pct']:+.1f}%    {adj:+.0f}%")
        
        # TOP/Bottom 섹터
        print("\n" + "-" * 70)
        print("🏆 TOP 3 Sectors:")
        for i, (sector, stats) in enumerate(sorted_sectors[:3], 1):
            top = stats['top_performer']
            print(f"   {i}. {sector} (Avg: {stats['average_score']}) - Top: {top['name']} ({top['score']})")
        
        print("\n⚠️  BOTTOM 3 Sectors:")
        for i, (sector, stats) in enumerate(sorted_sectors[-3:], 1):
            bottom = stats['bottom_performer']
            print(f"   {i}. {sector} (Avg: {stats['average_score']}) - Bottom: {bottom['name']} ({bottom['score']})")
        
        # 결과 구성
        result = {
            'agent_id': 'SECTOR_001',
            'agent_name': 'Sector Analyst',
            'analysis_date': datetime.now().isoformat(),
            'total_stocks_analyzed': len(results),
            'sector_count': len(self.sector_stats),
            'sectors': self.sector_stats,
            'adjustments': self.adjustments,
            'recommendations': {
                'overweight': [s for s, a in self.adjustments.items() if a['adjustment_pct'] >= 10],
                'neutral': [s for s, a in self.adjustments.items() if -5 <= a['adjustment_pct'] < 10],
                'underweight': [s for s, a in self.adjustments.items() if a['adjustment_pct'] < -5]
            }
        }
        
        print("\n" + "=" * 70)
        print("✅ SECTOR ANALYSIS COMPLETE")
        print("=" * 70)
        
        return result
    
    def save_result(self, result: Dict):
        """결과 저장"""
        output_path = f'{BASE_PATH}/data/level2_daily'
        os.makedirs(output_path, exist_ok=True)
        
        date_str = datetime.now().strftime('%Y%m%d_%H%M')
        output_file = f'{output_path}/sector_analysis_{date_str}.json'
        
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(result, f, indent=2, ensure_ascii=False)
        
        print(f"\n💾 Result saved: {output_file}")
        return output_file


def main():
    """메인 함수"""
    agent = SectorAnalysisAgent()
    result = agent.analyze()
    
    if result:
        agent.save_result(result)
        
        print("\n📋 JSON Output:")
        print(json.dumps(result, indent=2, ensure_ascii=False)[:2000] + "...")


if __name__ == '__main__':
    main()
