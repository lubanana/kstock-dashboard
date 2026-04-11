#!/usr/bin/env python3
"""
Stock Database CLI
==================
종목 데이터베이스 관리 CLI 도구

사용법:
    python stock_db_cli.py sync          # 전체 동기화
    python stock_db_cli.py info 005930   # 종목 정보 조회
    python stock_db_cli.py convert 005930 krx dart  # 코드 변환
    python stock_db_cli.py stats         # 통계 확인
    python stock_db_cli.py verify        # 매핑 검증
"""

import sys
import argparse
from stock_database_manager import StockDatabaseManager


def main():
    parser = argparse.ArgumentParser(
        description='한국주식 종목 데이터베이스 관리 CLI',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog='''
예시:
  %(prog)s sync                    # 전체 동기화
  %(prog)s info 005930             # 종목 정보 조회
  %(prog)s search 삼성             # 종목명 검색
  %(prog)s convert 005930 krx dart # 코드 변환
  %(prog)s stats                   # 통계 확인
  %(prog)s verify                  # 매핑 검증
        '''
    )
    
    subparsers = parser.add_subparsers(dest='command', help='사용 가능한 명령')
    
    # sync
    sync_parser = subparsers.add_parser('sync', help='전체 데이터베이스 동기화')
    
    # info
    info_parser = subparsers.add_parser('info', help='종목 정보 조회')
    info_parser.add_argument('code', help='종목 코드')
    
    # search
    search_parser = subparsers.add_parser('search', help='종목명 검색')
    search_parser.add_argument('name', help='검색할 종목명')
    
    # convert
    convert_parser = subparsers.add_parser('convert', help='코드 변환')
    convert_parser.add_argument('code', help='변환할 코드')
    convert_parser.add_argument('from_type', choices=['krx', 'dart', 'naver'], help='원본 타입')
    convert_parser.add_argument('to_type', choices=['krx', 'dart', 'naver'], help='대상 타입')
    
    # stats
    stats_parser = subparsers.add_parser('stats', help='통계 확인')
    
    # verify
    verify_parser = subparsers.add_parser('verify', help='매핑 검증')
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return
    
    manager = StockDatabaseManager()
    
    if args.command == 'sync':
        print("🔄 데이터베이스 동기화 시작...")
        success = manager.sync_databases()
        if success:
            print("\n✅ 동기화 완료!")
        else:
            print("\n❌ 동기화 실패!")
            sys.exit(1)
    
    elif args.command == 'info':
        print(f"📊 종목 정보 조회: {args.code}")
        info = manager.get_stock_info(code=args.code)
        if info:
            print("\n" + "="*50)
            print(f"종목코드: {info['krx_code']}")
            print(f"종목명: {info['name']}")
            print(f"타입: {info['code_type']}")
            print(f"KRX: {info['krx_code']}")
            print(f"DART: {info['dart_code']}")
            print(f"Naver: {info['naver_code']}")
            if info.get('sector'):
                print(f"섹터: {info['sector']}")
            if info.get('industry'):
                print(f"업종: {info['industry']}")
            print("="*50)
        else:
            print(f"❌ 종목을 찾을 수 없습니다: {args.code}")
            sys.exit(1)
    
    elif args.command == 'search':
        print(f"🔍 종목 검색: {args.name}")
        info = manager.get_stock_info(name=args.name)
        if info:
            print(f"\n✅ 찾음: {info['name']} ({info['krx_code']})")
        else:
            print(f"❌ 검색 결과 없음: {args.name}")
            sys.exit(1)
    
    elif args.command == 'convert':
        print(f"🔄 코드 변환: {args.code} ({args.from_type} → {args.to_type})")
        result = manager.convert_code(args.code, args.from_type, args.to_type)
        if result:
            print(f"✅ 결과: {result}")
        else:
            print(f"❌ 변환 실패")
            sys.exit(1)
    
    elif args.command == 'stats':
        print("📈 통계 확인...")
        verify = manager.verify_code_mapping()
        print("\n" + "="*50)
        print(f"총 매핑 수: {verify['total_mapping']:,}")
        print(f"DART 연결: {verify['dart_linked']:,}")
        print("\n타입별 분포:")
        for code_type, count in verify['type_distribution'].items():
            print(f"  {code_type}: {count:,}")
        print("="*50)
    
    elif args.command == 'verify':
        print("🔍 매핑 검증...")
        verify = manager.verify_code_mapping()
        print("\n" + "="*50)
        print("검증 결과:")
        print(f"  총 매핑: {verify['total_mapping']:,}")
        print(f"  DART 연결: {verify['dart_linked']:,}")
        
        # 검증 로직
        issues = []
        if verify['total_mapping'] < 2700:
            issues.append("⚠️ 매핑 수가 부족합니다 (기대: 2700+)")
        
        dart_ratio = verify['dart_linked'] / verify['total_mapping'] if verify['total_mapping'] > 0 else 0
        if dart_ratio < 5:
            issues.append(f"⚠️ DART 연결 비율이 낮습니다 (현재: {dart_ratio:.1f}x)")
        
        if issues:
            print("\n발견된 문제:")
            for issue in issues:
                print(f"  {issue}")
        else:
            print("\n✅ 모든 검증 통과!")
        print("="*50)


if __name__ == '__main__':
    main()
