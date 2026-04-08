#!/usr/bin/env python3
"""
2604 스캐너 최적화 백테스트
- 로컬DB만 사용
- 영업일 기준 처리
- 배치 처리로 속도 개선
"""

import sys
sys.path.insert(0, '/root/.openclaw/workspace/strg')

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import List, Dict, Tuple
from dataclasses import dataclass

from v2.strategies.scanner_2604 import Scanner2604
from v2.core.data_manager import DataManager


@dataclass
class BacktestResult:
    """백테스트 결과"""
    date: str
    total_signals: int
    avg_score: float
    max_score: float
    min_score: float
    stocks: List[Dict]


def get_business_days(start_date: str, end_date: str) -> List[str]:
    """영업일 리스트 생성 (주말 제외)"""
    start = datetime.strptime(start_date, '%Y-%m-%d')
    end = datetime.strptime(end_date, '%Y-%m-%d')
    
    dates = []
    current = start
    while current <= end:
        # 주말 제외 (월=0, 일=6)
        if current.weekday() < 5:
            dates.append(current.strftime('%Y-%m-%d'))
        current += timedelta(days=1)
    
    return dates


def run_backtest(start_date: str, end_date: str, min_score: float = 75.0) -> Dict:
    """
    2604 스캐너 백테스트 실행
    
    Args:
        start_date: 시작일 (YYYY-MM-DD)
        end_date: 종료일 (YYYY-MM-DD)
        min_score: 최소 진입 점수
    
    Returns:
        백테스트 결과 딕셔너리
    """
    print("=" * 80)
    print("📊 2604 스캐너 백테스트 (최적화 버전)")
    print("=" * 80)
    
    # 영업일 계산
    business_days = get_business_days(start_date, end_date)
    print(f"\n📅 테스트 기간: {start_date} ~ {end_date}")
    print(f"   영업일 수: {len(business_days)}일")
    print(f"   진입 점수: {min_score}+")
    print()
    
    # 스캐너 초기화
    scanner = Scanner2604(use_krx=False)
    dm = DataManager()
    
    # 결과 저장
    all_results = []
    all_signals = []
    
    for date in business_days:
        print(f"🔍 {date} 처리 중...", end=" ")
        
        # 데이터 확인
        conn = dm._get_connection()
        count_df = pd.read_sql_query(
            f"SELECT COUNT(*) as cnt FROM price_data WHERE date='{date}'", 
            conn
        )
        conn.close()
        
        count = count_df.iloc[0]['cnt']
        
        if count < 3000:
            print(f"⚠️ 데이터 부족 ({count}종목) - 스킵")
            continue
        
        # 스캔 실행
        try:
            signals = scanner.run(dm, date)
            
            # 점수 필터링
            filtered = [s for s in signals if s.score >= min_score]
            
            print(f"✅ {len(filtered)}개 신호 ({count}종목 중)")
            
            if filtered:
                scores = [s.score for s in filtered]
                result = BacktestResult(
                    date=date,
                    total_signals=len(filtered),
                    avg_score=sum(scores) / len(scores),
                    max_score=max(scores),
                    min_score=min(scores),
                    stocks=[{
                        'code': s.code,
                        'name': s.name,
                        'score': s.score,
                        'price': s.price,
                        'volume_score': s.volume_score,
                        'technical_score': s.technical_score,
                        'fib_score': s.fib_score,
                        'market_score': s.market_score,
                        'momentum_score': s.momentum_score
                    } for s in filtered[:5]]  # 상위 5개만 저장
                )
                all_results.append(result)
                all_signals.extend([(date, s) for s in filtered])
                
                # 상위 3개 출력
                for s in filtered[:3]:
                    print(f"      → {s.name} ({s.code}): {s.score:.1f}점")
                    
        except Exception as e:
            print(f"❌ 오류: {e}")
            continue
    
    # 결과 요약
    print("\n" + "=" * 80)
    print("📈 백테스트 결과 요약")
    print("=" * 80)
    
    total_days = len([r for r in all_results if r.total_signals > 0])
    total_signals = len(all_signals)
    
    print(f"\n기간: {start_date} ~ {end_date} ({len(business_days)}영업일)")
    print(f"신호 발생 일수: {total_days}일")
    print(f"총 신호 수: {total_signals}개")
    
    if total_days > 0:
        print(f"평균 일일 신호: {total_signals/total_days:.1f}개")
    
    if all_signals:
        scores = [s.score for _, s in all_signals]
        
        print(f"\n📊 점수 분포:")
        print(f"   85점+: {len([s for s in scores if s >= 85])}개")
        print(f"   80-84점: {len([s for s in scores if 80 <= s < 85])}개")
        print(f"   75-79점: {len([s for s in scores if 75 <= s < 80])}개")
        print(f"   70-74점: {len([s for s in scores if 70 <= s < 75])}개")
        
        print(f"\n📈 점수 통계:")
        print(f"   평균: {sum(scores)/len(scores):.1f}")
        print(f"   최고: {max(scores):.1f}")
        print(f"   최저: {min(scores):.1f}")
        print(f"   중간: {sorted(scores)[len(scores)//2]:.1f}")
        
        # 고유 종목
        unique_codes = set(s.code for _, s in all_signals)
        print(f"\n🎯 고유 종목: {len(unique_codes)}개")
        
        # 일별 상세
        print(f"\n📅 일별 신호 현황:")
        for r in all_results:
            if r.total_signals > 0:
                print(f"   {r.date}: {r.total_signals}개 (평균 {r.avg_score:.1f}점)")
    
    print("=" * 80)
    
    # 결과 저장
    return {
        'period': f"{start_date} ~ {end_date}",
        'business_days': business_days,
        'total_days': total_days,
        'total_signals': total_signals,
        'avg_signals_per_day': total_signals / total_days if total_days > 0 else 0,
        'unique_stocks': len(set(s.code for _, s in all_signals)) if all_signals else 0,
        'score_stats': {
            'avg': sum(scores) / len(scores) if all_signals else 0,
            'max': max(scores) if all_signals else 0,
            'min': min(scores) if all_signals else 0
        },
        'daily_results': all_results,
        'all_signals': all_signals
    }


if __name__ == "__main__":
    import json
    
    # 백테스트 실행
    result = run_backtest(
        start_date="2026-03-27",
        end_date="2026-04-07",
        min_score=75.0
    )
    
    # JSON 저장
    output_file = "/root/.openclaw/workspace/strg/reports/2604_backtest_result.json"
    
    # dataclass 직렬화
    class DateTimeEncoder(json.JSONEncoder):
        def default(self, obj):
            if isinstance(obj, BacktestResult):
                return obj.__dict__
            return super().default(obj)
    
    # signals는 제외하고 저장 (용량 문제)
    save_data = {k: v for k, v in result.items() if k != 'all_signals'}
    
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(save_data, f, ensure_ascii=False, indent=2, cls=DateTimeEncoder)
    
    print(f"\n💾 결과 저장: {output_file}")
