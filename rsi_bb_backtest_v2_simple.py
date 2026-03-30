#!/usr/bin/env python3
"""
RSI + 볼린저밴드 단타 전략 - 전체 종목 확장 백테스트 v2.1
개선된 필터링 + 병렬 처리
"""

import pandas as pd
import numpy as np
from datetime import datetime
import sqlite3
import json
import sys

sys.path.insert(0, '/root/.openclaw/workspace/strg')

from fdr_wrapper import get_price

class RSIBBBacktestV2:
    def __init__(self):
        self.fee_rate = 0.00015  # 0.015%
        self.sl_rate = 0.02  # 손절 -2%
        self.tp_rate = 0.03  # 익절 +3%
        self.tp_rate_ext = 0.05  # 확장 익절 +5%
        self.max_hold_days = 3
        
        # 필터링 (완화)
        self.min_trading_amount = 5  # 5억원 (20일 평균)
        self.min_atr_pct = 1.5  # ATR 1.5%+
        
        # 기술적 지표
        self.bb_period = 20
        self.bb_std = 2
        self.rsi_period = 14
        self.rsi_lower = 25
        self.rsi_upper = 35
        self.volume_ma_period = 20
        self.volume_threshold = 1.3  # 1.3배
        
    def get_stock_list(self):
        """종목 리스트 조회"""
        conn = sqlite3.connect('data/pivot_strategy.db')
        cursor = conn.cursor()
        
        # 대형주 + 중형주 위주
        cursor.execute("""
            SELECT symbol, name, market_cap, market 
            FROM stock_info 
            WHERE market IN ('KOSPI', 'KOSDAQ')
              AND name NOT LIKE '%관리%'
              AND name NOT LIKE '%투자유의%'
            ORDER BY COALESCE(market_cap, 0) DESC
        """)
        
        stocks = cursor.fetchall()
        conn.close()
        
        return [{'code': s[0], 'name': s[1], 'market_cap': s[2], 'market': s[3]} for s in stocks]
    
    def calculate_rsi(self, prices, period=14):
        delta = prices.diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
        rs = gain / loss
        return 100 - (100 / (1 + rs))
    
    def backtest_stock(self, stock, start_date, end_date):
        """단일 종목 백테스트"""
        ticker = stock['code']
        name = stock.get('name', '')
        
        try:
            df = get_price(ticker, start_date, end_date)
            if df is None or len(df) < 50:
                return [], "데이터 부족"
            
            # 거래대금 필터
            df['Amount'] = df['Close'] * df['Volume'] / 100000000  # 억원
            avg_amount = df['Amount'].tail(20).mean()
            if avg_amount < self.min_trading_amount:
                return [], f"거래대금 부족 ({avg_amount:.1f}억)"
            
            # ATR 필터
            df['ATR'] = (df['High'] - df['Low']).rolling(14).mean()
            atr_pct = (df['ATR'].iloc[-1] / df['Close'].iloc[-1]) * 100
            if atr_pct < self.min_atr_pct:
                return [], f"ATR 부족 ({atr_pct:.1f}%)"
            
            # 기술적 지표
            df['RSI'] = self.calculate_rsi(df['Close'], self.rsi_period)
            df['BB_Middle'] = df['Close'].rolling(window=self.bb_period).mean()
            df['BB_Std'] = df['Close'].rolling(window=self.bb_period).std()
            df['BB_Upper'] = df['BB_Middle'] + (df['BB_Std'] * self.bb_std)
            df['BB_Lower'] = df['BB_Middle'] - (df['BB_Std'] * self.bb_std)
            df['Volume_MA'] = df['Volume'].rolling(window=self.volume_ma_period).mean()
            df['Volume_Ratio'] = df['Volume'] / df['Volume_MA']
            df['Return_5d'] = (df['Close'] - df['Close'].shift(5)) / df['Close'].shift(5) * 100
            
            # 매수 신호
            df['Buy_Signal'] = (
                (df['RSI'] >= self.rsi_lower) & 
                (df['RSI'] <= self.rsi_upper) &
                (df['Close'] <= df['BB_Lower'] * 1.02) &
                (df['Volume_Ratio'] >= self.volume_threshold) &
                (df['Close'] > df['Open'])  # 양봉
            )
            
            # 백테스트
            trades = []
            position = None
            entry_price = entry_date = None
            
            for i in range(35, len(df)):
                date = df.index[i]
                row = df.iloc[i]
                
                if position is None and row['Buy_Signal']:
                    position = 'LONG'
                    entry_price = row['Close']
                    entry_date = date
                    entry_rsi = row['RSI']
                
                elif position == 'LONG':
                    current_price = row['Close']
                    holding_days = (date - entry_date).days
                    pnl_rate = (current_price - entry_price) / entry_price
                    
                    exit_reason = None
                    if pnl_rate <= -self.sl_rate:
                        exit_reason = 'STOP_LOSS'
                    elif pnl_rate >= self.tp_rate_ext:
                        exit_reason = 'TP_EXT'
                    elif pnl_rate >= self.tp_rate:
                        exit_reason = 'TAKE_PROFIT'
                    elif holding_days >= self.max_hold_days:
                        exit_reason = 'TIME_EXIT'
                    
                    if exit_reason:
                        net_pnl_rate = (pnl_rate - self.fee_rate * 2) * 100
                        trades.append({
                            'ticker': ticker, 'name': name,
                            'entry_date': entry_date.strftime('%Y-%m-%d'),
                            'exit_date': date.strftime('%Y-%m-%d'),
                            'holding_days': holding_days,
                            'entry_price': round(entry_price, 0),
                            'exit_price': round(current_price, 0),
                            'entry_rsi': round(entry_rsi, 1),
                            'net_pnl_rate': round(net_pnl_rate, 2),
                            'result': 'WIN' if net_pnl_rate > 0 else 'LOSS',
                            'exit_reason': exit_reason
                        })
                        position = None
            
            return trades, f"✅ {len(trades)}거래"
            
        except Exception as e:
            return [], f"❌ {str(e)[:20]}"

