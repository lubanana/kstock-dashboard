# KStock Dashboard

📈 한국 주식 정량 분석 및 백테스트 플랫폼

## 🌐 라이브 대시보드

**https://lubanana.github.io/kstock-dashboard**

## 📊 전략 성과 비교

### 백테스트 결과 (2025-01-01 ~ 2026-03-18)

| 전략 | 총 수익률 | 승률 | 평균 수익률 | 최종 자본 | 평가 |
|------|-----------|------|-------------|-----------|------|
| **V-Series + Fib + ATR** | **+109.50%** 🏆 | **56.3%** | **+6.73%** | **₩209,500,727** | ⭐⭐⭐⭐⭐ |
| M-Strategy v1 | -11.75% | 37.3% | -1.56% | ₩88,245,000 | ⚠️ |
| M-Strategy v2 | -16.67% | 34.7% | -1.35% | ₩83,334,399 | ⚠️ |
| S-Strategy | -17.80% | 27.8% | -2.49% | ₩82,199,922 | ⚠️ |
| B01 (Buffett Quality) | -35.67% | 8.7% | -8.45% | ₩64,329,540 | ❌ |

> **초기 자본**: ₩100,000,000 | **백테스트 기간**: 약 14개월

### 핵심 발견

```
✅ Fibonacci + ATR 기반 리스크 관리가 AI 예측보다 우수한 결과
✅ 가치 투자 + 기술적 분석 결합 (V-Series)이 최고의 성과
✅ 손익비 1:2+ 필터가 승률과 수익률 향상에 기여
⚠️ AI 예측 모델 (60% 신뢰도)은 실제 승률 27-37%에 그침
```

---

## 📋 전략 목록

### 🥇 V-Series (Value + Fibonacci + ATR)
**파일**: `v_series_fib_atr_backtest.py`

**전략 개요**:
- **진입**: Fibonacci 38.2%~50% 되돌림 구간
- **목표가**: Fibonacci 161.8% 확장
- **손절가**: ATR(14) × 1.5
- **필터**: 손익비 1:1.5 이상, 가치점수 65점+
- **리밸런싱**: 월간

**성과**:
- 총 거래: 64회
- 승률: 56.3% (36승/28패)
- 평균 손익비: 1:3.41
- 최대 수익: +33.81% (SK하이닉스)

