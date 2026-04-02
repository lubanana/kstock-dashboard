# 한국 주식 데이터 인프라 현황 보고서

**작성일**: 2026-04-02  
**점검자**: Kimi Claw  
**대상**: /root/.openclaw/workspace/strg/data

---

## 📊 전체 현황 요약

| 구분 | 상태 | 비고 |
|:---|:---:|:---|
| **가격 데이터 (일봉)** | ✅ 양호 | pivot_strategy.db 완비 |
| **기술적 지표** | ⚠️ 부분 | 일부 DB에만 존재 |
| **분봉 데이터** | ❌ 없음 | 미구축 |
| **실시간 데이터** | ⚠️ 부분 | fdr_wrapper로 일부 지원 |
| **공시 데이터** | ✅ 양호 | DART DB 259MB |

---

## 🗄️ DB별 상세 현황

### ✅ 1. pivot_strategy.db (166.5 MB) - **주력 DB**
```
상태: ✅ 양호 (메인 데이터 소스)
테이블: stock_prices (1,833,007 rows)
기간: 2023-03-20 ~ 2026-04-02 (약 3년)
종목수: 3,556개
컬럼: symbol, date, Open, High, Low, Close, Volume
```

**활용**: 백테스트, 스캐닝, fdr_wrapper 기본 DB

---

### ⚠️ 2. level1_prices.db (0.5 MB) - **개선 필요**
```
상태: ⚠️ 부족 (단일 날짜)
테이블: price_data (3,286 rows)
기간: 2026-03-10 ~ 2026-03-10 (1일)
종목수: 3,286개
컬럼: code, name, market, date, open, high, low, close, volume, change_pct, ma5, ma20, ma60, rsi, macd, score, recommendation, status
```

**문제**: 역사 데이터 없음  
**해결책**: pivot_strategy.db에서 마이그레이션 (별도 스크립트 필요)

---

### ✅ 3. DART 공시 DB (283.6 MB)

| DB | 크기 | 내용 | 상태 |
|:---|:---:|:---|:---:|
| dart_cache.db | 259.9 MB | disclosures (458,271건) | ✅ 양호 |
| dart_financial.db | 1.8 MB | financial_data (13,144건) | ✅ 양호 |
| dart_focused.db | 21.9 MB | financial_statements (77,253건) | ✅ 양호 |

**활용**: NPS 스캐너, 재무 분석

---

### ⚠️ 4. 기타 레벨별 DB

| DB | 크기 | 상태 | 비고 |
|:---|:---:|:---:|:---|
| level1_daily.db | 0.6 MB | ⚠️ 부족 | 분석용, 최신화 필요 |
| level1_final.db | 0.6 MB | ⚠️ 부족 | 통합 데이터 |
| level1_consolidated.db | 0.0 MB | ❌ 비어있음 | 미사용 |
| minervini_signals.db | 0.1 MB | ✅ 양호 | SEPA 신호 371개 |
| livermore_signals.db | 0.0 MB | ⚠️ 부족 | 36개만 존재 |

---

## 🔧 구축 완료된 항목

### ✅ 완료 (작동 중)
1. **fdr_wrapper** - FinanceDataReader 캐싱 래퍼
   - DB: pivot_strategy.db 사용
   - 기간: 2023-03-20 ~ 현재 (3년+)
   - 종목: 3,556개

2. **DART 공시 수집 시스템**
   - 458,271건 공시 데이터
   - 77,253건 재무제표
   - 자동 업데이트 로직 존재

3. **기본 스캐너 인프라**
   - SEPA/VCP 스캐너
   - NPS 스캐너
   - KAGGRESSIVE 스캐너
   - IVF 스캐너 (v2.0)

---

## ⚠️ 누락된 항목 및 개선 필요사항

### P1-높음 (즉시 조치 권장)

