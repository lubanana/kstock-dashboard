"""
K-Stock Strategy Catalog Module
한국 주식 전략 카탈로그 모듈 - 번호로 쉽게 호출

Usage:
    from strategy_catalog import run_strategy, get_strategy_info, list_strategies
    
    # 전략 실행
    result = run_strategy('M03')  # S3: 신규 모멘텀
    
    # 전략 정보 확인
    info = get_strategy_info('V01')
    
    # 모든 전략 목록
    strategies = list_strategies()
"""

import subprocess
import json
import os
from typing import Dict, List, Optional, Union
from datetime import datetime

# 전략 카탈로그 정의
STRATEGY_CATALOG = {
    # P 시리즈 - Pivot Point
    'P01': {
        'name': '피벗 포인트 돌파',
        'category': 'Pivot',
        'description': '20일 고점 돌파 + 거래량 급증',
        'file': 'pivot_strategy.py',
        'type': 'scanner',
        'criteria': ['20일 고점 돌파', '거래량 1.5배+'],
        'params': {'lookback': 20, 'volume_threshold': 1.5}
    },
    
    # B 시리즈 - Buy Strength
    'B01': {
        'name': 'Buy Strength A등급',
        'category': 'Buy Strength',
        'description': '추세+모멘텀+거래량 80점+',
        'file': 'buy_strength_scanner.py',
        'type': 'scanner',
        'criteria': ['추세 40점', '모멘텀 30점', '거래량 30점'],
        'params': {'min_score': 80, 'min_amount': 1e9, 'min_price': 1000}
    },
    'B02': {
        'name': 'Buy Strength 월간',
        'category': 'Buy Strength',
        'description': '월간 누적 신호 분석',
        'file': 'monthly_report_generator.py',
        'type': 'analyzer',
        'criteria': ['일별 스캔 집계', '빈도 분석', '수익률 추적'],
        'params': {'days': 20}
    },
    
    # S 시리즈 - SEPA/VCP
    'S01': {
        'name': 'SEPA 트렌드 템플릿',
        'category': 'SEPA',
        'description': 'Mark Minervini 8가지 추세 기준',
        'file': 'sepa_vcp_strategy.py',
        'type': 'scanner',
        'criteria': ['주가>MA150', 'MA150>MA200', 'MA200상승', '52주고점25%이내', 'RS상위25%'],
        'params': {'min_data_days': 200}
    },
    'S02': {
        'name': 'VCP 패턴',
        'category': 'SEPA',
        'description': '변동성 수축 패턴 감지',
        'file': 'sepa_vcp_visualizer.py',
        'type': 'visualizer',
        'criteria': ['2-4회 수축', '폭/기간 감소', '거래량 감소'],
        'params': {'min_contractions': 2, 'max_contractions': 4}
    },
    'S03': {
        'name': 'VCP + 피벗',
        'category': 'SEPA',
        'description': 'VCP + 피벗 라인 돌파',
        'file': 'sepa_vcp_scanner.py',
        'type': 'scanner',
        'criteria': ['VCP 완성', '피벗 돌파', '거래량 급증'],
        'params': {'pivot_breakout': True, 'volume_surge': 1.5}
    },
    
    # M 시리즈 - Multi-Strategy
    'M01': {
        'name': 'S1: 거래대금 TOP20',
        'category': 'Multi-Strategy',
        'description': '20일 평균 거래대금 10억+',
        'file': 'multi_strategy_scanner.py',
        'type': 'sub_strategy',
        'criteria': ['20일 평균 거래대금 >= 10억'],
        'params': {'min_avg_amount': 1e9, 'days': 20},
        'backtest_result': {'win_rate': 0.65, 'profit': 0.08}
    },
    'M02': {
        'name': 'S2: 턴어라운드',
        'category': 'Multi-Strategy',
        'description': '60일 저점 대비 10% 반등 + RSI 40-60',
        'file': 'multi_strategy_scanner.py',
        'type': 'sub_strategy',
        'criteria': ['60일 저점 대비 10%+ 반등', 'RSI 40-60'],
        'params': {'rebound_pct': 10, 'rsi_range': [40, 60]},
        'backtest_result': {'win_rate': 0.30, 'profit': -0.05, 'note': '성능 저하, 제외 권장'}
    },
    'M03': {
        'name': 'S3: 신규 모멘텀',
        'category': 'Multi-Strategy',
        'description': 'MACD > 0 + RSI > 50',
        'file': 'multi_strategy_scanner.py',
        'type': 'sub_strategy',
        'criteria': ['MACD > 0', 'RSI > 50'],
        'params': {'macd_positive': True, 'min_rsi': 50},
        'backtest_result': {'win_rate': 0.68, 'profit': 0.12}
    },
    'M04': {
        'name': 'S4: 2000억 돌파',
        'category': 'Multi-Strategy',
        'description': '당일 거래대금 2000억+',
        'file': 'multi_strategy_scanner.py',
        'type': 'sub_strategy',
        'criteria': ['당일 거래대금 >= 2000억'],
        'params': {'min_amount': 2e10},
        'backtest_result': {'win_rate': 0.45, 'profit': -0.02, 'note': '조합용만 권장'}
    },
    'M05': {
        'name': 'S5: MA200 상승세',
        'category': 'Multi-Strategy',
        'description': '주가 > MA200 + MA200 상승',
        'file': 'multi_strategy_scanner.py',
        'type': 'sub_strategy',
        'criteria': ['주가 > MA200', 'MA200 상승 추세'],
        'params': {'ma_period': 200},
        'backtest_result': {'win_rate': 0.62, 'profit': 0.05}
    },
    'M10': {
        'name': '멀티전략 종합',
        'category': 'Multi-Strategy',
        'description': '5가지 전략 조합 스캔',
        'file': 'multi_strategy_scanner.py',
        'type': 'scanner',
        'criteria': ['5가지 전략 조합 평가'],
        'params': {'strategies': ['M01', 'M02', 'M03', 'M04', 'M05']},
        'note': '2개 이상 충족 권장'
    },
    'M11': {
        'name': '멀티전략 백테스트',
        'category': 'Multi-Strategy',
        'description': '2026.01~03 과거 검증',
        'file': 'multi_strategy_backtest.py',
        'type': 'backtest',
        'criteria': ['시뮬레이션', '수익률 검증', 'MDD 계산'],
        'params': {'start': '2026-01-01', 'end': '2026-03-17'},
        'backtest_result': {
            'total_return': 0.0949,
            'win_rate': 0.387,
            'mdd': -0.1377,
            'avg_hold_days': 5.6,
            'best_combo': 'S1+S3 (71.4%)'
        }
    },
    
    # V 시리즈 - Buffett Value
    'V01': {
        'name': '그레이엄 순유동자산',
        'category': 'Value',
        'description': '저평가 + 거래량 증가',
        'file': 'buffett_integrated_scanner.py',
        'type': 'sub_strategy',
        'criteria': ['P/B < 1.5', '거래량 1.5배+', '3개월 수익률 양수'],
        'params': {'max_pb': 1.5, 'min_volume_ratio': 1.5},
        'backtest_result': {'total_return': 1.14, 'cagr': 0.402, 'mdd': 0.0, 'win_rate': 0.706}
    },
    'V02': {
        'name': '퀄리티 적정가',
        'category': 'Value',
        'description': 'ROE 15%+ + Moat + 적정가',
        'file': 'buffett_integrated_scanner.py',
        'type': 'sub_strategy',
        'criteria': ['ROE >= 15%', 'Moat 존재', '적정가 내'],
        'params': {'min_roe': 15, 'fair_value_check': True},
        'backtest_result': {'total_return': 0.988, 'cagr': 0.357, 'mdd': -0.04, 'win_rate': 0.46}
    },
    'V03': {
        'name': '배당성장',
        'category': 'Value',
        'description': '변동성 < 40% + 안정적 성장',
        'file': 'buffett_integrated_scanner.py',
        'type': 'sub_strategy',
        'criteria': ['변동성 < 40%', '안정적 성장', '배당 안정성'],
        'params': {'max_volatility': 0.40},
        'backtest_result': {'total_return': 0.563, 'cagr': 0.219, 'mdd': -0.034, 'win_rate': 0.76}
    },
    'V10': {
        'name': '버핏 3전략 종합',
        'category': 'Value',
        'description': '그레이엄+퀄리티+배당 동시 실행',
        'file': 'buffett_integrated_scanner.py',
        'type': 'scanner',
        'criteria': ['3가지 전략 동시 평가'],
        'params': {'strategies': ['V01', 'V02', 'V03']}
    },
    'V11': {
        'name': '버핏 백테스트',
        'category': 'Value',
        'description': '2024.01~2026.03 27개월 검증',
        'file': 'buffett_backtester.py',
        'type': 'backtest',
        'criteria': ['월별 리밸런싱', '수익률 추적'],
        'params': {'start': '2024-01-01', 'end': '2026-03-17', 'rebalance': 'monthly'},
        'backtest_result': {
            'total_return': {'V01': 1.14, 'V02': 0.988, 'V03': 0.563},
            'period_months': 27
        }
    },
    
    # N 시리즈 - NPS Value (국민연금 패턴)
    'N01': {
        'name': 'NPS 저평가 우량주',
        'category': 'NPS Value',
        'description': '국민연금 장기 가치 투자 패턴 복제',
        'file': 'nps_value_scanner_real.py',
        'type': 'scanner',
        'criteria': [
            '3년 연속 ROE 10~15%',
            'PBR ≤ 1.0 or 업종 하위 30%',
            'NPS 지분 ≥ 5%',
            '배당성향 20~50%'
        ],
        'params': {
            'roe_min': 0.10,
            'roe_max': 0.15,
            'pbr_max': 1.0,
            'nps_min': 0.05,
            'payout_range': [0.20, 0.50],
            'min_market_cap': 1000e8,
            'exclude_financials': True
        },
        'scoring_weights': {
            'roe': 0.40,
            'dividend': 0.25,
            'valuation': 0.20,
            'nps': 0.15
        }
    },
    'N02': {
        'name': 'NPS 알고리즘 문서',
        'category': 'NPS Value',
        'description': '4-Filter 알고리즘 설계 문서',
        'file': 'nps_scanner_algorithm.py',
        'type': 'documentation',
        'criteria': ['알고리즘 설계', '필터링 로직', '스코어링 가중치'],
        'note': '설계 문서 참조용'
    }
}


