#!/usr/bin/env python3
"""
Daily Livermore Pivot Point Database Builder (Sequential Version)
일자별 전환점 포착 데이터베이스 구축 (순차 실행 버전)

기간: 2025-02-01 ~ 현재
저장: data/daily_pivot/YYYY-MM-DD.json
"""

import os
import sys
import json
import pandas as pd
import numpy as np
import FinanceDataReader as fdr
from datetime import datetime, timedelta
from typing import List, Dict, Optional


def load_stock_list() -> List[Dict]:
    """전체 종목 리스트 로드"""
    stocks = []
    try:
        with open('data/kospi_stocks.json', 'r', encoding='utf-8') as f:
            data = json.load(f)
            for s in data.get('stocks', []):
                stocks.append({'code': s['code'], 'name': s['name'], 'market': 'KOSPI'})
    except Exception as e:
        print(f"   ⚠️ KOSPI 로드 오류: {e}")
    
    try:
        with open('data/kosdaq_stocks.json', 'r', encoding='utf-8') as f:
            data = json.load(f)
            for s in data.get('stocks', []):
                stocks.append({'code': s['code'], 'name': s['name'], 'market': 'KOSDAQ'})
    except Exception as e:
        print(f"   ⚠️ KOSDAQ 로드 오류: {e}")
    
    return stocks


def scan_stock_for_date(stock: Dict, target_date: str, lookback_days: int = 60) -> Optional[Dict]:
    """특정 일자의 전환점 포착 여부 확인"""
    code = stock['code']
    name = stock['name']
    market = stock['market']
    
    try:
        target = datetime.strptime(target_date, '%Y-%m-%d')
        start = target - timedelta(days=lookback_days)
        
        df = fdr.DataReader(code, start.strftime('%Y-%m-%d'), target.strftime('%Y-%m-%d'))
        
        if df is None or len(df) < 21:
            return None
        
        # target_date가 데이터에 없으면 스킵
        date_strings = [d.strftime('%Y-%m-%d') for d in df.index]
        if target_date not in date_strings:
            return None
        
        # target_date 행 찾기
        target_idx = date_strings.index(target_date)
        if target_idx == 0:
            return None  # 첫날은 이전 데이터 없음
        
        target_data = df.iloc[target_idx]
        prev_data = df.iloc[target_idx - 1]
        
        # 과거 20일/60일 최고가 (전일까지)
        prev_df = df.iloc[:target_idx]
        high_20 = prev_df['High'].tail(20).max()
        high_60 = prev_df['High'].tail(60).max()
        
        current_price = target_data['Close']
        volume = target_data['Volume']
        
        # 20일 평균 거래량 (전일까지)
        volume_ma20 = prev_df['Volume'].tail(20).mean()
        volume_ratio = volume / volume_ma20 if volume_ma20 > 0 else 1.0
        
        # 전환점 돌파 확인
        pivot_break_20 = current_price > high_20 if not pd.isna(high_20) else False
        pivot_break_60 = current_price > high_60 if not pd.isna(high_60) else False
        pivot_break = pivot_break_20 or pivot_break_60
        
        if not pivot_break:
            return None
        
        # 점수 계산
        break_strength_20 = (current_price / high_20 - 1) * 100 if high_20 > 0 else 0
        break_strength_60 = (current_price / high_60 - 1) * 100 if high_60 > 0 else 0
        break_strength = max(break_strength_20, break_strength_60)
        
        volume_score = min(30, max(0, (volume_ratio - 1.5) * 20))
        break_score = min(40, break_strength * 4)
        
        ma20 = prev_df['Close'].tail(20).mean()
        trend_score = 30 if current_price > ma20 else 15
        
        total_score = volume_score + break_score + trend_score
        volume_confirm = volume_ratio >= 1.5
        
        if not volume_confirm:
            total_score *= 0.7
        
        return {
            'date': target_date,
            'code': code,
            'name': name,
            'market': market,
            'current_price': float(current_price),
            'pivot_break_20': pivot_break_20,
            'pivot_break_60': pivot_break_60,
            'high_20': float(high_20),
            'high_60': float(high_60),
            'volume_ratio': float(volume_ratio),
            'volume_confirm': volume_confirm,
            'break_strength': float(break_strength),
            'score': float(total_score),
            'entry_1': float(current_price),
            'entry_2': float(current_price * 1.05),
            'entry_3': float(current_price * 1.1025),
            'stop_loss': float(current_price * 0.90)
        }
        
    except Exception as e:
        return None


