#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
SEPA + VCP Strategy - Usage Examples
====================================
Mark Minervini SEPA 전략과 VCP 패턴 사용 예시

필요한 조건:
1. Trend Template (트렌드 템플릿)
2. VCP (Volatility Contraction Pattern)
3. Volume Dry-up (거래량 급감)
4. Relative Strength (상대강도 상위 25%)
5. Pivot Breakout (피벗 돌파 + 거래량 급증)
"""

import pandas as pd
from sepa_vcp_strategy import SEPA_VCP_Strategy, SEPASignal
from sepa_vcp_visualizer import SEPA_VCP_Visualizer
from sepa_vcp_scanner import SEPAVCPScanner
from fdr_wrapper import FDRWrapper


def example_single_stock():
    """예시 1: 단일 종목 분석"""
    print("\n" + "="*60)
    print("예시 1: 단일 종목 SEPA + VCP 분석")
    print("="*60)
    
    # 데이터 로드
    fdr = FDRWrapper('./data/pivot_strategy.db')
    df = fdr.get_price('005930', days=300)  # 삼성전자
    
    if df is not None:
        df.columns = [c.lower() for c in df.columns]
        df.reset_index(inplace=True)
        if 'index' in df.columns:
            df.rename(columns={'index': 'date'}, inplace=True)
        
        # 전략 분석
        strategy = SEPA_VCP_Strategy()
        signal = strategy.analyze_symbol('005930', df)
        
        if signal:
            # 텍스트 리포트 출력
            visualizer = SEPA_VCP_Visualizer()
            print(visualizer.generate_signal_report(signal))
            
            # 차트 생성
            visualizer.plot_matplotlib(df, signal, './reports/sepa_005930.png')
            visualizer.plot_plotly(df, signal, './reports/sepa_005930.html')
        else:
            print("❌ 신호가 감지되지 않았습니다.")


def example_multiple_stocks():
    """예시 2: 다중 종목 스캔"""
    print("\n" + "="*60)
    print("예시 2: 다중 종목 SEPA + VCP 스캔")
    print("="*60)
    
    scanner = SEPAVCPScanner(
        db_path='./data/pivot_strategy.db',
        output_dir='./reports/sepa',
        max_workers=4
    )
    
    # 상위 100개 종목만 스캔 (테스트용)
    results, valid_signals = scanner.scan_all(market='KOSPI', limit=100, min_score=50)
    
    if not results.empty:
        print(f"\n✅ {len(results)}개 종목에서 신호 감지!")
        print("\n📊 TOP 10:")
        print(results.head(10)[['symbol', 'name', 'close', 'score', 'vcp_passed', 'volume_surge']].to_string(index=False))
        
        # 결과 저장
        scanner.save_results(results)
        
        # 상위 5개 차트 생성
        scanner.generate_charts(valid_signals, top_n=5)
    else:
        print("⚠️ 신호가 감지된 종목이 없습니다.")


def example_custom_parameters():
    """예시 3: 사용자 정의 파라미터"""
    print("\n" + "="*60)
    print("예시 3: 사용자 정의 파라미터 설정")
    print("="*60)
    
    # 더 엄격한 조건 설정
    strict_strategy = SEPA_VCP_Strategy(
        contraction_min_count=3,      # 최소 3번의 수축
        contraction_max_count=4,      # 최대 4번
        max_contraction_depth=0.20,   # 최대 20% 수축 (더 엄격)
        min_volume_dry_up=0.5,        # 50% 이하 거래량 급감
        min_volume_surge=2.0,         # 2배 이상 거래량 급증
        pivot_proximity=0.02          # 피벗 2% 이내
    )
    
    # 느슨한 조건 설정
    loose_strategy = SEPA_VCP_Strategy(
        contraction_min_count=2,
        max_contraction_depth=0.30,   # 30%까지 허용
        min_volume_dry_up=0.7,        # 70% 이하
        min_volume_surge=1.3,         # 1.3배 이상
        pivot_proximity=0.05          # 피벗 5% 이내
    )
    
    print("\n엄격한 전략 설정:")
    print(f"  - 최소 수축 횟수: {strict_strategy.contraction_min_count}")
    print(f"  - 최대 수축 깊이: {strict_strategy.max_contraction_depth*100:.0f}%")
    print(f"  - 거래량 급감 기준: {strict_strategy.min_volume_dry_up*100:.0f}%")
    print(f"  - 거래량 급증 기준: {strict_strategy.min_volume_surge:.1f}배")


def example_vcp_identification():
    """예시 4: VCP 수축 패턴 식별 과정 설명"""
    print("\n" + "="*60)
    print("예시 4: VCP 수축 패턴 식별 과정")
    print("="*60)
    
    strategy = SEPA_VCP_Strategy()
    
    # 샘플 데이터로 설명
    print("""
