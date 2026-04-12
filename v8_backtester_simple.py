#!/usr/bin/env python3
"""
2604 V8 Unified Backtester - Simple & Fast
==========================================
단순화된 고성능 백테스트 엔진

전략:
1. 배치 데이터 로딩 (한 번만)
2. 개별 종목 순회 (캐시 활용)
3. 신뢰성 높은 기존 로직 재사용
"""

import sys
sys.path.insert(0, '/root/.openclaw/workspace/strg')

import pandas as pd
import numpy as np
import sqlite3
import json
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass

from scanner_2604_v8_unified import Scanner2604V8Unified, HoldingPeriod
from fibonacci_target_integrated import calculate_scanner_targets


@dataclass 
class Trade:
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
    ichimoku_signal: Dict


class V8BacktesterSimple:
    """단순화된 고성능 백테스터"""
    
    def __init__(self, db_path: str = 'data/level1_prices.db'):
        self.db_path = db_path
        self.trades: List[Trade] = []
        self._cache: Dict[str, pd.DataFrame] = {}
        self._scanner = None
        
    def run_backtest(self, start_date: str, end_date: str, 
                     initial_capital: float = 10000000) -> Dict:
        """백테스트 실행"""
        print("=" * 70)
        print("🔥 2604 V8 Unified Backtester (Simple & Fast)")
        print("=" * 70)
        print(f"📅 기간: {start_date} ~ {end_date}")
        print(f"💰 초기 자본: {initial_capital:,.0f}원")
        print("=" * 70)
        
        # 데이터 로딩
        self._load_data(start_date, end_date)
        
        # 스캐너 초기화
        self._scanner = Scanner2604V8Unified(self.db_path)
        
        # 거래일 리스트
        all_dates = sorted(self._cache_dates.keys())
        trading_days = [d for d in all_dates if start_date <= d <= end_date]
        print(f"📅 거래일 수: {len(trading_days)}일\n")
        
        capital = initial_capital
        daily_signals = []
        
        for i, date in enumerate(trading_days):
            print(f"📅 {date} ({i+1}/{len(trading_days)})")
            
            signals = self._scan_day(date)
            print(f"   신호: {len(signals)}개")
            
            if signals:
                for s in signals[:3]:  # 상위 3개만 표시
                    print(f"      • {s['code']}: {s['score']}점 ({s['holding'].description})")
            
            for signal in signals:
                daily_signals.append({'date': date, 'signal': signal})
                
                if i + 1 < len(trading_days):
                    entry_date = trading_days[i + 1]
                    trade = self._simulate_trade(signal, entry_date, capital)
                    if trade:
                        self.trades.append(trade)
                        capital += trade.pnl
        
        return self._calculate_results(initial_capital, capital, daily_signals)
    
    def _load_data(self, start_date: str, end_date: str):
        """배치 데이터 로딩 - 최적화된 SQLite 설정"""
        print("📦 데이터 로딩 중 (최적화)...")
        
        # 최적화된 연결 설정
        conn = sqlite3.connect(self.db_path, isolation_level=None)
        conn.execute('PRAGMA journal_mode=WAL')
        conn.execute('PRAGMA synchronous=NORMAL')
        conn.execute('PRAGMA cache_size=-100000')  # 100MB cache
        conn.execute('PRAGMA temp_store=MEMORY')
        conn.execute('PRAGMA mmap_size=30000000000')
        
        preload_start = (datetime.strptime(start_date, '%Y-%m-%d') - timedelta(days=80)).strftime('%Y-%m-%d')
        
        # covering index 활용한 쿼리
        query = f"""
        SELECT date, code, name, open, high, low, close, volume 
        FROM price_data 
        WHERE date BETWEEN '{preload_start}' AND '{end_date}'
        ORDER BY code, date ASC
        """
        
        df = pd.read_sql_query(query, conn)
        conn.close()
        
        # 종목별 캐시
        self._cache = {}
        for code, group in df.groupby('code'):
            if len(group) >= 60:
                self._cache[code] = group.sort_values('date').reset_index(drop=True)
        
        # 날짜별 종목 맵
        self._cache_dates = {}
        for date, group in df.groupby('date'):
            self._cache_dates[date] = group[['code', 'name']].drop_duplicates().to_dict('records')
        
        print(f"   ✓ {len(self._cache)}개 종목 로드 완료")
    
    def _scan_day(self, date: str) -> List[Dict]:
        """신호 스캔"""
        signals = []
        stocks = self._cache_dates.get(date, [])
        
        for stock in stocks:
            code = stock['code']
            name = stock['name']
            
            if code not in self._cache:
                continue
            
            df_full = self._cache[code]
            df = df_full[df_full['date'] <= date].copy()
            
            if len(df) < 60:
                continue
            
            signal = self._analyze(df, code, name, date)
            if signal:
                signals.append(signal)
        
        signals.sort(key=lambda x: x['score'], reverse=True)
        return signals[:10]
    
    def _analyze(self, df: pd.DataFrame, code: str, name: str, date: str) -> Optional[Dict]:
        """개별 종목 분석"""
        # 지표 계산
        df = self._calc_indicators(df)
        latest = df.iloc[-1]
        
        # 하드 필터
        if not (40 <= latest['rsi'] <= 70):
            return None
        if latest['adx'] < 20:
            return None
        
        vol_ratio = latest['volume'] / latest['volume_ma20'] if latest['volume_ma20'] > 0 else 0
        if vol_ratio < 1.5:
            return None
        
        # 점수 계산 (V8 방식 - 100점 만점)
        scores = {}
        
        # 거래량 (30점)
        if vol_ratio >= 5.0: scores['volume'] = 30
        elif vol_ratio >= 3.0: scores['volume'] = 25
        elif vol_ratio >= 2.0: scores['volume'] = 20
        else: scores['volume'] = 15
        
        # 기술적 (25점)
        tech = 0
        if 40 <= latest['rsi'] <= 60: tech += 10
        if latest['macd_hist'] > 0: tech += 5
        if latest['close'] > latest['ma5'] > latest['ma20']: tech += 5
        scores['technical'] = tech
        
        # 기타 점수
        scores['fibonacci'] = 20
        scores['momentum'] = min(abs(latest['close'] - df.iloc[-20]['close']) / df.iloc[-20]['close'] * 100 * 2, 10)
        scores['market'] = 15
        
        total = sum(scores.values())
        
        if total < 80:
            return None
        
        # 일목균형표 (보유일수용)
        prev = df.iloc[-2] if len(df) > 1 else latest
        tk_cross = (prev['tenkan_sen'] <= prev['kijun_sen'] and latest['tenkan_sen'] > latest['kijun_sen'])
        above_cloud = latest['close'] > latest['cloud_top']
        
        volatility = latest['atr'] / latest['close'] * 100
        
        # 보유일수 결정
        holding = HoldingPeriod.MEDIUM
        if total >= 95 and volatility >= 5:
            holding = HoldingPeriod.DAY_TRADE
        elif total >= 100 and tk_cross:
            holding = HoldingPeriod.SHORT
        elif above_cloud and latest['cloud_thickness_pct'] >= 5:
            holding = HoldingPeriod.LONG
        
        return {
            'code': code, 'name': name, 'date': date, 'score': total,
            'price': latest['close'], 'atr': latest['atr'], 'holding': holding,
            'tk_cross': tk_cross, 'above_cloud': above_cloud, 'vol_ratio': vol_ratio
        }
    
    def _calc_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        """기술적 지표 계산"""
        df = df.copy()
        
        # 이동평균
        df['ma5'] = df['close'].rolling(5, min_periods=1).mean()
        df['ma20'] = df['close'].rolling(20, min_periods=1).mean()
        
        # RSI
        delta = df['close'].diff()
        gain = delta.where(delta > 0, 0)
        loss = -delta.where(delta < 0, 0)
        avg_gain = gain.ewm(span=14, adjust=False, min_periods=1).mean()
        avg_loss = loss.ewm(span=14, adjust=False, min_periods=1).mean()
        rs = avg_gain / avg_loss.replace(0, np.nan)
        df['rsi'] = 100 - (100 / (1 + rs))
        df['rsi'] = df['rsi'].fillna(50)
        
        # MACD
        ema12 = df['close'].ewm(span=12, adjust=False, min_periods=1).mean()
        ema26 = df['close'].ewm(span=26, adjust=False, min_periods=1).mean()
        df['macd'] = ema12 - ema26
        df['macd_signal'] = df['macd'].ewm(span=9, adjust=False, min_periods=1).mean()
        df['macd_hist'] = df['macd'] - df['macd_signal']
        
        # ATR
        df['tr'] = np.maximum(df['high'] - df['low'], 
                              np.maximum(abs(df['high'] - df['close'].shift(1)),
                                        abs(df['low'] - df['close'].shift(1))))
        df['atr'] = df['tr'].ewm(span=14, adjust=False, min_periods=1).mean()
        
        # ADX
        df['plus_dm'] = np.where((df['high'] - df['high'].shift(1)) > (df['low'].shift(1) - df['low']),
                                  np.maximum(df['high'] - df['high'].shift(1), 0), 0)
        df['minus_dm'] = np.where((df['low'].shift(1) - df['low']) > (df['high'] - df['high'].shift(1)),
                                   np.maximum(df['low'].shift(1) - df['low'], 0), 0)
        df['plus_di'] = 100 * df['plus_dm'].ewm(span=14, adjust=False, min_periods=1).mean() / df['atr'].replace(0, np.nan)
        df['minus_di'] = 100 * df['minus_dm'].ewm(span=14, adjust=False, min_periods=1).mean() / df['atr'].replace(0, np.nan)
        df['dx'] = 100 * abs(df['plus_di'] - df['minus_di']) / (df['plus_di'] + df['minus_di']).replace(0, np.nan)
        df['adx'] = df['dx'].ewm(span=14, adjust=False, min_periods=1).mean().fillna(0)
        
        # 거래량
        df['volume_ma20'] = df['volume'].rolling(20, min_periods=1).mean()
        
        # 일목균형표
        high_9 = df['high'].rolling(window=9).max()
        low_9 = df['low'].rolling(window=9).min()
        df['tenkan_sen'] = (high_9 + low_9) / 2
        
        high_26 = df['high'].rolling(window=26).max()
        low_26 = df['low'].rolling(window=26).min()
        df['kijun_sen'] = (high_26 + low_26) / 2
        
        df['senkou_span_a'] = ((df['tenkan_sen'] + df['kijun_sen']) / 2).shift(-26)
        
        high_52 = df['high'].rolling(window=52).max()
        low_52 = df['low'].rolling(window=52).min()
        df['senkou_span_b'] = ((high_52 + low_52) / 2).shift(-26)
        
        df['cloud_top'] = df[['senkou_span_a', 'senkou_span_b']].max(axis=1)
        df['cloud_bottom'] = df[['senkou_span_a', 'senkou_span_b']].min(axis=1)
        df['cloud_thickness_pct'] = (df['cloud_top'] - df['cloud_bottom']) / df['close'] * 100
        
        return df
    
    def _simulate_trade(self, signal: Dict, entry_date: str, capital: float) -> Optional[Trade]:
        """거래 시뮬레이션"""
        code = signal['code']
        
        if code not in self._cache:
            return None
        
        df = self._cache[code]
        entry_row = df[df['date'] == entry_date]
        
        if len(entry_row) == 0:
            return None
        
        entry_price = entry_row.iloc[0]['open']
        
        # 목표가/손절가
        entry_df = pd.DataFrame([entry_row.iloc[0].to_dict()])
        targets = calculate_scanner_targets(entry_df, entry_price)
        
        if targets is None:
            return None
        
        # 청산
        holding = signal['holding']
        exit_result = self._simulate_exit(code, entry_date, entry_price, targets, holding)
        
        if not exit_result:
            return None
        
        position_size = min(capital * 0.1, 2000000)
        shares = int(position_size / entry_price)
        
        if shares == 0:
            return None
        
        pnl = (exit_result['exit_price'] - entry_price) * shares
        pnl_pct = (exit_result['exit_price'] - entry_price) / entry_price * 100
        
        return Trade(
            entry_date=entry_date, exit_date=exit_result['exit_date'],
            code=code, name=signal['name'], entry_price=entry_price,
            exit_price=exit_result['exit_price'], shares=shares, pnl=pnl, pnl_pct=pnl_pct,
            holding_days=exit_result['holding_days'], exit_reason=exit_result['reason'],
            signal_score=signal['score'], recommended_holding=holding.description,
            ichimoku_signal={'tk_cross': signal['tk_cross'], 'above_cloud': signal['above_cloud']}
        )
    
    def _simulate_exit(self, code: str, entry_date: str, entry_price: float,
                       targets: Dict, holding) -> Optional[Dict]:
        """청산 시뮬레이션"""
        df = self._cache[code]
        future_df = df[df['date'] > entry_date].head(holding.max_days + 1)
        
        if len(future_df) == 0:
            return None
        
        for i, (_, row) in enumerate(future_df.iterrows()):
            days = i + 1
            
            if holding == HoldingPeriod.DAY_TRADE:
                return {'exit_date': row['date'], 'exit_price': row['close'], 'holding_days': days, 'reason': 'time_exit'}
            
            if row['low'] <= targets['stop_loss']:
                return {'exit_date': row['date'], 'exit_price': targets['stop_loss'], 'holding_days': days, 'reason': 'stop_loss'}
            
            if holding == HoldingPeriod.SHORT and row['high'] >= targets['tp2']:
                return {'exit_date': row['date'], 'exit_price': targets['tp2'], 'holding_days': days, 'reason': 'take_profit'}
            
            if holding in [HoldingPeriod.MEDIUM, HoldingPeriod.LONG]:
                profit_pct = (row['close'] - entry_price) / entry_price * 100
                activation = 10 if holding.description.startswith('중기') else 15
                
                if profit_pct >= activation:
                    high_since = future_df.iloc[:i+1]['high'].max()
                    if row['close'] <= high_since * 0.95:
                        return {'exit_date': row['date'], 'exit_price': row['close'], 'holding_days': days, 'reason': 'trailing_stop'}
            
            if days >= holding.max_days:
                return {'exit_date': row['date'], 'exit_price': row['close'], 'holding_days': days, 'reason': 'time_exit'}
        
        return {'exit_date': future_df.iloc[-1]['date'], 'exit_price': future_df.iloc[-1]['close'], 
                'holding_days': len(future_df), 'reason': 'time_exit'}
    
    def _calculate_results(self, initial: float, final: float, signals: List[Dict]) -> Dict:
        """결과 계산"""
        if not self.trades:
            return {'total_trades': 0, 'win_rate': 0, 'total_return': 0, 'avg_return': 0, 'message': 'No trades'}
        
        trades_df = pd.DataFrame([{
            'pnl_pct': t.pnl_pct, 'win': t.pnl_pct > 0,
            'holding_days': t.holding_days, 'exit_reason': t.exit_reason,
            'holding_type': t.recommended_holding, 'tk_cross': t.ichimoku_signal['tk_cross']
        } for t in self.trades])
        
        return {
            'total_trades': len(self.trades),
            'winning_trades': int(trades_df['win'].sum()),
            'losing_trades': len(self.trades) - int(trades_df['win'].sum()),
            'win_rate': trades_df['win'].mean() * 100,
            'avg_return': trades_df['pnl_pct'].mean(),
            'total_return': (final - initial) / initial * 100,
            'avg_holding_days': trades_df['holding_days'].mean(),
            'by_holding': {h: {'trades': len(g), 'win_rate': g['win'].mean() * 100, 'avg_return': g['pnl_pct'].mean()}
                          for h, g in trades_df.groupby('holding_type')},
            'by_exit': {r: {'trades': len(g), 'win_rate': g['win'].mean() * 100, 'avg_return': g['pnl_pct'].mean()}
                       for r, g in trades_df.groupby('exit_reason')},
            'tk_cross_win_rate': trades_df[trades_df['tk_cross']]['win'].mean() * 100 if trades_df['tk_cross'].any() else 0,
            'non_tk_cross_win_rate': trades_df[~trades_df['tk_cross']]['win'].mean() * 100 if (~trades_df['tk_cross']).any() else 0
        }


def main():
    bt = V8BacktesterSimple()
    results = bt.run_backtest('2026-03-12', '2026-04-09')
    
    print("\n" + "=" * 70)
    print("📊 백테스트 결과")
    print("=" * 70)
    print(f"총 거래: {results['total_trades']}회")
    print(f"승률: {results['win_rate']:.1f}%")
    print(f"평균 수익률: {results['avg_return']:+.2f}%")
    print(f"총 수익률: {results['total_return']:+.2f}%")
    
    if results['total_trades'] > 0:
        print("\n📈 보유 기간별:")
        for h, d in results['by_holding'].items():
            print(f"  {h}: {d['trades']}회, 승률 {d['win_rate']:.1f}%, 수익 {d['avg_return']:+.2f}%")
        
        print(f"\n🎯 TK_CROSS: {results['tk_cross_win_rate']:.1f}%")
        print(f"🎯 Non-TK_CROSS: {results['non_tk_cross_win_rate']:.1f}%")
    
    # 저장
    import os
    os.makedirs('reports', exist_ok=True)
    with open('reports/v8_backtest_results.json', 'w') as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    print("\n💾 reports/v8_backtest_results.json 저장 완료")


if __name__ == '__main__':
    main()
