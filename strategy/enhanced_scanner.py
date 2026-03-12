#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Enhanced Multi-Stock Pivot Point Scanner
========================================
파라미터 기반 다중 종목 스캐너

Features:
- 개별 종목 또는 전체 종목 스캔
- 기준 일자 지정 가능
- StockRepository 통합
- CLI 인터페이스 지원
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Literal
import concurrent.futures
from tqdm import tqdm
import warnings
warnings.filterwarnings('ignore')

from fdr_wrapper import FDRWrapper
from stock_repository import StockRepository


class EnhancedScanner:
    """
    향상된 다중 종목 스캐너 (파라미터 기반)
    """
    
    def __init__(
        self,
        pivot_period: int = 20,
        volume_threshold: float = 1.5,
        min_price: float = 1000,
        min_volume: int = 100000,
        db_path: str = './data/pivot_strategy.db'
    ):
        """
        Parameters:
        -----------
        pivot_period : int
            피벗 포인트 계산 기간 (일)
        volume_threshold : float
            거래량 임계값 (1.5 = 150%)
        min_price : float
            최소 주가 (원)
        min_volume : int
            최소 일평균 거래량
        db_path : str
            데이터베이스 파일 경로
        """
        self.pivot_period = pivot_period
        self.volume_threshold = volume_threshold
        self.min_price = min_price
        self.min_volume = min_volume
        self.db_path = db_path
        
        self.repo = StockRepository(db_path)
        self.results: List[Dict] = []
    
    def scan_single(
        self, 
        symbol: str, 
        name: str = '', 
        market: str = '',
        base_date: str = None
    ) -> Optional[Dict]:
        """
        개별 종목 스캔
        
        Parameters:
        -----------
        symbol : str
            종목코드
        name : str
            종목명
        market : str
            시장 (KOSPI/KOSDAQ)
        base_date : str
            기준 일자 (YYYY-MM-DD), None이면 오늘
        
        Returns:
        --------
        dict : 신호 정보 또는 None
        """
        try:
            # 기준 일자 설정
            if base_date is None:
                base_date = datetime.now().strftime('%Y-%m-%d')
            
            base_dt = datetime.strptime(base_date, '%Y-%m-%d')
            
            # 데이터 수집 기간 (기준일 - pivot_period*3 ~ 기준일)
            start_date = (base_dt - timedelta(days=self.pivot_period * 3)).strftime('%Y-%m-%d')
            
            # FDRWrapper 사용
            with FDRWrapper(self.db_path) as fdr:
                df = fdr.get_price(symbol, start_date, base_date)
            
            if df.empty or len(df) < self.pivot_period + 5:
                return None
            
            # 컬럼명 소문자로
            df.columns = [col.lower() for col in df.columns]
            
            # 기준일 데이터 찾기
            df.index = pd.to_datetime(df.index)
            base_data = df[df.index <= base_dt]
            
            if len(base_data) < 2:
                return None
            
            latest = base_data.iloc[-1]
            prev = base_data.iloc[-2]
            
            # 최소 가격 필터
            if latest['close'] < self.min_price:
                return None
            
            # 평균 거래량 필터 (최근 20일)
            avg_volume = base_data['volume'].tail(20).mean()
            if avg_volume < self.min_volume:
                return None
            
            # 피벗 고가 계산 (기준일 기준)
            df_calc = base_data.copy()
            df_calc[f'high_{self.pivot_period}'] = df_calc['high'].rolling(window=self.pivot_period).max()
            df_calc['volume_ma20'] = df_calc['volume'].rolling(window=20).mean()
            
            if len(df_calc) < 2:
                return None
            
            # 피벗 돌파 확인
            pivot_high = df_calc[f'high_{self.pivot_period}'].iloc[-2]
            volume_ma20 = df_calc['volume_ma20'].iloc[-2]
            
            # 조건 체크
            price_break = latest['close'] > pivot_high
            volume_spike = latest['volume'] > (volume_ma20 * self.volume_threshold)
            
            if price_break and volume_spike:
                signal = {
                    'symbol': symbol,
                    'name': name,
                    'market': market,
                    'date': base_date,
                    'close': latest['close'],
                    'open': latest['open'],
                    'high': latest['high'],
                    'low': latest['low'],
                    'volume': int(latest['volume']),
                    'pivot_high': pivot_high,
                    'volume_ma20': int(volume_ma20),
                    'volume_ratio': latest['volume'] / volume_ma20 if volume_ma20 > 0 else 0,
                    'price_change_pct': ((latest['close'] - prev['close']) / prev['close']) * 100,
                    'score': 0  # 후에 계산
                }
                # 점수 계산
                signal['score'] = (signal['volume_ratio'] - 1) * 50 + max(signal['price_change_pct'], 0) * 2
                return signal
            
            return None
            
        except Exception as e:
            return None
    
    def scan_multiple(
        self,
        symbols: List[Dict],
        base_date: str = None,
        max_workers: int = 4,
        progress: bool = True
    ) -> pd.DataFrame:
        """
        여러 종목 스캔
        
        Parameters:
        -----------
        symbols : List[Dict]
            [{'symbol': '005930', 'name': '삼성전자', 'market': 'KOSPI'}, ...]
        base_date : str
            기준 일자
        max_workers : int
            병렬 처리 스레드 수
        progress : bool
            진행바 표시 여부
        
        Returns:
        --------
        pd.DataFrame : 스캔 결과
        """
        print(f"\n🔍 {len(symbols)}개 종목 스캔 시작...")
        if base_date:
            print(f"📅 기준일: {base_date}")
        
        self.results = []
        
        # 병렬 스캔
        with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = {
                executor.submit(
                    self.scan_single,
                    s.get('symbol', ''),
                    s.get('name', ''),
                    s.get('market', ''),
                    base_date
                ): s
                for s in symbols
            }
            
            iterator = concurrent.futures.as_completed(futures)
            if progress:
                iterator = tqdm(iterator, total=len(futures), desc="Scanning")
            
            for future in iterator:
                result = future.result()
                if result:
                    self.results.append(result)
        
        # DataFrame 변환
        if self.results:
            df = pd.DataFrame(self.results)
            df = df.sort_values('score', ascending=False).reset_index(drop=True)
            print(f"\n✅ 신호 감지: {len(df)}개 종목")
            return df
        else:
            print("\n⚠️ 신호 감지된 종목 없음")
            return pd.DataFrame()
    
    def scan_all(
        self,
        market: Literal['ALL', 'KOSPI', 'KOSDAQ'] = 'ALL',
        base_date: str = None,
        limit: int = None,
        max_workers: int = 4,
        progress: bool = True
    ) -> pd.DataFrame:
        """
        전체 종목 스캔
        
        Parameters:
        -----------
        market : str
            'ALL', 'KOSPI', 또는 'KOSDAQ'
        base_date : str
            기준 일자
        limit : int
            최대 스캔 종목 수
        max_workers : int
            병렬 처리 스레드 수
        progress : bool
            진행바 표시 여부
        
        Returns:
        --------
        pd.DataFrame : 스캔 결과
        """
        # 종목 리스트 조회
        if market == 'ALL':
            kospi = self.repo.get_stocks_by_market('KOSPI', limit//2 if limit else None)
            kosdaq = self.repo.get_stocks_by_market('KOSDAQ', limit//2 if limit else None)
            symbols = kospi + kosdaq
        else:
            symbols = self.repo.get_stocks_by_market(market, limit)
        
        if limit and len(symbols) > limit:
            symbols = symbols[:limit]
        
        print(f"📊 대상 종목: {len(symbols)}개 ({market})")
        
        return self.scan_multiple(symbols, base_date, max_workers, progress)
    
    def scan_by_symbols(
        self,
        symbol_list: List[str],
        base_date: str = None,
        max_workers: int = 4,
        progress: bool = True
    ) -> pd.DataFrame:
        """
        특정 종목 리스트 스캔
        
        Parameters:
        -----------
        symbol_list : List[str]
            종목코드 리스트 ['005930', '035420', ...]
        base_date : str
            기준 일자
        max_workers : int
            병렬 처리 스레드 수
        
        Returns:
        --------
        pd.DataFrame : 스캔 결과
        """
        # 종목 정보 조회
        symbols = []
        for sym in symbol_list:
            info = self.repo.get_stock_by_symbol(sym)
            if info:
                symbols.append(info)
        
        print(f"📊 대상 종목: {len(symbols)}개 (지정)")
        
        return self.scan_multiple(symbols, base_date, max_workers, progress)
    
    def save_results(
        self, 
        df: pd.DataFrame, 
        base_date: str = None,
        output_dir: str = './data'
    ) -> List[str]:
        """
        결과 저장
        
        Returns:
        --------
        List[str] : 저장된 파일 경로 리스트
        """
        import os
        os.makedirs(output_dir, exist_ok=True)
        
        if base_date is None:
            base_date = datetime.now().strftime('%Y%m%d')
        else:
            base_date = base_date.replace('-', '')
        
        saved_files = []
        
        # CSV 저장
        csv_path = os.path.join(output_dir, f'scan_result_{base_date}.csv')
        df.to_csv(csv_path, index=False, encoding='utf-8-sig')
        saved_files.append(csv_path)
        print(f"💾 CSV: {csv_path}")
        
        # Excel 저장
        if not df.empty:
            excel_path = os.path.join(output_dir, f'scan_result_{base_date}.xlsx')
            df.to_excel(excel_path, index=False, sheet_name='Scan Results')
            saved_files.append(excel_path)
            print(f"💾 Excel: {excel_path}")
        
        return saved_files
    
    def close(self):
        """리소스 정리"""
        self.repo.close()
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()


def main():
    """CLI 테스트"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Pivot Point Stock Scanner')
    parser.add_argument('--mode', choices=['single', 'multiple', 'all'], default='all',
                       help='Scan mode: single, multiple, or all')
    parser.add_argument('--symbols', nargs='+', help='Stock symbols to scan')
    parser.add_argument('--market', choices=['ALL', 'KOSPI', 'KOSDAQ'], default='ALL',
                       help='Market to scan')
    parser.add_argument('--date', help='Base date (YYYY-MM-DD)')
    parser.add_argument('--limit', type=int, help='Maximum number of stocks to scan')
    parser.add_argument('--workers', type=int, default=4, help='Number of parallel workers')
    
    args = parser.parse_args()
    
    print("🚀 Enhanced Stock Scanner")
    print("=" * 60)
    
    with EnhancedScanner() as scanner:
        if args.mode == 'single' and args.symbols:
            # 개별 종목 스캔
            result = scanner.scan_single(args.symbols[0], base_date=args.date)
            if result:
                print(f"\n✅ 신호 감지:")
                for k, v in result.items():
                    print(f"  {k}: {v}")
            else:
                print("\n❌ 신호 없음")
                
        elif args.mode == 'multiple' and args.symbols:
            # 여러 종목 스캔
            results = scanner.scan_by_symbols(args.symbols, args.date, args.workers)
            if not results.empty:
                scanner.save_results(results, args.date)
                print("\n🏆 TOP 5:")
                print(results.head()[['symbol', 'name', 'score', 'volume_ratio']].to_string(index=False))
                
        else:
            # 전체 종목 스캔
            results = scanner.scan_all(args.market, args.date, args.limit, args.workers)
            if not results.empty:
                scanner.save_results(results, args.date)
                print("\n🏆 TOP 10:")
                print(results.head(10)[['symbol', 'name', 'score', 'volume_ratio']].to_string(index=False))
    
    print("\n✅ 완료!")


if __name__ == "__main__":
    main()
