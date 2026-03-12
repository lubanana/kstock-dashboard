#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Korean Stock Pivot Point Strategy Backtester
============================================
한국 주식 시장(KOSPI/KOSDAQ) 피벗 포인트 전략 백테스팅 프로그램

전략 요약:
- 진입: 20일/60일 신고가 돌파 + 거래량 150% 이상
- 피라미딩: 30% → 30% → 40% (5% 상승마다 추가 진입)
- 손절: 평균단가 -10%
- 익절: 최고점 대비 -15% (트레일링 스탑)

Dependencies:
    pip install finance-datareader pandas pandas-ta matplotlib plotly
"""

import pandas as pd
import numpy as np
import FinanceDataReader as fdr
import pandas_ta as ta
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple
import warnings
warnings.filterwarnings('ignore')


@dataclass
class TradeRecord:
    """개별 거래 기록"""
    entry_date: datetime
    exit_date: Optional[datetime] = None
    entry_price: float = 0.0
    exit_price: float = 0.0
    shares_1st: int = 0  # 1차 진입 주식 수
    shares_2nd: int = 0  # 2차 진입 주식 수
    shares_3rd: int = 0  # 3차 진입 주식 수
    avg_cost: float = 0.0  # 평균 매수단가
    highest_price: float = 0.0  # 보유 중 최고가 (트레일링 스탑용)
    total_invested: float = 0.0  # 총 투자금액
    pnl: float = 0.0  # 손익
    return_pct: float = 0.0  # 수익률
    exit_reason: str = ""  # 청산 사유 (stop_loss / take_profit / end_of_data)


@dataclass
class BacktestResult:
    """백테스트 결과"""
    trades: List[TradeRecord] = field(default_factory=list)
    equity_curve: pd.DataFrame = field(default_factory=pd.DataFrame)
    final_return: float = 0.0
    mdd: float = 0.0
    win_rate: float = 0.0
    profit_factor: float = 0.0


class PivotPointStrategy:
    """
    피벗 포인트 전략 백테스터
    
    Parameters:
    -----------
    symbol : str
        종목코드 (예: '005930' - 삼성전자)
    start_date : str
        시작일 (YYYY-MM-DD)
    end_date : str
        종료일 (YYYY-MM-DD)
    initial_capital : float
        초기 자본금
    pivot_period : int
        피벗 포인트 계산 기간 (20 또는 60)
    volume_threshold : float
        거래량 임계값 (1.5 = 150%)
    """
    
    def __init__(
        self,
        symbol: str,
        start_date: str,
        end_date: str,
        initial_capital: float = 10_000_000,  # 1000만원
        pivot_period: int = 20,
        volume_threshold: float = 1.5,
        pyramiding_pct_1: float = 0.30,  # 1차 진입 비율
        pyramiding_pct_2: float = 0.30,  # 2차 진입 비율
        pyramiding_pct_3: float = 0.40,  # 3차 진입 비율
        pyramiding_trigger: float = 0.05,  # 피라미딩 트리거 (5%)
        stop_loss_pct: float = 0.10,  # 손절 -10%
        trailing_stop_pct: float = 0.15,  # 트레일링 스탑 -15%
    ):
        self.symbol = symbol
        self.start_date = start_date
        self.end_date = end_date
        self.initial_capital = initial_capital
        self.pivot_period = pivot_period
        self.volume_threshold = volume_threshold
        
        # 피라미딩 설정
        self.pyramiding_pct = [pyramiding_pct_1, pyramiding_pct_2, pyramiding_pct_3]
        self.pyramiding_trigger = pyramiding_trigger
        
        # 리스크 관리 설정
        self.stop_loss_pct = stop_loss_pct
        self.trailing_stop_pct = trailing_stop_pct
        
        # 데이터 저장
        self.data: Optional[pd.DataFrame] = None
        self.trades: List[TradeRecord] = []
        
    def fetch_data(self) -> pd.DataFrame:
        """
        FinanceDataReader로 주가 데이터 수집
        """
        print(f"📊 {self.symbol} 데이터 수집 중...")
        
        # 데이터 수집 (시작일보다 pivot_period만큼 더 가져와서 계산용)
        fetch_start = (datetime.strptime(self.start_date, '%Y-%m-%d') - 
                      timedelta(days=self.pivot_period * 2)).strftime('%Y-%m-%d')
        
        df = fdr.DataReader(self.symbol, fetch_start, self.end_date)
        
        if df.empty:
            raise ValueError(f"데이터를 가져올 수 없습니다: {self.symbol}")
        
        # 컬럼명 표준화
        df.columns = [col.lower() for col in df.columns]
        
        # 필요한 컬럼 확인
        required_cols = ['open', 'high', 'low', 'close', 'volume']
        for col in required_cols:
            if col not in df.columns:
                raise ValueError(f"필수 컬럼 누락: {col}")
        
        # 인덱스 정리
        df.index = pd.to_datetime(df.index)
        df = df.sort_index()
        
        # 실제 분석 시작일부터 필터링
        df = df[df.index >= self.start_date]
        
        self.data = df
        print(f"✅ {len(df)}일 분의 데이터 수집 완료")
        return df
    
    def calculate_indicators(self) -> pd.DataFrame:
        """
        기술적 지표 계산
        """
        df = self.data.copy()
        
        # 피벗 포인트 (N일 최고가)
        df[f'high_{self.pivot_period}'] = df['high'].rolling(window=self.pivot_period).max()
        
        # 거래량 이동평균
        df['volume_ma20'] = df['volume'].rolling(window=20).mean()
        
        # 피벗 돌파 신호
        df['pivot_break'] = df['close'] > df[f'high_{self.pivot_period}'].shift(1)
        
        # 거래량 조건
        df['volume_spike'] = df['volume'] > (df['volume_ma20'].shift(1) * self.volume_threshold)
        
        # 진입 신호 (피벗 돌파 + 거래량 급증)
        df['entry_signal'] = df['pivot_break'] & df['volume_spike']
        
        # Pandas TA 추가 지표 (최적화용)
        # RSI
        df.ta.rsi(length=14, append=True)
        
        # 볼린저 밴드
        df.ta.bbands(length=20, append=True)
        
        # MACD
        df.ta.macd(append=True)
        
        # ATR (변동성)
        df.ta.atr(length=14, append=True)
        
        return df
    
    def run_backtest(self) -> BacktestResult:
        """
        백테스트 실행
        """
        if self.data is None:
            self.fetch_data()
        
        df = self.calculate_indicators()
        
        # 결과 DataFrame 준비
        df['position'] = 0  # 0: 무포지션, 1~3: 피라미딩 단계
        df['cash'] = self.initial_capital
        df['holdings'] = 0.0
        df['total_value'] = self.initial_capital
        df['shares'] = 0
        
        current_trade: Optional[TradeRecord] = None
        position_level = 0  # 0, 1, 2, 3
        
        print(f"🔍 백테스트 실행 중... ({self.start_date} ~ {self.end_date})")
        
        for i in range(1, len(df)):
            date = df.index[i]
            prev_date = df.index[i-1]
            
            row = df.iloc[i]
            prev_row = df.iloc[i-1]
            
            # 현재 포지션 복사
            df.loc[date, 'cash'] = df.loc[prev_date, 'cash']
            df.loc[date, 'shares'] = df.loc[prev_date, 'shares']
            
            if current_trade is None:
                # 무포지션 상태 - 진입 신호 확인
                if row['entry_signal'] and not pd.isna(row[f'high_{self.pivot_period}']):
                    # 1차 진입
                    entry_amount = self.initial_capital * self.pyramiding_pct[0]
                    shares = int(entry_amount / row['close'])
                    cost = shares * row['close']
                    
                    if shares > 0 and df.loc[prev_date, 'cash'] >= cost:
                        current_trade = TradeRecord(
                            entry_date=date,
                            entry_price=row['close'],
                            shares_1st=shares,
                            avg_cost=row['close'],
                            highest_price=row['close'],
                            total_invested=cost
                        )
                        
                        df.loc[date, 'cash'] -= cost
                        df.loc[date, 'shares'] = shares
                        position_level = 1
                        
                        print(f"  📈 1차 진입: {date.strftime('%Y-%m-%d')} @ {row['close']:,.0f}원 ({shares}주)")
            
            else:
                # 포지션 보유 중
                current_price = row['close']
                shares = df.loc[prev_date, 'shares']
                
                # 최고가 업데이트 (트레일링 스탑용)
                if current_price > current_trade.highest_price:
                    current_trade.highest_price = current_price
                
                # 2차 진입 체크 (1차 진입가 대비 5% 상승)
                if position_level == 1:
                    trigger_price = current_trade.entry_price * (1 + self.pyramiding_trigger)
                    if current_price >= trigger_price:
                        entry_amount = self.initial_capital * self.pyramiding_pct[1]
                        new_shares = int(entry_amount / current_price)
                        cost = new_shares * current_price
                        
                        if new_shares > 0 and df.loc[prev_date, 'cash'] >= cost:
                            # 평균단가 재계산
                            total_shares = shares + new_shares
                            total_cost = (current_trade.avg_cost * shares) + cost
                            current_trade.avg_cost = total_cost / total_shares
                            current_trade.shares_2nd = new_shares
                            current_trade.total_invested += cost
                            
                            df.loc[date, 'cash'] -= cost
                            df.loc[date, 'shares'] = total_shares
                            position_level = 2
                            shares = total_shares
                            
                            print(f"  📈 2차 진입: {date.strftime('%Y-%m-%d')} @ {current_price:,.0f}원 ({new_shares}주)")
                
                # 3차 진입 체크 (2차 진입가 대비 5% 상승)
                elif position_level == 2:
                    # 2차 진입가 계산
                    second_entry_price = current_trade.entry_price * (1 + self.pyramiding_trigger)
                    trigger_price = second_entry_price * (1 + self.pyramiding_trigger)
                    
                    if current_price >= trigger_price:
                        entry_amount = self.initial_capital * self.pyramiding_pct[2]
                        new_shares = int(entry_amount / current_price)
                        cost = new_shares * current_price
                        
                        if new_shares > 0 and df.loc[prev_date, 'cash'] >= cost:
                            total_shares = shares + new_shares
                            total_cost = (current_trade.avg_cost * shares) + cost
                            current_trade.avg_cost = total_cost / total_shares
                            current_trade.shares_3rd = new_shares
                            current_trade.total_invested += cost
                            
                            df.loc[date, 'cash'] -= cost
                            df.loc[date, 'shares'] = total_shares
                            position_level = 3
                            shares = total_shares
                            
                            print(f"  📈 3차 진입: {date.strftime('%Y-%m-%d')} @ {current_price:,.0f}원 ({new_shares}주)")
                
                # 손절 체크 (-10%)
                stop_price = current_trade.avg_cost * (1 - self.stop_loss_pct)
                if current_price <= stop_price:
                    # 전량 매도
                    revenue = shares * current_price
                    df.loc[date, 'cash'] += revenue
                    df.loc[date, 'shares'] = 0
                    
                    current_trade.exit_date = date
                    current_trade.exit_price = current_price
                    current_trade.pnl = revenue - current_trade.total_invested
                    current_trade.return_pct = (current_trade.pnl / current_trade.total_invested) * 100
                    current_trade.exit_reason = 'stop_loss'
                    
                    self.trades.append(current_trade)
                    print(f"  🔴 손절: {date.strftime('%Y-%m-%d')} @ {current_price:,.0f}원 (수익률: {current_trade.return_pct:+.2f}%)")
                    
                    current_trade = None
                    position_level = 0
                    continue
                
                # 트레일링 스탑 체크 (-15% from highest)
                trailing_stop_price = current_trade.highest_price * (1 - self.trailing_stop_pct)
                if current_price <= trailing_stop_price and current_price > current_trade.avg_cost:
                    # 익절
                    revenue = shares * current_price
                    df.loc[date, 'cash'] += revenue
                    df.loc[date, 'shares'] = 0
                    
                    current_trade.exit_date = date
                    current_trade.exit_price = current_price
                    current_trade.pnl = revenue - current_trade.total_invested
                    current_trade.return_pct = (current_trade.pnl / current_trade.total_invested) * 100
                    current_trade.exit_reason = 'take_profit'
                    
                    self.trades.append(current_trade)
                    print(f"  🟢 익절: {date.strftime('%Y-%m-%d')} @ {current_price:,.0f}원 (수익률: {current_trade.return_pct:+.2f}%, 최고: {current_trade.highest_price:,.0f})")
                    
                    current_trade = None
                    position_level = 0
                    continue
            
            # 포지션 평가액 업데이트
            df.loc[date, 'holdings'] = df.loc[date, 'shares'] * row['close']
            df.loc[date, 'total_value'] = df.loc[date, 'cash'] + df.loc[date, 'holdings']
        
        # 미청산 포지션이 있으면 마지막 날에 강제 청산
        if current_trade is not None:
            last_date = df.index[-1]
            last_price = df.loc[last_date, 'close']
            shares = df.loc[last_date, 'shares']
            
            revenue = shares * last_price
            df.loc[last_date, 'cash'] += revenue
            df.loc[last_date, 'shares'] = 0
            
            current_trade.exit_date = last_date
            current_trade.exit_price = last_price
            current_trade.pnl = revenue - current_trade.total_invested
            current_trade.return_pct = (current_trade.pnl / current_trade.total_invested) * 100
            current_trade.exit_reason = 'end_of_data'
            
            self.trades.append(current_trade)
            print(f"  ⏹️  강제청산: {last_date.strftime('%Y-%m-%d')} @ {last_price:,.0f}원 (수익률: {current_trade.return_pct:+.2f}%)")
        
        # 결과 계산
        result = self._calculate_results(df)
        return result
    
    def _calculate_results(self, df: pd.DataFrame) -> BacktestResult:
        """
        백테스트 결과 계산
        """
        # 최종 수익률
        final_value = df['total_value'].iloc[-1]
        final_return = ((final_value - self.initial_capital) / self.initial_capital) * 100
        
        # MDD 계산
        df['peak'] = df['total_value'].cummax()
        df['drawdown'] = (df['total_value'] - df['peak']) / df['peak'] * 100
        mdd = df['drawdown'].min()
        
        # 승률 계산
        if self.trades:
            wins = sum(1 for t in self.trades if t.pnl > 0)
            win_rate = (wins / len(self.trades)) * 100
            
            # Profit Factor
            gross_profit = sum(t.pnl for t in self.trades if t.pnl > 0)
            gross_loss = abs(sum(t.pnl for t in self.trades if t.pnl < 0))
            profit_factor = gross_profit / gross_loss if gross_loss > 0 else float('inf')
        else:
            win_rate = 0
            profit_factor = 0
        
        # 거래 기록 DataFrame 생성
        trades_df = pd.DataFrame([
            {
                '진입일': t.entry_date,
                '청산일': t.exit_date,
                '진입가': t.entry_price,
                '청산가': t.exit_price,
                '1차주식수': t.shares_1st,
                '2차주식수': t.shares_2nd,
                '3차주식수': t.shares_3rd,
                '평균단가': t.avg_cost,
                '투자금액': t.total_invested,
                '손익': t.pnl,
                '수익률(%)': t.return_pct,
                '청산사유': t.exit_reason
            }
            for t in self.trades
        ])
        
        result = BacktestResult(
            trades=self.trades,
            equity_curve=df[['cash', 'holdings', 'total_value', 'drawdown']].copy(),
            final_return=final_return,
            mdd=mdd,
            win_rate=win_rate,
            profit_factor=profit_factor
        )
        
        # 결과 출력
        self._print_results(result, trades_df)
        
        return result, trades_df
    
    def _print_results(self, result: BacktestResult, trades_df: pd.DataFrame):
        """
        결과 출력
        """
        print("\n" + "="*60)
        print("📊 백테스트 결과")
        print("="*60)
        print(f"총 거래 횟수: {len(self.trades)}회")
        print(f"승률: {result.win_rate:.1f}%")
        print(f"Profit Factor: {result.profit_factor:.2f}")
        print(f"\n최종 수익률: {result.final_return:+.2f}%")
        print(f"최대 낙폭 (MDD): {result.mdd:.2f}%")
        print(f"\n초기 자본: {self.initial_capital:,.0f}원")
        print(f"최종 자산: {result.equity_curve['total_value'].iloc[-1]:,.0f}원")
        print("="*60)
        
        if not trades_df.empty:
            print("\n📋 거래 내역:")
            print(trades_df.to_string(index=False))


def main():
    """
    메인 실행 함수 - 예시
    """
    # 삼성전자 (005930) 백테스트 예시
    strategy = PivotPointStrategy(
        symbol='005930',  # 삼성전자
        start_date='2024-01-01',
        end_date='2024-12-31',
        initial_capital=10_000_000,  # 1000만원
        pivot_period=20,  # 20일 신고가
        volume_threshold=1.5,  # 거래량 150%
    )
    
    result, trades_df = strategy.run_backtest()
    
    return result, trades_df


if __name__ == "__main__":
    result, trades_df = main()
