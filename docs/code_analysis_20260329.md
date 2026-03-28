# 🔍 코드 분석 및 취약점 리포트
## 2026년 03월 29일 오전 2시 기준

---

## 📊 분석 개요

| 항목 | 개수 |
|:---|:---:|
| 🔴 보안 취약점 | 42개 |
| 💡 개선점 | 64개 |
| ⚡ 성능 이슈 | 42개 |
| 📝 코드 품질 | 0개 |

---

## 🔴 보안 취약점

### 1. SQL Injection Risk
- **파일:** `watchdog_hybrid.py`
- **심각도:** HIGH
- **설명:** 문자열 포맷팅을 사용한 SQL 쿼리 발견. 파라미터화된 쿼리 사용 권장.

### 2. Bare Except Clause
- **파일:** `dashboard.py`
- **심각도:** LOW
- **설명:** bare except: 사용. 구체적인 예외 지정 권장.
- **라인:** 57

### 3. Bare Except Clause
- **파일:** `dashboard.py`
- **심각도:** LOW
- **설명:** bare except: 사용. 구체적인 예외 지정 권장.
- **라인:** 63

### 4. Bare Except Clause
- **파일:** `dashboard.py`
- **심각도:** LOW
- **설명:** bare except: 사용. 구체적인 예외 지정 권장.
- **라인:** 69

### 5. Bare Except Clause
- **파일:** `dashboard.py`
- **심각도:** LOW
- **설명:** bare except: 사용. 구체적인 예외 지정 권장.
- **라인:** 75

### 6. Bare Except Clause
- **파일:** `dashboard.py`
- **심각도:** LOW
- **설명:** bare except: 사용. 구체적인 예외 지정 권장.
- **라인:** 81

### 7. Bare Except Clause
- **파일:** `investigation_report.py`
- **심각도:** LOW
- **설명:** bare except: 사용. 구체적인 예외 지정 권장.
- **라인:** 39

### 8. Bare Except Clause
- **파일:** `investigation_report.py`
- **심각도:** LOW
- **설명:** bare except: 사용. 구체적인 예외 지정 권장.
- **라인:** 48

### 9. Bare Except Clause
- **파일:** `investigation_report.py`
- **심각도:** LOW
- **설명:** bare except: 사용. 구체적인 예외 지정 권장.
- **라인:** 57

### 10. Bare Except Clause
- **파일:** `investigation_report.py`
- **심각도:** LOW
- **설명:** bare except: 사용. 구체적인 예외 지정 권장.
- **라인:** 66

## 💡 개선점

### 1. Excessive Print Statements
- **파일:** `daily_level1_fdr.py`
- **우선순위:** MEDIUM
- **설명:** print() 문이 33개 발견. 로깅 라이브러리 사용 권장.

### 2. Excessive Print Statements
- **파일:** `dart_batch_collector.py`
- **우선순위:** MEDIUM
- **설명:** print() 문이 28개 발견. 로깅 라이브러리 사용 권장.

### 3. Excessive Print Statements
- **파일:** `full_db_builder_2024_2026.py`
- **우선순위:** MEDIUM
- **설명:** print() 문이 36개 발견. 로깅 라이브러리 사용 권장.

### 4. Excessive Print Statements
- **파일:** `double_signal_scanner.py`
- **우선순위:** MEDIUM
- **설명:** print() 문이 23개 발견. 로깅 라이브러리 사용 권장.

### 5. Excessive Print Statements
- **파일:** `value_stock_scanner.py`
- **우선순위:** MEDIUM
- **설명:** print() 문이 24개 발견. 로깅 라이브러리 사용 권장.

### 6. Large File
- **파일:** `value_stock_scanner.py`
- **우선순위:** LOW
- **설명:** 파일이 569줄로 큼. 모듈 분리 검토.

### 7. Excessive Print Statements
- **파일:** `fundamental_collector.py`
- **우선순위:** MEDIUM
- **설명:** print() 문이 29개 발견. 로깅 라이브러리 사용 권장.

### 8. Excessive Print Statements
- **파일:** `oneil_scanner.py`
- **우선순위:** MEDIUM
- **설명:** print() 문이 28개 발견. 로깅 라이브러리 사용 권장.

### 9. Excessive Print Statements
- **파일:** `kosdaq_scanner.py`
- **우선순위:** MEDIUM
- **설명:** print() 문이 24개 발견. 로깅 라이브러리 사용 권장.

### 10. Excessive Print Statements
- **파일:** `daily_level1_fullmarket.py`
- **우선순위:** MEDIUM
- **설명:** print() 문이 38개 발견. 로깅 라이브러리 사용 권장.

## ⚡ 성능 이슈

### 1. Blocking Sleep
- **파일:** `daily_level1_fdr.py`
- **심각도:** LOW
- **설명:** time.sleep() 사용 1회. 비동기 처리 검토.

### 2. Blocking Sleep
- **파일:** `watchdog_hybrid.py`
- **심각도:** LOW
- **설명:** time.sleep() 사용 3회. 비동기 처리 검토.

### 3. Blocking Sleep
- **파일:** `level1_pykrx.py`
- **심각도:** LOW
- **설명:** time.sleep() 사용 2회. 비동기 처리 검토.

### 4. Blocking Sleep
- **파일:** `dart_batch_collector.py`
- **심각도:** LOW
- **설명:** time.sleep() 사용 1회. 비동기 처리 검토.

### 5. Potential Connection Leak
- **파일:** `full_db_builder_2024_2026.py`
- **심각도:** HIGH
- **설명:** DB connect()와 close() 개수 불일치. 연결 누수 가능성.

### 6. Blocking Sleep
- **파일:** `full_db_builder_2024_2026.py`
- **심각도:** LOW
- **설명:** time.sleep() 사용 1회. 비동기 처리 검토.

### 7. Blocking Sleep
- **파일:** `naver_price_fetcher.py`
- **심각도:** LOW
- **설명:** time.sleep() 사용 2회. 비동기 처리 검토.

### 8. Blocking Sleep
- **파일:** `fdr_batch_processor.py`
- **심각도:** LOW
- **설명:** time.sleep() 사용 1회. 비동기 처리 검토.

### 9. Blocking Sleep
- **파일:** `daily_update_batch.py`
- **심각도:** LOW
- **설명:** time.sleep() 사용 1회. 비동기 처리 검토.

### 10. Blocking Sleep
- **파일:** `level1_hybrid.py`
- **심각도:** LOW
- **설명:** time.sleep() 사용 2회. 비동기 처리 검토.

---

## 📋 종합 평가

🔴 **다수의 개선사항 필요** - 우선순위별 정리 후 조치 권장

---

*자동 생성된 리포트* | *생성 시간: 2026-03-29 03:00:01 KST*
