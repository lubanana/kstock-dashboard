# 📊 외부 데이터 소스 통합 전략 방안

**작성일:** 2026-03-15  
**대상 데이터:** Bigkinds, Our World in Data, Google Trends, Statista

---

## 1️⃣ Bigkinds (빅카인즈) - 한국 뉴스 빅데이터

### 데이터 특성
- 한국 54개 언론사 뉴스 아카이브 (1990년~현재)
- 키워드 검색, 트렌드 분석, 감성 분석 가능
- 산업/기업별 언급 빈도 및 감정 분석

### 매매전략 통합 방안

#### A. 뉴스 감성 분석 기반 필터 (Multi-Strategy에 적용)
```python
class NewsSentimentFilter:
    """
    Bigkinds API 연동하여 뉴스 감성 분석
    """
    def analyze_sentiment(self, symbol: str, days: int = 7) -> Dict:
        """
        종목별 뉴스 감성 분석
        Returns:
            {
                'sentiment_score': 0.75,  # -1 ~ +1 (긍정/부정)
                'mention_count': 45,       # 언급 횟수
                'trend': 'increasing',     # increasing/decreasing/stable
                'keywords': ['계약', '매출', '성장'],
                'risk_keywords': ['소송', '적자', '리스크']
            }
        """
        
    def apply_to_strategy(self, signals: List[StrategySignal]) -> List[StrategySignal]:
        """
        Multi-Strategy 신호에 뉴스 필터 적용
        """
        filtered = []
        for signal in signals:
            sentiment = self.analyze_sentiment(signal.symbol)
            
            # 긍정 뉴스 가산점
            if sentiment['sentiment_score'] > 0.3:
                signal.priority_score += 2
                
            # 부정 뉴스 제외
            if sentiment['sentiment_score'] < -0.5:
                continue
                
            # 급증하는 언급 = 모멘텀 신호
            if sentiment['trend'] == 'increasing' and sentiment['mention_count'] > 20:
                signal.priority_score += 1
                
            filtered.append(signal)
        return filtered
```

#### B. 이벤트 기반 트레이딩 (SEPA+VCP에 적용)
| 이벤트 유형 | 진입 신호 | 청산 신호 |
|-------------|-----------|-----------|
| **긍정적 실적 발표** | VCP 돌파 + 긍정 뉴스 시 강하게 진입 | 실적 쇼크 시 즉시 청산 |
| **산업 정책 발표** | 정책 수혜주 + 거래량 급증 시 진입 | 정책 불확실성 시 관망 |
| **M&A 뉴스** | 인수합병 루머 시 거래량 확인 후 진입 | 공식 부인 시 손절 |

#### C. 섹터 로테이션 탐지 (Buy Strength에 적용)
```python
def detect_sector_rotation() -> Dict[str, float]:
    """
    뉴스 언급 증가율 기반 섹터 로테이션 탐지
    """
    sectors = {
        '반도체': bigkinds.get_mention_growth('반도체', days=7),
        '2차전지': bigkinds.get_mention_growth('2차전지', days=7),
        '바이오': bigkinds.get_mention_growth('바이오', days=7),
        'AI': bigkinds.get_mention_growth('AI', days=7)
    }
    
    # 언급 증가율 상위 2개 섹터에 가중치 부여
    top_sectors = sorted(sectors.items(), key=lambda x: x[1], reverse=True)[:2]
    return {sector: 1.2 for sector, _ in top_sectors}  # 20% 가중치
```

---

## 2️⃣ Our World in Data - 글로벌 거시 데이터

### 데이터 특성
- 글로벌 경제, 환경, 사회 데이터
- 원자재 가격, 에너지 가격, 기후 데이터
- 장기 추세 및 사이클 분석

### 매매전략 통합 방안

