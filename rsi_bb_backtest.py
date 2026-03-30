#!/usr/bin/env python3
"""
RSI + 볼린저밴드 단타 전략 백테스트
- 진입: RSI 30↓ + BB 하단 터치 + 거래량 1.5배↑
- 손절: -2%
- 익절: +3%
- 최대 보유: 3일 (단타)
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import sqlite3
import json
import os
import sys

# Add parent path for fdr_wrapper
sys.path.insert(0, '/root/.openclaw/workspace/strg')

try:
    from fdr_wrapper import get_price
except ImportError:
    print("❌ fdr_wrapper not found. Using yfinance fallback.")
    get_price = None

class RSIBBBacktest:
    def __init__(self, initial_capital=10000000, fee_rate=0.015):
        self.initial_capital = initial_capital
        self.fee_rate = fee_rate / 100  # 0.015% → 0.00015
        self.sl_rate = 0.02  # 손절 -2%
        self.tp_rate = 0.03  # 익절 +3%
        self.max_hold_days = 3  # 최대 보유 3일
        
        # 볼린저밴드 설정
        self.bb_period = 20
        self.bb_std = 2
        
        # RSI 설정
        self.rsi_period = 14
        
        # 거래량 설정
        self.volume_ma_period = 20
        self.volume_threshold = 1.5  # 1.5배
        
    def calculate_rsi(self, prices, period=14):
        """RSI 계산"""
        delta = prices.diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
        rs = gain / loss
        rsi = 100 - (100 / (1 + rs))
        return rsi
    
    def calculate_bollinger(self, df):
        """볼린저밴드 계산"""
        df['BB_Middle'] = df['Close'].rolling(window=self.bb_period).mean()
        df['BB_Std'] = df['Close'].rolling(window=self.bb_period).std()
        df['BB_Upper'] = df['BB_Middle'] + (df['BB_Std'] * self.bb_std)
        df['BB_Lower'] = df['BB_Middle'] - (df['BB_Std'] * self.bb_std)
        return df
    
    def calculate_volume_ma(self, df):
        """거래량 이동평균"""
        df['Volume_MA'] = df['Volume'].rolling(window=self.volume_ma_period).mean()
        df['Volume_Ratio'] = df['Volume'] / df['Volume_MA']
        return df
    
    def generate_signals(self, df):
        """매매 신호 생성"""
        df = df.copy()
        
        # RSI 계산
        df['RSI'] = self.calculate_rsi(df['Close'], self.rsi_period)
        
        # 볼린저밴드 계산
        df = self.calculate_bollinger(df)
        
        # 거래량 계산
        df = self.calculate_volume_ma(df)
        
        # 신호 조건
        # 매수: RSI <= 30 AND 종가 <= BB 하단 AND 거래량 >= 1.5배
        df['Buy_Signal'] = (
            (df['RSI'] <= 30) & 
            (df['Close'] <= df['BB_Lower']) &
            (df['Volume_Ratio'] >= self.volume_threshold)
        )
        
        # 매도 신호는 다음 캔들에서 확인 (역전 패턴)
        df['Sell_Signal'] = (
            (df['RSI'] >= 70) & 
            (df['Close'] >= df['BB_Upper'])
        )
        
        return df
    
    def backtest_stock(self, ticker, start_date, end_date):
        """단일 종목 백테스트"""
        try:
            # 데이터 수집
            if get_price:
                df = get_price(ticker, start_date, end_date)
            else:
                import FinanceDataReader as fdr
                df = fdr.DataReader(ticker, start_date, end_date)
            
            if df is None or len(df) < 50:
                return None
            
            # 신호 생성
            df = self.generate_signals(df)
            
            # 백테스트 시뮬레이션
            trades = []
            position = None
            entry_price = 0
            entry_date = None
            
            for i in range(self.rsi_period + 10, len(df)):
                date = df.index[i]
                row = df.iloc[i]
                
                # 포지션 없음 - 매수 신호 확인
                if position is None:
                    if row['Buy_Signal']:
                        position = 'LONG'
                        entry_price = row['Close']
                        entry_date = date
                        entry_rsi = row['RSI']
                        entry_bb_lower = row['BB_Lower']
                        entry_volume_ratio = row['Volume_Ratio']
                
                # 포지션 보유 중 - 청산 조건 확인
                elif position == 'LONG':
                    current_price = row['Close']
                    holding_days = (date - entry_date).days
                    
                    # 수익률 계산
                    pnl_rate = (current_price - entry_price) / entry_price
                    
                    # 청산 조건
                    exit_reason = None
                    
                    if pnl_rate <= -self.sl_rate:  # 손절 -2%
                        exit_reason = 'STOP_LOSS'
                    elif pnl_rate >= self.tp_rate:  # 익절 +3%
                        exit_reason = 'TAKE_PROFIT'
                    elif row['Sell_Signal']:  # 매도 신호
                        exit_reason = 'SELL_SIGNAL'
                    elif holding_days >= self.max_hold_days:  # 최대 보유일
                        exit_reason = 'TIME_EXIT'
                    
                    if exit_reason:
                        # 거래 기록
                        fee = (entry_price + current_price) * self.fee_rate
                        net_pnl = (current_price - entry_price) - fee
                        net_pnl_rate = net_pnl / entry_price
                        
                        trades.append({
                            'ticker': ticker,
                            'entry_date': entry_date.strftime('%Y-%m-%d'),
                            'exit_date': date.strftime('%Y-%m-%d'),
                            'entry_price': round(entry_price, 2),
                            'exit_price': round(current_price, 2),
                            'holding_days': holding_days,
                            'entry_rsi': round(entry_rsi, 2),
                            'entry_volume_ratio': round(entry_volume_ratio, 2),
                            'exit_reason': exit_reason,
                            'pnl_rate': round(pnl_rate * 100, 2),
                            'net_pnl_rate': round(net_pnl_rate * 100, 2),
                            'result': 'WIN' if net_pnl > 0 else 'LOSS'
                        })
                        
                        position = None
            
            return trades
            
        except Exception as e:
            print(f"   ❌ {ticker} 오류: {e}")
            return None
    
    def run_backtest(self, tickers, start_date, end_date, progress_file=None):
        """다중 종목 백테스트"""
        all_trades = []
        
        print(f"\n📊 RSI+BB 단타 백테스트 시작")
        print(f"   기간: {start_date} ~ {end_date}")
        print(f"   종목 수: {len(tickers)}")
        print(f"   손절: -{self.sl_rate*100}% / 익절: +{self.tp_rate*100}%")
        print("="*70)
        
        for i, ticker in enumerate(tickers, 1):
            print(f"\n[{i}/{len(tickers)}] {ticker} 분석 중...", end=' ')
            trades = self.backtest_stock(ticker, start_date, end_date)
            
            if trades:
                all_trades.extend(trades)
                wins = sum(1 for t in trades if t['result'] == 'WIN')
                print(f"✅ {len(trades)}거래 (승: {wins}, 패: {len(trades)-wins})")
            else:
                print("❌ 신호 없음")
            
            # 진행상황 저장
            if progress_file and i % 10 == 0:
                self._save_progress(progress_file, i, len(tickers), all_trades)
        
        return all_trades
    
    def _save_progress(self, filepath, current, total, trades):
        """중간 진행상황 저장"""
        progress = {
            'current': current,
            'total': total,
            'trades': len(trades),
            'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        }
        with open(filepath, 'w') as f:
            json.dump(progress, f, indent=2)
    
    def generate_report(self, trades, output_path):
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
        
        # 누적 수익률 (복리 계산)
        cumulative = (1 + df['net_pnl_rate'] / 100).cumprod()
        total_return = (cumulative.iloc[-1] - 1) * 100 if len(cumulative) > 0 else 0
        
        # 종목별 분석
        ticker_stats = df.groupby('ticker').agg({
            'result': lambda x: (x == 'WIN').sum() / len(x) * 100,
            'net_pnl_rate': 'mean'
        }).round(2)
        ticker_stats.columns = ['win_rate', 'avg_pnl']
        
        # 청산 이유 분석
        exit_stats = df.groupby('exit_reason').size()
        
        # 리포트 출력
        report = f"""