def list_strategies(category: Optional[str] = None) -> List[Dict]:
    """
    모든 전략 목록 반환
    
    Args:
        category: 'Pivot', 'Buy Strength', 'SEPA', 'Multi-Strategy', 'Value' 중 선택
        
    Returns:
        전략 정보 리스트
    """
    strategies = []
    for code, info in STRATEGY_CATALOG.items():
        if category is None or info['category'] == category:
            strategies.append({
                'code': code,
                'name': info['name'],
                'category': info['category'],
                'description': info['description'],
                'type': info['type']
            })
    return strategies


def get_strategy_info(code: str) -> Dict:
    """
    특정 전략의 상세 정보 반환
    
    Args:
        code: 전략 코드 (예: 'M03', 'V01')
        
    Returns:
        전략 상세 정보
    """
    if code not in STRATEGY_CATALOG:
        raise ValueError(f"Unknown strategy code: {code}. Use list_strategies() to see available codes.")
    
    return STRATEGY_CATALOG[code]


def run_strategy(code: str, **kwargs) -> Dict:
    """
    전략 실행
    
    Args:
        code: 전략 코드
        **kwargs: 전략별 추가 파라미터
        
    Returns:
        실행 결과
    """
    if code not in STRATEGY_CATALOG:
        raise ValueError(f"Unknown strategy code: {code}")
    
    info = STRATEGY_CATALOG[code]
    print(f"🚀 [{code}] {info['name']} 실행 중...")
    print(f"   설명: {info['description']}")
    print(f"   파일: {info['file']}")
    
    # 파라미터 병합
    params = {**info.get('params', {}), **kwargs}
    
    # 실행 로직 (실제 구현시 각 파일 import 후 실행)
    result = {
        'code': code,
        'name': info['name'],
        'params': params,
        'status': 'ready',
        'timestamp': datetime.now().isoformat(),
        'note': '실제 실행은 해당 Python 파일을 직접 실행하세요'
    }
    
    # 백테스트 결과가 있는 경우 추가
    if 'backtest_result' in info:
        result['backtest'] = info['backtest_result']
    
    print(f"✅ [{code}] 실행 준비 완료")
    return result


