#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Market Intelligence CLI
=======================
시장조사 통합 CLI 도구

사용법:
    python market_intelligence_cli.py analyze --symbol 475150 --name "이터닉스" --sector "반도체"
    python market_intelligence_cli.py report --file market_analysis_475150.json
    python market_intelligence_cli.py batch --symbols "475150,005930,000660"
"""

import argparse
import json
import sys
from datetime import datetime

from market_intelligence import MarketIntelligence


def cmd_analyze(args):
    """종목 분석 명령"""
    mi = MarketIntelligence()
    
    print(f"\\n🔍 [{args.name}] 시장조사 분석 시작...")
    analysis = mi.analyze_stock(args.symbol, args.name, args.sector)
    
    # 콘솔 리포트 출력
    report = mi.generate_report(analysis)
    print(report)
    
    # 파일 저장
    output_file = args.output or f"market_analysis_{args.symbol}.json"
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(analysis, f, ensure_ascii=False, indent=2)
    
    print(f"\\n💾 결과 저장됨: {output_file}")
    
    # HTML 리포트 생성 옵션
    if args.html:
        html_file = output_file.replace('.json', '.html')
        generate_html_report(analysis, html_file)
        print(f"💾 HTML 리포트: {html_file}")


def cmd_report(args):
    """JSON 리포트를 HTML로 변환"""
    with open(args.file, 'r', encoding='utf-8') as f:
        analysis = json.load(f)
    
    output = args.output or args.file.replace('.json', '.html')
    generate_html_report(analysis, output)
    print(f"✅ HTML 리포트 생성 완료: {output}")


def cmd_batch(args):
    """배치 분석 명령"""
    symbols = args.symbols.split(',')
    sectors = args.sectors.split(',') if args.sectors else ['반도체'] * len(symbols)
    names = args.names.split(',') if args.names else symbols
    
    mi = MarketIntelligence()
    results = []
    
    print(f"\\n📊 {len(symbols)}개 종목 배치 분석 시작...")
    
    for i, symbol in enumerate(symbols):
        name = names[i] if i < len(names) else symbol
        sector = sectors[i] if i < len(sectors) else '반도체'
        
        print(f"\\n[{i+1}/{len(symbols)}] {name}({symbol}) 분석 중...")
        analysis = mi.analyze_stock(symbol.strip(), name.strip(), sector.strip())
        results.append(analysis)
    
    # 종합 결과 저장
    output_file = args.output or f"batch_analysis_{datetime.now().strftime('%Y%m%d')}.json"
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    
    print(f"\\n✅ 배치 분석 완료! 결과 저장됨: {output_file}")
    
    # 요약 출력
    print("\\n📈 분석 요약:")
    print("-" * 70)
    print(f"{'종목':<15} {'섹터':<10} {'점수':<8} {'추천':<10}")
    print("-" * 70)
    for r in results:
        print(f"{r['name']:<15} {r['sector']:<10} {r['composite_score']:<8.1f} {r['recommendation']:<10}")


def cmd_compare(args):
    """여러 종목 비교 분석"""
    symbols = args.symbols.split(',')
    names = args.names.split(',') if args.names else symbols
    sectors = args.sectors.split(',') if args.sectors else ['반도체'] * len(symbols)
    
    mi = MarketIntelligence()
    
    print("\\n📊 종목 비교 분석")
    print("=" * 70)
    
    results = []
    for i, symbol in enumerate(symbols):
        analysis = mi.analyze_stock(
            symbol.strip(),
            names[i].strip() if i < len(names) else symbol,
            sectors[i].strip() if i < len(sectors) else '반도체'
        )
        results.append(analysis)
    
    # 비교 테이블 출력
    print(f"\\n{'종목':<12} {'점수':<8} {'뉴스':<8} {'산업성장':<10} {'트렌드':<8} {'추천':<10}")
    print("-" * 70)
    
    for r in results:
        news_score = r['news_sentiment']['score'] if r['news_sentiment'] else 0
        industry_growth = r['industry_data']['growth_rate'] if r['industry_data'] else 0
        trend_avg = sum(t['index'] for t in r['google_trends']) / len(r['google_trends']) if r['google_trends'] else 0
        
        print(f"{r['name']:<12} {r['composite_score']:<8.1f} {news_score:<+8.2f} {industry_growth:<10.1f} {trend_avg:<8.0f} {r['recommendation']:<10}")


def generate_html_report(analysis: dict, output_file: str):
    """HTML 리포트 생성"""
    
    html = f"""
<!DOCTYPE html>
<html lang="ko">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>시장조사 리포트 - {analysis['name']}</title>
    <script src="https://cdn.tailwindcss.com"></script>
    <link href="https://fonts.googleapis.com/css2?family=Noto+Sans+KR:wght@400;500;700&display=swap" rel="stylesheet">
    <style>* {{ font-family: 'Noto Sans KR', sans-serif; }}</style>
