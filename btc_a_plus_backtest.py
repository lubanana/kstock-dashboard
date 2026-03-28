#!/usr/bin/env python3
"""
A+ 타점 백테스터 - 비트코인 (BTC/USDT)
롱/숏 공매수/공매도 지원
"""

import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from dataclasses import dataclass
from typing import List, Dict, Optional
import os
import json
import yfinance as yf

REPORT_DIR = "/root/.openclaw/workspace/sub/reports"

@dataclass
class BTCTradeResult:
    entry_date: str
    exit_date: str
    signal_type: str  # 'LONG' or 'SHORT'
    entry_price: float
    exit_price: float
    stop_loss: float
    take_profit: float
    pnl: float  # 수익률 %
    exit_reason: str  # 'TP', 'SL', 'TIME'
    holding_days: int
    leverage: float  # 레버리지

def get_btc_data(start_date: str, end_date: str) -> pd.DataFrame:
    """비트코인 데이터 다운로드 (Yahoo Finance)"""
    print(f"📊 BTC 데이터 다운로드 중... ({start_date} ~ {end_date})")
    
    # Yahoo Finance에서 BTC-USD 데이터 가져오기
    ticker = yf.Ticker("BTC-USD")
    df = ticker.history(start=start_date, end=end_date, interval='1d')
    
    if df.empty:
        raise ValueError("BTC 데이터를 가져올 수 없습니다")
    
    df = df.reset_index()
    df.columns = [c.lower().replace(' ', '_') for c in df.columns]
    df['date'] = pd.to_datetime(df['date']).dt.strftime('%Y-%m-%d')
    
    # 거래량 컬럼명 통일
    if 'volume' not in df.columns and 'volumefrom' in df.columns:
        df['volume'] = df['volumefrom']
    
    print(f"   총 {len(df)}일 데이터 로드 완료")
    return df

def calculate_indicators(df: pd.DataFrame) -> pd.DataFrame:
    """3지표 계산"""
    df = df.copy()
    
    # ATR
    df['tr1'] = df['high'] - df['low']
    df['tr2'] = abs(df['high'] - df['close'].shift(1))
    df['tr3'] = abs(df['low'] - df['close'].shift(1))
    df['tr'] = df[['tr1', 'tr2', 'tr3']].max(axis=1)
    df['atr'] = df['tr'].rolling(window=14).mean()
    df['atr_pct'] = df['atr'] / df['close'] * 100  # ATR %
    
    # Swing Pivots (5-5)
    left = right = 5
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
    
    # PMO
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
    
    special_level = 1.7
    df['pmo_above_17'] = df['pmo'] > special_level
    df['pmo_below_minus17'] = df['pmo'] < -special_level
    df['pmo_17_cross_up'] = (df['pmo'] > special_level) & (df['pmo'].shift(1) <= special_level)
    df['pmo_17_cross_down'] = (df['pmo'] < special_level) & (df['pmo'].shift(1) >= special_level)
    df['pmo_cross_up'] = (df['pmo'] > df['pmo_signal']) & (df['pmo'].shift(1) <= df['pmo_signal'].shift(1))
    df['pmo_cross_down'] = (df['pmo'] < df['pmo_signal']) & (df['pmo'].shift(1) >= df['pmo_signal'].shift(1))
    
    return df

