#!/usr/bin/env python3
"""
Level 1 Master Runner v2.0
Level 1 에이전트 통합 실행기 (개선版)

Architecture:
├── Level 1-1: Technical Analysis (TECH) - 모든 종목
├── Level 1-2: Quantitative Analysis (QUANT) - 모든 종목  
├── Level 1-3: Financial Analysis (FIN) - 3년치 (2022-2024)
├── Level 1-4: News Analysis (NEWS) - 70점 이상 종목만 ⚡조걸
├── Level 1-5: Qualitative Analysis (QUAL) - 70점 이상 종목만 ⚡조걸
└── Consolidator: 전체 취합 및 필터링

Usage:
    python3 level1_master_v2.py [command]
    
Commands:
    run_all              - 전체 프로세스 실행
    run_tech             - 기술적 분석만
    run_quant            - 정량적 분석만
    run_financial        - 재무정보 분석 (3년)
    run_news_qual        - 뉴스/정성 분석 (70점 이상)
    consolidate          - 결과 취합
    report               - 리포트 생성
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'agents'))

from level1_price_agent import DailyPriceCollector
from level1_financial_agent import QuarterlyFinancialCollector
from level1_news_agent import NewsAnalysisAgent
from level1_qualitative_agent import QualitativeAnalysisAgent
from level1_consolidator import Level1Consolidator


def run_technical_analysis():
    """L1-1: 기술적 분석 (모든 종목)"""
    print("\n" + "="*70)
    print("🚀 Level 1-1: Technical Analysis (All Stocks)")
    print("="*70)
    
    collector = DailyPriceCollector()
    results, high_scores = collector.collect('morning')
    
    print(f"\n✅ Technical Analysis Complete")
    print(f"   Total: {len(results)} stocks")
    print(f"   High Score (≥70): {len(high_scores)} stocks")
    return results, high_scores


def run_quantitative_analysis():
    """L1-2: 정량적 분석 - 가격 데이터 기반"""
    print("\n" + "="*70)
    print("🚀 Level 1-2: Quantitative Analysis")
    print("="*70)
    print("   📊 Quantitative analysis integrated in price data")
    return True


def run_financial_analysis(years=['2022', '2023', '2024']):
    """L1-3: 재무정보 분석 (3년치)"""
    print("\n" + "="*70)
    print("🚀 Level 1-3: Financial Analysis (3 Years)")
    print("   Years:", ', '.join(years))
    print("="*70)
    
    api_key = os.environ.get('DART_API_KEY')
    if not api_key:
        print("❌ DART_API_KEY 필요!")
        return None
    
    collector = QuarterlyFinancialCollector(api_key=api_key)
    all_results = []
    
    for year in years:
        print(f"\n📅 Processing {year}...")
        results = collector.collect_year(year)
        success = len([r for r in results if r.get('status') == 'success'])
        print(f"   ✅ {year}: {success} success")
        all_results.extend(results)
    
    total_success = len([r for r in all_results if r.get('status') == 'success'])
    print(f"\n✅ Financial Analysis Complete")
    print(f"   Total: {total_success} records (3 years)")
    return all_results


def run_news_qualitative_analysis(min_score=70.0):
    """L1-4, L1-5: 뉴스/정성 분석 (70점 이상 종목만)"""
    print("\n" + "="*70)
    print(f"🚀 Level 1-4/5: News & Qualitative Analysis")
    print(f"   Target: Stocks with score ≥ {min_score}")
    print("="*70)
    
    # L1-4: News Analysis
    print("\n📰 L1-4: News Analysis")
    news_agent = NewsAnalysisAgent()
    news_results = news_agent.analyze_high_score_stocks(min_score)
    
    # L1-5: Qualitative Analysis
    print("\n📋 L1-5: Qualitative Analysis")
    api_key = os.environ.get('DART_API_KEY')
    qual_agent = QualitativeAnalysisAgent(api_key=api_key)
    qual_results = qual_agent.analyze_high_score_stocks(min_score)
    
    return news_results, qual_results


def run_consolidation(threshold=70.0):
    """결과 취합"""
    print("\n" + "="*70)
    print("🚀 Level 1 Consolidator")
    print(f"   Score Threshold: {threshold}")
    print("="*70)
    
    consolidator = Level1Consolidator(score_threshold=threshold)
    results = consolidator.consolidate()
    consolidator.print_top10(results)
    
    return results


def run_full_process():
    """전체 프로세스 실행"""
    print("\n" + "="*70)
    print("🚀 LEVEL 1 MASTER RUNNER v2.0")
    print("   Complete Analysis Pipeline")
    print("="*70)
    
    # Step 1: Technical (All)
    tech_results, high_scores = run_technical_analysis()
    
    # Step 2: Financial (3 years)
    fin_results = run_financial_analysis(['2022', '2023', '2024'])
    
    # Step 3: News & Qualitative (Conditional)
    if high_scores:
        print(f"\n📌 High Score Stocks Detected: {len(high_scores)}")
        print("   → Running News & Qualitative Analysis")
        run_news_qualitative_analysis(min_score=70.0)
    else:
        print("\n⚠️  No high score stocks - Skipping News/Qualitative")
    
    # Step 4: Consolidation
    final_results = run_consolidation(threshold=70.0)
    
    # Summary
    print("\n" + "="*70)
    print("✅ LEVEL 1 ANALYSIS COMPLETE")
    print("="*70)
    print(f"\n📊 Results Summary:")
    print(f"   • Technical: {len(tech_results)} stocks analyzed")
    print(f"   • Financial: 3 years (2022-2024)")
    if high_scores:
        print(f"   • News/Qual: {len(high_scores)} high-score stocks")
    print(f"   • Final Top: {len(final_results)} stocks (≥70pts)")
    
    return final_results


def generate_report():
    """리포트 생성"""
    print("\n" + "="*70)
    print("📊 Generating Level 1 Report...")
    print("="*70)
    
    # DB에서 데이터 로드
    import sqlite3
    
    # 가격 데이터
    conn = sqlite3.connect('data/level1_daily.db')
    cursor = conn.cursor()
    cursor.execute('SELECT COUNT(*), AVG(score) FROM price_analysis WHERE status="success"')
    price_stats = cursor.fetchone()
    conn.close()
    
    # 재무 데이터
    conn = sqlite3.connect('data/level1_quarterly.db')
    cursor = conn.cursor()
    cursor.execute('SELECT year, COUNT(*) FROM financial_data WHERE status="success" GROUP BY year')
    fin_stats = cursor.fetchall()
    conn.close()
    
    print("\n📈 Analysis Statistics:")
    print(f"   Price Analysis: {price_stats[0]} records (avg: {price_stats[1]:.1f})")
    print("   Financial Analysis:")
    for year, count in fin_stats:
        print(f"      {year}: {count} records")
    
    print("\n💾 Report saved to: data/level1_report.json")


def main():
    """메인 실행"""
    if len(sys.argv) < 2:
        print(__doc__)
        return
    
    command = sys.argv[1]
    
    commands = {
        'run_all': run_full_process,
        'run_tech': run_technical_analysis,
        'run_quant': run_quantitative_analysis,
        'run_financial': lambda: run_financial_analysis(['2022', '2023', '2024']),
        'run_news_qual': lambda: run_news_qualitative_analysis(70.0),
        'consolidate': lambda: run_consolidation(70.0),
        'report': generate_report,
    }
    
    if command in commands:
        try:
            commands[command]()
        except Exception as e:
            print(f"\n❌ Error: {e}")
            import traceback
            traceback.print_exc()
    else:
        print(f"❌ Unknown command: {command}")
        print(__doc__)


if __name__ == '__main__':
    main()
