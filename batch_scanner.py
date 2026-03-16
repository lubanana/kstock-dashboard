#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Batch Scanner for Historical Data
==================================
특정 기간 동안 매일 스캔을 실행하는 프로그램

Usage:
    python batch_scanner.py --start 2026-02-01 --end 2026-02-28 --market ALL
"""

import pandas as pd
from datetime import datetime, timedelta
from pathlib import Path
from enhanced_scanner import EnhancedScanner
import argparse


def scan_single_date(base_date: str, market: str = 'ALL', limit: int = None) -> pd.DataFrame:
    """
    특정 날짜에 대한 스캔 실행
    
    Parameters:
    -----------
    base_date : str
        스캔 기준일 (YYYY-MM-DD)
    market : str
        'ALL', 'KOSPI', 'KOSDAQ'
    limit : int
        종목 수 제한 (None이면 전체)
    
    Returns:
    --------
    pd.DataFrame : 스캔 결과
    """
    print(f"\n{'='*60}")
    print(f"📅 {base_date} 스캔 시작")
    print(f"{'='*60}")
    
    with EnhancedScanner() as scanner:
        results = scanner.scan_all(
            market=market,
            base_date=base_date,
            limit=limit,
            max_workers=8,
            progress=True
        )
        
        if not results.empty:
            # 날짜 컬럼 추가
            results['scan_date'] = base_date
            
            # 저장
            output_dir = Path('./data/daily_scans')
            output_dir.mkdir(parents=True, exist_ok=True)
            
            csv_path = output_dir / f"scan_{base_date}.csv"
            results.to_csv(csv_path, index=False, encoding='utf-8-sig')
            print(f"💾 저장 완료: {csv_path}")
            
            return results
        else:
            print(f"⚠️ {base_date}: 신호 감지된 종목 없음")
            return pd.DataFrame()


def batch_scan(start_date: str, end_date: str, market: str = 'ALL', limit: int = None):
    """
    기간별 배치 스캔
    
    Parameters:
    -----------
    start_date : str
        시작일 (YYYY-MM-DD)
    end_date : str
        종료일 (YYYY-MM-DD)
    market : str
        시장 선택
    limit : int
        종목 수 제한
    """
    start_dt = datetime.strptime(start_date, '%Y-%m-%d')
    end_dt = datetime.strptime(end_date, '%Y-%m-%d')
    
    all_results = []
    current_date = start_dt
    
    while current_date <= end_dt:
        date_str = current_date.strftime('%Y-%m-%d')
        
        try:
            result = scan_single_date(date_str, market, limit)
            if not result.empty:
                all_results.append(result)
        except Exception as e:
            print(f"❌ {date_str} 스캔 실패: {e}")
        
        current_date += timedelta(days=1)
    
    # 전체 결과 통합
    if all_results:
        combined = pd.concat(all_results, ignore_index=True)
        combined = combined.sort_values(['scan_date', 'score'], ascending=[False, False])
        
        output_path = Path('./data/daily_scans') / f"combined_{start_date}_{end_date}.csv"
        combined.to_csv(output_path, index=False, encoding='utf-8-sig')
        
        print(f"\n{'='*60}")
        print(f"✅ 전체 스캔 완료")
        print(f"📊 총 {len(combined)}개 신호 (기간: {start_date} ~ {end_date})")
        print(f"💾 통합 파일: {output_path}")
        print(f"{'='*60}")
        
        return combined
    else:
        print("\n⚠️ 스캔된 신호 없음")
        return pd.DataFrame()


def main():
    parser = argparse.ArgumentParser(description='기간별 배치 스캔')
    parser.add_argument('--start', default='2026-02-01', help='시작일 (YYYY-MM-DD)')
    parser.add_argument('--end', default='2026-02-28', help='종료일 (YYYY-MM-DD)')
    parser.add_argument('--market', default='ALL', choices=['ALL', 'KOSPI', 'KOSDAQ'])
    parser.add_argument('--limit', type=int, help='종목 수 제한 (테스트용)')
    
    args = parser.parse_args()
    
    print("🚀 배치 스캔 시작")
    print(f"📅 기간: {args.start} ~ {args.end}")
    print(f"📊 시장: {args.market}")
    
    batch_scan(args.start, args.end, args.market, args.limit)


if __name__ == "__main__":
    main()