**리포트**: [V_Series_Fib_ATR_Report.html](https://lubanana.github.io/kstock-dashboard/V_Series_Fib_ATR_Report.html)

---

### 🤖 AI 기반 전략들

#### M-Strategy + AI v1/v2
**파일**: `m_strategy_ai_backtest.py`, `m_strategy_ai_backtest_v2.py`

**전략 개요**:
- RandomForest + GradientBoosting 앙상블
- Primary 모델 (60% 신뢰도) + Meta 모델 (65% 신뢰도)
- 기술적 필터: RSI, Volume Ratio, ADX

**결과**: AI 예측 신뢰도와 실제 승률 간 큰 괴리 발생
- 예상 신뢰도: 60%+
- 실제 승률: 34-37%

#### S-Strategy + AI
**파일**: `s_strategy_ai_backtest.py`

**결과**: -17.80% (10승/36패)

#### B01 (Buffett + AI)
**파일**: `b01_ai_backtest.py`

**결과**: -35.67% (2승/23패) - 최저 성과

---

### 📈 기술적 분석 스캐너

| 전략 | 설명 | 파일 |
|------|------|------|
| **리버모어** | 52주 신고가 돌파 + 거래량 증가 | `livermore_scanner.py` |
| **오닐** | CANSLIM 기반 거래량 폭발 | `oneil_scanner.py` |
| **미너비니** | VCP (Volatility Contraction Pattern) | `minervini_scanner.py` |
| **SEPA VCP** | Mark Minervini 트렌드 템플릿 | `sepa_vcp_strategy.py` |
| **Pivot Point** | 피봇 포인트 브레이크아웃 | `pivot_strategy.py` |
| **Buy Strength** | 추세+모멘텀+거래량 종합 점수 | `buy_strength_scanner.py` |

---

### 💰 가치 투자 전략

| 전략 | 설명 | 파일 |
|------|------|------|
| **B01 (Buffett Quality)** | Graham + Quality + Dividend 통합 | `b01_scanner.py` |
| **Graham Net-Net** | 순유동자산 대비 저평가 | `buffett_strategy_1_graham_netnet.py` |
| **Quality Fair Price** | ROE 15%+ 적정가 매수 | `buffett_strategy_2_quality_fairprice.py` |
| **Dividend Machine** | 배당성장 + 배당수익률 | `buffett_strategy_3_dividend_machine.py` |
| **NPS Value** | 국민연금 기준 가치주 | `nps_value_scanner.py` |

---

## 📁 폴리더 구조

```
.
├── docs/                              # GitHub Pages 소스
│   ├── index.html                     # 대시보드 메인
│   ├── V_Series_Fib_ATR_Report.html   # ⭐ V-Series 리포트 (+109%)
│   ├── livermore_report.html          # 리버모어 리포트
│   ├── combined_strategy_report.html  # 통합 리포트
│   └── ...
│
├── reports/                           # 백테스트 결과
│   ├── v_series/                      # V-Series 결과
│   ├── m_strategy/                    # M-Strategy 결과
│   ├── s_strategy/                    # S-Strategy 결과
│   ├── b01_value/                     # B01 결과
│   ├── buffett_backtest/              # Buffett 전략 결과
│   └── ...
│
├── *.py                               # 스캐너 및 백테스터
│   ├── v_series_fib_atr_backtest.py   # ⭐ V-Series 백테스터
│   ├── m_strategy_ai_backtest_v2.py   # M-Strategy v2
│   ├── b01_ai_backtest.py             # B01 + AI
│   ├── livermore_scanner.py           # 리버모어 스캐너
│   ├── oneil_scanner.py               # 오닐 스캐너
│   └── ...
│
├── local_db.py                        # SQLite DB 관리
├── fdr_wrapper.py                     # FinanceDataReader 래퍼
└── data/
    └── pivot_strategy.db              # 주가 데이터 (3,286종목)
```

---

## 🚀 로컬 실행

### V-Series 백테스트 실행
```bash
cd /root/.openclaw/workspace/strg
python3 v_series_fib_atr_backtest.py
```

### 스캐너 실행
```bash
# 개별 스캐너
python3 livermore_scanner.py
python3 oneil_scanner.py
python3 minervini_scanner.py

# 통합 스캔
python3 buffett_integrated_scanner.py
```

### 리포트 생성
```bash
python3 v_series_report_generator.py
python3 b01_ai_report_generator.py
```

### 로컬 서버로 확인
```bash
python3 -m http.server 8080 --directory docs
```

---

## 💻 스캐너 코드 사용 예시

### 1. 리버모어 스캐너 (52주 신고가)
```python
from livermore_scanner import LivermoreScanner
import pandas as pd

# 스캐너 초기화
scanner = LivermoreScanner()

# 특정 종목 스캔
symbols = ['005930', '000660', '051910']
results = scanner.scan(symbols)

# 결과 확인
for stock in results:
    print(f"{stock['name']}: {stock['price']:,}원 (신고가 돌파)")
```

### 2. 오닐 스캐너 (CANSLIM)
```python
from oneil_scanner import ONeilScanner

scanner = ONeilScanner(
    min_eps_growth=0.25,      # 최소 EPS 성장률 25%
    min_relative_strength=80,  # 상대강도 80 이상
    min_volume_surge=2.0       # 거래량 2배 이상
)

# 스캔 실행
results = scanner.scan_market(
    start_date='2026-03-01',
    end_date='2026-03-18'
)

# 상위 10개 출력
for stock in results[:10]:
    print(f"{stock['code']} - RS: {stock['rs_score']}, Volume: {stock['volume_ratio']:.1f}x")
```

### 3. 미너비니 스캐너 (VCP)
```python
from minervini_scanner import MinerviniScanner

scanner = MinerviniScanner(
    max_contractions=4,        # 최대 4단계 수축
    min_rs_rank=80,            # RS 순위 80% 이상
    max_volatility_decrease=0.6 # 변동성 60% 이하로 축소
)

# VCP 패턴 검색
vcp_stocks = scanner.find_vcp_patterns(
    symbols=['035720', '068270'],
    lookback_days=60
)

for stock in vcp_stocks:
    print(f"{stock['code']}: {stock['contractions']}단계 수축, Pivot: {stock['pivot_price']}")
```

### 4. SEPA VCP 스캐너
```python
from sepa_vcp_strategy import SEPAVCPStrategy

strategy = SEPAVCPStrategy(
    trend_template=True,      # 트렌드 템플릿 적용
    min_rs_rank=80,
    vcp_contractions=3
)

# 백테스트
results = strategy.backtest(
    symbols=['005930', '000660'],
    start_date='2025-01-01',
    end_date='2026-03-18'
)

print(f"총 수익률: {results['total_return']:.2f}%")
print(f"승률: {results['win_rate']:.1f}%")
```

### 5. Pivot Point 스캐너
```python
from pivot_strategy import PivotStrategy

strategy = PivotStrategy(
    pivot_lookback=20,        # 20일 피봇
    volume_threshold=1.5,     # 거래량 1.5배
    min_price=1000           # 최소 주가 1,000원
)

# 피봇 브레이크아웃 탐지
breakouts = strategy.scan_breakouts(
    date='2026-03-18',
    market='KOSPI'
)

for stock in breakouts:
    print(f"{stock['code']}: 피봇 {stock['pivot_level']:,} 돌파!")
```

### 6. Buy Strength 스캐너
```python
from buy_strength_scanner import BuyStrengthScanner

scanner = BuyStrengthScanner(
    trend_weight=0.4,         # 추세 가중치 40%
    momentum_weight=0.3,      # 모멘텀 가중치 30%
    volume_weight=0.3         # 거래량 가중치 30%
)

# 종합 점수 계산
scores = scanner.calculate_scores(
    symbols=['005930', '035720', '068270']
)

# A등급 이상 필터링
a_grade = [s for s in scores if s['grade'] == 'A']
for stock in a_grade:
    print(f"{stock['name']}: {stock['total_score']:.1f}점 ({stock['grade']}등급)")
```

### 7. Buffett 스캐너 (B01)
```python
from b01_scanner import B01Scanner

scanner = B01Scanner(
    graham_weight=0.3,        # Graham 30%
    quality_weight=0.4,       # Quality 40%
    dividend_weight=0.3       # Dividend 30%
)

# 가치주 스캔
value_stocks = scanner.scan_value_stocks(
    min_market_cap=100000000000,  # 시총 1,000억 이상
    top_n=20
)

for stock in value_stocks:
    print(f"{stock['name']}: 가치점수 {stock['value_score']}/100")
```

### 8. NPS 가치 스캐너
```python
from nps_value_scanner import NPSValueScanner

scanner = NPSValueScanner()

# NPS 기준 가치주 필터링
nps_stocks = scanner.scan(
    min_dividend_yield=2.0,   # 배당수익률 2%+
    max_pe=15,                # PER 15 이하
    min_roe=10                # ROE 10%+
)

print(f"NPS 가치주 {len(nps_stocks)}개 발견")
for stock in nps_stocks[:5]:
    print(f"  - {stock['name']}: PER {stock['pe']}, ROE {stock['roe']}%")
```

### 9. V-Series Fibonacci + ATR 스캐너
```python
from v_series_fib_atr_backtest import ValueFibATRStrategy, BacktestEngine

# 전략 설정
strategy = ValueFibATRStrategy(
    value_score_threshold=65.0,   # 가치점수 65점+
    risk_reward_ratio=1.5,        # 1:1.5 손익비
    atr_multiplier=1.5,           # ATR × 1.5
    fib_entry_tolerance=0.05      # ±5% 허용
)

# 백테스트 엔진
engine = BacktestEngine(
    strategy=strategy,
    initial_capital=100_000_000,
    rebalance_days=30
)

# 백테스트 실행
results = engine.run_backtest(
    symbols=['005930', '000660', '051910'],
    start_date='2025-01-01',
    end_date='2026-03-18',
    max_positions=5
)

print(f"📊 V-Series 결과:")
print(f"  총 수익률: {results['total_return']:+.2f}%")
print(f"  승률: {results['win_rate']:.1f}%")
print(f"  최종 자본: ₩{results['final_capital']:,.0f}")
```

### 10. 통합 멀티 스트레티지 스캐너
```python
from buffett_integrated_scanner import IntegratedScanner

# 통합 스캐너 (모든 전략 병렬 실행)
scanner = IntegratedScanner(
    strategies=['livermore', 'oneil', 'minervini', 'buffett', 'v_series'],
    max_workers=5
)

# 전체 시장 스캔
all_results = scanner.scan_all(
    market='KOSPI',
    date='2026-03-18'
)

# 중복 제거 및 종합 점수 계산
combined = scanner.combine_results(all_results)

print("🔥 통합 추천 종목 TOP 10:")
for i, stock in enumerate(combined[:10], 1):
    strategies = ', '.join(stock['strategies'])
    print(f"{i}. {stock['name']} ({stock['code']}) - {strategies}")
```

---

## 📊 데이터베이스

- **종목 수**: 3,286개 (KOSPI 1,619 + KOSDAQ 1,667)
- **데이터 기간**: 2024-07-26 ~ 2026-03-18
- **데이터 소스**: FinanceDataReader (FDR)
- **캐싱**: SQLite 로컬 DB

---

## 🔄 자동 갱신

- **스캔 시간**: 매일 오전 7:00 (한국 시간)
- **배포 시간**: 매일 오전 7:30 (한국 시간)
- **데이터 소스**: FinanceDataReader (Yahoo Finance)

---

## 📝 주요 학습사항

### 1. AI 예측의 한계
- 60% 신뢰도 threshold 설정에도 실제 승률은 27-37%에 그침
- 과적합(overfitting) 또는 feature leakage 가능성
- 단순한 기술적 규칙이 복잡한 AI 모델보다 우수한 경우 존재

### 2. 리스크 관리의 중요성
- **ATR 기반 동적 손절**: 변동성에 적응하여 MDD 감소
- **Fibonacci 레벨**: 심리적 지지/저항 레벨 활용
- **손익비 필터**: 1:2 이상 필터링이 장기 수익률 향상에 기여

### 3. 전략 결합의 효과
- **가치 투자 + 기술적 분석**: V-Series의 성공
- **단순함의 미학**: 복잡한 AI보다 명확한 규칙 기반 전략이 유리

---

## ⚠️ 면책 조항

이 프로젝트는 **교육 및 연구 목적**으로 제작되었습니다.

- 모든 투자 결정은 본인의 책임입니다.
- 과거 성과가 미래 수익을 보장하지 않습니다.
- 이 정보에 의존한 투자 결과에 대해 책임지지 않습니다.
- 실제 투자 전 충분한 검증과 리스크 관리가 필요합니다.

---

## 📅 업데이트 이력

| 날짜 | 내용 |
|------|------|
| 2026-03-19 | V-Series + Fibonacci + ATR 백테스트 완료 (+109.50%) |
| 2026-03-19 | README 전략 성과 분석 섹션 추가 |
| 2026-03-18 | M-Strategy AI v2 백테스트 완료 |
| 2026-03-17 | Buffett 3-strategy 스캔 및 백테스트 완료 |
| 2026-03-16 | B01 AI 리포트 생성기 완성 |
| 2026-03-13 | SEPA VCP 전략 구현 완료 |
| 2026-03-12 | Pivot Point 전략 구현 완료 |

---

**제작**: lubanana  
**Repository**: https://github.com/lubanana/kstock-dashboard
