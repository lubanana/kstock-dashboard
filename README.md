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
