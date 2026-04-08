# KRX Open API 활성화 가이드

## 현재 상태 (2026-04-08)
- ✅ API Key 발급 완료
- ✅ **유가증권 일별매매정보** - 사용 가능 (962개 KOSPI 종목)
- ✅ **유가증권 종목기본정보** - 사용 가능
- ❌ **코스닥 일별매매정보** - 권한 필요 (401)
- ❌ **KOSPI/KOSDAQ 지수** - 권한 필요 (401)

## 활성화 방법

### 1. KRX Open API 사이트 접속
https://openapi.krx.co.kr/contents/OPP/MAIN/main/index.cmd

### 2. 로그인
- API Key 발급 시 사용한 계정으로 로그인

### 3. 서비스 이용 신청
**[서비스이용] → [카테고리] → [개별 서비스] → [신청]**

신청이 필요한 서비스 목록:

| 서비스 | 엔드포인트 | 설명 | 상태 |
|:---|:---|:---|:---:|
| **KOSPI 시리즈 일별시세정보** | `/idx/kospi_dd_trd` | KOSPI 지수 | ❌ 미신청 |
| **KOSDAQ 시리즈 일별시세정보** | `/idx/kosdaq_dd_trd` | KOSDAQ 지수 | ❌ 미신청 |
| **유가증권 일별매매정보** | `/sto/stk_bydd_trd` | KOSPI 종목 시세 | ✅ 사용중 |
| **코스닥 일별매매정보** | `/sto/ksq_bydd_trd` | KOSDAQ 종목 시세 | ❌ 미신청 |

## 현재 보유 API Key
```
KRX_API_KEY=6D827493BEA34A938C8E2F7343CC414254ED3D21
```

위치: `/root/.openclaw/workspace/strg/.env.krx`

## 테스트 코드
```bash
cd /root/.openclaw/workspace/strg
python3 v2/core/krx_api.py
python3 v2/core/krx_datasource.py
```

## Python 사용 예시
```python
from v2.core.krx_api import KRXAPI
from v2.core.krx_datasource import KRXDataSource

# API 클라이언트
api = KRXAPI()
kospi_stocks = api.get_kospi_stocks('20250407')

# 데이터 소스 (DataFrame)
source = KRXDataSource()
df = source.fetch_daily_prices('20250407')

# 특정 종목 조회
samsung = api.get_stock_detail('005930', '20250407')
```

## 데이터 필드

### 종목 시세 (OutBlock_1)
| 필드 | 설명 | 예시 |
|:---|:---|:---|
| ISU_CD | 종목코드 (풀코드) | KR7005930003 |
| ISU_NM | 종목명 | 삼성전자 |
| MKT_NM | 시장구분 | KOSPI |
| TDD_CLSPRC | 종가 | 56100 |
| TDD_OPNPRC | 시가 | 57500 |
| TDD_HGPRC | 고가 | 57500 |
| TDD_LWPRC | 저가 | 56000 |
| ACC_TRDVOL | 거래량 | 12345678 |
| ACC_TRDVAL | 거래대금 | 123456789000 |
| MKTCAP | 시가총액 | 332091687424200 |
| FLUC_RT | 등락률 | -2.60 |

## 참고
- 분당 1,000회 호출 제한
- 일일 10,000회 기본 한도
- KOSPI 데이터만 수집 가능 (KOSDAQ은 추가 신청 필요)
