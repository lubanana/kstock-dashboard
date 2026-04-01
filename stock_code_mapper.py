#!/usr/bin/env python3
"""
Stock Code Mapper - DART/KRX/Naver 코드 매핑 시스템

KRX 코드 규칙:
- 기본: 6자리 숫자 (예: 017890)
- 특수 코드:
  - A0: 권리락 (Attachment)
  - N0: 신주인수권부사채 (BW)
  - M0: 신주인수권증서
  - K0: 구주주배정
  - etc.

DART: 6자리 숫자만 사용 (특수 코드 → 기본 코드 매핑 필요)
Naver: 6자리 숫자 코드 사용 (특수 코드 불필요, 기본 종목만 표시)
"""

import re
import sqlite3
from dataclasses import dataclass
from typing import Optional, List, Dict


@dataclass
class StockCodeMapping:
    """종목 코드 매핑 정보"""
    dart_code: str        # DART용 6자리 숫자
    krx_code: str         # KRX용 코드 (특수 문자 포함 가능)
    naver_code: str       # Naver용 6자리 숫자
    name: str             # 종목명
    code_type: str        # 'normal', 'attachment', 'bw', etc.
    
    @property
    def is_special(self) -> bool:
        """특수 코드 여부"""
        return not self.krx_code.isdigit()


class StockCodeMapper:
    """종목 코드 매핑 관리자"""
    
    # 특수 코드 접미사 패턴
    SPECIAL_SUFFIXES = {
        'A0': 'attachment',    # 권리락
        'N0': 'bw',           # 신주인수권부사채
        'M0': 'ws',           # 신주인수권증서
        'K0': 'rights',       # 구주주배정
        'S0': 's',            # 특수
        'C0': 'c',            # 전환사채
    }
    
    def __init__(self, db_path: str = 'data/pivot_strategy.db'):
        self.db_path = db_path
        self._mapping_cache: Dict[str, StockCodeMapping] = {}
        self._build_cache()
    
    def _build_cache(self):
        """DB에서 코드 매핑 캐시 구축"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('SELECT symbol, name FROM stock_info')
        for symbol, name in cursor.fetchall():
            mapping = self._create_mapping(symbol, name)
            self._mapping_cache[symbol] = mapping
            # dart_code로도 조회 가능하도록
            self._mapping_cache[mapping.dart_code] = mapping
        
        conn.close()
    
    def _create_mapping(self, krx_code: str, name: str) -> StockCodeMapping:
        """KRX 코드로부터 매핑 생성"""
        # 숫자만 추출 (6자리)
        digits = re.sub(r'[^0-9]', '', krx_code)
        dart_code = digits.zfill(6)[:6]
        
        # 코드 타입 판별
        code_type = 'normal'
        for suffix, type_name in self.SPECIAL_SUFFIXES.items():
            if krx_code.endswith(suffix):
                code_type = type_name
                break
        
        # 네이버 코드: 특수 코드는 기본 종목 코드로 매핑
        naver_code = dart_code
        
        return StockCodeMapping(
            dart_code=dart_code,
            krx_code=krx_code,
            naver_code=naver_code,
            name=name,
            code_type=code_type
        )
    
    def get_mapping(self, code: str) -> Optional[StockCodeMapping]:
        """코드로 매핑 조회"""
        return self._mapping_cache.get(code)
    
    def get_dart_code(self, code: str) -> Optional[str]:
        """DART용 코드 반환"""
        mapping = self.get_mapping(code)
        return mapping.dart_code if mapping else None
    
    def get_naver_code(self, code: str) -> Optional[str]:
        """Naver용 코드 반환"""
        mapping = self.get_mapping(code)
        return mapping.naver_code if mapping else None
    
    def get_naver_url(self, code: str, page: str = 'main') -> Optional[str]:
        """네이버 증권 URL 생성"""
        naver_code = self.get_naver_code(code)
        if not naver_code:
            return None
        
        urls = {
            'main': f'https://finance.naver.com/item/main.naver?code={naver_code}',
            'news': f'https://finance.naver.com/item/news_news.naver?code={naver_code}',
            'community': f'https://finance.naver.com/item/board.naver?code={naver_code}',
        }
        return urls.get(page)
    
    def get_all_by_dart_code(self, dart_code: str) -> List[StockCodeMapping]:
        """같은 DART 코드를 가진 모든 매핑 조회 (기본+특수)"""
        results = []
        for mapping in self._mapping_cache.values():
            if mapping.dart_code == dart_code:
                results.append(mapping)
        return results
    
    def list_special_codes(self) -> List[StockCodeMapping]:
        """특수 코드 목록 반환"""
        return [m for m in self._mapping_cache.values() if m.is_special]
    
    def normalize_code(self, code: str) -> str:
        """임의의 코드를 DART/네이버용 6자리 숫자로 정규화"""
        mapping = self.get_mapping(code)
        if mapping:
            return mapping.dart_code
        # 매핑 없으면 숫자만 추출
        return re.sub(r'[^0-9]', '', code).zfill(6)[:6]


def create_code_mapping_table():
    """DB에 코드 매핑 테이블 생성"""
    conn = sqlite3.connect('data/pivot_strategy.db')
    cursor = conn.cursor()
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS stock_code_mapping (
            krx_code TEXT PRIMARY KEY,
            dart_code TEXT NOT NULL,
            naver_code TEXT NOT NULL,
            name TEXT,
            code_type TEXT DEFAULT 'normal',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    cursor.execute('''
        CREATE INDEX IF NOT EXISTS idx_dart_code ON stock_code_mapping(dart_code)
    ''')
    
    # stock_info 데이터로 매핑 테이블 채우기
    mapper = StockCodeMapper()
    
    for mapping in mapper._mapping_cache.values():
        cursor.execute('''
            INSERT OR REPLACE INTO stock_code_mapping 
            (krx_code, dart_code, naver_code, name, code_type)
            VALUES (?, ?, ?, ?, ?)
        ''', (mapping.krx_code, mapping.dart_code, mapping.naver_code, 
              mapping.name, mapping.code_type))
    
    conn.commit()
    conn.close()
    print('✅ 코드 매핑 테이블 생성 완료!')


if __name__ == '__main__':
    # 테스트
    mapper = StockCodeMapper()
    
    print('='*70)
    print('📊 Stock Code Mapper 테스트')
    print('='*70)
    
    # 특수 코드 확인
    print('\n⚠️ 특수 코드 목록 (샘플):')
    special = mapper.list_special_codes()[:10]
    for s in special:
        print(f'   {s.krx_code} → DART: {s.dart_code}, Naver: {s.naver_code} ({s.code_type})')
    
    # 한국알콜 테스트
    print('\n📋 한국알콜 코드 매핑:')
    for code in ['017890', '0015N0']:
        m = mapper.get_mapping(code)
        if m:
            print(f'   {code} → DART: {m.dart_code}, Naver: {m.naver_code}')
            print(f'   네이버 URL: {mapper.get_naver_url(code)}')
    
    # 매핑 테이블 생성
    print('\n' + '='*70)
    create_code_mapping_table()
    print('='*70)