def run_sequential(codes: List[str], delay: int = 1) -> List[Dict]:
    """
    여러 전략 순차 실행
    
    Args:
        codes: 전략 코드 리스트 (예: ['M01', 'M02', 'M03'])
        delay: 전략 간 딜레이 (초)
        
    Returns:
        실행 결과 리스트
    """
    results = []
    print(f"🔄 {len(codes)}개 전략 순차 실행 시작...")
    print("=" * 60)
    
    for i, code in enumerate(codes, 1):
        print(f"\n[{i}/{len(codes)}] 실행 중...")
        result = run_strategy(code)
        results.append(result)
        
        if i < len(codes) and delay > 0:
            print(f"   {delay}초 대기...")
            import time
            time.sleep(delay)
    
    print("\n" + "=" * 60)
    print(f"✅ 모든 전략 실행 완료 ({len(codes)}개)")
    return results


def get_best_combinations() -> List[Dict]:
    """
    백테스트 기반 최고 성능 조합 반환
    
    Returns:
        추천 조합 리스트
    """
    return [
        {
            'name': '고승률 모멘텀',
            'codes': ['M01', 'M03'],
            'win_rate': 0.714,
            'profit': 0.15,
            'description': '거래대금 + 모멘텀 조합 (71.4% 승률)'
        },
        {
            'name': '균형 잡힌 가치',
            'codes': ['V01', 'V02'],
            'win_rate': 0.58,
            'profit': 1.06,
            'description': '그레이엄 + 퀄리티 (CAGR 38%)'
        },
        {
            'name': '안정적 배당',
            'codes': ['V03', 'B01'],
            'win_rate': 0.76,
            'profit': 0.35,
            'description': '배당성장 + Buy Strength A등급'
        }
    ]


