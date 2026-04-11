# 종목 데이터베이스 관리 시스템

## 개요

한국주식 KRX 종목정보와 DART 공시 데이터를 통합 관리하는 시스템

## 데이터베이스 구조

### 1. level1_prices.db
| 테이블 | 설명 |
|:---|:---|
| `price_data` | OHLCV 가격 데이터 |
| `stock_info` | 종목 기본정보 (코드, 명칭, 시장, 섹터) |

### 2. pivot_strategy.db
| 테이블 | 설명 |
|:---|:---|
| `stock_info` | 종목 기본정보 |
| `stock_code_mapping` | **코드 매핑 (KRX ↔ DART)** |
| `dart_disclosures` | DART 공시 데이터 |
| `mapping_log` | 매핑 변경 로그 |

### 3. Code Mapping Table
```sql
stock_code_mapping:
- krx_code: KRX 종목코드 (Primary Key)
- dart_code: DART 기업코드 (일반적으로 동일)
- naver_code: Naver Finance 코드
- name: 종목명
- code_type: 종목타입 (normal/etf/preferred/spac)
```

## 코드 매핑 규칙

| 종목타입 | 판별 기준 |
|:---|:---|
| `normal` | 일반 주식 |
| `etf` | ETF/ETN (TIGER, KODEX, KBSTAR 등) |
| `preferred` | 우선주 (명칭에 '우' 포함) |
| `spac` | 스팩 (명칭에 '스팩' 포함) |

**참고**: KRX 코드와 DART 코드는 대부분 동일합니다.

## 사용법

### 1. 전체 동기화
```bash
cd strg
python3 stock_database_manager.py
# 또는
python3 stock_db_cli.py sync
```

### 2. 종목 정보 조회
```bash
python3 stock_db_cli.py info 005930
```

### 3. 코드 변환
```bash
# KRX → DART
python3 stock_db_cli.py convert 005930 krx dart

# KRX → Naver
python3 stock_db_cli.py convert 005930 krx naver
```

### 4. 통계 확인
```bash
python3 stock_db_cli.py stats
```

### 5. 검증
```bash
python3 stock_db_cli.py verify
```

## 주기적 동기화

### 크론 설정 (권장)
```bash
# 매주 일요일 03:00에 실행
0 3 * * 0 /root/.openclaw/workspace/strg/cron/stock_sync_weekly.sh
```

### 수동 등록
```bash
openclaw cron create \
  --name stock-sync-weekly \
  --schedule "cron 0 3 * * 0" \
  --command "bash /root/.openclaw/workspace/strg/cron/stock_sync_weekly.sh" \
  --target isolated
```

## 현재 상태

| 항목 | 값 |
|:---|---:|
| 총 종목 수 | 2,773 |
| 코드 매핑 | 2,776 |
| DART 연결 | 26,454 공시 |
| 타입 분포 | normal: 2,533 / preferred: 166 / spac: 77 |

## API 활용 예시

### Python
```python
from stock_database_manager import StockDatabaseManager

manager = StockDatabaseManager()

# 종목 정보 조회
info = manager.get_stock_info(code='005930')
print(info['name'])  # 삼성전자

# 코드 변환
dart_code = manager.convert_code('005930', 'krx', 'dart')  # 005930

# 전체 동기화
manager.sync_databases()
```

### SQL 직접 조회
```sql
-- 종목 코드 매핑 조회
SELECT * FROM stock_code_mapping WHERE krx_code = '005930';

-- DART 공시와 조인
SELECT dd.*, scm.name 
FROM dart_disclosures dd
JOIN stock_code_mapping scm ON dd.stock_code = scm.krx_code
WHERE scm.krx_code = '005930';
```

## 파일 목록

| 파일 | 설명 |
|:---|:---|
| `stock_database_manager.py` | 핵심 관리 클래스 |
| `stock_db_cli.py` | CLI 도구 |
| `cron/stock_sync_weekly.sh` | 주간 동기화 스크립트 |
| `docs/STOCK_DATABASE.md` | 이 문서 |

## 로그 위치

```
/root/.openclaw/workspace/logs/stock_sync_YYYYMMDD.log
```

## 주의사항

1. **DART 코드**: 대부분 KRX 코드와 동일하지만, 일부 기업은 다를 수 있음
2. **ETF/ETN**: 코드 타입이 `etf`로 분류됨
3. **상장폐지 종목**: KRX 목록에서 제외되면 자동 삭제되지 않음 (수정 필요)
