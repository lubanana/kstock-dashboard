#!/usr/bin/env python3
"""
KStock Level 1 Watchdog
5분 단위 모니터링 및 자동 재시작

Features:
- 5분마다 프로세스 상태 체크
- 중단 시 자동 재시작
- Telegram 알림 발송
- 로그 기록
"""

import os
import sys
import time
import subprocess
from datetime import datetime

BASE_PATH = '/home/programs/kstock_analyzer'
LOG_FILE = f'{BASE_PATH}/logs/watchdog.log'
CHECK_INTERVAL = 300  # 5분 (초)
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID', '32083875')


def log(message):
    """로그 기록"""
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    log_msg = f"[{timestamp}] {message}"
    print(log_msg)
    with open(LOG_FILE, 'a', encoding='utf-8') as f:
        f.write(log_msg + '\n')


def send_telegram(message):
    """Telegram 알림"""
    try:
        subprocess.run([
            'openclaw', 'message', 'send',
            '--channel', 'telegram',
            '--to', TELEGRAM_CHAT_ID,
            message
        ], capture_output=True, timeout=30)
    except Exception as e:
        log(f"Telegram error: {e}")


def is_process_running():
    """프로세스 실행 중인지 확인 (psutil 없이)"""
    try:
        result = subprocess.run(
            ['pgrep', '-f', 'level1_sequential.py'],
            capture_output=True,
            text=True
        )
        return result.returncode == 0 and result.stdout.strip()
    except Exception as e:
        log(f"Process check error: {e}")
        return False


def get_progress():
    """현재 진행 상황 확인"""
    try:
        checkpoint_file = f'{BASE_PATH}/data/sequential_checkpoint.json'
        if os.path.exists(checkpoint_file):
            import json
            with open(checkpoint_file, 'r') as f:
                data = json.load(f)
            completed = data.get('completed', 0)
            pct = (completed / 3286) * 100
            return completed, pct
        return 0, 0.0
    except Exception as e:
        log(f"Progress check error: {e}")
        return 0, 0.0


def restart_process():
    """프로세스 재시작"""
    try:
        log("🔄 Restarting level1_sequential.py...")
        
        # 백그라운드 실행
        subprocess.Popen(
            ['python3', f'{BASE_PATH}/level1_sequential.py'],
            stdout=open(f'{BASE_PATH}/logs/sequential_{datetime.now().strftime("%Y%m%d_%H%M")}.log', 'a'),
            stderr=subprocess.STDOUT,
            cwd=BASE_PATH
        )
        
        log("✅ Process restarted")
        return True
    except Exception as e:
        log(f"❌ Restart failed: {e}")
        return False


def main():
    """메인 watchdog 루프"""
    log("=" * 70)
    log("🐕 KStock Level 1 Watchdog Started")
    log("=" * 70)
    log(f"Check interval: {CHECK_INTERVAL//60} minutes")
    log(f"Target: 3,286 stocks")
    log("=" * 70)
    
    # 초기 알림
    completed, pct = get_progress()
    send_telegram(f"🐕 Watchdog 시작\n현재 진행: {completed}개 ({pct:.1f}%)")
    
    last_progress = completed
    same_count = 0
    
    while True:
        try:
            # 현재 시간
            now = datetime.now().strftime('%H:%M:%S')
            
            # 프로세스 상태 확인
            running = is_process_running()
            completed, pct = get_progress()
            
            if running:
                log(f"✅ [{now}] Running - {completed} stocks ({pct:.1f}%)")
                
                # 진행이 없는지 확인 (3회 연속 같은 값이면 재시작)
                if completed == last_progress:
                    same_count += 1
                    if same_count >= 3:
                        log("⚠️ No progress for 3 checks, restarting...")
                        send_telegram(f"⚠️ 진행 없음 ({completed}개)\n재시작 시도...")
                        restart_process()
                        same_count = 0
                else:
                    same_count = 0
                    last_progress = completed
                    
                    # 100개 단위 알림
                    if completed % 100 == 0 and completed > 0:
                        send_telegram(f"📊 진행: {completed}개 ({pct:.1f}%)")
            else:
                log(f"❌ [{now}] Process not running - {completed} stocks ({pct:.1f}%)")
                send_telegram(f"❌ 프로세스 중단됨 ({completed}개)\n재시작 중...")
                
                if restart_process():
                    send_telegram(f"✅ 재시작 완료")
                else:
                    send_telegram(f"❌ 재시작 실패 - 수동 확인 필요")
            
            # 완료 확인
            if completed >= 3286:
                log("🎉 All stocks completed!")
                send_telegram(f"🎉 전체 완료! {completed}개")
                break
            
            # 대기
            time.sleep(CHECK_INTERVAL)
            
        except KeyboardInterrupt:
            log("\n⚠️ Watchdog stopped by user")
            break
        except Exception as e:
            log(f"❌ Watchdog error: {e}")
            time.sleep(60)  # 오류 시 1분 후 재시도


if __name__ == '__main__':
    main()
