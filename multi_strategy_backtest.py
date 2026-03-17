#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Multi-Strategy Backtester
=========================
5가지 전략을 활용한 백테스팅 시스템

- 2026년 1월 ~ 현재까지 일별 스캔
- 발굴 종목 추적 및 포지션 관리
- 매매 규칙:
  * 진입: 전략 충족 시 당일 종가 진입 (전략 수에 비례한 가중치)
  * 청산: 
    - 목표가 +15% 도달 시 50% 수익실현
    - 목표가 +25% 도달 시 나머지 50% 수익실현
    - 손절가 -7% 도달 시 전량 손절
    - 보유 20거래일 초과 시 시가 청산
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from pathlib import Path
import json
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass, field
from collections import defaultdict

from fdr_wrapper import FDRWrapper, DatabaseManager


@dataclass
class Position:
    """포지션 정보"""
    symbol: str
    name: str
    entry_date: str
    entry_price: float
    quantity: int
    strategies: List[str] = field(default_factory=list)
    target_price_15: float = 0
    target_price_25: float = 0
    stop_loss: float = 0
    
    def __post_init__(self):
        self.target_price_15 = self.entry_price * 1.15
        self.target_price_25 = self.entry_price * 1.25
        self.stop_loss = self.entry_price * 0.93


@dataclass
class Trade:
    """거래 기록"""
    symbol: str
    name: str
    entry_date: str
    exit_date: str
    entry_price: float
    exit_price: float
    quantity: int
    strategies: List[str]
    exit_reason: str  # 'target_15', 'target_25', 'stop_loss', 'timeout'
    pnl: float  # 손익 금액
    pnl_pct: float  # 수익률 %
    holding_days: int


