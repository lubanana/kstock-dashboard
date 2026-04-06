#!/usr/bin/env python3
"""
V2 Unified Scanner
통합 스캐너 - 모든 전략을 일관된 인터페이스로 실행

사용법:
    python scanner.py --date 2026-04-03 --strategy all
    python scanner.py --date 2026-04-03 --strategy explosive,dplus
    python scanner.py --date 2026-04-03 --strategy explosive --min-score 80
"""
import argparse
import json
import sys
from datetime import datetime
from pathlib import Path

# Add paths for imports
v2_dir = Path(__file__).parent
core_dir = v2_dir / 'core'
strategies_dir = v2_dir / 'strategies'

sys.path.insert(0, str(v2_dir))
sys.path.insert(0, str(core_dir))
sys.path.insert(0, str(strategies_dir))

from data_manager import DataManager
from report_engine import ReportEngine
from explosive import ExplosiveV7Strategy
from dplus import DPlusStrategy
from ivf import IVFScanner


def main():
    parser = argparse.ArgumentParser(description='V2 Unified Stock Scanner')
    parser.add_argument('--date', type=str, required=True, 
                       help='분석 기준일 (YYYY-MM-DD)')
    parser.add_argument('--strategy', type=str, default='all',
                       help='실행할 전략 (all, explosive, dplus, comma-separated)')
    parser.add_argument('--min-score', type=float, default=None,
                       help='최소 점수 필터')
    parser.add_argument('--output', type=str, default='docs/v2_report.html',
                       help='출력 HTML 파일 경로')
    parser.add_argument('--json', type=str, default=None,
                       help='JSON 결과 저장 경로 (optional)')
    
    args = parser.parse_args()
    
    # Validate date
    try:
        datetime.strptime(args.date, '%Y-%m-%d')
    except ValueError:
        print(f"❌ 잘못된 날짜 형식: {args.date}")
        print("   올바른 형식: YYYY-MM-DD (예: 2026-04-03)")
        sys.exit(1)
    
    print("="*60)
    print("📊 V2 Unified Scanner")
    print("="*60)
    print(f"📅 분석 기준일: {args.date}")
    print(f"🎯 전략: {args.strategy}")
    print("-"*60)
    
    # Initialize data manager
    data_manager = DataManager()
    
    # Load available codes
    codes = data_manager.get_all_codes(args.date)
    print(f"📈 대상 종목: {len(codes)}개")
    
    # Parse strategies
    strategy_map = {
        'explosive': ExplosiveV7Strategy,
        'dplus': DPlusStrategy,
        'ivf': IVFScanner,
    }
    
    if args.strategy == 'all':
        strategies_to_run = list(strategy_map.keys())
    else:
        strategies_to_run = [s.strip() for s in args.strategy.split(',')]
    
    # Run strategies
    results = []
    total_signals = 0
    
    for strat_name in strategies_to_run:
        if strat_name not in strategy_map:
            print(f"⚠️ 알 수 없는 전략: {strat_name}")
            continue
        
        print(f"\n🔄 {strat_name} 전략 실행 중...")
        
        # Create strategy instance
        strategy = strategy_map[strat_name]()
        
        # Special handling for D+ (needs market data)
        if strat_name == 'dplus':
            market_data = data_manager.load_all_stocks(args.date)
            strategy.set_market_data(market_data)
        
        # Run strategy
        signals = strategy.run(data_manager, args.date)
        
        # Filter by score
        if args.min_score:
            signals = [s for s in signals if s.score >= args.min_score]
        
        # Sort by score
        signals = sorted(signals, key=lambda x: x.score, reverse=True)
        
        stats = strategy.get_stats()
        
        print(f"   ✅ 신호: {len(signals)}개")
        print(f"   📊 평균 점수: {stats['avg_score']:.1f}")
        print(f"   🔥 최고 점수: {stats['max_score']:.1f}")
        
        results.append({
            'name': strategy.config.name,
            'signals': signals,
            'stats': stats
        })
        
        total_signals += len(signals)
    
    # Generate summary stats
    summary = {
        'date': args.date,
        'total_stocks': len(codes),
        'total_signals': total_signals,
        'buy_signals': sum(r['stats']['buy_signals'] for r in results),
        'avg_score': sum(r['stats']['avg_score'] for r in results) / len(results) if results else 0
    }
    
    # Generate report
    print(f"\n📄 리포트 생성 중...")
    report_engine = ReportEngine("V2 통합 스캔 리포트")
    html = report_engine.generate(results, args.date, summary)
    
    # Save HTML
    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(html)
    
    print(f"   ✅ HTML 저장: {output_path}")
    
    # Save JSON if requested
    if args.json:
        json_data = {
            'date': args.date,
            'summary': summary,
            'strategies': [
                {
                    'name': r['name'],
                    'stats': r['stats'],
                    'signals': [s.to_dict() for s in r['signals']]
                }
                for r in results
            ]
        }
        
        json_path = Path(args.json)
        json_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(json_path, 'w', encoding='utf-8') as f:
            json.dump(json_data, f, ensure_ascii=False, indent=2)
        
        print(f"   ✅ JSON 저장: {json_path}")
    
    print("\n" + "="*60)
    print("✅ 스캔 완료!")
    print("="*60)
    print(f"총 {total_signals}개 신호 발견")
    print(f"리포트: {output_path}")


if __name__ == '__main__':
    main()
