#!/usr/bin/env python3
"""
RSI + 볼린저밴드 단타 전략 - 전체 종목 확장 백테스트 v2.0
필터링 조건 강화:
1. 시총 1,000억원 이상
2. 거래대금 10억원 이상 (20일 평균)
3. ATR 2% 이상 (변동성 확보)
4. 이전 5일 수익률 -5% 이상 (하락 후 반등)
5. 관리/투자유의 종목 제외

진입 조건 (개선):
- RSI 25~35 (과매도, 기존 30 고정 → 유연화)
- BB 하단 터치 + 양봉 마감
- 거래량 1.5배↑
- MACD 히스토그램 개선 (음수→양수 전환)

청산 조건:
- 손절: -2% (고정)
- 익절: +3% (고정) or +5% (추세 지속 시)
- 시간: 최대 3일
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import sqlite3
import json
import os
import sys
from concurrent.futures import ProcessPoolExecutor, as_completed
import multiprocessing

sys.path.insert(0, '/root/.openclaw/workspace/strg')

try:
    from fdr_wrapper import get_price
except ImportError:
    get_price = None

class RSIBBBacktestV2:
    def __init__(self, initial_capital=10000000, fee_rate=0.015):
        self.initial_capital = initial_capital
        self.fee_rate = fee_rate / 100
        self.sl_rate = 0.02  # 손절 -2%
        self.tp_rate = 0.03  # 익절 +3%
        self.tp_rate_extended = 0.05  # 추세 지속 시 +5%
        self.max_hold_days = 3
        
        # 필터링 조건
        self.min_market_cap = 1000  # 1,000억원
        self.min_trading_amount = 10  # 10억원 (일일)
        self.min_atr_pct = 2.0  # ATR 2% 이상
        self.min_prev_return = -5.0  # 이전 5일 -5% 이상 하락
        
        # 기술적 지표 설정
        self.bb_period = 20
        self.bb_std = 2
        self.rsi_period = 14
        self.rsi_lower = 25  # 과매도 하한
        self.rsi_upper = 35  # 과매도 상한
        self.volume_ma_period = 20
        self.volume_threshold = 1.5
        self.macd_fast = 12
        self.macd_slow = 26
        self.macd_signal = 9
        
    def get_stock_list(self, db_path='data/pivot_strategy.db'):
        """백테스트 대상 종목 조회"""
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        query = """
        SELECT symbol, name, market_cap, sector, market
        FROM stock_info 
        WHERE (market_cap >= ? OR market_cap IS NULL)
          AND market IN ('KOSPI', 'KOSDAQ')
          AND name NOT LIKE '%관리%'
          AND name NOT LIKE '%투자유의%'
          AND name NOT LIKE '%홈페이지%'
          AND name NOT LIKE '%스팩%'
        ORDER BY COALESCE(market_cap, 0) DESC
        """
        
        # 시총 1,000억 이상 (단위: 억원)
        cursor.execute(query, (self.min_market_cap,))
        stocks = cursor.fetchall()
        conn.close()
        
        return [{'code': s[0], 'name': s[1], 'market_cap': s[2], 'sector': s[3], 'market': s[4]} for s in stocks]
    
    def calculate_atr(self, df, period=14):
        """ATR (Average True Range) 계산"""
        high_low = df['High'] - df['Low']
        high_close = np.abs(df['High'] - df['Close'].shift())
        low_close = np.abs(df['Low'] - df['Close'].shift())
        ranges = pd.concat([high_low, high_close, low_close], axis=1)
        true_range = np.max(ranges, axis=1)
        atr = true_range.rolling(period).mean()
        return atr
    
    def calculate_rsi(self, prices, period=14):
        """RSI 계산"""
        delta = prices.diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
        rs = gain / loss
        rsi = 100 - (100 / (1 + rs))
        return rsi
    
    def calculate_macd(self, df):
        """MACD 계산"""
        ema_fast = df['Close'].ewm(span=self.macd_fast).mean()
        ema_slow = df['Close'].ewm(span=self.macd_slow).mean()
        df['MACD'] = ema_fast - ema_slow
        df['MACD_Signal'] = df['MACD'].ewm(span=self.macd_signal).mean()
        df['MACD_Hist'] = df['MACD'] - df['MACD_Signal']
        return df
    
    def calculate_bollinger(self, df):
        """볼린저밴드 계산"""
        df['BB_Middle'] = df['Close'].rolling(window=self.bb_period).mean()
        df['BB_Std'] = df['Close'].rolling(window=self.bb_period).std()
        df['BB_Upper'] = df['BB_Middle'] + (df['BB_Std'] * self.bb_std)
        df['BB_Lower'] = df['BB_Middle'] - (df['BB_Std'] * self.bb_std)
        df['BB_Width'] = (df['BB_Upper'] - df['BB_Lower']) / df['BB_Middle']
        df['BB_Position'] = (df['Close'] - df['BB_Lower']) / (df['BB_Upper'] - df['BB_Lower'])
        return df
    
    def filter_stocks(self, ticker, start_date, end_date):
        """사전 필터링 - 데이터 품질 확인"""
        try:
            if get_price:
                df = get_price(ticker, start_date, end_date)
            else:
                import FinanceDataReader as fdr
                df = fdr.DataReader(ticker, start_date, end_date)
            
            if df is None or len(df) < 50:
                return None, "데이터 부족"
            
            # 최근 20일 거래대금 평균 계산
            df['Trading_Amount'] = df['Close'] * df['Volume']
            avg_trading_amount = df['Trading_Amount'].tail(20).mean() / 100000000  # 억원
            
            if avg_trading_amount < self.min_trading_amount:
                return None, f"거래대금 부족 ({avg_trading_amount:.1f}억)"
            
            # ATR 계산
            df['ATR'] = self.calculate_atr(df)
            atr_pct = (df['ATR'].iloc[-1] / df['Close'].iloc[-1]) * 100
            
            if atr_pct < self.min_atr_pct:
                return None, f"ATR 부족 ({atr_pct:.2f}%)"
            
            return df, "필터 통과"
            
        except Exception as e:
            return None, f"오류: {str(e)[:30]}"
    
    def generate_signals(self, df):
        """개선된 매매 신호 생성"""
        df = df.copy()
        
        # RSI
        df['RSI'] = self.calculate_rsi(df['Close'], self.rsi_period)
        
        # 볼린저밴드
        df = self.calculate_bollinger(df)
        
        # MACD
        df = self.calculate_macd(df)
        
        # 거래량
        df['Volume_MA'] = df['Volume'].rolling(window=self.volume_ma_period).mean()
        df['Volume_Ratio'] = df['Volume'] / df['Volume_MA']
        
        # 5일 수익률
        df['Return_5d'] = (df['Close'] - df['Close'].shift(5)) / df['Close'].shift(5) * 100
        
        # 캔들 패턴 (양봉/음봉)
        df['Is_Bullish'] = df['Close'] > df['Open']
        
        # 개선된 매수 신호
        df['Buy_Signal'] = (
            (df['RSI'] >= self.rsi_lower) & 
            (df['RSI'] <= self.rsi_upper) &  # RSI 25~35 구간
            (df['Close'] <= df['BB_Lower'] * 1.01) &  # BB 하단 ±1%
            (df['Volume_Ratio'] >= self.volume_threshold) &  # 거래량 1.5배
            (df['Return_5d'] <= self.min_prev_return) &  # 5일 -5% 이상 하락
            (df['MACD_Hist'] > df['MACD_Hist'].shift(1)) &  # MACD 개선
            (df['Is_Bullish'] == True)  # 양봉
        )
        
        # 매도 신호
        df['Sell_Signal'] = (
            (df['RSI'] >= 70) & 
            (df['Close'] >= df['BB_Upper'] * 0.99) &
            (df['MACD_Hist'] < df['MACD_Hist'].shift(1))
        )
        
        return df
    
    def backtest_stock(self, ticker_info, start_date, end_date):
        """단일 종목 백테스트"""
        ticker = ticker_info['code']
        name = ticker_info.get('name', '')
        
        try:
            # 사전 필터링
            df, msg = self.filter_stocks(ticker, start_date, end_date)
            if df is None:
                return [], msg
            
            # 신호 생성
            df = self.generate_signals(df)
            
            # 백테스트
            trades = []
            position = None
            entry_price = entry_date = entry_rsi = entry_bb_pos = None
            
            for i in range(max(self.rsi_period, self.bb_period) + 10, len(df)):
                date = df.index[i]
                row = df.iloc[i]
                
                # 포지션 없음
                if position is None:
                    if row['Buy_Signal']:
                        position = 'LONG'
                        entry_price = row['Close']
                        entry_date = date
                        entry_rsi = row['RSI']
                        entry_bb_pos = row['BB_Position']
                        entry_volume_ratio = row['Volume_Ratio']
                        entry_prev_return = row['Return_5d']
                
                # 포지션 보유
                elif position == 'LONG':
                    current_price = row['Close']
                    holding_days = (date - entry_date).days
                    pnl_rate = (current_price - entry_price) / entry_price
                    
                    # 청산 조건
                    exit_reason = None
                    
                    if pnl_rate <= -self.sl_rate:
                        exit_reason = 'STOP_LOSS'
                    elif pnl_rate >= self.tp_rate_extended:
                        exit_reason = 'TAKE_PROFIT_EXT'
                    elif pnl_rate >= self.tp_rate and row['Sell_Signal']:
                        exit_reason = 'TAKE_PROFIT'
                    elif holding_days >= self.max_hold_days:
                        exit_reason = 'TIME_EXIT'
                    elif row['Sell_Signal']:
                        exit_reason = 'SELL_SIGNAL'
                    
                    if exit_reason:
                        fee = (entry_price + current_price) * self.fee_rate
                        net_pnl = (current_price - entry_price) - fee
                        net_pnl_rate = net_pnl / entry_price
                        
                        trades.append({
                            'ticker': ticker,
                            'name': name,
                            'entry_date': entry_date.strftime('%Y-%m-%d'),
                            'exit_date': date.strftime('%Y-%m-%d'),
                            'entry_price': round(entry_price, 2),
                            'exit_price': round(current_price, 2),
                            'holding_days': holding_days,
                            'entry_rsi': round(entry_rsi, 2),
                            'entry_bb_position': round(entry_bb_pos, 4),
                            'entry_volume_ratio': round(entry_volume_ratio, 2),
                            'entry_prev_return': round(entry_prev_return, 2),
                            'exit_reason': exit_reason,
                            'pnl_rate': round(pnl_rate * 100, 2),
                            'net_pnl_rate': round(net_pnl_rate * 100, 2),
                            'result': 'WIN' if net_pnl > 0 else 'LOSS'
                        })
                        position = None
            
            return trades, f"✅ {len(trades)}거래"
            
        except Exception as e:
            return [], f"❌ 오류: {str(e)[:30]}"
    
    def run_backtest_parallel(self, stocks, start_date, end_date, max_workers=4, progress_file='backtest_progress.json'):
        """병렬 백테스트 실행"""
        all_trades = []
        filtered_out = {'거래대금 부족': 0, 'ATR 부족': 0, '데이터 부족': 0, '오류': 0}
        
        print(f"\n📊 RSI+BB 단타 백테스트 v2.0 (전체 종목)")
        print(f"   기간: {start_date} ~ {end_date}")
        print(f"   대상 종목: {len(stocks)}개")
        print(f"   필터: 시총 {self.min_market_cap}억+, 거래대금 {self.min_trading_amount}억+, ATR {self.min_atr_pct}%+")
        print(f"   진입: RSI {self.rsi_lower}~{self.rsi_upper}, BB 하단, 거래량 {self.volume_threshold}배")
        print(f"   청산: -{self.sl_rate*100}% 손절 / +{self.tp_rate*100}% or +{self.tp_rate_extended*100}% 익절")
        print("="*80)
        
        completed = 0
        
        with ProcessPoolExecutor(max_workers=max_workers) as executor:
            future_to_stock = {
                executor.submit(self.backtest_stock, stock, start_date, end_date): stock 
                for stock in stocks
            }
            
            for future in as_completed(future_to_stock):
                stock = future_to_stock[future]
                try:
                    trades, msg = future.result()
                    
                    if trades:
                        all_trades.extend(trades)
                        wins = sum(1 for t in trades if t['result'] == 'WIN')
                        print(f"[{completed+1}/{len(stocks)}] {stock['code']} ({stock['name'][:8]}): {msg} (승: {wins})")
                    else:
                        # 필터링 사유 집계
                        for key in filtered_out:
                            if key in msg:
                                filtered_out[key] += 1
                                break
                        if completed % 50 == 0:
                            print(f"[{completed+1}/{len(stocks)}] {stock['code']} - {msg}")
                    
                    completed += 1
                    
                    # 진행상황 저장
                    if completed % 100 == 0:
                        progress = {
                            'completed': completed,
                            'total': len(stocks),
                            'trades': len(all_trades),
                            'filtered': filtered_out,
                            'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                        }
                        with open(progress_file, 'w') as f:
                            json.dump(progress, f, indent=2)
                            
                except Exception as e:
                    print(f"[{completed+1}/{len(stocks)}] {stock['code']} - ❌ 실행 오류: {e}")
                    completed += 1
        
        return all_trades, filtered_out
    
    def generate_report(self, trades, filtered_out, output_path):
        """백테스트 리포트 생성"""
        if not trades:
            print("\n⚠️ 거래 내역 없음")
            return
        
        df = pd.DataFrame(trades)
        
        # 기본 통계
        total_trades = len(df)
        wins = len(df[df['result'] == 'WIN'])
        losses = total_trades - wins
        win_rate = (wins / total_trades * 100) if total_trades > 0 else 0
        
        avg_pnl = df['net_pnl_rate'].mean()
        avg_win = df[df['result'] == 'WIN']['net_pnl_rate'].mean() if wins > 0 else 0
        avg_loss = df[df['result'] == 'LOSS']['net_pnl_rate'].mean() if losses > 0 else 0
        
        max_win = df['net_pnl_rate'].max()
        max_loss = df['net_pnl_rate'].min()
        
        # 누적 수익률
        cumulative = (1 + df['net_pnl_rate'] / 100).cumprod()
        total_return = (cumulative.iloc[-1] - 1) * 100 if len(cumulative) > 0 else 0
        
        # Profit Factor
        gross_profit = df[df['result'] == 'WIN']['net_pnl_rate'].sum() if wins > 0 else 0
        gross_loss = abs(df[df['result'] == 'LOSS']['net_pnl_rate'].sum()) if losses > 0 else 0.001
        profit_factor = gross_profit / gross_loss
        
        # 종목별 통계
        ticker_stats = df.groupby(['ticker', 'name']).agg({
            'result': ['count', lambda x: (x == 'WIN').sum() / len(x) * 100],
            'net_pnl_rate': 'mean'
        }).round(2)
        ticker_stats.columns = ['trades', 'win_rate', 'avg_pnl']
        ticker_stats = ticker_stats.reset_index()
        
        # 청산 이유
        exit_stats = df.groupby('exit_reason').size().sort_values(ascending=False)
        
        # 연도별 통계
        df['year'] = pd.to_datetime(df['entry_date']).dt.year
        yearly_stats = df.groupby('year').agg({
            'result': lambda x: (x == 'WIN').sum() / len(x) * 100,
            'net_pnl_rate': 'sum'
        }).round(2)
        
        # 리포트 출력
        report = f"""# 📊 RSI + 볼린저밴드 단타 백테스트 리포트 v2.0
