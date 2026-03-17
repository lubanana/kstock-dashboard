# K-Stock Strategy Catalog
# 한국 주식 전략 카탈로그 - 빠른 참조 및 호출용

## 📋 전략 번호 체계

### 메인 카테고리
- **P**ivot Strategy: P 시리즈
- **B**uy Strength: B 시리즈
- **S**EPA/VCP: S 시리즈
- **M**ulti-Strategy: M 시리즈
- **V**alue (Buffett): V 시리즈

---

## 🎯 전략 목록

### P 시리즈 - Pivot Point Strategy

| 코드 | 전략명 | 설명 | 파일 |
|------|--------|------|------|
| P01 | **피벗 포인트 돌파** | 20일 고점 돌파 + 거래량 급증 | `pivot_strategy.py` |

**호출 예시:**
```python
from strategy_catalog import run_strategy
result = run_strategy('P01', date='2026-03-17')
```

---

### B 시리즈 - Buy Strength Score

| 코드 | 전략명 | 설명 | 파일 |
|------|--------|------|------|
| B01 | **Buy Strength A등급** | 추세+모멘텀+거래량 80점+ | `buy_strength_scanner.py` |
| B02 | **Buy Strength 월간** | 월간 누적 신호 분석 | `monthly_report_generator.py` |

**스코어링:**
- 추세 (40점): 정배열 + 눌림목
- 모멘텀 (30점): RSI 50-70 + MACD 상승
- 거래량 (30점): 20일 평균 대비 150%+

**호출 예시:**
```python
from strategy_catalog import run_strategy
result = run_strategy('B01', market='KOSPI', min_score=80)
```

---

### S 시리즈 - SEPA + VCP (Mark Minervini)

| 코드 | 전략명 | 설명 | 파일 |
|------|--------|------|------|
| S01 | **SEPA 트렌드 템플릿** | 8가지 추세 기준 필터 | `sepa_vcp_strategy.py` |
| S02 | **VCP 패턴** | 변동성 수축 패턴 감지 | `sepa_vcp_visualizer.py` |
| S03 | **VCP + 피벗** | VCP + 피벗 라인 돌파 | `sepa_vcp_scanner.py` |

**SEPA 8가지 기준:**
1. 주가 > MA150
2. MA150 > MA200
3. MA200 상승 추세
4. 52주 최고가 대비 25% 이내
5. RS Rating 상위 25%
6. 주가 > 10원
7. 거래대금 10억+
8. ADR > 1.5%

**호출 예시:**
```python
from strategy_catalog import run_strategy
result = run_strategy('S03', min_contractions=3)
```

---

### M 시리즈 - Multi-Strategy (5가지 조합)

| 코드 | 전략명 | 설명 | 파일 |
|------|--------|------|------|
| M01 | **S1: 거래대금 TOP20** | 20일 평균 거래대금 10억+ | `multi_strategy_scanner.py` |
| M02 | **S2: 턴어라운드** | 60일 저점 대비 10% 반등 + RSI 40-60 | `multi_strategy_scanner.py` |
| M03 | **S3: 신규 모멘텀** | MACD > 0 + RSI > 50 | `multi_strategy_scanner.py` |
| M04 | **S4: 2000억 돌파** | 당일 거래대금 2000억+ | `multi_strategy_scanner.py` |
| M05 | **S5: MA200 상승세** | 주가 > MA200 + MA200 상승 | `multi_strategy_scanner.py` |
| M10 | **멀티전략 종합** | 5가지 전략 조합 스캔 | `multi_strategy_scanner.py` |
| M11 | **백테스트** | 멀티전략 과거 검증 | `multi_strategy_backtest.py` |

**백테스트 결과:**
- 2026.01~03: +9.49% 수익
- 승률: 38.7%
- 최고 조합: S1+S3 (71.4% 승률)

**호출 예시:**
```python
from strategy_catalog import run_strategy
# 개별 전략
result_s1 = run_strategy('M01')
result_s2 = run_strategy('M02')
result_s3 = run_strategy('M03')

# 전체 조합
result_all = run_strategy('M10')

# 백테스트
backtest = run_strategy('M11', start='2026-01-01', end='2026-03-17')
```

---

### V 시리즈 - Buffett Value Strategy