class MultiStrategyBacktester:
    """멀티 전략 백테스터"""
    
    def __init__(self, db_path: str = './data/pivot_strategy.db', 
                 initial_capital: float = 100_000_000):  # 1억원 초기자본
        self.db_path = db_path
        self.initial_capital = initial_capital
        self.current_capital = initial_capital
        
        # fdr_wrapper 인스턴스
        self.fdr = FDRWrapper(db_path=db_path)
        
        # 포트폴리오 상태
        self.positions: Dict[str, Position] = {}  # 현재 보유 포지션
        self.trades: List[Trade] = []  # 완료된 거래
        self.daily_values: List[Dict] = []  # 일별 자산 가치
        
        # 설정
        self.max_positions = 10  # 최대 동시 보유 종목
        self.position_size_per_strategy = 0.1  # 전략당 10% 투자
        
    def get_trading_dates(self, start_date: str, end_date: str) -> List[str]:
        """거래일 목록 반환 - fdr_wrapper 통해 DB 조회"""
        with DatabaseManager(self.db_path) as db:
            query = """
                SELECT DISTINCT date FROM stock_prices 
                WHERE date BETWEEN ? AND ?
                ORDER BY date
            """
            dates = pd.read_sql_query(query, db.conn, params=(start_date, end_date))['date'].tolist()
        return dates
    
    def get_stock_data_on_date(self, symbol: str, date: str, days_back: int = 252) -> pd.DataFrame:
        """특정 날짜 기준 과거 데이터 조회 - fdr_wrapper 사용"""
        # 시작일 계산 (days_back 만큼 이전)
        end_dt = datetime.strptime(date, '%Y-%m-%d')
        start_dt = end_dt - timedelta(days=days_back * 1.5)  # 여유분
        start_date = start_dt.strftime('%Y-%m-%d')
        
        # fdr_wrapper로 데이터 조회
        df = self.fdr.get_price(symbol, start_date, date)
        
        if df.empty:
            return pd.DataFrame()
        
        # 최근 days_back 개만 필터링
        df = df.sort_values('date')
        df = df.tail(days_back)
        
        df.columns = [c.lower() for c in df.columns]
        return df
    
    def get_stock_info(self) -> pd.DataFrame:
        """전체 종목 정보 조회 - fdr_wrapper 통해 DB 조회"""
        with DatabaseManager(self.db_path) as db:
            df = pd.read_sql_query("SELECT symbol, name, market FROM stock_info", db.conn)
        return df
    
    def calculate_ma(self, series: pd.Series, period: int) -> float:
        """이동평균 계산"""
        return series.tail(period).mean()
    
    def scan_strategies(self, df: pd.DataFrame, symbol: str, 
                        all_stocks_data: Dict[str, pd.DataFrame]) -> Dict:
        """5가지 전략 분석"""
        if len(df) < 60:
            return None
        
        latest = df.iloc[-1]
        current_price = latest['close']
        current_volume = latest['volume']
        amount = current_price * current_volume
        
        results = {
            'symbol': symbol,
            'price': current_price,
            'amount': amount,
            'strategies': []
        }
        
        # 전략 1: 거래대금 TOP 20 (별도 계산 필요)
        results['s1_eligible'] = True  # 플래그만 설정
        
        # 전략 2: 턴어라운드
        if len(df) >= 252:
            high_52w = df['high'].tail(252).max()
            from_52w_high = (current_price - high_52w) / high_52w
            hist_high = df['high'].max()
            from_hist_high = (current_price - hist_high) / hist_high
            
            if from_52w_high >= -0.10 or from_hist_high >= -0.05:
                results['strategies'].append('S2_턴어라운드')
                results['s2_from_52w'] = from_52w_high
        
        # 전략 3: 새로운 모멘텀
        if len(df) >= 20:
            avg_volume_20 = df['volume'].tail(20).mean()
            volume_ratio = current_volume / avg_volume_20 if avg_volume_20 > 0 else 0
            high_20 = df['high'].tail(20).max()
            
            prev_close = df.iloc[-2]['close'] if len(df) >= 2 else current_price
            price_change = (current_price - prev_close) / prev_close
            
            if volume_ratio >= 2.0 and (current_price >= high_20 or price_change >= 0.05):
                results['strategies'].append('S3_모멘텀')
                results['s3_volume_ratio'] = volume_ratio
        
        # 전략 4: 거래대금 2000억 첫 돌파
        if len(df) >= 60 and amount >= 2000e8:
            df['daily_amount'] = df['close'] * df['volume']
            past_60_max = df.iloc[-61:-1]['daily_amount'].max() if len(df) > 60 else 0
            if past_60_max < 2000e8:
                results['strategies'].append('S4_2000억돌파')
                results['s4_amount'] = amount
        
        # 전략 5: MA200 우상향
        if len(df) >= 200:
            ma200_current = df['close'].tail(200).mean()
            ma20_slice = df.iloc[-20:]
            if len(ma20_slice) >= 20:
                ma200_20days_ago = df.iloc[-20:]['close'].tail(200).mean()
                slope = (ma200_current - ma200_20days_ago) / ma200_20days_ago if ma200_20days_ago > 0 else 0
                if slope > 0.01:
                    results['strategies'].append('S5_MA200우상향')
                    results['s5_slope'] = slope
        
        results['strategy_count'] = len(results['strategies'])
        return results
    
    def get_top20_amount_stocks(self, date: str) -> List[Tuple[str, float, int]]:
        """특정 날짜 거래대금 TOP 20 계산"""
        conn = sqlite3.connect(self.db_path)
        
        # 해당 날짜의 모든 종목 거래대금 조회
        query = """
            SELECT symbol, close * volume as amount
            FROM stock_prices 
            WHERE date = ?
            ORDER BY amount DESC
            LIMIT 100
        """
        df = pd.read_sql_query(query, conn, params=(date,))
        conn.close()
        
        if df.empty:
            return []
        
        # TOP 20 반환
        return [(row['symbol'], row['amount'], idx+1) 
                for idx, row in df.head(20).iterrows()]
    
    def run_scan_for_date(self, date: str) -> List[Dict]:
        """특정 날짜 전체 종목 스캔"""
        # 종목 목록 로드
        stocks = self.get_stock_info()
        
        # 거래대금 TOP 20 계산
        top20 = self.get_top20_amount_stocks(date)
        top20_set = {s[0] for s in top20}
        top20_rank = {s[0]: s[2] for s in top20}
        
        results = []
        
        for _, stock in stocks.iterrows():
            symbol = stock['symbol']
            df = self.get_stock_data_on_date(symbol, date)
            
            if df.empty or len(df) < 60:
                continue
            
            scan_result = self.scan_strategies(df, symbol, {})
            if scan_result and scan_result['strategy_count'] >= 1:
                # 전략 1 체크
                if symbol in top20_set:
                    scan_result['strategies'].insert(0, f'S1_TOP20(#{top20_rank[symbol]})')
                    scan_result['strategy_count'] += 1
                    scan_result['s1_rank'] = top20_rank[symbol]
                
                scan_result['name'] = stock['name']
                scan_result['market'] = stock['market']
                results.append(scan_result)
        
        # 우선순위 정렬
        results.sort(key=lambda x: x['strategy_count'], reverse=True)
        return results
    
    def calculate_position_size(self, strategies: List[str], current_price: float) -> int:
        """포지션 크기 계산"""
        # 전략 수에 따라 가중치 부여
        weight = min(len(strategies) * 0.5, 1.0)  # 최대 100%
        invest_amount = self.current_capital * self.position_size_per_strategy * weight
        quantity = int(invest_amount / current_price)
        return max(quantity, 1)  # 최소 1주
    
    def check_exit_conditions(self, position: Position, df: pd.DataFrame, date: str) -> Optional[str]:
        """청산 조건 체크"""
        if df.empty or len(df) < 1:
            return None
        
        latest = df.iloc[-1]
        high = latest['high']
        low = latest['low']
        close = latest['close']
        
        # 손절가 체크
        if low <= position.stop_loss:
            return 'stop_loss'
        
        # 목표가 +25% 체크 (전량 청산)
        if high >= position.target_price_25:
            return 'target_25'
        
        # 목표가 +15% 체크 (부분 실현 - 시뮬레이션상 전량으로 처리)
        if high >= position.target_price_15:
            return 'target_15'
        
        # 보유 기간 체크 (20거래일)
        entry_dt = datetime.strptime(position.entry_date, '%Y-%m-%d')
        current_dt = datetime.strptime(date, '%Y-%m-%d')
        holding_days = (current_dt - entry_dt).days
        
        if holding_days >= 20:
            return 'timeout'
        
        return None
    
    def backtest(self, start_date: str = '2026-01-01', end_date: str = None):
        """백테스트 실행"""
        if end_date is None:
            end_date = datetime.now().strftime('%Y-%m-%d')
        
        print("🔥 Multi-Strategy Backtest")
        print("=" * 70)
        print(f"📅 기간: {start_date} ~ {end_date}")
        print(f"💰 초기자본: {self.initial_capital:,.0f}원")
        print()
        
        # 거래일 목록
        trading_dates = self.get_trading_dates(start_date, end_date)
        print(f"📊 분석할 거래일: {len(trading_dates)}일")
        print()
        
        # 일별 백테스트
        for i, date in enumerate(trading_dates):
            if i % 10 == 0:
                print(f"📅 {date} ({i+1}/{len(trading_dates)}) - 자산: {self.current_capital:,.0f}원")
            
            # 1. 기존 포지션 관리 (청산 체크)
            self._manage_positions(date)
            
            # 2. 새로운 종목 스캔 및 진입
            if len(self.positions) < self.max_positions:
                self._scan_and_enter(date)
            
            # 3. 일별 자산 기록
            self._record_daily_value(date)
        
        # 남은 포지션 청산 (마지막 날 종가)
        self._liquidate_all(trading_dates[-1] if trading_dates else end_date)
        
        # 결과 생성
        return self._generate_results()
    
    def _manage_positions(self, date: str):
        """보유 포지션 관리"""
        for symbol in list(self.positions.keys()):
            position = self.positions[symbol]
            df = self.get_stock_data_on_date(symbol, date, days_back=5)
            
            if df.empty:
                continue
            
            exit_reason = self.check_exit_conditions(position, df, date)
            if exit_reason:
                self._close_position(symbol, df, date, exit_reason)
    
    def _close_position(self, symbol: str, df: pd.DataFrame, date: str, reason: str):
        """포지션 청산"""
        position = self.positions.pop(symbol)
        latest = df.iloc[-1]
        
        # 청산가 결정
        if reason == 'stop_loss':
            exit_price = position.stop_loss
        elif reason == 'target_15':
            exit_price = position.target_price_15
        elif reason == 'target_25':
            exit_price = position.target_price_25
        else:
            exit_price = latest['close']
        
        # 손익 계산
        pnl = (exit_price - position.entry_price) * position.quantity
        pnl_pct = (exit_price - position.entry_price) / position.entry_price * 100
        
        # 자본 업데이트
        self.current_capital += position.entry_price * position.quantity + pnl
        
        # 거래 기록
        entry_dt = datetime.strptime(position.entry_date, '%Y-%m-%d')
        current_dt = datetime.strptime(date, '%Y-%m-%d')
        holding_days = (current_dt - entry_dt).days
        
        trade = Trade(
            symbol=symbol,
            name=position.name,
            entry_date=position.entry_date,
            exit_date=date,
            entry_price=position.entry_price,
            exit_price=exit_price,
            quantity=position.quantity,
            strategies=position.strategies,
            exit_reason=reason,
            pnl=pnl,
            pnl_pct=pnl_pct,
            holding_days=holding_days
        )
        self.trades.append(trade)
    
    def _scan_and_enter(self, date: str):
        """스캔 및 진입"""
        scan_results = self.run_scan_for_date(date)
        
        # 이미 보유 중인 종목 제외
        new_signals = [s for s in scan_results if s['symbol'] not in self.positions]
        
        # 상위 종목만 선택
        available_slots = self.max_positions - len(self.positions)
        top_signals = new_signals[:available_slots]
        
        for signal in top_signals:
            # 자본 확인
            position_size = self.calculate_position_size(
                signal['strategies'], signal['price']
            )
            invest_amount = position_size * signal['price']
            
            if invest_amount > self.current_capital * 0.5:  # 50% 이상 투자 제한
                continue
            
            # 포지션 생성
            position = Position(
                symbol=signal['symbol'],
                name=signal['name'],
                entry_date=date,
                entry_price=signal['price'],
                quantity=position_size,
                strategies=signal['strategies']
            )
            
            self.positions[signal['symbol']] = position
            self.current_capital -= invest_amount
            
            if len(self.positions) >= self.max_positions:
                break
    
    def _record_daily_value(self, date: str):
        """일별 자산 기록"""
        position_value = 0
        for symbol, position in self.positions.items():
            df = self.get_stock_data_on_date(symbol, date, days_back=1)
            if not df.empty:
                current_price = df.iloc[-1]['close']
                position_value += current_price * position.quantity
        
        total_value = self.current_capital + position_value
        self.daily_values.append({
            'date': date,
            'cash': self.current_capital,
            'position_value': position_value,
            'total_value': total_value,
            'positions': len(self.positions)
        })
    
    def _liquidate_all(self, date: str):
        """전량 청산"""
        for symbol in list(self.positions.keys()):
            position = self.positions[symbol]
            df = self.get_stock_data_on_date(symbol, date, days_back=1)
            
            if not df.empty:
                self._close_position(symbol, df, date, 'liquidation')
    
    def _generate_results(self) -> Dict:
        """백테스트 결과 생성"""
        if not self.trades:
            print("⚠️ 거래 기록 없음")
            return {}
        
        trades_df = pd.DataFrame([{
            '종목코드': t.symbol,
            '종목명': t.name,
            '진입일': t.entry_date,
            '청산일': t.exit_date,
            '진입가': t.entry_price,
            '청산가': t.exit_price,
            '수량': t.quantity,
            '전략': ','.join(t.strategies),
            '청산사유': t.exit_reason,
            '손익': t.pnl,
            '수익률': t.pnl_pct,
            '보유일': t.holding_days
        } for t in self.trades])
        
        # 저장
        output_dir = Path('./reports/multi_strategy_backtest')
        output_dir.mkdir(parents=True, exist_ok=True)
        
        trades_df.to_csv(output_dir / 'trades.csv', index=False, encoding='utf-8-sig')
        
        # 일별 가치 저장
        values_df = pd.DataFrame(self.daily_values)
        values_df.to_csv(output_dir / 'daily_values.csv', index=False, encoding='utf-8-sig')
        
        # 통계 계산
        winning_trades = trades_df[trades_df['손익'] > 0]
        losing_trades = trades_df[trades_df['손익'] <= 0]
        
        total_return = (self.current_capital - self.initial_capital) / self.initial_capital * 100
        
        stats = {
            '총거래수': len(trades_df),
            '승률': len(winning_trades) / len(trades_df) * 100 if len(trades_df) > 0 else 0,
            '총수익': trades_df['손익'].sum(),
            '평균수익률': trades_df['수익률'].mean(),
            '최대수익': trades_df['수익률'].max(),
            '최대손실': trades_df['수익률'].min(),
            '평균보유일': trades_df['보유일'].mean(),
            '초기자본': self.initial_capital,
            '최종자본': self.current_capital,
            '총수익률': total_return
        }
        
        # 전략별 성과
        strategy_performance = defaultdict(lambda: {'count': 0, 'win': 0, 'total_pnl': 0})
        for _, trade in trades_df.iterrows():
            strategies = trade['전략'].split(',')
            for strategy in strategies:
                strategy_performance[strategy]['count'] += 1
                if trade['손익'] > 0:
                    strategy_performance[strategy]['win'] += 1
                strategy_performance[strategy]['total_pnl'] += trade['손익']
        
        # 결과 출력
        print("\n" + "=" * 70)
        print("📊 백테스트 결과")
        print("=" * 70)
        print(f"\n💰 자산 변화: {self.initial_capital:,.0f}원 → {self.current_capital:,.0f}원")
        print(f"📈 총 수익률: {total_return:.2f}%")
        print(f"\n📋 거래 통계:")
        print(f"   총 거래 수: {stats['총거래수']}회")
        print(f"   승률: {stats['승률']:.1f}%")
        print(f"   평균 수익률: {stats['평균수익률']:.2f}%")
        print(f"   최대 수익: {stats['최대수익']:.2f}%")
        print(f"   최대 손실: {stats['최대손실']:.2f}%")
        print(f"   평균 보유일: {stats['평균보유일']:.1f}일")
        
        print(f"\n🎯 전략별 성과:")
        for strategy, perf in sorted(strategy_performance.items(), 
                                     key=lambda x: x[1]['total_pnl'], reverse=True):
            win_rate = perf['win'] / perf['count'] * 100 if perf['count'] > 0 else 0
            print(f"   {strategy}: {perf['count']}회 (승률 {win_rate:.1f}%), 총손익 {perf['total_pnl']:,.0f}원")
        
        print(f"\n💾 결과 저장: {output_dir}/")
        
        return {
            'stats': stats,
            'trades': trades_df,
            'daily_values': values_df,
            'strategy_performance': strategy_performance
        }


if __name__ == "__main__":
    backtester = MultiStrategyBacktester()
    results = backtester.backtest('2026-01-01')
    print("\n✅ 백테스트 완료!")
