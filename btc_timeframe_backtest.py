#!/usr/bin/env python3
"""
BTC A+ 백테스터 - 다양한 시간대 지원
- timeframe: 1d, 4h, 1h, 30m, 15m
"""

import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from dataclasses import dataclass
from typing import List, Dict, Optional
import os
import json

# CCXT 없으면 설치 안내
try:
    import ccxt
except ImportError:
    print("ccxt 설치 필요: pip install ccxt")
    import sys
    sys.exit(1)

REPORT_DIR = "/root/.openclaw/workspace/sub/reports"

@dataclass
class BTCTimeframeResult:
    timeframe: str  # '1d', '4h', '1h', etc.
    entry_time: str
    exit_time: str
    signal_type: str
    entry_price: float
    exit_price: float
    pnl: float
    exit_reason: str
    holding_bars: int

class BTCTimeframeBacktest:
    def __init__(self, timeframe='4h', leverage=1.0, start_date='2020-01-01', end_date='2025-03-28'):
        self.timeframe = timeframe
        self.leverage = leverage
        self.start_date = start_date
        self.end_date = end_date
        self.exchange = ccxt.binance({'enableRateLimit': True})
        
    def fetch_data(self) -> pd.DataFrame:
        """Binance에서 OHLCV 데이터 가져오기"""
        print(f"📊 Binance에서 BTC/USDT {self.timeframe} 데이터 로드 중...")
        
        since = self.exchange.parse8601(f'{self.start_date}T00:00:00Z')
        
        all_ohlcv = []
        while since < self.exchange.parse8601(f'{self.end_date}T00:00:00Z'):
            try:
                ohlcv = self.exchange.fetch_ohlcv('BTC/USDT', self.timeframe, since, limit=1000)
                if not ohlcv:
                    break
                all_ohlcv.extend(ohlcv)
                since = ohlcv[-1][0] + 1
                print(f"   {len(all_ohlcv)}개 봉 수집...", end='\r')
            except Exception as e:
                print(f"   오류: {e}")
                break
        
        if not all_ohlcv:
            raise ValueError("데이터를 가져올 수 없습니다")
        
        df = pd.DataFrame(all_ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
        df['date'] = pd.to_datetime(df['timestamp'], unit='ms').dt.strftime('%Y-%m-%d %H:%M')
        
        print(f"\n   총 {len(df)}개 {self.timeframe}봉 로드 완료")
        return df
    
    def calculate_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        """지표 계산 (시간대별 조정)"""
        df = df.copy()
        
        # ATR
        df['tr1'] = df['high'] - df['low']
        df['tr2'] = abs(df['high'] - df['close'].shift(1))
        df['tr3'] = abs(df['low'] - df['close'].shift(1))
        df['tr'] = df[['tr1', 'tr2', 'tr3']].max(axis=1)
        df['atr'] = df['tr'].rolling(window=14).mean()
        
        # 시간대별 Swing 피봇 조정
        # 일봉: 5-5, 4시간: 12-12 (2일), 1시간: 24-24 (1일)
        if self.timeframe == '1d':
            left = right = 5
        elif self.timeframe == '4h':
            left = right = 6  # 24시간 = 6개 4시간봉
        elif self.timeframe == '1h':
            left = right = 12  # 12시간
        else:
            left = right = 10
        
        df['pivot_high'] = 0
        df['pivot_low'] = 0
        
        for i in range(left, len(df) - right):
            is_high = all(df.iloc[i]['high'] >= df.iloc[i-j]['high'] for j in range(1, left+1)) and \
                      all(df.iloc[i]['high'] >= df.iloc[i+j]['high'] for j in range(1, right+1))
            if is_high:
                df.iloc[i, df.columns.get_loc('pivot_high')] = 1
            
            is_low = all(df.iloc[i]['low'] <= df.iloc[i-j]['low'] for j in range(1, left+1)) and \
                     all(df.iloc[i]['low'] <= df.iloc[i+j]['low'] for j in range(1, right+1))
            if is_low:
                df.iloc[i, df.columns.get_loc('pivot_low')] = 1
        
        # Swing Areas
        width_mult = 1.0
        df['resistance_upper'] = np.where(df['pivot_high'] == 1, df['high'], np.nan)
        df['resistance_lower'] = np.where(df['pivot_high'] == 1, df['high'] - df['atr'] * width_mult, np.nan)
        df['support_upper'] = np.where(df['pivot_low'] == 1, df['low'] + df['atr'] * width_mult, np.nan)
        df['support_lower'] = np.where(df['pivot_low'] == 1, df['low'], np.nan)
        
        df['resistance_upper'] = df['resistance_upper'].ffill()
        df['resistance_lower'] = df['resistance_lower'].ffill()
        df['support_upper'] = df['support_upper'].ffill()
        df['support_lower'] = df['support_lower'].ffill()
        
        # Support Retest
        df['support_broken'] = df['low'] < df['support_lower']
        df['support_broken'] = df['support_broken'].rolling(window=20).max()
        df['in_support'] = (df['close'] >= df['support_lower']) & (df['close'] <= df['support_upper'])
        df['support_retest'] = df['in_support'] & df['support_broken']
        
        # Resistance Retest
        df['resistance_broken'] = df['high'] > df['resistance_upper']
        df['resistance_broken'] = df['resistance_broken'].rolling(window=20).max()
        df['in_resistance'] = (df['close'] >= df['resistance_lower']) & (df['close'] <= df['resistance_upper'])
        df['resistance_retest'] = df['in_resistance'] & df['resistance_broken']
        
        # CCI OBV
        df['price_change'] = df['close'].diff()
        df['obv_direction'] = np.where(df['price_change'] > 0, 1, np.where(df['price_change'] < 0, -1, 0))
        df['obv'] = (df['obv_direction'] * df['volume']).cumsum()
        
        tp = (df['high'] + df['low'] + df['close']) / 3
        sma_tp = tp.rolling(window=20).mean()
        mean_dev = tp.rolling(window=20).apply(lambda x: np.mean(np.abs(x - x.mean())))
        df['cci'] = (tp - sma_tp) / (0.015 * mean_dev)
        df['obv_color'] = np.where(df['cci'] >= 0, 'GREEN', 'RED')
        df['obv_ema'] = df['obv'].ewm(span=13, adjust=False).mean()
        df['obv_cross_up'] = (df['obv'] > df['obv_ema']) & (df['obv'].shift(1) <= df['obv_ema'].shift(1))
        df['obv_cross_down'] = (df['obv'] < df['obv_ema']) & (df['obv'].shift(1) >= df['obv_ema'].shift(1))
        
        # PMO (시간대별 조정)
        def custom_smooth(series, period):
            result = series.copy()
            multiplier = 2 / period
            for i in range(1, len(series)):
                result.iloc[i] = (series.iloc[i] - result.iloc[i-1]) * multiplier + result.iloc[i-1]
            return result
        
        df['roc'] = ((df['close'] / df['close'].shift(1)) * 100) - 100
        df['roc'] = df['roc'].fillna(0)
        df['roc_smooth1'] = custom_smooth(df['roc'], 35)
        df['roc_10x'] = df['roc_smooth1'] * 10
        df['pmo'] = custom_smooth(df['roc_10x'], 20)
        df['pmo_signal'] = df['pmo'].ewm(span=10, adjust=False).mean()
        
        # PMO 레벨 조정 (BTC 변동성 고려)
        special_level = 1.7
        df['pmo_above_17'] = df['pmo'] > special_level
        df['pmo_below_minus17'] = df['pmo'] < -special_level
        df['pmo_17_cross_up'] = (df['pmo'] > special_level) & (df['pmo'].shift(1) <= special_level)
        df['pmo_17_cross_down'] = (df['pmo'] < -special_level) & (df['pmo'].shift(1) >= -special_level)
        df['pmo_cross_up'] = (df['pmo'] > df['pmo_signal']) & (df['pmo'].shift(1) <= df['pmo_signal'].shift(1))
        df['pmo_cross_down'] = (df['pmo'] < df['pmo_signal']) & (df['pmo'].shift(1) >= df['pmo_signal'].shift(1))
        
        return df
    
    def find_signals(self, df: pd.DataFrame) -> List[Dict]:
        """A+ 신호 찾기"""
        signals = []
        
        for i in range(50, len(df) - 30):
            row = df.iloc[i]
            
            # LONG
            swing_long = bool(row['support_retest']) and (row['close'] > row['open'])
            cci_obv_long = bool(row['obv_cross_up']) and (row['obv_color'] == 'GREEN')
            pmo_long = bool(row['pmo_17_cross_up']) or (bool(row['pmo_cross_up']) and bool(row['pmo_above_17']))
            
            if swing_long and cci_obv_long and pmo_long:
                signals.append({
                    'index': i,
                    'time': row['date'],
                    'type': 'LONG',
                    'entry': row['close'],
                    'stop': row['low'] * 0.995,
                    'target': row['close'] + (row['close'] - row['low'] * 0.995) * 2
                })
            
            # SHORT
            swing_short = bool(row['resistance_retest']) and (row['close'] < row['open'])
            cci_obv_short = bool(row['obv_cross_down']) and (row['obv_color'] == 'RED')
            pmo_short = bool(row['pmo_17_cross_down']) or (bool(row['pmo_cross_down']) and bool(row['pmo_below_minus17']))
            
            if swing_short and cci_obv_short and pmo_short:
                signals.append({
                    'index': i,
                    'time': row['date'],
                    'type': 'SHORT',
                    'entry': row['close'],
                    'stop': row['high'] * 1.005,
                    'target': row['close'] - (row['high'] * 1.005 - row['close']) * 2
                })
        
        return signals
    
    def simulate(self, df: pd.DataFrame, signal: Dict) -> Optional[BTCTimeframeResult]:
        """거래 시뮬레이션"""
        entry_idx = signal['index']
        entry_price = signal['entry']
        stop_loss = signal['stop']
        take_profit = signal['target']
        signal_type = signal['type']
        entry_time = df.iloc[entry_idx]['date']
        
        # 시간대별 보유 기간 조정
        max_bars = {'1d': 20, '4h': 30, '1h': 48, '30m': 60, '15m': 80}.get(self.timeframe, 20)
        exit_idx = min(entry_idx + max_bars, len(df) - 1)
        
        exit_reason = None
        exit_price = None
        exit_time = None
        
        for i in range(entry_idx + 1, exit_idx + 1):
            row = df.iloc[i]
            
            if signal_type == 'LONG':
                if row['low'] <= stop_loss:
                    exit_price = stop_loss
                    exit_reason = 'SL'
                    exit_time = row['date']
                    break
                elif row['high'] >= take_profit:
                    exit_price = take_profit
                    exit_reason = 'TP'
                    exit_time = row['date']
                    break
            else:
                if row['high'] >= stop_loss:
                    exit_price = stop_loss
                    exit_reason = 'SL'
                    exit_time = row['date']
                    break
                elif row['low'] <= take_profit:
                    exit_price = take_profit
                    exit_reason = 'TP'
                    exit_time = row['date']
                    break
        
        if exit_reason is None:
            exit_price = df.iloc[exit_idx]['close']
            exit_reason = 'TIME'
            exit_time = df.iloc[exit_idx]['date']
        
        if signal_type == 'LONG':
            pnl = (exit_price - entry_price) / entry_price * 100 * self.leverage
        else:
            pnl = (entry_price - exit_price) / entry_price * 100 * self.leverage
        
        holding_bars = exit_idx - entry_idx
        
        return BTCTimeframeResult(
            timeframe=self.timeframe,
            entry_time=entry_time,
            exit_time=exit_time,
            signal_type=signal_type,
            entry_price=entry_price,
            exit_price=exit_price,
            pnl=pnl,
            exit_reason=exit_reason,
            holding_bars=holding_bars
        )
    
    def run(self) -> List[BTCTimeframeResult]:
        """백테스트 실행"""
        print(f"\n{'='*70}")
        print(f"🪙 BTC A+ 백테스트 [{self.timeframe}]")
        print(f"{'='*70}")
        print(f"레버리지: {self.leverage}x | 양방향 (LONG/SHORT)\n")
        
        df = self.fetch_data()
        df = self.calculate_indicators(df)
        signals = self.find_signals(df)
        
        print(f"🔍 A+ 신호: {len(signals)}개 발견\n")
        
        results = []
        for signal in signals:
            result = self.simulate(df, signal)
            if result:
                results.append(result)
        
        return results

def test_multiple_timeframes():
    """여러 시간대 테스트"""
    timeframes = ['1d', '4h', '1h']
    all_results = {}
    
    for tf in timeframes:
        try:
            backtest = BTCTimeframeBacktest(timeframe=tf, leverage=1.0)
            results = backtest.run()
            all_results[tf] = results
            
            if results:
                pnls = [r.pnl for r in results]
                wins = len([r for r in results if r.pnl > 0])
                print(f"\n📊 {tf} 결과:")
                print(f"   거래: {len(results)}건 | 승률: {wins/len(results)*100:.1f}%")
                print(f"   총 수익: {sum(pnls):.2f}% | 평균: {np.mean(pnls):.2f}%")
            else:
                print(f"\n⚠️ {tf}: 신호 없음")
                
        except Exception as e:
            print(f"\n❌ {tf} 오류: {e}")
            all_results[tf] = []
    
    return all_results

def generate_comparison_report(all_results: Dict):
    """시간대 비교 리포트 생성"""
    date_str = datetime.now().strftime('%Y-%m-%d')
    
    html = f"""<!DOCTYPE html>
<html lang="ko">
<head>
    <meta charset="UTF-8">
    <title>BTC A+ 시간대 비교 - {date_str}</title>
    <style>
        body {{ font-family: 'Segoe UI', sans-serif; background: #1a1a2e; color: #eee; padding: 20px; }}
        .container {{ max-width: 1200px; margin: 0 auto; }}
        .header {{ text-align: center; padding: 40px; background: linear-gradient(135deg, #f7931a, #ffd700); border-radius: 15px; margin-bottom: 30px; }}
        .header h1 {{ color: #1a1a2e; font-size: 2.5em; }}
        .tf-section {{ background: rgba(255,255,255,0.05); padding: 25px; border-radius: 12px; margin-bottom: 20px; }}
        .tf-section h3 {{ color: #f7931a; margin-bottom: 15px; font-size: 1.5em; }}
        table {{ width: 100%; border-collapse: collapse; font-size: 0.9em; margin-top: 15px; }}
        th, td {{ padding: 10px; text-align: center; border-bottom: 1px solid rgba(255,255,255,0.1); }}
        th {{ color: #f7931a; }}
        .profit {{ color: #4ecca3; font-weight: bold; }} .loss {{ color: #ff6b6b; font-weight: bold; }}
        .long {{ background: #4ecca3; color: #000; padding: 3px 8px; border-radius: 3px; }}
        .short {{ background: #ff6b6b; color: #000; padding: 3px 8px; border-radius: 3px; }}
        .summary {{ display: grid; grid-template-columns: repeat(4, 1fr); gap: 10px; margin-bottom: 15px; }}
        .sum-card {{ background: rgba(0,0,0,0.2); padding: 15px; border-radius: 8px; text-align: center; }}
        .sum-card .num {{ font-size: 1.8em; font-weight: bold; color: #f7931a; }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🪙 BTC A+ 시간대 비교</h1>
            <div style="color: #333; margin-top: 10px;">Binance BTC/USDT | 롱/숏 양방향</div>
        </div>
"""
    
    for tf, results in all_results.items():
        if not results:
            continue
            
        pnls = [r.pnl for r in results]
        wins = len([r for r in results if r.pnl > 0])
        win_rate = wins / len(results) * 100 if results else 0
        total = sum(pnls)
        avg = np.mean(pnls) if pnls else 0
        longs = len([r for r in results if r.signal_type == 'LONG'])
        shorts = len([r for r in results if r.signal_type == 'SHORT'])
        
        html += f"""
        <div class="tf-section">
            <h3>⏰ {tf} 시간대</h3>
            <div class="summary">
                <div class="sum-card"><div class="num">{len(results)}</div><div>총 거래</div></div>
                <div class="sum-card"><div class="num" style="color: {'#4ecca3' if total > 0 else '#ff6b6b'};">{total:+.1f}%</div><div>총 수익</div></div>
                <div class="sum-card"><div class="num">{win_rate:.0f}%</div><div>승률</div></div>
                <div class="sum-card"><div class="num">{avg:+.1f}%</div><div>평균</div></div>
            </div>
            <div style="margin-bottom: 10px;">
                <span class="long">LONG {longs}건</span> | <span class="short">SHORT {shorts}건</span>
            </div>
            <table>
                <tr><th>시간</th><th>포지션</th><th>진입가</th><th>청산가</th><th>수익률</th><th>청산</th><th>보유봉</th></tr>
"""
        for r in sorted(results, key=lambda x: x.entry_time, reverse=True)[:20]:
            pnl_class = 'profit' if r.pnl > 0 else 'loss'
            pos_class = 'long' if r.signal_type == 'LONG' else 'short'
            html += f"<tr><td>{r.entry_time}</td><td><span class='{pos_class}'>{r.signal_type}</span></td><td>${r.entry_price:,.0f}</td><td>${r.exit_price:,.0f}</td><td class='{pnl_class}'>{r.pnl:+.2f}%</td><td>{r.exit_reason}</td><td>{r.holding_bars}봉</td></tr>"
        
        html += "</table></div>"
    
    html += """
        <div style="text-align: center; padding: 30px; color: #666;">
            <p>⚠️ 과거 성과가 미래 수익을 보장하지 않습니다.</p>
        </div>
    </div>
</body>
</html>"""
    
    os.makedirs(REPORT_DIR, exist_ok=True)
    html_path = f"{REPORT_DIR}/BTC_TIMEFRAME_COMPARISON_{date_str}.html"
    with open(html_path, 'w', encoding='utf-8') as f:
        f.write(html)
    
    return html_path

def main():
    print("🪙 BTC 다중 시간대 백테스트 시작...")
    print("테스트: 1d, 4h, 1h")
    
    all_results = test_multiple_timeframes()
    
    print(f"\n{'='*70}")
    print("✅ 모든 시간대 테스트 완료!")
    print(f"{'='*70}")
    
    # 요약
    print("\n📊 시간대별 요약:")
    for tf, results in all_results.items():
        if results:
            pnls = [r.pnl for r in results]
            wins = len([r for r in results if r.pnl > 0])
            print(f"  {tf}: {len(results)}건, 승률 {wins/len(results)*100:.1f}%, 총 {sum(pnls):+.2f}%")
        else:
            print(f"  {tf}: 신호 없음")
    
    # 리포트 생성
    print("\n📄 비교 리포트 생성 중...")
    html_path = generate_comparison_report(all_results)
    print(f"    {html_path}")
    
    os.system(f"cp {html_path} /root/.openclaw/workspace/strg/docs/")
    print("    GitHub Pages 배포 완료")
    
    print(f"\n{'='*70}")

if __name__ == "__main__":
    main()
