#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
버핏 가치투자 전략 비교 및 선택 가이드
========================================

3가지 전략의 장단점 비교와 선택 기준
"""

def compare_strategies():
    """
    3가지 전략 비교
    """
    print("=" * 80)
    print("📊 버핏 가치투자 전략 3가지 비교")
    print("=" * 80)
    
    strategies = {
        '전략1': {
            'name': '그레이엄 순유동자산',
            'file': 'buffett_strategy_1_graham_netnet.py',
            'core': '10센트에 1달러짜리 사기',
            'focus': '자산 가치',
            'risk_level': '중',
            'return_potential': '높음 (50%+ 가능)',
            'time_horizon': '2-3년',
            'diversification': '20종목+ 필수',
            'best_for': '단기 수익, 깊은 가치추구',
            'pros': [
                '강력한 마진 오브 세이프티',
                '심리적 안정감 (자산 밑천)',
                '단기 상승 잠재력 큼',
                '시장 하락 시 방어력 우수'
            ],
            'cons': [
                '좋은 종목 찾기 어려움',
                '턴어라운드 실패 리스크',
                '현금흐름 부족 종목 다수',
                '장기 보유시 수익률 저하'
            ],
            'key_metrics': 'P/NCAV < 1, P/B < 1',
            'buffett_quote': '"10센트에 1달러짜리를 사라"'
        },
        '전략2': {
            'name': '좋은 회사 적정가',
            'file': 'buffett_strategy_2_quality_fairprice.py',
            'core': '해자 있는 좋은 회사를 싸게',
            'focus': '수익성 + 성장성',
            'risk_level': '중-낮음',
            'return_potential': '중-높음 (15-20%/년)',
            'time_horizon': '5-10년',
            'diversification': '10-15종목',
            'best_for': '중장기 성장, 퀄리티 중시',
            'pros': [
                '지속 가능한 경쟁 우위',
                '복리 효과 극대화',
                '경기 침체에도 회복력',
                '관리가 쉬움 (좋은 회사)'
            ],
            'cons': [
                '매수 타이밍 잡기 어려움',
                '밸류에이션 고평가 우려',
                '인내심 필요 (장기)',
                '기회가 제한적'
            ],
            'key_metrics': 'ROE > 15%, PEG < 1',
            'buffett_quote': '"훌륭한 회사를 합리적인 가격에"'
        },
        '전략3': {
            'name': '현금창출 머신 배당성장',
            'file': 'buffett_strategy_3_dividend_machine.py',
            'core': '꾸준한 현금흐름 + 배당성장',
            'focus': '현금창출 + 배당',
            'risk_level': '낮음',
            'return_potential': '중 (10-12%/년)',
            'time_horizon': '10년+ (영구)',
            'diversification': '15-20종목',
            'best_for': '안정적 소득, 은퇴 준비',
            'pros': [
                '꾸준한 현금흐름',
                '심리적 안정 (배당)',
                '인플레이션 헤지',
                '복리 + 배당 재투자',
                '은퇴 후 생활비 마련'
            ],
            'cons': [
                '단기 수익률 낮음',
                '금리 상승 시 타격',
                '성장성 제한적',
                '세금 이슈 (배당소득)'
            ],
            'key_metrics': '배당수익률 > 2.5%, FCF Yield > 5%',
            'buffett_quote': '"현금창출 머신을 모아라"'
        }
    }
    
    # 전략별 요약
    for key, strategy in strategies.items():
        print(f"\n{'='*80}")
        print(f"{key}: {strategy['name']}")
        print(f"{'='*80}")
        print(f"\n💡 핵심 철학: {strategy['core']}")
        print(f"🎯 집중 가치: {strategy['focus']}")
        print(f"⚠️  리스크 수준: {strategy['risk_level']}")
        print(f"📈 예상 수익률: {strategy['return_potential']}")
        print(f"⏰ 권장 보유기간: {strategy['time_horizon']}")
        print(f"📊 분산 정도: {strategy['diversification']}")
        print(f"👤 적합한 투자자: {strategy['best_for']}")
        print(f"📏 핵심 지표: {strategy['key_metrics']}")
        print(f"💬 버핏 명언: {strategy['buffett_quote']}")
        
        print(f"\n✅ 장점:")
        for pro in strategy['pros']:
            print(f"   • {pro}")
        
        print(f"\n❌ 단점:")
        for con in strategy['cons']:
            print(f"   • {con}")
    
    return strategies


def selection_guide():
    """
    선택 가이드
    """
    print("\n" + "=" * 80)
    print("🎯 나에게 맞는 전략 선택 가이드")
    print("=" * 80)
    
    questions = [
        {
            'q': 'Q1. 투자 기간은?',
            'options': {
                'A': ('2-3년', ['전략1']),
                'B': ('5-10년', ['전략2']),
                'C': ('10년+ 또는 영구', ['전략3'])
            }
        },
        {
            'q': 'Q2. 목표 수익률은?',
            'options': {
                'A': ('연 20% 이상 (고위험)', ['전략1']),
                'B': ('연 15-20% (중위험)', ['전략2']),
                'C': ('연 10-12% + 안정적 소득 (저위험)', ['전략3'])
            }
        },
        {
            'q': 'Q3. 현재 투자 목적은?',
            'options': {
                'A': ('자본 급성장', ['전략1', '전략2']),
                'B': ('자산 보존 + 성장', ['전략2']),
                'C': ('안정적 소득/은퇴', ['전략3']),
                'D': ('심리적 안정 + 수익', ['전략3', '전략2'])
            }
        },
        {
            'q': 'Q4. 손실 감내 능력은?',
            'options': {
                'A': ('30% 손실도 감내', ['전략1']),
                'B': ('20% 까지', ['전략2']),
                'C': ('10% 미만', ['전략3'])
            }
        },
        {
            'q': 'Q5. 관리할 시간은?',
            'options': {
                'A': ('주 5시간+ (적극)', ['전략1']),
                'B': ('월 2-3시간 (보통)', ['전략2']),
                'C': ('최소 (수동)', ['전략3'])
            }
        }
    ]
    
    print("""
