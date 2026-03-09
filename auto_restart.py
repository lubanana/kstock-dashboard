#!/usr/bin/env python3
"""
KStock Auto-Restart Runner
프로세스 중단 시 자동 재시작
"""

import subprocess
import time
import os
from datetime import datetime

def log(msg):
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    print(f"[{timestamp}] {msg}")

def main():
    log("=" * 60)
    log("🔄 KStock Auto-Restart Runner")
    log("=" * 60)
    
    restart_count = 0
    max_restarts = 100  # 최대 재시작 횟수
    
    while restart_count < max_restarts:
        restart_count += 1
        log(f"\n🚀 Starting attempt #{restart_count}")
        
        try:
            # 프로세스 실행
            process = subprocess.Popen(
                ['python3', 'level1_dbqueue.py'],
                cwd='/home/programs/kstock_analyzer',
                stdout=open('/home/programs/kstock_analyzer/logs/dbqueue_run.log', 'a'),
                stderr=subprocess.STDOUT
            )
            
            log(f"   PID: {process.pid}")
            
            # 2분 동안 실행 대기
            try:
                process.wait(timeout=120)
                log(f"   ⚠️ Process exited with code: {process.returncode}")
            except subprocess.TimeoutExpired:
                # 2분 후에도 실행 중이면 정상
                log("   ✅ Running for 2 minutes successfully")
                
                # 5분 더 기다리기
                try:
                    process.wait(timeout=300)
                    log(f"   ⚠️ Process exited after 7 minutes: {process.returncode}")
                except subprocess.TimeoutExpired:
                    log("   ✅ Running for 7 minutes - considering stable")
                    # 30분마다 상태 체크
                    while True:
                        time.sleep(1800)  # 30분
                        if process.poll() is not None:
                            log(f"   ⚠️ Process exited: {process.returncode}")
                            break
                        log("   ✅ Still running...")
            
        except Exception as e:
            log(f"   ❌ Error: {e}")
        
        # 잠시 대기 후 재시작
        log("   ⏳ Waiting 10 seconds before restart...")
        time.sleep(10)
    
    log("\n" + "=" * 60)
    log(f"Reached max restarts ({max_restarts}). Stopping.")
    log("=" * 60)

if __name__ == '__main__':
    main()
