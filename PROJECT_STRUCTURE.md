# K-Stock Dashboard 프로젝트 구조 명세서

**작성일**: 2026-03-21  
**프로젝트 경로**: `/root/.openclaw/workspace/strg`  
**GitHub**: https://github.com/lubanana/kstock-dashboard

---

## 📁 디렉토리 구조 개요

```
strg/
├── 📊 data/                    # 데이터베이스 및 캐시
├── 📈 docs/                    # GitHub Pages 정적 리포트
├── 📉 reports/                 # 생성된 리포트 (JSON/HTML)
├── 🔧 strategy/                # Pivot Point 전략 모듈
├── 🤖 agents/                  # AI 에이전트 설정
├── 📰 analysis/                # 기술적 분석 모듈
└── 🐍 *.py                     # 메인 Python 프로그램
```

---

## 1️⃣ 데이터 래퍼/기반 계층 (Data Wrappers & Infrastructure)

> **역할**: 외부 API 연동, 데이터 표준화, 로컬 캐싱

| 파일 | 설명 | 주요 기능 |
|------|------|-----------|
| **fdr_wrapper.py** | FinanceDataReader 래퍼 | 주가 데이터 fetch, 캐싱, 병렬 처리 |
| **naver_price_fetcher.py** | 네이버 금융 래퍼 | 실시간 주가, 뉴스 크롤링 |
| **pykrx_wrapper.py** | KRX 데이터 래퍼 | 한국거래소 공식 데이터 (없음 - level1_pykrx.py 참조) |
| **level1_pykrx.py** | PyKRX 기반 데이터 수집 | 전종목 일봉, 분봉 데이터 수집 |
| **kstock_data.py** | 기본 데이터 모델 | Stock, Price 데이터 클래스 |
| **stock_repository.py** | DB 추상화 레이어 | CRUD operations, 캐싱 관리 |
| **local_db.py** | SQLite 관리 | Connection pool, 트랜잭션 관리 |
| **fundamental_collector.py** | 펀더멘탈 데이터 수집 | 재무제표, 지표 데이터 |

---

## 2️⃣ 전략 스캐너 (Strategy Scanners)

> **역할**: 각종 트레이딩 전략 구현 및 신호 탐지

### 🎯 메인 전략 스캐너

| 파일 | 전략명 | 설명 | 입장 조건 |
|------|--------|------|-----------|
| **integrated_multi_scanner.py** | 통합 멀티 전략 | V + NPS + B01 + Multi 통합 | 종합 점수 70점+ |
| **v_series_scanner.py** | V-Series | 가치 + 피볼나치 + ATR | Value 65+, Fib 38.2~50% |
| **nps_value_scanner.py** | NPS | Net Purchase Strength | 추세+모멘텀+거래량 점수 70+ |
| **b01_buffett_scanner.py** | B01 Buffett | 버핏 가치투자 | 장기추세+저변동성+수익률 65+ |
| **m10_scanner.py** | M10 | AI 예측 + 기술적 분석 | AI Primary 60%+, RSI 35~75 |
| **minervini_scanner.py** | SEPA/VCP | Mark Minervini 트렌드 | Trend Template 8가지 |
| **oneil_scanner.py** | O'Neil CANSLIM | William O'Neil 성장주 | EPS, RS, 수급 분석 |
| **livermore_scanner.py** | Livermore 포인트 | 전고점 돌파 | Box theory, Pivot point |
| **smc_fvg_trader.py** | SMC FVG | Smart Money Concept | Fair Value Gap, Order Block |
| **nb_strategy_scanner.py** | News-Based | 뉴스 기반 감성 분석 | AI 뉴스 분석 + 기술적 지표 |

### 📊 Pivot Point 전략 (strategy/ 폴터)

