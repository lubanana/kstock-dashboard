#!/usr/bin/env python3
"""
Daily Livermore Pivot Point Database Builder
일자별 전환점 포착 데이터베이스 구축

기간: 2025-02-01 ~ 현재
저장: data/daily_pivot/YYYY-MM-DD.json
"""

import os
import json
import pandas as pd
import numpy as np
import FinanceDataReader as fdr
from datetime import datetime, timedelta
from typing import List, Dict, Optional
from concurrent.futures import ProcessPoolExecutor, as_completed
from multiprocessing import Manager, Lock
import multiprocessing


# 전역 변수
progress_counter = None
lock = None
total_stocks = 0


def init_worker(shared_counter, shared_lock, total):
    """Worker 초기화"""
    global progress_counter, lock, total_stocks
    progress_counter = shared_counter
    lock = shared_lock
    total_stocks = total


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
    """
    특정 일자의 전환점 포착 여부 확인
    
    Parameters:
    -----------
    stock : Dict
        {'code': str, 'name': str, 'market': str}
    target_date : str
        'YYYY-MM-DD'
    lookback_days : int
        과거 데이터 조회 기간
    """
    code = stock['code']
    name = stock['name']
    market = stock['market']
    
    try:
        # 날짜 파싱
        target = datetime.strptime(target_date, '%Y-%m-%d')
        start = target - timedelta(days=lookback_days)
        
        # 데이터 수집
        df = fdr.DataReader(code, start.strftime('%Y-%m-%d'), target.strftime('%Y-%m-%d'))
        
        if df is None or len(df) < 21:
            return None
        
        # target_date가 데이터에 없으면 스킵 (휴일 등)
        if target_date not in [d.strftime('%Y-%m-%d') for d in df.index]:
            return None
        
        # 지표 계산
        df['high_20'] = df['High'].rolling(20).max()
        df['high_60'] = df['High'].rolling(60).max()
        df['volume_ma20'] = df['Volume'].rolling(20).mean()
        df['volume_ratio'] = df['Volume'] / df['volume_ma20']
        
        # target_date 행 찾기
        target_data = df.loc[df.index[-1]] if df.index[-1].strftime('%Y-%m-%d') == target_date else None
        
        if target_data is None:
            return None
        
        current_price = target_data['Close']
        prev_high_20 = df['high_20'].iloc[-2] if len(df) > 1 else df['high_20'].iloc[-1]
        prev_high_60 = df['high_60'].iloc[-2] if len(df) > 1 else df['high_60'].iloc[-1]
        volume_ratio = target_data['volume_ratio'] if not pd.isna(target_data['volume_ratio']) else 1.0
        
        # 전환점 돌파 확인
        pivot_break_20 = current_price > prev_high_20 if not pd.isna(prev_high_20) else False
        pivot_break_60 = current_price > prev_high_60 if not pd.isna(prev_high_60) else False
        pivot_break = pivot_break_20 or pivot_break_60
        
        # 거래량 확인 (150% 이상)
        volume_confirm = volume_ratio >= 1.5
        
        # 전환점 조건 미충족
        if not pivot_break:
            return None
        
        # 점수 계산
        if prev_high_20 > 0:
            break_strength_20 = (current_price / prev_high_20 - 1) * 100
        else:
            break_strength_20 = 0
        
        if prev_high_60 > 0:
            break_strength_60 = (current_price / prev_high_60 - 1) * 100
        else:
            break_strength_60 = 0
        
        break_strength = max(break_strength_20, break_strength_60)
        
        # 거래량 점수 (150% = 0점, 300% = 30점)
        volume_score = min(30, max(0, (volume_ratio - 1.5) * 20))
        
        # 돌파 강도 점수 (0% = 0점, 10% = 40점)
        break_score = min(40, break_strength * 4)
        
        # 추세 점수
        ma20 = df['Close'].rolling(20).mean().iloc[-1]
        trend_score = 30 if current_price > ma20 else 15
        
        total_score = volume_score + break_score + trend_score
        
        # 거래량 미확인 시 점수 감점
        if not volume_confirm:
            total_score *= 0.7
        
        return {
            'date': target_date,
            'code': code,
            'name': name,
            'market': market,
            'current_price': current_price,
            'pivot_break': pivot_break,
            'pivot_break_20': pivot_break_20,
            'pivot_break_60': pivot_break_60,
            'high_20': prev_high_20,
            'high_60': prev_high_60,
            'volume_ratio': volume_ratio,
            'volume_confirm': volume_confirm,
            'break_strength': break_strength,
            'score': total_score,
            'entry_1': current_price,
            'entry_2': current_price * 1.05,
            'entry_3': current_price * 1.1025,
            'stop_loss': current_price * 0.90
        }
        
    except Exception as e:
        return None


def scan_stock_parallel(args):
    """병렬 스캔 wrapper"""
    stock, target_date = args
    
    result = scan_stock_for_date(stock, target_date)
    
    # 진행률 업데이트
    global progress_counter, lock, total_stocks
    if lock and progress_counter:
        with lock:
            progress_counter.value += 1
            current = progress_counter.value
            if current % 200 == 0 or current == total_stocks:
                pct = current / total_stocks * 100
                print(f"      📊 {current}/{total_stocks} ({pct:.1f}%)")
    
    return result


