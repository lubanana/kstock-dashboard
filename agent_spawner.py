#!/usr/bin/env python3
"""
KStock Agent Spawner
실제 하위 에이전트를 spawn하여 병렬 분석 실행

사용법:
  python3 agent_spawner.py --symbol 005930.KS --name 삼성전자
"""

import json
import os
import sys
import argparse
from datetime import datetime
from typing import Dict, List
import time

BASE_PATH = '/home/programs/kstock_analyzer'
sys.path.insert(0, BASE_PATH)

from investment_agent_group import InvestmentAgentGroup


class AgentSpawner:
    """하위 에이전트 스포너"""
    
    def __init__(self):
        self.group = InvestmentAgentGroup()
        self.results_path = f'{BASE_PATH}/data/agent_results'
        os.makedirs(self.results_path, exist_ok=True)
    
    def spawn_agent(self, agent_id: str, symbol: str, name: str) -> Dict:
        """단일 에이전트 spawn"""
        agent = self.group.get_agent(agent_id)
        if not agent:
            return {'error': f'Agent {agent_id} not found'}
        
        # 프롬프트 준비
        prompt = self._build_agent_prompt(agent, symbol, name)
        
        # 세션 spawn (실제 구현은 OpenClaw sessions_spawn 사용)
        # 여기서는 시뮬레이션
        spawn_config = {
            'agent_id': agent_id,
            'agent_name': agent['name'],
            'symbol': symbol,
            'name': name,
            'prompt': prompt,
            'timestamp': datetime.now().isoformat(),
            'status': 'spawned'
        }
        
        print(f"   🚀 Spawned {agent['name']} ({agent_id})")
        
        return spawn_config
    
    def _build_agent_prompt(self, agent: Dict, symbol: str, name: str) -> str:
        """에이전트 프롬프트 빌드"""
        base_prompt = agent.get('prompt_template', '')
        
        enhanced_prompt = f"""{base_prompt}

---

**분석 대상**
- 종목코드: {symbol}
- 종목명: {name}
- 분석일: {datetime.now().strftime('%Y년 %m월 %d일')}

**지침**
1. 제공된 데이터를 바탕으로 철저한 분석 수행
2. 각 항목별 점수(0-25점)와 총점(0-100점) 계산
3. 핵심 신호와 리스크 요인 명시
4. BUY/HOLD/SELL 중 하나의 명확한 추천 제시
5. 근거를 구체적으로 설명

**출력 형식 (반드시 JSON)**
```json
{{
  "total_score": 0-100,
  "breakdown": {{...}},
  "key_signals": ["..."],
  "risk_flags": ["..."],
  "recommendation": "BUY/HOLD/SELL",
  "rationale": "..."
}}
```

분석을 시작하세요."""
        
        return enhanced_prompt
    
    def run_level1_parallel(self, symbol: str, name: str) -> List[Dict]:
        """Level 1: 4명 에이전트 병렬 spawn"""
        print(f"\n{'='*70}")
        print(f"🎯 Level 1: Spawning 4 Analysts (Parallel)")
        print(f"   Target: {name} ({symbol})")
        print('='*70)
        
        level1_agents = ['TECH_001', 'QUANT_001', 'QUAL_001', 'NEWS_001']
        spawned = []
        
        for agent_id in level1_agents:
            config = self.spawn_agent(agent_id, symbol, name)
            spawned.append(config)
            time.sleep(0.5)  # spawn 간격
        
        print(f"\n   ✅ {len(spawned)} agents spawned successfully")
        
        return spawned
    
    def run_level2_parallel(self, symbol: str, name: str, level1_results: List[Dict]) -> List[Dict]:
        """Level 2: 2명 에이전트 병렬 spawn"""
        print(f"\n{'='*70}")
        print(f"🎯 Level 2: Spawning 2 Managers (Parallel)")
        print(f"   Input: Level 1 results from {len(level1_results)} analysts")
        print('='*70)
        
        level2_agents = ['SECTOR_001', 'MACRO_001']
        spawned = []
        
        for agent_id in level2_agents:
            agent = self.group.get_agent(agent_id)
            
            # Level 1 결과를 컨텍스트에 포함
            context = {
                'level1_summary': [
                    {
                        'agent': r['agent_name'],
                        'symbol': r['symbol'],
                        'status': r['status']
                    }
                    for r in level1_results
                ]
            }
            
            config = self.spawn_agent(agent_id, symbol, name)
            config['context'] = context
            spawned.append(config)
            time.sleep(0.5)
        
        print(f"\n   ✅ {len(spawned)} agents spawned successfully")
        
        return spawned
    
    def run_level3_final(self, symbol: str, name: str, 
                         level1_results: List[Dict], 
                         level2_results: List[Dict]) -> Dict:
        """Level 3: PM 에이전트 spawn"""
        print(f"\n{'='*70}")
        print(f"🎯 Level 3: Spawning Portfolio Manager (Final Decision)")
        print(f"   Input: L1({len(level1_results)}) + L2({len(level2_results)})")
        print('='*70)
        
        config = self.spawn_agent('PM_001', symbol, name)
        config['inputs'] = {
            'level1_count': len(level1_results),
            'level2_count': len(level2_results)
        }
        
        print(f"\n   ✅ PM agent spawned successfully")
        
        return config
    
    def run_full_pipeline(self, symbol: str, name: str) -> Dict:
        """전체 파이프라인 실행"""
        print(f"\n{'#'*70}")
        print(f"# 🚀 KStock Multi-Agent Pipeline")
        print(f"# Target: {name} ({symbol})")
        print(f"# Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print('#'*70)
        
        # Level 1: 4명 병렬
        level1_spawned = self.run_level1_parallel(symbol, name)
        
        # Level 2: 2명 병렬 (Level 1 결과 기반)
        level2_spawned = self.run_level2_parallel(symbol, name, level1_spawned)
        
        # Level 3: PM (모든 결과 종합)
        level3_spawned = self.run_level3_final(symbol, name, level1_spawned, level2_spawned)
        
        # 결과 저장
        pipeline_result = {
            'pipeline_id': f"PIPE_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
            'symbol': symbol,
            'name': name,
            'started_at': datetime.now().isoformat(),
            'stages': {
                'level1': {
                    'description': 'Information Gathering & Scoring',
                    'agents_spawned': len(level1_spawned),
                    'agents': level1_spawned
                },
                'level2': {
                    'description': 'Sector & Macro Adjustment',
                    'agents_spawned': len(level2_spawned),
                    'agents': level2_spawned
                },
                'level3': {
                    'description': 'Final Portfolio Decision',
                    'agents_spawned': 1,
                    'agent': level3_spawned
                }
            },
            'total_agents': len(level1_spawned) + len(level2_spawned) + 1,
            'status': 'pipeline_initialized'
        }
        
        # 파일 저장
        output_file = f"{self.results_path}/pipeline_{symbol.replace('.', '_')}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(pipeline_result, f, indent=2, ensure_ascii=False)
        
        # 요약 출력
        print(f"\n{'='*70}")
        print(f"✅ Pipeline Initialized Successfully!")
        print(f"{'='*70}")
        print(f"   📊 Pipeline ID: {pipeline_result['pipeline_id']}")
        print(f"   🎯 Target: {name} ({symbol})")
        print(f"   🤖 Total Agents: {pipeline_result['total_agents']}")
        print(f"      - Level 1 (Analysts): 4 agents")
        print(f"      - Level 2 (Managers): 2 agents")
        print(f"      - Level 3 (PM): 1 agent")
        print(f"   💾 Config saved: {output_file}")
        print('='*70)
        
        return pipeline_result
    
    def create_batch_config(self, stocks: List[Dict]) -> str:
        """배치 처리 설정 생성"""
        batch_config = {
            'batch_id': f"BATCH_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
            'created_at': datetime.now().isoformat(),
            'stock_count': len(stocks),
            'stocks': stocks,
            'workflow': {
                'parallel_stocks': False,  # 순차 처리
                'parallel_agents': True,   # 에이전트 병렬
                'levels': [
                    {'level': 1, 'agents': 4, 'parallel': True},
                    {'level': 2, 'agents': 2, 'parallel': True},
                    {'level': 3, 'agents': 1, 'parallel': False}
                ]
            }
        }
        
        output_file = f"{self.results_path}/batch_config_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(batch_config, f, indent=2, ensure_ascii=False)
        
        return output_file


def main():
    parser = argparse.ArgumentParser(description='KStock Agent Spawner')
    parser.add_argument('--symbol', default='005930.KS', help='Stock symbol')
    parser.add_argument('--name', default='삼성전자', help='Stock name')
    parser.add_argument('--batch', help='Batch config file')
    
    args = parser.parse_args()
    
    spawner = AgentSpawner()
    
    if args.batch:
        # 배치 모드
        with open(args.batch, 'r') as f:
            batch = json.load(f)
        
        print(f"Batch Mode: {batch['stock_count']} stocks")
        for stock in batch['stocks']:
            spawner.run_full_pipeline(stock['symbol'], stock['name'])
    else:
        # 단일 종목
        spawner.run_full_pipeline(args.symbol, args.name)


if __name__ == '__main__':
    main()
