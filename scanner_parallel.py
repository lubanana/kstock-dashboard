#!/usr/bin/env python3
"""
Parallel Strategy Scanner
오닐 CANSLIM + 미니버니 SEPA 병렬 처리 스캐너

Features:
- ProcessPoolExecutor for parallel stock processing
- Configurable worker count
- Shared progress tracking
- Error isolation per stock
"""

import os
import sys
import json
import sqlite3
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Tuple
from concurrent.futures import ProcessPoolExecutor, as_completed
from multiprocessing import Manager, Lock
import FinanceDataReader as fdr


# Global variables for shared state
progress_counter = None
total_stocks = 0
lock = None


def init_worker(shared_counter, shared_lock, total):
    """Worker initialization"""
    global progress_counter, lock, total_stocks
    progress_counter = shared_counter
    lock = shared_lock
    total_stocks = total


def fetch_price_data(code: str, days: int = 300) -> Optional[pd.DataFrame]:
    """가격 데이터 수집"""
    try:
        end = datetime.now()
        start = end - timedelta(days=days)
        df = fdr.DataReader(code, start.strftime('%Y-%m-%d'), end.strftime('%Y-%m-%d'))
        
        if df is None or len(df) < 200:
            return None
        
        return df
    except Exception as e:
        return None


def scan_oneil_stock(stock: Dict) -> Optional[Dict]:
    """O'Neil 단일 종목 스캔"""
    code = stock['code']
    name = stock['name']
    market = stock['market']
    
    try:
        df = fetch_price_data(code)
        if df is None:
            return None
        
        close = df['Close']
        volume = df['Volume']
        
        # 52주 최고가
        high_52w = close.rolling(252).max().iloc[-1]
        current = close.iloc[-1]
        proximity_52w = (current / high_52w) * 100 if high_52w > 0 else 0
        
        # 거래량 급증
        avg_vol_20 = volume.iloc[-20:].mean()
        avg_vol_50 = volume.iloc[-50:].mean()
        volume_ratio = avg_vol_20 / avg_vol_50 if avg_vol_50 > 0 else 1
        
        # 이동평균선
        ma20 = close.rolling(20).mean().iloc[-1]
        ma50 = close.rolling(50).mean().iloc[-1]
        ma200 = close.rolling(200).mean().iloc[-1]
        
        # 정렬 확인
        ma_aligned = (ma20 > ma50) and (ma50 > ma200)
        
        # 점수 계산
        score_52w = min(25, proximity_52w / 4)
        score_volume = min(25, volume_ratio * 10)
        score_ma = 25 if ma_aligned else 0
        score_trend = min(25, (current / ma200 - 1) * 100 * 2) if ma200 > 0 else 0
        
        setup_quality = score_52w + score_volume + score_ma + score_trend
        
        if setup_quality < 40:
            return None
        
        signal_type = "STRONG_BUY" if setup_quality >= 80 else "BUY" if setup_quality >= 60 else "WATCH"
        
        return {
            'code': code,
            'name': name,
            'market': market,
            'date': datetime.now().strftime('%Y-%m-%d'),
            'strategy': 'ONeil',
            'score': setup_quality,
            'signal_type': signal_type,
            'proximity_52w': proximity_52w,
            'volume_ratio': volume_ratio,
            'ma_aligned': 1 if ma_aligned else 0,
            'current_price': current,
            'entry_price': current,
            'stop_loss': current * 0.93,
            'target_price': current * 1.20
        }
        
    except Exception as e:
        return None


