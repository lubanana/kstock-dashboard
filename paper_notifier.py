#!/usr/bin/env python3
"""
Paper Trading Notifier - 페이퍼트레이딩 알림 시스템
거래 발생 시 텔레그램 알림 전송
"""

import sys
sys.path.insert(0, '.')
import json
import time
from pathlib import Path
from datetime import datetime
from paper_trading import PaperTradingSystem, Trade
import subprocess


class TradingNotifier:
    """거래 알림 시스템"""
    
    def __init__(self, data_dir: str = "paper_trading_data"):
        self.data_dir = Path(data_dir)
        self.last_trade_count = 0
        self.last_check_time = None
        self._load_state()
    
    def _load_state(self):
        """상태 로드"""
        state_file = self.data_dir / "notifier_state.json"
        if state_file.exists():
            with open(state_file, 'r') as f:
                state = json.load(f)
                self.last_trade_count = state.get('trade_count', 0)
                self.last_check_time = state.get('last_check')
    
    def _save_state(self, trade_count: int):
        """상태 저장"""
        state_file = self.data_dir / "notifier_state.json"
        with open(state_file, 'w') as f:
            json.dump({
                'trade_count': trade_count,
                'last_check': datetime.now().isoformat()
            }, f)
    
    def check_and_notify(self):
        """거래 확인 및 알림"""
        # 거래 내역 로드
        trades_file = self.data_dir / "trades.json"
        if not trades_file.exists():
            return
        
        with open(trades_file, 'r', encoding='utf-8') as f:
            trades = json.load(f)
        
        current_count = len(trades)
        
        # 새로운 거래 확인
        if current_count > self.last_trade_count:
            new_trades = trades[self.last_trade_count:]
            
            for trade in new_trades:
                self._send_notification(trade)
            
            self._save_state(current_count)
            self.last_trade_count = current_count
            
            return len(new_trades)
        
        return 0
    
    def _send_notification(self, trade: dict):
        """알림 전송"""
        trade_type = trade.get('type', 'UNKNOWN')
        coin = trade.get('coin', 'UNKNOWN')
        price = trade.get('price', 0)
        volume = trade.get('volume', 0)
        reason = trade.get('reason', '')
        timestamp = trade.get('timestamp', '')
        
        # 시간 포맷팅
        try:
            dt = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
            time_str = dt.strftime('%H:%M:%S')
        except:
            time_str = timestamp[:8] if timestamp else '--:--:--'
        
        if trade_type == 'BUY':
            amount = trade.get('amount', 0)
            fee = trade.get('fee', 0)
            message = f"""🔵 [페이퍼] 매수 체결

코인: {coin}
가격: {price:,.0f} KRW
수량: {volume:.6f}
금액: {amount:,.0f} KRW
수수료: {fee:,.0f} KRW

사유: {reason}
시간: {time_str}"""
        
        elif trade_type == 'SELL':
            pnl = trade.get('pnl', 0)
            pnl_pct = trade.get('pnl_pct', 0)
            amount = trade.get('amount', 0)
            
            emoji = "🟢" if pnl > 0 else "🔴"
            
            message = f"""{emoji} [페이퍼] 매도 체결

코인: {coin}
가격: {price:,.0f} KRW
수량: {volume:.6f}
금액: {amount:,.0f} KRW

실현손익: {pnl:+,.0f} KRW ({pnl_pct:+.2f}%)
사유: {reason}
시간: {time_str}"""
        
        else:
            message = f"거래 알림: {trade_type} {coin}"
        
        # 콘솔 출력
        print("\n" + "="*60)
        print("📢 거래 알림")
        print("="*60)
        print(message)
        print("="*60 + "\n")
        
        # 알림 파일 기록
        self._log_notification(message)
    
    def _log_notification(self, message: str):
        """알림 로그 기록"""
        log_file = self.data_dir / "notifications.log"
        with open(log_file, 'a', encoding='utf-8') as f:
            f.write(f"\n{'='*60}\n")
            f.write(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}]\n")
            f.write(message)
            f.write(f"\n{'='*60}\n")


def run_monitor(interval_seconds: int = 30):
    """지속 모니터링 실행"""
    notifier = TradingNotifier()
    
    print("="*60)
    print("📡 페이퍼트레이딩 알림 모니터 시작")
    print("="*60)
    print(f"체크 간격: {interval_seconds}초")
    print("Ctrl+C로 종료")
    print("="*60 + "\n")
    
    try:
        while True:
            new_count = notifier.check_and_notify()
            if new_count > 0:
                print(f"✅ {new_count}개 새로운 거래 감지됨 ({datetime.now().strftime('%H:%M:%S')})")
            else:
                print(f"⏱️ 체크 완료 ({datetime.now().strftime('%H:%M:%S')}) - 새 거래 없음")
            
            time.sleep(interval_seconds)
    
    except KeyboardInterrupt:
        print("\n\n✅ 알림 모니터 종료")


if __name__ == '__main__':
    import argparse
    
    parser = argparse.ArgumentParser(description='Paper Trading Notifier')
    parser.add_argument('--interval', type=int, default=30,
                       help='체크 간격 (초)')
    parser.add_argument('--once', action='store_true',
                       help='한번만 실행')
    
    args = parser.parse_args()
    
    if args.once:
        notifier = TradingNotifier()
        count = notifier.check_and_notify()
        print(f"체크 완료: {count}개 새 거래")
    else:
        run_monitor(args.interval)
