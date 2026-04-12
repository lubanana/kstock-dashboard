#!/usr/bin/env python3
"""
2604 V8 Unified Backtester - Optimized
======================================
벡터화 + 멀티프로세싱 적용 버전

성능 개선:
1. 배치 데이터 로딩 (한 번의 쿼리로 모든 데이터 로드)
2. 벡터화된 지표 계산 (pandas groupby + transform)
3. 멀티프로세싱 (CPU 코어 수만큼 병렬 처리)
"""

import sys
sys.path.insert(0, '/root/.openclaw/workspace/strg')

import pandas as pd
import numpy as np
import sqlite3
import json
import multiprocessing as mp
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass
from enum import Enum

from scanner_2604_v8_unified import Scanner2604V8Unified, HoldingPeriod, IchimokuSignal
from fibonacci_target_integrated import calculate_scanner_targets


@dataclass
class Trade:
    """개별 거래 기록"""
    entry_date: str
    exit_date: str
    code: str
    name: str
    entry_price: float
    exit_price: float
    shares: int
    pnl: float
    pnl_pct: float
    holding_days: int
    exit_reason: str
    signal_score: int
    recommended_holding: str
    actual_holding: str
    ichimoku_signal: Dict


def calculate_indicators_batch(df: pd.DataFrame) -> pd.DataFrame:
    """벡터화된 지표 계산 (종목별 groupby 적용)"""
    df = df.copy()
    df = df.sort_values(['code', 'date'])
    
    # 그룹별 계산을 위한 helper
    def calc_group(group):
        g = group.copy()
        
        # 이동평균
        g['ma5'] = g['close'].rolling(5, min_periods=1).mean()
        g['ma20'] = g['close'].rolling(20, min_periods=1).mean()
        g['ma60'] = g['close'].rolling(60, min_periods=1).mean()
        
        # RSI
        delta = g['close'].diff()
        gain = delta.where(delta > 0, 0)
        loss = -delta.where(delta < 0, 0)
        avg_gain = gain.ewm(span=14, adjust=False, min_periods=1).mean()
        avg_loss = loss.ewm(span=14, adjust=False, min_periods=1).mean()
        rs = avg_gain / avg_loss.replace(0, np.nan)
        g['rsi'] = 100 - (100 / (1 + rs))
        g['rsi'] = g['rsi'].fillna(50)
        
        # MACD
        ema12 = g['close'].ewm(span=12, adjust=False, min_periods=1).mean()
        ema26 = g['close'].ewm(span=26, adjust=False, min_periods=1).mean()
        g['macd'] = ema12 - ema26
        g['macd_signal'] = g['macd'].ewm(span=9, adjust=False, min_periods=1).mean()
        g['macd_hist'] = g['macd'] - g['macd_signal']
        
        # 볼린저
        g['bb_middle'] = g['close'].rolling(20, min_periods=1).mean()
        bb_std = g['close'].rolling(20, min_periods=1).std()
        g['bb_upper'] = g['bb_middle'] + 2 * bb_std
        g['bb_lower'] = g['bb_middle'] - 2 * bb_std
        
        # ATR
        g['tr1'] = g['high'] - g['low']
        g['tr2'] = abs(g['high'] - g['close'].shift(1))
        g['tr3'] = abs(g['low'] - g['close'].shift(1))
        g['tr'] = g[['tr1', 'tr2', 'tr3']].max(axis=1).fillna(g['high'] - g['low'])
        g['atr'] = g['tr'].ewm(span=14, adjust=False, min_periods=1).mean()
        
        # ADX
        g['plus_dm'] = np.where(
            (g['high'] - g['high'].shift(1)) > (g['low'].shift(1) - g['low']),
            np.maximum(g['high'] - g['high'].shift(1), 0), 0)
        g['minus_dm'] = np.where(
            (g['low'].shift(1) - g['low']) > (g['high'] - g['high'].shift(1)),
            np.maximum(g['low'].shift(1) - g['low'], 0), 0)
        
        g['plus_di'] = 100 * g['plus_dm'].ewm(span=14, adjust=False, min_periods=1).mean() / g['atr'].replace(0, np.nan)
        g['minus_di'] = 100 * g['minus_dm'].ewm(span=14, adjust=False, min_periods=1).mean() / g['atr'].replace(0, np.nan)
        g['dx'] = 100 * abs(g['plus_di'] - g['minus_di']) / (g['plus_di'] + g['minus_di']).replace(0, np.nan)
        g['adx'] = g['dx'].ewm(span=14, adjust=False, min_periods=1).mean()
        g['adx'] = g['adx'].fillna(0)
        
        # 거래량
        g['volume_ma20'] = g['volume'].rolling(20, min_periods=1).mean()
        
        # 일목균형표
        tenkan_period, kijun_period, senkou_b_period, displacement = 9, 26, 52, 26
        
        high_9 = g['high'].rolling(window=tenkan_period).max()
        low_9 = g['low'].rolling(window=tenkan_period).min()
        g['tenkan_sen'] = (high_9 + low_9) / 2
        
        high_26 = g['high'].rolling(window=kijun_period).max()
        low_26 = g['low'].rolling(window=kijun_period).min()
        g['kijun_sen'] = (high_26 + low_26) / 2
        
        g['senkou_span_a'] = ((g['tenkan_sen'] + g['kijun_sen']) / 2).shift(-displacement)
        
        high_52 = g['high'].rolling(window=senkou_b_period).max()
        low_52 = g['low'].rolling(window=senkou_b_period).min()
        g['senkou_span_b'] = ((high_52 + low_52) / 2).shift(-displacement)
        
        g['cloud_top'] = g[['senkou_span_a', 'senkou_span_b']].max(axis=1)
        g['cloud_bottom'] = g[['senkou_span_a', 'senkou_span_b']].min(axis=1)
        g['cloud_thickness_pct'] = (g['cloud_top'] - g['cloud_bottom']) / g['close'] * 100
        
        return g
    
    # 종목별로 그룹화하여 계산
    result_dfs = []
    for code, group in df.groupby('code', sort=False):
        result_dfs.append(calc_group(group))
    
    df = pd.concat(result_dfs, ignore_index=True)
    return df