**생성일시:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

---

## 📈 종합 성과

| 항목 | 값 | 평가 |
|:---|---:|:---:|
| **총 거래 횟수** | {total_trades} | - |
| **승률** | {win_rate:.1f}% | {"🟢" if win_rate >= 60 else "🟡" if win_rate >= 50 else "🔴"} |
| **승 / 패** | {wins} / {losses} | - |
| **Profit Factor** | {profit_factor:.2f} | {"🟢" if profit_factor >= 1.5 else "🟡" if profit_factor >= 1.0 else "🔴"} |
| **총 수익률 (복리)** | +{total_return:.2f}% | {"🟢" if total_return > 0 else "🔴"} |
| **평균 수익/거래** | {avg_pnl:.2f}% | - |
| **평균 수익 (승)** | +{avg_win:.2f}% | - |
| **평균 손실 (패)** | {avg_loss:.2f}% | {"🟢" if avg_loss > -3 else "🟡"} |
| **최대 수익** | +{max_win:.2f}% | - |
| **최대 손실** | {max_loss:.2f}% | {"🟢" if max_loss > -5 else "🔴"} |
| **손익비** | 1:{abs(avg_win/avg_loss):.1f} | {"🟢" if abs(avg_win/avg_loss) >= 1.5 else "🟡"} |