| 파일 | 설명 |
|------|------|
| **pivot_strategy.py** | 피봇 포인트 브레이크아웃 전략 메인 엔진 |
| **scan.py** | 일일 스캐너 (배치용) |
| **enhanced_scanner.py** | 개선된 스캐너 (ATR 기반 손익비) |
| **multi_stock_scanner.py** | 다종목 병렬 스캐너 |

### 🔗 조합 전략

| 파일 | 설명 |
|------|------|
| **double_signal_scanner.py** | 2개 전략 동시 충족 종목 |
| **triple_signal_scanner.py** | 3개 전략 동시 충족 종목 |
| **scanner_parallel.py** | 병렬 스캐닝 엔진 |

---

## 3️⃣ 실행/오케스트레이션 계층 (Execution & Orchestration)

> **역할**: 스케줄링, 배치 실행, 모니터링, 에이전트 관리

### ⏰ 스케줄러 & 크론

| 파일 | 설명 | 실행 주기 |
|------|------|-----------|
| **daily_update_batch.py** | **일일 DB 업데이트 배치** | 매일 19:00 KST |
| **full_db_update.py** | 전체 DB 재구축 | 수동 실행 |
| **monitor_update.py** | 업데이트 모니터링 | 백그라운드 |
| **kstock_cron_manager.py** | 크론 작업 관리 | - |
| **level1_cron_batch.py** | Level1 데이터 크론 배치 | 매일 |
| **level1_batch_auto.py** | 자동 배치 실행기 | - |

### 🤖 에이전트 오케스트레이션

| 파일 | 설명 |
|------|------|
| **agent_orchestrator.py** | 멀티 에이전트 조율기 |
| **agent_spawner.py** | 에이전트 생성 관리 |
| **kstock_multi_agent.py** | 멀티 에이전트 시스템 |
| **investment_agent_group.py** | 투자 결정 에이전트 그룹 |
| **level1_job_manager.py** | 작업 큐 관리자 |

### 🔄 파이프라인

| 파일 | 설명 |
|------|------|
| **kstock_pipeline.py** | 전체 데이터 파이프라인 |
| **fdr_batch_processor.py** | FDR 병렬 처리기 |
| **level1_hybrid.py** | 하이브리드 데이터 수집 |
| **level1_sequential.py** | 순차적 데이터 수집 |
| **update_all_stocks.py** | 전종목 업데이트 |

### 👀 모니터링 & 알림

| 파일 | 설명 |
|------|------|
| **watchdog.py** | 기본 왓치독 |
| **watchdog_hybrid.py** | 하이브리드 모니터링 |
| **daily_pick_monitor.py** | 일일 선정 종목 모니터링 |
| **kstock_voice_alert.py** | 음성 알림 시스템 |
| **send_telegram_notification.py** | 텔레그램 알림 |
| **auto_restart.py** | 자동 재시작 유틸리티 |
| **premarket_monitor.py** | 장전 모니터링 |

---

## 4️⃣ 리포트 생성 계층 (Report Generation)

> **역할**: 스캔 결과 시각화, HTML 리포트 생성, GitHub Pages 배포

### 📑 통합 리포트 생성기

| 파일 | 설명 | 출력 |
|------|------|------|
| **integrated_report_generator.py** | **통합 멀티 전략 리포트** | HTML + TradingView 차트 |
| **b01_nps_integrated_report.py** | B01 + NPS 통합 리포트 | HTML |
| **mv_integrated_report.py** | Minervini 통합 리포트 | HTML |
| **v_series_daily_report.py** | V-Series 일일 리포트 | HTML |
| **nb_strategy_report.py** | News-Based 리포트 | HTML |

### 📊 단일 전략 리포트

| 파일 | 설명 |
|------|------|
| **generate_report.py** | 기본 리포트 생성기 |
| **generate_enhanced_report.py** | 개선된 리포트 |
| **generate_level1_report.py** | Level1 데이터 리포트 |
| **generate_level2_report.py** | Level2 분석 리포트 |
| **generate_level3_report.py** | Level3 포트폴리오 리포트 |
| **generate_enhanced_level3_report.py** | 고급 Level3 리포트 |
| **combined_report_generator.py** | 조합 리포트 생성 |
| **combined_report_generator_v2.py** | 개선된 조합 리포트 |

