# 2604 + Japanese Strategy Integration Plan
# 2604 통합 스캐너 일본 전략 통합 및 보유일수 계산 방안

## 1. 개요

### 통합 목표
2604 V7 Hybrid 스캐너에 일본 고전 기법(일목균형표)을 추가하여:
1. **정확도 향상**: TK_CROSS, 구름 돌파 등 강력한 신호 추가
2. **보유 전략 최적화**: 종목별 맞춤형 보유일수 계산
3. **다중 시간대 분석**: 단기/중기/장기 전략 자동 분류

---

## 2. 통합 아키텍처

### 2.1 스코어링 시스템 확장

```python
# 기존 (100점)
- 거래량: 30점
- 기술적: 25점
- 피볼나치: 20점
- 시장맥락: 15점
- 모멘텀: 10점

# 확장 (120점)
- 거래량: 25점      (-5)
- 기술적: 20점      (-5)
- 피볼나치: 20점    (유지)
- 시장맥락: 15점    (유지)
- 모멘텀: 10점      (유지)
- 일목균형: 20점    (+20)  # NEW
- 사카타/캔들: 10점 (+10)  # NEW (선택적)

# 진입 조건: 90점+ (기존 80점에서 상향)
```

### 2.2 일목균형표 점수 (20점)

| 신호 | 점수 | 조건 |
|:---|:---:|:---|
| TK_CROSS 골든 | 8점 | 전환선이 기준선 상향 돌파 |
| 구름 위 | 5점 | 종가가 구름 상단 위 |
| 상승 구름 | 4점 | 선행스팬A > 선행스팬B |
| 전환선 > 기준선 | 3점 | 전환선이 기준선 위에 위치 |
| **최대** | **20점** | - |

---

## 3. 추천 보유일수 계산 로직

### 3.1 계산 파라미터

```python
@dataclass
class HoldingPeriodInput:
    # 일목균형표 요소
    tk_cross_bullish: bool       # TK_CROSS 발생 여부
    price_above_cloud: bool      # 구름 위 여부
    cloud_thickness: float       # 구름 두께 (%)
    tenkan_kijun_distance: float # 전환선-기준선 거리 (%)
    
    # 기존 2604 요소
    signal_score: int            # 종합 점수 (0-120)
    adx: float                   # 추세 강도 (0-100)
    volatility: float            # ATR 기반 변동성 (%)
    volume_trend: str            # 'explosive' | 'strong' | 'normal'
```

### 3.2 보유일수 결정 트리

```
START
│
├─ score >= 100 AND tk_cross AND adx >= 30?
│  └─ YES → 단기 (2-3일)
│
├─ score >= 90 AND volatility >= 5%?
│  └─ YES → 당일 청산 (1일)
│
├─ above_cloud AND adx >= 25 AND volatility < 3%?
│  └─ YES → 중기 (5-10일)
│
├─ above_cloud AND cloud_thickness >= 5% AND adx >= 20?
│  └─ YES → 장기 (10-20일)
│
└─ DEFAULT → 중기 (5-10일)
```

### 3.3 보유 기간별 청산 전략

| 보유 기간 | 시간 스탑 | 주 청산 방식 | 트레일링 활성화 | 특이사항 |
|:---|:---:|:---|:---:|:---|
| 당일 (1일) | 1일 | time_exit | 없음 | 장 마감 전 청산 |
| 단기 (2-3일) | 3일 | TP2 | 5% | TP2 도달 후 트레일링 |
| 중기 (5-10일) | 10일 | trailing_stop | 10% | 10% 수익 시 트레일링 시작 |
| 장기 (10-20일) | 20일 | trailing_stop | 15% | 15% 수익 시 트레일링, 기준선 기반 스탑 |
| 추세추종 (20-60일) | 60일 | trailing_stop | 20% | Kijun-sen 이탈 시 청산 |

---

## 4. 출력 포맷 확장

### 4.1 JSON 출력 확장