def main():
    backtest = RSIBBBacktestV2()
    
    # 종목 리스트 (상위 50개 대형주)
    stocks = backtest.get_stock_list()[:50]
    print(f"📊 대상 종목: {len(stocks)}개 (상위 50개 대형주)")
    print(f"   기간: 2024-01-01 ~ 2025-03-30")
    print(f"   필터: 거래대금 {backtest.min_trading_amount}억+, ATR {backtest.min_atr_pct}%+")
    print(f"   진입: RSI {backtest.rsi_lower}~{backtest.rsi_upper}, BB 하단, 거래량 {backtest.volume_threshold}배")
    print("="*70)
    
    all_trades = []
    filtered = {'거래대금 부족': 0, 'ATR 부족': 0, '데이터 부족': 0, '오류': 0}
    
    for i, stock in enumerate(stocks, 1):
        print(f"[{i:2d}/{len(stocks)}] {stock['code']} ({stock['name'][:8]:8s})", end=' ')
        trades, msg = backtest.backtest_stock(stock, '2024-01-01', '2025-03-30')
        
        if trades:
            all_trades.extend(trades)
            wins = sum(1 for t in trades if t['result'] == 'WIN')
            print(f"→ {msg} (승: {wins})")
        else:
            for key in filtered:
                if key in msg:
                    filtered[key] += 1
                    break
            if i % 10 == 0 or '거래' in msg:
                print(f"→ {msg}")
            else:
                print()
    
    # 리포트
    print("\n" + "="*70)
    if all_trades:
        df = pd.DataFrame(all_trades)
        total = len(df)
        wins = len(df[df['result'] == 'WIN'])
        win_rate = wins / total * 100
        avg_pnl = df['net_pnl_rate'].mean()
        total_ret = ((1 + df['net_pnl_rate']/100).prod() - 1) * 100
        
        print(f"📈 백테스트 결과")
        print(f"   총 거래: {total}회")
        print(f"   승률: {win_rate:.1f}% ({wins}승 / {total-wins}패)")
        print(f"   총 수익률: +{total_ret:.2f}%")
        print(f"   평균 수익/거래: {avg_pnl:.2f}%")
        
        # 저장
        output = f'/root/.openclaw/workspace/strg/docs/rsi_bb_v2_backtest_{datetime.now().strftime("%Y%m%d")}.md'
        with open(output, 'w', encoding='utf-8') as f:
            f.write(f"# RSI+BB 단타 백테스트 v2.1\n\n")
            f.write(f"**대상:** 상위 50개 대형주\n")
            f.write(f"**기간:** 2024-01-01 ~ 2025-03-30\n")
            f.write(f"**총 거래:** {total}회\n")
            f.write(f"**승률:** {win_rate:.1f}%\n")
            f.write(f"**총 수익률:** +{total_ret:.2f}%\n\n")
            f.write("## 거래 내역\n\n")
            f.write("| 종목 | 진입일 | 청산일 | 진입RSI | 수익률 | 결과 |\n")
            f.write("|:---|:---|:---|---:|---:|:---:|\n")
            for t in all_trades[:30]:
                f.write(f"| {t['ticker']} | {t['entry_date']} | {t['exit_date']} | {t['entry_rsi']} | {t['net_pnl_rate']:+.2f}% | {t['result']} |\n")
        
        json_output = output.replace('.md', '.json')
        with open(json_output, 'w', encoding='utf-8') as f:
            json.dump({'summary': {'total': total, 'win_rate': win_rate, 'total_return': total_ret}, 'trades': all_trades}, f, ensure_ascii=False, indent=2)
        
        print(f"\n📄 저장: {output}")
    else:
        print("⚠️ 거래 내역 없음")
        print(f"   필터링: {filtered}")

if __name__ == '__main__':
    main()
