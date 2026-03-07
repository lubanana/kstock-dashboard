#!/usr/bin/env python3
"""
KStock Voice Alert System
음성 알림 시스템

Features:
- 중요 신호 음성 변환 (TTS)
- Telegram 음성 메시지 전송
- 포트폴리오 변동 음성 리포트
- 조건 기반 자동 알림

Environment Variables:
    TELEGRAM_BOT_TOKEN: Telegram Bot API Token
    TELEGRAM_CHAT_ID: Target chat ID for notifications
"""

import json
import os
import subprocess
import tempfile
from datetime import datetime
from typing import Dict, List, Optional
import asyncio


class VoiceAlertSystem:
    """KStock 음성 알림 시스템"""
    
    ALERT_TEMPLATES = {
        'strong_buy': {
            'template': "강력 매수 신호 발생. {name} 종목이 {score}점을 돌파하여 매수 추천 상태입니다. 현재가는 {price}원입니다.",
            'priority': 'high'
        },
        'portfolio_change': {
            'template': "포트폴리오 변경 알림. {action} 포지션이 변경되었습니다. {details}",
            'priority': 'medium'
        },
        'market_alert': {
            'template': "시장 상황 알림. 코스피가 {kospi_change}%, 코스닥이 {kosdaq_change}% 움직였습니다. 현재 시장 상황은 {market_condition}입니다.",
            'priority': 'high'
        },
        'stop_loss': {
            'template': "손절 알림. {name} 종목이 손절 라인인 {stop_price}원을 하회했습니다. 현재가는 {current_price}원입니다.",
            'priority': 'high'
        },
        'take_profit': {
            'template': "익절 알림. {name} 종목이 목표가인 {target_price}원을 상회했습니다. 현재가는 {current_price}원입니다.",
            'priority': 'medium'
        },
        'daily_summary': {
            'template': "오늘의 투자 요약입니다. 롱 포지션은 {long_count}개, 현금 비중은 {cash_pct}퍼센트입니다. Top 종목은 {top_stock}입니다.",
            'priority': 'low'
        }
    }
    
    def __init__(self, telegram_chat_id: str = None):
        # Load from environment variables
        self.telegram_chat_id = telegram_chat_id or os.getenv('TELEGRAM_CHAT_ID', '')
        self.telegram_bot_token = os.getenv('TELEGRAM_BOT_TOKEN', '')
        
        if not self.telegram_bot_token:
            print("⚠️  Warning: TELEGRAM_BOT_TOKEN not set in environment variables")
        if not self.telegram_chat_id:
            print("⚠️  Warning: TELEGRAM_CHAT_ID not set in environment variables")
        
        self.temp_dir = tempfile.gettempdir()
        
    def generate_tts(self, text: str, filename: str = None) -> str:
        """텍스트를 음성으로 변환 (TTS)"""
        if filename is None:
            filename = f"alert_{datetime.now().strftime('%Y%m%d_%H%M%S')}.mp3"
        
        output_path = os.path.join(self.temp_dir, filename)
        
        try:
            from gtts import gTTS
            tts = gTTS(text=text, lang='ko', slow=False)
            tts.save(output_path)
            print(f"✅ TTS 생성 완료: {output_path}")
            return output_path
        except ImportError:
            print("⚠️  gTTS not installed. Installing...")
            subprocess.run(['pip', 'install', 'gtts', '--break-system-packages', '-q'])
            return self.generate_tts(text, filename)
        except Exception as e:
            print(f"❌ TTS 생성 실패: {e}")
            return None
    
    def send_voice_telegram(self, audio_path: str) -> bool:
        """Telegram으로 음성 메시지 전송"""
        if not self.telegram_bot_token:
            print("❌ TELEGRAM_BOT_TOKEN not configured")
            return False
        
        if not self.telegram_chat_id:
            print("❌ TELEGRAM_CHAT_ID not configured")
            return False
        
        try:
            import requests
            url = f"https://api.telegram.org/bot{self.telegram_bot_token}/sendVoice"
            
            with open(audio_path, 'rb') as audio:
                files = {'voice': audio}
                data = {
                    'chat_id': self.telegram_chat_id,
                    'caption': f'🎙️ KStock Voice Alert - {datetime.now().strftime(\"%H:%M\")}'
                }
                response = requests.post(url, files=files, data=data, timeout=30)
                
                if response.status_code == 200:
                    print("✅ 음성 메시지 전송 완료")
                    return True
                else:
                    print(f"❌ 전송 실패: {response.text}")
                    return False
        except Exception as e:
            print(f"❌ Telegram 전송 오류: {e}")
            return False
    
    def send_text_alert(self, alert_type: str, **kwargs) -> bool:
        """텍스트 알림 전송"""
        template_info = self.ALERT_TEMPLATES.get(alert_type, {})
        template = template_info.get('template', '')
        
        if not template:
            return False
        
        message = template.format(**kwargs)
        
        try:
            result = subprocess.run(
                ['openclaw', 'message', 'send',
                 '--channel', 'telegram',
                 '--to', self.telegram_chat_id,
                 message],
                capture_output=True,
                text=True,
                timeout=30
            )
            return result.returncode == 0
        except Exception as e:
            print(f"❌ 텍스트 알림 실패: {e}")
            return False


def test_voice_alerts():
    """음성 알림 테스트"""
    print("=" * 60)
    print("🎙️ KStock Voice Alert System Test")
    print("=" * 60)
    
    voice = VoiceAlertSystem()
    print("\n✅ Voice Alert System initialized")
    print(f"   Chat ID: {voice.telegram_chat_id if voice.telegram_chat_id else 'Not set'}")
    print(f"   Bot Token: {'Set' if voice.telegram_bot_token else 'Not set'}")
    print("=" * 60)


if __name__ == '__main__':
    test_voice_alerts()