def analyze_stock_batch(args):
    """배치 분석 worker 함수"""
    code, group, date = args
    
    try:
        # 해당 날짜까지의 데이터만 사용
        df = group[group['date'] <= date].copy()
        if len(df) < 60:
            return None
        
        latest = df.iloc[-1]
        
        # 하드 필터
        if not (40 <= latest['rsi'] <= 70):
            return None
        if latest['adx'] < 20:
            return None
        vol_ratio = latest['volume'] / latest['volume_ma20'] if latest['volume_ma20'] > 0 else 0
        if vol_ratio < 1.5:
            return None
        
        # 점수 계산
        scores = {}
        
        # 거래량 (30점)
        vol_score = 0
        if vol_ratio >= 5.0: vol_score = 30
        elif vol_ratio >= 3.0: vol_score = 25
        elif vol_ratio >= 2.0: vol_score = 20
        elif vol_ratio >= 1.5: vol_score = 15
        scores['volume'] = vol_score
        
        # 기술적 (25점)
        tech_score = 0
        if 40 <= latest['rsi'] <= 60: tech_score += 10
        if latest['macd_hist'] > 0: tech_score += 5
        if latest['close'] > latest['ma5'] > latest['ma20']: tech_score += 5
        scores['technical'] = tech_score
        
        # 피볼나치 (20점)
        scores['fibonacci'] = 20
        
        # 모멘텀 (10점)
        mom_score = min(abs(latest['close'] - df.iloc[-20]['close']) / df.iloc[-20]['close'] * 100 * 2, 10)
        scores['momentum'] = int(mom_score)
        
        # 시장맥락 (15점)
        scores['market'] = 15
        
        total_score = sum(scores.values())
        
        if total_score < 80:
            return None
        
        # 일목균형표 신호
        prev = df.iloc[-2] if len(df) > 1 else latest
        tk_cross_bullish = (prev['tenkan_sen'] <= prev['kijun_sen'] and 
                           latest['tenkan_sen'] > latest['kijun_sen'])
        price_above_cloud = latest['close'] > latest['cloud_top']
        bullish_cloud = latest['senkou_span_a'] > latest['senkou_span_b']
        
        volatility = latest['atr'] / latest['close'] * 100
        adx = latest['adx']
        
        # 보유일수 결정
        holding = HoldingPeriod.MEDIUM
        if total_score >= 95 and volatility >= 5:
            holding = HoldingPeriod.DAY_TRADE
        elif total_score >= 100 and tk_cross_bullish and adx >= 30:
            holding = HoldingPeriod.SHORT
        elif price_above_cloud and adx >= 25 and volatility < 3:
            holding = HoldingPeriod.MEDIUM
        elif price_above_cloud and latest['cloud_thickness_pct'] >= 5 and adx >= 20:
            holding = HoldingPeriod.LONG
        
        return {
            'code': code,
            'name': latest.get('name', code),
            'date': date,
            'score': total_score,
            'price': latest['close'],
            'atr': latest['atr'],
            'holding': holding,
            'tk_cross': tk_cross_bullish,
            'above_cloud': price_above_cloud,
            'adx': adx,
            'rsi': latest['rsi'],
            'vol_ratio': vol_ratio
        }
    except Exception as e:
        return None


