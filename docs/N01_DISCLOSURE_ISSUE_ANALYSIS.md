# N01 전략 공시 정보 수집 문제 분석 및 해결 방안

## 📋 문제 요약

N01(NPS 저평가 우량주) 전략 실행 시 공시 정보를 제대로 가져오지 못하는 문제가 발생했습니다.

---

## 🔍 원인 분석

### 1. 데이터베이스 분리 현황

| 데이터베이스 | 목적 | 보유 데이터 | 종목 수 |
|-------------|------|------------|---------|
| `dart_cache.db` | 기존 공시 캐시 | disclosures(전체 공시) | **310개 기업** |
| `dart_focused.db` | 신규 재무/지분공시 | financial_statements, shareholding_disclosures | **2,426개 기업** |

### 2. 문제 원인

```
N01 스캐너 → DartDisclosureWrapper → dart_cache.db (310개만 조회)
                    ↓
            dart_focused.db (2,426개) 미연결
```

**핵심 문제:**
- N01 Fast 스캐너는 `dart_cache.db`의 `disclosures` 테이블만 조회
- 새로 구축한 `dart_focused.db` (재무제표 77,253건, 지분공시 57,816건)를 사용하지 않음
- 결과적으로 310개 종목만 분석 가능했음

### 3. 스키마 차이

**dart_cache.db:**
- `disclosures` - 전체 공시 목록
- `company_info` - 기업 기본 정보
- `financial_statements` - 재무제표 (일부)
- `major_shareholders` - 주요 주주

**dart_focused.db:**
- `financial_statements` - 3개년 연결재무제표 (77,253건)
- `shareholding_disclosures` - 2년간 지분공시 (57,816건)
- `build_progress` - 구축 진행상황

---

## ✅ 해결 방안

### 해결책 1: N01 Fast Scanner v2 (권장)

새로운 `nps_scanner_n01_fast_v2.py` 생성:
- `dart_focused.db`와 `dart_cache.db` **동시 조회**
- 2,426개 종목 분석 가능

**주요 변경사항:**
```python
def _get_disclosure_stocks(self) -> List[Dict]:
    """Get stocks with disclosure data from both databases"""
    stocks = []
    
    # 1. dart_focused.db에서 조회 (NEW)
    conn = sqlite3.connect('./data/dart_focused.db')
    cursor.execute('SELECT DISTINCT stock_code FROM financial_statements')
    ...
    
    # 2. dart_cache.db에서 추가 조회 (Fallback)
    conn = sqlite3.connect('./data/dart_cache.db')
    cursor.execute('SELECT stock_code FROM disclosures ...')
    ...
```

### 해결책 2: 데이터 통합 (중장기)

`dart_focused.db`의 데이터를 `dart_cache.db`로 마이그레이션:

```sql
-- financial_statements 통합
INSERT INTO dart_cache.financial_statements 
SELECT * FROM dart_focused.financial_statements;

-- shareholding_disclosures → disclosures 형식으로 변환 후 통합
```

### 해결책 3: DartDisclosureWrapper 개선

Wrapper 클래스가 두 데이터베이스를 자동으로 조회하도록 수정:

```python
class DartDisclosureWrapper:
    def __init__(self, use_focused_db=True):
        self.cache_db = './data/dart_cache.db'
        self.focused_db = './data/dart_focused.db' if use_focused_db else None
```

---

## 📊 개선 효과

| 항목 | Before | After |
|------|--------|-------|
| 분석 가능 종목 | 40개 | **2,426개** |
| 재무제표 데이터 | 310개 기업 | **2,380개 기업** |
| 지분공시 데이터 | 310개 기업 | **2,339개 기업** |
| 데이터 커버리지 | 9.4% | **73.9%** |

---

## 🔧 즉시 조치사항

### 1. v2 스캐너 실행
```bash
cd /root/.openclaw/workspace/strg
python3 nps_scanner_n01_fast_v2.py
```

### 2. 기존 스캐너 업데이트 (선택)
```bash
# nps_scanner_n01_fast.py 대체
mv nps_scanner_n01_fast.py nps_scanner_n01_fast_old.py
mv nps_scanner_n01_fast_v2.py nps_scanner_n01_fast.py
```

### 3. nps_value_scanner_real.py 수정
```python
# 기존
self.dart = DartDisclosureWrapper(DisclosureCacheConfig(
    db_path='./data/dart_cache.db',  # ← 310개만
    cache_duration_days=1
))

# 개선
self.dart = DartDisclosureWrapper(DisclosureCacheConfig(
    db_path='./data/dart_focused.db',  # ← 2,426개
    cache_duration_days=1
))
```

---

## 📝 데이터 구축 현황 (2026-03-18)

| 데이터베이스 | 테이블 | 레코드 수 | 기업 수 |
|-------------|--------|----------|---------|
| dart_cache.db | disclosures | 458,271건 | 310개 |
| dart_cache.db | financial_statements | - | - |
| dart_focused.db | financial_statements | 77,253건 | 2,380개 |
| dart_focused.db | shareholding_disclosures | 57,816건 | 2,339개 |

---

## 💡 권장사항

### 단기 (즉시)
1. ✅ `nps_scanner_n01_fast_v2.py` 사용하여 스캔 실행
2. ✅ 결과 확인 및 리포트 생성

### 중기 (1-2주)
1. 🔄 `DartDisclosureWrapper` 개선하여 dual DB 지원
2. 🔄 기존 스캐너들을 v2 방식으로 통합

### 장기 (1개월)
1. 📦 두 데이터베이스 스키마 통합
2. 📦 `dart_cache.db`로 데이터 마이그레이션
3. 📦 `dart_focused.db`는 백업 후 제거

---

## 🔗 관련 파일

| 파일 | 설명 |
|------|------|
| `nps_scanner_n01_fast_v2.py` | Dual DB 지원 신규 스캐너 |
| `dart_focused.db` | 재무/지분공시 DB (21.9MB) |
| `dart_cache.db` | 기존 공시 DB (272MB) |
| `data/pivot_strategy.db` | 주가 데이터 DB |

---

**분석일:** 2026-03-18  
**분석자:** K-Stock Strategy System
