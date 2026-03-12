#!/usr/bin/env python3
"""
Stock Scanner CLI
=================
주식 스캐너 명령행 인터페이스

Usage:
    # 개별 종목 스캔
    python scan.py --mode single --symbols 005930 --date 2024-01-15
    
    # 여러 종목 스캔
    python scan.py --mode multiple --symbols 005930 035420 000660 --date 2024-01-15
    
    # KOSPI 전체 스캔 (100개만)
    python scan.py --mode all --market KOSPI --limit 100 --date 2024-01-15
    
    # KOSDAQ 전체 스캔
    python scan.py --mode all --market KOSDAQ --date 2024-01-15
    
    # 전체 시장 스캔
    python scan.py --mode all --market ALL --limit 50
"""

import argparse
import sys
from datetime import datetime, timedelta
from enhanced_scanner import EnhancedScanner


def main():
    parser = argparse.ArgumentParser(
        description='피벗 포인트 돌파 신호 스캐너',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # 개별 종목 스캔
  python scan.py --mode single --symbols 005930 --date 2024-03-11
  
  # 여러 종목 스캔
  python scan.py --mode multiple --symbols 005930 035420 000660 --date 2024-03-11
  
  # KOSPI 전체 스캔 (상위 100개)
  python scan.py --mode all --market KOSPI --limit 100 --date 2024-03-11
  
  # KOSDAQ 전체 스캔
  python scan.py --mode all --market KOSDAQ --date 2024-03-11
  
  # 전체 시장 스캔 (최근 50개 종목)
  python scan.py --mode all --market ALL --limit 50
        """
    )
    
    parser.add_argument('--mode', 
                       choices=['single', 'multiple', 'all'], 
                       default='all',
                       help='스캔 모드 (기본: all)')
    
    parser.add_argument('--symbols', 
                       nargs='+', 
                       help='종목코드 리스트 (mode: single, multiple)')
    
    parser.add_argument('--market', 
                       choices=['ALL', 'KOSPI', 'KOSDAQ'], 
                       default='ALL',
                       help='시장 선택 (mode: all) (기본: ALL)')
    
    parser.add_argument('--date', 
                       help='기준 일자 (YYYY-MM-DD), 미입력 시 어제')
    
    parser.add_argument('--limit', 
                       type=int, 
                       help='최대 스캔 종목 수 (mode: all)')
    
    parser.add_argument('--workers', 
                       type=int, 
                       default=4, 
                       help='병렬 처리 스레드 수 (기본: 4)')
    
    parser.add_argument('--pivot-period', 
                       type=int, 
                       default=20, 
                       help='피벗 기간 (일) (기본: 20)')
    
    parser.add_argument('--volume-threshold', 
                       type=float, 
                       default=1.5, 
                       help='거래량 임계값 (기본: 1.5 = 150%%)')
    
    parser.add_argument('--min-price', 
                       type=float, 
                       default=1000, 
                       help='최소 주가 (기본: 1000원)')
    
    parser.add_argument('--min-volume', 
                       type=int, 
                       default=100000, 
                       help='최소 거래량 (기본: 100,000)')
    
    parser.add_argument('--output-dir', 
                       default='./data', 
                       help='결과 저장 디렉토리 (기본: ./data)')
    
    args = parser.parse_args()
    
    # 기준일 설정
    if args.date:
        base_date = args.date
    else:
        base_date = (datetime.now() - timedelta(days=1)).strftime('%Y-%m-%d')
    
    print("=" * 70)
    print("🚀 피벗 포인트 돌파 신호 스캐너")
    print("=" * 70)
    print(f"📅 기준일: {base_date}")
    print(f"📊 피벗 기간: {args.pivot_period}일")
    print(f"📈 거래량 임계값: {args.volume_threshold * 100:.0f}%")
    print("=" * 70)
    
    # 스캐너 초기화
    with EnhancedScanner(
        pivot_period=args.pivot_period,
        volume_threshold=args.volume_threshold,
        min_price=args.min_price,
        min_volume=args.min_volume
    ) as scanner:
        
        try:
            if args.mode == 'single':
                # 개별 종목 스캔
                if not args.symbols:
                    print("❌ 종목코드를 입력하세요: --symbols 005930")
                    sys.exit(1)
                
                symbol = args.symbols[0]
                print(f"\n🔍 개별 종목 스캔: {symbol}")
                
                result = scanner.scan_single(symbol, base_date=base_date)
                
                if result:
                    print("\n✅ 신호 감지!")
                    print("-" * 70)
                    for key, value in result.items():
                        print(f"  {key:20s}: {value}")
                    print("-" * 70)
                else:
                    print(f"\n❌ {symbol}: 피벗 돌파 신호 없음")
            
            elif args.mode == 'multiple':
                # 여러 종목 스캔
                if not args.symbols:
                    print("❌ 종목코드를 입력하세요: --symbols 005930 035420 ...")
                    sys.exit(1)
                
                print(f"\n🔍 여러 종목 스캔: {len(args.symbols)}개")
                print(f"   {', '.join(args.symbols)}")
                
                results = scanner.scan_by_symbols(
                    args.symbols, 
                    base_date=base_date,
                    max_workers=args.workers,
                    progress=True
                )
                
                if not results.empty:
                    print(f"\n✅ {len(results)}개 종목 신호 감지!")
                    print("\n🏆 결과:")
                    print("-" * 70)
                    display_cols = ['symbol', 'name', 'market', 'close', 'volume_ratio', 'price_change_pct', 'score']
                    print(results[display_cols].to_string(index=False))
                    print("-" * 70)
                    
                    # 저장
                    saved = scanner.save_results(results, base_date, args.output_dir)
                    print(f"\n💾 결과 저장 완료: {len(saved)}개 파일")
                else:
                    print("\n⚠️ 신호 감지된 종목 없음")
            
            else:  # mode == 'all'
                # 전체 종목 스캔
                print(f"\n🔍 전체 종목 스캔: {args.market}")
                if args.limit:
                    print(f"   (상위 {args.limit}개 종목만)")
                
                results = scanner.scan_all(
                    market=args.market,
                    base_date=base_date,
                    limit=args.limit,
                    max_workers=args.workers,
                    progress=True
                )
                
                if not results.empty:
                    print(f"\n✅ {len(results)}개 종목 신호 감지!")
                    print("\n🏆 TOP 10:")
                    print("-" * 70)
                    display_cols = ['symbol', 'name', 'market', 'close', 'volume_ratio', 'price_change_pct', 'score']
                    print(results[display_cols].head(10).to_string(index=False))
                    print("-" * 70)
                    
                    # 저장
                    saved = scanner.save_results(results, base_date, args.output_dir)
                    print(f"\n💾 결과 저장 완료:")
                    for f in saved:
                        print(f"   - {f}")
                else:
                    print("\n⚠️ 신호 감지된 종목 없음")
        
        except KeyboardInterrupt:
            print("\n\n⚠️ 사용자에 의해 중단됨")
            sys.exit(0)
        except Exception as e:
            print(f"\n❌ 오류 발생: {e}")
            sys.exit(1)
    
    print("\n✅ 완료!")


if __name__ == "__main__":
    main()
