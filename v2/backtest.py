#!/usr/bin/env python3
"""
V2 Backtest CLI
백테스팅 명령행 도구
"""
import sys
import argparse
import json
from pathlib import Path
from datetime import datetime, timedelta

# Set up paths
v2_dir = Path(__file__).parent
core_dir = v2_dir / 'core'
strategies_dir = v2_dir / 'strategies'

sys.path.insert(0, str(v2_dir))
sys.path.insert(0, str(core_dir))
sys.path.insert(0, str(strategies_dir))

from data_manager import DataManager
from backtest_engine import BacktestEngine
from explosive import ExplosiveV7Strategy
from dplus import DPlusStrategy


def main():
    parser = argparse.ArgumentParser(description='V2 Backtest Tool')
    parser.add_argument('--strategy', type=str, required=True,
                       help='백테스트할 전략 (explosive, dplus)')
    parser.add_argument('--start', type=str, required=True,
                       help='시작일 (YYYY-MM-DD)')
    parser.add_argument('--end', type=str, required=True,
                       help='종료일 (YYYY-MM-DD)')
    parser.add_argument('--stop-loss', type=float, default=-0.07,
                       help='손절률 (기본: -7%%)')
    parser.add_argument('--take-profit', type=float, default=0.25,
                       help='익절률 (기본: +25%%)')
    parser.add_argument('--max-hold', type=int, default=7,
                       help='최대 보유일 (기본: 7일)')
    parser.add_argument('--codes', type=str, default=None,
                       help='테스트할 종목 (쉼표 구분, 미지정시 전체)')
    parser.add_argument('--json', type=str, default=None,
                       help='결과 저장 JSON 경로')
    
    args = parser.parse_args()
    
    # Validate dates
    try:
        datetime.strptime(args.start, '%Y-%m-%d')
        datetime.strptime(args.end, '%Y-%m-%d')
    except ValueError:
        print("❌ 잘못된 날짜 형식. YYYY-MM-DD 형식을 사용하세요.")
        sys.exit(1)
    
    print("=" * 70)
    print("📊 V2 Backtest Engine")
    print("=" * 70)
    print(f"🎯 전략: {args.strategy}")
    print(f"📅 기간: {args.start} ~ {args.end}")
    print(f"🛡️  손절: {args.stop_loss:.1%} | 🎯 익절: {args.take_profit:.1%}")
    print("-" * 70)
    
    # Initialize
    data_manager = DataManager()
    
    # Create strategy
    strategy_map = {
        'explosive': ExplosiveV7Strategy,
        'dplus': DPlusStrategy
    }
    
    if args.strategy not in strategy_map:
        print(f"❌ 알 수 없는 전략: {args.strategy}")
        print(f"   사용 가능: {', '.join(strategy_map.keys())}")
        sys.exit(1)
    
    strategy = strategy_map[args.strategy]()
    
    # Parse codes
    codes = None
    if args.codes:
        codes = [c.strip() for c in args.codes.split(',')]
        print(f"📈 대상 종목: {len(codes)}개 (지정됨)")
    else:
        # 전체 종목 로드
        codes = data_manager.get_all_codes(args.end)
        print(f"📈 대상 종목: {len(codes)}개 (전체)")
    
    # Create backtest engine
    engine = BacktestEngine(
        data_manager=data_manager,
        stop_loss=args.stop_loss,
        take_profit=args.take_profit,
        max_holding_days=args.max_hold
    )
    
    # Run backtest
    print("\n🔍 백테스트 실행 중...")
    result = engine.run(strategy, args.start, args.end, codes)
    
    # Print results
    print(engine.generate_report(result))
    
    # Save JSON if requested
    if args.json:
        json_data = {
            'strategy': result.strategy_name,
            'period': {'start': result.start_date, 'end': result.end_date},
            'metrics': {
                'total_trades': result.total_trades,
                'win_rate': result.win_rate,
                'total_return': result.total_return,
                'avg_return': result.avg_return,
                'max_drawdown': result.max_drawdown,
                'sharpe_ratio': result.sharpe_ratio,
                'profit_factor': result.profit_factor
            },
            'trades': [
                {
                    'entry': t.entry_date,
                    'exit': t.exit_date,
                    'code': t.code,
                    'pnl_pct': t.pnl_pct,
                    'reason': t.exit_reason
                }
                for t in result.trades
            ]
        }
        
        json_path = Path(args.json)
        json_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(json_path, 'w', encoding='utf-8') as f:
            json.dump(json_data, f, ensure_ascii=False, indent=2)
        
        print(f"\n💾 결과 저장: {json_path}")
    
    print("=" * 70)


if __name__ == '__main__':
    main()
