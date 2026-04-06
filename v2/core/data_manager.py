"""
V2 Core - Data Manager
DB 및 데이터 소스 통합 관리
"""
import sqlite3
import pandas as pd
from datetime import datetime, timedelta
from typing import Optional, List, Dict
import FinanceDataReader as fdr


class DataManager:
    """데이터 관리자 (싱글톤)"""
    _instance = None
    
    def __new__(cls, db_path: str = "data/level1_prices.db"):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self, db_path: str = "data/level1_prices.db"):
        if self._initialized:
            return
        self.db_path = db_path
        self._name_map: Dict[str, str] = {}
        self._initialized = True
    
    def _get_connection(self) -> sqlite3.Connection:
        """DB 연결 반환"""
        return sqlite3.connect(self.db_path)
    
    def load_stock_data(self, 
                       code: str, 
                       end_date: str, 
                       days: int = 60) -> Optional[pd.DataFrame]:
        """
        특정 종목 데이터 로드
        
        Args:
            code: 종목코드
            end_date: 종료일 (YYYY-MM-DD)
            days: 필요한 거래일 수
        """
        conn = self._get_connection()
        
        # 날짜 범위 계산 (넉넉히)
        end_dt = datetime.strptime(end_date, '%Y-%m-%d')
        start_dt = end_dt - timedelta(days=days * 2)  # 주말 고려
        start_date = start_dt.strftime('%Y-%m-%d')
        
        query = """
            SELECT * FROM price_data 
            WHERE code = ? AND date BETWEEN ? AND ?
            ORDER BY date ASC
        """
        df = pd.read_sql(query, conn, params=(code, start_date, end_date))
        conn.close()
        
        if len(df) < days // 2:  # 최소 데이터 체크
            return None
            
        df['date'] = pd.to_datetime(df['date'])
        return df
    
    def load_all_stocks(self,
                       date: str,
                       min_volume: Optional[int] = None) -> pd.DataFrame:
        """
        특정 일자 전체 종목 로드
        
        Args:
            date: 기준일 (YYYY-MM-DD)
            min_volume: 최소 거래량 필터
        """
        conn = self._get_connection()
        
        query = "SELECT * FROM price_data WHERE date = ?"
        params = [date]
        
        if min_volume:
            query += " AND volume >= ?"
            params.append(min_volume)
        
        df = pd.read_sql(query, conn, params=params)
        conn.close()
        
        return df
    
    def get_stock_name(self, code: str) -> str:
        """종목명 조회 (캐싱)"""
        if code in self._name_map:
            return self._name_map[code]
        
        conn = self._get_connection()
        query = "SELECT DISTINCT name FROM price_data WHERE code = ? LIMIT 1"
        result = pd.read_sql(query, conn, params=(code,))
        conn.close()
        
        name = result['name'].iloc[0] if len(result) > 0 else code
        self._name_map[code] = name
        return name
    
    def get_all_codes(self, date: str) -> List[str]:
        """특정 일자 모든 종목코드"""
        conn = self._get_connection()
        query = "SELECT DISTINCT code FROM price_data WHERE date = ?"
        codes = pd.read_sql(query, conn, params=(date,))['code'].tolist()
        conn.close()
        return codes
    
    def fetch_from_fdr(self,
                      code: str,
                      start_date: str,
                      end_date: str) -> Optional[pd.DataFrame]:
        """
        FinanceDataReader에서 데이터 fetch (백업용)
        """
        try:
            df = fdr.DataReader(code, start=start_date, end=end_date)
            if df.empty:
                return None
            df = df.reset_index()
            df.columns = ['date', 'open', 'high', 'low', 'close', 'volume', 'change']
            df['code'] = code
            df['date'] = df['date'].dt.strftime('%Y-%m-%d')
            return df
        except Exception:
            return None
