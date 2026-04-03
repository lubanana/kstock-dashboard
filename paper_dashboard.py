#!/usr/bin/env python3
"""
Paper Trading Dashboard - 페이퍼트레이딩 대시보드
"""

import sys
sys.path.insert(0, '.')
from paper_trading import PaperTradingSystem
from bithumb_trading_simulator import BithumbPublicAPI
from datetime import datetime
import json


def print_dashboard():
    """대시보드 출력"""
    paper = PaperTradingSystem()
    api = BithumbPublicAPI()
    
    # 화면 클리어
    print("\033[2J\033[H")
    
    # 헤더
    print("="*80)
    print(f"🚀 BITHUMB PAPER TRADING DASHBOARD | {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("="*80)
    
    # 포트폴리오 요약
    portfolio_value = paper.balance_krw
    positions_value = 0
    
    print(f"\n💰 계좌 요약")
    print("-"*80)
    print(f"   초기 자본: {paper.initial_balance:>20,.0f} KRW")
    print(f"   현재 현금: {paper.balance_krw:>20,.0f} KRW")
    
    # 포지션 상세
    if paper.positions:
        print(f"\n📊 보유 포지션")
        print("-"*80)
        print(f"   {'코인':<8} {'수량':>14} {'진입가':>14} {'현재가':>14} {'수익률':>10} {'평가금':>14}")
        print("   " + "-"*76)
        
        for coin, pos in paper.positions.items():
            ticker = api.get_ticker(coin)
            if ticker and 'data' in ticker:
                current_price = float(ticker['data'].get('closing_price', pos.entry_price))
                pnl_pct = (current_price - pos.entry_price) / pos.entry_price * 100
                value = pos.volume * current_price
                positions_value += value
                
                print(f"   {coin:<8} {pos.volume:>14,.6f} {pos.entry_price:>14,.0f} {current_price:>14,.0f} {pnl_pct:>+9.1f}% {value:>14,.0f}")
        
        print("   " + "-"*76)
    
    total_value = paper.balance_krw + positions_value
    total_return = (total_value - paper.initial_balance) / paper.initial_balance * 100
    
    print(f"\n   {'포지션 합계:':<20} {positions_value:>20,.0f} KRW")
    print(f"   {'총 평가액:':<20} {total_value:>20,.0f} KRW")
    print(f"   {'총 수익률:':<20} {total_return:>+19.2f}%")
    
    # 거래 내역
    sell_trades = [t for t in paper.trades if t.type == 'SELL']
    if sell_trades:
        print(f"\n🔄 거래 통계")
        print("-"*80)
        wins = [t for t in sell_trades if t.pnl and t.pnl > 0]
        losses = [t for t in sell_trades if t.pnl and t.pnl <= 0]
        
        total_profit = sum(t.pnl for t in wins)
        total_loss = sum(t.pnl for t in losses)
        
        print(f"   총 거래: {len(sell_trades)}회")
        print(f"   승률: {len(wins)}/{len(sell_trades)} ({len(wins)/len(sell_trades)*100:.1f}%)")
        print(f"   총 수익: {total_profit:+,.0f} KRW")
        print(f"   총 손실: {total_loss:+,.0f} KRW")
        print(f"   순손익: {total_profit + total_loss:+,.0f} KRW")
        
        if wins:
            print(f"   최대 수익: {max(t.pnl for t in wins):+,.0f} KRW")
        if losses:
            print(f"   최대 손실: {min(t.pnl for t in losses):+,.0f} KRW")
    
    # 최근 거래
    if paper.trades:
        print(f"\n📋 최근 거래 (최근 5개)")
        print("-"*80)
        print(f"   {'시간':<20} {'타입':<6} {'코인':<6} {'가격':>14} {'수량':>12} {'손익':>12}")
        print("   " + "-"*76)
        
        for trade in paper.trades[-5:]:
            time_str = trade.timestamp[:19].replace('T', ' ')
            pnl_str = f"{trade.pnl:+,.0f}" if trade.pnl else "-"
            print(f"   {time_str:<20} {trade.type:<6} {trade.coin:<6} {trade.price:>14,.0f} {trade.volume:>12,.4f} {pnl_str:>12}")
    
    # 시장 현황
    print(f"\n📈 시장 현황")
    print("-"*80)
    coins = ['BTC', 'ETH', 'XRP', 'SOL']
    
    for coin in coins:
        ticker = api.get_ticker(coin)
        if ticker and 'data' in ticker:
            data = ticker['data']
            price = float(data.get('closing_price', 0))
            open_price = float(data.get('opening_price', price))
            change = (price - open_price) / open_price * 100 if open_price else 0
            emoji = "🟢" if change >= 0 else "🔴"
            print(f"   {emoji} {coin:<6} {price:>14,.0f} KRW ({change:>+.2f}%)")
    
    print("\n" + "="*80)
    print("💡 명령어: python paper_trading.py --mode scan (스캔) | --mode monitor (모니터링)")
    print("="*80)


def main():
    """메인"""
    import argparse
    
    parser = argparse.ArgumentParser()
    parser.add_argument('--refresh', action='store_true', help='실시간 갱신 모드')
    args = parser.parse_args()
    
    if args.refresh:
        import time
        try:
            while True:
                print_dashboard()
                time.sleep(60)  # 1분마다 갱신
        except KeyboardInterrupt:
            print("\n\n✅ 대시보드 종료")
    else:
        print_dashboard()


if __name__ == '__main__':
    main()
