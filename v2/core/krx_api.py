#!/usr/bin/env python3
"""
KRX Open API Wrapper
한국거래소 묵제 API 연동

Features:
- 실시간 시세 조회
- 종목 목록 조회
- 지수 데이터 조회
- 주식정보 조회

API Docs: https://openapi.krx.co.kr/
"""

import os
import json
import requests
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from dotenv import load_dotenv

# Load API Key
load_dotenv('/root/.openclaw/workspace/strg/.env.krx')
API_KEY = os.getenv('KRX_API_KEY')
BASE_URL = "http://data-dbg.krx.co.kr/svc/apis"

class KRXAPI:
    """KRX Open API 클라이언트"""
    
    def __init__(self, api_key: str = None):
        self.api_key = api_key or API_KEY
        if not self.api_key:
            raise ValueError("KRX API Key가 필요합니다.")
        
        self.base_url = BASE_URL
        self.session = requests.Session()
        self.session.headers.update({
            'AUTH_KEY': self.api_key,
            'Accept': 'application/json',
            'User-Agent': 'Mozilla/5.0 (compatible; KRX-API-Client/1.0)'
        })
    
    def _get(self, endpoint: str, params: Dict = None) -> Dict:
        """API 호출 기본 메서드 (GET)"""
        url = f"{self.base_url}/{endpoint}"
        
        try:
            response = self.session.get(
                url,
                params=params,
                timeout=30
            )
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            print(f"KRX API Error: {e}")
            if hasattr(e.response, 'text'):
                print(f"Response: {e.response.text[:200]}")
            return {}
    
    def get_kospi_index(self, date: str = None) -> List[Dict]:
        """
        KOSPI 시리즈 지수 조회
        
        Args:
            date: 기준일자 (YYYYMMDD), None이면 오늘
        """
        if date is None:
            date = datetime.now().strftime('%Y%m%d')
        
        result = self._get(
            'idx/kospi_dd_trd',
            {'basDd': date}
        )
        return result.get('OutBlock_1', [])
    
    def get_kosdaq_index(self, date: str = None) -> List[Dict]:
        """
        KOSDAQ 시리즈 지수 조회
        
        Args:
            date: 기준일자 (YYYYMMDD), None이면 오늘
        """
        if date is None:
            date = datetime.now().strftime('%Y%m%d')
        
        result = self._get(
            'idx/kosdaq_dd_trd',
            {'basDd': date}
        )
        return result.get('OutBlock_1', [])
    
    def get_kospi_stocks(self, date: str = None) -> List[Dict]:
        """
        KOSPI 전종목 시세 조회
        
        Args:
            date: 기준일자 (YYYYMMDD), None이면 오늘
        """
        if date is None:
            date = datetime.now().strftime('%Y%m%d')
        
        result = self._get(
            'sto/stk_bydd_trd',
            {'basDd': date}
        )
        return result.get('OutBlock_1', [])
    
    def get_kosdaq_stocks(self, date: str = None) -> List[Dict]:
        """
        KOSDAQ 전종목 시세 조회
        
        Args:
            date: 기준일자 (YYYYMMDD), None이면 오늘
        """
        if date is None:
            date = datetime.now().strftime('%Y%m%d')
        
        result = self._get(
            'sto/ksq_bydd_trd',
            {'basDd': date}
        )
        return result.get('OutBlock_1', [])
    
    def get_stock_detail(self, stock_code: str, date: str = None) -> Optional[Dict]:
        """
        특정 종목 상세 정보 조회
        
        Args:
            stock_code: 종목코드 (6자리)
            date: 기준일자 (YYYYMMDD)
        """
        if date is None:
            date = datetime.now().strftime('%Y%m%d')
        
        # KOSPI 먼저 검색
        stocks = self.get_kospi_stocks(date)
        for stock in stocks:
            if stock.get('ISU_SRT_CD') == stock_code or stock.get('ISU_CD') == stock_code:
                return stock
        
        # KOSDAQ 검색
        stocks = self.get_kosdaq_stocks(date)
        for stock in stocks:
            if stock.get('ISU_SRT_CD') == stock_code or stock.get('ISU_CD') == stock_code:
                return stock
        
        return None
    
    def get_market_summary(self, date: str = None) -> Dict:
        """시장 전체 요약 정보"""
        if date is None:
            date = datetime.now().strftime('%Y%m%d')
        
        kospi = self.get_kospi_index(date)
        kosdaq = self.get_kosdaq_index(date)
        
        summary = {
            'date': date,
            'kospi': kospi[0] if kospi else None,
            'kosdaq': kosdaq[0] if kosdaq else None,
            'timestamp': datetime.now().isoformat()
        }
        return summary


