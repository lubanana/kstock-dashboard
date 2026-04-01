#!/usr/bin/env python3
"""
KAGGRESSIVE Paper Trading Monitor
- 8AM/5PM 알림
- 매수/매도 신호 감지
"""

import sys
sys.path.insert(0, '/root/.openclaw/workspace/strg')

import sqlite3
import json
from datetime import datetime, timedelta
from fdr_wrapper import get_price


class PaperTradingMonitor:
    """페이퍼트레이딩 모니터"""
    
    def __init__(self):
        self.positions_file = 'data/paper_positions.json'
        self.load_positions()
    
    def load_positions(self):
        """보유 포지션 로드"""
        try:
            with open(self.positions_file, 'r') as f:
                self.positions = json.load(f)
        except:
            self.positions = []
    
    def save_positions(self):
        """보유 포지션 저장"""
        with open(self.positions_file, 'w') as f:
            json.dump(self.positions, f, ensure_ascii=False, indent=2)
    
    def check_entry_signals(self, threshold=65):
        """진입 신호 확인"""
        from kagg import KAggressiveScanner
        scanner = KAggressiveScanner()
        
        conn = sqlite3.connect('data/pivot_strategy.db')
        cursor = conn.cursor()
        
        today = datetime.now().strftime('%Y-%m-%d')
        
        # 종목 가져오기
        cursor.execute('''
            SELECT DISTINCT s.symbol, s.name
            FROM stock_info s
            JOIN stock_prices p ON s.symbol = p.symbol AND p.date = ?
            LIMIT 100
        ''', (today,))
        
        symbols = cursor.fetchall()
        conn.close()
        
        entry_signals = []
        
        for sym, name in symbols:
            try:
                result = scanner.calculate_kagg_score(sym, today)
                if result and result['kagg_score'] >= threshold:
                    # 이미 보유중인지 확인
                    if not any(p['symbol'] == sym and p['status'] == 'open' for p in self.positions):
                        entry_signals.append({
                            'time': datetime.now().strftime('%H:%M'),
                            'symbol': sym,
                            'name': name,
                            'score': result['kagg_score'],
                            'price': result['price'],
                            'type': 'ENTRY'
                        })
            except:
                continue
        
        return entry_signals
    
    def check_exit_signals(self):
        """청산 신호 확인 (7일 보유 또는 손절가 도달)"""
        exit_signals = []
        today = datetime.now()
        today_str = today.strftime('%Y-%m-%d')
        
        for pos in self.positions:
            if pos['status'] != 'open':
                continue
            
            try:
                # 현재가 조회
                df = get_price(pos['symbol'], today_str, today_str)
                if df is None or df.empty:
                    continue
                
                current_price = df['Close'].iloc[0]
                entry_date = datetime.strptime(pos['entry_date'], '%Y-%m-%d')
                hold_days = (today - entry_date).days
                
                # 청산 조건 확인
                exit_reason = None
                
                # 1. 7거래일 경과
                if hold_days >= 7:
                    exit_reason = '만기청산'
                
                # 2. 손절가 도달
                elif current_price <= pos['stop_loss']:
                    exit_reason = '손절'
                
                # 3. 목표가 도달 (선택적)
                elif current_price >= pos['target_price']:
                    exit_reason = '목표도달'
                
                if exit_reason:
                    return_pct = ((current_price - pos['entry_price']) / pos['entry_price']) * 100
                    
                    exit_signals.append({
                        'time': datetime.now().strftime('%H:%M'),
                        'symbol': pos['symbol'],
                        'name': pos['name'],
                        'entry_price': pos['entry_price'],
                        'exit_price': current_price,
                        'return_pct': return_pct,
                        'reason': exit_reason,
                        'type': 'EXIT'
                    })
                    
                    # 포지션 업데이트
                    pos['status'] = 'closed'
                    pos['exit_date'] = today_str
                    pos['exit_price'] = current_price
                    pos['return_pct'] = return_pct
            
            except:
                continue
        
        self.save_positions()
        return exit_signals
    
    def get_portfolio_summary(self):
        """포트폴리오 요약"""
        today = datetime.now().strftime('%Y-%m-%d')
        
        open_positions = [p for p in self.positions if p['status'] == 'open']
        closed_positions = [p for p in self.positions if p['status'] == 'closed']
        
        # 현재 보유 종목 평가
        open_summary = []
        total_unrealized = 0
        
        for pos in open_positions:
            try:
                df = get_price(pos['symbol'], today, today)
                if df is not None and not df.empty:
                    current = df['Close'].iloc[0]
                    unrealized = ((current - pos['entry_price']) / pos['entry_price']) * 100
                    total_unrealized += unrealized
                    
                    open_summary.append({
                        'name': pos['name'],
                        'return': unrealized
                    })
            except:
                continue
        
        # 실현 손익
        total_realized = sum(p.get('return_pct', 0) for p in closed_positions)
        
        return {
            'open_count': len(open_positions),
            'closed_count': len(closed_positions),
            'open_positions': open_summary,
            'total_unrealized': total_unrealized,
            'total_realized': total_realized,
            'total_return': total_unrealized + total_realized
        }


def format_notification(signals, summary=None):
    """알림 메시지 포맷팅"""
    lines = []
    
    if signals:
        entries = [s for s in signals if s['type'] == 'ENTRY']
        exits = [s for s in signals if s['type'] == 'EXIT']
        
        if entries:
            lines.append(f"🟢 매수 신호 ({len(entries)}개)")
            for e in entries[:5]:  # 상위 5개만
                lines.append(f"   {e['name']} ({e['symbol']}): {e['score']}점 @ {e['price']:,.0f}원")
        
        if exits:
            lines.append(f"\n🔴 매도 신호 ({len(exits)}개)")
            for x in exits:
                emoji = '📈' if x['return_pct'] > 0 else '📉'
                lines.append(f"   {emoji} {x['name']}: {x['return_pct']:+.2f}% ({x['reason']})")
    
    if summary:
        lines.append(f"\n📊 포트폴리오 현황")
        lines.append(f"   보유: {summary['open_count']}종목 | 청산: {summary['closed_count']}종목")
        lines.append(f"   평가손익: {summary['total_unrealized']:+.2f}%")
        lines.append(f"   실현손익: {summary['total_realized']:+.2f}%")
        lines.append(f"   총 수익: {summary['total_return']:+.2f}%")
    
    return '\n'.join(lines) if lines else None


if __name__ == '__main__':
    import argparse
    
    parser = argparse.ArgumentParser()
    parser.add_argument('--check', choices=['entry', 'exit', 'all'], default='all')
    parser.add_argument('--summary', action='store_true')
    args = parser.parse_args()
    
    monitor = PaperTradingMonitor()
    signals = []
    
    if args.check in ['entry', 'all']:
        entry = monitor.check_entry_signals()
        signals.extend(entry)
    
    if args.check in ['exit', 'all']:
        exit_sigs = monitor.check_exit_signals()
        signals.extend(exit_sigs)
    
    summary = None
    if args.summary:
        summary = monitor.get_portfolio_summary()
    
    message = format_notification(signals, summary)
    
    if message:
        print(message)
    else:
        print("📭 신호 없음")