def scan_single_date(target_date: str, stocks: List[Dict], max_workers: int = 8, min_score: float = 0) -> List[Dict]:
    """
    단일 일자 전체 종목 스캔
    
    Parameters:
    -----------
    target_date : str
        'YYYY-MM-DD'
    stocks : List[Dict]
        종목 리스트
    max_workers : int
        병렬 워커 수
    min_score : float
        최소 점수 (0 = 전환점 돌파만 확인)
    """
    global total_stocks
    total_stocks = len(stocks)
    
    print(f"   🚀 {target_date} 스캔 시작 ({total_stocks}종목)")
    
    # 공유 상태
    manager = Manager()
    shared_counter = manager.Value('i', 0)
    shared_lock = manager.Lock()
    
    results = []
    args_list = [(stock, target_date) for stock in stocks]
    
    # 병렬 처리
    multiprocessing.set_start_method('spawn', force=True)
    
    with ProcessPoolExecutor(
        max_workers=max_workers,
        initializer=init_worker,
        initargs=(shared_counter, shared_lock, total_stocks)
    ) as executor:
        futures = {executor.submit(scan_stock_parallel, arg): arg for arg in args_list}
        
        for future in as_completed(futures):
            try:
                result = future.result()
                if result and result['score'] >= min_score:
                    results.append(result)
            except:
                pass
    
    # 점수순 정렬
    results = sorted(results, key=lambda x: x['score'], reverse=True)
    
    print(f"   ✅ {target_date}: {len(results)}개 신호 발견")
    
    return results


def build_daily_database(start_date: str = '2025-02-01', end_date: str = None, max_workers: int = 8):
    """
    일자별 데이터베이스 구축
    
    Parameters:
    -----------
    start_date : str
        시작일 'YYYY-MM-DD'
    end_date : str
        종료일 (None = 어제)
    max_workers : int
        병렬 워커 수
    """
    if end_date is None:
        end_date = (datetime.now() - timedelta(days=1)).strftime('%Y-%m-%d')
    
    # 출력 디렉토리 생성
    output_dir = 'data/daily_pivot'
    os.makedirs(output_dir, exist_ok=True)
    
    # 종목 리스트 로드
    stocks = load_stock_list()
    
    print("\n" + "="*70)
    print("📊 Daily Livermore Pivot Point Database Builder")
    print("="*70)
    print(f"   Period: {start_date} ~ {end_date}")
    print(f"   Stocks: {len(stocks)}개")
    print(f"   Workers: {max_workers}")
    print(f"   Output: {output_dir}/")
    print("="*70)
    
    # 영업일 목록 생성 (주말 제외)
    start = datetime.strptime(start_date, '%Y-%m-%d')
    end = datetime.strptime(end_date, '%Y-%m-%d')
    
    current = start
    business_days = []
    while current <= end:
        if current.weekday() < 5:  # 월~금
            business_days.append(current.strftime('%Y-%m-%d'))
        current += timedelta(days=1)
    
    print(f"\n📅 영업일: {len(business_days)}일")
    
    # 일자별 스캔
    summary = []
    
    for i, date_str in enumerate(business_days, 1):
        print(f"\n[{i}/{len(business_days)}] {date_str}")
        
        # 이미 존재하는 파일 체크
        output_file = f"{output_dir}/{date_str}.json"
        if os.path.exists(output_file):
            # 기존 파일 로드하여 개수 확인
            try:
                with open(output_file, 'r', encoding='utf-8') as f:
                    existing = json.load(f)
                    count = len(existing.get('signals', []))
                    print(f"   ⏭️  이미 존재함 ({count}개 신호)")
                    summary.append({'date': date_str, 'signals': count})
                    continue
            except:
                pass
        
        # 스캔 실행
        results = scan_single_date(date_str, stocks, max_workers, min_score=0)
        
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
        
        # 상위 3개 출력
        if results:
            print(f"   🏆 Top 3:")
            for j, r in enumerate(results[:3], 1):
                vol_status = "✓" if r['volume_confirm'] else "✗"
                print(f"      {j}. {r['name']}: {r['score']:.1f}pts (거래량{vol_status})")
    
    # 요약 저장
    summary_file = f"{output_dir}/_summary.json"
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
    print(f"   저장 위치: {output_dir}/")
    print(f"   요약 파일: {summary_file}")
    
    # 통계 출력
    total_signals = sum(s['signals'] for s in summary)
    avg_signals = total_signals / len(summary) if summary else 0
    
    print(f"\n📈 통계:")
    print(f"   총 영업일: {len(summary)}일")
    print(f"   총 신호: {total_signals}개")
    print(f"   일평균 신호: {avg_signals:.1f}개")
    print("="*70)


if __name__ == '__main__':
    import sys
    
    # 기본값
    start_date = '2025-02-01'
    end_date = (datetime.now() - timedelta(days=1)).strftime('%Y-%m-%d')
    max_workers = 8
    
    # 인자 파싱
    if len(sys.argv) > 1:
        start_date = sys.argv[1]
    if len(sys.argv) > 2:
        end_date = sys.argv[2]
    if len(sys.argv) > 3:
        max_workers = int(sys.argv[3])
    
    build_daily_database(start_date, end_date, max_workers)