# 📊 RSI + 볼린저밴드 단타 백테스트 리포트
**생성일시:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

---

## 📈 종합 성과

| 항목 | 값 |
|:---|---:|
| **총 거래 횟수** | {total_trades} |
| **승률** | {win_rate:.1f}% |
| **승 / 패** | {wins} / {losses} |
| **총 수익률** | +{total_return:.2f}% |
| **평균 수익/거래** | {avg_pnl:.2f}% |
| **평균 수익 (승)** | +{avg_win:.2f}% |
| **평균 손실 (패)** | {avg_loss:.2f}% |
| **최대 수익** | +{max_win:.2f}% |
| **최대 손실** | {max_loss:.2f}% |
| **손익비** | 1:{abs(avg_win/avg_loss):.1f} |

---

## 📋 청산 이유 분석

| 청산 이유 | 횟수 | 비율 |
|:---|---:|---:|
"""
        for reason, count in exit_stats.items():
            pct = count / total_trades * 100
            report += f"| {reason} | {count} | {pct:.1f}% |\n"
        
        report += f"""

---

## 🏆 종목별 성과 TOP 10

| 종목 | 승률 | 평균 수익률 |
|:---|---:|---:|
"""
        top_tickers = ticker_stats.sort_values('win_rate', ascending=False).head(10)
        for ticker, row in top_tickers.iterrows():
            report += f"| {ticker} | {row['win_rate']:.1f}% | {row['avg_pnl']:+.2f}% |\n"
        
        report += f"""

