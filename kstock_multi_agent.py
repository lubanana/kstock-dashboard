#!/usr/bin/env python3
"""
KStock Multi-Agent Orchestrator
멀티 에이전트 오케스트레이션 시스템

Features:
- 4개 에이전트 병렬 실행
- 구조화된 핸드오프
- 컨텍스트 공유
- 결과 통합
"""

import asyncio
import json
import time
from datetime import datetime
from typing import Dict, List, Optional, Any
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from enum import Enum

import sys
sys.path.insert(0, '/home/programs/kstock_analyzer')
sys.path.insert(0, '/home/programs/kstock_analyzer/agents')

from agents.technical_agent import TechnicalAnalysisAgent
from agents.quant_agent import QuantAnalysisAgent
from agents.qualitative_agent import QualitativeAnalysisAgent
from agents.enhanced_news_agent import EnhancedNewsAgent


class AgentType(Enum):
    TECHNICAL = "technical"
    QUANT = "quant"
    QUALITATIVE = "qualitative"
    NEWS = "news"


@dataclass
class AgentResult:
    agent_type: AgentType
    symbol: str
    status: str
    score: float
    recommendation: str
    signals: List[str] = field(default_factory=list)
    risks: List[str] = field(default_factory=list)
    execution_time: float = 0.0
    error: Optional[str] = None


class MultiAgentOrchestrator:
    """멀티 에이전트 오케스트레이터"""
    
    AGENT_MAP = {
        AgentType.TECHNICAL: TechnicalAnalysisAgent,
        AgentType.QUANT: QuantAnalysisAgent,
        AgentType.QUALITATIVE: QualitativeAnalysisAgent,
        AgentType.NEWS: EnhancedNewsAgent
    }
    
    def __init__(self, max_workers: int = 4):
        self.max_workers = max_workers
        self.executor = ThreadPoolExecutor(max_workers=max_workers)
        
    def run_agent_sync(self, agent_type: AgentType, symbol: str, name: str) -> AgentResult:
        """동기 에이전트 실행"""
        start = time.time()
        
        try:
            agent_class = self.AGENT_MAP.get(agent_type)
            agent = agent_class(symbol, name)
            result = agent.analyze()
            
            return AgentResult(
                agent_type=agent_type,
                symbol=symbol,
                status='success',
                score=result.get('total_score', 0),
                recommendation=result.get('recommendation', 'HOLD'),
                signals=result.get('key_signals', [])[:3],
                risks=result.get('key_risks', [])[:2],
                execution_time=time.time() - start
            )
            
        except Exception as e:
            return AgentResult(
                agent_type=agent_type,
                symbol=symbol,
                status='failed',
                score=0,
                recommendation='HOLD',
                error=str(e),
                execution_time=time.time() - start
            )
    
    async def run_parallel(self, symbol: str, name: str) -> Dict:
        """4개 에이전트 병렬 실행"""
        print(f"\n🚀 Parallel Analysis: {name} ({symbol})")
        start = time.time()
        
        loop = asyncio.get_event_loop()
        tasks = []
        
        for agent_type in AgentType:
            task = loop.run_in_executor(
                self.executor,
                self.run_agent_sync,
                agent_type,
                symbol,
                name
            )
            tasks.append(task)
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # 결과 집계
        result_map = {}
        total_score = 0
        
        for result in results:
            if isinstance(result, AgentResult):
                result_map[result.agent_type.value] = {
                    'score': result.score,
                    'recommendation': result.recommendation,
                    'signals': result.signals,
                    'risks': result.risks,
                    'execution_time': result.execution_time,
                    'status': result.status
                }
                total_score += result.score
        
        avg_score = total_score / 4 if result_map else 0
        elapsed = time.time() - start
        
        print(f"   ✅ Complete in {elapsed:.1f}s (평균: {avg_score:.1f}pts)")
        
        return {
            'symbol': symbol,
            'name': name,
            'avg_score': avg_score,
            'elapsed': elapsed,
            'agents': result_map
        }


def test_orchestrator():
    """테스트"""
    print("="*60)
    print("🎯 Multi-Agent Orchestrator Test")
    print("="*60)
    
    orchestrator = MultiAgentOrchestrator(max_workers=4)
    
    # 테스트 종목
    test_stocks = [
        ('005930.KS', '삼성전자'),
        ('000660.KS', 'SK하이닉스')
    ]
    
    for symbol, name in test_stocks:
        result = asyncio.run(orchestrator.run_parallel(symbol, name))
        
        print(f"\n📊 {name} 결과:")
        print(f"   평균 점수: {result['avg_score']:.1f}")
        print(f"   소요 시간: {result['elapsed']:.1f}s")
        
        for agent_type, data in result['agents'].items():
            status = "✅" if data['status'] == 'success' else "❌"
            print(f"   {status} {agent_type}: {data['score']:.1f}pts ({data['execution_time']:.1f}s)")
    
    print("\n" + "="*60)


if __name__ == '__main__':
    test_orchestrator()
