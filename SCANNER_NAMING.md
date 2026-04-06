# 📊 스캐너 명명 규칙 및 목록

## 1. 홍인기 스캐너 (D+ 주도주 매매법)

### 공식 명칭
**"홍인기 D+ 주도주 스캐너"** (Hong Inki D+ Leading Stock Scanner)

### 파일명
- `honginki_dplus_strategy.py`
- `dplus_leading_stock_strategy.py` (원본)

### 전략 개요
| 항목 | 내용 |
|:---|:---|
| **창시자** | 대왕개미 홍인기 (YouTube: 303K 구독자) |
| **영상** | https://youtu.be/cI9XTnBS5JQ |
| **핵심 개념** | 주도 테마 대장주를 D+0, D+1, D+2로 스윙 매매 |
| **진입 조건** | 5개+ 상한가 섹터, 대장주 9:30AM 확인 후 진입 |
| **수익 실현** | D+0 상한가 일부, D+1 갭상승 추가, D+2 전량 |
| **특징** | 시장 급락 시 주도주 매수 기회로 활용 |

### 매매 규칙 요약
```
1. 주도 테마 감지: 동일 섹터 5개 이상 상한가
2. 대장주 선별: 거래대금 충분, 소형주 제외
3. 진입: 오전 9:30 테마 확인 후
4. D+0: 상한가 도달 시 일부 수익 실현 + 오버나잇
5. D+1: 갭상승 시 절반 수익, 되돌림 시 분할 매수
6. D+2: 추가 갭상승 시 전량 수익 실현
7. 리스크 관리: 지수 급락 시 주도주 분할 매수
```

---

## 2. 개선안 7 스캐너 (폭발적 상승)

### 공식 명칭
**"KAGGRESSIVE 폭발적 상승 스캐너 V7"** (KAGGRESSIVE Explosive Rise Scanner V7)

### 파일명
- `explosive_scanner_v7.py`

### 전략 개요
| 항목 | 내용 |
|:---|:---|
| **버전** | V7 (개선안 7 - 복합 1+2+5) |
| **스코어링** | 100점 만점 |
| **진입 기준** | 85점+, ADX 20+, RSI 40-70 |
| **리스크 관리** | -7% 손절, +25% 익절, 10% 트레일링 |
| **포지션** | 90점+ 20%, 85-89점 8%, 섹터 중복 금지 |

### 스코어링 상세
| 요소 | 배점 | 기준 |
|:---|:---:|:---|
| 거래량 | 30점 | 20일 평균 대비 300%+ |
| 기술적 | 20점 | 20일선 상향 돌파 + 정배열 |
| 시가총액 | 15점 | 5,000억원 이하 |
| 외국인 수급 | 10점 | 3거래일 연속 순매수 |
| 뉴스/이벤트 | 15점 | 긍정적 트리거 존재 |
| 테마 | 10점 | 핫섹터(로봇/AI/바이오/반도체) |

---

## 3. 네이밍 컨벤션

### 패턴
```
[전략_창시자]_[전략_명칭]_[버전].py
```

### 예시
| 전략 | 파일명 | 설명 |
|:---|:---|:---|
| 홍인기 D+ | `honginki_dplus_strategy.py` | YouTube 분석 기반 |
| KAGGRESSIVE V7 | `explosive_scanner_v7.py` | 개선안 7 기반 |
| 홍인기 D+ 백테스트 | `honginki_dplus_backtest.py` | (향후 생성) |
| 홍인기 D+ 리포트 | `honginki_dplus_report.py` | (향후 생성) |

---

## 4. 관련 파일 목록

### 핵심 전략 파일
```
/root/.openclaw/workspace/strg/
├── honginki_dplus_strategy.py      # 홍인기 D+ 주도주 스캐너
├── dplus_leading_stock_strategy.py  # (원본)
├── explosive_scanner_v7.py          # KAGGRESSIVE V7 스캐너
└── SCANNER_NAMING.md                # 이 파일
```

### 생성된 리포트
```
/root/.openclaw/workspace/strg/docs/
├── explosive_scan_report_YYYYMMDD.html   # V7 스캔 결과
└── index.html                             # GitHub Pages 메인
```

---

*Last Updated: 2026-04-06*
