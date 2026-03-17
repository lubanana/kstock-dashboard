"""
OpenDartReader Wrapper with Environment Variable Support
Uses API key from .env file
"""
import os
from pathlib import Path
from dotenv import load_dotenv
from typing import Optional, List, Dict, Any, Union
import pandas as pd

# Load .env file
env_path = Path(__file__).parent / '.env'
load_dotenv(dotenv_path=env_path, override=True)

# Import OpenDartReader
try:
    import OpenDartReader
except ImportError:
    raise ImportError("OpenDartReader not installed. Run: pip install OpenDartReader")


class DartReader:
    """
    OpenDartReader Wrapper Class
    Automatically loads API key from .env file
    """
    
    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize OpenDartReader with API key
        
        Parameters:
        -----------
        api_key : str, optional
            OpenDart API key. If not provided, loads from .env file
        """
        if api_key is None:
            api_key = os.getenv('OPENDART_API_KEY')
            if not api_key:
                raise ValueError(
                    "API key not found. Please set OPENDART_API_KEY in .env file "
                    "or pass it directly to the constructor."
                )
        
        self.api_key = api_key
        self.dart = OpenDartReader(api_key)
        print(f"✅ OpenDartReader initialized (API Key: {api_key[:10]}...)")
    
    # ============================================================
    # 1. 공시 정보 조회 (Disclosure Information)
    # ============================================================
    
    def list_disclosures(self, 
                         corp_code: str,
                         start_date: Optional[str] = None,
                         end_date: Optional[str] = None,
                         page_count: int = 100) -> pd.DataFrame:
        """
        공시 목록 조회
        
        Parameters:
        -----------
        corp_code : str
            고유번호 (8자리)
        start_date : str, optional
            시작일 (YYYYMMDD), None이면 1년 전
        end_date : str, optional
            종료일 (YYYYMMDD), None이면 오늘
        page_count : int
            페이지당 건수 (default: 100, max: 100)
        
        Returns:
        --------
        pd.DataFrame : 공시 목록
        """
        return self.dart.list(corp_code, start_date, end_date, page_count)
    
    def find_disclosures(self,
                         corp_name: str,
                         start_date: Optional[str] = None,
                         end_date: Optional[str] = None) -> pd.DataFrame:
        """
        기업명으로 공시 검색
        
        Parameters:
        -----------
        corp_name : str
            기업명 (예: '삼성전자')
        start_date : str, optional
            시작일 (YYYYMMDD)
        end_date : str, optional
            종료일 (YYYYMMDD)
        
        Returns:
        --------
        pd.DataFrame : 공시 목록
        """
        return self.dart.find(corp_name, start_date, end_date)
    
    def find_all_disclosures(self,
                             search_keyword: str,
                             start_date: Optional[str] = None,
                             end_date: Optional[str] = None) -> pd.DataFrame:
        """
        전체 기업 대상 공시 검색
        
        Parameters:
        -----------
        search_keyword : str
            검색어
        start_date : str, optional
            시작일 (YYYYMMDD)
        end_date : str, optional
            종료일 (YYYYMMDD)
        
        Returns:
        --------
        pd.DataFrame : 공시 목록
        """
        return self.dart.find_all(search_keyword, start_date, end_date)
    
    # ============================================================
    # 2. 기업 정보 조회 (Company Information)
    # ============================================================
    
    def get_company_info(self, corp_code: str) -> pd.DataFrame:
        """
        기업 개황 정보 조회
        
        Parameters:
        -----------
        corp_code : str
            고유번호 (8자리)
        
        Returns:
        --------
        pd.DataFrame : 기업 정보
        """
        return self.dart.company(corp_code)
    
    def get_corp_code(self, corp_name: str) -> Optional[str]:
        """
        기업명으로 고유번호 조회
        
        Parameters:
        -----------
        corp_name : str
            기업명 (예: '삼성전자')
        
        Returns:
        --------
        str : 고유번호 (8자리) or None
        """
        return self.dart.find_corp_code(corp_name)
    
    # ============================================================
    # 3. 사업보고서 (Annual Report)
    # ============================================================
    
    def get_major_stockholders(self, corp_code: str, year: str) -> pd.DataFrame:
        """
        최대주주 현황
        
        Parameters:
        -----------
        corp_code : str
            고유번호
        year : str
            연도 (YYYY)
        
        Returns:
        --------
        pd.DataFrame : 최대주주 정보
        """
        return self.dart.major_stockholders(corp_code, year)
    
    def get_major_stockholders_change(self, corp_code: str, year: str) -> pd.DataFrame:
        """
        최대주주 변동 현황
        
        Parameters:
        -----------
        corp_code : str
            고유번호
        year : str
            연도 (YYYY)
        
        Returns:
        --------
        pd.DataFrame : 변동 내역
        """
        return self.dart.major_stockholders_change(corp_code, year)
    
    def get_executives(self, corp_code: str, year: str) -> pd.DataFrame:
        """
        임원 현황
        
        Parameters:
        -----------
        corp_code : str
            고유번호
        year : str
            연도 (YYYY)
        
        Returns:
        --------
        pd.DataFrame : 임원 정보
        """
        return self.dart.executives(corp_code, year)
    
    def get_employee_status(self, corp_code: str, year: str) -> pd.DataFrame:
        """
        직원 현황
        
        Parameters:
        -----------
        corp_code : str
            고유번호
        year : str
            연도 (YYYY)
        
        Returns:
        --------
        pd.DataFrame : 직원 정보
        """
        return self.dart.employee(corp_code, year)
    
    def get_dividend_info(self, corp_code: str, year: str) -> pd.DataFrame:
        """
        배당 정보
        
        Parameters:
        -----------
        corp_code : str
            고유번호
        year : str
            연도 (YYYY)
        
        Returns:
        --------
        pd.DataFrame : 배당 정보
        """
        return self.dart.dividend(corp_code, year)
    
    # ============================================================
    # 4. 재무제표 (Financial Statements)
    # ============================================================
    
    def get_financial_statement(self,
                                 corp_code: str,
                                 year: str,
                                 report_code: str = '11011') -> pd.DataFrame:
        """
        재무제표 조회 (전체)
        
        Parameters:
        -----------
        corp_code : str
            고유번호
        year : str
            연도 (YYYY)
        report_code : str
            11011: 사업보고서, 11012: 반기보고서, 11013: 분기보고서, 11014: 3분기보고서
        
        Returns:
        --------
        pd.DataFrame : 재무제표
        """
        return self.dart.finstate(corp_code, year, report_code)
    
    def get_financial_statement_summary(self,
                                         corp_code: str,
                                         year: str,
                                         report_code: str = '11011') -> pd.DataFrame:
        """
        재무제표 요약
        
        Parameters:
        -----------
        corp_code : str
            고유번호
        year : str
            연도 (YYYY)
        report_code : str
            보고서 코드
        
        Returns:
        --------
        pd.DataFrame : 재무제표 요약
        """
        return self.dart.finstate_summary(corp_code, year, report_code)
    
    def get_financial_statement_all(self,
                                     corp_code: str,
                                     year: str) -> pd.DataFrame:
        """
        전체 재무제표 (연결/개별)
        
        Parameters:
        -----------
        corp_code : str
            고유번호
        year : str
            연도 (YYYY)
        
        Returns:
        --------
        pd.DataFrame : 전체 재무제표
        """
        return self.dart.finstate_all(corp_code, year)
    
    def get_xbrl(self,
                 corp_code: str,
                 year: str,
                 report_code: str = '11011') -> Any:
        """
        XBRL 재무제표 조회
        
        Parameters:
        -----------
        corp_code : str
            고유번호
        year : str
            연도 (YYYY)
        report_code : str
            보고서 코드
        
        Returns:
        --------
        XBRL data
        """
        return self.dart.xbrl(corp_code, year, report_code)
    
    # ============================================================
    # 5. 지분 공시 (Shareholding Disclosure)
    # ============================================================
    
    def get_major_shareholders_report(self,
                                       start_date: Optional[str] = None,
                                       end_date: Optional[str] = None) -> pd.DataFrame:
        """
        대량보유 상황보고
        
        Parameters:
        -----------
        start_date : str, optional
            시작일 (YYYYMMDD)
        end_date : str, optional
            종료일 (YYYYMMDD)
        
        Returns:
        --------
        pd.DataFrame : 대량보유자 정보
        """
        return self.dart.major_shareholders(start_date, end_date)
    
    def get_shareholders_change(self,
                                 start_date: Optional[str] = None,
                                 end_date: Optional[str] = None) -> pd.DataFrame:
        """
        임원·주요주주 특정증권등 소유상황 보고
        
        Parameters:
        -----------
        start_date : str, optional
            시작일 (YYYYMMDD)
        end_date : str, optional
            종료일 (YYYYMMDD)
        
        Returns:
        --------
        pd.DataFrame : 소유상황 변동
        """
        return self.dart.shareholders_change(start_date, end_date)
    
    # ============================================================
    # 6. Utility Methods
    # ============================================================
    
    def get_stock_code(self, corp_code: str) -> Optional[str]:
        """
        고유번호로 종목코드 조회
        
        Parameters:
        -----------
        corp_code : str
            고유번호
        
        Returns:
        --------
        str : 종목코드 (6자리) or None
        """
        return self.dart.get_stock_code(corp_code)
    
    def download_corp_codes(self, save_path: Optional[str] = None) -> pd.DataFrame:
        """
        전체 고유번호 목록 다운로드
        
        Parameters:
        -----------
        save_path : str, optional
            저장 경로
        
        Returns:
        --------
        pd.DataFrame : 고유번호 목록
        """
        return self.dart.download_corp_codes(save_path)


# ============================================================
# Example Usage
# ============================================================

def example():
    """OpenDartReader 사용 예시"""
    print("🚀 OpenDartReader Example")
    print("=" * 60)
    
    # 1. 초기화 (.env에서 API 키 자동 로드)
    dart = DartReader()
    
    # 2. 기업 검색
    print("\n📊 1. 기업 검색")
    corp_name = "삼성전자"
    corp_code = dart.get_corp_code(corp_name)
    print(f"   {corp_name} 고유번호: {corp_code}")
    
    # 3. 최근 공시 조회
    print(f"\n📋 2. {corp_name} 최근 공시 조회")
    disclosures = dart.find_disclosures(corp_name)
    if not disclosures.empty:
        print(f"   최근 공시 {len(disclosures)}건")
        print(disclosures[['corp_name', 'report_nm', 'rcept_dt']].head())
    
    # 4. 재무제표 조회
    print(f"\n💰 3. {corp_name} 2024년 재무제표")
    try:
        fs = dart.get_financial_statement(corp_code, '2024')
        if not fs.empty:
            print(f"   재무제표 항목 {len(fs)}개")
            print(fs[['sj_nm', 'account_nm', 'thstrm_amount']].head())
    except Exception as e:
        print(f"   ⚠️ Error: {e}")
    
    print("\n✅ Example completed!")


if __name__ == '__main__':
    example()
