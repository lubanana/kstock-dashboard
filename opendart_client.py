"""
OpenDart API Client Example
Shows how to use the API key from environment variables
"""
import requests
import time
from typing import Optional, Dict, Any
from opendart_config import get_api_key, get_headers, OPENDART_BASE_URL, OPENDART_RATE_LIMIT

class OpenDartClient:
    """OpenDart API 클라이언트"""
    
    def __init__(self):
        self.api_key = get_api_key()
        self.base_url = OPENDART_BASE_URL
        self.headers = get_headers()
        self.last_request_time = 0
        self.min_interval = 1.0 / OPENDART_RATE_LIMIT  # Rate limit 준수
    
    def _rate_limit(self):
        """Rate limit 준수를 위한 대기"""
        elapsed = time.time() - self.last_request_time
        if elapsed < self.min_interval:
            time.sleep(self.min_interval - elapsed)
        self.last_request_time = time.time()
    
    def get_company_info(self, corp_code: str) -> Optional[Dict[str, Any]]:
        """
        기업 기본 정보 조회
        
        Parameters:
        -----------
        corp_code : str
            고유번호 (8자리)
        
        Returns:
        --------
        dict : 기업 정보
        """
        self._rate_limit()
        
        url = f"{self.base_url}/company.json"
        params = {
            'crtfc_key': self.api_key,
            'corp_code': corp_code
        }
        
        try:
            response = requests.get(url, params=params, headers=self.headers, timeout=30)
            response.raise_for_status()
            data = response.json()
            
            if data.get('status') == '000':
                return data
            else:
                print(f"⚠️ API Error: {data.get('message', 'Unknown error')}")
                return None
                
        except requests.exceptions.RequestException as e:
            print(f"❌ Request failed: {e}")
            return None
    
    def get_financial_statement(self, corp_code: str, bsns_year: str, reprt_code: str = '11011') -> Optional[Dict[str, Any]]:
        """
        재무제표 조회
        
        Parameters:
        -----------
        corp_code : str
            고유번호
        bsns_year : str
            사업연도 (YYYY)
        reprt_code : str
            보고서 코드 (11011: 사업보고서, 11012: 반기보고서, 11013: 분기보고서)
        
        Returns:
        --------
        dict : 재무제표 데이터
        """
        self._rate_limit()
        
        url = f"{self.base_url}/fnlttSinglAcnt.json"
        params = {
            'crtfc_key': self.api_key,
            'corp_code': corp_code,
            'bsns_year': bsns_year,
            'reprt_code': reprt_code
        }
        
        try:
            response = requests.get(url, params=params, headers=self.headers, timeout=30)
            response.raise_for_status()
            data = response.json()
            
            if data.get('status') == '000':
                return data
            else:
                print(f"⚠️ API Error: {data.get('message', 'Unknown error')}")
                return None
                
        except requests.exceptions.RequestException as e:
            print(f"❌ Request failed: {e}")
            return None
    
    def get_major_stockholders(self, corp_code: str, bsns_year: str) -> Optional[Dict[str, Any]]:
        """
        대량보유 상황보고 조회
        
        Parameters:
        -----------
        corp_code : str
            고유번호
        bsns_year : str
            사업연도 (YYYY)
        
        Returns:
        --------
        dict : 대량보유자 정보
        """
        self._rate_limit()
        
        url = f"{self.base_url}/hyslrSttus.json"
        params = {
            'crtfc_key': self.api_key,
            'corp_code': corp_code,
            'bsns_year': bsns_year,
            'reprt_code': '11011'
        }
        
        try:
            response = requests.get(url, params=params, headers=self.headers, timeout=30)
            response.raise_for_status()
            return response.json()
            
        except requests.exceptions.RequestException as e:
            print(f"❌ Request failed: {e}")
            return None


# 사용 예시
def example_usage():
    """OpenDart API 사용 예시"""
    print("🚀 OpenDart API Client Example")
    print("=" * 50)
    
    # 클라이언트 초기화 (자동으로 .env에서 API 키 로드)
    client = OpenDartClient()
    print(f"✅ API Key loaded: {client.api_key[:10]}...")
    print(f"   Base URL: {client.base_url}")
    print()
    
    # 예시: 삼성전자 조회 (corp_code는 OpenDart에서 제공하는 고유번호 사용)
    # 참고: 실제 사용시에는 corp_code 목록을 먼저 조회해야 함
    print("📊 Example: Get company info")
    print("   (Note: corp_code is required, not stock symbol)")
    print()
    
    # corp_code 조회 방법
    print("💡 How to get corp_code:")
    print("   1. Download corp code list from OpenDart")
    print("   2. Or use /corpCode.json API endpoint")
    print()
    
    print("✅ OpenDart Client is ready to use!")
    print("   from opendart_client import OpenDartClient")
    print("   client = OpenDartClient()")


if __name__ == '__main__':
    example_usage()
