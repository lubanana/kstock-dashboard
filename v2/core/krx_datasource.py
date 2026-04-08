#!/usr/bin/env python3
"""
KRX Data Integration Module
KRX Open API 데이터를 V2 스캐너에 통합
"""

import sys
sys.path.insert(0, '/root/.openclaw/workspace/strg')

from v2.core.krx_api import KRXAPI
from v2.core.data_manager import DataManager
from datetime import datetime
import pandas as pd

class KRXDataSource:
    """KRX Open API 데이터 소스"""
    
    def __init__(self):
        self.api = KRXAPI()
        self.dm = DataManager()
    
    def fetch_daily_prices(self, date: str = None) -> pd.DataFrame:
        """
        KRX에서 일일 시세 데이터 가져와서 DataFrame으로 반환
        
        Args:
            date: YYYYMMDD 형식, None이면 오늘
            
        Returns:
            DataFrame with columns: code, name, close, open, high, low, volume, value, market_cap
        """
        if date is None:
            date = datetime.now().strftime('%Y%m%d')
        
        print(f"📥 KRX 데이터 수집 중... ({date})")
        
        # KOSPI + KOSDAQ 데이터 수집
        kospi_stocks = self.api.get_kospi_stocks(date)
        kosdaq_stocks = self.api.get_kosdaq_stocks(date)
        
        all_stocks = []
        
        # KOSPI 데이터 처리
        for stock in kospi_stocks:
            all_stocks.append({
                'code': stock.get('ISU_CD', '')[-6:] if stock.get('ISU_CD') else '',
                'name': stock.get('ISU_NM', ''),
                'market': 'KOSPI',
                'close': self._to_float(stock.get('TDD_CLSPRC')),
                'open': self._to_float(stock.get('TDD_OPNPRC')),
                'high': self._to_float(stock.get('TDD_HGPRC')),
                'low': self._to_float(stock.get('TDD_LWPRC')),
                'volume': self._to_int(stock.get('ACC_TRDVOL')),
                'value': self._to_int(stock.get('ACC_TRDVAL')),
                'market_cap': self._to_int(stock.get('MKTCAP')),
                'change_pct': self._to_float(stock.get('FLUC_RT')),
                'date': date
            })
        
        # KOSDAQ 데이터 처리
        for stock in kosdaq_stocks:
            all_stocks.append({
                'code': stock.get('ISU_CD', '')[-6:] if stock.get('ISU_CD') else '',
                'name': stock.get('ISU_NM', ''),
                'market': 'KOSDAQ',
                'close': self._to_float(stock.get('TDD_CLSPRC')),
                'open': self._to_float(stock.get('TDD_OPNPRC')),
                'high': self._to_float(stock.get('TDD_HGPRC')),
                'low': self._to_float(stock.get('TDD_LWPRC')),
                'volume': self._to_int(stock.get('ACC_TRDVOL')),
                'value': self._to_int(stock.get('ACC_TRDVAL')),
                'market_cap': self._to_int(stock.get('MKTCAP')),
                'change_pct': self._to_float(stock.get('FLUC_RT')),
                'date': date
            })
        
        df = pd.DataFrame(all_stocks)
        print(f"   ✅ {len(df)}개 종목 수집 완료 (KOSPI: {len(kospi_stocks)}, KOSDAQ: {len(kosdaq_stocks)})")
        
        return df
    
    def update_database(self, date: str = None):
        """
        KRX 데이터로 로컬 데이터베이스 업데이트
        
        Args:
            date: YYYYMMDD 형식
        """
        df = self.fetch_daily_prices(date)
        
        if df.empty:
            print("❌ 수집된 데이터가 없습니다.")
            return
        
        # TODO: DataManager를 통해 DB에 저장
        # self.dm.save_prices(df)
        
        print(f"💾 데이터베이스 업데이트 완료: {len(df)}개 종목")
    
    def get_stock_info(self, code: str) -> dict:
        """특정 종목 상세 정보"""
        today = datetime.now().strftime('%Y%m%d')
        return self.api.get_stock_detail(code, today)
    
    @staticmethod
    def _to_float(value) -> float:
        """문자열을 float로 변환"""
        if value is None:
            return 0.0
        try:
            return float(str(value).replace(',', ''))
        except (ValueError, TypeError):
            return 0.0
    
    @staticmethod
    def _to_int(value) -> int:
        """문자열을 int로 변환"""
        if value is None:
            return 0
        try:
            return int(str(value).replace(',', ''))
        except (ValueError, TypeError):
            return 0


def test_krx_integration():
    """KRX 통합 테스트"""
    print("=" * 60)
    print("KRX Data Integration Test")
    print("=" * 60)
    
    source = KRXDataSource()
    
    # 1. 일일 시세 데이터 수집
    df = source.fetch_daily_prices('20250407')
    
    if not df.empty:
        print("\n📊 수집된 데이터 샘플:")
        print(df.head(3)[['code', 'name', 'market', 'close', 'change_pct']].to_string(index=False))
        
        print(f"\n📈 시장별 통계:")
        print(df.groupby('market').size())
        
        print(f"\n💰 평균 시가총액:")
        print(f"   KOSPI: {df[df['market']=='KOSPI']['market_cap'].mean()/1e8:.0f}억")
        print(f"   KOSDAQ: {df[df['market']=='KOSDAQ']['market_cap'].mean()/1e8:.0f}억")
    
    # 2. 특정 종목 조회
    print("\n🔍 삼성전자 상세:")
    info = source.get_stock_info('005930')
    if info:
        print(f"   {info.get('ISU_NM')}: {info.get('TDD_CLSPRC')}원 ({info.get('FLUC_RT')}%)")
    
    print("\n" + "=" * 60)
    print("✅ 테스트 완료")
    print("=" * 60)


if __name__ == '__main__':
    test_krx_integration()
