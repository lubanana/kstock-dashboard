#!/usr/bin/env python3
"""
Monitor DB Update Progress - 모니터링 스크립트
"""

import subprocess
import time
from datetime import datetime, timezone, timedelta

def monitor():
    print("=" * 60)
    print("📊 DB 업데이트 모니터링")
    print("=" * 60)
    print("10분 간격으로 진행 상황을 보고합니다.")
    print("Ctrl+C로 종료")
    print("=" * 60)
    
    try:
        while True:
            # 로그 확인
            result = subprocess.run(
                ['tail', '-50', '/root/.openclaw/workspace/strg/full_update.log'],
                capture_output=True, text=True
            )
            
            now = datetime.now(timezone(timedelta(hours=9)))
            print(f"\n[{now.strftime('%H:%M:%S')}] 현재 로그 상태:")
            print("-" * 60)
            print(result.stdout[-2000:] if len(result.stdout) > 2000 else result.stdout)
            print("-" * 60)
            
            # 프로세스 확인
            ps_result = subprocess.run(
                ['pgrep', '-f', 'full_db_update.py'],
                capture_output=True, text=True
            )
            
            if not ps_result.stdout.strip():
                print("⚠️ 프로세스가 종료되었습니다.")
                break
            
            print(f"⏳ 다음 보고: 10분 후... (PID: {ps_result.stdout.strip()})")
            time.sleep(600)  # 10 minutes
            
    except KeyboardInterrupt:
        print("\n\n모니터링 종료")

if __name__ == '__main__':
    monitor()
