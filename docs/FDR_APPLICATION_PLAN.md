# FinanceDataReader Level 1 적용 방안

## 📊 FDR 주요 기능

### 1. 종목 리스트
```python
import FinanceDataReader as fdr

# KOSPI 종목 리스트
kospi = fdr.StockListing('KOSPI')

# KOSDAQ 종목 리스트  
kosdaq = fdr.StockListing('KOSDAQ')

# KRX 전체
krx = fdr.StockListing('KRX')
```

### 2. 가격 데이터 (OHLCV)
```python
# 개별 종목 가격
df = fdr.DataReader('005930', '2025-01-01', '2026-03-10')
# 컬럼: Open, High, Low, Close, Volume, Change
```

### 3. 지수 데이터
```python
# 코스피 지수
kospi_index = fdr.DataReader('KS11', '2025-01-01')

# 코스닥 지수
kosdaq_index = fdr.DataReader('KQ11', '2025-01-01')

# VIX (변동성)
vix = fdr.DataReader('VIX', '2025-01-01')
```

### 4. 환율
```python
# 원/달러 환율
usd_krw = fdr.DataReader('USD/KRW', '2025-01-01')
```

---

## 🎯 에이전트별 적용 방안

### 1. Technical Analysis Agent (TECH)
**현재**: yfinance / PyKRX
**개선**: FDR로 OHLCV 데이터 수집

```python
# FDR 기반 기술적 분석
import FinanceDataReader as fdr

def get_price_data_fdr(symbol, days=60):
    end = datetime.now()
    start = end - timedelta(days=days)
    df = fdr.DataReader(symbol, start.strftime('%Y-%m-%d'), end.strftime('%Y-%m-%d'))
    return df

# 이동평균, RSI, MACD 계산
df = get_price_data_fdr('005930')
ma5 = df['Close'].rolling(5).mean()
ma20 = df['Close'].rolling(20).mean()
```

**장점**:
- 한국 시장 데이터 더 안정적
- 조정된 종가 (Adjusted Close) 제공
- 결측치 적음

---

### 2. Quant Analysis Agent (QUANT)
**현재**: PyKRX PER/PBR
**개선**: FDR + 추가 데이터

```python
# FDR는 직접 PER/PBR 제공하지 않음
# 대안: PyKRX 유지 또는 FDR + 외부 데이터 결합

# FDR로 시가총액 계산 가능
df = fdr.DataReader('005930', '2025-01-01')
latest_price = df['Close'].iloc[-1]
# 주식수 * 주가 = 시총 (주식수는 별도 필요)
```

**결론**: PER/PBR는 PyKRX 유지, 가격 데이터만 FDR로 전환

---

### 3. Qualitative Analysis Agent (QUAL)
**현재**: 정성적 분석 (비즈니스 모델 등)
**개선**: FDR로 산업군/섹터 데이터 활용

```python
# KRX 산업별 현황 (섹터 분류)
# FDR 직접 제공하지 않음
# 대안: KRX 웹사이트 크롤링 또는 기존 방식 유지
```

**결론**: FDR 직접 적용 어려움, 기존 방식 유지

---

### 4. News Sentiment Agent (NEWS)
**현재**: 네이버 뉴스 크롤링
**개선**: FDR는 뉴스 데이터 제공하지 않음

**결론**: 기존 방식 유지

---

## 💡 최종 적용 방안

### 적용 가능
| 에이전트 | 적용 내용 | 우선순위 |
|:--------:|----------|:-------:|
| **TECH** | OHLCV 데이터 → FDR | 🔴 높음 |
| **QUANT** | 가격 데이터 → FDR, 재무는 PyKRX 유지 | 🟡 중간 |
| **QUAL** | FDR 미적용 | 🟢 유지 |
| **NEWS** | FDR 미적용 | 🟢 유지 |

### 권장 구조
```
Level 1 Analysis
├── TECH: FinanceDataReader (OHLCV)
├── QUANT: PyKRX (PER/PBR) + FDR (가격)
├── QUAL: 기존 방식 유지
└── NEWS: 기존 방식 유지
```

---

## 🔧 구현 계획

### Phase 1: TECH Agent FDR 전환
- [ ] `technical_agent_fdr.py` 생성
- [ ] OHLCV 데이터 FDR로 수집
- [ ] 기술적 지표 계산 검증
- [ ] 성능 테스트

### Phase 2: 통합 테스트
- [ ] 4개 에이전트 병렬 실행
- [ ] 결과 비교 (yfinance vs FDR)
- [ ] 안정성 테스트

### Phase 3: 전체 적용
- [ ] 기존 코드 대체
- [ ] 문서 업데이트
- [ ] 모니터링 강화

---

## 📈 기대 효과

| 항목 | 기존 (yfinance) | 개선 (FDR) |
|------|----------------|-----------|
| **안정성** | 중간 | 높음 |
| **한국 시장** | 외부 API | Native |
| **속도** | 느림 | 빠름 |
| **결측치** | 많음 | 적음 |
| **조정 주가** | 불확실 | 확실 |