def find_a_plus_signals_btc(df: pd.DataFrame) -> List[Dict]:
    """BTC A+ 신호 찾기 (롱/숏)"""
    signals = []
    
    for i in range(50, len(df) - 30):
        row = df.iloc[i]
        
        # LONG 조건 (3중 확인)
        swing_long = bool(row['support_retest']) and (row['close'] > row['open'])
        cci_obv_long = bool(row['obv_cross_up']) and (row['obv_color'] == 'GREEN')
        pmo_long = bool(row['pmo_17_cross_up']) or (bool(row['pmo_cross_up']) and bool(row['pmo_above_17']))
        
        if swing_long and cci_obv_long and pmo_long:
            signals.append({
                'index': i,
                'date': row['date'],
                'type': 'LONG',
                'entry': row['close'],
                'stop': row['low'] * 0.99,
                'target': row['close'] + (row['close'] - row['low'] * 0.99) * 2
            })
        
        # SHORT 조건 (3중 확인)
        swing_short = bool(row['resistance_retest']) and (row['close'] < row['open'])
        cci_obv_short = bool(row['obv_cross_down']) and (row['obv_color'] == 'RED')
        pmo_short = bool(row['pmo_17_cross_down']) or (bool(row['pmo_cross_down']) and bool(row['pmo_below_minus17']))
        
        if swing_short and cci_obv_short and pmo_short:
            signals.append({
                'index': i,
                'date': row['date'],
                'type': 'SHORT',
                'entry': row['close'],
                'stop': row['high'] * 1.01,
                'target': row['close'] - (row['high'] * 1.01 - row['close']) * 2
            })
    
    return signals

def simulate_trade_btc(df: pd.DataFrame, signal: Dict, leverage: float = 1.0) -> Optional[BTCTradeResult]:
    """BTC 거래 시뮬레이션"""
    entry_idx = signal['index']
    entry_price = signal['entry']
    stop_loss = signal['stop']
    take_profit = signal['target']
    signal_type = signal['type']
    entry_date = df.iloc[entry_idx]['date']
    
    # 최대 14일 보유 (BTC는 변동성 높음)
    max_days = 14
    exit_idx = min(entry_idx + max_days, len(df) - 1)
    
    exit_reason = None
    exit_price = None
    exit_date = None
    
    for i in range(entry_idx + 1, exit_idx + 1):
        row = df.iloc[i]
        high = row['high']
        low = row['low']
        
        if signal_type == 'LONG':
            if low <= stop_loss:
                exit_price = stop_loss
                exit_reason = 'SL'
                exit_date = row['date']
                break
            elif high >= take_profit:
                exit_price = take_profit
                exit_reason = 'TP'
                exit_date = row['date']
                break
        else:  # SHORT
            if high >= stop_loss:
                exit_price = stop_loss
                exit_reason = 'SL'
                exit_date = row['date']
                break
            elif low <= take_profit:
                exit_price = take_profit
                exit_reason = 'TP'
                exit_date = row['date']
                break
    
    if exit_reason is None:
        exit_price = df.iloc[exit_idx]['close']
        exit_reason = 'TIME'
        exit_date = df.iloc[exit_idx]['date']
    
    # PnL 계산 (레버리지 적용)
    if signal_type == 'LONG':
        pnl = (exit_price - entry_price) / entry_price * 100 * leverage
    else:  # SHORT
        pnl = (entry_price - exit_price) / entry_price * 100 * leverage
    
    holding_days = exit_idx - entry_idx
    
    return BTCTradeResult(
        entry_date=entry_date,
        exit_date=exit_date,
        signal_type=signal_type,
        entry_price=entry_price,
        exit_price=exit_price,
        stop_loss=stop_loss,
        take_profit=take_profit,
        pnl=pnl,
        exit_reason=exit_reason,
        holding_days=holding_days,
        leverage=leverage
    )

def run_btc_backtest(start_date: str, end_date: str, leverage: float = 1.0) -> List[BTCTradeResult]:
    """BTC 백테스트 실행"""
    print(f"\n{'='*70}")
    print(f"🪙 BTC A+ 타점 백테스트")
    print(f"{'='*70}")
    print(f"기간: {start_date} ~ {end_date}")
    print(f"레버리지: {leverage}x")
    print(f"포지션: LONG/SHORT 양방향\n")
    
    # 데이터 로드
    df = get_btc_data(start_date, end_date)
    
    # 지표 계산
    print("📊 지표 계산 중...")
    df = calculate_indicators(df)
    
    # 신호 찾기
    print("🔍 A+ 신호 검색 중...")
    signals = find_a_plus_signals_btc(df)
    print(f"   {len(signals)}개 신호 발견\n")
    
    # 시뮬레이션
    results = []
    for signal in signals:
        result = simulate_trade_btc(df, signal, leverage)
        if result:
            results.append(result)
    
    return results, df

