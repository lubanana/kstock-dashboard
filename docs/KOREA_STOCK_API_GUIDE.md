# 한국 주식 묵제 API 비교 보고서

## 요약
현재 사용 중인 **FinanceDataReader(FDR)**가 가장 묵제적이고 안정적인 선택. 다른 API들은 보완용으로 활용 권장.

---

## 1. 🥇 FinanceDataReader (FDR) - 현재 사용중

| 항목 | 내용 |
|:---|:---|
| **비용** | 완전 묵제 (MIT 라이선스) |
| **데이터** | KRX (한국거래소) 일일 OHLCV |
| **지연시간** | T+1 (장 마감 다음날) |
| **커버리지** | KOSPI + KOSDAQ 전 종목 |
| **장점** | 안정적, 한국 특화, 활발한 커뮤니티 |
| **단점** | 실시간 데이터 없음, 분봉 없음 |

```python
# 현재 사용 예시
import FinanceDataReader as fdr

# 전 종목 목록
stocks = fdr.StockListing('KOSPI')  # 또는 'KOSDAQ', 'KRX'

# 가격 데이터
df = fdr.DataReader('005930', '2024-01-01', '2024-12-31')  # 삼성전자
```

**현재 시스템 적용 상태**: ✅ 기본 데이터 소스로 사용 중

---

## 2. 🥈 KRX Open API (한국거래소)

| 항목 | 내용 |
|:---|:---|
| **비용** | 묵제 |
| **인증** | API Key 필요 (KRX 홈페이지 가입) |
| **데이터** | 실시간 시세, 호가, 체결 |
| **제한** | 분당 1,000회 호출 |
| **장점** | 공식 데이터, 실시간 가능 |
| **단점** | 복잡한 인증, 상업적 이용 제한 |

```python
# 신청 방법
# 1. https://data.krx.co.kr/ 접속
# 2. 회원가입 → API 인증키 발급
# 3. 일일 호출량: 10,000회 (기본)

import requests

url = "http://data.krx.co.kr/comm/bldAttendant/getJsonData.cmd"
params = {
    'bld': 'dbms/MDC/STAT/standard/MDCSTAT01501',
    'locale': 'ko_KR',
    'mktId': 'STK',  # STK=KOSPI, KSQ=KOSDAQ
    'trdDd': '20240407'
}
response = requests.get(url, params=params)
data = response.json()
```

**적용 권장도**: ⭐⭐⭐ 실시간 데이터 필요시 고려

---

## 3. 🥉 DART Open API (금융감독원)

| 항목 | 내용 |
|:---|:---|
| **비용** | 묵제 |
| **인증** | API Key 필요 (DART 홈페이지) |
| **데이터** | 기업 공시, 재무제표, 사업보고서 |
| **커버리지** | 상장사 전체 |
| **장점** | 공식 공시 데이터, 신뢰도 높음 |
| **단점** | 가격 데이터 없음, 재무/공시 전문 |

```python
# 현재 사용 중 (OpenDartReader)
import OpenDartReader

dart = OpenDartReader(api_key)

# 공시 목록
dart.list('005930', start='2024-01-01', end='2024-12-31')

# 재무제표
dart.finstate('005930', 2023)
```

**현재 시스템 적용 상태**: ✅ 공시/재무 데이터로 사용 중

---

## 4. Yahoo Finance API

| 항목 | 내용 |
|:---|:---|
| **비용** | 묵제 (yfinance 라이브러리) |
| **데이터** | OHLCV, 분봉(1m~1mo) |
| **지연** | 15~20분 지연 |
| **커버리지** | 주요 종목만 (삼성전자, SK하이닉스 등) |
| **장점** | 분봉 데이터, 글로벌 주식 |
| **단점** | 한국 소형주 커버리지 낮음 |

```python
import yfinance as yf

# 티커 변환 필요 (005930.KS = 삼성전자)
ticker = yf.Ticker("005930.KS")
df = ticker.history(period="1y", interval="1d")

# 분봉 데이터
df_min = ticker.history(period="5d", interval="5m")
```

**적용 권장도**: ⭐⭐⭐ 분봉 필요시 보완용

---

## 5. Naver Finance (웹 스크래핑)

| 항목 | 내용 |
|:---|:---|
| **비용** | 묵제 (비공식) |
| **데이터** | 실시간 시세, 뉴스, 토론방 |
| **방법** | requests + BeautifulSoup |
| **장점** | 빠른 업데이트, 한국 특화 |
| **단점** | 공식 API 아님, 구조 변경 시 대응 필요 |

