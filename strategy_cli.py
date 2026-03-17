#!/usr/bin/env python3
"""
K-Stock Strategy CLI
전략 코드로 빠르게 실행하는 명령줄 도구

Examples:
    # 전략 목록 보기
    python strategy_cli.py list
    
    # 특정 전략 정보
    python strategy_cli.py info M03
    
    # 전략 실행
    python strategy_cli.py run M03
    
    # 여러 전략 순차 실행
    python strategy_cli.py sequential M01,M02,M03
    
    # 최고 조합 보기
    python strategy_cli.py best
"""

import argparse
import sys
from strategy_catalog import (
    list_strategies, get_strategy_info, run_strategy, 
    run_sequential, get_best_combinations, print_strategy_table
)


def cmd_list(args):
    """전략 목록 출력"""
    if args.category:
        strategies = list_strategies(category=args.category)
        print(f"\n📁 {args.category} 전략 목록")
        print("-" * 60)
    else:
        strategies = list_strategies()
        print_strategy_table()
        return
    
    for s in strategies:
        print(f"  {s['code']:4} | {s['name']:30} | {s['type']}")
    print(f"\n총 {len(strategies)}개 전략")


def cmd_info(args):
    """전략 정보 출력"""
    try:
        info = get_strategy_info(args.code)
        print(f"\n📊 [{args.code}] {info['name']}")
        print("=" * 60)
        print(f"설명: {info['description']}")
        print(f"카테고리: {info['category']}")
        print(f"타입: {info['type']}")
        print(f"파일: {info['file']}")
        print(f"\n기준:")
        for i, c in enumerate(info['criteria'], 1):
            print(f"  {i}. {c}")
        
        if 'params' in info:
            print(f"\n파라미터:")
            for k, v in info['params'].items():
                print(f"  {k}: {v}")
        
        if 'backtest_result' in info:
            print(f"\n📈 백테스트 결과:")
            for k, v in info['backtest_result'].items():
                print(f"  {k}: {v}")
        
        if 'note' in info:
            print(f"\n💡 참고: {info['note']}")
            
    except ValueError as e:
        print(f"❌ 오류: {e}")
        sys.exit(1)


def cmd_run(args):
    """전략 실행"""
    result = run_strategy(args.code)
    print(f"\n✅ 실행 결과:")
    print(f"  코드: {result['code']}")
    print(f"  이름: {result['name']}")
    print(f"  상태: {result['status']}")
    print(f"  시간: {result['timestamp']}")
    
    if 'backtest' in result:
        print(f"\n📊 백테스트:")
        for k, v in result['backtest'].items():
            print(f"  {k}: {v}")


def cmd_sequential(args):
    """순차 실행"""
    codes = args.codes.split(',')
    results = run_sequential(codes, delay=args.delay)
    
    print(f"\n📊 실행 요약:")
    print("-" * 60)
    for r in results:
        print(f"  {r['code']:4} | {r['name']:25} | {r['status']}")


def cmd_best(args):
    """최고 조합 출력"""
    combos = get_best_combinations()
    print("\n🏆 추천 전략 조합")
    print("=" * 60)
    
    for i, combo in enumerate(combos, 1):
        print(f"\n{i}. {combo['name']}")
        print(f"   전략: {', '.join(combo['codes'])}")
        print(f"   승률: {combo['win_rate']*100:.1f}%")
        print(f"   수익: {combo['profit']*100:.1f}%")
        print(f"   설명: {combo['description']}")


def cmd_report(args):
    """리포트 경로 출력"""
    reports = {
        'B01': 'buy_strength_report.html',
        'M10': 'multi_strategy_report.html',
        'M11': 'multi_strategy_backtest_report.html',
        'V01': 'buffett_graham_detailed_report.html',
        'V10': 'buffett_comprehensive_report_20260317_0607.html',
    }
    
    print("\n📄 전략별 리포트 URL")
    print("=" * 60)
    print("https://lubanana.github.io/kstock-dashboard/")
    print("-" * 60)
    
    for code, filename in reports.items():
        info = get_strategy_info(code)
        print(f"{code:4} | {info['name']:25} | {filename}")


def main():
    parser = argparse.ArgumentParser(
        description='K-Stock Strategy CLI - 전략 코드로 빠르게 실행',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog='''
전략 코드 목록:
  P01     : 피벗 포인트 돌파
  B01     : Buy Strength A등급
  B02     : Buy Strength 월간
  S01-S03 : SEPA/VCP 전략
  M01-M05 : 멀티전략 개별
  M10     : 멀티전략 종합
  M11     : 멀티전략 백테스트
  V01-V03 : 버핏 3전략 개별
  V10     : 버핏 3전략 종합
  V11     : 버핏 백테스트

예시:
  python strategy_cli.py list
  python strategy_cli.py info M03
  python strategy_cli.py run M03
  python strategy_cli.py sequential M01,M02,M03
  python strategy_cli.py best
        '''
    )
    
    subparsers = parser.add_subparsers(dest='command', help='명령어')
    
    # list
    list_parser = subparsers.add_parser('list', help='전략 목록 보기')
    list_parser.add_argument('--category', '-c', help='카테고리 필터')
    list_parser.set_defaults(func=cmd_list)
    
    # info
    info_parser = subparsers.add_parser('info', help='전략 정보 보기')
    info_parser.add_argument('code', help='전략 코드 (예: M03)')
    info_parser.set_defaults(func=cmd_info)
    
    # run
    run_parser = subparsers.add_parser('run', help='전략 실행')
    run_parser.add_argument('code', help='전략 코드 (예: M03)')
    run_parser.set_defaults(func=cmd_run)
    
    # sequential
    seq_parser = subparsers.add_parser('sequential', help='여러 전략 순차 실행')
    seq_parser.add_argument('codes', help='전략 코드 (콤마 구분, 예: M01,M02,M03)')
    seq_parser.add_argument('--delay', '-d', type=int, default=1, help='전략 간 딜레이(초)')
    seq_parser.set_defaults(func=cmd_sequential)
    
    # best
    best_parser = subparsers.add_parser('best', help='최고 조합 보기')
    best_parser.set_defaults(func=cmd_best)
    
    # report
    report_parser = subparsers.add_parser('report', help='리포트 경로 보기')
    report_parser.set_defaults(func=cmd_report)
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        sys.exit(0)
    
    args.func(args)


if __name__ == '__main__':
    main()