def analyze_btc_results(results: List[BTCTradeResult]) -> Dict:
    """BTC 백테스트 결과 분석"""
    if not results:
        return {}
    
    total = len(results)
    wins = len([r for r in results if r.pnl > 0])
    losses = total - wins
    win_rate = wins / total * 100
    
    pnls = [r.pnl for r in results]
    long_pnls = [r.pnl for r in results if r.signal_type == 'LONG']
    short_pnls = [r.pnl for r in results if r.signal_type == 'SHORT']
    
    avg_pnl = np.mean(pnls)
    total_return = sum(pnls)
    
    wins_pnl = [r.pnl for r in results if r.pnl > 0]
    losses_pnl = [r.pnl for r in results if r.pnl <= 0]
    
    avg_win = np.mean(wins_pnl) if wins_pnl else 0
    avg_loss = np.mean(losses_pnl) if losses_pnl else 0
    
    profit_factor = abs(sum(wins_pnl) / sum(losses_pnl)) if sum(losses_pnl) != 0 else float('inf')
    
    tp_exits = len([r for r in results if r.exit_reason == 'TP'])
    sl_exits = len([r for r in results if r.exit_reason == 'SL'])
    time_exits = len([r for r in results if r.exit_reason == 'TIME'])
    
    long_count = len([r for r in results if r.signal_type == 'LONG'])
    short_count = len([r for r in results if r.signal_type == 'SHORT'])
    
    return {
        'total_trades': total,
        'wins': wins,
        'losses': losses,
        'win_rate': win_rate,
        'avg_pnl': avg_pnl,
        'total_return': total_return,
        'avg_win': avg_win,
        'avg_loss': avg_loss,
        'profit_factor': profit_factor,
        'tp_exits': tp_exits,
        'sl_exits': sl_exits,
        'time_exits': time_exits,
        'max_drawdown': min(pnls) if pnls else 0,
        'max_profit': max(pnls) if pnls else 0,
        'long_count': long_count,
        'short_count': short_count,
        'long_avg': np.mean(long_pnls) if long_pnls else 0,
        'short_avg': np.mean(short_pnls) if short_pnls else 0
    }

