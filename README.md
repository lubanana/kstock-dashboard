# 📊 K-Stock Strategy Dashboard

한국 주식(KOSPI/KOSDAQ) 다중 전략 백테스팅 및 스캐닝 플랫폼

## 🎯 전략 카탈로그 (Strategy Codes)

총 **18개 전략**을 코드화하여 빠르게 호출할 수 있습니다.

```bash
# CLI로 전략 실행
python strategy_cli.py run M03          # S3: 신규 모멘텀
python strategy_cli.py sequential M01,M02,M03  # 순차 실행
python strategy_cli.py best             # 추천 조합 보기
```

### 전략 코드 체계

| 시리즈 | 카테고리 | 설명 |
|--------|----------|------|
| **P** | Pivot Point | 피벗 포인트 돌파 전략 |
| **B** | Buy Strength | 매수 강도 점수 기반 |
| **S** | SEPA/VCP | Mark Minervini 전략 |
| **M** | Multi-Strategy | 5가지 전략 조합 |
| **V** | Value (Buffett) | 버핏 가치투자 3전략 |

---

## 📋 전략 목록

### P 시리즈 - Pivot Point
| 코드 | 이름 | 설명 |
|------|------|------|
| **P01** | 피벗 포인트 돌파 | 20일 고점 돌파 + 거래량 150%+ |

### B 시리즈 - Buy Strength Score
| 코드 | 이름 | 설명 | 파일 |
|------|------|------|------|
| **B01** | Buy Strength A등급 | 추세(40)+모멘텀(30)+거래량(30) 80점+ | `buy_strength_scanner.py` |
| **B02** | Buy Strength 월간 | 월간 누적 신호 분석 | `monthly_report_generator.py` |

**스코어링:**
- 추세 40점: 정배열(주가>20EMA>60EMA) + 눌림목
- 모멘텀 30점: RSI 50-70 + MACD Histogram 증가
- 거래량 30점: 20일 평균 대비 150%+

### S 시리즈 - SEPA + VCP (Mark Minervini)
| 코드 | 이름 | 설명 | 파일 |
|------|------|------|------|
| **S01** | SEPA 트렌드 템플릿 | 8가지 추세 기준 필터 | `sepa_vcp_strategy.py` |
| **S02** | VCP 패턴 | 변동성 수축 패턴 감지 | `sepa_vcp_visualizer.py` |
| **S03** | VCP + 피벗 | VCP 완성 + 피벗 돌파 | `sepa_vcp_scanner.py` |

**SEPA 8가지 기준:**
1. 주가 > MA150
2. MA150 > MA200
3. MA200 상승 추세
4. 52주 최고가 대비 25% 이내
5. RS Rating 상위 25%
6. 주가 > 10원
7. 거래대금 10억+
8. ADR > 1.5%

### M 시리즈 - Multi-Strategy (5가지 조합)
| 코드 | 이름 | 설명 | 백테스트 결과 |
|------|------|------|---------------|
| **M01** | S1: 거래대금 TOP20 | 20일 평균 거래대금 10억+ | 65% 승률 |
| **M02** | S2: 턴어라운드 | 60일 저점 대비 10% 반등 + RSI 40-60 | 30% (성능저하) |
| **M03** | S3: 신규 모멘텀 | MACD > 0 + RSI > 50 | **68% 승률** ⭐ |
| **M04** | S4: 2000억 돌파 | 당일 거래대금 2000억+ | 45% (조합용) |
| **M05** | S5: MA200 상승세 | 주가 > MA200 + MA200 상승 | 62% 승률 |
| **M10** | 멀티전략 종합 | 5가지 전략 조합 스캔 | - |
| **M11** | 멀티전략 백테스트 | 2026.01~03 검증 | +9.49% 수익 |

**백테스트 결과:**
- 기간: 2026.01~03 (2.5개월)
- 총 거래: 124회
- 승률: 38.7%
- 수익률: +9.49%
- **최고 조합: S1+S3 (71.4% 승률)**

