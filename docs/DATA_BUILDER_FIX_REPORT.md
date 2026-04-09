# 종목 주가 구축 프로그램 정리 보고서

## 문제점 분석

### 원인: DB 불일치
| DB 파일 | 테이블 | 사용처 | 상태 |
|:---|:---|:---|:---|
| `pivot_strategy.db` | `stock_prices` | fdr_wrapper, parallel_daily_update | ❌ 스캐너 미사용 |
| `level1_prices.db` | `price_data` | **스캐너 사용** | ⚠️ 업데이트 안됨 |

**결과**: 데이터 구축 프로그램은 `pivot_strategy.db`에 저장했지만, 스캐너는 `level1_prices.db`를 읽어서 **데이터 불일치 발생**

---

## 해결책

### 1. 통합 데이터 업데이터 생성
**파일**: `unified_daily_updater.py`
- `level1_prices.db`의 `price_data` 테이블에 직접 저장
- 스캐너와 동일 DB 사용으로 일관성 확보
- 병렬 처리 (8 workers)로 빠른 구축
- 자동 지표 계산 (MA, RSI, MACD)

### 2. fdr_wrapper 수정
**파일**: `fdr_wrapper.py`
- 기본 DB를 `level1_prices.db`로 변경
- `price_data` 테이블 스키마 지원
- 하위 호환성 유지

### 3. cron 정리
**제거된 중복 작업**:
- `parallel_daily_update.py` cron job 제거
- `daily_update_batch.py` cron job 제거

**새로 설정된 작업**:

| 시간 | 작업 | 설명 |
|:---|:---|:---|
| 07:30 | `unified_daily_updater.py` | 장마감 후 데이터 구축 (월-금) |
| 08:00 | `daily_scan.sh` | 스캐너 실행 및 리포트 생성 |

---

## 현재 구조

### 데이터 흐름
```
┌─────────────────────────────────────────────────────────────┐
│  19:30 KST (장마감 후)                                       │
│  unified_daily_updater.py ──────▶ level1_prices.db         │
│                                      (price_data 테이블)     │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│  08:00 KST (다음날)                                          │
│  scanner_2604_v7_hybrid.py ◀────── level1_prices.db         │
│           │                        (동일 DB 읽기)           │
│           ▼                                                 │
│  JSON + HTML 리포트 생성                                     │
│  GitHub Push                                                │
└─────────────────────────────────────────────────────────────┘
```

### 파일 구조
```
strg/
├── unified_daily_updater.py     # 메인 데이터 구축 (새로 생성)
├── fdr_wrapper.py               # 수정됨 (level1_prices.db 사용)
├── daily_scan.sh                # 수정됨 (unified updater 사용)
├── scanner_2604_v7_hybrid.py    # 통합 스캐너 (목표가 계산 포함)
├── diagnose_data_status.py      # 진단 도구 (새로 생성)
└── data/
    └── level1_prices.db         # 통합 DB (유일한 데이터 소스)
```

---

## 사용법

### 수동 데이터 구축
```bash
# 특정 날짜 데이터 구축
python3 unified_daily_updater.py --date 2026-04-09 --workers 8

# 오늘 데이터 구축
python3 unified_daily_updater.py --workers 8
```

### 데이터 상태 확인
```bash
python3 diagnose_data_status.py
```

### 스캐너 수동 실행
```bash
# 오늘 날짜 스캔
python3 scanner_2604_v7_hybrid.py

# 특정 날짜 스캔
python3 scanner_2604_v7_hybrid.py --date 2026-04-08
```

---

## cron 작업 현황

```bash
# 확인
 crontab -l
```

**현재 설정**:
```
# 매일 오전 8시 스캐너 실행
0 8 * * * /root/.openclaw/workspace/strg/daily_scan.sh >> /var/log/daily_scanner.log 2>&1

# 매일 오후 7:30 데이터 구축 (월-금)
30 19 * * 1-5 cd /root/.openclaw/workspace/strg && python3 unified_daily_updater.py --workers 8 >> /var/log/unified_updater.log 2>&1
```

---

## 로그 확인

```bash
# 데이터 구축 로그
tail -f /var/log/unified_updater.log

# 스캐너 로그
tail -f /var/log/daily_scanner.log

# 진단 도구로 상태 확인
python3 diagnose_data_status.py
```

---

## GitHub 커밋

| 커밋 | 설명 |
|:---|:---|
| `7c18c08` | Add data status diagnostic tool |
| `834bb6a` | Fix: Unify DB to level1_prices.db |
| `4dd7b65` | Add target/stoploss calculation module |

---

## 검증 결과

```
📊 데이터 구축 진단 보고서
============================================================
1️⃣ 총 데이터 레코드: 1,829,899개
2️⃣ 고유 종목 수: 3,560개
3️⃣ 데이터 기간: 2023-03-20 ~ 2026-04-08

4️⃣ 최근 5일간 데이터 현황:
   2026-04-08: 3,545개 ✅
   2026-04-07: 3,545개 ✅
   2026-04-06: 3,545개 ✅

✅ 어제(2026-04-08) 데이터 정상: 3,545개
```

---

**작성일**: 2026-04-09
