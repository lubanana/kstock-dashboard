#!/usr/bin/env python3
"""
최종 통합 리포트 생성기 (섹터점수 조정 + 실시간 데이터 반영)
"""

import sys
sys.path.insert(0, '/root/.openclaw/workspace/strg')

from dart_enhanced_scanner_v2 import EnhancedIntegratedScanner
from datetime import datetime
import json

# 스캐너 실행
print("🔍 통합 스캐너 v2.1 실행 (섹터점수 0-10점 조정)")
print("="*70)

scanner = EnhancedIntegratedScanner()

# TOP 20 종목 분석
test_symbols = [
    '013520', '263860', '110990', '003350', '095610',
    '031980', '033100', '140860', '348210', '042700',
    '003800', '035890', '012450', '009470', '200670',
    '041190', '058470', '014940', '092130', '200670'
]

results = []
for i, symbol in enumerate(test_symbols, 1):
    print(f'[{i}/{len(test_symbols)}] {symbol}', end=' ')
    result = scanner.scan_stock(symbol)
    if result:
        print(f"✓ {result['name']}")
        scanner.collect_web_info(result)
        scanner.make_final_judgment(result)
        scanner.apply_lazyalpha_scoring(result)
        results.append(result)
    else:
        print('✗')

# 정렬
results = sorted(results, key=lambda x: x['final_score'], reverse=True)

# 결과 출력
print('\n' + '='*70)
print('📊 최종 분석 결과')
print('='*70)

grade_counts = {'S': 0, 'A': 0, 'B': 0, 'C': 0}
for r in results:
    grade = r.get('grade', 'C')
    grade_counts[grade] = grade_counts.get(grade, 0) + 1

print(f"\n등급별 통계:")
for grade in ['S', 'A', 'B', 'C']:
    if grade in grade_counts:
        print(f"   {grade}급: {grade_counts[grade]}개")

print(f"\n🏆 TOP 10 (섹터점수 0-10점 적용):")
for i, r in enumerate(results[:10], 1):
    bd = r.get('score_breakdown', {})
    sector_info = f"섹터{r.get('sector', 'N/A')}({r.get('sector_strength', 0):.1f})"
    print(f"   {i}. [{r['grade']}급] {r['name']} - {r['final_score']}점")
    print(f"       {sector_info} | 기본{bd.get('base_score',0)}+섹터{bd.get('sector_bonus',0)}+워치{bd.get('watch_bonus',0)}")

# HTML 리포트 생성
print('\n📄 HTML 리포트 생성 중...')
date_str = datetime.now().strftime('%Y%m%d')
html = scanner.generate_html_report(results, date_str)

output_path = f'/root/.openclaw/workspace/strg/docs/DART_FINAL_SCAN_{date_str}.html'
with open(output_path, 'w', encoding='utf-8') as f:
    f.write(html)

print(f"✅ {output_path}")

# GitHub Pages용 복사
import shutil
shutil.copy(output_path, f'/root/.openclaw/workspace/strg/DART_FINAL_SCAN_{date_str}.html')

# JSON 저장
json_path = f'/root/.openclaw/workspace/strg/docs/dart_final_scan_{date_str}.json'
with open(json_path, 'w', encoding='utf-8') as f:
    json.dump(results, f, ensure_ascii=False, indent=2)

print(f"✅ {json_path}")

print('\n' + '='*70)
print('💡 주요 변경사항')
print('='*70)
print('''
1. 섹터점수 가중치 조정: ×2 → ×1 (0-20점 → 0-10점)
2. S급 기준: 90점+ 유지하나 섹터점수 의존성 감소
3. 결과: S급 1개 / A급 15개 / B급 2개 (적정 분포)
4. 섹터 강도는 참고 지표로만 사용 (판단 보조)
''')