### 📈 특화 리포트

| 파일 | 설명 |
|------|------|
| **report_livermore.py** | Livermore 전략 리포트 |
| **report_livermore_v2.py** | Livermore 리포트 v2 |
| **consolidated_report.py** | 통합 분석 리포트 |
| **generate_dashboard.py** | 대시보드 생성 |
| **dashboard.py** | 실시간 대시보드 서버 |
| **investigation_report.py** | 조사/분석 리포트 |

---

## 5️⃣ 데이터베이스 구축 계층 (Database Construction)

> **역할**: DB 스키마 설계, 초기 데이터 구축, 마이그레이션

### 🏗️ DB 빌더

| 파일 | 설명 | 대상 DB |
|------|------|---------|
| **build_daily_pivot_db.py** | 피봇 전략 DB 구축 | pivot_strategy.db |
| **build_daily_pivot_db_seq.py** | 순차적 DB 빌더 | pivot_strategy.db |
| **build_daily_simple.py** | 간단한 DB 구축 | - |
| **generate_sample_daily_pivot.py** | 샘플 데이터 생성 | - |

### 📥 데이터 임포터

| 파일 | 설명 |
|------|------|
| **import_kospi_stocks.py** | 코스피 종목 리스트 임포트 |
| **import_kosdaq_stocks.py** | 코스닥 종목 리스트 임포트 |
| **kospi_master_parser.py** | 코스피 마스터 데이터 파싱 |

### 🔄 업데이터

| 파일 | 설명 |
|------|------|
| **update_data.py** | 데이터 업데이트 |
| **update_db_latest.py** | 최신 데이터로 업데이트 |
| **update_db_quick.py** | 빠른 업데이트 |

---

## 6️⃣ DART/공시 데이터 계층

> **역할**: 금융감독원 DART API 연동, 공시 데이터 수집

| 파일 | 설명 |
|------|------|
| **dart_batch_collector.py** | DART 일괄 수집기 |
| **dart_2024_collector.py** | 2024년 공시 데이터 수집 |
| **test_dart_reader.py** | DART API 테스트 |
| **level2_news_collector.py** | 뉴스 데이터 수집 |
| **level2_news_mapper.py** | 뉴스-종목 매핑 |
| **naver_news_scraper.py** | 네이버 뉴스 크롤러 |

---

## 7️⃣ 백테스팅 및 분석 도구 (Backtesting & Analysis)

| 파일 | 설명 |
|------|------|
| **smc_fvg_backtest.py** | SMC FVG 전략 백테스트 |
| **smc_fvg_yahoo_backtest.py** | 야후 파이낸스 기반 백테스트 |
| **smc_fvg_visualizer.py** | SMC FVG 시각화 |
| **custom_stock_analysis.py** | 사용자 정의 분석 |
| **custom_stock_analysis_simple.py** | 간단한 분석 도구 |
| **strategy_research.py** | 전략 연구/개발 도구 |
| **analysis/technical.py** | 기술적 분석 모듈 |

---

## 8️⃣ 유틸리티 및 보조 도구 (Utilities)

| 파일 | 설명 |
|------|------|
| **kosdaq_scanner.py** | 코스닥 전용 스캐너 |
| **send_telegram_notification.py** | 알림 발송 |
| **kstock.sh** | 쉘 실행 스크립트 |
| **kosdaq.sh** | 코스닥 스캔 스크립트 |
| **minervini.sh** | Minervini 스캔 스크립트 |
| **oneil.sh** | O'Neil 스캔 스크립트 |
| **livermore.sh** | Livermore 스캔 스크립트 |
| **run_bg.sh** | 백그라운드 실행 스크립트 |