def test_krx_api():
    """KRX API 테스트"""
    print("=" * 60)
    print("KRX Open API 연결 테스트")
    print("=" * 60)
    
    try:
        api = KRXAPI()
        print(f"✅ API Key 로드 성공: {api.api_key[:10]}...")
        print(f"   Base URL: {api.base_url}")
        
        # 테스트용 과거 날짜 (최근 영업일)
        test_date = '20250404'
        print(f"\n📅 테스트 날짜: {test_date}")
        
        # 1. KOSPI 지수 테스트
        print("\n📊 KOSPI 지수 조회...")
        kospi = api.get_kospi_index(test_date)
        if kospi:
            for idx in kospi[:3]:
                print(f"   {idx.get('IDX_NM', 'N/A')}: {idx.get('CLSPRC_IDX', 'N/A')} ({idx.get('FLUC_RT', 'N/A')}%)")
        else:
            print("   ⚠️ KOSPI 지수 데이터 없음 (API 권한 필요)")
        
        # 2. KOSDAQ 지수 테스트
        print("\n📈 KOSDAQ 지수 조회...")
        kosdaq = api.get_kosdaq_index(test_date)
        if kosdaq:
            for idx in kosdaq[:3]:
                print(f"   {idx.get('IDX_NM', 'N/A')}: {idx.get('CLSPRC_IDX', 'N/A')} ({idx.get('FLUC_RT', 'N/A')}%)")
        else:
            print("   ⚠️ KOSDAQ 지수 데이터 없음 (API 권한 필요)")
        
        # 3. KOSPI 종목 목록 테스트 (샘플 5개)
        print("\n🏢 KOSPI 종목 목록 조회 (샘플)...")
        stocks = api.get_kospi_stocks(test_date)
        if stocks:
            for stock in stocks[:5]:
                print(f"   {stock.get('ISU_ABBRV', 'N/A')} ({stock.get('ISU_SRT_CD', 'N/A')}): {stock.get('TDD_CLSPRC', 'N/A')}")
        else:
            print("   ⚠️ 종목 데이터 없음 (API 권한 필요)")
        
        # 4. 특정 종목 테스트
        print("\n🔍 삼성전자 상세 조회...")
        samsung = api.get_stock_detail('005930', test_date)
        if samsung:
            print(f"   종목명: {samsung.get('ISU_ABBRV', 'N/A')}")
            print(f"   종가: {samsung.get('TDD_CLSPRC', 'N/A')}")
            print(f"   등락률: {samsung.get('FLUC_RT', 'N/A')}%")
            print(f"   시가총액: {samsung.get('MKTCAP', 'N/A')}")
        else:
            print("   ⚠️ 종목 데이터 없음 (API 권한 필요)")
        
        print("\n" + "=" * 60)
        print("✅ KRX API 테스트 완료")
        print("=" * 60)
        print("\n💡 참고:")
        print("   - API Key 발급 후에도 각 서비스별 이용 신청 필요")
        print("   - https://openapi.krx.co.kr/ 에서 서비스 이용 신청")
        
    except Exception as e:
        print(f"\n❌ 오류 발생: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    return True


if __name__ == '__main__':
    test_krx_api()
