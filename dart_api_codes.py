"""
OpenDART API Reference - 공시조회용 코드 정의
https://opendart.fss.or.kr/guide/detail.do?apiGrpCd=DS001&apiId=2019018
"""
from enum import Enum
from typing import Dict, List, Optional


class DisclosureKind(Enum):
    """공시종류 코드"""
    A = "정기공시"           # 사업보고서, 반기보고서, 분기보고서
    B = "주요사항보고서"      # 주요사항보고서
    C = "발행공시"           # 증권신고(집합투자), 증권신고(합병)
    D = "지분공시"           # 임원·주요주주특정증권등소유상황보고서
    E = "기타공시"           # 자기주식취득·처분, 전환사채등
    F = "외부감사관련"        # 감사보고서, 연결감사보고서
    G = "펀드공시"           # 펀드공시
    H = "자산유동화"         # 자산유동화
    I = "거래소공시"          # 거래소공시
    J = "공정위공시"          # 공정위공시


class DisclosureKindDetail(Enum):
    """공시상세종류 코드 (주요사항보고서 - B)"""
    # A: 정기공시
    A001 = "사업보고서"
    A002 = "반기보고서"
    A003 = "분기보고서"
    A004 = "등록법인결산서류(자본시장법이전)"
    
    # B: 주요사항보고서
    B001 = "주요사항보고서"
    B002 = "주요사항보고서(법인분할결정 등)"
    B003 = "주요사항보고서(사채발행결정 등)"
    B004 = "주요사항보고서(해외증권발행결정 등)"
    
    # C: 발행공시
    C001 = "증권신고(집합투자증권)"
    C002 = "증권신고(합병)"
    C003 = "증권신고(증권의예탁)"
    C004 = "신주인수권부사채모집"
    C005 = "사채권발행실적보고서"
    C006 = "신주인수권행사결과보고서"
    
    # D: 지분공시
    D001 = "임원·주요주주특정증권등소유상황보고서"
    D002 = "최대주주등소유주식변동신고서"
    D003 = "최대주주등소유주식변동신고서(신규상장등)"
    
    # E: 기타공시
    E001 = "자기주식취득·처분"
    E002 = "전환사채등의포괴적교환이전"
    E003 = "교환사채의교환청구"
    E004 = "채권은행등의의견표명"
    E005 = "종속회사의채무증권발행결정"
    E006 = "종속회사의주식취득"
    E007 = "종속회사의주식처분"
    
    # F: 외부감사관련
    F001 = "감사보고서"
    F002 = "연결감사보고서"
    F003 = "결산공시정정신고서"
    
    # G: 펀드공시
    G001 = "집합투자증권"
    G002 = "집합투자업"
    
    # H: 자산유동화
    H001 = "자산유동화계획"
    H002 = "사업·운용보고서"
    
    # I: 거래소공시
    I001 = "수시공시"
    I002 = "공정공시"
    
    # J: 공정위공시
    J001 = "대규모내국인투자"
    J002 = "대규모내국인투자변경"


# 공시종류별 상세코드 매핑
DISCLOSURE_KIND_MAP: Dict[str, List[str]] = {
    "A": ["A001", "A002", "A003", "A004"],
    "B": ["B001", "B002", "B003", "B004"],
    "C": ["C001", "C002", "C003", "C004", "C005", "C006"],
    "D": ["D001", "D002", "D003"],
    "E": ["E001", "E002", "E003", "E004", "E005", "E006", "E007"],
    "F": ["F001", "F002", "F003"],
    "G": ["G001", "G002"],
    "H": ["H001", "H002"],
    "I": ["I001", "I002"],
    "J": ["J001", "J002"],
}


# NPS 관심 공시 유형
NPS_RELEVANT_DISCLOSURES = [
    "D001",  # 임원·주요주주특정증권등소유상황보고서 (NPS 지분 관련)
    "D002",  # 최대주주등소유주식변동신고서
    "A001",  # 사업보고서 (재무정보)
    "A002",  # 반기보고서
    "A003",  # 분기보고서
]


# 투자 관련 주요 공시
INVESTMENT_RELEVANT_DISCLOSURES = [
    "B001",  # 주요사항보고서
    "C001",  # 증권신고(집합투자증권)
    "E001",  # 자기주식취득·처분
    "E002",  # 전환사채등의포괴적교환이전
    "E005",  # 종속회사의채무증권발행결정
]


def get_disclosure_name(kind: str, kind_detail: Optional[str] = None) -> str:
    """공시코드에 해당하는 이름 반환"""
    if kind_detail:
        try:
            return DisclosureKindDetail[kind_detail].value
        except KeyError:
            pass
    
    try:
        return DisclosureKind[kind].value
    except KeyError:
        return "Unknown"


def get_disclosure_filters(filter_type: str = "nps") -> List[str]:
    """
    특정 필터 타입에 해당하는 공시상세코드 반환
    
    Parameters:
    -----------
    filter_type : str
        'nps' - NPS 관심 공시
        'investment' - 투자 관련 주요 공시
        'all' - 전체 공시
    
    Returns:
    --------
    List[str] : 공시상세코드 리스트
    """
    if filter_type == "nps":
        return NPS_RELEVANT_DISCLOSURES
    elif filter_type == "investment":
        return INVESTMENT_RELEVANT_DISCLOSURES
    elif filter_type == "all":
        return [d.name for d in DisclosureKindDetail]
    else:
        return []


# API 에러 코드 정의
API_ERROR_CODES = {
    "000": "정상",
    "010": "등록되지 않은 키입니다.",
    "011": "사용할 수 없는 키입니다.",
    "012": "접근할 수 없는 IP입니다.",
    "013": "조회된 데이타가 없습니다.",
    "014": "파일이 존재하지 않습니다.",
    "020": "요청 제한을 초과하였습니다.",
    "021": "조회 가능한 회사 개수가 초과하였습니다.(최대 100건)",
    "100": "필드의 부적절한 값입니다.",
    "101": "부적절한 접근입니다.",
    "800": "시스템 점검으로 인한 서비스가 중지 중입니다.",
    "900": "정의되지 않은 오류가 발생하였습니다.",
    "901": "사용자 계정의 개인정보 보유기간이 만료되어 사용할 수 없는 키입니다.",
}


def get_error_message(code: str) -> str:
    """API 에러코드에 해당하는 메시지 반환"""
    return API_ERROR_CODES.get(code, f"Unknown error code: {code}")
