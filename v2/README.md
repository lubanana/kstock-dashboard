# V2 Unified Scanner

**처음부터 다시 설계한 리팩토링 버전**

## 개요

기존 57개 스캐너의 코드 중복과 파편화를 해결한 통합 스캐너 프레임워크

## 핵심 개선사항

| 항목 | V1 (Legacy) | V2 (Refactored) |
|:---|:---|:---|
| **파일 수** | 57개 스캐너 | 2개 전략 + 공통 인프라 |
| **코드 중복** | RSI/MA/ADX 계산 57번 반복 | `core/indicators.py`에서 1번 |
| **DB 연결** | 전략마다 다른 방식 | `DataManager` 싱글톤 |
| **리포트** | 10+개 생성기 | `ReportEngine` 1개 |
| **설정 관리** | 코드 하드코딩 | `config/strategies.yaml` |
| **전략 추가** | 새 파일 생성 | 기존 클래스 상속 |

## 아키텍처

```
v2/
├── core/                      # 공통 인프라
│   ├── indicators.py          # 기술적 지표 (RSI, MA, ADX, etc)
│   ├── data_manager.py        # DB/DataReader 통합
│   ├── strategy_base.py       # 전략 베이스 클래스
│   └── report_engine.py       # HTML 리포트 생성
├── strategies/                # 전략 플러그인
│   ├── explosive.py           # KAGGRESSIVE V7
│   └── dplus.py               # 홍인기 D+
├── config/
│   └── strategies.yaml        # 전략 파라미터
└── scanner.py                 # 메인 실행기
```

## 사용법

### 1. 전체 전략 실행
```bash
python v2/scanner.py --date 2026-04-03 --strategy all
```

### 2. 특정 전략만 실행
```bash
python v2/scanner.py --date 2026-04-03 --strategy explosive
python v2/scanner.py --date 2026-04-03 --strategy dplus
```

### 3. 복수 전략 + 점수 필터
```bash
python v2/scanner.py --date 2026-04-03 \
  --strategy explosive,dplus \
  --min-score 80 \
  --output docs/v2_report.html \
  --json results/v2_result.json
```

## 새로운 전략 추가

```python
# v2/strategies/my_strategy.py
from v2.core import StrategyBase, Signal, StrategyConfig

class MyStrategy(StrategyBase):
    def __init__(self):
        config = StrategyConfig(
            name="내 전략",
            description="전략 설명",
            min_score=70
        )
        super().__init__(config)
    
    def analyze(self, df, code, date):
        # 분석 로직
        score = calculate_score(df)
        
        if score >= self.config.min_score:
            return Signal(
                code=code,
                name=...,
                date=date,
                signal_type='buy',
                score=score,
                reason=[...],
                metadata={...}
            )
        return None
```

## V1 → V2 마이그레이션 가이드

### Legacy 파일 위치
```
legacy/scanners/     # 기존 57개 스캐너
```

### 주요 변경사항
1. **기술적 지표**: 직접 계산 → `Indicators` 클래스 사용
2. **데이터 로드**: 개별 DB 쿼리 → `DataManager.load_stock_data()`
3. **신호 반환**: dict → `Signal` dataclass
4. **리포트**: 직접 HTML 작성 → `ReportEngine` 사용

## 성능 비교

| 지표 | V1 | V2 |
|:---|---:|---:|
| 코드 라인 수 | ~15,000 | ~2,500 |
| 중복 코드 | 80%+ | <5% |
| 새 전략 추가 시간 | 2시간 | 15분 |
| 유지보수 난이도 | 높음 | 낮음 |

## 향후 계획

- [ ] 백테스팅 프레임워크 통합
- [ ] 실시간 알림 시스템
- [ ] 웹 대시보드
- [ ] 전략 최적화 (Grid Search)
