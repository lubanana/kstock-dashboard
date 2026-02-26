#!/usr/bin/env python3
"""
KStock Analyzer - Main Entry Point
한국 주식 종합 분석 프로그램
"""

import sys
import os
from datetime import datetime
from colorama import init, Fore, Style

# 경로 설정
sys.path.insert(0, '/home/programs/kstock_analyzer')

from data.fetcher import StockDataFetcher
from analysis.technical import TechnicalAnalyzer
from tabulate import tabulate

init(autoreset=True)


def print_banner():
    """프로그램 배너 출력"""
    print(Fore.CYAN + """
    ╔══════════════════════════════════════════╗
    ║         KStock Analyzer v1.0             ║
    ║    Korean Stock Analysis with FDR        ║
    ╚══════════════════════════════════════════╝
    """ + Style.RESET_ALL)


def analyze_stock(symbol: str, name: str = ""):
    """종목 분석"""
    print(f"\n{Fore.YELLOW}🔍 분석 중... {symbol} {name}{Style.RESET_ALL}")
    
    fetcher = StockDataFetcher()
    analyzer = TechnicalAnalyzer()
    
    try:
        df = fetcher.get_price(symbol, period=60)
        if df.empty:
            print(f"{Fore.RED}❌ 데이터를 가져올 수 없습니다.{Style.RESET_ALL}")
            return
        
        df = analyzer.full_analysis(df)
        signals = analyzer.generate_signals(df)
        
        latest = df.iloc[-1]
        
        # 기본 정보
        print(f"\n{Fore.GREEN}📊 기본 정보{Style.RESET_ALL}")
        basic_data = [
            ["종가", f"{latest['Close']:,.0f}"],
            ["거래량", f"{latest['Volume']:,.0f}"],
            ["20일선", f"{latest.get('MA20', 0):,.0f}"],
            ["60일선", f"{latest.get('MA60', 0):,.0f}"],
        ]
        print(tabulate(basic_data, tablefmt="simple"))
        
        # 기술적 지표
        print(f"\n{Fore.GREEN}📈 기술적 지표{Style.RESET_ALL}")
        tech_data = [
            ["RSI", f"{latest.get('RSI', 0):.1f}"],
            ["MACD", f"{latest.get('MACD', 0):.2f}"],
            ["MACD Signal", f"{latest.get('MACD_Signal', 0):.2f}"],
            ["볼린저 위치", f"{latest.get('BB_Position', 0)*100:.1f}%"],
        ]
        print(tabulate(tech_data, tablefmt="simple"))
        
        # 매매 신호
        print(f"\n{Fore.GREEN}🎯 매매 신호{Style.RESET_ALL}")
        signal_data = [
            ["추세", signals['trend']],
            ["RSI", signals['rsi_signal']],
            ["MACD", signals['macd_signal']],
            ["종합", signals['overall']],
        ]
        print(tabulate(signal_data, tablefmt="simple"))
        
    except Exception as e:
        print(f"{Fore.RED}❌ 오류 발생: {e}{Style.RESET_ALL}")


def search_and_analyze():
    """종목 검색 후 분석"""
    fetcher = StockDataFetcher()
    
    keyword = input("\n🔍 검색어 (종목명 또는 코드): ").strip()
    if not keyword:
        return
    
    results = fetcher.search_stock(keyword)
    
    if results.empty:
        print(f"{Fore.RED}❌ 검색 결과가 없습니다.{Style.RESET_ALL}")
        return
    
    print(f"\n{Fore.GREEN}📋 검색 결과: {len(results)}개{Style.RESET_ALL}")
    display_cols = ['Code', 'Name', 'Market']
    available_cols = [c for c in display_cols if c in results.columns]
    print(results[available_cols].head(10).to_string(index=False))
    
    if len(results) == 1:
        code = results.iloc[0]['Code']
        name = results.iloc[0]['Name']
        analyze_stock(code, name)
    else:
        code = input("\n📌 분석할 종목코드: ").strip()
        if code:
            name = results[results['Code'] == code]['Name'].values
            name = name[0] if len(name) > 0 else ""
            analyze_stock(code, name)


def quick_list():
    """인기 종목 리스트"""
    popular = [
        ("005930", "삼성전자"),
        ("000660", "SK하이닉스"),
        ("035420", "NAVER"),
        ("005380", "현대차"),
        ("051910", "LG화학"),
        ("035720", "카카오"),
        ("006400", "삼성SDI"),
        ("068270", "셀트리온"),
    ]
    
    print(f"\n{Fore.GREEN}📋 인기 종목{Style.RESET_ALL}")
    for i, (code, name) in enumerate(popular, 1):
        print(f"  {i}. {code} - {name}")
    
    choice = input("\n선택 (번호 또는 코드): ").strip()
    
    if choice.isdigit() and 1 <= int(choice) <= len(popular):
        code, name = popular[int(choice)-1]
        analyze_stock(code, name)
    elif choice:
        analyze_stock(choice)


def main():
    """메인 함수"""
    print_banner()
    
    # 명령행 인수 처리
    if len(sys.argv) > 1:
        symbol = sys.argv[1]
        analyze_stock(symbol)
        return
    
    # 대화형 모드
    while True:
        print(f"\n{Fore.CYAN}{'='*50}{Style.RESET_ALL}")
        print("1. 🔍 종목 검색 및 분석")
        print("2. 📋 인기 종목")
        print("3. 📊 지수 조회")
        print("0. 👋 종료")
        print(f"{Fore.CYAN}{'='*50}{Style.RESET_ALL}")
        
        choice = input("\n선택: ").strip()
        
        if choice == '1':
            search_and_analyze()
        elif choice == '2':
            quick_list()
        elif choice == '3':
            print(f"\n{Fore.YELLOW}📊 KOSPI: 2,641 (예시){Style.RESET_ALL}")
        elif choice == '0':
            print(f"\n{Fore.GREEN}👋 프로그램을 종료합니다.{Style.RESET_ALL}")
            break
        else:
            print(f"{Fore.RED}❌ 잘못된 선택입니다.{Style.RESET_ALL}")


if __name__ == "__main__":
    main()