#### A. 원자재 가격 기반 섹터 선호도 (Multi-Strategy에 적용)
```python
class MacroDataFilter:
    """
    Our World in Data 기반 거시 경제 필터
    """
    def __init__(self):
        self.oil_data = self.fetch_oil_prices()  # 유가 데이터
        self.copper_data = self.fetch_copper_prices()  # 구리 가격 (Dr. Copper)
        
    def get_sector_bias(self) -> Dict[str, float]:
        """
        원자재 가격 추세 기반 섹터 선호도
        """
        oil_trend = self.calculate_trend(self.oil_data, days=30)
        copper_trend = self.calculate_trend(self.copper_data, days=30)
        
        sector_bias = {}
        
        # 유가 상승 → 정유, 에너지 관련주 선호
        if oil_trend > 0.05:  # 5% 이상 상승
            sector_bias['정유'] = 1.3
            sector_bias['에너지'] = 1.3
            sector_bias['항공'] = 0.7  # 유가 상승 불리
            
        # 구리 상승 → 경기 민감주, 건설, 전기차 선호
        if copper_trend > 0.03:
            sector_bias['건설'] = 1.2
            sector_bias['전기차'] = 1.2
            sector_bias['반도체'] = 1.1
            
        return sector_bias
```

#### B. 글로벌 경기 사이클 판단 (전략 가중치 조정)
| 지표 | 상승 시 | 하락 시 | 적용 전략 |
|------|---------|---------|-----------|
| **구리 가격** | 경기 확장 → 순환주 선호 | 경기 위축 → 방어주 선호 | 섹터 가중치 조정 |
| **유가** | 인플레이션 우려 → 에너지주 | 경기 침체 우려 → 정유주 약세 | S3_모멘텀 필터링 |
| **CO2 배출량** | 산업 활동 활발 → 자동차, 화학 | 경기 둔화 → 수출주 주의 | 시장 환경 판단 |

#### C. 글로벌 수출 국가 경기 (KOSPI 관련)
```python
def get_korea_export_correlation() -> Dict[str, float]:
    """
    한국 수출 의존 국가들의 경기 지표
    """
    # 중국, 미국, 베트남 등 주요 수출국 GDP 성장률
    china_growth = ourworldindata.get_gdp_growth('China')
    us_growth = ourworldindata.get_gdp_growth('United States')
    
    # 수출 중심주(삼성전자, 현대차 등) 가중치 조정
    if china_growth > 5 and us_growth > 2:
        return {'수출주': 1.3, '내수주': 0.9}
    else:
        return {'수출주': 0.8, '내수주': 1.2}
```

---

## 3️⃣ Google Trends - 검색 트렌드 데이터

### 데이터 특성
- 검색어 관심도 추이 (0~100 상대 지수)
- 지역별, 시간별 검색 패턴
- 상관관계 및 예측 분석 가능

### 매매전략 통합 방안

#### A. 개인 투자자 관심도 기반 모멘텀 지표 (Buy Strength에 적용)
```python
class GoogleTrendsMomentum:
    """
    Google Trends 기반 개인 투자자 심리 지표
    """
    def get_search_trend(self, symbol: str) -> Dict:
        """
        종목명/테마 검색 트렌드 분석
        """
        # 종목명 검색 트렌드
        stock_trend = google_trends.get_interest(symbol, days=30)
        
        # 관련 테마 검색 트렌드
        sector_trend = google_trends.get_interest(get_sector_keyword(symbol), days=30)
        
        return {
            'stock_trend': stock_trend,
            'sector_trend': sector_trend,
            'trend_change': (stock_trend[-1] - stock_trend[-7]) / stock_trend[-7],
            'is_breakout': stock_trend[-1] > 80  # 관심도 급증
        }
        
    def calculate_momentum_score(self, symbol: str) -> int:
        """
        검색 트렌드 기반 모멘텀 점수 (Buy Strength에 통합)
        """
        trend = self.get_search_trend(symbol)
        score = 0
        
        # 검색 트렌드 상승
        if trend['trend_change'] > 0.5:  # 50% 이상 증가
            score += 15
        elif trend['trend_change'] > 0.2:
            score += 10
            
        # 관심도 급증 (FOMO 신호)
        if trend['is_breakout']:
            score += 10
            
        return min(20, score)  # 최대 20점
```

