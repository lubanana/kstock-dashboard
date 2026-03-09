#!/usr/bin/env python3
"""
KStock Hybrid Analyzer Watchdog
1분마다 프로세스 체크 및 자동 재시작
"""

import os
import sys
import time
import subprocess
import signal
from datetime import datetime

BASE_PATH = '/home/programs/kstock_analyzer'
LOG_FILE = f'{BASE_PATH}/logs/watchdog_hybrid.log'
CHECK_INTERVAL = 60  # 1분
TELEGRAM_CHAT_ID = '32083875'

running = True


def log(message):
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    log_msg = f"[{timestamp}] {message}"
    print(log_msg)
    with open(LOG_FILE, 'a', encoding='utf-8') as f:
        f.write(log_msg + '\n')


def send_telegram(message):
    try:
        subprocess.run([
            'openclaw', 'message', 'send',
            '--channel', 'telegram',
            '--to', TELEGRAM_CHAT_ID,
            message
        ], capture_output=True, timeout=10)
    except:
        pass


def is_process_running():
    """프로세스 실행 중인지 확인"""
    try:
        result = subprocess.run(
            ['pgrep', '-f', 'level1_hybrid.py'],
            capture_output=True, text=True
        )
        return result.returncode == 0 and result.stdout.strip()
    except:
        return False


def get_progress():
    """현재 진행 상황"""
    try:
        import sqlite3
        conn = sqlite3.connect(f'{BASE_PATH}/data/job_queue_hybrid.db')
        cursor = conn.cursor()
        cursor.execute("SELECT status, COUNT(*) FROM jobs GROUP BY status")
        stats = {'total': 0, 'completed': 0, 'failed': 0}
        for row in cursor.fetchall():
            if row[0] == 'completed':
                stats['completed'] = row[1]
            elif row[0] == 'failed':
                stats['failed'] = row[1]
            stats['total'] += row[1]
        conn.close()
        return stats
    except:
        return {'total': 3286, 'completed': 0, 'failed': 0}


def reset_processing_jobs():
    """processing 상태 작업 초기화"""
    try:
        import sqlite3
        conn = sqlite3.connect(f'{BASE_PATH}/data/job_queue_hybrid.db')
        cursor = conn.cursor()
        cursor.execute("UPDATE jobs SET status='pending' WHERE status='processing'")
        conn.commit()
        conn.close()
        log("   🔄 Reset processing jobs")
    except Exception as e:
        log(f"   ⚠️ Reset error: {e}")


def restart_analyzer():
    """분석기 재시작"""
    try:
        log("   🔄 Restarting analyzer...")
        
        # processing 상태 초기화
        reset_processing_jobs()
        
        # 프로세스 시작
        subprocess.Popen(
            ['python3', f'{BASE_PATH}/level1_hybrid.py'],
            stdout=open(f'{BASE_PATH}/logs/hybrid_analyzer.log', 'a'),
            stderr=subprocess.STDOUT,
            cwd=BASE_PATH
        )
        
        log("   ✅ Analyzer restarted")
        return True
    except Exception as e:
        log(f"   ❌ Restart failed: {e}")
        return False


def signal_handler(signum, frame):
    global running
    log("\n⚠️ Watchdog stopped by signal")
    running = False


def main():
    global running
    
    signal.signal(signal.SIGTERM, signal_handler)
    signal.signal(signal.SIGINT, signal_handler)
    
    log("=" * 70)
    log("🐕 Hybrid Analyzer Watchdog Started")
    log("=" * 70)
    log(f"Check interval: {CHECK_INTERVAL} seconds")
    
    # 초기 알림
    stats = get_progress()
    send_telegram(f"🐕 Watchdog 시작\n현재: {stats['completed']}/3286 ({stats['completed']/3286*100:.1f}%)")
    
    last_completed = stats['completed']
    no_progress_count = 0
    
    while running:
        try:
            now = datetime.now().strftime('%H:%M:%S')
            is_running = is_process_running()
            stats = get_progress()
            pct = stats['completed'] / 3286 * 100
            
            if is_running:
                log(f"✅ [{now}] Running - {stats['completed']} stocks ({pct:.1f}%)")
                
                # 진행 체크
                if stats['completed'] == last_completed:
                    no_progress_count += 1
                    if no_progress_count >= 3:  # 3분간 진행 없음
                        log("   ⚠️ No progress for 3 minutes, restarting...")
                        # 프로세스 종료 후 재시작
                        subprocess.run(['pkill', '-f', 'level1_hybrid.py'], capture_output=True)
                        time.sleep(2)
                        if restart_analyzer():
                            send_telegram(f"⚠️ 진행 없음 → 재시작\n({stats['completed']}개)")
                        no_progress_count = 0
                else:
                    no_progress_count = 0
                    last_completed = stats['completed']
                    
                    # 100개 단위 알림
                    if stats['completed'] % 100 == 0 and stats['completed'] > 0:
                        send_telegram(
                            f"📊 진행: {stats['completed']}/3286 ({pct:.1f}%)\n"
                            f"✅ 성공: {stats['completed']} | ❌ 실패: {stats['failed']}"
                        )
            else:
                log(f"❌ [{now}] Process not running - {stats['completed']} stocks ({pct:.1f}%)")
                
                if restart_analyzer():
                    send_telegram(f"❌ 프로세스 중단 → 재시작\n({stats['completed']}개 완료)")
                else:
                    send_telegram(f"❌ 재시작 실패 - 수동 확인 필요")
            
            # 완료 확인
            if stats['completed'] >= 3286:
                log("🎉 All jobs completed!")
                send_telegram(f"🎉 전체 완료! {stats['completed']}개")
                break
            
            time.sleep(CHECK_INTERVAL)
            
        except Exception as e:
            log(f"❌ Watchdog error: {e}")
            time.sleep(10)
    
    log("=" * 70)
    log("🐕 Watchdog stopped")


if __name__ == '__main__':
    main()
