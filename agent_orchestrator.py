#!/usr/bin/env python3
"""
KStock Agent Orchestrator
투자 에이전트 그룹 실행 오케스트레이터

사용법:
  python3 agent_orchestrator.py --symbol 005930.KS --name 삼성전자
  python3 agent_orchestrator.py --batch stocks.json
"""

import json
import os
import sys
import argparse
from datetime import datetime
from typing import Dict, List
import subprocess

BASE_PATH = '/home/programs/kstock_analyzer'
CONFIG_PATH = f'{BASE_PATH}/agent_group_config.json'
RESULTS_PATH = f'{BASE_PATH}/data/agent_results'


class AgentOrchestrator:
    """에이전트 오케스트레이터"""
    
    def __init__(self):
        self.config = self._load_config()
        os.makedirs(RESULTS_PATH, exist_ok=True)
    
    def _load_config(self) -> Dict:
        """설정 로드"""
        with open(CONFIG_PATH, 'r', encoding='utf-8') as f:
            return json.load(f)
    
    def get_agent_prompt(self, agent_id: str, symbol: str, name: str) -> str:
        """에이전트별 프롬프트 생성"""
        # 에이전트 찾기
        agent = None
        for level_name, level_data in self.config['levels'].items():
            for a in level_data['agents']:
                if a['id'] == agent_id:
                    agent = a
                    break
            if agent:
                break
        
        if not agent:
            return ""
        
        prompt = f"""{agent['prompt_template']}

---

**분석 대상 종목**
- 종목코드: {symbol}
- 종목명: {name}

**당신의 역할**: {agent['role']}
**전문 분야**: {agent['specialty']}

현재 시장 데이터와 종목 정보를 바탕으로 분석을 수행하고, 0-100점의 점수와 함께 상세한 근거를 제시하세요.

출력은 반드시 JSON 형식으로 제공하세요."""
        
        return prompt
    
    def run_level1_analysis(self, symbol: str, name: str) -> Dict:
        """Level 1 분석 실행 (4명 병렬)"""
        print(f"\n{'='*60}")
        print(f"Level 1 Analysis: {name} ({symbol})")
        print('='*60)
        
        level1_agents = ['TECH_001', 'QUANT_001', 'QUAL_001', 'NEWS_001']
        results = {}
        
        for agent_id in level1_agents:
            agent = self._get_agent_info(agent_id)
            print(f"\n🤖 Running {agent['name']}...")
            
            # 여기서 실제로는 sessions_spawn을 사용
            # 현재는 시뮬레이션
            prompt = self.get_agent_prompt(agent_id, symbol, name)
            
            # 결과 저장 구조
            results[agent_id] = {
                'agent_name': agent['name'],
                'agent_role': agent['role'],
                'prompt': prompt[:200] + '...',
                'status': 'pending',
                'result': None
            }
            
            print(f"   ✓ Prompt prepared ({len(prompt)} chars)")
        
        return results
    
    def run_level2_analysis(self, symbol: str, name: str, level1_results: Dict) -> Dict:
        """Level 2 분석 실행 (2명 병렬)"""
        print(f"\n{'='*60}")
        print(f"Level 2 Analysis: {name} ({symbol})")
        print('='*60)
        
        level2_agents = ['SECTOR_001', 'MACRO_001']
        results = {}
        
        for agent_id in level2_agents:
            agent = self._get_agent_info(agent_id)
            print(f"\n🤖 Running {agent['name']}...")
            
            prompt = self.get_agent_prompt(agent_id, symbol, name)
            
            results[agent_id] = {
                'agent_name': agent['name'],
                'agent_role': agent['role'],
                'level1_input': level1_results,
                'prompt': prompt[:200] + '...',
                'status': 'pending',
                'result': None
            }
            
            print(f"   ✓ Prompt prepared ({len(prompt)} chars)")
        
        return results
    
    def run_level3_decision(self, symbol: str, name: str, 
                            level1_results: Dict, level2_results: Dict) -> Dict:
        """Level 3 최종 결정"""
        print(f"\n{'='*60}")
        print(f"Level 3 Decision: {name} ({symbol})")
        print('='*60)
        
        agent_id = 'PM_001'
        agent = self._get_agent_info(agent_id)
        
        print(f"\n🤖 Running {agent['name']}...")
        
        prompt = self.get_agent_prompt(agent_id, symbol, name)
        
        result = {
            'agent_name': agent['name'],
            'agent_role': agent['role'],
            'level1_input': level1_results,
            'level2_input': level2_results,
            'prompt': prompt[:200] + '...',
            'status': 'pending',
            'result': None
        }
        
        print(f"   ✓ Prompt prepared ({len(prompt)} chars)")
        
        return {agent_id: result}
    
    def _get_agent_info(self, agent_id: str) -> Dict:
        """에이전트 정보 조회"""
        for level_name, level_data in self.config['levels'].items():
            for agent in level_data['agents']:
                if agent['id'] == agent_id:
                    return agent
        return {}
    
    def run_full_analysis(self, symbol: str, name: str) -> Dict:
        """전체 분석 실행"""
        print(f"\n{'#'*70}")
        print(f"# KStock Multi-Agent Analysis")
        print(f"# Target: {name} ({symbol})")
        print(f"# Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print('#'*70)
        
        # Level 1
        level1_results = self.run_level1_analysis(symbol, name)
        
        # Level 2
        level2_results = self.run_level2_analysis(symbol, name, level1_results)
        
        # Level 3
        level3_results = self.run_level3_decision(symbol, name, level1_results, level2_results)
        
        # 종합 결과
        final_result = {
            'analysis_id': f"ANALYSIS_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
            'symbol': symbol,
            'name': name,
            'timestamp': datetime.now().isoformat(),
            'level_1': level1_results,
            'level_2': level2_results,
            'level_3': level3_results,
            'status': 'completed'
        }
        
        # 결과 저장
        output_file = f"{RESULTS_PATH}/{symbol.replace('.', '_')}_{datetime.now().strftime('%Y%m%d')}.json"
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(final_result, f, indent=2, ensure_ascii=False)
        
        print(f"\n{'='*70}")
        print(f"✅ Analysis Complete!")
        print(f"   Results saved: {output_file}")
        print('='*70)
        
        return final_result
    
    def generate_report(self, results: Dict) -> str:
        """분석 결과 리포트 생성"""
        html = f"""
<!DOCTYPE html>
<html lang="ko">
<head>
    <meta charset="UTF-8">
    <title>Analysis Report - {results['name']}</title>
    <style>
        body {{ font-family: Arial, sans-serif; max-width: 1000px; margin: 0 auto; padding: 20px; }}
        .header {{ background: linear-gradient(135deg, #667eea, #764ba2); color: white; padding: 30px; border-radius: 15px; }}
        .level {{ margin: 20px 0; padding: 20px; background: #f8f9fa; border-radius: 10px; }}
        .agent {{ margin: 10px 0; padding: 15px; background: white; border-left: 4px solid #3498db; }}
        .level-1 {{ border-color: #3498db; }}
        .level-2 {{ border-color: #9b59b6; }}
        .level-3 {{ border-color: #e74c3c; }}
    </style>
</head>
<body>
    <div class="header">
        <h1>Multi-Agent Analysis Report</h1>
        <p>{results['name']} ({results['symbol']})</p>
        <p>{results['timestamp']}</p>
    </div>
    
    <div class="level">
        <h2>Level 1: Analysts (4 agents)</h2>
        <div class="agent">
            <h3>Technical Analyst</h3>
            <p>Status: {results['level_1'].get('TECH_001', {}).get('status', 'N/A')}</p>
        </div>
        <div class="agent">
            <h3>Quant Analyst</h3>
            <p>Status: {results['level_1'].get('QUANT_001', {}).get('status', 'N/A')}</p>
        </div>
    </div>
    
    <div class="level">
        <h2>Level 2: Managers (2 agents)</h2>
        <div class="agent">
            <h3>Sector Analyst</h3>
            <p>Status: {results['level_2'].get('SECTOR_001', {}).get('status', 'N/A')}</p>
        </div>
    </div>
    
    <div class="level">
        <h2>Level 3: Portfolio Manager</h2>
        <div class="agent">
            <h3>Final Decision</h3>
            <p>Status: {results['level_3'].get('PM_001', {}).get('status', 'N/A')}</p>
        </div>
    </div>
</body>
</html>"""
        
        return html


def main():
    parser = argparse.ArgumentParser(description='KStock Agent Orchestrator')
    parser.add_argument('--symbol', help='Stock symbol (e.g., 005930.KS)')
    parser.add_argument('--name', help='Stock name (e.g., 삼성전자)')
    parser.add_argument('--batch', help='Batch file with multiple stocks (JSON)')
    
    args = parser.parse_args()
    
    orchestrator = AgentOrchestrator()
    
    if args.batch:
        # 배치 처리
        with open(args.batch, 'r') as f:
            stocks = json.load(f)
        
        for stock in stocks:
            print(f"\n{'#'*70}")
            print(f"Processing {stock['name']}...")
            orchestrator.run_full_analysis(stock['symbol'], stock['name'])
    
    elif args.symbol and args.name:
        # 단일 종목 분석
        results = orchestrator.run_full_analysis(args.symbol, args.name)
        
        # 리포트 생성
        report_html = orchestrator.generate_report(results)
        report_file = f"{BASE_PATH}/docs/analysis_{args.symbol.replace('.', '_')}.html"
        with open(report_file, 'w', encoding='utf-8') as f:
            f.write(report_html)
        
        print(f"\n📄 Report generated: {report_file}")
    
    else:
        # 데모 모드
        print("KStock Agent Orchestrator")
        print("=" * 60)
        print("\nUsage:")
        print("  python3 agent_orchestrator.py --symbol 005930.KS --name 삼성전자")
        print("  python3 agent_orchestrator.py --batch stocks.json")
        print("\nRunning demo mode...\n")
        
        results = orchestrator.run_full_analysis('005930.KS', '삼성전자')


if __name__ == '__main__':
    main()