#### B. "혜자 종목" 탐지 알고리즘 (Multi-Strategy에 적용)
| 패턴 | 설명 | 진입 타이밍 |
|------|------|-------------|
| **검색 ↑ + 주가 ↓** | 관심 증가 but 주가 아직 반응 전 | 선제적 진입 기회 |
| **검색 ↑ + 주가 ↑** | 모멘텀 형성 중 | 추격 매수 가능 |
| **검색 ↓ + 주가 ↑** | 주가만 오르고 관심 없음 | 탑픽킹 경고 |
| **검색 ↓ + 주가 ↓** | 관심 소멸 | 회피 |

```python
def detect_opportunity(symbol: str) -> str:
    """
    검색 트렌드와 주가의 괴리 탐지
    """
    search_change = google_trends.get_change(symbol, days=7)
    price_change = get_price_change(symbol, days=7)
    
    if search_change > 0.3 and price_change < 0.05:
        return "OPPORTUNITY"  # 검색 ↑ 주가 ↓ = 기회
    elif search_change > 0.3 and price_change > 0.1:
        return "MOMENTUM"     # 검색 ↑ 주가 ↑ = 모멘텀
    elif search_change < -0.2 and price_change > 0.1:
        return "WARNING"      # 검색 ↓ 주가 ↑ = 경고
    else:
        return "NEUTRAL"
```

#### C. 테마/섹터 트렌드 선행 지표
```python
def get_sector_trend_ranking() -> List[Tuple[str, float]]:
    """
    섹터별 검색 트렌드 순위
    """
    sectors = ['반도체', '2차전지', '바이오', 'AI', '로봇', '항공']
    trends = []
    
    for sector in sectors:
        trend = google_trends.get_interest(sector, days=14)
        change = (trend[-1] - trend[0]) / trend[0]
        trends.append((sector, change))
        
    return sorted(trends, key=lambda x: x[1], reverse=True)
```

---

## 4️⃣ Statista - 산업/시장 통계 데이터

### 데이터 특성
- 산업별 시장 규모 및 성장률
- 기업별 시장 점유율
- 글로벌 트렌드 및 예측

### 매매전략 통합 방안

#### A. 산업 성장률 기반 장기 필터 (Buy Strength에 적용)
```python
class IndustryGrowthFilter:
    """
    Statista 기반 산업 성장률 필터
    """
    def __init__(self):
        self.industry_growth = {
            '반도체': statista.get_cagr('semiconductor_market_kr'),
            '2차전지': statista.get_cagr('battery_market_kr'),
            '바이오': statista.get_cagr('biotech_market_kr'),
            '게임': statista.get_cagr('gaming_market_kr')
        }
        
    def get_sector_score(self, sector: str) -> int:
        """
        산업 성장률 기반 점수 (Buy Strength에 통합)
        """
        growth = self.industry_growth.get(sector, 0)
        
        if growth > 20:  # 연평균 20% 이상 성장
            return 10
        elif growth > 15:
            return 7
        elif growth > 10:
            return 5
        else:
            return 0
```

#### B. 시장 점유율 변화 기반 종목 선별 (SEPA+VCP에 적용)
```python
def analyze_market_share_trend(symbol: str) -> Dict:
    """
    시장 점유율 추이 분석
    """
    share_history = statista.get_market_share_history(symbol)
    
    # 점유율 상승 추세
    if share_history[-1] > share_history[-4]:  # YoY 상승
        return {
            'trend': 'increasing',
            'score': 15,
            'message': f'시장 점유율 상승 중: {share_history[-4]:.1f}% → {share_history[-1]:.1f}%'
        }
    else:
        return {
            'trend': 'decreasing',
            'score': 0,
            'message': '시장 점유율 하락 중'
        }
```

#### C. 글로벌 트렌드 기반 섹터 선호도
| 트렌드 | 수혜 섹터 | 적용 전략 |
|--------|-----------|-----------|
| **AI 시장 성장** | 반도체, 클라우드, 소프트웨어 | Buy Strength 가중치 +5 |
| **전기차 보급률 상승** | 2차전지, 전기차 부품 | Multi-Strategy 가중치 +3 |
| **바이오시밀러 성장** | 바이오, 제약 | SEPA+VCP 필터링 완화 |
| **게임 시장 확대** | 게임, 메타버스 | 거래량 기준 하향 조정 |

---

## 5️⃣ 통합 전략 아키텍처

