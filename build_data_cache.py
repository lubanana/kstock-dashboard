#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Build 1-Year Price Data Cache
=============================
FinanceDataReader로 전 종목 1년치 주가 데이터를 구축하는 스크립트

Features:
- 전 종목(KOSPI+KOSDAQ) 1년치 데이터 일괄 수집
- 기존 캐시된 데이터는 스킵, 없는 데이터만 API 호출
- 진행상황 표시 및 에러 로깅
- 재시도 로직 포함
"""

import pandas as pd
import json
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Dict, Set
import time

from fdr_wrapper import FDRWrapper
from local_db import LocalDB


class DataBuilder:
    """1년치 주가 데이터 구축 클래스"""
    
    def __init__(self, db_path: str = './data/pivot_strategy.db'):
        self.db = LocalDB(db_path)
        self.fdr = FDRWrapper(db_path)
        
        # 날짜 설정 (1년치)
        self.end_date = datetime.now().strftime('%Y-%m-%d')
        self.start_date = (datetime.now() - timedelta(days=365)).strftime('%Y-%m-%d')
        
        print(f"📅 데이터 수집 기간: {self.start_date} ~ {self.end_date}")
        
        # 통계
        self.stats = {
            'total': 0,
            'success': 0,
            'failed': 0,
            'skipped': 0,
            'api_calls': 0
        }
    
    def load_stock_list(self, market: str = 'ALL') -> List[Dict]:
        """종목 리스트 로드"""
        with open('./data/stock_list.json', 'r') as f:
            data = json.load(f)
        
        stocks = data.get('stocks', [])
        
        if market != 'ALL':
            stocks = [s for s in stocks if s['market'] == market]
        
        return stocks
    
    def check_existing_data(self, symbol: str, min_days: int = 200) -> bool:
        """
        이미 충분한 데이터가 있는지 확인
        
        Args:
            symbol: 종목코드
            min_days: 최소 필요 일수 (기본 200일)
        
        Returns:
            True면 데이터 충분 (스킵 가능)
        """
        try:
            existing = self.db.get_prices(symbol, self.start_date, self.end_date)
            if len(existing) >= min_days:
                return True
        except:
            pass
        return False
    
    def fetch_single(self, symbol: str, retries: int = 3, delay: float = 0.5) -> bool:
        """
        단일 종목 데이터 가져오기
        
        Args:
            symbol: 종목코드
            retries: 재시도 횟수
            delay: 재시도 간격(초)
        
        Returns:
            성공 여부
        """
        for attempt in range(retries):
            try:
                # FinanceDataReader 직접 호출
                import FinanceDataReader as fdr
                df = fdr.DataReader(symbol, self.start_date, self.end_date)
                
                if df.empty:
                    print(f"  ⚠️ 데이터 없음: {symbol}")
                    return False
                
                # DB에 저장
                self.db.save_prices(df, symbol)
                self.stats['api_calls'] += 1
                
                return True
                
            except Exception as e:
                print(f"  ❌ 시도 {attempt+1}/{retries} 실패: {symbol} - {e}")
                if attempt < retries - 1:
                    time.sleep(delay * (attempt + 1))  # 점진적 대기
                else:
                    return False
        
        return False
    
    def build_all(self, market: str = 'ALL', skip_existing: bool = True):
        """
        전 종목 데이터 구축
        
        Args:
            market: 'KOSPI', 'KOSDAQ', 또는 'ALL'
            skip_existing: 이미 있는 데이터는 스킵
        """
        stocks = self.load_stock_list(market)
        self.stats['total'] = len(stocks)
        
        print(f"\n🔍 총 {len(stocks)}개 종목 데이터 구축 시작...")
        print("=" * 60)
        
        for i, stock in enumerate(stocks, 1):
            symbol = stock['symbol']
            name = stock['name']
            
            print(f"\n[{i}/{len(stocks)}] {symbol} - {name}")
            
            # 기존 데이터 확인
            if skip_existing and self.check_existing_data(symbol):
                print(f"  ⏭️  캐시됨 (스킵)")
                self.stats['skipped'] += 1
                continue
            
            # 데이터 가져오기
            if self.fetch_single(symbol):
                print(f"  ✅ 성공")
                self.stats['success'] += 1
            else:
                print(f"  ❌ 실패")
                self.stats['failed'] += 1
            
            # 진행상황 출력 (10개마다)
            if i % 10 == 0:
                self.print_progress()
            
            # API 부하 방지를 위한 짧은 대기
            time.sleep(0.1)
        
        print("\n" + "=" * 60)
        print("✅ 데이터 구축 완료!")
        self.print_stats()
    
    def build_missing_only(self, market: str = 'ALL'):
        """부족한 데이터만 보충"""
        stocks = self.load_stock_list(market)
        
        # 부족한 종목만 필터링
        missing_stocks = []
        for stock in stocks:
            if not self.check_existing_data(stock['symbol']):
                missing_stocks.append(stock)
        
        print(f"\n🔍 캐시 부족 종목: {len(missing_stocks)}개 / 전체 {len(stocks)}개")
        
        if not missing_stocks:
            print("✅ 모든 종목에 충분한 데이터가 있습니다!")
            return
        
        # 부족한 종목만 구축
        self.stats['total'] = len(missing_stocks)
        
        for i, stock in enumerate(missing_stocks, 1):
            symbol = stock['symbol']
            name = stock['name']
            
            print(f"\n[{i}/{len(missing_stocks)}] {symbol} - {name}")
            
            if self.fetch_single(symbol):
                print(f"  ✅ 성공")
                self.stats['success'] += 1
            else:
                print(f"  ❌ 실패")
                self.stats['failed'] += 1
            
            if i % 10 == 0:
                self.print_progress()
            
            time.sleep(0.1)
        
        print("\n" + "=" * 60)
        print("✅ 보충 완료!")
        self.print_stats()
    
    def print_progress(self):
        """진행상황 출력"""
        total = self.stats['total']
        processed = self.stats['success'] + self.stats['failed'] + self.stats['skipped']
        pct = (processed / total * 100) if total > 0 else 0
        
        print(f"\n📊 진행: {processed}/{total} ({pct:.1f}%)")
        print(f"   ✅ 성공: {self.stats['success']} | ⏭️  스킵: {self.stats['skipped']} | ❌ 실패: {self.stats['failed']}")
    
    def print_stats(self):
        """최종 통계 출력"""
        print("\n📈 최종 통계")
        print("-" * 40)
        print(f"  총 종목: {self.stats['total']}")
        print(f"  ✅ 성공: {self.stats['success']}")
        print(f"  ⏭️  스킵: {self.stats['skipped']}")
        print(f"  ❌ 실패: {self.stats['failed']}")
        print(f"  🌐 API 호출: {self.stats['api_calls']}")
        
        success_rate = (self.stats['success'] / self.stats['total'] * 100) if self.stats['total'] > 0 else 0
        print(f"  📉 성공률: {success_rate:.1f}%")
    
    def verify_data(self, sample_size: int = 10):
        """데이터 검증 (샘플링)"""
        print("\n🔍 데이터 검증 (샘플링)")
        print("=" * 60)
        
        stocks = self.load_stock_list()
        import random
        samples = random.sample(stocks, min(sample_size, len(stocks)))
        
        for stock in samples:
            symbol = stock['symbol']
            df = self.db.get_prices(symbol, self.start_date, self.end_date)
            
            if df.empty:
                print(f"  ❌ {symbol}: 데이터 없음")
            else:
                days = len(df)
                start = df.index[0] if hasattr(df.index[0], 'strftime') else df['date'].iloc[0]
                end = df.index[-1] if hasattr(df.index[-1], 'strftime') else df['date'].iloc[-1]
                print(f"  ✅ {symbol}: {days}일 ({start} ~ {end})")


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='1년치 주가 데이터 구축')
    parser.add_argument('--market', default='ALL', choices=['ALL', 'KOSPI', 'KOSDAQ'],
                      help='시장 선택')
    parser.add_argument('--mode', default='missing', choices=['all', 'missing'],
                      help='구축 모드 (all: 전체, missing: 부족한 것만)')
    parser.add_argument('--verify', action='store_true',
                      help='구축 후 데이터 검증')
    
    args = parser.parse_args()
    
    print("🚀 1년치 주가 데이터 구축 시작")
    print("=" * 60)
    
    builder = DataBuilder()
    
    if args.mode == 'all':
        builder.build_all(market=args.market, skip_existing=True)
    else:
        builder.build_missing_only(market=args.market)
    
    if args.verify:
        builder.verify_data()
    
    print("\n✅ 완료!")
