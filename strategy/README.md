# Pivot Point Strategy Package

피벗 포인트 돌파 전략 백테스팅 및 스캐닝 프로그램

## 📁 파일 구성

```
strg/
├── pivot_strategy.py       # 메인 전략 백테스터
├── pivot_report.py         # 보고서 생성 및 시각화
├── multi_stock_scanner.py  # 다중 종목 스캐너
├── requirements.txt        # 의존성 목록
└── README.md              # 이 파일
```

## 📦 설치

```bash
pip install -r requirements.txt
```

## 🚀 사용법

### 1. 단일 종목 백테스트

```python
from pivot_strategy import PivotPointStrategy

strategy = PivotPointStrategy(
    symbol='005930',           # 삼성전자
    start_date='2024-01-01',
    end_date='2024-12-31',
    initial_capital=10_000_000,  # 1000만원
    pivot_period=20,           # 20일 신고가
    volume_threshold=1.5,      # 거래량 150%
)

result, trades_df = strategy.run_backtest()
```

### 2. 보고서 생성

```python
from pivot_report import StrategyReport, StrategyVisualizer

# 보고서 생성
report = StrategyReport(output_dir='./reports')
report_path = report.generate_report(strategy, result, trades_df)

# 시각화
viz = StrategyVisualizer()
viz.plot_trades_matplotlib(strategy, result, save_path='chart.png')
viz.plot_trades_plotly(strategy, result, save_path='chart.html')
```

### 3. 전 종목 스캔

```python
from multi_stock_scanner import MultiStockScanner

scanner = MultiStockScanner(
    pivot_period=20,
    volume_threshold=1.5,
)

results = scanner.scan_all(max_workers=8)
scanner.save_results(results)
```

## 📊 전략 파라미터

| 파라미터 | 기본값 | 설명 |
|---------|-------|------|
| `pivot_period` | 20 | 피벗 포인트 계산 기간 (일) |
| `volume_threshold` | 1.5 | 거래량 임계값 (1.5 = 150%) |
| `pyramiding_pct_1` | 0.30 | 1차 진입 비율 (30%) |
| `pyramiding_pct_2` | 0.30 | 2차 진입 비율 (30%) |
| `pyramiding_pct_3` | 0.40 | 3차 진입 비율 (40%) |
| `pyramiding_trigger` | 0.05 | 피라미딩 트리거 (5%) |
| `stop_loss_pct` | 0.10 | 손절 라인 (10%) |
| `trailing_stop_pct` | 0.15 | 트레일링 스탑 (15%) |

## 📈 출력 결과

- **최종 수익률**: 초기 자본 대비 최종 수익률
- **MDD (최대 낙폭)**: 최대 낙폭률
- **승률**: 수익 거래 비율
- **Profit Factor**: 총 수익 / 총 손실
- **거래 내역**: 매수/매도 시점 기록 DataFrame

## 🎨 시각화

- **Matplotlib**: 정적 차트 (4개 서브플롯)
  - 주가 + 매매 신호
  - 거래량
  - 포트폴리오 가치
  - Drawdown
  
- **Plotly**: 인터랙티브 차트
  - 캔들스틱 차트
  - 호버 상세 정보
  - 줌/패닝 지원

## 📋 출력 예시

```
📊 백테스트 결과
============================================================
총 거래 횟수: 5회
승률: 60.0%
Profit Factor: 2.35

최종 수익률: +23.45%
최대 낙폭 (MDD): -8.32%

초기 자본: 10,000,000원
최종 자산: 12,345,000원
============================================================
```

## ⚠️ 주의사항

- 이 프로그램은 교육 목적으로 제작되었습니다.
- 실제 투자에 사용하기 전에 충분한 검증이 필요합니다.
- 과거 성과가 미래 수익을 보장하지 않습니다.

## 🔧 Requirements

- Python 3.8+
- finance-datareader
- pandas
- pandas-ta
- matplotlib
- plotly
- numpy