### V 시리즈 - Buffett Value Strategy
| 코드 | 이름 | 설명 | 백테스트 (27개월) |
|------|------|------|-------------------|
| **V01** | 그레이엄 순유동자산 | 저평가 + 거래량 증가 | **+114.0% (CAGR 40.2%)** ⭐ |
| **V02** | 퀄리티 적정가 | ROE 15%+ + Moat + 적정가 | +98.8% (CAGR 35.7%) |
| **V03** | 배당성장 | 변동성 < 40% + 안정적 성장 | +56.3% (CAGR 21.9%) |
| **V10** | 버핏 3전략 종합 | 3가지 전략 동시 실행 | - |
| **V11** | 버핏 백테스트 | 2024.01~2026.03 검증 | 월별 리밸런싱 |

**그레이엄 점수 기준:**
- 저평가(30점): 52주 저가 대비 1.3 미만
- 거래량(20점): 20일 평균 대비 1.5배+
- 모멘텀(20점): 3개월 수익률 양수
- RSI(15점): 30-60 사이
- 추세(15점): 정배열

### N 시리즈 - NPS Value (국민연금 패턴)
| 코드 | 이름 | 설명 | 필터 | 파일 |
|------|------|------|------|------|
| **N01** | NPS 저평가 우량주 | 국민연금 장기 가치 투자 패턴 복제 | 4-Filters | `nps_value_scanner_real.py` |
| **N02** | NPS 알고리즘 문서 | 4-Filter 설계 문서 | - | `nps_scanner_algorithm.py` |

**4-Filter 알고리즘:**
```
[Filter 1: ROE] 3년 연속 10% ≤ ROE ≤ 15%
    Score = 100 - |ROE_AVG - 12.5%| × 1000

[Filter 2: PBR] PBR ≤ 1.0 OR 업종 하위 30%
    Score = Absolute(50) + Relative to Industry(50)

[Filter 3: NPS] 지분 ≥ 5% AND 2분기 유지/확대
    Score = min(70, 지분율×1000) + Trend Bonus(30)

[Filter 4: Dividend] 3년 평균 > 시장평균, 성향 20~50%
    Score = Yield(50) + Payout(50)
```

**가중치:**
- ROE: 40% (최우선)
- 배당: 25%
- 저평가: 20%
- NPS 지분: 15%

**세부 조건:**
- 금융업(은행/증권/보험) 제외
- 관리/환기종목 제외
- 시가총액 1,000억원 이상

**사용 방법:**
```bash
python nps_value_scanner_real.py              # 전체 스캔
python nps_value_scanner_real.py --limit 100  # 100개만 테스트
python strategy_cli.py run N01                # CLI로 실행
```

---

## 🚀 빠른 시작

### 1. 전략 목록 보기
```bash
python strategy_cli.py list
python strategy_cli.py list --category "Multi-Strategy"
```

### 2. 전략 정보 확인
```bash
python strategy_cli.py info M03
python strategy_cli.py info V01
```

### 3. 전략 실행
```bash
python strategy_cli.py run M03
```

### 4. 여러 전략 순차 실행
```bash
python strategy_cli.py sequential M01,M02,M03
```

### 5. 추천 조합 보기
```bash
python strategy_cli.py best
```

---

## 💎 추천 포트폴리오 (백테스트 기반)

### 1. 고승률 모멘텀
| 전략 | 비중 | 승률 | 특징 |
|------|------|------|------|
| M01 + M03 | 100% | **71.4%** | 거래대금 + 모멘텀 조합 |

### 2. 균형 잡힌 가치
| 전략 | 비중 | CAGR | 특징 |
|------|------|------|------|
| V01 (그레이엄) | 30% | 40.2% | 고성장 |
| V02 (퀄리티) | 50% | 35.7% | 핵심 포지션 |
| V03 (배당) | 20% | 21.9% | 안정적 |

### 3. 안정적 배당
| 전략 | 비중 | 승률 | 특징 |
|------|------|------|------|
| V03 (배당) | 70% | 76% | 방어적 |
| B01 (A등급) | 30% | - | 모멘텀 보완 |

---

## 📁 파일 구조