def print_strategy_table():
    """전략 목록 테이블 출력"""
    print("\n" + "=" * 80)
    print("K-Stock Strategy Catalog")
    print("=" * 80)
    
    categories = {}
    for code, info in STRATEGY_CATALOG.items():
        cat = info['category']
        if cat not in categories:
            categories[cat] = []
        categories[cat].append((code, info['name'], info['type']))
    
    for cat, items in categories.items():
        print(f"\n📁 {cat}")
        print("-" * 80)
        for code, name, type_ in items:
            print(f"  {code:4} | {name:25} | {type_}")
    
    print("\n" + "=" * 80)


# CLI 지원
if __name__ == '__main__':
    import sys
    
    if len(sys.argv) < 2:
        print_strategy_table()
        print("\n사용법:")
        print("  python strategy_catalog.py list")
        print("  python strategy_catalog.py info <code>")
        print("  python strategy_catalog.py run <code>")
        print("  python strategy_catalog.py sequential <code1,code2,...>")
        print("\n예시:")
        print("  python strategy_catalog.py info M03")
        print("  python strategy_catalog.py run V01")
        print("  python strategy_catalog.py sequential M01,M02,M03")
    
    elif sys.argv[1] == 'list':
        print_strategy_table()
    
    elif sys.argv[1] == 'info' and len(sys.argv) > 2:
        code = sys.argv[2]
        info = get_strategy_info(code)
        print(f"\n📊 [{code}] {info['name']}")
        print(f"   설명: {info['description']}")
        print(f"   파일: {info['file']}")
        print(f"   기준: {', '.join(info['criteria'])}")
        if 'backtest_result' in info:
            print(f"   백테스트: {info['backtest_result']}")
    
    elif sys.argv[1] == 'run' and len(sys.argv) > 2:
        code = sys.argv[2]
        result = run_strategy(code)
        print(f"\n결과: {json.dumps(result, indent=2, ensure_ascii=False)}")
    
    elif sys.argv[1] == 'sequential' and len(sys.argv) > 2:
        codes = sys.argv[2].split(',')
        results = run_sequential(codes)
        print(f"\n총 {len(results)}개 전략 실행 완료")