class V8BacktesterOptimized:
    """최적화된 2604 V8 백테스트 엔진"""
    
    def __init__(self, db_path: str = 'data/level1_prices.db'):
        self.db_path = db_path
        self.trades: List[Trade] = []
        self._data_cache = None
        self._num_workers = min(mp.cpu_count(), 8)  # 최대 8코어 사용
        
    def run_backtest(self, start_date: str, end_date: str, 
                     initial_capital: float = 10000000) -> Dict:
        """백테스트 실행"""
        print("=" * 70)
        print("🔥 2604 V8 Unified Backtester (Optimized)")
        print("=" * 70)
        print(f"📅 기간: {start_date} ~ {end_date}")
        print(f"💰 초기 자본: {initial_capital:,.0f}원")
        print(f"🖥️  워커 수: {self._num_workers}개")
        print("=" * 70)
        
        # 배치 데이터 로딩
        print("📦 배치 데이터 로딩 중...")
        self._preload_data(start_date, end_date)
        
        # 지표 계산 (벡터화)
        print("📊 기술적 지표 계산 중 (벡터화)...")
        self._data_with_indicators = calculate_indicators_batch(self._data_cache)
        print(f"   ✓ {self._data_with_indicators['code'].nunique()}개 종목 지표 계산 완료")
        
        # 거래일 리스트
        trading_days = sorted(self._data_with_indicators['date'].unique())
        # start_date ~ end_date 범위만
        trading_days = [d for d in trading_days if start_date <= d <= end_date]
        print(f"📅 거래일 수: {len(trading_days)}일")
        
        capital = initial_capital
        daily_signals = []
        
        for i, date in enumerate(trading_days):
            print(f"\n📅 {date} ({i+1}/{len(trading_days)})")
            
            # 멀티프로세싱으로 신호 스캔
            signals = self._scan_day_parallel(date)
            print(f"   신호: {len(signals)}개")
            
            if not signals:
                continue
            
            for signal in signals:
                daily_signals.append({'date': date, 'signal': signal})
                
                # 다음날 진입 시뮬레이션
                if i + 1 < len(trading_days):
                    entry_date = trading_days[i + 1]
                    trade = self._simulate_trade(signal, entry_date, capital)
                    
                    if trade:
                        self.trades.append(trade)
                        capital += trade.pnl
                        print(f"   📈 {signal['code']}: {trade.pnl_pct:+.2f}% ({trade.holding_days}일)")
        
        return self._calculate_results(initial_capital, capital, daily_signals)
    
    def _preload_data(self, start_date: str, end_date: str):
        """배치 데이터 로딩"""
        conn = sqlite3.connect(self.db_path)
        
        # 60일 이전 데이터도 포함 (지표 계산용)
        preload_start = (datetime.strptime(start_date, '%Y-%m-%d') - timedelta(days=70)).strftime('%Y-%m-%d')
        
        query = f"""
        SELECT date, code, name, open, high, low, close, volume 
        FROM price_data 
        WHERE date BETWEEN '{preload_start}' AND '{end_date}'
        ORDER BY code, date ASC
        """
        
        self._data_cache = pd.read_sql_query(query, conn)
        conn.close()
        
        print(f"   ✓ {len(self._data_cache):,}개 레코드, {self._data_cache['code'].nunique()}개 종목")
    
    def _scan_day_parallel(self, date: str) -> List[Dict]:
        """멀티프로세싱 병렬 스캔"""
        # 해당 날짜 이전 데이터가 있는 종목 필터
        date_data = self._data_with_indicators[self._data_with_indicators['date'] <= date]
        
        # 종목별로 그룹화
        grouped = date_data.groupby('code')
        
        # 워커에 전달할 인자 준비
        worker_args = [(code, group, date) for code, group in grouped if len(group) >= 60]
        
        if not worker_args:
            return []
        
        # 멀티프로세싱 실행
        with mp.Pool(processes=self._num_workers) as pool:
            results = pool.map(analyze_stock_batch, worker_args)
        
        # None 필터링 및 정렬
        signals = [r for r in results if r is not None]
        signals.sort(key=lambda x: x['score'], reverse=True)
        return signals[:10]
    
    def _simulate_trade(self, signal: Dict, entry_date: str, capital: float) -> Optional[Trade]:
        """거래 시뮬레이션"""
        code = signal['code']
        
        # 진입가 조회
        entry_rows = self._data_cache[(self._data_cache['code'] == code) & 
                                       (self._data_cache['date'] == entry_date)]
        if len(entry_rows) == 0:
            return None
        
        entry_price = entry_rows.iloc[0]['open']
        entry_data = entry_rows.iloc[0].to_dict()
        
        # 목표가/손절가 계산
        entry_df = pd.DataFrame([entry_data])
        targets = calculate_scanner_targets(entry_df, entry_price)
        
        if targets is None:
            return None
        
        # 청산 시뮬레이션
        holding = signal['holding']
        exit_result = self._simulate_exit(code, entry_date, entry_price, targets, holding)
        
        if not exit_result:
            return None
        
        # 포지션 크기
        position_size = min(capital * 0.1, 2000000)
        shares = int(position_size / entry_price)
        
        if shares == 0:
            return None
        
        pnl = (exit_result['exit_price'] - entry_price) * shares
        pnl_pct = (exit_result['exit_price'] - entry_price) / entry_price * 100
        
        return Trade(
            entry_date=entry_date,
            exit_date=exit_result['exit_date'],
            code=code,
            name=signal.get('name', code),
            entry_price=entry_price,
            exit_price=exit_result['exit_price'],
            shares=shares,
            pnl=pnl,
            pnl_pct=pnl_pct,
            holding_days=exit_result['holding_days'],
            exit_reason=exit_result['reason'],
            signal_score=signal['score'],
            recommended_holding=holding.description,
            actual_holding=holding.description,
            ichimoku_signal={
                'tk_cross': signal.get('tk_cross', False),
                'above_cloud': signal.get('above_cloud', False)
            }
        )
    
    def _simulate_exit(self, code: str, entry_date: str, entry_price: float,
                       targets: Dict, holding: HoldingPeriod) -> Optional[Dict]:
        """청산 시뮬레이션"""
        future_df = self._data_cache[(self._data_cache['code'] == code) & 
                                      (self._data_cache['date'] > entry_date)].head(holding.max_days + 1)
        
        if len(future_df) == 0:
            return None
        
        for i, (_, row) in enumerate(future_df.iterrows()):
            holding_days = i + 1
            
            # 당일 청산
            if holding == HoldingPeriod.DAY_TRADE:
                return {'exit_date': row['date'], 'exit_price': row['close'], 
                        'holding_days': holding_days, 'reason': 'time_exit'}
            
            # 손절가
            if row['low'] <= targets['stop_loss']:
                return {'exit_date': row['date'], 'exit_price': targets['stop_loss'],
                        'holding_days': holding_days, 'reason': 'stop_loss'}
            
            # TP2 (단기)
            if holding == HoldingPeriod.SHORT and row['high'] >= targets['tp2']:
                return {'exit_date': row['date'], 'exit_price': targets['tp2'],
                        'holding_days': holding_days, 'reason': 'take_profit'}
            
            # 트레일링 (중기/장기)
            if holding in [HoldingPeriod.MEDIUM, HoldingPeriod.LONG]:
                profit_pct = (row['close'] - entry_price) / entry_price * 100
                trail_activation = 10 if holding == HoldingPeriod.MEDIUM else 15
                
                if profit_pct >= trail_activation:
                    high_since = future_df.iloc[:i+1]['high'].max()
                    if row['close'] <= high_since * 0.95:
                        return {'exit_date': row['date'], 'exit_price': row['close'],
                                'holding_days': holding_days, 'reason': 'trailing_stop'}
            
            # 시간 스탑
            if holding_days >= holding.max_days:
                return {'exit_date': row['date'], 'exit_price': row['close'],
                        'holding_days': holding_days, 'reason': 'time_exit'}
        
        return {'exit_date': future_df.iloc[-1]['date'], 'exit_price': future_df.iloc[-1]['close'],
                'holding_days': len(future_df), 'reason': 'time_exit'}
    
    def _calculate_results(self, initial: float, final: float, signals: List[Dict]) -> Dict:
        """결과 계산"""
        if not self.trades:
            return {'total_trades': 0, 'win_rate': 0, 'total_return': 0, 'message': 'No trades executed'}
        
        trades_df = pd.DataFrame([{
            'pnl_pct': t.pnl_pct, 'win': t.pnl_pct > 0,
            'holding_days': t.holding_days, 'exit_reason': t.exit_reason,
            'recommended_holding': t.recommended_holding,
            'tk_cross': t.ichimoku_signal['tk_cross']
        } for t in self.trades])
        
        results = {
            'total_trades': len(self.trades),
            'winning_trades': int(trades_df['win'].sum()),
            'losing_trades': len(self.trades) - int(trades_df['win'].sum()),
            'win_rate': trades_df['win'].mean() * 100,
            'avg_return': trades_df['pnl_pct'].mean(),
            'total_return': (final - initial) / initial * 100,
            'avg_holding_days': trades_df['holding_days'].mean(),
            'by_holding_period': {},
            'by_exit_reason': {},
            'tk_cross_win_rate': trades_df[trades_df['tk_cross'] == True]['win'].mean() * 100 if len(trades_df[trades_df['tk_cross'] == True]) > 0 else 0,
            'non_tk_cross_win_rate': trades_df[trades_df['tk_cross'] == False]['win'].mean() * 100 if len(trades_df[trades_df['tk_cross'] == False]) > 0 else 0
        }
        
        for period in trades_df['recommended_holding'].unique():
            period_df = trades_df[trades_df['recommended_holding'] == period]
            results['by_holding_period'][period] = {
                'trades': len(period_df), 'win_rate': period_df['win'].mean() * 100,
                'avg_return': period_df['pnl_pct'].mean()
            }
        
        for reason in trades_df['exit_reason'].unique():
            reason_df = trades_df[trades_df['exit_reason'] == reason]
            results['by_exit_reason'][reason] = {
                'trades': len(reason_df), 'win_rate': reason_df['win'].mean() * 100,
                'avg_return': reason_df['pnl_pct'].mean()
            }
        
        return results


