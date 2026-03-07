#!/usr/bin/env python3
"""
KStock Enhanced Cron Manager
향상된 Cron 작업 관리 시스템

Environment Variables:
    TELEGRAM_CHAT_ID: Target chat ID for notifications
"""

import json
import os
import subprocess
import sys
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
import time


# 환경 변수에서 Telegram Chat ID 로드
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID', '')


class KStockCronManager:
    """KStock Cron 작업 관리자"""
    
    CONFIG_FILE = '/home/programs/kstock_analyzer/config/cron_config.json'
    HISTORY_FILE = '/home/programs/kstock_analyzer/data/cron_history.json'
    LOG_DIR = '/home/programs/kstock_analyzer/logs/cron'
    
    SCHEDULE = {
        'morning_analysis': {
            'name': '오전 분석',
            'time': '08:00',
            'cron': '0 8 * * 1-5',  # 평일(월~금) 08:00
            'timezone': 'Asia/Seoul',
            'tasks': ['level1', 'level2', 'level3', 'report'],
            'dependencies': [],
            'retry': 3,
            'retry_delay': 300,
            'timeout': 600,
            'enabled': True
        },
        'afternoon_analysis': {
            'name': '오후 분석',
            'time': '14:00',
            'cron': '0 14 * * 1-5',  # 평일(월~금) 14:00
            'timezone': 'Asia/Seoul',
            'tasks': ['level1', 'level2', 'level3', 'report'],
            'dependencies': [],
            'retry': 3,
            'retry_delay': 300,
            'timeout': 600,
            'enabled': True
        },
        'evening_analysis': {
            'name': '저녁 분석',
            'time': '19:00',
            'cron': '0 19 * * 1-5',  # 평일(월~금) 19:00
            'timezone': 'Asia/Seoul',
            'tasks': ['level1', 'level2', 'level3', 'report'],
            'dependencies': [],
            'retry': 3,
            'retry_delay': 300,
            'timeout': 600,
            'enabled': True
        },
        'daily_check': {
            'name': '일일 점검',
            'time': '22:00',
            'cron': '0 22 * * 0-4',  # 일~목 22:00 (다음 날 장 대비)
            'timezone': 'Asia/Seoul',
            'tasks': ['system_check', 'strategy_research'],
            'dependencies': [],
            'retry': 2,
            'retry_delay': 600,
            'timeout': 900,
            'enabled': True
        }
    }
    
    def __init__(self):
        self.ensure_directories()
        self.load_config()
        
        if not TELEGRAM_CHAT_ID:
            print("⚠️  Warning: TELEGRAM_CHAT_ID not set in environment variables")
    
    def ensure_directories(self):
        os.makedirs(os.path.dirname(self.CONFIG_FILE), exist_ok=True)
        os.makedirs(os.path.dirname(self.HISTORY_FILE), exist_ok=True)
        os.makedirs(self.LOG_DIR, exist_ok=True)
    
    def load_config(self):
        if os.path.exists(self.CONFIG_FILE):
            with open(self.CONFIG_FILE, 'r') as f:
                self.config = json.load(f)
        else:
            self.config = self.SCHEDULE
            self.save_config()
    
    def save_config(self):
        with open(self.CONFIG_FILE, 'w') as f:
            json.dump(self.config, f, indent=2)
    
    def install_cron_jobs(self):
        """Cron 작업 설치"""
        if not TELEGRAM_CHAT_ID:
            print("⚠️  Warning: TELEGRAM_CHAT_ID not set, skipping cron installation")
            return
        
        for job_id, config in self.SCHEDULE.items():
            if not config.get('enabled', False):
                continue
            
            # 평일(월~금) 스케줄 사용
            cron_expr = config.get('cron', '0 8 * * 1-5')
            
            subprocess.run([
                'openclaw', 'cron', 'add',
                '--name', f'kstock_{job_id}',
                '--cron', cron_expr,
                '--tz', config['timezone'],
                '--session', 'isolated',
                '--to', TELEGRAM_CHAT_ID,
                '--channel', 'telegram',
                '--message', f"📊 {config['name']} 시작\n\npython3 /home/programs/kstock_analyzer/kstock_cron_manager.py --run {job_id}"
            ], capture_output=True)
            
            print(f"✅ Installed: {job_id} ({cron_expr})")
        
        print("\n🎉 All cron jobs installed!")
        print("\nIMPORTANT: Set TELEGRAM_CHAT_ID in .env file before running!")


def main():
    import argparse
    
    parser = argparse.ArgumentParser(description='KStock Enhanced Cron Manager')
    parser.add_argument('--install', action='store_true', help='Cron 작업 설치')
    
    args = parser.parse_args()
    
    manager = KStockCronManager()
    
    if args.install:
        manager.install_cron_jobs()
    else:
        parser.print_help()


if __name__ == '__main__':
    main()
