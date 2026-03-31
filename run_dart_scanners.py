#!/usr/bin/env python3
"""
통합 스캐너 실행 스크립트 (DART 재무 데이터 활용)
- DART Quality Oversold Scanner
- Short-term Surge Scanner
"""

import subprocess
import sys
from datetime import datetime

def run_scanner(scanner_name, script_path):
    """개별 스캐너 실행"""
    print(f"\n{'='*70}")
    print(f"🔄 {scanner_name} 실행 중...")
    print(f"{'='*70}")
    
    try:
        result = subprocess.run(
            [sys.executable, script_path],
            capture_output=True,
            text=True,
            timeout=300
        )
        print(result.stdout)
        if result.stderr:
            print("오류:", result.stderr)
        return True
    except subprocess.TimeoutExpired:
        print(f"⚠️ {scanner_name} 시간 초과")
        return False
    except Exception as e:
        print(f"⚠️ {scanner_name} 실행 오류: {e}")
        return False

def main():
    print("="*70)
    print("🎯 한국 주식 듀얼 스캐너 시스템 (DART 재무 데이터 연동)")
    print("="*70)
    print(f"실행 시간: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print("\n💡 DART 데이터베이스:")
    print("  • dart_financial.db - 재무 데이터 (13,144건)")
    print("  • dart_cache.db - 공시 데이터 (458,271건)")
    
    # 스캐너 목록
    scanners = [
        ("DART 재무 + 과매도 스캐너", "/root/.openclaw/workspace/strg/dart_quality_oversold_scanner.py"),
        ("단기 급등 가능성 스캐너", "/root/.openclaw/workspace/strg/short_term_surge_scanner.py"),
    ]
    
    results = []
    for name, path in scanners:
        success = run_scanner(name, path)
        results.append((name, success))
    
    # 종합 결과
    print("\n" + "="*70)
    print("📊 스캐너 실행 결과")
    print("="*70)
    for name, success in results:
        status = "✅ 성공" if success else "❌ 실패"
        print(f"  {name}: {status}")
    
    print(f"\n📁 결과 파일 위치: /root/.openclaw/workspace/strg/docs/")
    print("="*70)

if __name__ == '__main__':
    main()