| 코드 | 전략명 | 설명 | 파일 |
|------|--------|------|------|
| V01 | **그레이엄 순유동자산** | 저평가 + 거래량 증가 | `buffett_integrated_scanner.py` |
| V02 | **퀄리티 적정가** | ROE 15%+ + Moat + 적정가 | `buffett_integrated_scanner.py` |
| V03 | **배당성장** | 변동성 < 40% + 안정적 성장 | `buffett_integrated_scanner.py` |
| V10 | **버핏 3전략 종합** | 3가지 전략 동시 실행 | `buffett_integrated_scanner.py` |
| V11 | **백테스트** | 2024.01~2026.03 검증 | `buffett_backtester.py` |

**그레이엄 점수 기준:**
- 저평가 (30점): 52주 저가 대비 1.3 미만
- 거래량 (20점): 20일 평균 대비 1.5배+
- 모멘텀 (20점): 3개월 수익률 양수
- RSI (15점): 30-60 사이
- 추세 (15점): 정배열

**백테스트 결과 (27개월):**
| 전략 | 수익률 | CAGR | MDD | 승률 |
|------|--------|------|-----|------|
| 그레이엄 | +114.0% | 40.2% | 0.0% | 70.6% |
| 퀄리티 | +98.8% | 35.7% | -4.0% | 46.0% |
| 배당 | +56.3% | 21.9% | -3.4% | 76.0% |

**호출 예시:**
```python
from strategy_catalog import run_strategy

# 개별 전략
graham = run_strategy('V01')
quality = run_strategy('V02')
dividend = run_strategy('V03')

# 3전략 종합
all_buffett = run_strategy('V10')

# 백테스트
backtest = run_strategy('V11', period='27m')
```

---

## 🔧 빠른 호출 가이드

### Python 모듈 사용

```python
from strategy_catalog import run_strategy, get_strategy_info, list_strategies

# 1. 모든 전략 목록 보기
strategies = list_strategies()
print(strategies)

# 2. 특정 전략 정보 확인
info = get_strategy_info('M03')
print(info['description'])
print(info['criteria'])

# 3. 전략 실행
result = run_strategy('M03')  # S3: 신규 모멘텀

# 4. 여러 전략 순차 실행
for code in ['M01', 'M02', 'M03']:
    result = run_strategy(code)
    print(f"{code}: {len(result)}개 선정")

# 5. 조합 전략 실행
best_combo = run_strategy('M01')  # S1
best_combo = run_strategy('M03')  # S3
# S1+S3 조합이 역사적으로 71.4% 승률
```

### CLI 명령어

```bash
# 전략 실행
python strategy_cli.py --code M03

# 여러 전략 순차 실행
python strategy_cli.py --codes M01,M02,M03 --sequential

# 백테스트
python strategy_cli.py --code V11 --backtest --start 2024-01-01

# 결과 저장
python strategy_cli.py --code M10 --output ./results/
```

---

## 📊 전략 조합 추천

### 단기 모멘텀 포트폴리오
| 전략 | 비중 | 예상 수익 |
|------|------|----------|
| M03 (신규 모멘텀) | 40% | 높음 |
| B01 (Buy Strength) | 35% | 중간 |
| M05 (MA200 상승) | 25% | 안정적 |

### 가치 + 성장 균형 포트폴리오
| 전략 | 비중 | 예상 수익 |
|------|------|----------|
| V01 (그레이엄) | 30% | 높음 |
| V02 (퀄리티) | 50% | 중간 |
| V03 (배당) | 20% | 안정적 |

### 멀티팩터 고승률 포트폴리오
| 전략 | 비중 | 특징 |
|------|------|------|
| M01+S3 조합 | 60% | 71.4% 승률 (백테스트) |
| B01 | 30% | A등급만 |
| V03 | 10% | 방어적 |

---

## 📁 리포트 파일 위치

| 전략 코드 | HTML 리포트 | CSV 데이터 |
|-----------|-------------|------------|
| P01 | `scan_report_YYYYMMdd.html` | - |
| B01 | `buy_strength_report.html` | `buy_strength_YYYYMMDD.csv` |
| B02 | `feb2026_monthly_report.html` | `feb2026_*.csv` |
| M10 | `multi_strategy_report.html` | `multi_strategy_scan_*.csv` |
| M11 | `multi_strategy_backtest_report.html` | `trades.csv`, `daily_values.csv` |
| V01 | `buffett_graham_detailed_report.html` | `buffett_graham_*.csv` |
| V10 | `buffett_comprehensive_report_*.html` | `buffett_scan_*.json` |
| V11 | 백테스트 내장 | `buffett_backtest/*.csv` |

---

*최종 업데이트: 2026-03-17*
*총 18개 전략 등록 완료*
