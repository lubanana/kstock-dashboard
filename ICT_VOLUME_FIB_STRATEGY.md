# 📊 수급 + 거래량 + 피볼나치 파동 + ICT 이론 통합 매매법

## 개요
스마트머니의 흐름을 추적하는 4가지 핵심 요소를 통합한 고급 매매 방법론

---

## 1️⃣ ICT (Inner Circle Trader) 핵심 개념

### ICT 8대 핵심 개념

| 개념 | 설명 | 매매 적용 |
|:---|:---|:---|
| **Market Structure** | 시장 구조 분석 (BOS/CHoCH) | 추세 방향 설정 |
| **Order Block** | 기관 대량 주문 구간 | 진입/청산 구간 |
| **Fair Value Gap** | 가격 불균형 구간 | 되돌림 진입 |
| **Liquidity Pools** | 유동성 풀 (스탑로스 밀집) | 목표가/회피 구간 |
| **OTE Zone** | 최적 진입 구간 (62~79%) | 정밀 진입 |
| **Kill Zones** | 거래시간대 (런던/뉴욕) | 고확률 시간대 |
| **Power of 3** | 누적-조작-분배 | 일봉 구조 파악 |
| **Order Flow** | 기관 주문 흐름 | 방향성 확인 |

### ICT 핵심 용어

```
📈 BOS (Break of Structure)
   - 상승: 고점을 뚫고 상승 (추세 지속 확인)
   - 하띝: 저점을 뚫고 하락 (추세 지속 확인)

📉 CHoCH (Change of Character)  
   - 상승추세의 저점을 뚫음 → 추세 전환 가능성
   - 하락추세의 고점을 뚫음 → 추세 전환 가능성

🎯 Order Block (OB)
   - 급등/급락 전 마지막 반대 방향 봉
   - Bullish OB: 상승 전 마지막 음봉
   - Bearish OB: 하락 전 마지막 양봉

⚡ Fair Value Gap (FVG)
   - 3개 봉으로 이루어진 가격 격차
   - Bullish FVG: 고가 < 전봉저가 (상승 갭)
   - Bearish FVG: 저가 > 전봉고가 (하락 갭)
   
💧 Liquidity Pools
   - Buy Side: 스윙 고점 위 (상승 돌파 후 하락)
   - Sell Side: 스윙 저점 아래 (하락 돌파 후 상승)

🎲 Power of 3
   - Accumulation (누적): 박스권 형성
   - Manipulation (조작): 가짜 돌파 (유동성 확보)
   - Distribution (분배): 진짜 방향으로 이동
```

---

## 2️⃣ 볼륨 프로파일 (Volume Profile) 분석

### 핵심 구성요소

| 요소 | 설명 | 매매 의미 |
|:---|:---|:---|
| **POC** | 최다거래 가격 | 강력한 지지/저항 |
| **Value Area (VA)** | 거래량 70% 구간 | 핵심 거래 범위 |
| **HVN** | 고거래량 노드 | 지지/저항 가능성 ↑ |
| **LVN** | 저거래량 노드 | 급등락/돌파 가능성 ↑ |
| **VAH** | 가치영역 상단 | 저항선 |
| **VAL** | 가치영역 하단 | 지지선 |

### 볼륨 프로파일 매매 전략

```python
# 전략 1: POC 기반 지지/저항
if price_near_poc:
    if bullish_structure:
        entry = poc_level
        stop = poc_level - 1.5 * atr
    else:
        entry = poc_level  
        stop = poc_level + 1.5 * atr

# 전략 2: VA 돌파 매매
if breakout_above_vah and volume_confirm:
    entry = vah_level
    target = vah_level + (vah - val)  # VA 폭 만큼
    
# 전략 3: LVN 돌파 (빠른 이동)
if price_in_lvn and volume_surge:
    # LVN 구간은 저항이 약함 → 빠른 추세
    position_size *= 1.2  # 포지션 확대
```

---

## 3️⃣ 피볼나치 파동 (Fibonacci Wave) 분석

### 엘리엇 파동 + 피볼나치 결합

