#!/usr/bin/env python3
"""
Jesse Livermore Pivot Point Scanner
제시 리버모어 전환점 실시간 스캐너

전체 3,286개 종목 대상 실시간 스캔
"""

import os
import json
import sqlite3
import pandas as pd
import numpy as np
import FinanceDataReader as fdr
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Tuple
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
    except: pass
    
    try:
        with open('data/kosdaq_stocks.json', 'r', encoding='utf-8') as f:
            data = json.load(f)
            for s in data.get('stocks', []):
                stocks.append({'code': s['code'], 'name': s['name'], 'market': 'KOSDAQ'})
    except: pass
    
    return stocks


def scan_livermore_stock(stock: Dict, pivot_period: int = 20, volume_threshold: float = 1.5) -> Optional[Dict]:
    """
    단일 종목 리버모어 스캔
    
    Parameters:
    -----------
    stock : Dict
        {'code': str, 'name': str, 'market': str}
    pivot_period : int
        전환점 계산 기간
    volume_threshold : float
        거래량 임계값 (1.5 = 150%)
    """
    code = stock['code']
    name = stock['name']
    market = stock['market']
    
    try:
        # 데이터 수집 (최근 100일)
        end = datetime.now()
        start = end - timedelta(days=100)
        df = fdr.DataReader(code, start.strftime('%Y-%m-%d'), end.strftime('%Y-%m-%d'))
        
        if df is None or len(df) < pivot_period + 5:
            return None
        
        # 지표 계산 (pandas_ta)
        df['high_20'] = df['High'].rolling(pivot_period).max()
        df['high_60'] = df['High'].rolling(60).max()
        df['volume_ma20'] = df['Volume'].rolling(20).mean()
        df['volume_ratio'] = df['Volume'] / df['volume_ma20']
        
        # 오늘 데이터
        today = df.iloc[-1]
        yesterday = df.iloc[-2] if len(df) > 1 else today
        
        current_price = today['Close']
        prev_high_20 = yesterday['high_20']
        prev_high_60 = yesterday['high_60']
        volume_ratio = today['volume_ratio']
        
        # 전환점 돌파 확인
        pivot_break = (current_price > prev_high_20) or (current_price > prev_high_60)
        volume_confirm = volume_ratio >= volume_threshold
        
        if not (pivot_break and volume_confirm):
            return None
        
        # 점수 계산
        # 가격 돌파 강도
        if prev_high_20 > 0:
            break_strength_20 = (current_price / prev_high_20 - 1) * 100
        else:
            break_strength_20 = 0
            
        if prev_high_60 > 0:
            break_strength_60 = (current_price / prev_high_60 - 1) * 100
        else:
            break_strength_60 = 0
        
        break_strength = max(break_strength_20, break_strength_60)
        
        # 거래량 점수
        volume_score = min(30, (volume_ratio - 1) * 20)
        
        # 돌파 점수
        break_score = min(40, break_strength * 4)
        
        # 추세 점수 (20일선 대비)
        ma20 = df['Close'].rolling(20).mean().iloc[-1]
        trend_score = 30 if current_price > ma20 else 15
        
        total_score = volume_score + break_score + trend_score
        
        # 신호 등급
        if total_score >= 80:
            signal_grade = "STRONG_BUY"
        elif total_score >= 60:
            signal_grade = "BUY"
        elif total_score >= 40:
            signal_grade = "WATCH"
        else:
            signal_grade = "NEUTRAL"
        
        # 피라미딩 진입 가격 계산
        entry_1 = current_price
        entry_2 = entry_1 * 1.05  # +5%
        entry_3 = entry_2 * 1.05  # +5%
        
        # 손절/익절 가격
        stop_loss = entry_1 * 0.90  # -10%
        
        return {
            'code': code,
            'name': name,
            'market': market,
            'date': end.strftime('%Y-%m-%d'),
            'current_price': current_price,
            'pivot_period': pivot_period,
            'high_20': prev_high_20,
            'high_60': prev_high_60,
            'volume_ratio': volume_ratio,
            'break_strength': break_strength,
            'score': total_score,
            'signal_grade': signal_grade,
            'entry_1': entry_1,
            'entry_2': entry_2,
            'entry_3': entry_3,
            'stop_loss': stop_loss,
            'position_size_1': 0.30,  # 30%
            'position_size_2': 0.30,  # 30%
            'position_size_3': 0.40,  # 40%
        }
        
    except Exception as e:
        return None


def scan_stock_parallel(args):
    """병렬 스캔 wrapper"""
    stock, pivot_period, volume_threshold = args
    
    result = scan_livermore_stock(stock, pivot_period, volume_threshold)
    
    # 진행률 업데이트
    global progress_counter, lock, total_stocks
    if lock:
        with lock:
            progress_counter.value += 1
            current = progress_counter.value
            if current % 100 == 0 or current == total_stocks:
                print(f"   📊 Progress: {current}/{total_stocks} ({current/total_stocks*100:.1f}%)")
    
    return result