---

## 📋 필터링 결과

| 사유 | 제외 종목 수 |
|:---|---:|
"""
        for reason, count in filtered_out.items():
            report += f"| {reason} | {count} |\n"
        
        report += f"""

---

## 📊 청산 이유 분석

| 청산 이유 | 횟수 | 비율 |
|:---|---:|---:|
"""
        for reason, count in exit_stats.items():
            pct = count / total_trades * 100
            report += f"| {reason} | {count} | {pct:.1f}% |\n"
        
        report += f"""

---

## 📅 연도별 성과

| 연도 | 승률 | 총 수익률 |
|:---|---:|---:|
"""
        for year, row in yearly_stats.iterrows():
            report += f"| {year} | {row['result']:.1f}% | {row['net_pnl_rate']:+.2f}% |\n"
        
        report += f"""

---

## 🏆 종목별 성과 TOP 20

| 순위 | 종목 | 이름 | 거래수 | 승률 | 평균수익률 |
|:---:|:---|:---|---:|---:|---:|
"""
        top_tickers = ticker_stats.sort_values('win_rate', ascending=False).head(20)
        for i, (_, row) in enumerate(top_tickers.iterrows(), 1):
            name_short = row['name'][:10] if row['name'] else '-'
            report += f"| {i} | {row['ticker']} | {name_short} | {int(row['trades'])} | {row['win_rate']:.0f}% | {row['avg_pnl']:+.2f}% |\n"
        
        report += f"""