</head>
<body class="bg-gray-100 py-8">
    <div class="max-w-4xl mx-auto bg-white rounded-xl shadow-lg p-8">
        <div class="text-center mb-8">
            <h1 class="text-3xl font-bold text-gray-800">{analysis['name']} ({analysis['symbol']})</h1>
            <p class="text-gray-500 mt-2">{analysis['sector']} | {analysis['timestamp'][:10]}</p>
        </div>
        
        <div class="bg-gradient-to-r from-blue-500 to-purple-600 rounded-xl p-6 text-white text-center mb-8">
            <div class="text-5xl font-bold">{analysis['composite_score']:.1f}</div>
            <div class="text-xl mt-2">종합 점수</div>
            <div class="text-2xl font-bold mt-4">{analysis['recommendation']}</div>
        </div>
"""
    
    # 뉴스 섹션
    if analysis.get('news_sentiment'):
        ns = analysis['news_sentiment']
        html += f"""
        <div class="mb-6">
            <h2 class="text-xl font-bold mb-4">📰 뉴스 감성 분석</h2>
            <div class="grid grid-cols-2 gap-4">
                <div class="bg-gray-50 p-4 rounded-lg">
                    <div class="text-sm text-gray-500">감성 점수</div>
                    <div class="text-2xl font-bold {'text-green-600' if ns['score'] > 0 else 'text-red-600'}">{ns['score']:+.2f}</div>
                </div>
                <div class="bg-gray-50 p-4 rounded-lg">
                    <div class="text-sm text-gray-500">언급 횟수</div>
                    <div class="text-2xl font-bold">{ns['mentions']}회</div>
                </div>
            </div>
        </div>
"""
    
    # 산업 섹션
    if analysis.get('industry_data'):
        ind = analysis['industry_data']
        html += f"""
        <div class="mb-6">
            <h2 class="text-xl font-bold mb-4">🏭 산업 분석</h2>
            <div class="grid grid-cols-2 gap-4">
                <div class="bg-green-50 p-4 rounded-lg">
                    <div class="text-sm text-gray-500">연평균 성장률</div>
                    <div class="text-2xl font-bold text-green-600">{ind['growth_rate']:.1f}%</div>
                </div>
                <div class="bg-blue-50 p-4 rounded-lg">
                    <div class="text-sm text-gray-500">시장 규모</div>
                    <div class="text-2xl font-bold text-blue-600">{ind['market_size']:.0f}B USD</div>
                </div>
            </div>
        </div>
"""
    
    html += """
    </div>
</body>
</html>
"""
    
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(html)


def main():
    parser = argparse.ArgumentParser(
        description='시장조사 통합 CLI 도구',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
예시:
  # 단일 종목 분석
  python market_intelligence_cli.py analyze --symbol 475150 --name "이터닉스" --sector "반도체"
  
  # HTML 리포트 포함
  python market_intelligence_cli.py analyze --symbol 475150 --name "이터닉스" --html
  
  # 배치 분석
  python market_intelligence_cli.py batch --symbols "475150,005930,000660" \\
                                          --names "이터닉스,삼성전자,SK하이닉스" \\
                                          --sectors "반도체,반도체,반도체"
  
  # 종목 비교
  python market_intelligence_cli.py compare --symbols "475150,005930" \\
                                            --names "이터닉스,삼성전자"
        """
    )
    
    subparsers = parser.add_subparsers(dest='command', help='명령')
    
    # analyze 명령
    analyze_parser = subparsers.add_parser('analyze', help='종목 분석')
    analyze_parser.add_argument('--symbol', required=True, help='종목코드')
    analyze_parser.add_argument('--name', required=True, help='종목명')
    analyze_parser.add_argument('--sector', default='반도체', help='섹터')
    analyze_parser.add_argument('--output', '-o', help='출력 파일명')
    analyze_parser.add_argument('--html', action='store_true', help='HTML 리포트도 생성')
    analyze_parser.set_defaults(func=cmd_analyze)
    
    # report 명령
    report_parser = subparsers.add_parser('report', help='JSON을 HTML로 변환')
    report_parser.add_argument('file', help='JSON 파일')
    report_parser.add_argument('--output', '-o', help='출력 HTML 파일명')
    report_parser.set_defaults(func=cmd_report)
    
    # batch 명령
    batch_parser = subparsers.add_parser('batch', help='배치 분석')
    batch_parser.add_argument('--symbols', required=True, help='종목코드 (콤마 구분)')
    batch_parser.add_argument('--names', help='종목명 (콤마 구분)')
    batch_parser.add_argument('--sectors', help='섹터 (콤마 구분)')
    batch_parser.add_argument('--output', '-o', help='출력 파일명')
    batch_parser.set_defaults(func=cmd_batch)
    
    # compare 명령
    compare_parser = subparsers.add_parser('compare', help='종목 비교')
    compare_parser.add_argument('--symbols', required=True, help='종목코드 (콤마 구분)')
    compare_parser.add_argument('--names', help='종목명 (콤마 구분)')
    compare_parser.add_argument('--sectors', help='섹터 (콤마 구분)')
    compare_parser.set_defaults(func=cmd_compare)
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        sys.exit(1)
    
    args.func(args)


if __name__ == '__main__':
    main()
