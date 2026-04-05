#!/usr/bin/env python3
"""
개선안 7 플러스 최적화 전략
최종 권장: 시나리오8_복합235
성과: 수익률 +24.65%, 승률 53.7%, MDD 6.39%, 샤프 1.25
"""

class OptimizedStrategy:
    # 진입 조건
    ENTRY_SCORE_MIN = 85
    RSI_MIN, RSI_MAX = 40, 70
    MA_ALIGNMENT_REQUIRED = True
    MARKET_REGIME_FILTER = True
    
    # 추가 필터
    REQUIRE_CONSECUTIVE_UP = False  # 3일 연속 양봉
    SECTOR_UNIQUE = False  # 섹터 중복 금지
    FOREIGN_DAYS = 3  # 외국인 순매수 일수
    
    # 리스크 관리
    STOP_LOSS = -7.0
    TAKE_PROFIT = 25.0
    TRAILING_STOP = 10.0
    MAX_HOLD_DAYS = 90
    EARLY_EXIT_ENABLED = False
    EARLY_EXIT_DAYS = 14 if False else None
    EARLY_EXIT_LOSS = -3.0 if False else None
    
    # 포트폴리오
    MAX_POSITIONS = 10