def generate_btc_report(results: List[BTCTradeResult], stats: Dict, leverage: float):
    """BTC 백테스트 리포트 생성"""
    date_str = datetime.now().strftime('%Y-%m-%d')
    
    html = f"""<!DOCTYPE html>
<html lang="ko">
<head>
    <meta charset="UTF-8">
    <title>BTC A+ 백테스트 - {date_str}</title>
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{ font-family: 'Segoe UI', sans-serif; background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%); color: #eee; padding: 20px; min-height: 100vh; }}
        .container {{ max-width: 1200px; margin: 0 auto; }}
        .header {{ text-align: center; padding: 40px; background: linear-gradient(135deg, #f7931a 0%, #ffd700 100%); border-radius: 15px; margin-bottom: 30px; }}
        .header h1 {{ color: #1a1a2e; font-size: 2.5em; }}
        .header .btc {{ font-size: 3em; margin-bottom: 10px; }}
        .stats {{ display: grid; grid-template-columns: repeat(4, 1fr); gap: 15px; margin-bottom: 30px; }}
        .stat-card {{ background: rgba(255,255,255,0.05); padding: 25px; border-radius: 12px; text-align: center; }}
        .stat-card .number {{ font-size: 2.2em; font-weight: bold; margin-bottom: 5px; }}
        .stat-card .label {{ color: #888; font-size: 0.9em; }}
        .positive {{ color: #4ecca3; }} .negative {{ color: #ff6b6b; }} .neutral {{ color: #f7931a; }}
        .section {{ background: rgba(255,255,255,0.03); padding: 25px; border-radius: 12px; margin-bottom: 25px; }}
        .section h3 {{ color: #f7931a; margin-bottom: 20px; font-size: 1.3em; }}
        .long-short {{ display: grid; grid-template-columns: 1fr 1fr; gap: 20px; }}
        .ls-card {{ background: rgba(0,0,0,0.2); padding: 20px; border-radius: 10px; text-align: center; }}
        .ls-card.long {{ border-left: 4px solid #4ecca3; }}
        .ls-card.short {{ border-left: 4px solid #ff6b6b; }}
        table {{ width: 100%; border-collapse: collapse; font-size: 0.9em; }}
        th, td {{ padding: 12px; text-align: center; border-bottom: 1px solid rgba(255,255,255,0.1); }}
        th {{ color: #f7931a; font-weight: bold; }}
        .profit {{ color: #4ecca3; font-weight: bold; }} .loss {{ color: #ff6b6b; font-weight: bold; }}
        .long-badge {{ background: #4ecca3; color: #000; padding: 3px 10px; border-radius: 5px; font-weight: bold; }}
        .short-badge {{ background: #ff6b6b; color: #000; padding: 3px 10px; border-radius: 5px; font-weight: bold; }}
        .exit-tp {{ color: #4ecca3; }} .exit-sl {{ color: #ff6b6b; }} .exit-time {{ color: #888; }}
        .footer {{ text-align: center; padding: 30px; color: #666; margin-top: 20px; }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <div class="btc">🪙</div>
            <h1>BTC A+ 타점 백테스트</h1>
            <div style="color: #333; margin-top: 10px; font-size: 1.1em;">
                롱/숏 양방향 | 레버리지 {leverage}x | 2020-2025
            </div>
        </div>
        
        <div class="stats">
            <div class="stat-card">
                <div class="number {'positive' if stats['total_return'] > 0 else 'negative'}">{stats['total_return']:.1f}%</div>
                <div class="label">총 수익률</div>
            </div>
            <div class="stat-card">
                <div class="number neutral">{stats['total_trades']}</div>
                <div class="label">총 거래</div>
            </div>
            <div class="stat-card">
                <div class="number positive">{stats['win_rate']:.1f}%</div>
                <div class="label">승률</div>
            </div>
            <div class="stat-card">
                <div class="number {'positive' if stats['profit_factor'] > 1 else 'negative'}">{stats['profit_factor']:.2f}</div>
                <div class="label">Profit Factor</div>
            </div>
            <div class="stat-card">
                <div class="number {'positive' if stats['avg_pnl'] > 0 else 'negative'}">{stats['avg_pnl']:.2f}%</div>
                <div class="label">평균 수익률</div>
            </div>
            <div class="stat-card">
                <div class="number positive">{stats['avg_win']:.2f}%</div>
                <div class="label">평균 수익</div>
            </div>
            <div class="stat-card">
                <div class="number negative">{stats['avg_loss']:.2f}%</div>
                <div class="label">평균 손실</div>
            </div>
            <div class="stat-card">
                <div class="number" style="color: #ffd700;">{stats['max_profit']:.1f}%</div>
                <div class="label">최대 수익</div>
            </div>
        </div>
        
        <div class="section">
            <h3>📊 롱 vs 숏 비교</h3>
            <div class="long-short">
                <div class="ls-card long">
                    <div style="font-size: 1.5em; font-weight: bold; color: #4ecca3; margin-bottom: 10px;">🟢 LONG</div>
                    <div style="font-size: 2em; font-weight: bold;">{stats['long_count']}건</div>
                    <div style="color: {'#4ecca3' if stats['long_avg'] > 0 else '#ff6b6b'}; font-size: 1.3em; margin-top: 10px;">{stats['long_avg']:+.2f}%</div>
                </div>
                <div class="ls-card short">
                    <div style="font-size: 1.5em; font-weight: bold; color: #ff6b6b; margin-bottom: 10px;">🔴 SHORT</div>
                    <div style="font-size: 2em; font-weight: bold;">{stats['short_count']}건</div>
                    <div style="color: {'#4ecca3' if stats['short_avg'] > 0 else '#ff6b6b'}; font-size: 1.3em; margin-top: 10px;">{stats['short_avg']:+.2f}%</div>
                </div>
            </div>
        </div>
        
        <div class="section">
            <h3>📈 거래 내역 (전체)</h3>
            <table>
                <tr>
                    <th>#️⃣</th>
                    <th>포지션</th>
                    <th>진입일</th>
                    <th>청산일</th>
                    <th>진입가</th>
                    <th>청산가</th>
                    <th>수익률</th>
                    <th>청산</th>
                    <th>보유일</th>
                </tr>
"""
    
    for i, r in enumerate(sorted(results, key=lambda x: x.entry_date, reverse=True), 1):
        pnl_class = 'profit' if r.pnl > 0 else 'loss'
        pos_badge = 'long-badge' if r.signal_type == 'LONG' else 'short-badge'
        exit_class = f"exit-{r.exit_reason.lower()}"
        
        html += f"""
                <tr>
                    <td>{i}</td>
                    <td><span class="{pos_badge}">{r.signal_type}</span></td>
                    <td>{r.entry_date}</td>
                    <td>{r.exit_date}</td>
                    <td>${r.entry_price:,.2f}</td>
                    <td>${r.exit_price:,.2f}</td>
                    <td class="{pnl_class}">{r.pnl:+.2f}%</td>
                    <td class="{exit_class}">{r.exit_reason}</td>
                    <td>{r.holding_days}일</td>
                </tr>
"""
    
    html += """
            </table>
        </div>
        
        <div class="footer">
            <p>⚠️ 과거 성과가 미래 수익을 보장하지 않습니다.</p>
            <p>※ 본 백테스트는 A+ 셋업(3중 확인) + 레버리지 적용 결과</p>
            <p>※ 실제 거래 시 슬리피지, 펀딩비, 청산 위험을 고려해야 합니다.</p>
        </div>
    </div>
</body>
</html>"""
    
    os.makedirs(REPORT_DIR, exist_ok=True)
    html_path = f"{REPORT_DIR}/BTC_A_PLUS_BACKTEST_{date_str}.html"
    with open(html_path, 'w', encoding='utf-8') as f:
        f.write(html)
    
    return html_path

