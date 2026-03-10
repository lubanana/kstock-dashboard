#!/usr/bin/env python3
"""
Korean Stock Fundamental Data Collector
한국 주식 재무정보 수집기

Options:
1. PyKRX (stable) - PER, PBR, EPS, BPS, 배당수익률
2. Naver Finance (web scraping) - 실시간 기업정보
3. DART-fss (official) - 정기공시 재무제표
4. KRX direct API - 시장데이터
"""

from pykrx import stock
from datetime import datetime
from typing import Dict, Optional, List
import pandas as pd


class FundamentalDataCollector:
    """재무정보 수집기 - PyKRX 기반"""
    
    def __init__(self):
        self.today = datetime.now().strftime('%Y%m%d')
        
    def get_fundamental(self, code: str) -> Optional[Dict]:
        """
        개별 종목 재무정보 수집
        
        Returns:
            {
                'per': float,
                'pbr': float,
                'eps': float,
                'bps': float,
                'dividend_yield': float,
                'market_cap': int,
                'shares': int
            }
        """
        try:
            # 1. 티커에서 6자리 코드 추출
            base_code = code.replace('.KS', '').replace('.KQ', '')
            
            # 2. 기본 정보 (PyKRX)
            df = stock.get_market_fundamental(self.today, base_code)
            if df is None or len(df) == 0:
                return None
            
            row = df.iloc[0]
            
            # 3. 시가총액
            cap_df = stock.get_market_cap(self.today, base_code)
            market_cap = cap_df.iloc[0]['시가총액'] if cap_df is not None else 0
            shares = cap_df.iloc[0]['상장주식수'] if cap_df is not None else 0
            
            return {
                'code': base_code,
                'date': self.today,
                'per': float(row.get('PER', 0)),
                'pbr': float(row.get('PBR', 0)),
                'eps': float(row.get('EPS', 0)),
                'bps': float(row.get('BPS', 0)),
                'dividend_yield': float(row.get('DIV', 0)),
                'market_cap': int(market_cap),
                'shares': int(shares),
                'source': 'pykrx'
            }
            
        except Exception as e:
            print(f"   ❌ Error fetching {code}: {e}")
            return None
    
    def get_batch_fundamentals(self, codes: List[str]) -> List[Dict]:
        """
        다중 종목 재무정보 수집
        """
        results = []
        total = len(codes)
        
        print(f"\\n📊 Fetching fundamentals for {total} stocks...")
        
        for i, code in enumerate(codes, 1):
            result = self.get_fundamental(code)
            if result:
                results.append(result)
                print(f"   [{i}/{total}] ✅ {code}: PER={result['per']:.1f}, PBR={result['pbr']:.1f}")
            else:
                print(f"   [{i}/{total}] ❌ {code}: Failed")
            
            # Rate limiting
            if i % 50 == 0:
                print(f"   📦 Progress: {i}/{total} ({i/total*100:.1f}%)")
        
        print(f"\\n✅ Complete: {len(results)}/{total} stocks")
        return results
    
    def get_all_krx_fundamentals(self) -> pd.DataFrame:
        """
        전체 KRX 종목 재무정보
        """
        print("\\n🚀 Fetching all KRX fundamentals...")
        
        df = stock.get_market_fundamental(self.today)
        
        print(f"✅ Retrieved {len(df)} stocks")
        print(f"\\nColumns: {list(df.columns)}")
        print(f"\\nSample:")
        print(df.head())
        
        return df


def test_collector():
    """테스트"""
    collector = FundamentalDataCollector()
    
    # 1. 개별 종목 테스트
    print("=" * 60)
    print("🧪 Single Stock Test")
    print("=" * 60)
    
    test_codes = ['005930', '000660', '035420']  # 삼성, SK하이닉스, NAVER
    
    for code in test_codes:
        result = collector.get_fundamental(code)
        if result:
            print(f"\\n📈 {result['code']}:")
            print(f"   PER: {result['per']:.1f}")
            print(f"   PBR: {result['pbr']:.1f}")
            print(f"   EPS: {result['eps']:,.0f}원")
            print(f"   BPS: {result['bps']:,.0f}원")
            print(f"   배당수익률: {result['dividend_yield']:.2f}%")
            print(f"   시총: {result['market_cap']/1e8:.0f}억원")
    
    # 2. 전체 종목 테스트 (샘플)
    print("\\n" + "=" * 60)
    print("🧪 Batch Test (10 stocks)")
    print("=" * 60)
    
    batch_codes = ['005930', '000660', '035420', '051910', '005380', 
                   '207940', '068270', '000270', '028260', '035720']
    
    results = collector.get_batch_fundamentals(batch_codes)
    
    # 3. 전체 KRX 테스트
    print("\\n" + "=" * 60)
    print("🧪 All KRX Test")
    print("=" * 60)
    
    all_df = collector.get_all_krx_fundamentals()
    
    print("\\n🏆 Top 10 by Lowest PER:")
    low_per = all_df.nsmallest(10, 'PER')
    print(low_per[['PER', 'PBR', 'EPS', 'BPS']])


if __name__ == '__main__':
    test_collector()