def scan_single_date(target_date: str, stocks: List[Dict], min_score: float = 0) -> List[Dict]:
    """단일 일자 전체 종목 스캔 (순차)"""
    total = len(stocks)
    print(f"   🚀 {target_date} 스캔 시작 ({total}종목)")
    
    results = []
    
    for i, stock in enumerate(stocks, 1):
        result = scan_stock_for_date(stock, target_date)
        if result and result['score'] >= min_score:
            results.append(result)
        
        # 진행률 표시 (100개마다)
        if i % 500 == 0 or i == total:
            pct = i / total * 100
            print(f"      📊 {i}/{total} ({pct:.1f}%) - 신호: {len(results)}개")
    
    # 점수순 정렬
    results = sorted(results, key=lambda x: x['score'], reverse=True)
    
    print(f"   ✅ {target_date}: {len(results)}개 신호 발견")
    
    return results


def build_daily_database(start_date: str = '2025-02-01', end_date: str = None):
    """일자별 데이터베이스 구축"""
    if end_date is None:
        end_date = (datetime.now() - timedelta(days=1)).strftime('%Y-%m-%d')
    
    output_dir = 'data/daily_pivot'
    os.makedirs(output_dir, exist_ok=True)
    
    stocks = load_stock_list()
    
    print("\n" + "="*70)
    print("📊 Daily Livermore Pivot Point Database Builder")
    print("="*70)
    print(f"   Period: {start_date} ~ {end_date}")
    print(f"   Stocks: {len(stocks)}개")
    print(f"   Output: {output_dir}/")
    print("="*70)
    
    # 영업일 목록 생성
    start = datetime.strptime(start_date, '%Y-%m-%d')
    end = datetime.strptime(end_date, '%Y-%m-%d')
    
    current = start
    business_days = []
    while current <= end:
        if current.weekday() < 5:  # 월~금
            business_days.append(current.strftime('%Y-%m-%d'))
        current += timedelta(days=1)
    
    print(f"\n📅 영업일: {len(business_days)}일")
    
    # 요약 데이터 로드 (이미 처리된 날짜 확인)
    summary_file = f"{output_dir}/_summary.json"
    processed_dates = set()
    summary = []
    
    if os.path.exists(summary_file):
        try:
            with open(summary_file, 'r', encoding='utf-8') as f:
                existing = json.load(f)
                summary = existing.get('daily_stats', [])
                processed_dates = {s['date'] for s in summary}
                print(f"   ℹ️  이미 처리된 날짜: {len(processed_dates)}일")
        except:
            pass
    
    # 남은 날짜만 처리
    remaining_days = [d for d in business_days if d not in processed_dates]
    print(f"   📝 처리할 날짜: {len(remaining_days)}일")
    
    # 일자별 스캔
    for i, date_str in enumerate(remaining_days, 1):
        print(f"\n[{i}/{len(remaining_days)}] {date_str}")
        
        output_file = f"{output_dir}/{date_str}.json"
        
        # 스캔 실행
        results = scan_single_date(date_str, stocks, min_score=0)
        
        # 저장
        output = {
            'date': date_str,
            'total_stocks_scanned': len(stocks),
            'signals_found': len(results),
            'signals': results
        }
        
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(output, f, ensure_ascii=False, indent=2, default=str)
        
        summary.append({'date': date_str, 'signals': len(results)})
        
        # 중간 요약 저장
        if i % 5 == 0:
            with open(summary_file, 'w', encoding='utf-8') as f:
                json.dump({
                    'start_date': start_date,
                    'end_date': end_date,
                    'total_days': len(business_days),
                    'daily_stats': summary
                }, f, ensure_ascii=False, indent=2)
        
        # 상위 3개 출력
        if results:
            print(f"   🏆 Top 3:")
            for j, r in enumerate(results[:3], 1):
                vol_status = "✓" if r['volume_confirm'] else "✗"
                print(f"      {j}. {r['name']}: {r['score']:.1f}pts (거래량{vol_status})")
    
    # 최종 요약 저장
    with open(summary_file, 'w', encoding='utf-8') as f:
        json.dump({
            'start_date': start_date,
            'end_date': end_date,
            'total_days': len(business_days),
            'daily_stats': summary
        }, f, ensure_ascii=False, indent=2)
    
    print("\n" + "="*70)
    print("✅ 데이터베이스 구축 완료!")
    print("="*70)
    
    total_signals = sum(s['signals'] for s in summary)
    avg_signals = total_signals / len(summary) if summary else 0
    
    print(f"   저장 위치: {output_dir}/")
    print(f"   총 영업일: {len(summary)}일")
    print(f"   총 신호: {total_signals}개")
    print(f"   일평균 신호: {avg_signals:.1f}개")
    print("="*70)


if __name__ == '__main__':
    start_date = '2025-02-01'
    end_date = (datetime.now() - timedelta(days=1)).strftime('%Y-%m-%d')
    
    if len(sys.argv) > 1:
        start_date = sys.argv[1]
    if len(sys.argv) > 2:
        end_date = sys.argv[2]
    
    build_daily_database(start_date, end_date)
