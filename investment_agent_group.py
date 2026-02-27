#!/usr/bin/env python3
"""
KStock Investment Agent Group - Multi-Level AI Investment System
3레벨 계층형 투자 에이전트 그룹 관리 시스템

Level 1: 실무진 (4명) - 정보 수집 및 스코어링
Level 2: 중간 관리자 (2명) - 섹터/매크로 조정  
Level 3: 포트폴리오 매니저 (1명) - 최종 결정
"""

import json
import os
from datetime import datetime
from typing import Dict, List, Any

BASE_PATH = '/home/programs/kstock_analyzer'
AGENTS_CONFIG = f'{BASE_PATH}/agent_group_config.json'


class InvestmentAgentGroup:
    """투자 에이전트 그룹 관리자"""
    
    def __init__(self):
        self.agents = self._load_or_create_config()
    
    def _load_or_create_config(self) -> Dict:
        """에이전트 설정 로드 또는 생성"""
        if os.path.exists(AGENTS_CONFIG):
            with open(AGENTS_CONFIG, 'r', encoding='utf-8') as f:
                return json.load(f)
        
        # 기본 에이전트 그룹 구성
        config = {
            'created_at': datetime.now().isoformat(),
            'group_name': 'KStock Investment Alpha Team',
            'levels': {
                'level_1_analysts': {
                    'description': '정보 수집 및 스코어링 (0-100점)',
                    'agents': [
                        {
                            'id': 'TECH_001',
                            'name': 'Technical Analyst',
                            'role': '기술적 분석가',
                            'specialty': '가격, 모멘텀, 볼린저 밴드, 거래량',
                            'level': 1,
                            'weight': 0.25,
                            'status': 'active',
                            'prompt_template': '''당신은 기술적 분석 전문가입니다.
주어진 종목의 다음 지표를 분석하여 0-100점을 매기세요:

1. 가격 추세 (0-25점)
   - 이동평균선 배열 (5일 > 20일 > 60일)
   - 현재가 vs 이동평균선 위치

2. 모멘텀 (0-25점)
   - RSI (14일)
   - MACD 골든/데드 크로스
   - 스토캐스틱

3. 볼린저 밴드 (0-25점)
   - 밴드 위치 (%B)
   - 밴드폭 (squeeze 여부)
   - 밴드 돌파 방향

4. 거래량 (0-25점)
   - 평균 대비 거래량 비율
   - 거래량 추세
   - OBV 방향

출력 형식:
{
  "total_score": 0-100,
  "breakdown": {
    "price_trend": 0-25,
    "momentum": 0-25,
    "bollinger": 0-25,
    "volume": 0-25
  },
  "key_signals": ["신호1", "신호2"],
  "risk_flags": ["리스크1"],
  "recommendation": "BUY/HOLD/SELL"
}'''
                        },
                        {
                            'id': 'QUANT_001',
                            'name': 'Quant Analyst', 
                            'role': '정량적 분석가',
                            'specialty': '재무 지표 및 성장률',
                            'level': 1,
                            'weight': 0.25,
                            'status': 'active',
                            'prompt_template': '''당신은 정량적 분석 전문가입니다.
주어진 종목의 재무 데이터를 분석하여 0-100점을 매기세요:

1. 수익성 (0-25점)
   - ROE (Return on Equity)
   - ROA (Return on Assets)
   - 영업이익률
   - 순이익률

2. 성장성 (0-25점)
   - 매출 성장률 (YoY, QoQ)
   - 영업이익 성장률
   - EPS 성장률

3. 안정성 (0-25점)
   - 부채비율
   - 유동비율
   - 현금흐름

4. 밸류에이션 (0-25점)
   - PER (동종업계 대비)
   - PBR
   - PEG ratio
   - EV/EBITDA

출력 형식:
{
  "total_score": 0-100,
  "breakdown": {
    "profitability": 0-25,
    "growth": 0-25,
    "stability": 0-25,
    "valuation": 0-25
  },
  "key_metrics": {"PER": 0, "ROE": 0},
  "peer_comparison": "상위/중위/하위",
  "recommendation": "BUY/HOLD/SELL"
}'''
                        },
                        {
                            'id': 'QUAL_001',
                            'name': 'Qualitative Analyst',
                            'role': '정성적 분석가', 
                            'specialty': '기업 보고서 리스크 및 비즈니스 모델',
                            'level': 1,
                            'weight': 0.25,
                            'status': 'active',
                            'prompt_template': '''당신은 정성적 분석 전문가입니다.
주어진 기업의 질적 요소를 분석하여 0-100점을 매기세요:

1. 비즈니스 모델 (0-25점)
   - 경쟁 우위 (모호, 넓은 해자)
   - 수익 모델의 지속가능성
   - 시장 지위

2. 경영진 품질 (0-25점)
   - CEO 리더십 및 이력
   - 주주환원 정책
   - 투명성 및 커뮤니케이션

3. 산업 전망 (0-25점)
   - TAM (Total Addressable Market)
   - 산업 성장률
   - 기술 혁신 수준

4. 리스크 요인 (0-25점)
   - 규제 리스크
   - 경쟁 심화 위험
   - 공급망 리스크
   - ESG 이슈

출력 형식:
{
  "total_score": 0-100,
  "breakdown": {
    "business_model": 0-25,
    "management": 0-25,
    "industry_outlook": 0-25,
    "risk_factors": 0-25
  },
  "moat_rating": "Wide/Narrow/None",
  "key_risks": ["리스크1", "리스크2"],
  "recommendation": "BUY/HOLD/SELL"
}'''
                        },
                        {
                            'id': 'NEWS_001',
                            'name': 'News Sentiment Analyst',
                            'role': '뉴스 센티먼트 분석가',
                            'specialty': '호재/악재 뉴스 및 감성 분석',
                            'level': 1,
                            'weight': 0.25,
                            'status': 'active',
                            'prompt_template': '''당신은 뉴스 센티먼트 분석 전문가입니다.
주어진 종목의 뉴스 및 소셜 미디어 감성을 분석하여 0-100점을 매기세요:

1. 뉴스 감성 (0-25점)
   - 최근 30일 뉴스 긍정/부정 비율
   - 주요 미디어 커버리지 톤
   - 애널리스트 리포트 평가

2. 소셜 미디어 (0-25점)
   - 커뮤니티 센티먼트 (클리앙, 뽐뿌 등)
   - 트위터/X 언급량 및 감성
   - 개인투자자 관심도

3. 이벤트 리스크 (0-25점)
   - 실적 발표 임박 여부
   - 주주총회/배당일정
   - 공시 리스크

4. 모멘텀 신호 (0-25점)
   - 뉴스 볼륨 추세
   - 센티먼트 변화 방향
   - 이상 거래량 동반 여부

출력 형식:
{
  "total_score": 0-100,
  "breakdown": {
    "news_sentiment": 0-25,
    "social_media": 0-25,
    "event_risk": 0-25,
    "momentum_signals": 0-25
  },
  "sentiment_trend": "Improving/Stable/Declining",
  "key_news": ["뉴스1", "뉴스2"],
  "recommendation": "BUY/HOLD/SELL"
}'''
                        }
                    ]
                },
                'level_2_managers': {
                    'description': '섹터 및 매크로 조정',
                    'agents': [
                        {
                            'id': 'SECTOR_001',
                            'name': 'Sector Analyst',
                            'role': '섹터 분석가',
                            'specialty': '동종 업계 평균 비교 및 섹터 로테이션',
                            'level': 2,
                            'weight': 0.5,
                            'status': 'active',
                            'prompt_template': '''당신은 섹터 분석 전문가입니다.
Level 1 분석가들의 점수를 바탕으로 섹터 조정을 수행하세요:

1. 상대 강도 분석
   - 섹터 내 상대 순위
   - 섹터 평균 vs 개별종목
   - 섹터 모멘텀

2. 섹터 로테이션
   - 현재 유리한 섹터 판단
   - 자금 흐름 방향
   - 섹터 밸류에이션

3. 조정 계수 적용
   - 강세 섹터: +10% 가중
   - 약세 섹터: -10% 가중
   - 중립 섹터: 변동 없음

입력: Level 1 분석가들의 점수
출력: 섹터 조정된 점수 (0-100)'''
                        },
                        {
                            'id': 'MACRO_001',
                            'name': 'Macro Analyst',
                            'role': '매크로 분석가',
                            'specialty': '금리, 환율, VIX 등 거시경제 분석',
                            'level': 2,
                            'weight': 0.5,
                            'status': 'active',
                            'prompt_template': '''당신은 매크로 분석 전문가입니다.
거시경제 환경을 분석하여 포트폴리오 조정을 수행하세요:

1. 금리 환경
   - 미국 10년물 국채 금리
   - 한국 기준금리
   - 금리 전망

2. 환율
   - 원/달러 환율 추세
   - 통화 정책 방향

3. 변동성 지표
   - VIX 지수
   - KOSPI 변동성
   - 글로벌 리스크 온/오프

4. 유동성
   - FTX 유동성
   - 글로벌 자금 흐름

조정 범위: -20% ~ +20%

입력: Level 1 점수, 현재 매크로 데이터
출력: 매크로 조정된 점수 (0-100)'''
                        }
                    ]
                },
                'level_3_pm': {
                    'description': '최종 포트폴리오 결정',
                    'agents': [
                        {
                            'id': 'PM_001',
                            'name': 'Portfolio Manager',
                            'role': '포트폴리오 매니저',
                            'specialty': '최종 Long-Short 포트폴리오 구성',
                            'level': 3,
                            'weight': 1.0,
                            'status': 'active',
                            'prompt_template': '''당신은 최고 투자책임자(CIO) 겸 포트폴리오 매니저입니다.
모든 분석가들의 의견을 종합하여 최종 포트폴리오를 구성하세요:

[입력 데이터]
- Level 1: 4명 분석가의 개별 점수 및 코멘트
- Level 2: 섹터/매크로 조정 점수
- 리스크 예산 및 제약조건

[결정 프로세스]
1. 종목별 종합 점수 계산
   - 가중 평균: L1(50%) + L2(30%) + PM 판단(20%)

2. Long-Short 분류
   - Long: 종합점수 >= 70
   - Neutral: 40 < 점수 < 70
   - Short: 점수 <= 40

3. 포지션 사이징
   - Conviction 레벨에 따른 비중 결정
   - 리스크 관리 (개별종목 최대 10%)
   - 섹터 다각화

4. 리스크 관리
   - 베타 중립 고려
   - 변동성 조절
   - 스트레스 시나리오

[출력 형식]
{
  "portfolio": {
    "long_positions": [
      {"symbol": "", "name": "", "weight": 0.0, "conviction": "High/Medium/Low", "rationale": ""}
    ],
    "short_positions": [
      {"symbol": "", "name": "", "weight": 0.0, "conviction": "High/Medium/Low", "rationale": ""}
    ],
    "cash_ratio": 0.0
  },
  "summary": {
    "total_score_avg": 0,
    "portfolio_beta": 0,
    "expected_volatility": 0,
    "key_themes": [""],
    "risk_factors": [""]
  },
  "rebalancing": {
    "add": [""],
    "reduce": [""],
    "exit": [""]
  }
}'''
                        }
                    ]
                }
            },
            'workflow': {
                'description': '분석 워크플로우',
                'steps': [
                    '1. Level 1: 4명 분석가가 동시에 개별 종목 분석 (병렬)',
                    '2. Level 2: 섹터/매크로 분석가가 조정 수행 (병렬)',
                    '3. Level 3: PM이 최종 포트폴리오 구성 (순차)',
                    '4. 리포트 생성 및 GitHub 업데이트'
                ]
            }
        }
        
        # 설정 저장
        os.makedirs(os.path.dirname(AGENTS_CONFIG), exist_ok=True)
        with open(AGENTS_CONFIG, 'w', encoding='utf-8') as f:
            json.dump(config, f, indent=2, ensure_ascii=False)
        
        return config
    
    def get_agent(self, agent_id: str) -> Dict:
        """특정 에이전트 정보 조회"""
        for level_name, level_data in self.agents['levels'].items():
            for agent in level_data['agents']:
                if agent['id'] == agent_id:
                    return agent
        return {}
    
    def get_level_agents(self, level: int) -> List[Dict]:
        """레벨별 에이전트 목록 조회"""
        level_key = f'level_{level}_{"analysts" if level == 1 else "managers" if level == 2 else "pm"}'
        return self.agents['levels'].get(level_key, {}).get('agents', [])
    
    def list_all_agents(self) -> List[Dict]:
        """모든 에이전트 목록"""
        all_agents = []
        for level_name, level_data in self.agents['levels'].items():
            for agent in level_data['agents']:
                all_agents.append({
                    'id': agent['id'],
                    'name': agent['name'],
                    'role': agent['role'],
                    'level': agent['level'],
                    'status': agent['status']
                })
        return all_agents
    
    def generate_analysis_request(self, symbol: str, name: str) -> Dict:
        """분석 요청 생성"""
        return {
            'request_id': f"ANALYSIS_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
            'symbol': symbol,
            'name': name,
            'timestamp': datetime.now().isoformat(),
            'workflow': [
                {
                    'level': 1,
                    'agents': ['TECH_001', 'QUANT_001', 'QUAL_001', 'NEWS_001'],
                    'parallel': True
                },
                {
                    'level': 2,
                    'agents': ['SECTOR_001', 'MACRO_001'],
                    'parallel': True,
                    'depends_on': [1]
                },
                {
                    'level': 3,
                    'agents': ['PM_001'],
                    'parallel': False,
                    'depends_on': [1, 2]
                }
            ]
        }


def main():
    """메인 함수"""
    print("=" * 70)
    print("KStock Investment Agent Group - Configuration")
    print("=" * 70)
    
    group = InvestmentAgentGroup()
    
    print("\n📊 Agent Group Structure:")
    print("-" * 70)
    
    for level in [1, 2, 3]:
        agents = group.get_level_agents(level)
        level_names = {1: "Level 1 - Analysts", 2: "Level 2 - Managers", 3: "Level 3 - PM"}
        
        print(f"\n{level_names[level]} ({len(agents)} agents)")
        print("-" * 40)
        
        for agent in agents:
            print(f"  📌 {agent['name']}")
            print(f"     ID: {agent['id']}")
            print(f"     Role: {agent['role']}")
            print(f"     Specialty: {agent['specialty']}")
            print(f"     Weight: {agent['weight']}")
            print()
    
    print("=" * 70)
    print("\n✅ Agent group configuration saved!")
    print(f"   Config file: {AGENTS_CONFIG}")
    
    # 예시 분석 요청
    print("\n📋 Example Analysis Request:")
    example = group.generate_analysis_request('005930.KS', '삼성전자')
    print(json.dumps(example, indent=2, ensure_ascii=False))


if __name__ == '__main__':
    main()
