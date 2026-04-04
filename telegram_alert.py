"""
텔레그램 알림 모듈

환경 변수:
- TELEGRAM_BOT_TOKEN: 봇 토큰
- TELEGRAM_CHAT_ID: 채팅 ID
"""

import os
import asyncio
import aiohttp
from datetime import datetime
from typing import Optional


class TelegramAlert:
    """텔레그램 알림 클래스"""
    
    def __init__(self):
        self.bot_token = os.getenv('TELEGRAM_BOT_TOKEN')
        self.chat_id = os.getenv('TELEGRAM_CHAT_ID')
        self.enabled = bool(self.bot_token and self.chat_id)
    
    async def send_signal_alert(self, signal):
        """시그널 알림 전송"""
        if not self.enabled:
            print("[텔레그램 비활성화] 알림을 별도로 볼 수 없습니다.")
            return
        
        emoji_map = {
            'STRONG_BUY': '🟢🟢',
            'BUY': '🟢',
            'NEUTRAL': '⚪',
            'SELL': '🔴',
            'STRONG_SELL': '🔴🔴'
        }
        
        emoji = emoji_map.get(signal.strength.value, '⚪')
        
        message = f"""
{emoji} <b>크립토 시그널 알림</b>

<b>종목:</b> {signal.symbol}
<b>신호:</b> {signal.strength.value}
<b>점수:</b> {signal.total_score:.1f}/100

<b>진입 설정:</b>
• 진입가: {signal.entry_price:,.0f} KRW
• 손절가: {signal.stop_loss:,.0f} KRW (-7%)
• 익절가: {signal.take_profit:,.0f} KRW (+21%)

<b>사유:</b> {signal.reason}

<i>{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</i>
"""
        
        url = f"https://api.telegram.org/bot{self.bot_token}/sendMessage"
        payload = {
            'chat_id': self.chat_id,
            'text': message,
            'parse_mode': 'HTML'
        }
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(url, json=payload, timeout=10) as resp:
                    if resp.status == 200:
                        print("✅ 텔레그램 알림 전송 완료")
                    else:
                        print(f"⚠️ 텔레그램 전송 실패: {resp.status}")
        except Exception as e:
            print(f"❌ 텔레그램 오류: {e}")
    
    async def send_summary(self, signals: list):
        """일일 요약 알림"""
        if not self.enabled:
            return
        
        buy_signals = [s for s in signals if 'BUY' in s.strength.value]
        sell_signals = [s for s in signals if 'SELL' in s.strength.value]
        
        message = f"""
📊 <b>일일 시그널 요약</b>

<b>매수 신호:</b> {len(buy_signals)}개
<b>매도 신호:</b> {len(sell_signals)}개
<b>중립:</b> {len(signals) - len(buy_signals) - len(sell_signals)}개

<i>{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</i>
"""
        
        url = f"https://api.telegram.org/bot{self.bot_token}/sendMessage"
        payload = {
            'chat_id': self.chat_id,
            'text': message,
            'parse_mode': 'HTML'
        }
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(url, json=payload, timeout=10) as resp:
                    pass
        except:
            pass


# 편의 함수
def get_telegram_alert() -> TelegramAlert:
    """텔레그램 알림 인스턴스 반환"""
    return TelegramAlert()