| 파동 | 피볼나치 관계 | 매매 시점 |
|:---|:---|:---|
| **Wave 1** | 추세 시작 | 관망 (확인 필요) |
| **Wave 2** | Wave 1의 50~61.8% 되돌림 | 매수 진입 (추세 확인 후) |
| **Wave 3** | Wave 1의 161.8~261.8% 확장 | 핵심 수익 구간 |
| **Wave 4** | Wave 3의 38.2% 되돌림 | 추가 매수 |
| **Wave 5** | Wave 1의 100~161.8% 확장 | 익절/추세 종료 |

### ICT + 피볼나치 통합

```
Optimal Trade Entry (OTE) Zone = 62% ~ 79% Fibonacci
├── 62%: 보수적 진입
├── 70%: 균형 진입  
└── 79%: 공격적 진입

Confluence (합치) 구간:
├── Fibonacci 61.8% + Order Block
├── Fibonacci 50% + Fair Value Gap
└── Fibonacci 38.2% + Volume Profile POC
```

---

## 4️⃣ 수급 분석 (Capital Flow)

### 핵심 지표

| 지표 | 계산 | 해석 |
|:---|:---|:---|
| **RVol** | 당일거래량 / 20일평균 | 2.0+ = 유의미한 변화 |
| **VIR** | (당일-전일)/전일 | 150%+ = 급증 |
| **거래대금** | 거래량 × 주가 | 큰손 참여 확인 |
| **누적/분배** | (종가-저가)/(고가-저가) × 거래량 | 0.7+ = 누적 |

### 스마트머니 흔적 감지

```python
smart_money_signals = {
    # 큰손 매집
    'accumulation': '장중 하락 후 종가 부근 강한 매수',
    
    # 유동성 확보  
    'liquidity_grab': '스윙 고점/저점 돌파 후 역전',
    
    # 추세 시작
    'trend_start': 'FVG 형성 + 거래량 급증',
    
    # 추세 종료
    'trend_end': 'CHoCH + 거래량 급감',
}
```

---

## 5️⃣ 통합 매매 시스템 설계

### 진입 시그널 (Confluence 3개 이상)

```
[강력 매수 시그널]
✓ ICT: Bullish Order Block + BOS 확인
✓ 피볼나치: 61.8% 되돌림 (OTE Zone)
✓ 볼륨프로파일: POC 지지 + VA 낮은 구간
✓ 수급: RVol ≥ 2.0 + 누적확인

[진입 조건]
1. 1봉전: Stop Hunt (유동성 확보)
2. 현재: Order Block 근접 + FVG 유지
3. 확인: 거래량 급증 (RVol ≥ 1.5)
4. 진입: OTE Zone (62~79%) 내 청산가
```

### 손절/익절 전략

```python
# 손절: Order Block 반대편
stop_loss = bullish_ob_low * 0.995  # -0.5%

# 목표1: Liquidity Pool (스윙 고점)
target_1 = recent_swing_high

# 목표2: Fibonacci Extension (161.8%)
target_2 = entry + (entry - wave_low) * 1.618

# 목표3: 다음 Order Block
target_3 = next_bearish_ob_high
```

---

## 6️⃣ 스캐너 구현 아키텍처

### 모듈 구조

```
ict_volume_fib_scanner/
├── core/
│   ├── __init__.py
│   ├── ict_analyzer.py        # ICT 개념 분석
│   ├── volume_profile.py      # 볼륨 프로파일
│   ├── fibonacci_waves.py     # 피볼나치 파동
│   └── capital_flow.py        # 수급 분석
│
├── scanner/
│   ├── __init__.py
│   ├── signal_generator.py    # 신호 통합
│   ├── entry_optimizer.py     # 진입 최적화
│   └── risk_manager.py        # 리스크 관리
│
├── data/
│   ├── fetcher.py             # 데이터 수집
│   └── cache.py               # 캐싱
│
└── reports/
    ├── html_generator.py      # 리포트 생성
    └── visualizer.py          # 차트 시각화
```

### 핵심 클래스 설계

