#!/usr/bin/env python3
"""
2604 V2 백테스트 엔진
2026년 4월 8일 개선판

특징:
- 영업일 기준 처리
- 로컬DB만 사용 (KRX API 미사용)
- 데이터 품질 검증 포함
- 상세 결과 저장
"""

import sys
sys.path.insert(0, '/root/.openclaw/workspace/strg')

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import List, Dict, Tuple
from dataclasses import dataclass, asdict
import json

from v2.strategies.scanner_2604_v2 import Scanner2604V2
from v2.core.data_manager import DataManager


@dataclass
class DailyResult:
    """일별 결과"""
    date: str
    total_signals: int
    avg_score: float
    max_score: float
    min_score: float
    signals: List[Dict]


def get_business_days(start_date: str, end_date: str, dm: DataManager) -> List[str]:
    """DB에 실제로 데이터가 있는 영업일만 반환"""
    conn = dm._get_connection()
    
    # DB에 있는 날짜 확인
    df = pd.read_sql_query('''
        SELECT DISTINCT date, COUNT(*) as count
        FROM price_data
        WHERE date BETWEEN ? AND ?
        GROUP BY date
        HAVING count >= 3000
        ORDER BY date
    ''', conn, params=(start_date, end_date))
    
    conn.close()
    
    return df['date'].tolist()


def run_backtest_v2(start_date: str, end_date: str, min_score: float = 75.0) -> Dict:
    """
    2604 V2 백테스트 실행
    
    Args:
        start_date: 시작일 (YYYY-MM-DD)
        end_date: 종료일 (YYYY-MM-DD)
        min_score: 최소 진입 점수
    
    Returns:
        백테스트 결과 딕셔너리
    """
    print("=" * 80)
    print("📊 2604 V2 백테스트 (개선판)")
    print("=" * 80)
    
    # 데이터 준비
    dm = DataManager()
    business_days = get_business_days(start_date, end_date, dm)
    
    print(f"\n📅 테스트 기간: {start_date} ~ {end_date}")
    print(f"   유효 영업일: {len(business_days)}일")
    print(f"   진입 점수: {min_score}+")
    print()
    
    # 스캐너 초기화
    scanner = Scanner2604V2(use_krx=False)
    
    # 결과 저장
    all_results = []
    all_signals = []
    
    for i, date in enumerate(business_days, 1):
        print(f"[{i}/{len(business_days)}] {date} 처리 중...", end=" ")
        
        try:
            signals = scanner.run(dm, date)
            
            # 점수 필터링
            filtered = [s for s in signals if s.score >= min_score]
            
            if filtered:
                scores = [s.score for s in filtered]
                result = DailyResult(
                    date=date,
                    total_signals=len(filtered),
                    avg_score=sum(scores) / len(scores),
                    max_score=max(scores),
                    min_score=min(scores),
                    signals=[{
                        'code': s.code,
                        'name': s.name,
                        'score': s.score,
                        'price': s.metadata.get('price', 0),
                        'reasons': s.reason[:3]
                    } for s in filtered]
                )
                all_results.append(result)
                all_signals.extend([(date, s) for s in filtered])
                
                print(f"✅ {len(filtered)}개 신호")
            else:
                print("⏭️ 0개 (신호 없음)")
                    
        except Exception as e:
            print(f"❌ 오류: {str(e)[:50]}")
            continue
    
    # 결과 요약
    print("\n" + "=" * 80)
    print("📈 백테스트 결과 요약")
    print("=" * 80)
    
    total_days = len([r for r in all_results if r.total_signals > 0])
    total_signals = sum(r.total_signals for r in all_results)
    
    print(f"\n기간: {start_date} ~ {end_date}")
    print(f"테스트 일수: {len(business_days)}일")
    print(f"신호 발생 일수: {total_days}일")
    print(f"총 신호 수: {total_signals}개")
    
    if total_days > 0:
        print(f"평균 일일 신호: {total_signals/total_days:.1f}개")
    
    if all_signals:
        scores = [s.score for _, s in all_signals]
        
        print(f"\n📊 점수 분포:")
        print(f"   90점+: {len([s for s in scores if s >= 90])}개")
        print(f"   85-89점: {len([s for s in scores if 85 <= s < 90])}개")
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
                top_stock = r.signals[0] if r.signals else {'name': '-', 'code': '-'}
                print(f"   {r.date}: {r.total_signals}개 (평균 {r.avg_score:.1f}점) | TOP: {top_stock['name']}({top_stock['score']:.0f}점)")
    
    print("=" * 80)
    
    # 결과 저장
    return {
        'period': f"{start_date} ~ {end_date}",
        'business_days': business_days,
        'total_days': len(business_days),
        'signal_days': total_days,
        'total_signals': total_signals,
        'avg_signals_per_day': total_signals / total_days if total_days > 0 else 0,
        'unique_stocks': len(set(s.code for _, s in all_signals)) if all_signals else 0,
        'score_stats': {
            'avg': sum(scores) / len(scores) if all_signals else 0,
            'max': max(scores) if all_signals else 0,
            'min': min(scores) if all_signals else 0
        },
        'daily_results': [asdict(r) for r in all_results]
    }


def save_results(result: Dict, output_dir: str = "/root/.openclaw/workspace/strg/reports"):
    """결과 저장"""
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    
    # JSON 저장
    json_file = f"{output_dir}/2604_v2_backtest_{timestamp}.json"
    with open(json_file, 'w', encoding='utf-8') as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
    
    print(f"\n💾 JSON 저장: {json_file}")
    
    # Markdown 리포트
    md_file = f"{output_dir}/2604_v2_backtest_{timestamp}.md"
    with open(md_file, 'w', encoding='utf-8') as f:
        f.write("# 2604 V2 백테스트 결과\n\n")
        f.write(f"**테스트 기간**: {result['period']}\n\n")
        f.write(f"**총 신호**: {result['total_signals']}개\n\n")
        f.write(f"**고유 종목**: {result['unique_stocks']}개\n\n")
        
        f.write("## 일별 결과\n\n")
        f.write("| 날짜 | 신호 수 | 평균 점수 | TOP 종목 |\n")
        f.write("|:---|---:|---:|:---|\n")
        
        for day in result['daily_results']:
            if day['total_signals'] > 0:
                top = day['signals'][0] if day['signals'] else {'name': '-', 'score': 0}
                f.write(f"| {day['date']} | {day['total_signals']} | {day['avg_score']:.1f} | {top['name']} ({top['score']:.0f}점) |\n")
    
    print(f"💾 Markdown 저장: {md_file}")
    
    return json_file, md_file


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='2604 V2 백테스트')
    parser.add_argument('--start', default='2026-03-27', help='시작일 (YYYY-MM-DD)')
    parser.add_argument('--end', default='2026-04-07', help='종료일 (YYYY-MM-DD)')
    parser.add_argument('--min-score', type=float, default=75.0, help='최소 진입 점수')
    
    args = parser.parse_args()
    
    # 백테스트 실행
    result = run_backtest_v2(args.start, args.end, args.min_score)
    
    # 결과 저장
    save_results(result)
