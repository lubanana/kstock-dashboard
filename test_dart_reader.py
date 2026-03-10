#!/usr/bin/env python3
"""
OpenDartReader Test - 재무정보 수집 테스트 (수정版)

Requirements:
- pip install OpenDartReader
- DART API KEY (https://opendart.fss.or.kr/ 에서 발급)

핵심: DART는 종목코드(6자리)가 아닌 고유번호(8자리)를 사용합니다!
"""

import os
import pandas as pd
from datetime import datetime

# OpenDartReader 설치 확인
try:
    import OpenDartReader
except ImportError:
    print("📦 Installing OpenDartReader...")
    os.system("pip install OpenDartReader --break-system-packages -q")
    import OpenDartReader


class DartFinancialCollector:
    """DART 기반 재무정보 수집기"""
    
    def __init__(self, api_key: str = None):
        """
        초기화
        
        Args:
            api_key: DART API 키 (없으면 환경변수 DART_API_KEY 사용)
        """
        if api_key is None:
            api_key = os.environ.get('DART_API_KEY')
        
        if not api_key:
            raise ValueError("DART API KEY가 필요합니다.")
        
        self.api_key = api_key
        self.dart = OpenDartReader(api_key)
        print(f"✅ DART API initialized")
    
    def get_corp_code(self, stock_code: str) -> str:
        """
        종목코드(6자리)로 고유번호(8자리) 조회
        
        Returns:
            고유번호(8자리) 또는 None
        """
        try:
            # OpenDartReader의 find_corp_code 메서드 사용
            corp_code = self.dart.find_corp_code(stock_code)
            return corp_code
        except Exception as e:
            print(f"   ❌ Error finding corp_code for {stock_code}: {e}")
            return None
    
    def test_connection(self):
        """API 연결 테스트"""
        try:
            # 삼성전자 기업개황 조회
            company = self.dart.company('005930')
            print("\n🧪 API Connection Test")
            print("=" * 50)
            print(f"Company: {company.get('corp_name', 'N/A')}")
            print(f"Code: {company.get('stock_code', 'N/A')}")
            print(f"Corp Code: {company.get('corp_code', 'N/A')}")
            print(f"CEO: {company.get('ceo_nm', 'N/A')}")
            print(f"Sector: {company.get('induty_code', 'N/A')}")
            print("✅ API connection successful!")
            return True
        except Exception as e:
            print(f"❌ API connection failed: {e}")
            return False
    
    def get_financial_statement(self, stock_code: str, year: str = None, reprt_code: str = '11011'):
        """
        재무제표 조회
        
        Args:
            stock_code: 종목코드(6자리) - 005930
            year: 조회 연도 (None이면 전년)
            reprt_code: 보고서 코드
                - 11011: 사업보고서
                - 11012: 반기보고서  
                - 11013: 1분기보고서
                - 11014: 3분기보고서
        
        Returns:
            재무제표 DataFrame
        """
        if year is None:
            year = '2023'  # 2023년 데이터 조회 (2024년 사업보고서는 아직 제출 안됨)
        
        # 종목코드로 고유번호 조회
        corp_code = self.get_corp_code(stock_code)
        if not corp_code:
            print(f"   ⚠️  Could not find corp_code for {stock_code}")
            return None
        
        print(f"   🔍 Stock: {stock_code} → Corp: {corp_code}")
        
        try:
            # 재무제표 조회 (finstate 메서드 사용)
            fs = self.dart.finstate(corp_code, year, reprt_code)
            
            if fs is None or len(fs) == 0:
                print(f"   ⚠️  No financial data for {stock_code} in {year}")
                return None
            
            return fs
            
        except Exception as e:
            print(f"   ❌ Error fetching {stock_code}: {e}")
            return None
    
    def get_major_financials(self, stock_code: str, year: str = None) -> dict:
        """
        주요 재무정보 추출
        
        Returns:
            {
                'revenue': 매출액,
                'operating_profit': 영업이익,
                'net_income': 당기순이익,
                'total_assets': 총자산,
                'total_liabilities': 총부채,
                'total_equity': 총자본
            }
        """
        fs = self.get_financial_statement(stock_code, year)
        
        if fs is None:
            return None
        
        try:
            # 주요 항목 추출
            result = {}
            
            # 매출액 (손익계산서)
            revenue_row = fs[fs['account_nm'].str.contains('매출액|수익', na=False, regex=True)]
            if len(revenue_row) > 0:
                result['revenue'] = self._parse_amount(revenue_row.iloc[0]['thstrm_amount'])
            
            # 영업이익
            op_row = fs[fs['account_nm'].str.contains('영업이익', na=False)]
            if len(op_row) > 0:
                result['operating_profit'] = self._parse_amount(op_row.iloc[0]['thstrm_amount'])
            
            # 당기순이익
            net_row = fs[fs['account_nm'].str.contains('당기순이익|순이익', na=False)]
            if len(net_row) > 0:
                result['net_income'] = self._parse_amount(net_row.iloc[0]['thstrm_amount'])
            
            # 총자산 (재무상태표)
            asset_row = fs[fs['account_nm'].str.contains('자산총계|총자산', na=False)]
            if len(asset_row) > 0:
                result['total_assets'] = self._parse_amount(asset_row.iloc[0]['thstrm_amount'])
            
            # 총부채
            liab_row = fs[fs['account_nm'].str.contains('부채총계|총부채', na=False)]
            if len(liab_row) > 0:
                result['total_liabilities'] = self._parse_amount(liab_row.iloc[0]['thstrm_amount'])
            
            # 총자본
            equity_row = fs[fs['account_nm'].str.contains('자본총계|총자본', na=False)]
            if len(equity_row) > 0:
                result['total_equity'] = self._parse_amount(equity_row.iloc[0]['thstrm_amount'])
            
            return result
            
        except Exception as e:
            print(f"   ❌ Error parsing financials: {e}")
            return None
    
    def _parse_amount(self, amount_str) -> int:
        """금액 문자열을 정수로 변환"""
        if pd.isna(amount_str):
            return 0
        
        # 쉼표와 공백 제거
        amount_str = str(amount_str).replace(',', '').replace(' ', '')
        
        # 괄호는 음수
        if '(' in amount_str and ')' in amount_str:
            amount_str = amount_str.replace('(', '-').replace(')', '')
        
        try:
            return int(float(amount_str))
        except:
            return 0
    
    def test_financials(self):
        """재무정보 테스트"""
        print("\n🧪 Financial Statement Test")
        print("=" * 50)
        
        test_companies = [
            ('005930', '삼성전자'),
            ('000660', 'SK하이닉스'),
            ('035420', 'NAVER')
        ]
        
        for code, name in test_companies:
            print(f"\n📊 {name} ({code})")
            
            # 기업개황
            try:
                company = self.dart.company(code)
                print(f"   사업자번호: {company.get('bizr_no', 'N/A')}")
                print(f"   업종: {company.get('induty_code', 'N/A')}")
            except Exception as e:
                print(f"   ⚠️  Company info error: {e}")
            
            # 재무정보
            financials = self.get_major_financials(code)
            
            if financials:
                print(f"   매출액: {financials.get('revenue', 0):,}원")
                print(f"   영업이익: {financials.get('operating_profit', 0):,}원")
                print(f"   당기순이익: {financials.get('net_income', 0):,}원")
                print(f"   총자산: {financials.get('total_assets', 0):,}원")
                print(f"   총자본: {financials.get('total_equity', 0):,}원")
            else:
                print(f"   ⚠️  No financial data available")


def main():
    """메인 테스트"""
    print("=" * 60)
    print("🚀 OpenDartReader Test - 재무정보 수집")
    print("=" * 60)
    
    # API KEY 확인
    api_key = os.environ.get('DART_API_KEY')
    
    if not api_key:
        print("\n⚠️  DART_API_KEY 환경변수가 설정되지 않았습니다.")
        return
    
    try:
        # 테스트 실행
        collector = DartFinancialCollector(api_key)
        
        # 연결 테스트
        if collector.test_connection():
            # 재무정보 테스트
            collector.test_financials()
        
        print("\n" + "=" * 60)
        print("✅ Test Complete!")
        print("=" * 60)
        
    except Exception as e:
        print(f"\n❌ Test failed: {e}")


if __name__ == '__main__':
    main()