```python
class ICTVolumeFibScanner:
    """
    ICT + 볼륨프로파일 + 피볼나치 + 수급 통합 스캐너
    """
    
    def __init__(self):
        self.ict = ICTAnalyzer()
        self.vp = VolumeProfileAnalyzer()
        self.fib = FibonacciWaveAnalyzer()
        self.flow = CapitalFlowAnalyzer()
    
    def scan(self, symbol, timeframe='1D'):
        # 1. ICT 분석
        ict_signals = self.ict.analyze(symbol)
        
        # 2. 볼륨 프로파일
        vp_levels = self.vp.calculate(symbol)
        
        # 3. 피볼나치 파동
        fib_levels = self.fib.calculate(symbol)
        
        # 4. 수급 분석
        flow_data = self.flow.analyze(symbol)
        
        # 5. 통합 신호 생성
        signal = self.generate_signal(
            ict_signals, vp_levels, 
            fib_levels, flow_data
        )
        
        return signal
    
    def generate_signal(self, ict, vp, fib, flow):
        """Confluence 기반 신호 생성"""
        score = 0
        confluence = []
        
        # ICT 점수
        if ict['order_block_near']:
            score += 25
            confluence.append('OrderBlock')
        if ict['fvg_present']:
            score += 20
            confluence.append('FVG')
        if ict['bos_confirmed']:
            score += 15
            confluence.append('BOS')
            
        # 볼륨프로파일 점수
        if vp['price_near_poc']:
            score += 20
            confluence.append('POC')
        if vp['in_value_area']:
            score += 10
            
        # 피볼나치 점수
        if 50 <= fib['retracement'] <= 79:
            score += 20
            confluence.append('OTE_Zone')
            
        # 수급 점수
        if flow['rvol'] >= 2.0:
            score += 15
            confluence.append('HighVolume')
        if flow['accumulation']:
            score += 10
            confluence.append('Accumulation')
        
        return {
            'score': score,
            'confluence': confluence,
            'signal': 'STRONG_BUY' if score >= 80 else
                     'BUY' if score >= 60 else
                     'NEUTRAL',
            'entry_zone': self.calculate_entry(ict, fib),
            'stop_loss': self.calculate_stop(ict),
            'targets': self.calculate_targets(vp, fib)
        }
```

---

## 7️⃣ 신호 등급 및 매매 전략

### 종합 점수 체계

| 점수 | 등급 | 신호 | 포지션 | 리스크 |
|:---:|:---:|:---|:---|:---|
| 90~100 | S | 강력 매수 | 20% | 1:4+ |
| 80~89 | A | 매수 | 15% | 1:3~4 |
| 70~79 | B | 관망 후 매수 | 10% | 1:2.5~3 |
| 60~69 | C | 조걸부 매수 | 5% | 1:2 |
| < 60 | D | 제외 | - | - |

### 매매 일지 템플릿

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
[매매 기록] #{번호}
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
종목: {symbol}
진입일: {entry_date}
진입가: {entry_price}

[신호 분석]
□ ICT: {order_block}/{fvg}/{bos}
□ 볼륨프로파일: {poc_position}
□ 피볼나치: {retracement_level}%
□ 수급: RVol={rvol}, 누적={accumulation}

[진입 근거]
Confluence: {confluence_items}
신호등급: {signal_grade} ({score}점)

[리스크 관리]
손절가: {stop_loss}
목표1: {target_1} (손익비: {rr_1})
목표2: {target_2} (손익비: {rr_2})

[결과]
청산일: {exit_date}
수익률: {return_pct}%
평가: {review}
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

---

## 8️⃣ 백테스트 계획

### 테스트 시나리오

| 시나리오 | 조건 | 기대 결과 |
|:---|:---|:---|
| **이상적** | Confluence 4개+ | 승률 65%+ |
| **표준** | Confluence 3개 | 승률 50~55% |
| **최소** | Confluence 2개 | 승률 40~45% |
| **실패** | Confluence 1개 | 승률 < 40% |

### 측정 지표

```python
backtest_metrics = {
    'win_rate': '승률 (%)',
    'profit_factor': '수익비율',
    'sharpe_ratio': '샤프비율',
    'max_drawdown': '최대낙폭 (%)',
    'avg_rr': '평균 손익비',
    'confluence_correlation': '합치 강도별 승률',
}
```

---

## 💡 핵심 인사이트

1. **Confluence가 핵심** - 단일 신호보다 다중 신호 겹침이 중요
2. **시간이 아군** - Kill Zone 시간대 거래 확률 ↑
3. **유동성 존중** - Liquidity Pool 인식 필수
4. **거래량 확인** - 모든 신호는 거래량으로 검증
5. **단순함 추구** - 3개 이상 지표 복잡도 ↓

---

> "시장은 무작위가 아니다. 스마트머니의 흔적을 읽어라." - ICT