#### 1. level1_prices.db 역사 데이터 백필
```
현재: 2026-03-10 단일 날짜
목표: 2023-01-01 ~ 현재 (3년+)
방법: pivot_strategy.db에서 마이그레이션
소요시간: 30분
```

#### 2. 일별 자동 업데이터
```
현재: 수동 실행 (daily_update_batch.py 등)
개선: Cron 자동화 필요
주기: 매일 18:00 (장 종료 후)
```

### P2-중간 (1주 내 조치)

#### 3. 기술적 지표 사전 계산
```
현재: 스캐너에서 실시간 계산
개선: DB에 RSI, MACD, 볼린저밴드 등 사전 저장
장점: 스캐너 속도 5~10배 향상
```

#### 4. 분봉 데이터 (선택적)
```
용도: 고빈도 트레이딩, 캔들 패턴 정밀 분석
방법: pykrx 또는 CCXT (암호화폐)
용량: 일봉의 240배 (1분봉 기준)
```

### P3-낮음 (필요시)

#### 5. 실시간 웹소켓 연결
```
용도: 실시간 시그널링
방법: 한국투자증권 API, eBest API
우선순위: 낮음 (일봉 기반 전략이므로)
```

---

## 🛠️ 즉시 실행 가능한 작업

### 1. level1_prices.db 백필 스크립트
```bash
cd /root/.openclaw/workspace/strg
python3 backfill_level1_prices.py
```

### 2. Cron 일별 업데이트 등록
```bash
# /etc/cron.d/kstock-updater
0 18 * * 1-5 root cd /root/.openclaw/workspace/strg && python3 daily_update_batch.py
```

### 3. fdr_wrapper 최신 데이터 확인
```python
from fdr_wrapper import FDRWrapper
fdr = FDRWrapper()
stats = fdr.get_cache_stats()
print(stats)
```

---

## 📈 데이터 활용 현황

| 전략/스캐너 | 사용 DB | 데이터 기간 | 상태 |
|:---|:---|:---:|:---:|
| Pivot Point Backtest | pivot_strategy.db | 3년 | ✅ |
| SEPA/VCP Scanner | pivot_strategy.db | 3년 | ✅ |
| NPS Scanner | dart_focused.db | 3년 | ✅ |
| KAGGRESSIVE | pivot_strategy.db | 3년 | ✅ |
| IVF Scanner | pivot_strategy.db | 3년 | ✅ |
| Level1 분석 | level1_prices.db | 1일 | ⚠️ |

---

## 🎯 결론 및 권장사항

### 핵심 발견
1. **pivot_strategy.db가 충분** - 3년치 데이터, 3,556종목
2. **fdr_wrapper가 정상 작동** - 캐싱, API 폴트백 모두 이상 없음
3. **level1_prices.db만 부족** - 단일 날짜 데이터, 백필 필요

### 즉시 조치 (오늘)
- [ ] level1_prices.db 백필 완료
- [ ] backfill 스크립트 수정 (에러 처리 개선)

### 단기 조치 (이번 주)
- [ ] 일별 업데이터 Cron 등록
- [ ] 데이터 품질 검증 자동화

### 중기 조치 (이번 달)
- [ ] 기술적 지표 사전 계산 테이블 생성
- [ ] 분봉 데이터 구축 (필요시)

---

## 📁 관련 파일

| 파일 | 설명 |
|:---|:---|
| `fdr_wrapper.py` | FinanceDataReader 캐싱 래퍼 |
| `check_data_infrastructure.py` | 현황 점검 스크립트 |
| `backfill_level1_prices.py` | 역사 데이터 백필 |
| `daily_update_batch.py` | 일별 업데이터 |
| `data/pivot_strategy.db` | 메인 가격 데이터 (166MB) |
| `data/level1_prices.db` | Level1 가격 데이터 (0.5MB) |

---

**보고서 생성**: 2026-04-02 11:50  
**다음 점검 예정**: 2026-04-09
