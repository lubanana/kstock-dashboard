#!/usr/bin/env python3
"""
Daily Pick Log Monitor
GitHub daily_pick_log 모니터링 및 알림 시스템

Features:
- 매일 새로운 pick log 확인
- Telegram 알림 발송

Environment Variables:
    TELEGRAM_CHAT_ID: Target chat ID for notifications
    DAILY_PICK_URL: GitHub raw URL for daily pick log (optional)
"""

import json
import os
import subprocess
import urllib.request
import urllib.error
from datetime import datetime
from typing import Dict, Optional


class DailyPickLogMonitor:
    """Daily Pick Log 모니터"""
    
    GITHUB_RAW_URL = os.getenv('DAILY_PICK_URL', '')
    LOCAL_CACHE_DIR = "/home/programs/kstock_analyzer/data/daily_pick"
    TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID', '')
    
    def __init__(self):
        if not self.GITHUB_RAW_URL:
            raise ValueError("DAILY_PICK_URL environment variable not set")
        
        os.makedirs(self.LOCAL_CACHE_DIR, exist_ok=True)
        self.last_check = self.load_last_check()
        
        if not self.TELEGRAM_CHAT_ID:
            print("⚠️  Warning: TELEGRAM_CHAT_ID not set")
    
    def load_last_check(self) -> str:
        cache_file = f"{self.LOCAL_CACHE_DIR}/last_check.json"
        if os.path.exists(cache_file):
            with open(cache_file, 'r') as f:
                return json.load(f).get('last_check', '')
        return ''
    
    def fetch_daily_pick(self) -> Optional[Dict]:
        today = datetime.now().strftime('%Y-%m-%d')
        url = f"{self.GITHUB_RAW_URL}/{today}.json"
        
        try:
            req = urllib.request.Request(url)
            req.add_header('User-Agent', 'Mozilla/5.0')
            
            with urllib.request.urlopen(req, timeout=30) as response:
                return json.loads(response.read().decode('utf-8'))
        except urllib.error.HTTPError as e:
            if e.code == 404:
                print(f"📭 No pick log for {today}")
                return None
            return None
        except Exception as e:
            print(f"❌ Error: {e}")
            return None
    
    def send_notification(self, data: Dict) -> bool:
        if not self.TELEGRAM_CHAT_ID:
            return False
        
        picks = data.get('picks', [])
        message = f"📊 Daily Pick - {len(picks)} stocks"
        
        try:
            subprocess.run([
                'openclaw', 'message', 'send',
                '--to', self.TELEGRAM_CHAT_ID, message
            ], capture_output=True, timeout=30)
            return True
        except:
            return False
    
    def run(self):
        print("📊 Daily Pick Log Monitor")
        data = self.fetch_daily_pick()
        if data:
            self.send_notification(data)
        return data


def main():
    monitor = DailyPickLogMonitor()
    monitor.run()


if __name__ == '__main__':
    main()