def scan_minervini_stock(stock: Dict) -> Optional[Dict]:
    """Minervini 단일 종목 스캔"""
    code = stock['code']
    name = stock['name']
    market = stock['market']
    
    try:
        df = fetch_price_data(code)
        if df is None or len(df) < 200:
            return None
        
        close = df['Close']
        
        # 이동평균선
        ma50 = close.rolling(50).mean().iloc[-1]
        ma150 = close.rolling(150).mean().iloc[-1]
        ma200 = close.rolling(200).mean().iloc[-1]
        current = close.iloc[-1]
        
        # Trend Template
        cond1 = current > ma150
        cond2 = current > ma200
        cond3 = ma150 > ma200
        cond4 = ma50 > ma150
        
        ma200_series = close.rolling(200).mean()
        ma200_trend = (ma200_series.iloc[-1] - ma200_series.iloc[-20]) / ma200_series.iloc[-20] * 100
        cond5 = ma200_trend > 0
        
        passed = sum([cond1, cond2, cond3, cond4, cond5])
        trend_pass = passed >= 4
        stage = "STAGE_2" if passed == 5 else "STAGE_1" if passed >= 3 else "STAGE_3" if passed >= 2 else "STAGE_4"
        
        # VCP
        vcp_score = 0
        if len(close) >= 60:
            period1 = close.iloc[-60:-40]
            period2 = close.iloc[-40:-20]
            period3 = close.iloc[-20:]
            
            vol1 = period1.std() / period1.mean() * 100
            vol2 = period2.std() / period2.mean() * 100
            vol3 = period3.std() / period3.mean() * 100
            
            if vol1 > vol2 > vol3:
                vcp_score = min(100, (1 - vol3/vol1) * 100)
        
        # Consolidation
        period = min(20, len(close))
        recent = close.iloc[-period:]
        high = recent.max()
        low = recent.min()
        avg = recent.mean()
        tightness = max(0, 100 - ((high - low) / avg * 100) * 5)
        
        # Composite score
        base_score = 40 if trend_pass else 0
        composite = base_score + (vcp_score * 0.25) + (tightness * 0.15)
        
        if composite < 40:
            return None
        
        signal_type = "BREAKOUT" if trend_pass and vcp_score >= 60 else "WATCHLIST" if trend_pass else "NEUTRAL"
        
        return {
            'code': code,
            'name': name,
            'market': market,
            'date': datetime.now().strftime('%Y-%m-%d'),
            'strategy': 'Minervini',
            'score': composite,
            'signal_type': signal_type,
            'stage': stage,
            'vcp_score': vcp_score,
            'consolidation': tightness,
            'current_price': current,
            'entry_price': current,
            'stop_loss': current * 0.93,
            'target_price': current * 1.15
        }
        
    except Exception as e:
        return None


def scan_stock_parallel(args):
    """병렬 스캔 wrapper"""
    stock, strategy = args
    
    try:
        if strategy == 'oneil':
            result = scan_oneil_stock(stock)
        else:
            result = scan_minervini_stock(stock)
        
        # Update progress
        with lock:
            progress_counter.value += 1
            current = progress_counter.value
            if current % 100 == 0 or current == total_stocks:
                print(f"   📊 Progress: {current}/{total_stocks} ({current/total_stocks*100:.1f}%)")
        
        return result
        
    except Exception as e:
        return None