---

## 📊 데이터베이스 파일 목록

### 메인 DB

| 파일 | 설명 | 용량 |
|------|------|------|
| **pivot_strategy.db** | 메인 주가 데이터베이스 | ~50MB |
| **dart_cache.db** | DART 공시 데이터 캐시 | ~10MB |
| **dart_focused.db** | 핵심 DART 데이터 | ~5MB |

### Level DB

| 파일 | 설명 |
|------|------|
| **level1_prices.db** | Level1 가격 데이터 |
| **level1_consolidated.db** | 통합 Level1 데이터 |
| **level1_quarterly.db** | 분기별 Level1 데이터 |
| **level2_macro.db** | 거시경제 데이터 |
| **level3_portfolio.db** | 포트폴리오 데이터 |

### 작업 큐 DB

| 파일 | 설명 |
|------|------|
| **job_queue_pykrx.db** | PyKRX 작업 큐 |
| **level1_dbqueue.db** | Level1 작업 큐 |

---

## 🔧 주요 실행 흐름

### 일일 자동화 플로우

```
┌─────────────────┐     ┌──────────────────┐     ┌─────────────────┐
│  daily_update   │────▶│  integrated_multi │────▶│    integrated   │
│    _batch.py    │     │    _scanner.py     │     │ report_generator │
│  (19:00 KST)    │     │                    │     │                 │
└─────────────────┘     └──────────────────┘     └─────────────────┘
         │                       │                        │
         ▼                       ▼                        ▼
┌─────────────────┐     ┌──────────────────┐     ┌─────────────────┐
│  Update prices  │     │  Run strategies  │     │  Deploy to      │
│  to local DB    │     │  (V/NPS/B01/...) │     │  GitHub Pages   │
└─────────────────┘     └──────────────────┘     └─────────────────┘
```

### 수동 실행 플로우

```
┌─────────────────┐     ┌──────────────────┐     ┌─────────────────┐
│  full_db_update │────▶│     scanner      │────▶│  report_gen     │
│     .py         │     │   (specific)     │     │   (specific)    │
│  (Full rebuild) │     │                  │     │                 │
└─────────────────┘     └──────────────────┘     └─────────────────┘
```

---

## 📝 설정 파일

| 파일 | 설명 |
|------|------|
| **requirements.txt** | Python 의존성 |
| **.env** | 환경 변수 (API 키 등) |
| **.env.example** | 환경 변수 예시 |
| **agent_group_config.json** | 에이전트 그룹 설정 |
| **market_data_index.json** | 시장 데이터 인덱스 |
| **config/** | 설정 파일 디렉토리 |

---

## 🔗 GitHub Pages 배포

- **URL**: https://lubanana.github.io/kstock-dashboard/
- **소스**: `docs/` 디렉토리
- **자동화**: 리포트 생성 시 `docs/`에 복사 후 Git push

---

## ⚠️ 주의사항

1. **DB 파일 제외**: `*.db` 파일은 `.gitignore`에 포함 (용량 제한)
2. **API Rate Limit**: FDR/PyKRX는 0.1초 지연 필수
3. **크론 설정**: `crontab -e`로 확인/수정
4. **로그 확인**: `logs/` 또는 `*.log` 파일

---

## 🔄 최근 업데이트

| 날짜 | 변경 내용 | 커밋 |
|------|-----------|------|
| 2026-03-21 | 종목명 표시 개선, 손익비 계산 수정 | ff69771 |
| 2026-03-20 | 전체 종목 스캔 (3,299개) 기능 추가 | ad6d706 |
| 2026-03-20 | 일일 배치 업데이트 시스템 구축 | 9edcba7 |
| 2026-03-20 | B01 + NPS 스캐너 추가 | 7482316 |

---

*문서 작성: Kimi Claw*  
*마지막 업데이트: 2026-03-21*
