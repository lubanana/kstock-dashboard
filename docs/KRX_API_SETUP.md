# KRX Open API 활성화 가이드

## 현재 상태
- ✅ API Key 발급 완료
- ❌ 서비스 이용 권한 미신청 (401 Unauthorized)

## 활성화 방법

### 1. KRX Open API 사이트 접속
https://openapi.krx.co.kr/contents/OPP/MAIN/main/index.cmd

### 2. 로그인
- API Key 발급 시 사용한 계정으로 로그인

### 3. 서비스 이용 신청
**[서비스이용] → [주식] → [필요한 서비스] → [신청]**

신청이 필요한 서비스 목록:

| 서비스 | 엔드포인트 | 설명 |
|:---|:---|:---|
| **KOSPI 시리즈 일별시세정보** | `/idx/kospi_dd_trd` | KOSPI 지수 |
| **KOSDAQ 시리즈 일별시세정보** | `/idx/kosdaq_dd_trd` | KOSDAQ 지수 |
| **유가증권 일별매매정보** | `/sto/stk_bydd_trd` | KOSPI 종목 시세 |
| **코스닥 일별매매정보** | `/sto/ksq_bydd_trd` | KOSDAQ 종목 시세 |

### 4. 승인 대기
- 영업일 기준 1~2일 소요
- 승인 완료 후 API 사용 가능

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

api = KRXAPI()

# KOSPI 지수 조회
kospi = api.get_kospi_index('20250404')

# KOSDAQ 지수 조회
kosdaq = api.get_kosdaq_index('20250404')

# 전종목 시세
stocks = api.get_kospi_stocks('20250404')

# 특정 종목 조회
samsung = api.get_stock_detail('005930', '20250404')
```

## 참고
- 분당 1,000회 호출 제한
- 일일 10,000회 기본 한도
- 상업적 이용 시 별도 문의 필요
