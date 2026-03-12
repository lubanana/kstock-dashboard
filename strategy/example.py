#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Quick Start Example
===================
pivot_strategy.py + pivot_report.py 통합 사용 예시
"""

from pivot_strategy import PivotPointStrategy
from pivot_report import StrategyReport, StrategyVisualizer
from multi_stock_scanner import MultiStockScanner
import os


def example_single_stock():
    """
    예시 1: 단일 종목 백테스트 + 보고서 생성
    """
    print("=" * 60)
    print("예시 1: 삼성전자(005930) 백테스트")
    print("=" * 60)
    
    # 전략 설정
    strategy = PivotPointStrategy(
        symbol='005930',              # 삼성전자
        start_date='2024-01-01',
        end_date='2024-12-31',
        initial_capital=10_000_000,   # 1000만원
        pivot_period=20,              # 20일 신고가
        volume_threshold=1.5,         # 거래량 150%
        stop_loss_pct=0.10,           # 손절 -10%
        trailing_stop_pct=0.15,       # 익절 -15%
    )
    
    # 백테스트 실행
    result, trades_df = strategy.run_backtest()
    
    # 보고서 생성
    report = StrategyReport(output_dir='./reports')
    report_path = report.generate_report(strategy, result, trades_df)
    
    # 차트도 함께 생성됨
    print(f"\n📁 생성된 파일:")
    print(f"   - {report_path}")
    
    return strategy, result, trades_df


def example_multi_scan():
    """
    예시 2: 전 종목 스캔
    """
    print("\n" + "=" * 60)
    print("예시 2: KOSPI/KOSDAQ 전 종목 스캔")
    print("=" * 60)
    
    scanner = MultiStockScanner(
        pivot_period=20,
        volume_threshold=1.5,
        min_price=1000,
        min_volume=100000,
        max_stocks=50,  # 테스트용: 50개만 스캔
    )
    
    results = scanner.scan_all(max_workers=4)
    
    if not results.empty:
        scanner.save_results(results)
        
        print("\n🏆 TOP 5 픽:")
        top5 = scanner.get_top_picks(results, 5)
        print(top5.to_string(index=False))
    
    return results


def example_custom_params():
    """
    예시 3: 커스텀 파라미터 백테스트
    """
    print("\n" + "=" * 60)
    print("예시 3: 60일 피벗 + 공격적 피라미딩")
    print("=" * 60)
    
    strategy = PivotPointStrategy(
        symbol='035420',              # NAVER
        start_date='2024-01-01',
        end_date='2024-12-31',
        initial_capital=10_000_000,
        pivot_period=60,              # 60일 신고가 (더 강한 신호)
        volume_threshold=2.0,         # 거래량 200%
        pyramiding_pct_1=0.50,        # 1차: 50%
        pyramiding_pct_2=0.30,        # 2차: 30%
        pyramiding_pct_3=0.20,        # 3차: 20%
        stop_loss_pct=0.08,           # 손절 -8% (더 타이트하게)
        trailing_stop_pct=0.12,       # 익절 -12%
    )
    
    result, trades_df = strategy.run_backtest()
    
    return strategy, result, trades_df


def example_visualization_only():
    """
    예시 4: 시각화만 수행
    """
    print("\n" + "=" * 60)
    print("예시 4: 시각화 데모")
    print("=" * 60)
    
    # 먼저 백테스트 실행
    strategy = PivotPointStrategy(
        symbol='005930',
        start_date='2024-06-01',
        end_date='2024-12-31',
        initial_capital=10_000_000,
        pivot_period=20,
        volume_threshold=1.5,
    )
    
    result, _ = strategy.run_backtest()
    
    # 시각화
    viz = StrategyVisualizer()
    
    # Matplotlib 차트
    print("\n📊 Matplotlib 차트 생성 중...")
    fig = viz.plot_trades_matplotlib(
        strategy, result, 
        save_path='./reports/example_chart.png'
    )
    
    # Plotly 차트
    print("📊 Plotly 인터랙티브 차트 생성 중...")
    plotly_fig = viz.plot_trades_plotly(
        strategy, result,
        save_path='./reports/example_interactive.html'
    )
    
    print("\n✅ 차트 생성 완료!")
    print("   - ./reports/example_chart.png")
    print("   - ./reports/example_interactive.html")


if __name__ == "__main__":
    # reports 디렉토리 생성
    os.makedirs('./reports', exist_ok=True)
    
    print("🚀 Pivot Point Strategy Quick Start Examples\n")
    
    # 예시 실행 (원하는 예시의 주석을 해제하세요)
    
    # 예시 1: 단일 종목 백테스트
    example_single_stock()
    
    # 예시 2: 전 종목 스캔 (시간이 오래 걸림)
    # example_multi_scan()
    
    # 예시 3: 커스텀 파라미터
    # example_custom_params()
    
    # 예시 4: 시각화만
    # example_visualization_only()
    
    print("\n" + "=" * 60)
    print("모든 예시가 완료되었습니다!")
    print("reports/ 디렉토리에서 결과를 확인하세요.")
    print("=" * 60)