class ParallelStrategyScanner:
    """병렬 전략 스캐너"""
    
    def __init__(self, max_workers: int = 8):
        self.max_workers = max_workers
        self.oneil_db = 'data/oneil_signals.db'
        self.minervini_db = 'data/minervini_signals.db'
        self.init_dbs()
    
    def init_dbs(self):
        """DB 초기화"""
        os.makedirs('data', exist_ok=True)
        
        # O'Neil DB
        conn = sqlite3.connect(self.oneil_db)
        conn.execute('''CREATE TABLE IF NOT EXISTS oneil_signals (
            code TEXT, name TEXT, market TEXT, date TEXT, score REAL,
            signal_type TEXT, current_price REAL, entry_price REAL,
            stop_loss REAL, target_price REAL, UNIQUE(code, date))''')
        conn.commit()
        conn.close()
        
        # Minervini DB
        conn = sqlite3.connect(self.minervini_db)
        conn.execute('''CREATE TABLE IF NOT EXISTS minervini_signals (
            code TEXT, name TEXT, market TEXT, date TEXT, score REAL,
            signal_type TEXT, stage TEXT, vcp_score REAL, current_price REAL,
            entry_price REAL, stop_loss REAL, target_price REAL, UNIQUE(code, date))''')
        conn.commit()
        conn.close()
    
    def load_stock_list(self) -> List[Dict]:
        """전체 종목 로드"""
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
    
    def scan_strategy(self, strategy: str, stocks: List[Dict], min_score: float = 60) -> List[Dict]:
        """전략별 병렬 스캔"""
        global total_stocks
        total_stocks = len(stocks)
        
        print(f"\n🚀 {strategy.upper()} Parallel Scan")
        print(f"   Workers: {self.max_workers} | Stocks: {total_stocks}")
        print("="*70)
        
        # Shared state
        manager = Manager()
        shared_counter = manager.Value('i', 0)
        shared_lock = manager.Lock()
        
        results = []
        args_list = [(stock, strategy) for stock in stocks]
        
        # Parallel processing
        with ProcessPoolExecutor(
            max_workers=self.max_workers,
            initializer=init_worker,
            initargs=(shared_counter, shared_lock, total_stocks)
        ) as executor:
            futures = {executor.submit(scan_stock_parallel, arg): arg for arg in args_list}
            
            for future in as_completed(futures):
                try:
                    result = future.result()
                    if result and result['score'] >= min_score:
                        results.append(result)
                        self.save_to_db(result, strategy)
                except Exception as e:
                    pass
        
        # Sort by score
        results = sorted(results, key=lambda x: x['score'], reverse=True)
        
        print(f"\n✅ {strategy.upper()} Complete!")
        print(f"   Signals: {len(results)}")
        
        return results
    
    def save_to_db(self, result: Dict, strategy: str):
        """DB 저장"""
        try:
            if strategy == 'oneil':
                conn = sqlite3.connect(self.oneil_db)
                conn.execute('''INSERT OR REPLACE INTO oneil_signals
                    (code, name, market, date, score, signal_type, current_price,
                     entry_price, stop_loss, target_price)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''',
                    (result['code'], result['name'], result['market'], result['date'],
                     result['score'], result['signal_type'], result['current_price'],
                     result['entry_price'], result['stop_loss'], result['target_price']))
            else:
                conn = sqlite3.connect(self.minervini_db)
                conn.execute('''INSERT OR REPLACE INTO minervini_signals
                    (code, name, market, date, score, signal_type, stage, vcp_score,
                     current_price, entry_price, stop_loss, target_price)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''',
                    (result['code'], result['name'], result['market'], result['date'],
                     result['score'], result['signal_type'], result.get('stage', ''),
                     result.get('vcp_score', 0), result['current_price'],
                     result['entry_price'], result['stop_loss'], result['target_price']))
            conn.commit()
            conn.close()
        except Exception as e:
            pass
    
    def run_both(self, min_score: float = 60):
        """양쪽 전략 모두 실행"""
        stocks = self.load_stock_list()
        
        print("\n" + "="*70)
        print("🚀 Parallel Strategy Scanner")
        print(f"   Max Workers: {self.max_workers}")
        print("="*70)
        
        # O'Neil
        start_time = datetime.now()
        oneil_results = self.scan_strategy('oneil', stocks, min_score)
        oneil_time = (datetime.now() - start_time).total_seconds()
        
        # Minervini
        start_time = datetime.now()
        minervini_results = self.scan_strategy('minervini', stocks, min_score)
        minervini_time = (datetime.now() - start_time).total_seconds()
        
        # Summary
        print("\n" + "="*70)
        print("📊 Parallel Scan Summary")
        print("="*70)
        print(f"   O'Neil:     {len(oneil_results):3d} signals in {oneil_time:.1f}s")
        print(f"   Minervini:  {len(minervini_results):3d} signals in {minervini_time:.1f}s")
        print(f"   Total:      {len(oneil_results) + len(minervini_results)} signals")
        print(f"   Workers:    {self.max_workers}")
        
        # Save JSON
        with open('data/oneil_parallel_results.json', 'w', encoding='utf-8') as f:
            json.dump({'date': datetime.now().strftime('%Y-%m-%d'), 'stocks': oneil_results}, 
                     f, ensure_ascii=False, indent=2, default=str)
        
        with open('data/minervini_parallel_results.json', 'w', encoding='utf-8') as f:
            json.dump({'date': datetime.now().strftime('%Y-%m-%d'), 'stocks': minervini_results}, 
                     f, ensure_ascii=False, indent=2, default=str)
        
        return oneil_results, minervini_results


if __name__ == '__main__':
    import multiprocessing
    multiprocessing.set_start_method('spawn', force=True)
    
    max_workers = int(sys.argv[1]) if len(sys.argv) > 1 else 8
    min_score = float(sys.argv[2]) if len(sys.argv) > 2 else 60.0
    
    scanner = ParallelStrategyScanner(max_workers=max_workers)
    scanner.run_both(min_score=min_score)