def main():
    # BTC 백테스트 (2020-2025, 레버리지 1x)
    results, df = run_btc_backtest('2020-01-01', '2025-03-28', leverage=1.0)
    
    print(f"\n{'='*70}")
    print("✅ BTC 백테스트 완료!")
    print(f"{'='*70}")
    print(f"총 거래: {len(results)}건\n")
    
    if results:
        stats = analyze_btc_results(results)
        
        print("📊 성과 요약:")
        print(f"  총 수익률: {stats['total_return']:+.2f}%")
        print(f"  승률: {stats['win_rate']:.1f}% ({stats['wins']}승 / {stats['losses']}패)")
        print(f"  Profit Factor: {stats['profit_factor']:.2f}")
        print(f"  평균 수익률: {stats['avg_pnl']:+.2f}%")
        print(f"  롱 평균: {stats['long_avg']:+.2f}% ({stats['long_count']}건)")
        print(f"  숏 평균: {stats['short_avg']:+.2f}% ({stats['short_count']}건)")
        
        print("\n📄 리포트 생성 중...")
        html_path = generate_btc_report(results, stats, leverage=1.0)
        print(f"    {html_path}")
        
        os.system(f"cp {html_path} /root/.openclaw/workspace/strg/docs/")
        print("    GitHub Pages 배포 완료")
        
        print("\n🏆 TOP 5 수익:")
        for i, r in enumerate(sorted(results, key=lambda x: x.pnl, reverse=True)[:5], 1):
            print(f"  {i}. [{r.signal_type}] {r.entry_date}: {r.pnl:+.2f}%")
        
        print("\n⚠️ TOP 5 손실:")
        for i, r in enumerate(sorted(results, key=lambda x: x.pnl)[:5], 1):
            print(f"  {i}. [{r.signal_type}] {r.entry_date}: {r.pnl:+.2f}%")
    else:
        print("⚠️ A+ 신호 발견되지 않음")
    
    print(f"\n{'='*70}")

if __name__ == "__main__":
    main()
