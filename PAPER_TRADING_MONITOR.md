# KAGGRESSIVE Paper Trading Monitor

## 📅 일일 알림 스케줄

| 시간 | 알림 내용 |
|:---|:---|
| **오전 8:00** | 시장 시작 전 포트폴리오 현황 + 진입 신호 확인 |
| **오후 5:00** | 장 마감 후 결과 취합 + 청산 신호 확인 |

## 🔔 알림 유형

### 매수 신호 (🟢)
- 65점+ 종목 발생 시
- 신규 진입 가능 종목

### 매도 신호 (🔴)
- 7거래일 보유 만기
- 손절가 도달
- 목표가 도달

### 포트폴리오 요약 (📊)
- 보유 종목 수
- 평가 손익
- 실현 손익
- 총 수익률

## 🛠️ 파일 구조

```
strg/
├── paper_trading_monitor.py      # 모니터링 엔진
├── paper_trading_cron.sh         # 크론 실행 스크립트
├── paper_trading_schedule.json   # 스케줄 설정
└── data/
    └── paper_positions.json      # 보유 포지션 저장
```

## 📝 수동 실행

```bash
# 전체 확인
python3 paper_trading_monitor.py --check all --summary

# 진입 신호만
python3 paper_trading_monitor.py --check entry

# 청산 신호만  
python3 paper_trading_monitor.py --check exit

# 포트폴리오 요약
python3 paper_trading_monitor.py --summary
```

## ⚙️ 크론 설정 (수동)

```bash
# 크론탭 편집
crontab -e

# 오전 8시, 오후 5시 실행
0 8 * * 1-5 /root/.openclaw/workspace/strg/paper_trading_cron.sh
0 17 * * 1-5 /root/.openclaw/workspace/strg/paper_trading_cron.sh
```

## 📊 알림 예시

### 오전 8시 알림
```
📊 Paper Trading - 오전 현황 (08:00)

🟢 매수 신호 (2개)
   삼성전자 (005930): 72점 @ 67,500원
   SK하이닉스 (000660): 68점 @ 198,000원

📊 포트폴리오 현황
   보유: 3종목 | 청산: 5종목
   평가손익: +2.34%
   실현손익: +5.67%
   총 수익: +8.01%
```

### 오후 5시 알림
```
📊 Paper Trading - 장 마감 정산 (17:00)

🔴 매도 신호 (1개)
   📈 한미반도체: +12.41% (목표도달)

📊 포트폴리오 현황
   보유: 2종목 | 청산: 6종목
   평가손익: +1.23%
   실현손익: +8.45%
   총 수익: +9.68%
```

## 🎯 임계값 설정

`paper_trading_monitor.py`에서 수정:

```python
# 진입 기준 (기본: 65점)
entry = monitor.check_entry_signals(threshold=65)

# 보유일 (기본: 7일)
if hold_days >= 7:
    exit_reason = '만기청산'
```
