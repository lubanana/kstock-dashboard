#!/usr/bin/env python3
"""
Premarket Research Monitor
프리마켓 리서치 자료 모니터링 및 Telegram 알림

Environment Variables:
    TELEGRAM_CHAT_ID: Target chat ID for notifications
    PREMARKET_URL: GitHub raw URL for premarket research
"""

import json
import os
import subprocess
import urllib.request
from datetime import datetime
from typing import Dict, Optional


class PremarketResearchMonitor:
    """프리마켓 리서치 모니터"""
    
    GITHUB_RAW_URL = os.getenv('PREMARKET_URL', '')
    LOCAL_CACHE_DIR = "/home/programs/kstock_analyzer/data/premarket"
    TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID', '')
    
    def __init__(self):
        if not self.GITHUB_RAW_URL:
            raise ValueError("PREMARKET_URL environment variable not set")
        
        os.makedirs(self.LOCAL_CACHE_DIR, exist_ok=True)
        self.last_check = ""
        
        if not self.TELEGRAM_CHAT_ID:
            print("⚠️  Warning: TELEGRAM_CHAT_ID not set")
    
    def fetch_premarket_data(self) -> Optional[Dict]:
        today = datetime.now().strftime('%Y-%m-%d')
        url = f"{self.GITHUB_RAW_URL}/{today}.json"
        
        try:
            req = urllib.request.Request(url)
            req.add_header('User-Agent', 'Mozilla/5.0')
            
            with urllib.request.urlopen(req, timeout=30) as response:
                return json.loads(response.read().decode('utf-8'))
        except urllib.error.HTTPError as e:
            if e.code == 404:
                print(f"📭 No premarket data for {today}")
                return None
            return None
        except Exception as e:
            print(f"❌ Error: {e}")
            return None
    
    def send_notification(self, data: Dict) -> bool:
        if not self.TELEGRAM_CHAT_ID:
            return False
        
        message = f"📊 Premarket Report - {data.get('date', '')}"
        
        try:
            subprocess.run([
                'openclaw', 'message', 'send',
                '--to', self.TELEGRAM_CHAT_ID, message
            ], capture_output=True, timeout=30)
            return True
        except:
            return False
    
    def run(self):
        print("📊 Premarket Research Monitor")
        data = self.fetch_premarket_data()
        if data:
            self.send_notification(data)
        return data


def main():
    monitor = PremarketResearchMonitor()
    monitor.run()


if __name__ == '__main__':
    main()