---

## 📊 상세 거래 내역 (최근 30개)

| # | 종목 | 진입일 | 청산일 | 보유일 | 진입가 | 청산가 | 수익률 | 결과 | 청산사유 |
|:---:|:---|:---|:---|:---:|:---:|:---:|:---:|:---:|:---|
"""
        recent_trades = sorted(trades, key=lambda x: x['entry_date'], reverse=True)[:30]
        for i, trade in enumerate(recent_trades, 1):
            report += f"| {i} | {trade['ticker']} | {trade['entry_date']} | {trade['exit_date']} | {trade['holding_days']} | {trade['entry_price']:,.0f} | {trade['exit_price']:,.0f} | {trade['net_pnl_rate']:+.2f}% | {trade['result']} | {trade['exit_reason']} |\n"
        
        # 파일 저장
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(report)
        
        json_path = output_path.replace('.md', '.json')
        with open(json_path, 'w', encoding='utf-8') as f:
            json.dump({
                'summary': {
                    'total_trades': total_trades,
                    'win_rate': win_rate,
                    'wins': wins,
                    'losses': losses,
                    'profit_factor': profit_factor,
                    'total_return': total_return,
                    'avg_pnl': avg_pnl,
                    'avg_win': avg_win,
                    'avg_loss': avg_loss,
                    'max_win': max_win,
                    'max_loss': max_loss
                },
                'trades': trades,
                'filtered_out': filtered_out
            }, f, ensure_ascii=False, indent=2)
        
        print(f"\n📄 리포트 저장:")
        print(f"   Markdown: {output_path}")
        print(f"   JSON: {json_path}")
        
        return report

def main():
    # 백테스트 객체 생성
    backtest = RSIBBBacktestV2()
    
    # 종목 리스트 조회
    print("📋 종목 리스트 조회 중...")
    stocks = backtest.get_stock_list()
    print(f"   필터 통과 종목: {len(stocks)}개")
    
    if len(stocks) == 0:
        print("❌ 백테스트 대상 종목 없음")
        return
    
    # 테스트용 소규모 실행 (전체 실행 시 주석 해제)
    stocks = stocks[:200]  # 테스트용 200개 (전체 3,548개 중)
    
    # 백테스트 기간
    start_date = '2024-01-01'
    end_date = '2025-03-30'
    
    # 백테스트 실행
    trades, filtered_out = backtest.run_backtest_parallel(
        stocks, start_date, end_date, 
        max_workers=4,
        progress_file='/root/.openclaw/workspace/strg/backtest_progress_v2.json'
    )
    
    # 리포트 생성
    if trades:
        output_path = f'/root/.openclaw/workspace/strg/docs/rsi_bb_backtest_v2_{datetime.now().strftime("%Y%m%d")}.md'
        backtest.generate_report(trades, filtered_out, output_path)
    else:
        print("\n⚠️ 백테스트 결과 없음")
        print(f"   필터링 사유: {filtered_out}")

if __name__ == '__main__':
    main()