📊 VCP (Volatility Contraction Pattern) 식별 과정:

1. 스윙 고점(Swing High) 식별
   - 최근 6개월 데이터에서 스윙 고점들을 찾음
   - 고점 사이의 구간을 수축 구간으로 간주

2. 수축 구간 분석
   ┌─────────────────────────────────────────┐
   │  Contraction 1: 20% 깊이, 4주 기간     │
   │     ↓                                   │
   │  Contraction 2: 12% 깊이, 3주 기간     │
   │     ↓                                   │
   │  Contraction 3:  8% 깊이, 2주 기간     │
   │     ↓                                   │
   │  [피벗 라인] - 마지막 수축 고점        │
   └─────────────────────────────────────────┘

3. 유효성 체크
   ✓ 깊이가 좁아지는가? (20% → 12% → 8%)
   ✓ 기간이 짧아지는가? (4주 → 3주 → 2주)
   ✓ 수축 최후반 거래량 급감 (Volume Dry-up)

4. 진입 신호
   ✓ 피벗 라인 돌파
   ✓ 거래량 50% 이상 급증 (20일 평균 대비)
   ✓ 상대강도 상위 25%
    """)


def example_trend_template():
    """예시 5: Trend Template 상세 설명"""
    print("\n" + "="*60)
    print("예시 5: Minervini Trend Template")
    print("="*60)
    
    print("""
📈 Mark Minervini's Trend Template (8가지 조건):

필수 조건:
┌────────────────────────────────────────────────────────┐
│ 1. 주가 > 150일 이동평균선                             │
│    현재가 > MA150                                     │
│                                                        │
│ 2. 주가 > 200일 이동평균선                             │
│    현재가 > MA200                                     │
│                                                        │
│ 3. 150일선 > 200일선                                   │
│    MA150 > MA200                                      │
│                                                        │
│ 4. 200일선 상승 추세                                   │
│    MA200 > 1개월 전 MA200                            │
│                                                        │
│ 5. 주가 > 52주 최저가 대비 30% 이상                   │
│    (현재가 - 52주저가) / 52주저가 > 30%              │
│                                                        │
│ 6. 주가 > 52주 최고가 대비 25% 이내                   │
│    (현재가 - 52주고가) / 52주고가 > -25%             │
│                                                        │
│ 7. 상대강도 순위 상위 25%                              │
│    1년 수익률 기준 상위 25%                           │
│                                                        │
│ 8. 주가 상승 추세                                       │
│    주가가 주요 이동평균선 위에서 정배열               │
└────────────────────────────────────────────────────────┘

모든 조건 충족 시 = "Trend Template Passed"
    """)


if __name__ == "__main__":
    print("🔥 SEPA + VCP Strategy Examples")
    print("Mark Minervini's Trading Strategy")
    
    # 예시 실행
    example_trend_template()
    example_vcp_identification()
    example_custom_parameters()
    
    # 실제 분석 실행 (선택적)
    # example_single_stock()
    # example_multiple_stocks()
    
    print("\n" + "="*60)
    print("예시 실행 완료!")
    print("="*60)
    print("\n실제 종목 분석을 실행하려면:")
    print("  example_single_stock()  # 단일 종목")
    print("  example_multiple_stocks()  # 다중 종목")
