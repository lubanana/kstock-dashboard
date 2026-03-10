# Korean Stock Fundamental Data - Current Status

## ⚠️ PyKRX 현재 상태

**문제**: KRX 웹사이트 변경으로 인해 PyKRX 재무정보 API 작동 중단
- `get_market_fundamental()` 함수 오류 발생
- PER, PBR, EPS 등 조회 불가

---

## 🔧 대안 방안

### 1. 네이버 금융 웹 스크래핑 (권장)
```python
# 네이버 금융에서 재무정보 수집
import requests
from bs4 import BeautifulSoup

def get_naver_fundamental(code):
    url = f"https://finance.naver.com/item/main.nhn?code={code}"
    # PER, PBR, EPS 파싱
```

**장점**: 
- 실시간 데이터
- 안정적인 접근
- 추가 정보(투자지표, 컨센서스) 제공

**단점**:
- 웹 구조 변경 시 대응 필요
- Rate limiting 필요

---

### 2. 기존 데이터 활용
**현재 보유 데이터**:
- 3,286개 종목 가격 데이터 (O/H/L/C/V)
- 기술적 지표 (RSI, MACD, MA)
- 추세 정보

**활용 방안**:
- 가격 기반 분석으로 충분히 의사결정 가능
- 재무정보 없이도 기술적 분석으로 매매 가능
- PER/PBR은 참고용으로만 사용

---

### 3. dart-fss 라이브러리 (공시정보)
```python
# pip install dart-fss
import dart_fss as dart

# 정기공시 재무제표 조회
```

**장점**:
- 공식 공시 데이터
- 신뢰도 높음

**단점**:
- 실시간 아님 (분기/연간)
- API 승인 필요

---

## 💡 권장 방안

### 단기: 네이버 금융 스크래핑
- PER, PBR, EPS 수집
- 3,286개 종목 배치 처리
- SQLite에 저장

### 중기: dart-fss 통합
- 분기별 재무제표 수집
- ROE, 부채비율 등 추가 지표

### 현재: 가격 데이터 중심 분석
- 기존 3,286개 가격 데이터로 충분
- 기술적 분석 + 시장 심리로 의사결정
- 재무정보는 부가 참고용

---

## 📊 현재 가능한 분석

| 분석 유형 | 데이터 | 가능 여부 |
|:---------:|--------|:---------:|
| 기술적 분석 | OHLCV | ✅ 가능 |
| 추세 분석 | MA, RSI, MACD | ✅ 가능 |
| 시장 심리 | 거래량, 변동성 | ✅ 가능 |
| 밸류에이션 | PER, PBR | ❌ 제한 |
| 재무건전성 | 부채비율, ROE | ❌ 제한 |

---

## 🎯 결론

**FDR**: 가격 데이터만 제공 → 기술적 분석에 최적
**재무정보**: PyKRX 오류로 인해 네이버 스크래핑 또는 dart-fss 사용 권장

**단기적으로는 기존 가격 데이터로 충분히 분석 가능합니다!**
