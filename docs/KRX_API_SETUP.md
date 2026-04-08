# KRX Open API 활성화 가이드

## 현재 상태 (2026-04-08 10:40)

| 서비스 | 엔드포인트 | 상태 | 종목/데이터 수 |
|:---|:---|:---:|:---:|
| **KOSPI 시리즈 일별시세정보** | `/idx/kospi_dd_trd` | ✅ | 3개 지수 |
| **KOSDAQ 시리즈 일별시세정보** | `/idx/kosdaq_dd_trd` | ✅ | 3개 지수 |
| **유가증권 일별매매정보** | `/sto/stk_bydd_trd` | ✅ | 962개 KOSPI |
| **코스닥 일별매매정보** | `/sto/ksq_bydd_trd` | ❌ | 401 Unauthorized |

## ⚠️ 확인 필요

**"코스닥 일별매매정보"** 서비스 권한이 실제로 승인되었는지 확인:

1. https://openapi.krx.co.kr/ 접속
2. 로그인 → **[마이페이지] → [나의 API 서비스]**
3. 아래 서비스가 **"승인완료"** 상태인지 확인:
   - `코스닥 일별매매정보` (endpoint: `/sto/ksq_bydd_trd`)

## 현재 보유 API Key
```
KRX_API_KEY=6D827493BEA34A938C8E2F7343CC414254ED3D21
```

위치: `/root/.openclaw/workspace/strg/.env.krx`

## 테스트 코드
```bash
cd /root/.openclaw/workspace/strg
python3 v2/core/krx_api.py
```

## Python 사용 예시
```python
from v2.core.krx_api import KRXAPI
from v2.core.krx_datasource import KRXDataSource

api = KRXAPI()

# 지수 조회 ✅
kospi_index = api.get_kospi_index('20250407')
kosdaq_index = api.get_kosdaq_index('20250407')

# KOSPI 종목 시세 ✅
kospi_stocks = api.get_kospi_stocks('20250407')  # 962개

# KOSDAQ 종목 시세 ❌ (401)
kosdaq_stocks = api.get_kosdaq_stocks('20250407')  # 권한 필요

# 데이터 소스
source = KRXDataSource()
df = source.fetch_daily_prices('20250407')  # KOSPI만 수집
```

## 테스트 결과 샘플

### 지수 데이터 ✅
| 지수 | 값 | 등락률 |
|:---|---:|---:|
| 코스피 | 2,465.42 | -0.86% |
| 코스피 200 | 328.67 | -1.28% |
| 코스닥 | 687.39 | +0.57% |
| 코스닥 150 | 1,137.70 | +0.76% |

### KOSPI 종목 시세 ✅
| 종목 | 코드 | 종가 | 등락률 | 시가총액 |
|:---|:---|---:|---:|---:|
| AJ네트웍스 | 095570 | 3,695 | 0.00% | 1,652억 |
| 삼성전자 | 005930 | 56,100 | -2.60% | 332조 |

### KOSDAQ 종목 시세 ❌
```
401 Unauthorized
```

## 참고
- 분당 1,000회 호출 제한
- 일일 10,000회 기본 한도
- 승인 후 5~10분 지연 가능
