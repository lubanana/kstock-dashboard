"""
NPS Value Scanner - Algorithm Design Document
국민연금 장기 가치 투자 패턴 복제 알고리즘
"""

# ============================================================
# NPS Value Scanner Algorithm
# ============================================================

"""
┌─────────────────────────────────────────────────────────────────────────┐
│                         NPS VALUE SCANNER                               │
│                    National Pension Service Pattern                     │
└─────────────────────────────────────────────────────────────────────────┘

[INPUT]
  └─▶ 상장 종목 전체 데이터 (재무제표 + 지분공시)
      ├─ KOSPI/KOSDAQ 전 종목
      ├─ DART 재무제표 데이터
      └─ DART 지분공시 데이터

[PRE-FILTERING]
  ├─ 금융업 제외 (은행/증권/보험/금융지주)
  ├─ 관리/환기종목 제외
  └─ 시가총액 1,000억원 이상

[STEP 1: ROE FILTER] ───────────────────────────────────────────────────
  
  조건: 최근 3년 연속 ROE 10% ≤ ROE ≤ 15%
  
  계산식:
    ROE = 당기순이익 / 평균 자기자본 × 100
    
  3년 연속 검증:
    ├─ 2022년: ROE_2022
    ├─ 2023년: ROE_2023
    └─ 2024년: ROE_2024
    
  통과 조건:
    ALL(10% ≤ ROE_YYYY ≤ 15% for YYYY in [2022, 2023, 2024])
    
  점수 계산:
    ROE_SCORE = 100 - |ROE_AVG - 12.5%| × 1000 + CONSISTENCY_BONUS
    
    where:
      ROE_AVG = (ROE_2022 + ROE_2023 + ROE_2024) / 3
      CONSISTENCY_BONUS = 20 - STD(ROE) × 200 (max 20)

[STEP 2: PBR FILTER] ───────────────────────────────────────────────────
  
  조건: PBR ≤ 1.0 OR 업종 하위 30%
  
  계산식:
    PBR = 주가 / BPS(주당순자산)
    BPS = (자본총계 - 자본조정) / 발행주식수
    
  업종 비교:
    PBR_PERCENTILE = RANK(PBR) / COUNT(업종) × 100
    
  통과 조건:
    PBR ≤ 1.0 OR PBR_PERCENTILE ≤ 30%
    
  점수 계산:
    PBR_SCORE = ABSOLUTE_SCORE + RELATIVE_SCORE
    
    ABSOLUTE_SCORE:
      ├─ PBR ≤ 0.5: 50점
      ├─ 0.5 < PBR ≤ 1.0: 40 + (1.0 - PBR) × 20점
      ├─ 1.0 < PBR ≤ 1.5: 20 + (1.5 - PBR) × 40점
      └─ PBR > 1.5: max(0, 30 - (PBR - 1.5) × 20)점
      
    RELATIVE_SCORE (vs 업종 평균):
      ├─ PBR ≤ 업종평균 × 0.7: 30점
      ├─ 업종평균 × 0.7 < PBR ≤ 업종평균: 20 + (1 - 상대비율) × 33점
      └─ PBR > 업종평균: max(0, 20 - (상대비율 - 1) × 30)점

[STEP 3: NPS OWNERSHIP FILTER] ─────────────────────────────────────────
  
  조건: 국민연금 지분율 ≥ 5% AND 최근 2분기 유지/확대
  
  데이터 소스: DART major_shareholders API
  
  검색 키워드: "국민연금공단", "국민연금"
  
  지분율 추적:
    ├─ CURRENT_Q: 현재 분기 지분율
    ├─ PREV_Q: 전분기 지분율
    └─ PREV_PREV_Q: 전전분기 지분율
    
  통과 조건:
    CURRENT_Q ≥ 5% AND CURRENT_Q ≥ PREV_Q
    
  트렌드 분류:
    ├─ INCREASING: CURRENT_Q > PREV_Q × 1.01
    ├─ STABLE: |CURRENT_Q - PREV_Q| ≤ PREV_Q × 0.01
    └─ DECREASING: CURRENT_Q < PREV_Q × 0.99
    
  점수 계산:
    NPS_SCORE = min(70, 지분율 × 1000) + TREND_BONUS
    
    TREND_BONUS:
      ├─ INCREASING: +30점
      ├─ STABLE: +15점
      └─ DECREASING: +0점

[STEP 4: DIVIDEND FILTER] ──────────────────────────────────────────────
  
  조건: 3년 평균 배당수익률 > 시장평균 AND 배당성향 20~50%
  
  계산식:
    배당수익률 = (주당배당금 / 주가) × 100
    배당성향 = (배당금총액 / 당기순이익) × 100
    
  3년 평균:
    DIV_YIELD_AVG = (DY_2022 + DY_2023 + DY_2024) / 3
    
  통과 조건:
    DIV_YIELD_AVG > KOSPI_AVG_DY AND 20% ≤ PAYOUT_RATIO ≤ 50%
    
  점수 계산:
    DIVIDEND_SCORE = YIELD_SCORE + PAYOUT_SCORE
    
    YIELD_SCORE = min(50, DIV_YIELD_AVG × 15)
    
    PAYOUT_SCORE:
      ├─ 20% ≤ PAYOUT ≤ 50%: 50 - |PAYOUT - 35%| × 100
      └─ 그 외: 0점

[SCORING & RANKING] ─────────────────────────────────────────────────────
  
  최종 점수 = 가중치 적용
  
  WEIGHTS:
    ├─ ROE_SCORE × 0.40 (40%)
    ├─ DIVIDEND_SCORE × 0.25 (25%)
    ├─ VALUATION_SCORE × 0.20 (20%)
    └─ NPS_SCORE × 0.15 (15%)
    
  TOTAL_SCORE = Σ(WEIGHT_i × SCORE_i)
  
  RANKING:
    └─ TOTAL_SCORE 내림차순 정렬
    
[OUTPUT]
  └─▶ 최종 스코어링 상위 20개 종목 리스트
      ├─ JSON format
      ├─ CSV format
      └─ HTML Report

"""

