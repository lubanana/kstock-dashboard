# KStock 데이터 활용 가이드

## 빠른 시작
```python
from kstock_data import data

# 시장 상태 확인
data.market_status()
# → "KOSPI: 6,307 (+3.67%) | BULLISH | RSI 과매수 (81.58)"

# KOSPI 데이터
df = data.kospi(30)  # 최근 30일

# 매매 신호
signal = data.kospi_signal()
# → "CAUTION: 과매수, 익절 고려"

# 조건 확인
if data.is_bullish('kospi'):
    print("상승 추세!")

if data.is_overbought('kospi'):
    print("과매수 경고!")
```

## 사용 예시

### 1. KOSPI 분석
```python
# 최근 데이터
kospi = data.kospi(60)  # 60일
latest = kospi.iloc[-1]

# 이동평균 계산
ma20 = kospi['Close'].rolling(20).mean().iloc[-1]
ma60 = kospi['Close'].rolling(60).mean().iloc[-1]
```

### 2. 삼성전자 분석
```python
samsung = data.stock('samsung')
if samsung is not None:
    latest_price = samsung['Close'].iloc[-1]
    change = samsung['Close'].pct_change().iloc[-1] * 100
```

### 3. 리포트 생성
```python
summary = data.kospi_summary()
print(f"""
KOSPI 현황
- 종가: {summary['price']:,.0f}
- 등락: {summary['change_pct']:+.2f}%
- 추세: {summary['trend']}
- RSI: {summary['rsi']:.1f}
- 알림: {summary['alert']}
""")
```

## 데이터 파일 위치
- `/home/programs/kstock_analyzer/data/kospi_history.csv`
- `/home/programs/kstock_analyzer/data/kosdaq_history.csv`
- `/home/programs/kstock_analyzer/data/samsung.csv`
- `/home/programs/kstock_analyzer/data/skhynix.csv`
- `/home/programs/kstock_analyzer/market_data_index.json`

## 업데이트 방법
```bash
cd /home/programs/kstock_analyzer
python3 update_data.py  # 향후 업데이트 스크립트
```
