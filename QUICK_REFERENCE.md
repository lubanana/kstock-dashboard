# 📚 K-Stock Dashboard Quick Reference

**핵심 프로그램 빠른 참조 가이드**

---

## 🚀 자주 사용하는 명령어

### 1. 일일 업데이트 (19:00 자동 실행)

```bash
# 수동 실행
python3 daily_update_batch.py

# 전체 DB 재구축
python3 full_db_update.py

# 모니터링
python3 monitor_update.py
```

### 2. 스캐너 실행

```bash
# 통합 멀티 전략 스캔 (V + NPS + B01)
python3 integrated_multi_scanner.py

# 개별 전략 스캔
python3 v_series_scanner.py
python3 nps_value_scanner.py
python3 b01_buffett_scanner.py
python3 m10_scanner.py

# Pivot Point 스캔
cd strategy && python3 scan.py
```

### 3. 리포트 생성

```bash
# 통합 리포트
python3 integrated_report_generator.py

# V-Series 리포트
python3 v_series_daily_report.py

# B01 + NPS 통합
python3 b01_nps_integrated_report.py
```

---

## 📊 프로그램별 상세 사용법

### 🔧 Data Wrappers

#### fdr_wrapper.py
```python
from fdr_wrapper import get_price

# 단일 종목
df = get_price('005930', start='2024-01-01')

# 여러 종목
from fdr_wrapper import get_prices_parallel
prices = get_prices_parallel(['005930', '000660'], max_workers=4)
```

#### stock_repository.py
```python
from stock_repository import StockRepository

repo = StockRepository()

# 데이터 저장
repo.save_prices(symbol, df)

# 데이터 조회
df = repo.get_prices(symbol, start='2024-01-01')

# 캐시 확인
if repo.is_cached(symbol, '2026-03-20'):
    print("캐시됨")
```

---

### 🎯 Strategy Scanners

#### integrated_multi_scanner.py
```bash
# 전체 종목 스캔 (3,299개)
python3 integrated_multi_scanner.py

# 출력
# - reports/multi_strategy/v_scan_*.json
# - reports/multi_strategy/nps_scan_*.json
# - reports/multi_strategy/b01_scan_*.json
# - reports/multi_strategy/multi_scan_*.json
```

**선정 기준:**
| 전략 | 최소 점수 | 상위 개수 |
|------|----------|----------|
| V-Strategy | 70점 | 10개 |
| NPS | 70점 | 10개 |
| B01 | 65점 | 10개 |
| Multi | 65점 | 10개 |

#### v_series_scanner.py
```bash
python3 v_series_scanner.py

# 필터 조건:
# - Value Score 65+
# - Fibonacci Retracement 38.2% ~ 50%
# - ATR 기반 손익비 1:1.5 이상
```

#### nps_value_scanner.py
```bash
python3 nps_value_scanner.py

# 점수 구성:
# - 추세 점수 (40점): EMA20 > EMA60
# - 모멘텀 점수 (35점): RSI 50~60
# - 거래량 점수 (25점): 20일 평균 대비 150%+
```

---

### ⏰ Execution/Scheduling

#### daily_update_batch.py
```bash
# 설정된 70개 핵심 종목 업데이트
python3 daily_update_batch.py

# 크론 설정 (자동)
# 0 19 * * * cd /path && python3 -u daily_update_batch.py >> /var/log/stock_update.log 2>&1
```

**특징:**
- 10분마다 진행 상황 보고
- 누락된 종목 자동 구축
- 실패 시 재시도

#### monitor_update.py
```bash
# 백그라운드 모니터링
python3 monitor_update.py &

# 기능:
# - 프로세스 상태 체크 (10분 간격)
# - 완료 알림
# - 에러 로깅
```

---

### 📈 Report Generation

#### integrated_report_generator.py
```bash
# 리포트 생성
python3 integrated_report_generator.py

# 출력 파일:
# - ./reports/Integrated_Multi_Strategy_Report_YYYYMMDD_HHMM.html
# - ./docs/Integrated_Multi_Strategy_Report_YYYYMMDD_HHMM.html (GitHub용)

# GitHub Pages URL:
# https://lubanana.github.io/kstock-dashboard/Integrated_Multi_Strategy_Report_YYYYMMDD_HHMM.html
```

**리포트 기능:**
- 전략별 필터 탭
- 종목 코드 + 종목명 표시
- 현재가/목표가/손절가 표시
- 실제 손익비 계산값
- TradingView 차트 연동 (클릭 시 모달)

---

### 🏗️ Database Construction