### 데이터 파이프라인
```
┌─────────────────────────────────────────────────────────────┐
│                    External Data Pipeline                   │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  ┌─────────────┐   ┌─────────────┐   ┌─────────────────┐   │
│  │  Bigkinds   │   │ Google      │   │ Statista        │   │
│  │  (뉴스)      │   │ Trends      │   │ (산업통계)       │   │
│  └──────┬──────┘   └──────┬──────┘   └────────┬────────┘   │
│         │                 │                    │            │
│         ▼                 ▼                    ▼            │
│  ┌──────────────────────────────────────────────────────┐  │
│  │              Data Aggregation Layer                   │  │
│  │  - Sentiment Score                                    │  │
│  │  - Search Momentum                                    │  │
│  │  - Industry Growth                                    │  │
│  └──────────────────────┬───────────────────────────────┘  │
│                         │                                   │
│                         ▼                                   │
│  ┌──────────────────────────────────────────────────────┐  │
│  │              Strategy Enhancement Layer              │  │
│  │                                                      │  │
│  │  ┌──────────────┐  ┌──────────────┐  ┌───────────┐  │  │
│  │  │ Buy Strength │  │ Multi-Strat  │  │ SEPA+VCP  │  │  │
│  │  │  + 뉴스점수   │  │ + 트렌드필터  │  │+ 산업성장  │  │  │
│  │  └──────────────┘  └──────────────┘  └───────────┘  │  │
│  └──────────────────────────────────────────────────────┘  │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

### 통합 가중치 시스템
```python
class EnhancedSignalGenerator:
    """
    외부 데이터 통합 신호 생성기
    """
    def generate_enhanced_signal(self, symbol: str) -> EnhancedSignal:
        # 기존 전략 신호
        base_signal = multi_strategy.scan_single(symbol)
        
        # 외부 데이터 점수
        bigkinds_score = bigkinds.get_sentiment_score(symbol) * 10  # -10 ~ +10
        trends_score = google_trends.get_momentum_score(symbol)      # 0 ~ 20
        industry_score = statista.get_sector_score(get_sector(symbol))  # 0 ~ 10
        
        # 통합 점수 계산
        total_score = (
            base_signal.priority_score +
            bigkinds_score +
            trends_score +
            industry_score
        )
        
        # 리스크 필터 (Bigkinds 부정 뉴스)
        if bigkinds_score < -5:
            return None  # 진입 금지
            
        return EnhancedSignal(
            symbol=symbol,
            base_score=base_signal.priority_score,
            enhanced_score=total_score,
            factors={
                'base': base_signal.priority_score,
                'news': bigkinds_score,
                'trends': trends_score,
                'industry': industry_score
            }
        )
```

---

## 6️⃣ 구현 우선순위

### Phase 1: Google Trends (즉시 적용 가능)
- **난이도:** 하
- **API:** pytrends 라이브러리 (묶
- **효과:** 개인 투자자 심리 반영
- **적용 전략:** Buy Strength (+모멘텀 점수)

### Phase 2: Bigkinds (API 신청 필요)
- **난이도:** 중
- **API:** 빅카인즈 Open API (신청 필요)
- **효과:** 뉴스 기반 필터링
- **적용 전략:** Multi-Strategy (+감성 필터)

### Phase 3: Our World in Data + Statista
- **난이도:** 중~상
- **API:** 직접 크롤링 또는 구독
- **효과:** 거시 경제 및 산업 트렌드
- **적용 전략:** 전략별 섹터 가중치

---

## 7️⃣ 기대 효과

| 데이터 소스 | 적용 전략 | 기대 효과 |
|-------------|-----------|-----------|
| **Bigkinds** | Multi-Strategy | 승률 38.7% → 45% (부정 뉴스 필터링) |
| **Google Trends** | Buy Strength | A등급 종목 선별율 향상 |
| **Our World in Data** | 섹터 로테이션 | 상승 섹터 선제 포착 |
| **Statista** | 장기 필터 | 성장 산업 중심 선별 |

---

*검토 완료: 2026-03-15*  
*적용 대상: Pivot Point, Buy Strength, SEPA+VCP, Multi-Strategy*