```python
import requests
from bs4 import BeautifulSoup

# 종목 시세
url = f"https://finance.naver.com/item/main.nhn?code=005930"
response = requests.get(url)
soup = BeautifulSoup(response.text, 'html.parser')

# 현재가
price = soup.select_one('.no_today .blind').text
```

**적용 권장도**: ⭐⭐ 실시간 필요시 임시방편 (공식 API 권장)

---

## 6. Alpha Vantage

| 항목 | 내용 |
|:---|:---|
| **비용** | 월 25회 묵제, 초과시 $29.99/월 |
| **데이터** | OHLCV, 기술적 지표 |
| **커버리지** | 글로벌 (한국 주요 종목) |
| **장점** | RESTful API, 다양한 지표 |
| **단점** | 한국 시장 커버리지 제한적 |

```python
import requests

API_KEY = 'YOUR_API_KEY'
url = f'https://www.alphavantage.co/query?function=TIME_SERIES_DAILY&symbol=005930.KS&apikey={API_KEY}'
response = requests.get(url)
data = response.json()
```

**적용 권장도**: ⭐⭐ 글로벌 포트폴리오용

---

## 7. Investing.com API

| 항목 | 내용 |
|:---|:---|
| **비용** | 묵제 (investpy 라이브러리) |
| **데이터** | OHLCV, 뉴스, 캘린더 |
| **커버리지** | 글로벌 (한국 포함) |
| **장점** | 다양한 시장, 경제 캘린더 |
| **단점** | 비공식 API, 불안정 |

```python
import investpy

# 한국 주식
df = investpy.get_stock_historical_data(
    stock='005930',
    country='south korea',
    from_date='01/01/2024',
    to_date='12/31/2024'
)
```

**적용 권장도**: ⭐⭐ 보조 데이터용

---

## 8. World Trading Data (WTD)

| 항목 | 내용 |
|:---|:---|
| **비용** | 일 250회 묵제 |
| **데이터** | 실시간, 역사 데이터 |
| **커버리지** | 전 세계 70+ 거래소 |
| **장점** | 간단한 REST API |
| **단점** | 한국 시장 커버리지 불명확 |

---

## 9. Twelve Data

| 항목 | 내용 |
|:---|:---|
| **비용** | 월 800회 묵제 |
| **데이터** | 실시간, 분봉, 기술적 지표 |
| **커버리지** | 70+ 거래소 |
| **장점** | WebSocket 지원 |
| **단점** | 묵제 플랜 제한적 |

```python
import requests

API_KEY = 'YOUR_API_KEY'
url = f'https://api.twelvedata.com/time_series?symbol=005930:KRX&interval=1day&apikey={API_KEY}'
```

---

## 📊 종합 비교표

| API | 실시간 | 분봉 | 가격 | 재무 | 공시 | 비용 | 권장도 |
|:---|:---:|:---:|:---:|:---:|:---:|:---|:---:|
| **FDR** | ❌ | ❌ | ✅ | ❌ | ❌ | 묵제 | ⭐⭐⭐⭐⭐ |
| **KRX API** | ✅ | ❌ | ✅ | ❌ | ❌ | 묵제 | ⭐⭐⭐⭐ |
| **DART** | ❌ | ❌ | ❌ | ✅ | ✅ | 묵제 | ⭐⭐⭐⭐⭐ |
| **Yahoo** | ⚠️ | ✅ | ✅ | ❌ | ❌ | 묵제 | ⭐⭐⭐ |
| **Naver** | ✅ | ❌ | ✅ | ❌ | ⚠️ | 묵제 | ⭐⭐ |
| **Alpha Vantage** | ❌ | ❌ | ✅ | ❌ | ❌ | 제한적 | ⭐⭐ |

---

## 💡 권장 아키텍처

```
┌─────────────────────────────────────────────────────────────┐
│  데이터 계층                                                 │
├─────────────────────────────────────────────────────────────┤
│  1차: FinanceDataReader (기본 OHLCV)                        │
│  2차: DART (공시/재무제표)                                   │
│  3차: KRX API (실시간 필요시)  또는  TradingView Webhook     │
│  4차: Yahoo Finance (분봉 데이터)                            │
└─────────────────────────────────────────────────────────────┘
```

---

## 🚀 다음 단계 제안

| 우선순위 | 작업 | 예상 효과 |
|:---|:---|:---|
| 1 | KRX API 키 발급 | 실시간 데이터 확보 |
| 2 | Yahoo Finance 분봉 연동 | 단기 전략 백테스트 |
| 3 | DART 데이터 고도화 | 재무 기반 필터링 |
| 4 | KRX 실시간 + V2 연동 | 실시간 알림 시스템 |

---

**결론**: 현재 FDR + DART 조합이 최적. 실시간 필요시 KRX API 추가 권장.

*작성일: 2026-04-07*
