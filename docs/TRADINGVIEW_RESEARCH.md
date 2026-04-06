# TradingView 연동 연구 보고서

## 개요
TradingView를 통한 가격 정보 구축 및 스캐너 구동 방법 연구

---

## 1. TradingView 데이터 접근 방법

### 1.1 공식 API (REST API)
- **대상**: 브로커, 기관 투자자
- **비용**: 유료 (월 $XX~XXX)
- **특징**: 실시간 데이터, 실행 기능
- **적합성**: ❌ 개인/소규모 팀에는 과도한 비용

### 1.2 Lightweight Charts (오픈소스)
- **GitHub**: https://github.com/tradingview/lightweight-charts
- **라이선스**: Apache 2.0 (Attribution 필수)
- **용도**: 웹 차트 렌더링
- **데이터 소스**: 자체 제공 필요 (TV 데이터 X)
- **적합성**: ⚠️ UI용이지 데이터 수집용 아님

### 1.3 Pine Script + Export
- **방법**: Pine Script로 지표 개발 → CSV/JSON export
- **제한**: 수동 export, 자동화 어려움
- **적합성**: ⚠️ 자동화 불가

### 1.4 비공식 라이브러리 (tvdatafeed)
- **GitHub**: StreamAlpha/tvdatafeed (현재 archived)
- **방법**: TradingView 웹소켓 역분석
- **상태**: 유지보수 중단, 불안정
- **적합성**: ❌ 위험한 방법

---

## 2. 대안 비교

| 방법 | 실시간 | 자동화 | 비용 | 안정성 | 권장 |
|:---|:---:|:---:|:---:|:---:|:---:|
| **FinanceDataReader** | 지연(1일) | ✅ | 물건 | 중간 | ⭐⭐⭐⭐⭐ |
| **TradingView 공식 API** | 실시간 | ✅ | 유료 | 높음 | ⭐⭐⭐ |
| **tvdatafeed** | 실시간 | ⚠️ | 물건 | 낮음 | ⭐ |
| **Yahoo Finance** | 지연(15분) | ✅ | 물건 | 중간 | ⭐⭐⭐⭐ |
| **CCXT (암호화폐)** | 실시간 | ✅ | 물건 | 중간 | ⭐⭐⭐⭐ |

---

## 3. 현재 시스템 대비 TradingView 연동 장단점

### ✅ 장점
1. **실시간 데이터**: 1분/5분/15분 단위 스캐닝 가능
2. **풍부한 지표**: 100+ 기술적 지표 내장
3. **글로벌 시장**: 한국 + 미국 + 선물 동시 모니터링
4. **알림 연동**: Webhook → 텔레그램/Discord

### ❌ 단점
1. **비용**: Pro+ 플랜 ($30/월) 필요
2. **API 제한**: 공식 API는 고가
3. **자동화 한계**: Pine Script는 백테스트/알림용
4. **의존성**: TV 서비스 중단 시 시스템 마비

---

## 4. 권장 아키텍처 (하이브리드)

```
┌─────────────────────────────────────────────────────────────┐
│                    TradingView (Pro+)                        │
│  - 실시간 차트 모니터링                                       │
│  - Pine Script 스캐너 (선별적 사용)                           │
│  - Webhook 알림 → 텔레그램                                    │
└────────────────────┬────────────────────────────────────────┘
                     │ Webhook (Signals only)
                     ▼
┌─────────────────────────────────────────────────────────────┐
│                    V2 Unified Scanner                        │
│  - FinanceDataReader (일일 OHLCV)                            │
│  - 백테스팅 프레임워크                                        │
│  - 포트폴리오 관리                                           │
│  - 실전 거래 실행 (선택)                                      │
└─────────────────────────────────────────────────────────────┘
```

---

## 5. Pine Script 스캐너 예시 (IVF 스타일)

```pinescript
//@version=5
indicator("IVF Scanner Signal", overlay=true)

// === 1. 수급 (Supply/Demand) ===
buyingPressure = (close - low) / (high - low + 0.001)
supplyScore = buyingPressure > 0.7 ? 30 : buyingPressure > 0.6 ? 20 : 10

// === 2. 거래량 (Volume Profile) ===
volRatio = volume / ta.sma(volume, 20)
volumeScore = volRatio > 3 ? 25 : volRatio > 2 ? 15 : 5

// === 3. 피볼나치 ===
swingHigh = ta.highest(high, 40)
swingLow = ta.lowest(low, 40)
fib382 = swingHigh - (swingHigh - swingLow) * 0.382
fib618 = swingHigh - (swingHigh - swingLow) * 0.618
inFibZone = close <= fib382 and close >= fib618
fibScore = inFibZone ? 25 : 0

// === 4. ICT (간소화) ===
// Fair Value Gap detection
fvgUp = low > high[1]
fvgScore = fvgUp ? 20 : 0

// === 총점 ===
totalScore = supplyScore + volumeScore + fibScore + fvgScore

// === 신호 ===
signal = totalScore >= 75

plotshape(signal, style=shape.triangleup, location=location.belowbar, 
          color=color.green, size=size.normal, title="IVF Buy")

alertcondition(signal, title="IVF Signal", 
               message='IVF 75+ Score: {{ticker}} at {{close}}')
```

---

## 6. Webhook 연동 설정

### TradingView Alert → V2 Scanner

```python
# webhook_server.py
from flask import Flask, request
import json

app = Flask(__name__)

@app.route('/webhook/tradingview', methods=['POST'])
def tradingview_webhook():
    data = request.json
    # {
    #   "ticker": "005930",
    #   "price": "75000",
    #   "score": "82",
    #   "time": "2026-04-06T09:30:00Z"
    # }
    
    # V2 스캐너로 전달
    process_signal(data)
    return "OK"

def process_signal(data):
    # V2 시스템과 연동
    pass

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
```

---

## 7. 결론 및 권장사항

### ✅ 추천 방식
1. **데이터**: FinanceDataReader (현재 방식 유지)
   - 물건, 안정적, 한국 주식 전문
   - 일일 OHLCV에 적합

2. **실시간 스캐닝**: TradingView Pine Script (보조)
   - Pro+ 구독 시 1분/5분 단위 스캐너
   - Webhook으로 V2에 신호 전달
   - 주요 종목 선별 감시용

3. **차트**: Lightweight Charts (V2 Report)
   - 리포트 차트 렌더링 개선
   - TradingView 스타일 유사하게

### ❌ 비추천
- TradingView 공식 API (비용 과다)
- tvdatafeed (보안/유지보수 이슈)
- 완전 TV 대체 (의존성 위험)

---

## 8. 다음 단계 (옵션)

| 우선순위 | 작업 | 예상 시간 |
|:---|:---|:---|
| 1 | TradingView Pro+ 테스트 계정 생성 | 10분 |
| 2 | Pine Script IVF 스캐너 개발 | 30분 |
| 3 | Webhook 서버 구축 | 1시간 |
| 4 | V2 Report에 Lightweight Charts 적용 | 2시간 |

---

*작성일: 2026-04-07*
*참고: TradingView 공식 문서, GitHub 오픈소스 프로젝트*
