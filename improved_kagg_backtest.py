#!/usr/bin/env python3
"""
KAGGRESSIVE 개선 전략 백테스트 (v1.1)
- 진입 기준: 70점+ (기존 65점)
- RSI 필터: 40~60
- 거래량: 20일 평균 1.5배+
- 가격: 5일 이동평균 위
- ADX: 20+ (추세 강도)
- 목표 R:R: 1:3
"""

import sys
sys.path.insert(0, '/root/.openclaw/workspace/strg')

import sqlite3
import json
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from fdr_wrapper import get_price


class ImprovedKaggBacktest:
    """개선된 KAGGRESSIVE 백테스트"""
    
    def __init__(self):
        self.conn = sqlite3.connect('data/pivot_strategy.db')
        self.trades = []
        
    def calculate_rsi(self, prices, period=14):
        """RSI 계산"""
        if len(prices) < period + 1:
            return None
        
        deltas = np.diff(prices)
        gains = np.where(deltas > 0, deltas, 0)
        losses = np.where(deltas < 0, -deltas, 0)
        
        avg_gain = np.mean(gains[-period:])
        avg_loss = np.mean(losses[-period:])
        
        if avg_loss == 0:
            return 100
        
        rs = avg_gain / avg_loss
        rsi = 100 - (100 / (1 + rs))
        return rsi
    
    def calculate_adx(self, high, low, close, period=14):
        """ADX 계산 (단순화)"""
        if len(high) < period + 1:
            return None
        
        # True Range
        tr1 = high[-1] - low[-1]
        tr2 = abs(high[-1] - close[-2])
        tr3 = abs(low[-1] - close[-2])
        tr = max(tr1, tr2, tr3)
        
        # Directional Movement
        plus_dm = high[-1] - high[-2] if high[-1] > high[-2] else 0
        minus_dm = low[-2] - low[-1] if low[-1] < low[-2] else 0
        
        if plus_dm > minus_dm:
            minus_dm = 0
        else:
            plus_dm = 0
        
        # Simplified ADX (approximation)
        atr = np.mean([max(h-l, abs(h-c), abs(l-c)) for h, l, c in zip(high[-period:], low[-period:], close[-period:])])
        if atr == 0:
            return 0
        
        dx = abs(plus_dm - minus_dm) / (plus_dm + minus_dm + 0.001) * 100
        return dx
    
    def calculate_sma(self, prices, period):
        """단순 이동평균"""
        if len(prices) < period:
            return None
        return np.mean(prices[-period:])
    
    def check_entry_conditions(self, symbol, date_str):
        """개선된 진입 조건 확인 (단계적 필터)"""
        try:
            # 60일치 데이터 로드
            end_date = datetime.strptime(date_str, '%Y-%m-%d')
            start_date = end_date - timedelta(days=90)
            
            df = get_price(symbol, start_date.strftime('%Y-%m-%d'), date_str)
            if df is None or len(df) < 30:
                return None
            
            # 기술적 지표 계산
            closes = df['Close'].values
            highs = df['High'].values
            lows = df['Low'].values
            volumes = df['Volume'].values
            
            # 1. KAGGRESSIVE 점수 먼저 확인 (65+로 완화)
            from kagg import KAggressiveScanner
            scanner = KAggressiveScanner()
            result = scanner.calculate_kagg_score(symbol, date_str)
            
            if not result or result['kagg_score'] < 65:
                return None
            
            score = result['kagg_score']
            
            # 2. RSI (35~65로 완화)
            rsi = self.calculate_rsi(closes, 14)
            if rsi is None or rsi < 35 or rsi > 65:
                return None
            
            # 3. 거래량 (20일 평균 1.2배+로 완화)
            volume_ma20 = np.mean(volumes[-20:])
            current_volume = volumes[-1]
            if current_volume < volume_ma20 * 1.2:
                return None
            
            # 4. 가격 > 5일 이동평균
            sma5 = self.calculate_sma(closes, 5)
            if sma5 is None or closes[-1] <= sma5:
                return None
            
            # 5. ADX (15+로 완화)
            adx = self.calculate_adx(highs, lows, closes, 14)
            if adx is None or adx < 15:
                return None
            
            return {
                'symbol': symbol,
                'date': date_str,
                'score': score,
                'price': closes[-1],
                'rsi': round(rsi, 1),
                'volume_ratio': round(current_volume / volume_ma20, 2),
                'adx': round(adx, 1),
                'sma5': round(sma5, 0)
            }
            
        except Exception as e:
            return None
    
    def simulate_trade(self, entry_info, hold_days=7):
        """거래 시뮬레이션 (R:R 1:3 목표)"""
        symbol = entry_info['symbol']
        entry_date = datetime.strptime(entry_info['date'], '%Y-%m-%d')
        entry_price = entry_info['price']
        
        # 개선된 손절/목표가 (R:R 1:3)
        stop_loss = entry_price * 0.93  # -7%
        target_price = entry_price * 1.21  # +21% (R:R 1:3)
        
        # 청산일 계산
        exit_date = entry_date + timedelta(days=hold_days)
        
        try:
            # 데이터 로드
            df = get_price(symbol, entry_date.strftime('%Y-%m-%d'), 
                          (exit_date + timedelta(days=5)).strftime('%Y-%m-%d'))
            if df is None or df.empty:
                return None
            
            # 청산일 찾기 (거래일 기준)
            df = df.reset_index()
            if 'Date' in df.columns:
                df['Date'] = pd.to_datetime(df['Date'])
            else:
                df['Date'] = pd.to_datetime(df['index'])
            
            entry_row = df[df['Date'] >= entry_date]
            if entry_row.empty:
                return None
            
            entry_idx = entry_row.index[0]
            exit_idx = min(entry_idx + hold_days, len(df) - 1)
            
            # 보유 기간 데이터
            hold_df = df.iloc[entry_idx:exit_idx+1]
            
            # 손절 체크
            stop_triggered = False
            target_triggered = False
            actual_exit_price = hold_df['Close'].iloc[-1]
            actual_exit_date = hold_df['Date'].iloc[-1]
            exit_reason = '보유만기'
            
            for idx, row in hold_df.iterrows():
                if idx == entry_idx:
                    continue
                    
                # 손절가 도달
                if row['Low'] <= stop_loss:
                    actual_exit_price = stop_loss
                    actual_exit_date = row['Date']
                    exit_reason = '손절'
                    stop_triggered = True
                    break
                
                # 목표가 도달
                if row['High'] >= target_price:
                    actual_exit_price = target_price
                    actual_exit_date = row['Date']
                    exit_reason = '목표도달'
                    target_triggered = True
                    break
            
            # 수익률 계산
            return_pct = ((actual_exit_price - entry_price) / entry_price) * 100
            
            return {
                'symbol': symbol,
                'entry_date': entry_date.strftime('%Y-%m-%d'),
                'exit_date': actual_exit_date.strftime('%Y-%m-%d') if isinstance(actual_exit_date, pd.Timestamp) else entry_info['date'],
                'entry_price': round(entry_price, 0),
                'exit_price': round(actual_exit_price, 0),
                'return_pct': round(return_pct, 2),
                'exit_reason': exit_reason,
                'score': entry_info['score'],
                'rsi': entry_info['rsi'],
                'adx': entry_info['adx'],
                'volume_ratio': entry_info['volume_ratio']
            }
            
        except Exception as e:
            return None
    
    def run_backtest(self, test_dates=None):
        """백테스트 실행"""
        if test_dates is None:
            # 테스트 기간: 2026년 1월~3월
            test_dates = []
            start = datetime(2026, 1, 2)
            end = datetime(2026, 3, 20)
            
            cursor = self.conn.cursor()
            cursor.execute("""
                SELECT DISTINCT date FROM stock_prices 
                WHERE date BETWEEN ? AND ?
                ORDER BY date
            """, (start.strftime('%Y-%m-%d'), end.strftime('%Y-%m-%d')))
            
            test_dates = [row[0] for row in cursor.fetchall()]
        
        print(f"📅 백테스트 기간: {test_dates[0]} ~ {test_dates[-1]} ({len(test_dates)}거래일)")
        print(f"🎯 진입 조건: KAGGRESSIVE 70+ / RSI 40~60 / 거래량 1.5x+ / ADX 20+ / 가격 > 5일선")
        print(f"📊 R:R 목표: 1:3 (손절 -7%, 목표 +21%)")
        print("=" * 70)
        
        all_trades = []
        
        for date_str in test_dates[::5]:  # 5일 간격으로 샘플링 (속도)
            print(f"\n🔍 {date_str} 스캔 중...")
            
            # 종목 가져오기
            cursor = self.conn.cursor()
            cursor.execute("""
                SELECT DISTINCT s.symbol, s.name
                FROM stock_info s
                JOIN stock_prices p ON s.symbol = p.symbol AND p.date = ?
                LIMIT 200
            """, (date_str,))
            
            symbols = cursor.fetchall()
            
            day_entries = []
            for sym, name in symbols:
                result = self.check_entry_conditions(sym, date_str)
                if result:
                    result['name'] = name
                    day_entries.append(result)
            
            if day_entries:
                # 상위 3개만 선택
                day_entries = sorted(day_entries, key=lambda x: x['score'], reverse=True)[:3]
                print(f"   ✓ {len(day_entries)}개 종목 진입")
                
                for entry in day_entries:
                    trade = self.simulate_trade(entry)
                    if trade:
                        trade['name'] = entry['name']
                        all_trades.append(trade)
                        emoji = '📈' if trade['return_pct'] > 0 else '📉'
                        print(f"     {emoji} {entry['name']}: {trade['return_pct']:+.2f}% ({trade['exit_reason']})")
        
        self.trades = all_trades
        return self.generate_report()
    
    def generate_report(self):
        """백테스트 리포트 생성"""
        if not self.trades:
            return "거래 없음"
        
        df = pd.DataFrame(self.trades)
        
        # 통계
        total_trades = len(df)
        wins = len(df[df['return_pct'] > 0])
        losses = len(df[df['return_pct'] <= 0])
        win_rate = (wins / total_trades) * 100 if total_trades > 0 else 0
        
        avg_return = df['return_pct'].mean()
        total_return = df['return_pct'].sum()
        max_profit = df['return_pct'].max()
        max_loss = df['return_pct'].min()
        
        # R:R 분석
        avg_win = df[df['return_pct'] > 0]['return_pct'].mean() if wins > 0 else 0
        avg_loss = abs(df[df['return_pct'] <= 0]['return_pct'].mean()) if losses > 0 else 0
        rr_ratio = avg_win / avg_loss if avg_loss > 0 else 0
        
        report = {
            'total_trades': total_trades,
            'wins': wins,
            'losses': losses,
            'win_rate': round(win_rate, 1),
            'avg_return': round(avg_return, 2),
            'total_return': round(total_return, 2),
            'max_profit': round(max_profit, 2),
            'max_loss': round(max_loss, 2),
            'avg_win': round(avg_win, 2),
            'avg_loss': round(avg_loss, 2),
            'rr_ratio': round(rr_ratio, 2),
            'trades': self.trades
        }
        
        return report
    
    def save_report(self, filename='improved_kagg_backtest.json'):
        """리포트 저장"""
        report = self.generate_report()
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(report, f, ensure_ascii=False, indent=2)
        return report


