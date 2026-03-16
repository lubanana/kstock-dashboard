# 📊 Market Intelligence Wrapper

**4개 외부 데이터 소스 통합 시장조사 시스템**

## 개요

이터닉스, 미국AI전력인프라 등 스캔된 종목에 대해 외부 데이터 소스를 활용한 심층 시장조사를 자동화하는 래퍼 프로그램입니다.

## 지원 데이터 소스

| 데이터 소스 | URL | 용도 | 상태 |
|------------|-----|------|------|
| **Bigkinds** | bigkinds.or.kr | 한국 뉴스 빅데이터/감성 분석 | ✅ 사용 가능 |
| **Our World in Data** | ourworldindata.org | 글로벌 거시 경제 지표 | ✅ 공개 데이터 |
| **Google Trends** | trends.google.co.kr | 검색 트렌드/관심도 분석 | ✅ 사용 가능 |
| **Statista** | statista.com | 산업 통계/시장 규모 | ⚠️ 일부 묶

## 설치

```bash
# 기본 의존성
pip install pandas requests beautifulsoup4

# Scrapling 설치 (선택)
pip install scrapling
scrapling install  # 브라우저 설치

# Google Trends (선택)
pip install pytrends
```

## 사용법

### 1. Python API

```python
from market_intelligence import MarketIntelligence

# 초기화
mi = MarketIntelligence()

# 종목 분석
analysis = mi.analyze_stock(
    symbol='475150',
    name='이터닉스',
    sector='반도체'
)

# 리포트 생성
report = mi.generate_report(analysis)
print(report)
```

### 2. CLI 도구

```bash
# 단일 종목 분석
python market_intelligence_cli.py analyze \
  --symbol 475150 \
  --name "이터닉스" \
  --sector "반도체" \
  --html

# 배치 분석
python market_intelligence_cli.py batch \
  --symbols "475150,486450,261240" \
  --names "이터닉스,미국AI전력인프라,미국달러선물" \
  --sectors "반도체,AI,ETF"

# 종목 비교
python market_intelligence_cli.py compare \
  --symbols "475150,005930" \
  --names "이터닉스,삼성전자"
```

### 3. Scrapling 기반 수집

```python
from scrapling_collector import ScraplingDataCollector

collector = ScraplingDataCollector()

# 모든 소스에서 수집
data = collector.collect_all(
    keyword='이터닉스',
    sector='semiconductor'
)
```

## 분석 지표

### 종합 점수 계산 (100점 만점)

| 구분 | 반영 비율 | 내용 |
|------|----------|------|
| **뉴스 감성** | 30% | Bigkinds 뉴스 긍/부정 분석 |
| **산업 성장** | 25% | Statista 산업별 CAGR |
| **검색 트렌드** | 25% | Google Trends 관심도 |
| **거시 환경** | 20% | Our World in Data 지표 |

### 추천 기준

| 종합점수 | 추천 | 설명 |
|---------|------|------|
| 75+ | **STRONG_BUY** | 강력 매수 |
| 60-74 | **BUY** | 매수 |
| 40-59 | **HOLD** | 보유 |
| 25-39 | **REDUCE** | 축소 |
| 0-24 | **SELL** | 매도 |

## 출력 예시

```
======================================================================
📊 시장조사 종합 분석 리포트
======================================================================

종목: 이터닉스 (475150)
섹터: 반도체
분석일: 2026-03-16

======================================================================
🎯 종합 판단
======================================================================

종합점수: 100.0/100
추천: STRONG_BUY

======================================================================
📰 뉴스 감성 분석
======================================================================

감성점수: +0.65 (긍정)
언급횟수: 45회
추세: increasing

긍정 키워드: AI 반도체, 장비 수주, 신규 계약
부정 키워드: 경쟁 심화

======================================================================
🏭 산업 분석
======================================================================

연평균 성장률: 18.5%
시장규모: 612.0B USD

주요 트렌드:
  • AI 칩 수요 증가
  • HBM 고성장
  • 파운드리 투자 확대

리스크 요인:
  • 중국 경쟁 심화
  • 사이클 조정

======================================================================
📈 검색 트렌드
======================================================================

이터닉스: 45/100 (rising)
반도체: 78/100 (rising)
AI: 85/100 (rising)
```

## 파일 구조

```
strg/
├── market_intelligence.py         # 메인 래퍼 클래스
├── market_intelligence_cli.py     # CLI 도구
├── scrapling_collector.py         # Scrapling 기반 수집
└── docs/
    └── market_intelligence.html   # 웹 인터페이스 (예정)
```

## 실제 데이터 연동

현재는 시뮬레이션 데이터를 사용하고 있습니다. 실제 데이터 연동을 위해서는:

### Bigkinds
```python
from scrapling import Fetcher

fetcher = Fetcher()
response = fetcher.get(f'https://www.bigkinds.or.kr/search?query={keyword}')
# HTML 파싱하여 뉴스 추출
```

### Our World in Data
```python
# 공개 API 사용
url = 'https://ourworldindata.org/grapher/oil-prices'
response = requests.get(url)
# JSON 데이터 추출
```

### Google Trends
```python
from pytrends.request import TrendReq

pytrends = TrendReq(hl='ko', tz=540)
pytrends.build_payload(['AI', '반도체'], timeframe='today 3-m', geo='KR')
data = pytrends.interest_over_time()
```

### Statista
```python
# 로그인 필요 시 세션 유지
session = requests.Session()
# 로그인 후 데이터 수집
```

## 라이선스

MIT License - 자유롭게 사용 및 수정 가능

## 참고사항

- 웹 스크래핑 시 `robots.txt` 및 이용약관 준수
- 합리적인 요청 간격 유지 (Rate Limiting)
- 상업적 사용 시 데이터 소스별 라이선스 확인