아래 질문에 답변핳면 가장 적합한 전략을 추천합니다:

Q1. 투자 기간은?
   A. 2-3년 (단기) → 전략1
   B. 5-10년 (중장기) → 전략2
   C. 10년+ 또는 영구 (장기) → 전략3

Q2. 목표 수익률은?
   A. 연 20% 이상 (고위험 고수익) → 전략1
   B. 연 15-20% (중위험 중수익) → 전략2
   C. 연 10-12% + 안정적 소득 (저위험) → 전략3

Q3. 현재 투자 목적은?
   A. 자본 급성장 → 전략1, 전략2
   B. 자산 보존 + 성장 → 전략2
   C. 은퇴 후 안정적 소득 → 전략3
   D. 심리적 안정 + 수익 → 전략3, 전략2

Q4. 손실 감내 능력은?
   A. 30% 손실도 감내 가능 → 전략1
   B. 20%까지 → 전략2
   C. 10% 미만 → 전략3

Q5. 관리할 시간은?
   A. 주 5시간+ (적극적) → 전략1
   B. 월 2-3시간 (보통) → 전략2
   C. 최소한만 (수동적) → 전략3
""")


def recommendation():
    """
    추천 조합
    """
    print("\n" + "=" * 80)
    print("💎 추천 포트폴리오 조합")
    print("=" * 80)
    
    portfolios = {
        '공격형 (30대 이하)': {
            'desc': '높은 수익 추구, 손실 감내 가능',
            'allocation': {
                '전략1 (순유동자산)': '40%',
                '전략2 (퀄리티)': '40%',
                '전략3 (배당)': '10%',
                '현금': '10%'
            },
            'expected_return': '연 18-25%',
            'risk': '높음'
        },
        '균형형 (30-50대)': {
            'desc': '성장과 안정의 균형',
            'allocation': {
                '전략1 (순유동자산)': '20%',
                '전략2 (퀄리티)': '50%',
                '전략3 (배당)': '20%',
                '현금': '10%'
            },
            'expected_return': '연 12-18%',
            'risk': '중간'
        },
        '안정형 (50대 이상)': {
            'desc': '자산 보존 + 소득',
            'allocation': {
                '전략1 (순유동자산)': '10%',
                '전략2 (퀄리티)': '30%',
                '전략3 (배당)': '50%',
                '현금': '10%'
            },
            'expected_return': '연 8-12%',
            'risk': '낮음'
        }
    }
    
    for name, portfolio in portfolios.items():
        print(f"\n{'='*60}")
        print(f"📌 {name}")
        print(f"{'='*60}")
        print(f"설명: {portfolio['desc']}")
        print(f"예상 수익률: {portfolio['expected_return']}")
        print(f"리스크 수준: {portfolio['risk']}")
        print("\n배분:")
        for strategy, ratio in portfolio['allocation'].items():
            print(f"   • {strategy}: {ratio}")


def next_steps():
    """
    다음 단계
    """
    print("\n" + "=" * 80)
    print("🚀 다음 단계")
    print("=" * 80)
    
    print("""
1️⃣  선택한 전략 실행파일 실행
    $ python3 buffett_strategy_X_[선택].py

2️⃣  실제 데이터 연동
    - 재무제표 DB 연결
    - 실시간 주가 연동
    - 알림 시스템 설정

3️⃣  백테스팅
    - 과거 10년 데이터로 검증
    - MDD, 샤프비율 계산
    - 리밸런싱 주기 설정

4️⃣  실전 투자
    - 소액으로 테스트 (3개월)
    - 매매 일지 작성
    - 분기별 리밸런싱

5️⃣  장기 모니터링
    - 자동 스캔 스케줄링
    - 포트폴리오 리포트 생성
    - 버핏 옥션 참고
""")


def main():
    """
    메인
    """
    # 전략 비교
    strategies = compare_strategies()
    
    # 선택 가이드
    selection_guide()
    
    # 추천 조합
    recommendation()
    
    # 다음 단계
    next_steps()
    
    print("\n" + "=" * 80)
    print("📝 최종 추천")
    print("=" * 80)
    print("""
💡 처음 시작하는 경우:
   → "전략2: 좋은 회사 적정가" 추천
   → 이유: 성공 확률 높음, 관리 용이, 버핏 핵심 철학

💡 적극적 투자자:
   → "전략1: 순유동자산" + "전략2" 조합
   → 이유: 단기 수익 + 중장기 성장 동시 추구

💡 은퇴 준비 또는 안정 선호:
   → "전략3: 배당성장" 추천
   → 이유: 심리적 안정, 꾸준한 현금흐름

💡 최고의 조합 (균형잡힌):
   → 전략2 (50%) + 전략3 (40%) + 현금 (10%)
   → 이유: 성장성 + 소득 + 유연성
""")


if __name__ == '__main__':
    main()