def main():
    backtester = V8BacktesterOptimized()
    results = backtester.run_backtest('2026-03-12', '2026-04-09')
    
    print("\n" + "=" * 70)
    print("📊 백테스트 결과")
    print("=" * 70)
    print(f"총 거래: {results['total_trades']}회")
    print(f"승률: {results['win_rate']:.1f}%")
    print(f"평균 수익률: {results['avg_return']:+.2f}%")
    print(f"총 수익률: {results['total_return']:+.2f}%")
    
    if results['total_trades'] > 0:
        print("\n📈 보유 기간별:")
        for period, data in results['by_holding_period'].items():
            print(f"  {period}: {data['trades']}회, 승률 {data['win_rate']:.1f}%, 수익 {data['avg_return']:+.2f}%")
        
        print("\n📉 청산 사유별:")
        for reason, data in results['by_exit_reason'].items():
            print(f"  {reason}: {data['trades']}회, 승률 {data['win_rate']:.1f}%, 수익 {data['avg_return']:+.2f}%")
        
        print(f"\n🎯 TK_CROSS 승률: {results['tk_cross_win_rate']:.1f}%")
        print(f"🎯 Non-TK_CROSS 승률: {results['non_tk_cross_win_rate']:.1f}%")
    
    # 결과 저장
    import os
    os.makedirs('reports', exist_ok=True)
    with open('reports/v8_backtest_results.json', 'w', encoding='utf-8') as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    print("\n💾 결과 저장: reports/v8_backtest_results.json")


if __name__ == '__main__':
    main()