# ============================================================
# Implementation Guide
# ============================================================

IMPLEMENTATION_STEPS = """
1. 데이터 소스 설정
   ├─ fdr_wrapper: 주가/시총 데이터
   ├─ dart_disclosure_wrapper: 재무제표/지분 데이터
   └─ SQLite 캐싱: API 호출 최소화

2. 데이터 수집 파이프라인
   ├─ Step 1: 전 종목 기본 정보 로드
   ├─ Step 2: DART corp_code 매핑
   ├─ Step 3: 3년 재무제표 일괄 수집
   ├─ Step 4: NPS 지분 데이터 수집
   └─ Step 5: 배당 데이터 수집

3. 필터링 및 스코어링
   ├─ Vectorized operations for speed
   ├─ Parallel processing for API calls
   └─ Incremental caching

4. 결과 산출
   ├─ TOP 20 선정
   ├─ HTML 리포트 생성
   └─ GitHub 업로드
"""

# ============================================================
# Sample Output Format
# ============================================================

SAMPLE_OUTPUT = {
    "scan_date": "2026-03-17",
    "scan_parameters": {
        "roe_min": 0.10,
        "roe_max": 0.15,
        "pbr_max": 1.0,
        "nps_min_ownership": 0.05,
        "min_market_cap": 100000000000
    },
    "results": [
        {
            "rank": 1,
            "symbol": "005930",
            "name": "삼성전자",
            "sector": "전기전자",
            "market_cap": 450000000000000,
            "roe_avg": 0.128,
            "roe_2022": 0.125,
            "roe_2023": 0.130,
            "roe_2024": 0.129,
            "pbr": 0.85,
            "nps_ownership": 0.072,
            "nps_trend": "increasing",
            "dividend_yield": 0.025,
            "payout_ratio": 0.35,
            "scores": {
                "roe": 92.5,
                "dividend": 78.3,
                "valuation": 85.0,
                "nps": 88.0
            },
            "total_score": 85.7
        }
    ]
}

# ============================================================
# Key Metrics Dictionary
# ============================================================

METRICS = {
    "ROE": {
        "full_name": "Return on Equity",
        "korean": "자기자본이익률",
        "formula": "당기순이익 / 평균자기자본",
        "ideal_range": "10~15%",
        "weight": 0.40
    },
    "PBR": {
        "full_name": "Price to Book Ratio",
        "korean": "주가순자산비율",
        "formula": "주가 / BPS",
        "ideal_range": "≤ 1.0x",
        "weight": 0.20
    },
    "NPS": {
        "full_name": "National Pension Service Ownership",
        "korean": "국민연금 지분율",
        "formula": "NPS 보유주식 / 총발행주식",
        "ideal_range": "≥ 5%",
        "weight": 0.15
    },
    "DIVIDEND": {
        "full_name": "Dividend Yield & Payout",
        "korean": "배당수익률 및 성향",
        "formula": "DPS / 주가, DPS / EPS",
        "ideal_range": "시장평균+, 20~50%",
        "weight": 0.25
    }
}

if __name__ == '__main__':
    print(__doc__)
    print("\n" + "=" * 70)
    print("NPS Value Scanner Algorithm Design Document")
    print("=" * 70)
    print(f"\nKey Metrics:")
    for key, value in METRICS.items():
        print(f"\n  {key} ({value['korean']}):")
        print(f"    Formula: {value['formula']}")
        print(f"    Ideal: {value['ideal_range']}")
        print(f"    Weight: {value['weight']*100:.0f}%")