```json
{
  "code": "032850",
  "name": "비트컴퓨터",
  "date": "2026-04-10",
  "score": 95,
  "scores": {
    "volume": 25,
    "technical": 20,
    "fibonacci": 20,
    "market": 15,
    "momentum": 10,
    "ichimoku": 15,
    "sakata": 0
  },
  "ichimoku": {
    "tenkan_sen": 5450,
    "kijun_sen": 5385,
    "cloud_position": "below",
    "tk_cross": false,
    "bullish_cloud": true,
    "cloud_thickness_pct": 4.5
  },
  "holding_strategy": {
    "period": "medium",
    "min_days": 5,
    "max_days": 10,
    "description": "중기 (5-10일)",
    "exit_strategy": {
      "primary": "trailing_stop",
      "time_stop": 10,
      "trail_activation_pct": 10.0,
      "notes": "10% 수익 시 트레일링 시작"
    }
  },
  "targets": {
    "entry": 5450,
    "stop_loss": 5271,
    "tp1": 6018,
    "tp2": 6309,
    "tp3": 7149,
    "risk_reward_tp2": 4.8
  }
}
```

### 4.2 리포트 시각화 추가

```html
<!-- 일목균형표 요약 카드 -->
<div class="ichimoku-summary">
  <div class="ichi-item">
    <span class="label">전환선</span>
    <span class="value">5,450</span>
  </div>
  <div class="ichi-item">
    <span class="label">기준선</span>
    <span class="value">5,385</span>
  </div>
  <div class="ichi-item highlight">
    <span class="label">추천 보유</span>
    <span class="value">5-10일</span>
  </div>
</div>

<!-- 청산 전략 박스 -->
<div class="exit-strategy">
  <h4>🎯 청산 전략</h4>
  <ul>
    <li><strong>보유 기간:</strong> 5-10일 (중기)</li>
    <li><strong>시간 스탑:</strong> 10일 경과 시 시장가 청산</li>
    <li><strong>트레일링:</strong> 10% 수익 시 트레일링 스탑 활성화</li>
  </ul>
</div>
```

---

## 5. 구현 단계

### Phase 1: 일목균형표 모듈 통합 (1-2일)
1. `scanner_2604_japanese_integration.py` 모듈 완성 ✅
2. 2604 V7 스캐너에 `IchimokuCalculator` 임포트
3. `calculate_indicators()`에 일목균형표 계산 추가
4. 스코어링에 일목균형표 20점 추가

### Phase 2: 보유일수 계산 (1일)
1. `HoldingPeriodCalculator` 통합
2. `scan_stock()` 메서드에 보유일수 계산 추가
3. JSON 출력에 `holding_strategy` 필드 추가

### Phase 3: 리포트 업데이트 (1일)
1. HTML 템플릿에 일목균형표 섹션 추가
2. 청산 전략 시각화 추가
3. 색상 코딩 (단기=빨강, 중기=노랑, 장기=초록)

### Phase 4: 백테스트 (2-3일)
1. 보유일수별 성과 비교
2. 최적 청산 파라미터 튜닝
3. 전략별 승률 검증

---

## 6. 기대 효과

### 정확도 향상
- TK_CROSS 필터 추가로 허위 신호 감소 예상
- 구름 위치 확인으로 추세 방향성 확보
- **목표: 승률 60% → 65%**

### 리스크 관리
- 종목별 맞춤형 보유 기간으로 최적 수익 실현
- 시간 스탑으로 미끄러짐 방지
- **목표: 평균 손익비 1:4.8 → 1:6.0**

### 사용자 경험
- 한 화면에서 진입/청산 전략 모두 확인
- 보유 기간별 수익률 예측 제공

---

## 7. 파일 구조

```
strg/
├── scanner_2604_v7_hybrid.py          # 기존 (수정)
├── scanner_2604_japanese_integration.py  # 일본 전략 모듈 (신규) ✅
├── scanner_2604_v8_unified.py         # 통합 버전 (Phase 4)
├── generate_2604_unified_report.py    # 리포트 생성기 (수정)
└── docs/
    └── 2604_v8_report_YYYYMMDD.html   # 확장 리포트
```

---

## 8. 테스트 시나리오

| 시나리오 | 입력 조건 | 예상 보유일수 | 검증 방법 |
|:---|:---|:---:|:---|
| 강한 단기 신호 | score=105, tk_cross=true, adx=35 | 2-3일 | 3일 후 수익률 확인 |
| 구름 돌파 | above_cloud=true, adx=28, vol=2% | 5-10일 | 10일 후 수익률 확인 |
| Fire Ant 스타일 | score=95, vol=6%, gap=3% | 1일 | 당일 청산 수익률 |
| 장기 추세 | above_cloud=true, thick=6%, adx=22 | 10-20일 | 20일 후 수익률 확인 |

---

**작성일**: 2026-04-12
**버전**: v1.0
**다음 단계**: Phase 1 구현 시작