if __name__ == '__main__':
    print("=" * 70)
    print("🔥 KAGGRESSIVE 개선 전략 백테스트 (v1.1)")
    print("=" * 70)
    
    backtest = ImprovedKaggBacktest()
    
    # 테스트 기간
    test_dates = []
    start = datetime(2026, 1, 2)
    for i in range(12):  # 12주
        test_dates.append((start + timedelta(days=i*7)).strftime('%Y-%m-%d'))
    
    report = backtest.run_backtest(test_dates)
    
    print("\n" + "=" * 70)
    print("📊 최종 백테스트 결과")
    print("=" * 70)
    
    if isinstance(report, dict):
        print(f"\n📈 거래 통계:")
        print(f"   총 거래: {report['total_trades']}회")
        print(f"   승률: {report['win_rate']}% ({report['wins']}승 / {report['losses']}패)")
        print(f"\n💰 수익 분석:")
        print(f"   평균 수익률: {report['avg_return']:+.2f}%")
        print(f"   총 수익률: {report['total_return']:+.2f}%")
        print(f"   최고 수익: {report['max_profit']:+.2f}%")
        print(f"   최대 손실: {report['max_loss']:+.2f}%")
        print(f"\n📊 R:R 분석:")
        print(f"   평균 수익: +{report['avg_win']:.2f}%")
        print(f"   평균 손실: -{report['avg_loss']:.2f}%")
        print(f"   R:R 비율: 1:{report['rr_ratio']:.2f}")
        
        # 저장
        backtest.save_report('docs/improved_kagg_backtest.json')
        print(f"\n✅ 리포트 저장: docs/improved_kagg_backtest.json")
    else:
        print(report)