class LivermoreScanner:
    """리버모어 전환점 스캐너"""
    
    def __init__(self, max_workers: int = 8, db_path: str = 'data/livermore_signals.db'):
        self.max_workers = max_workers
        self.db_path = db_path
        self.init_db()
    
    def init_db(self):
        """DB 초기화"""
        os.makedirs('data', exist_ok=True)
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS livermore_signals (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                code TEXT,
                name TEXT,
                market TEXT,
                date TEXT,
                current_price REAL,
                score REAL,
                signal_grade TEXT,
                volume_ratio REAL,
                break_strength REAL,
                entry_1 REAL,
                entry_2 REAL,
                entry_3 REAL,
                stop_loss REAL,
                UNIQUE(code, date)
            )
        ''')
        conn.commit()
        conn.close()
    
    def save_to_db(self, result: Dict):
        """DB 저장"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute('''
                INSERT OR REPLACE INTO livermore_signals
                (code, name, market, date, current_price, score, signal_grade,
                 volume_ratio, break_strength, entry_1, entry_2, entry_3, stop_loss)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                result['code'], result['name'], result['market'], result['date'],
                result['current_price'], result['score'], result['signal_grade'],
                result['volume_ratio'], result['break_strength'],
                result['entry_1'], result['entry_2'], result['entry_3'], result['stop_loss']
            ))
            conn.commit()
            conn.close()
        except Exception as e:
            pass
    
    def scan_all(self, min_score: float = 60, pivot_period: int = 20, volume_threshold: float = 1.5) -> List[Dict]:
        """
        전체 종목 스캔
        
        Parameters:
        -----------
        min_score : float
            최소 점수
        pivot_period : int
            전환점 기간
        volume_threshold : float
            거래량 임계값
        """
        stocks = load_stock_list()
        total = len(stocks)
        
        print("\n" + "="*70)
        print("🚀 Jesse Livermore Pivot Point Scanner")
        print("="*70)
        print(f"   Total Stocks: {total}")
        print(f"   Workers: {self.max_workers}")
        print(f"   Min Score: {min_score}")
        print(f"   Pivot Period: {pivot_period} days")
        print(f"   Volume Threshold: {volume_threshold*100:.0f}%")
        print("="*70)
        
        # 공유 상태
        manager = Manager()
        shared_counter = manager.Value('i', 0)
        shared_lock = manager.Lock()
        
        global total_stocks
        total_stocks = total
        
        results = []
        args_list = [(stock, pivot_period, volume_threshold) for stock in stocks]
        
        # 병렬 처리
        multiprocessing.set_start_method('spawn', force=True)
        
        with ProcessPoolExecutor(
            max_workers=self.max_workers,
            initializer=init_worker,
            initargs=(shared_counter, shared_lock, total)
        ) as executor:
            futures = {executor.submit(scan_stock_parallel, arg): arg for arg in args_list}
            
            for future in as_completed(futures):
                try:
                    result = future.result()
                    if result and result['score'] >= min_score:
                        results.append(result)
                        self.save_to_db(result)
                except:
                    pass
        
        # 점수순 정렬
        results = sorted(results, key=lambda x: x['score'], reverse=True)
        
        # 결과 출력
        print("\n" + "="*70)
        print("✅ Livermore Scan Complete!")
        print(f"   Total Signals: {len(results)}")
        print(f"   Strong Buy (≥80): {len([r for r in results if r['score'] >= 80])}")
        print(f"   Buy (60-79): {len([r for r in results if 60 <= r['score'] < 80])}")
        print("="*70)
        
        # JSON 저장
        output = {
            'scan_date': datetime.now().strftime('%Y-%m-%d %H:%M'),
            'pivot_period': pivot_period,
            'volume_threshold': volume_threshold,
            'total_stocks': total,
            'signals_found': len(results),
            'stocks': results[:100]  # TOP 100만 저장
        }
        
        with open('data/livermore_scan_results.json', 'w', encoding='utf-8') as f:
            json.dump(output, f, ensure_ascii=False, indent=2, default=str)
        
        print(f"   📁 Saved: data/livermore_scan_results.json")
        
        return results
    
    def print_top10(self, results: List[Dict]):
        """TOP 10 출력"""
        print("\n🏆 TOP 10 Livermore Signals:")
        print("-" * 90)
        print(f"{'순위':<5}{'종목':<15}{'점수':<8}{'신호':<12}{'현재가':<12}{'거래량':<10}{'돌파강도':<10}")
        print("-" * 90)
        
        for i, r in enumerate(results[:10], 1):
            print(f"{i:<5}{r['name']:<15}{r['score']:.1f<8}{r['signal_grade']:<12}"
                  f"{r['current_price']:>10,.0f}  {r['volume_ratio']:.1f}x    {r['break_strength']:.1f}%")


if __name__ == '__main__':
    import sys
    
    # 기본값
    max_workers = 8
    min_score = 60
    pivot_period = 20
    volume_threshold = 1.5
    
    # 인자 파싱
    if len(sys.argv) > 1:
        max_workers = int(sys.argv[1])
    if len(sys.argv) > 2:
        min_score = float(sys.argv[2])
    if len(sys.argv) > 3:
        pivot_period = int(sys.argv[3])
    if len(sys.argv) > 4:
        volume_threshold = float(sys.argv[4])
    
    # 스캐너 실행
    scanner = LivermoreScanner(max_workers=max_workers)
    results = scanner.scan_all(
        min_score=min_score,
        pivot_period=pivot_period,
        volume_threshold=volume_threshold
    )
    
    scanner.print_top10(results)