#### build_daily_pivot_db.py
```bash
# DB 초기 구축
python3 build_daily_pivot_db.py

# 기능:
# - KOSPI/KOSDAQ 전종목 데이터 수집
# - SQLite DB 생성
# - 인덱스 생성
```

#### update_db_latest.py
```bash
# 최신 데이터로 업데이트
python3 update_db_latest.py

# 기능:
# - 누락된 날짜만 업데이트
# - 중복 체크
# - 트랜잭션 관리
```

---

## 🐍 코드 예시

### 새로운 스캐너 만들기

```python
#!/usr/bin/env python3
"""
My Custom Scanner Template
"""

import pandas as pd
import numpy as np
from datetime import datetime
import sys
sys.path.insert(0, '.')
from fdr_wrapper import get_price
from stock_repository import StockRepository

class MyScanner:
    def __init__(self):
        self.symbols = self._load_symbols()
        self.results = []
    
    def _load_symbols(self):
        """종목 리스트 로드"""
        repo = StockRepository()
        return repo.get_all_symbols()
    
    def calculate_score(self, df: pd.DataFrame) -> dict:
        """점수 계산 로직"""
        latest = df.iloc[-1]
        
        # 예: RSI 기반 점수
        rsi = latest.get('rsi', 50)
        score = 100 - abs(rsi - 50) * 2  # RSI 50에 가까울수록 높은 점수
        
        return {
            'score': score,
            'rsi': rsi,
            'current_price': latest['close']
        }
    
    def scan(self):
        """전체 스캔 실행"""
        for symbol in self.symbols:
            df = get_price(symbol, days=60)
            if df.empty:
                continue
            
            result = self.calculate_score(df)
            
            # 선정 조건
            if result['score'] >= 70:
                self.results.append({
                    'symbol': symbol,
                    'score': result['score'],
                    'price': result['current_price'],
                    'rsi': result['rsi']
                })
        
        # 점수 기준 정렬
        self.results.sort(key=lambda x: x['score'], reverse=True)
        return self.results[:10]  # 상위 10개만
    
    def save_results(self, filename='my_scan_results.json'):
        """결과 저장"""
        import json
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump({
                'scan_date': datetime.now().strftime('%Y-%m-%d'),
                'count': len(self.results),
                'stocks': self.results
            }, f, ensure_ascii=False, indent=2)

if __name__ == '__main__':
    scanner = MyScanner()
    results = scanner.scan()
    scanner.save_results()
    print(f"선정된 종목: {len(results)}개")
```

---

## 📁 파일 경로 정리

### 중요 경로

```
strg/
├── data/
│   ├── pivot_strategy.db      # 메인 주가 DB
│   ├── dart_cache.db          # DART 공시 DB
│   └── level1_prices.db       # Level1 가격 DB
│
├── reports/
│   ├── multi_strategy/        # 통합 스캐너 결과
│   │   ├── v_scan_*.json
│   │   ├── nps_scan_*.json
│   │   ├── b01_scan_*.json
│   │   └── multi_scan_*.json
│   │
│   ├── b01_buffett/           # B01 리포트
│   ├── nps/                   # NPS 리포트
│   └── *.html                 # 생성된 HTML 리포트
│
├── docs/                      # GitHub Pages
│   └── *.html                 # 배포용 리포트
│
├── strategy/                  # Pivot Point 전략
│   ├── pivot_strategy.py
│   ├── scan.py
│   └── local_db.py
│
└── logs/                      # 로그 파일
```

---

## 🔍 트러블슈팅

### 문제: 종목명이 표시되지 않음
```python
# _get_name() 메서드에 종목 추가
names = {
    '신규종목코드': '종목명',
    # ...
}
```

### 문제: 손익비 계산 오류
```python
# calculate_atr_targets() 확인
potential_gain = target_price - current_price
potential_loss = current_price - stop_loss
rr_ratio = potential_gain / potential_loss if potential_loss > 0 else 0
```

### 문제: DB 업데이트 실패
```bash
# 프로세스 확인
ps aux | grep python3

# 로그 확인
tail -f full_update.log

# 수동 재실행
python3 full_db_update.py
```

### 문제: 크론 작업 확인
```bash
# 크론 목록 확인
crontab -l

# 크론 로그 확인
grep CRON /var/log/syslog
```

---

## 📞 지원 명령어

```bash
# Git 상태 확인
git status

# Git 커밋 및 푸시
git add -A
git commit -m "메시지"
git push origin main

# 디스크 사용량 확인
du -sh data/*.db

# 프로세스 모니터링
htop
# 또는
ps aux | grep python3

# 로그 실시간 확인
tail -f *.log
```

---

**작성일**: 2026-03-21  
**버전**: 1.0