```
strg/
├── 📜 Strategy Catalog
│   ├── STRATEGY_CATALOG.md      # 전략 카탈로그 문서
│   ├── strategy_catalog.py      # Python 모듈
│   └── strategy_cli.py          # CLI 도구
│
├── 🎯 Pivot Strategy
│   ├── pivot_strategy.py
│   ├── pivot_report.py
│   └── multi_stock_scanner.py
│
├── ⚡ Buy Strength
│   ├── buy_strength_scanner.py
│   ├── monthly_report_generator.py
│   └── chart_generator_feb2026.py
│
├── 🔬 SEPA/VCP
│   ├── sepa_vcp_strategy.py
│   ├── sepa_vcp_visualizer.py
│   └── sepa_vcp_scanner.py
│
├── 🎲 Multi-Strategy
│   ├── multi_strategy_scanner.py
│   ├── multi_strategy_backtest.py
│   └── multi_strategy_report.html
│
├── 💎 Buffett Value
│   ├── buffett_integrated_scanner.py
│   ├── buffett_backtester.py
│   ├── buffett_report_generator.py
│   └── buffett_graham_detailed_report.html
│
├── 📊 Data & Reports
│   ├── data/
│   │   └── pivot_strategy.db      # 3,286종목 가격 데이터
│   └── reports/
│       ├── strategy_sequential/   # S1/S2/S3 결과
│       ├── multi_strategy_backtest/
│       └── buy_strength_monthly/
│
└── 🌐 GitHub Pages
    └── docs/
        ├── index.html             # 리포트 대시보드
        ├── buy_strength_report.html
        ├── multi_strategy_report.html
        └── buffett_*.html
```

---

## 🌐 GitHub Pages 리포트

| 리포트 | URL | 설명 |
|--------|-----|------|
| **대시보드** | https://lubanana.github.io/kstock-dashboard/ | 전체 리포트 목록 |
| **Buy Strength** | /buy_strength_report.html | A등급 18종목 |
| **Multi-Strategy** | /multi_strategy_report.html | 5전략 조합 |
| **Buffett 종합** | /buffett_comprehensive_report_*.html | 3전략 비교 |
| **그레이엄 상세** | /buffett_graham_detailed_report.html | 클릭 가능한 TOP 20 |

---

## 📊 데이터베이스

- **종목 수**: 3,286개 (KOSPI 1,619 + KOSDAQ 1,667)
- **기간**: 2024.01.02 ~ 2026.03.17 (약 2년)
- **행 수**: 638,329개
- **크기**: 81MB (SQLite)

---

## 🔧 설치 및 실행

### 요구사항
```bash
pip install -r requirements.txt
```

### Python 모듈 사용
```python
from strategy_catalog import run_strategy, run_sequential

# 개별 실행
result = run_strategy('M03')  # S3: 신규 모멘텀

# 순차 실행
results = run_sequential(['M01', 'M02', 'M03'])

# 정보 확인
info = get_strategy_info('V01')
print(info['backtest_result'])
```

---

## ⚠️ 면책 조항

- 이 프로그램은 **교육 목적**으로 제작되었습니다.
- 실제 투자에 사용하기 전에 충분한 검증이 필요합니다.
- 과거 성과가 미래 수익을 보장하지 않습니다.
- 투자의 책임은 투자자 본인에게 있습니다.

---

## 📈 성과 요약

| 전략 | 수익률 | CAGR | 승률 | MDD | 기간 |
|------|--------|------|------|-----|------|
| 그레이엄 (V01) | +114.0% | 40.2% | 70.6% | 0.0% | 27개월 |
| 퀄리티 (V02) | +98.8% | 35.7% | 46.0% | -4.0% | 27개월 |
| 배당 (V03) | +56.3% | 21.9% | 76.0% | -3.4% | 27개월 |
| 멀티전략 (M11) | +9.49% | - | 38.7% | -13.77% | 2.5개월 |
| S1+S3 조합 | - | - | **71.4%** | - | 2.5개월 |

---

*최종 업데이트: 2026-03-17*
*총 18개 전략 등록 완료*
