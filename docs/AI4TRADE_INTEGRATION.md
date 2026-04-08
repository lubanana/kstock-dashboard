# AI4Trade 분석 및 매매 활용 방안

## 📊 플랫폼 분석: AI-Trader (ai4trade.ai)

### 핵심 기능

#### 1. **금융 이벤트 대시보드 (Financial Events Board)**
- **개별 종목 AI 분석**: AAPL, NVDA, MSFT, TSLA, GOOGL, AMD, QQQ 등
- **매매 신호**: buy / sell / defensive (방어적)
- **기술적 지표**: MA5/10/20/60, 지지/저항선, 추세 분석
- **리스크 평가**: 상승/하락 요인, 핵심 가격대

#### 2. **매크로 신호 (Macro Signals)**
| 지표 | 현재 상태 | 값 | 설명 |
|:---|:---:|:---|:---|
| BTC 추세 | bullish | +5.56% | 최근 1주 강한 모멘텀 |
| QQQ 추세 | defensive | -3.03% | 성장주 모멘텀 약화 |
| QQQ vs XLP | neutral | 1.92 | 성장/방어 균형 |
| 회피 심리 | neutral | 1.06% | 극단적 공포 아님 |
| 매크로 뉴스 톤 | bullish | 14 | 전체적으로 긍정적 |

#### 3. **ETF 자금 흐름 (ETF Flow Direction)**
- 비트코인 ETF: HODL, BITB, IBIT, ARKB, FBTC, BRRR, BTCW, EZBC
- 지표: 가격 변동%, 거래량 비율, 자금 흐름 점수
- 현재 상태: mixed (혼조)

#### 4. **실시간 뉴스 분석**
- 출처: Stock Traders Daily, Insider Monkey 등
- 감성 태그: Somewhat-Bullish, Bullish, Bearish 등
- 관련 종목 자동 매핑

---

## 🎯 한국 주식 매매 활용 방안

### 1. **매크로 신호 기반 섹터 로테이션**

```python
# 매크로 신호 → 한국 섹터 매핑
macro_signals = {
    "BTC_bullish": {
        "korean_sectors": ["블록체인", "핀테크", "IT"],
        "example_stocks": ["위메이드", "펄어비스", "한컴위드"],
        "action": "overweight"
    },
    "QQQ_defensive": {
        "korean_sectors": ["반도체", "바이오", "2차전지"],
        "example_stocks": ["삼성전자", "SK하이닉스", "삼성바이오"],
        "action": "underweight_or_selective"
    },
    "macro_bullish": {
        "korean_sectors": ["은행", "보험", "철강"],
        "example_stocks": ["삼성생명", "현대제철", "POSCO"],
        "action": "overweight"
    }
}
```

### 2. **AI 신호 기반 한국 종목 선별**

#### 미국 종목 → 한국 대체 종목 매핑

| 미국 종목 | AI 신호 | 한국 대체 종목 | 연관성 |
|:---|:---:|:---|:---|
| NVDA (183.26달러) | - | 삼성전자, SK하이닉스 | HBM 공급사 |
| AMD (229.35달러) | - | 원익IPS, 주성엔지니어링 | 장비사 |
| TSLA | - | 현대차, 기아 | 경쟁/협력 관계 |
| AAPL (sell 신호) | defensive | 비에이치, LG이노텍 | 부품사 주의 |

### 3. **2604 스캐너에 통합할 기능**

```python
# v2/strategies/ai4trade_integration.py

class AI4TradeIntegration:
    """
    AI4Trade 매크로/뉴스 데이터 연동
    """
    
    def __init__(self):
        self.macro_weight = 0.15  # 매크로 신호 가중치 15%
        self.news_weight = 0.10   # 뉴스 감성 가중치 10%
    
    def get_macro_score(self):
        """
        매크로 신호를 2604 스캐너 점수로 변환
        """
        scores = {
            'BTC_bullish': {'blockchain': +5, 'fintech': +3},
            'QQQ_defensive': {'semiconductor': -3, 'growth': -2},
            'macro_bullish': {'finance': +4, 'steel': +3},
            'safe_haven_neutral': {'gold': 0, 'bond': 0}
        }
        return scores
    
    def sector_rotation_signal(self):
        """
        섹터 로테이션 신호 생성
        """
        if self.btc_trend == 'bullish':
            return {
                'overweight': ['블록체인', '핀테크'],
                'underweight': ['방어주', '유틸리티']
            }
        elif self.qqq_trend == 'defensive':
            return {
                'overweight': ['가치주', '배당주'],
                'underweight': ['성장주', '테크']
            }
```

### 4. **실시간 알림 시스템**

```python
# ai4trade_alerts.py

class AI4TradeMonitor:
    """
    AI4Trade 신호 모니터링 및 알림
    """
    
    ALERT_RULES = {
        'BTC_breakout': {
            'condition': 'BTC > 75000',
            'korean_stocks': ['위메이드', '펄어비스'],
            'message': 'BTC 돌파 - 국내 블록체인 주목'
        },
        'NVDA_signal_change': {
            'condition': 'signal changes',
            'korean_stocks': ['삼성전자', 'SK하이닉스'],
            'message': 'NVDA 신호 변화 - 국내 반도체 체크'
        },
        'macro_turn_bullish': {
            'condition': 'macro_score > 10',
            'korean_sectors': ['금융', '철강'],
            'message': '매크로 전환 - 사이클 주 편입'
        }
    }
```

---

## 📈 구현 우선순위

### Phase 1: 데이터 연동 (1주)
- [ ] AI4Trade API 연동 (있는 경우)
- [ ] 웹 스크래핑 모듈 개발
- [ ] 매크로 신호 DB 저장

### Phase 2: 신호 변환 (1주)
- [ ] 미국 종목 → 한국 종목 매핑 테이블
- [ ] 매크로 신호 → 섹터 가중치 로직
- [ ] 2604 스캐너 통합

### Phase 3: 알림 시스템 (3일)
- [ ] 텔레그램 알림 연동
- [ ] 주요 신호 변경 시 실시간 알림
- [ ] 일일 리포트 자동 생성

---

## 🔗 참고 자료

- **플랫폼**: https://ai4trade.ai
- **주요 기능**: 금융 이벤트 대시보드, 매크로 신호, ETF 흐름, 뉴스 분석
- **언어**: 중국어 (简/繁), 영어 지원
- **가격**: 일부 기능 묶음 로그인 필요

---

*분석일: 2026-04-08*
*분석자: Kimi Claw*
