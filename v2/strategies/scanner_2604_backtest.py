#!/usr/bin/env python3
"""
2604 Scanner Quick Backtest
빠른 백테스트 실행 (최근 30일)
"""

import sys
sys.path.insert(0, '/root/.openclaw/workspace/strg')

import pandas as pd
from datetime import datetime, timedelta

from v2.strategies.scanner_2604 import Scanner2604
from v2.core.data_manager import DataManager


def quick_backtest(days: int = 30, min_score: float = 75.0):
    """
    빠른 백테스트
    
    Args:
        days: 백테스트 일수
        min_score: 최소 진입 점수
    """
    print("=" * 80)
    print("📊 2604 스캐너 빠른 백테스트")
    print("=" * 80)
    
    end_date = datetime.now()
    start_date = end_date - timedelta(days=days)
    
    print(f"기간: {start_date.strftime('%Y-%m-%d')} ~ {end_date.strftime('%Y-%m-%d')}")
    print(f"진입 점수: {min_score}+\n")
    
    scanner = Scanner2604(use_krx=False)
    dm = DataManager()
    
    # 거래일 생성
    date_range = pd.bdate_range(start=start_date, end=end_date)
    
    results = []
    for i, date in enumerate(date_range):
        date_str = date.strftime('%Y-%m-%d')
        
        try:
            signals = scanner.run(dm, date_str)
            
            if signals:
                for signal in signals:
                    results.append({
                        'date': date_str,
                        'code': signal.code,
                        'name': signal.name,
                        'score': signal.score,
                        'price': signal.metadata.get('price', 0),
                        'volume': signal.metadata.get('scores', {}).get('volume', 0),
                        'technical': signal.metadata.get('scores', {}).get('technical', 0),
                        'fibonacci': signal.metadata.get('scores', {}).get('fibonacci', 0),
                    })
            
            # 진행 상황 출력 (5일마다)
            if (i + 1) % 5 == 0 or i == 0:
                print(f"   {date_str}: {len(signals)}개 신호 (누적: {len(results)}개)")
                
        except Exception as e:
            print(f"   {date_str}: 오류 - {str(e)[:50]}")
            continue
    
    # 결과 요약
    print("\n" + "=" * 80)
    print("📈 백테스트 결과 요약")
    print("=" * 80)
    print(f"총 거래일: {len(date_range)}일")
    print(f"총 신호: {len(results)}개")
    print(f"평균 일일 신호: {len(results)/len(date_range):.1f}개")
    
    if results:
        df = pd.DataFrame(results)
        
        print(f"\n점수 분포:")
        print(f"   90점+: {len(df[df['score'] >= 90])}개")
        print(f"   85-89점: {len(df[(df['score'] >= 85) & (df['score'] < 90)])}개")
        print(f"   80-84점: {len(df[(df['score'] >= 80) & (df['score'] < 85)])}개")
        print(f"   75-79점: {len(df[(df['score'] >= 75) & (df['score'] < 80)])}개")
        
        print(f"\n평균 점수: {df['score'].mean():.1f}")
        print(f"최고 점수: {df['score'].max():.1f}")
        print(f"최저 점수: {df['score'].min():.1f}")
        
        # 중복 종목 확인
        unique_stocks = df['code'].nunique()
        print(f"\n고유 종목: {unique_stocks}개")
        print(f"평균 재진입: {len(results)/unique_stocks:.1f}회/종목")
        
        # TOP 10 종목
        print(f"\n🏆 TOP 10 (점수 기준):")
        top10 = df.nlargest(10, 'score')
        for i, row in top10.iterrows():
            print(f"   {row['name']} ({row['code']}): {row['score']:.1f}점 - {row['date']}")
    
    return results


if __name__ == '__main__':
    import sys
    days = int(sys.argv[1]) if len(sys.argv) > 1 else 30
    min_score = float(sys.argv[2]) if len(sys.argv) > 2 else 75.0
    
    quick_backtest(days, min_score)