---

## 📊 상세 거래 내역

| # | 종목 | 진입일 | 청산일 | 보유일 | 진입가 | 청산가 | 수익률 | 결과 | 청산사유 |
|:---:|:---|:---|:---|:---:|:---:|:---:|:---:|:---:|:---|
"""
        for i, trade in enumerate(trades[:50], 1):  # 상위 50개만
            report += f"| {i} | {trade['ticker']} | {trade['entry_date']} | {trade['exit_date']} | {trade['holding_days']} | {trade['entry_price']:,} | {trade['exit_price']:,} | {trade['net_pnl_rate']:+.2f}% | {trade['result']} | {trade['exit_reason']} |\n"
        
        if len(trades) > 50:
            report += f"\n... 외 {len(trades) - 50}개 거래\n"
        
        # 파일 저장
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(report)
        
        # JSON 저장
        json_path = output_path.replace('.md', '.json')
        with open(json_path, 'w', encoding='utf-8') as f:
            json.dump({
                'summary': {
                    'total_trades': total_trades,
                    'win_rate': win_rate,
                    'wins': wins,
                    'losses': losses,
                    'total_return': total_return,
                    'avg_pnl': avg_pnl,
                    'avg_win': avg_win,
                    'avg_loss': avg_loss
                },
                'trades': trades
            }, f, ensure_ascii=False, indent=2)
        
        print(f"\n📄 리포트 저장:")
        print(f"   Markdown: {output_path}")
        print(f"   JSON: {json_path}")
        
        return report

def main():
    # 테스트 종목 (KOSPI 대형주)
    test_tickers = [
        '005930',  # 삼성전자
        '000660',  # SK하이닉스
        '035420',  # NAVER
        '035720',  # 카카오
        '051910',  # LG화학
        '006400',  # 삼성SDI
        '028260',  # 삼성물산
        '012330',  # 현대모비스
        '105560',  # KB금융
        '055550',  # 신한지주
    ]
    
    # 백테스트 기간
    start_date = '2024-01-01'
    end_date = '2025-03-30'
    
    # 백테스트 실행
    backtest = RSIBBBacktest(initial_capital=10000000)
    trades = backtest.run_backtest(test_tickers, start_date, end_date)
    
    # 리포트 생성
    if trades:
        output_path = f'/root/.openclaw/workspace/strg/docs/rsi_bb_backtest_{datetime.now().strftime("%Y%m%d")}.md'
        backtest.generate_report(trades, output_path)
    else:
        print("\n⚠️ 백테스트 결과 없음")

if __name__ == '__main__':
    main()
