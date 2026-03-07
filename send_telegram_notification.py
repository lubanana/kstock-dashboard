#!/usr/bin/env python3
"""
Telegram Notification Sender for KStock Analyzer
KStock 분석 결과를 Telegram으로 발송

Environment Variables:
    TELEGRAM_CHAT_ID: Target chat ID for notifications
"""

import json
import os
from datetime import datetime

BASE_PATH = '/home/programs/kstock_analyzer'
DATA_PATH = f'{BASE_PATH}/data'

# Telegram 설정 (환경 변수에서 로드)
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID', '')

if not TELEGRAM_CHAT_ID:
    print("⚠️  Warning: TELEGRAM_CHAT_ID not set in environment variables")


def load_latest_report():
    """최신 Level 3 리포트 로드"""
    l3_files = [f for f in os.listdir(f'{DATA_PATH}/level3_daily')
                if f.startswith('portfolio_report_') and f.endswith('.json')] if os.path.exists(f'{DATA_PATH}/level3_daily') else []
    
    if not l3_files:
        return None
    
    latest_file = sorted(l3_files)[-1]
    with open(f'{DATA_PATH}/level3_daily/{latest_file}', 'r', encoding='utf-8') as f:
        return json.load(f)


def format_portfolio_message(report):
    """포트폴리오 메시지 포맷팅"""
    if not report:
        return "📊 분석 데이터를 찾을 수 없습니다."
    
    date = report.get('analysis_date', datetime.now().isoformat())[:10]
    summary = report.get('portfolio_summary', {})
    portfolio = report.get('portfolio', {})
    longs = portfolio.get('long', [])
    shorts = portfolio.get('short', [])
    
    market_condition = report.get('market_condition', 'NEUTRAL')
    signal_emoji = "🟢" if market_condition == "BULLISH" else "🟡" if market_condition == "NEUTRAL" else "🔴"
    
    message = f"""📊 KStock Daily Report - {date}

{signal_emoji} 시장 상황: {market_condition}

💰 포트폴리오 현황:
• Long: {len(longs)}종목 ({summary.get('long_pct', 0):.1f}%)
• Short: {len(shorts)}종목 ({summary.get('short_pct', 0):.1f}%)
• Cash: {summary.get('cash_pct', 100):.1f}%
"""
    
    if longs:
        message += "\n📈 Long Positions:\n"
        for pos in longs[:3]:
            message += f"• {pos.get('name', '')}: {pos.get('final_score', 0):.1f}pts\n"
    
    if shorts:
        message += "\n📉 Short Positions:\n"
        for pos in shorts[:3]:
            message += f"• {pos.get('name', '')}: {pos.get('final_score', 0):.1f}pts\n"
    
    message += f"\n🔗 상세 리포트:\nhttps://lubanana.github.io/kstock-dashboard/level3_report.html"
    
    return message


def send_telegram_message(message):
    """Telegram 메시지 발송"""
    import subprocess
    
    if not TELEGRAM_CHAT_ID:
        print("❌ TELEGRAM_CHAT_ID not configured")
        return False
    
    try:
        result = subprocess.run(
            ['openclaw', 'message', 'send', '--channel', 'telegram', 
             '--to', TELEGRAM_CHAT_ID, message],
            capture_output=True, text=True, timeout=30
        )
        return result.returncode == 0
    except Exception as e:
        print(f"Error sending message: {e}")
        return False


def main():
    """메인 함수"""
    print("Loading latest report...")
    report = load_latest_report()
    
    print("Formatting message...")
    message = format_portfolio_message(report)
    
    print("Sending Telegram notification...")
    if send_telegram_message(message):
        print("✅ Message sent successfully!")
    else:
        print("❌ Failed to send message")


if __name__ == '__main__':
    main()
