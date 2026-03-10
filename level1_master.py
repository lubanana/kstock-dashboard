#!/usr/bin/env python3
"""
Level 1 Master Runner
Level 1 에이전트 통합 실행기

Usage:
    python3 level1_master.py [command]
    
Commands:
    price_morning     - 아침 가격 수집 (08:00)
    price_afternoon   - 점심 가격 수집 (12:00)
    price_evening     - 저녁 가격 수집 (16:00)
    financial_2024    - 2024년 분기별 재무정보 수집
    consolidate       - 결과 취합 (70점 이상 필터링)
    full_daily        - 전체 일일 프로세스
"""

import sys
import os

# 경로 설정
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'agents'))

from level1_price_agent import DailyPriceCollector
from level1_financial_agent import QuarterlyFinancialCollector
from level1_consolidator import Level1Consolidator


def run_price_collection(slot: str):
    """가격 수집 실행"""
    print(f"\n{'='*60}")
    print(f"🚀 Level 1 Price Agent - {slot.upper()}")
    print(f"{'='*60}")
    
    collector = DailyPriceCollector()
    results, high_scores = collector.collect(slot)
    
    print(f"\n✅ {slot} 완료!")
    print(f"   총: {len(results)}개 종목")
    print(f"   고점수(≥70): {len(high_scores)}개 종목")
    
    if high_scores:
        print("\n📊 상위 5종목:")
        for s in sorted(high_scores, key=lambda x: x['score'], reverse=True)[:5]:
            print(f"   {s['name']}: {s['score']:.1f}pts")
    
    return results, high_scores


def run_financial_collection(year: str = '2024'):
    """재무정보 수집 실행"""
    print(f"\n{'='*60}")
    print(f"🚀 Level 1 Financial Agent - {year}")
    print(f"{'='*60}")
    
    api_key = os.environ.get('DART_API_KEY')
    if not api_key:
        print("❌ DART_API_KEY 환경변수가 필요합니다!")
        return None
    
    collector = QuarterlyFinancialCollector(api_key=api_key)
    results = collector.collect_year(year)
    
    success = len([r for r in results if r.get('status') == 'success'])
    print(f"\n✅ {year}년 분기별 재무정보 완료!")
    print(f"   성공: {success}/{len(results)}")
    
    return results


def run_consolidation(threshold: float = 70.0):
    """결과 취합 실행"""
    print(f"\n{'='*60}")
    print(f"🚀 Level 1 Consolidator (Threshold: {threshold})")
    print(f"{'='*60}")
    
    consolidator = Level1Consolidator(score_threshold=threshold)
    results = consolidator.consolidate()
    consolidator.print_top10(results)
    
    return results


def run_full_daily():
    """전체 일일 프로세스"""
    print("\n" + "="*60)
    print("🚀 Level 1 Full Daily Process")
    print("="*60)
    
    # 1. 가격 수집
    print("\n📌 Step 1: Price Collection")
    price_results, _ = run_price_collection('morning')
    
    # 2. 재무정보 확인 (이미 수집된 데이터 사용)
    print("\n📌 Step 2: Financial Data Check")
    if not os.path.exists('data/level1_quarterly.db'):
        print("   재무정보 DB 없음 → 수집 실행")
        run_financial_collection('2024')
    else:
        print("   ✅ 재무정보 DB 존재")
    
    # 3. 결과 취합
    print("\n📌 Step 3: Consolidation")
    top_stocks = run_consolidation(70.0)
    
    print("\n" + "="*60)
    print("✅ Full Daily Process Complete!")
    print(f"   상위 종목: {len(top_stocks)}개")
    print("="*60)
    
    return top_stocks


def main():
    """메인 실행"""
    if len(sys.argv) < 2:
        print(__doc__)
        print("\n사용 예시:")
        print("  python3 level1_master.py price_morning")
        print("  python3 level1_master.py consolidate")
        print("  python3 level1_master.py full_daily")
        return
    
    command = sys.argv[1]
    
    commands = {
        'price_morning': lambda: run_price_collection('morning'),
        'price_afternoon': lambda: run_price_collection('afternoon'),
        'price_evening': lambda: run_price_collection('evening'),
        'financial_2024': lambda: run_financial_collection('2024'),
        'consolidate': lambda: run_consolidation(70.0),
        'full_daily': run_full_daily,
    }
    
    if command in commands:
        try:
            commands[command]()
        except Exception as e:
            print(f"\n❌ Error: {e}")
            import traceback
            traceback.print_exc()
    else:
        print(f"❌ Unknown command: {command}")
        print(__doc__)


if __name__ == '__main__':
    main()
