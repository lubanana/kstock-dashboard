# 🔍 코드 분석 및 취약점 리포트
## 2026년 04월 08일 오전 2시 기준

---

## 📊 분석 개요

| 항목 | 개수 |
|:---|:---:|
| 🔴 보안 취약점 | 64개 |
| 💡 개선점 | 108개 |
| ⚡ 성능 이슈 | 70개 |
| 📝 코드 품질 | 0개 |

---

## 🔴 보안 취약점

### 1. Bare Except Clause
- **파일:** `global_market_analyzer.py`
- **심각도:** LOW
- **설명:** bare except: 사용. 구체적인 예외 지정 권장.
- **라인:** 163

### 2. Bare Except Clause
- **파일:** `global_market_analyzer.py`
- **심각도:** LOW
- **설명:** bare except: 사용. 구체적인 예외 지정 권장.
- **라인:** 179

### 3. SQL Injection Risk
- **파일:** `watchdog_hybrid.py`
- **심각도:** HIGH
- **설명:** 문자열 포맷팅을 사용한 SQL 쿼리 발견. 파라미터화된 쿼리 사용 권장.

### 4. Bare Except Clause
- **파일:** `dashboard.py`
- **심각도:** LOW
- **설명:** bare except: 사용. 구체적인 예외 지정 권장.
- **라인:** 57

### 5. Bare Except Clause
- **파일:** `dashboard.py`
- **심각도:** LOW
- **설명:** bare except: 사용. 구체적인 예외 지정 권장.
- **라인:** 63

### 6. Bare Except Clause
- **파일:** `dashboard.py`
- **심각도:** LOW
- **설명:** bare except: 사용. 구체적인 예외 지정 권장.
- **라인:** 69

### 7. Bare Except Clause
- **파일:** `dashboard.py`
- **심각도:** LOW
- **설명:** bare except: 사용. 구체적인 예외 지정 권장.
- **라인:** 75

### 8. Bare Except Clause
- **파일:** `dashboard.py`
- **심각도:** LOW
- **설명:** bare except: 사용. 구체적인 예외 지정 권장.
- **라인:** 81

### 9. Bare Except Clause
- **파일:** `investigation_report.py`
- **심각도:** LOW
- **설명:** bare except: 사용. 구체적인 예외 지정 권장.
- **라인:** 39

### 10. Bare Except Clause
- **파일:** `investigation_report.py`
- **심각도:** LOW
- **설명:** bare except: 사용. 구체적인 예외 지정 권장.
- **라인:** 48

## 💡 개선점

### 1. Excessive Print Statements
- **파일:** `global_market_analyzer.py`
- **우선순위:** MEDIUM
- **설명:** print() 문이 46개 발견. 로깅 라이브러리 사용 권장.

### 2. Excessive Print Statements
- **파일:** `daily_level1_fdr.py`
- **우선순위:** MEDIUM
- **설명:** print() 문이 33개 발견. 로깅 라이브러리 사용 권장.

### 3. Excessive Print Statements
- **파일:** `paper_trading_65.py`
- **우선순위:** MEDIUM
- **설명:** print() 문이 32개 발견. 로깅 라이브러리 사용 권장.

### 4. Excessive Print Statements
- **파일:** `backfill_level1_prices.py`
- **우선순위:** MEDIUM
- **설명:** print() 문이 27개 발견. 로깅 라이브러리 사용 권장.

### 5. Excessive Print Statements
- **파일:** `strategy_comparison_backtest.py`
- **우선순위:** MEDIUM
- **설명:** print() 문이 36개 발견. 로깅 라이브러리 사용 권장.

### 6. Large File
- **파일:** `strategy_comparison_backtest.py`
- **우선순위:** LOW
- **설명:** 파일이 512줄로 큼. 모듈 분리 검토.

### 7. Excessive Print Statements
- **파일:** `dart_batch_collector.py`
- **우선순위:** MEDIUM
- **설명:** print() 문이 28개 발견. 로깅 라이브러리 사용 권장.

### 8. Excessive Print Statements
- **파일:** `bithumb_trading_simulator.py`
- **우선순위:** MEDIUM
- **설명:** print() 문이 44개 발견. 로깅 라이브러리 사용 권장.

### 9. Large File
- **파일:** `bithumb_trading_simulator.py`
- **우선순위:** LOW
- **설명:** 파일이 551줄로 큼. 모듈 분리 검토.

### 10. Excessive Print Statements
- **파일:** `strict_mode_backtest.py`
- **우선순위:** MEDIUM
- **설명:** print() 문이 39개 발견. 로깅 라이브러리 사용 권장.

## ⚡ 성능 이슈

### 1. Blocking Sleep
- **파일:** `daily_level1_fdr.py`
- **심각도:** LOW
- **설명:** time.sleep() 사용 1회. 비동기 처리 검토.

### 2. Blocking Sleep
- **파일:** `watchdog_hybrid.py`
- **심각도:** LOW
- **설명:** time.sleep() 사용 3회. 비동기 처리 검토.

### 3. Potential Connection Leak
- **파일:** `backfill_level1_prices.py`
- **심각도:** HIGH
- **설명:** DB connect()와 close() 개수 불일치. 연결 누수 가능성.

### 4. Blocking Sleep
- **파일:** `level1_pykrx.py`
- **심각도:** LOW
- **설명:** time.sleep() 사용 2회. 비동기 처리 검토.

### 5. Blocking Sleep
- **파일:** `dart_batch_collector.py`
- **심각도:** LOW
- **설명:** time.sleep() 사용 1회. 비동기 처리 검토.

### 6. Blocking Sleep
- **파일:** `bithumb_trading_simulator.py`
- **심각도:** LOW
- **설명:** time.sleep() 사용 1회. 비동기 처리 검토.

### 7. Potential Connection Leak
- **파일:** `full_db_builder_2024_2026.py`
- **심각도:** HIGH
- **설명:** DB connect()와 close() 개수 불일치. 연결 누수 가능성.

### 8. Blocking Sleep
- **파일:** `full_db_builder_2024_2026.py`
- **심각도:** LOW
- **설명:** time.sleep() 사용 1회. 비동기 처리 검토.

### 9. Blocking Sleep
- **파일:** `naver_price_fetcher.py`
- **심각도:** LOW
- **설명:** time.sleep() 사용 2회. 비동기 처리 검토.

### 10. Blocking Sleep
- **파일:** `fdr_batch_processor.py`
- **심각도:** LOW
- **설명:** time.sleep() 사용 1회. 비동기 처리 검토.

---

## 📋 종합 평가

🔴 **다수의 개선사항 필요** - 우선순위별 정리 후 조치 권장

---

*자동 생성된 리포트* | *생성 시간: 2026-04-08 03:00:01 KST*
