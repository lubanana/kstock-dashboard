#!/usr/bin/env python3
"""
2604 V8 Unified Backtester
==========================
V8 핵심 기능인 "추천 보유일수"의 성과를 검증하는 백테스트 엔진

테스트 시나리오:
1. 보유 기간별 성과 비교 (당일/단기/중기/장기)
2. 청산 전략별 성과 비교 (TP2 vs Trailing Stop vs Time Exit)
3. 일목균형표 신호별 성과 비교 (TK_CROSS vs Non-TK_CROSS)

매수 시점: V8 진입 조건 충족 시 다음날 시가 진입
매도 시점: 
- 당일: 장 마감 전 청산
- 단기: TP2 또는 3일 시간 스탑
- 중기: 10% 트레일링 또는 10일 시간 스탑  
- 장기: 15% 트레일링 또는 20일 시간 스탑
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


class V8Backtester:
    """2604 V8 백테스트 엔진"""
    
    def __init__(self, db_path: str = 'data/level1_prices.db'):
        self.db_path = db_path
        self.scanner = Scanner2604V8Unified(db_path)
        self.trades: List[Trade] = []
        self._stock_data_cache: Dict[str, pd.DataFrame] = {}
        self._date_stocks: Dict[str, List[Dict]] = {}
        
    def run_backtest(self, start_date: str, end_date: str, 
                     initial_capital: float = 10000000) -> Dict:
        """백테스트 실행 - 배치 데이터 로딩 최적화"""
        print("=" * 70)
        print("🔥 2604 V8 Unified Backtester (Optimized)")
        print("=" * 70)
        print(f"📅 기간: {start_date} ~ {end_date}")
        print(f"💰 초기 자본: {initial_capital:,.0f}원")
        print("=" * 70)
        
        self.scanner.connect()
        
        # 거래일 리스트 생성
        trading_days = self._get_trading_days(start_date, end_date)
        print(f"📊 거래일 수: {len(trading_days)}일")
        
        # 배치 데이터 로딩 - 전체 기간 데이터 한 번에 메모리에 로드
        print("📦 배치 데이터 로딩 중...")
        self._preload_data(start_date, end_date)
        print(f"   ✓ {len(self._stock_data_cache)}개 종목 데이터 로드 완료")
        
        capital = initial_capital
        daily_signals = []
        
        for i, date in enumerate(trading_days):
            print(f"\n📅 {date} ({i+1}/{len(trading_days)})")
            
            # 당일 신호 스캔 (메모리 기반)
            signals = self._scan_day_batch(date)
            print(f"   신호: {len(signals)}개")
            
            if not signals:
                continue
            
            for signal in signals:
                daily_signals.append({
                    'date': date,
                    'signal': signal
                })
                
                # 다음날 진입 시뮬레이션
                if i + 1 < len(trading_days):
                    entry_date = trading_days[i + 1]
                    trade = self._simulate_trade_batch(signal, entry_date, capital)
                    
                    if trade:
                        self.trades.append(trade)
                        capital += trade.pnl
                        print(f"   📈 {signal['name']}: {trade.pnl_pct:+.2f}% ({trade.holding_days}일)")
        
        self.scanner.close()
        
        return self._calculate_results(initial_capital, capital, daily_signals)
    
    def _preload_data(self, start_date: str, end_date: str):
        """배치 데이터 로딩 - 전체 기간 데이터 한 번에 메모리에 캐시"""
        # 60일 이전 데이터도 포함 (지표 계산용)
        preload_start = (datetime.strptime(start_date, '%Y-%m-%d') - timedelta(days=70)).strftime('%Y-%m-%d')
        
        query = f"""
        SELECT * FROM price_data 
        WHERE date BETWEEN '{preload_start}' AND '{end_date}'
        ORDER BY code, date ASC
        """
        
        df = pd.read_sql_query(query, self.scanner.conn)
        
        # 종목별로 그룹화하여 캐시
        self._stock_data_cache = {}
        for code, group in df.groupby('code'):
            if len(group) >= 60:  # 최소 60일 데이터 필요
                self._stock_data_cache[code] = group.sort_values('date').reset_index(drop=True)
        
        # 거래일별 종목 맵핑 (빠른 조회용)
        self._date_stocks = {}
        for date, group in df.groupby('date'):
            self._date_stocks[date] = group[['code', 'name']].drop_duplicates().to_dict('records')
    
    def _get_trading_days(self, start_date: str, end_date: str) -> List[str]:
        """거래일 리스트 조회"""
        query = f"""
        SELECT DISTINCT date FROM price_data 
        WHERE date BETWEEN '{start_date}' AND '{end_date}'
        ORDER BY date ASC
        """
        df = pd.read_sql_query(query, self.scanner.conn)
        return df['date'].tolist()
    
    def _scan_day_batch(self, date: str) -> List[Dict]:
        """배치 데이터 기반 신호 스캔 (DB 쿼리 없이 메모리에서 처리)"""
        signals = []
        
        # 해당 날짜의 종목 리스트
        stocks = self._date_stocks.get(date, [])
        
        for stock in stocks:
            try:
                code = stock['code']
                name = stock['name']
                
                # 캐시된 데이터에서 해당 종목 데이터 가져오기
                if code not in self._stock_data_cache:
                    continue
                
                df_full = self._stock_data_cache[code]
                
                # 해당 날짜까지의 데이터만 사용
                df = df_full[df_full['date'] <= date].copy()
                if len(df) < 60:
                    continue
                
                signal = self._analyze_stock_batch(df, code, name, date)
                if signal:
                    signals.append(signal)
            except Exception as e:
                continue
        
        # 점수순 정렬
        signals.sort(key=lambda x: x['score'], reverse=True)
        return signals[:10]  # 상위 10개만
    
    def _analyze_stock_batch(self, df: pd.DataFrame, code: str, name: str, date: str) -> Optional[Dict]:
        """캐시된 데이터 기반 분석"""
        df = self.scanner.calculate_indicators(df)
        latest = df.iloc[-1]
        
        # 하드 필터
        if not (40 <= latest['rsi'] <= 70):
            return None
        if latest['adx'] < 20:
            return None
        vol_ratio = latest['volume'] / latest['volume_ma20'] if latest['volume_ma20'] > 0 else 0
        if vol_ratio < 1.5:
            return None
        
        # 점수 계산 (V7 방식 - 100점 만점)
        scores = {}
        
        # 거래량 (30점)
        vol_score = 0
        if vol_ratio >= 5.0:
            vol_score = 30
        elif vol_ratio >= 3.0:
            vol_score = 25
        elif vol_ratio >= 2.0:
            vol_score = 20
        elif vol_ratio >= 1.5:
            vol_score = 15
        scores['volume'] = vol_score
        
        # 기술적 (25점)
        tech_score = 0
        if 40 <= latest['rsi'] <= 60:
            tech_score += 10
        if latest['macd_hist'] > 0:
            tech_score += 5
        if latest['close'] > latest['ma5'] > latest['ma20']:
            tech_score += 5
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
        
        # 일목균형표 (보유일수 계산용)
        ichimoku = self.scanner.generate_ichimoku_signal(df)
        volatility = latest['atr'] / latest['close'] * 100
        holding, _ = self.scanner.calculate_holding_period(
            total_score=total_score,
            ichimoku=ichimoku,
            adx=latest['adx'],
            volatility=volatility
        )
        
        return {
            'code': code,
            'name': name,
            'date': date,
            'score': total_score,
            'price': latest['close'],
            'atr': latest['atr'],
            'holding': holding,
            'ichimoku': ichimoku,
            'adx': latest['adx'],
            'rsi': latest['rsi']
        }
    
    def _simulate_trade_batch(self, signal: Dict, entry_date: str, 
                               capital: float) -> Optional[Trade]:
        """캐시된 데이터 기반 거래 시뮬레이션"""
        code = signal['code']
        
        # 캐시된 데이터에서 진입일 데이터 찾기
        if code not in self._stock_data_cache:
            return None
        
        df = self._stock_data_cache[code]
        entry_row = df[df['date'] == entry_date]
        
        if len(entry_row) == 0:
            return None
        
        entry_price = entry_row.iloc[0]['open']
        
        # 목표가/손절가 계산
        entry_data = entry_row.iloc[0].to_dict()
        entry_df = pd.DataFrame([entry_data])
        targets = calculate_scanner_targets(entry_df, entry_price)
        
        if targets is None:
            return None
        
        # 보유 기간별 청산 시뮬레이션 (캐시된 데이터 사용)
        holding = signal['holding']
        exit_result = self._simulate_exit_batch(
            signal['code'], 
            entry_date, 
            entry_price,
            targets,
            holding
        )
        
        if not exit_result:
            return None
        
        # 포지션 크기 (최대 10% 투자)
        position_size = min(capital * 0.1, 2000000)  # 최대 200만원
        shares = int(position_size / entry_price)
        
        if shares == 0:
            return None
        
        pnl = (exit_result['exit_price'] - entry_price) * shares
        pnl_pct = (exit_result['exit_price'] - entry_price) / entry_price * 100
        
        return Trade(
            entry_date=entry_date,
            exit_date=exit_result['exit_date'],
            code=signal['code'],
            name=signal['name'],
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
                'tk_cross': signal['ichimoku'].tk_cross_bullish,
                'above_cloud': signal['ichimoku'].price_above_cloud
            }
        )
    
    def _simulate_exit_batch(self, code: str, entry_date: str, entry_price: float,
                              targets: Dict, holding: HoldingPeriod) -> Optional[Dict]:
        """캐시된 데이터 기반 청산 시뮬레이션"""
        # 캐시된 데이터에서 진입일 이후 데이터 가져오기
        if code not in self._stock_data_cache:
            return None
        
        df = self._stock_data_cache[code]
        future_df = df[df['date'] > entry_date].head(holding.max_days + 1)
        
        if len(future_df) == 0:
            return None
        
        # 보유 기간별 청산 로직
        for i, (_, row) in enumerate(future_df.iterrows()):
            holding_days = i + 1
            
            # 당일 청산
            if holding == HoldingPeriod.DAY_TRADE:
                return {
                    'exit_date': row['date'],
                    'exit_price': row['close'],
                    'holding_days': holding_days,
                    'reason': 'time_exit'
                }
            
            # 손절가 도달
            if row['low'] <= targets['stop_loss']:
                return {
                    'exit_date': row['date'],
                    'exit_price': targets['stop_loss'],
                    'holding_days': holding_days,
                    'reason': 'stop_loss'
                }
            
            # TP2 도달 (단기 전략)
            if holding == HoldingPeriod.SHORT and row['high'] >= targets['tp2']:
                return {
                    'exit_date': row['date'],
                    'exit_price': targets['tp2'],
                    'holding_days': holding_days,
                    'reason': 'take_profit'
                }
            
            # 트레일링 스탑 (중기/장기)
            if holding in [HoldingPeriod.MEDIUM, HoldingPeriod.LONG]:
                trailing_stop = entry_price * (1 + holding.trail_pct / 100)
                if row['low'] <= trailing_stop:
                    return {
                        'exit_date': row['date'],
                        'exit_price': trailing_stop,
                        'holding_days': holding_days,
                        'reason': 'trailing_stop'
                    }
            
            # 시간 스탑
            if holding_days >= holding.max_days:
                return {
                    'exit_date': row['date'],
                    'exit_price': row['close'],
                    'holding_days': holding_days,
                    'reason': 'time_exit'
                }
        
        # 데이터 끝까지 보유
        return {
            'exit_date': future_df.iloc[-1]['date'],
            'exit_price': future_df.iloc[-1]['close'],
            'holding_days': len(future_df),
            'reason': 'time_exit'
        }
    
    def _simulate_exit(self, code: str, entry_date: str, entry_price: float,
                       targets: Dict, holding: HoldingPeriod) -> Optional[Dict]:
        """청산 시뮬레이션"""
        # 향후 데이터 조회
        query = f"""
        SELECT date, open, high, low, close FROM price_data 
        WHERE code = '{code}' AND date > '{entry_date}'
        ORDER BY date ASC
        LIMIT {holding.max_days + 1}
        """
        df = pd.read_sql_query(query, self.scanner.conn)
        
        if len(df) == 0:
            return None
        
        # 보유 기간별 청산 로직
        for i, row in df.iterrows():
            holding_days = i + 1
            
            # 당일 청산
            if holding == HoldingPeriod.DAY_TRADE:
                return {
                    'exit_date': row['date'],
                    'exit_price': row['close'],
                    'holding_days': holding_days,
                    'reason': 'time_exit'
                }
            
            # 손절가 도달
            if row['low'] <= targets['stop_loss']:
                return {
                    'exit_date': row['date'],
                    'exit_price': targets['stop_loss'],
                    'holding_days': holding_days,
                    'reason': 'stop_loss'
                }
            
            # TP2 도달 (단기 전략)
            if holding == HoldingPeriod.SHORT and row['high'] >= targets['tp2']:
                return {
                    'exit_date': row['date'],
                    'exit_price': targets['tp2'],
                    'holding_days': holding_days,
                    'reason': 'take_profit'
                }
            
            # 트레일링 스탑 (중기/장기)
            if holding in [HoldingPeriod.MEDIUM, HoldingPeriod.LONG]:
                profit_pct = (row['close'] - entry_price) / entry_price * 100
                trail_activation = 10 if holding == HoldingPeriod.MEDIUM else 15
                
                if profit_pct >= trail_activation:
                    # 트레일링 활성화: 고점 대비 5% 하락 시 청산
                    high_since_entry = df.iloc[:i+1]['high'].max()
                    if row['close'] <= high_since_entry * 0.95:
                        return {
                            'exit_date': row['date'],
                            'exit_price': row['close'],
                            'holding_days': holding_days,
                            'reason': 'trailing_stop'
                        }
            
            # 시간 스탑
            if holding_days >= holding.max_days:
                return {
                    'exit_date': row['date'],
                    'exit_price': row['close'],
                    'holding_days': holding_days,
                    'reason': 'time_exit'
                }
        
        # 마지막 날 청산
        return {
            'exit_date': df.iloc[-1]['date'],
            'exit_price': df.iloc[-1]['close'],
            'holding_days': len(df),
            'reason': 'time_exit'
        }
    
    def _get_price_data(self, code: str, date: str) -> Optional[Dict]:
        """특정일 가격 데이터 조회 (캐시된 데이터 사용)"""
        if code not in self._stock_data_cache:
            return None
        
        df = self._stock_data_cache[code]
        row = df[df['date'] == date]
        
        if len(row) == 0:
            return None
        
        return row.iloc[0].to_dict()
    
    def _calculate_results(self, initial: float, final: float, 
                           signals: List[Dict]) -> Dict:
        """결과 계산"""
        if not self.trades:
            return {
                'total_trades': 0,
                'win_rate': 0,
                'total_return': 0,
                'message': 'No trades executed'
            }
        
        trades_df = pd.DataFrame([{
            'pnl_pct': t.pnl_pct,
            'win': t.pnl_pct > 0,
            'holding_days': t.holding_days,
            'exit_reason': t.exit_reason,
            'recommended_holding': t.recommended_holding,
            'tk_cross': t.ichimoku_signal['tk_cross']
        } for t in self.trades])
        
        results = {
            'period': f"{signals[0]['date'] if signals else 'N/A'} ~ {signals[-1]['date'] if signals else 'N/A'}",
            'total_trades': len(self.trades),
            'winning_trades': int(trades_df['win'].sum()),
            'losing_trades': len(self.trades) - int(trades_df['win'].sum()),
            'win_rate': trades_df['win'].mean() * 100,
            'avg_return': trades_df['pnl_pct'].mean(),
            'total_return': (final - initial) / initial * 100,
            'avg_holding_days': trades_df['holding_days'].mean(),
            
            # 보유 기간별 분석
            'by_holding_period': {},
            
            # 청산 사유별 분석
            'by_exit_reason': {},
            
            # TK_CROSS 분석
            'tk_cross_win_rate': trades_df[trades_df['tk_cross'] == True]['win'].mean() * 100 if len(trades_df[trades_df['tk_cross'] == True]) > 0 else 0,
            'non_tk_cross_win_rate': trades_df[trades_df['tk_cross'] == False]['win'].mean() * 100 if len(trades_df[trades_df['tk_cross'] == False]) > 0 else 0
        }
        
        # 보유 기간별 분석
        for period in trades_df['recommended_holding'].unique():
            period_df = trades_df[trades_df['recommended_holding'] == period]
            results['by_holding_period'][period] = {
                'trades': len(period_df),
                'win_rate': period_df['win'].mean() * 100,
                'avg_return': period_df['pnl_pct'].mean()
            }
        
        # 청산 사유별 분석
        for reason in trades_df['exit_reason'].unique():
            reason_df = trades_df[trades_df['exit_reason'] == reason]
            results['by_exit_reason'][reason] = {
                'trades': len(reason_df),
                'win_rate': reason_df['win'].mean() * 100,
                'avg_return': reason_df['pnl_pct'].mean()
            }
        
        return results


def main():
    """백테스트 실행"""
    backtester = V8Backtester()
    
    # 최근 20거래일 백테스트
    end_date = '2026-04-09'
    start_date = '2026-03-12'  # 약 20거래일 전
    
    results = backtester.run_backtest(start_date, end_date)
    
    print("\n" + "=" * 70)
    print("📊 백테스트 결과")
    print("=" * 70)
    print(f"\n총 거래: {results['total_trades']}회")
    print(f"승률: {results['win_rate']:.1f}%")
    print(f"평균 수익률: {results['avg_return']:+.2f}%")
    print(f"총 수익률: {results['total_return']:+.2f}%")
    print(f"평균 보유일: {results['avg_holding_days']:.1f}일")
    
    if results['by_holding_period']:
        print("\n📅 보유 기간별 성과")
        for period, data in results['by_holding_period'].items():
            print(f"   {period}: {data['trades']}거래, 승률 {data['win_rate']:.1f}%, 수익 {data['avg_return']:+.2f}%")
    
    if results['by_exit_reason']:
        print("\n🎯 청산 사유별 성과")
        for reason, data in results['by_exit_reason'].items():
            print(f"   {reason}: {data['trades']}거래, 승률 {data['win_rate']:.1f}%, 수익 {data['avg_return']:+.2f}%")
    
    print(f"\n📈 TK_CROSS 승률: {results['tk_cross_win_rate']:.1f}%")
    print(f"📉 Non-TK_CROSS 승률: {results['non_tk_cross_win_rate']:.1f}%")
    
    # 결과 저장
    results_file = f"reports/v8_backtest_{start_date.replace('-', '')}_{end_date.replace('-', '')}.json"
    with open(results_file, 'w', encoding='utf-8') as f:
        # DataFrame은 직렬화 불가능하므로 제외
        results_serializable = {k: v for k, v in results.items() if k != 'trades_df'}
        json.dump(results_serializable, f, ensure_ascii=False, indent=2)
    print(f"\n✅ 결과 저장: {results_file}")


if __name__ == '__main__':
    main()
