#!/usr/bin/env python3
"""
Jesse Livermore Pivot Point Strategy Backtester
제시 리버모어 전환점 + 피라미딩 백테스팅 시스템

핵심 전략:
1. Pivot Point 돌파: 20일(또는 60일) 신고가 돌파
2. 거래량 확인: 당일 거래량 > 20일 평균의 150%
3. 피라미딩:
   - 1차: 30% 매수
   - 2차: +5% 상승 시 30% 추가
   - 3차: +5% 상승 시 40% 추가
4. 리스크 관리:
   - 손절: 평균단가 -10%
   - 익절: 최고점 -15% (트레일링 스톱)
"""

import os
import json
import pandas as pd
import numpy as np
import FinanceDataReader as fdr
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Tuple
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from dataclasses import dataclass, field
from enum import Enum


class TradeStatus(Enum):
    """거래 상태"""
    IDLE = "대기"
    POSITION_1 = "1차 진입"
    POSITION_2 = "2차 진입"
    POSITION_3 = "3차 진입"
    CLOSED = "청산"


@dataclass
class Trade:
    """개별 거래 기록"""
    entry_date: datetime
    code: str
    name: str
    entries: List[Dict] = field(default_factory=list)  # 진입 기록들
    exit_date: Optional[datetime] = None
    exit_price: float = 0.0
    exit_reason: str = ""
    status: TradeStatus = TradeStatus.IDLE
    
    @property
    def avg_entry_price(self) -> float:
        """평균 진입가"""
        if not self.entries:
            return 0.0
        total_cost = sum(e['price'] * e['shares'] for e in self.entries)
        total_shares = sum(e['shares'] for e in self.entries)
        return total_cost / total_shares if total_shares > 0 else 0.0
    
    @property
    def total_shares(self) -> int:
        """총 보유 주식 수"""
        return sum(e['shares'] for e in self.entries)
    
    @property
    def total_invested(self) -> float:
        """총 투자금액"""
        return sum(e['price'] * e['shares'] for e in self.entries)


class LivermoreBacktester:
    """
    제시 리버모어 전환점 백테스터
    
    Parameters:
    -----------
    initial_capital : float
        초기 자본금 (기본값: 1억원)
    pivot_period : int
        전환점 계산 기간 (기본값: 20일)
    volume_threshold : float
        거래량 임계값 (기본값: 1.5 = 150%)
    pyramid_levels : List[float]
        피라미딩 비율 [0.3, 0.3, 0.4]
    stop_loss_pct : float
        손절 비율 (기본값: 0.10 = 10%)
    trailing_stop_pct : float
        트레일링 스톱 비율 (기본값: 0.15 = 15%)
    pyramid_step_pct : float
        피라미딩 진입 간격 (기본값: 0.05 = 5%)
    """
    
    def __init__(
        self,
        initial_capital: float = 100_000_000,  # 1억원
        pivot_period: int = 20,
        volume_threshold: float = 1.5,
        pyramid_levels: List[float] = None,
        stop_loss_pct: float = 0.10,
        trailing_stop_pct: float = 0.15,
        pyramid_step_pct: float = 0.05
    ):
        self.initial_capital = initial_capital
        self.pivot_period = pivot_period
        self.volume_threshold = volume_threshold
        self.pyramid_levels = pyramid_levels or [0.3, 0.3, 0.4]
        self.stop_loss_pct = stop_loss_pct
        self.trailing_stop_pct = trailing_stop_pct
        self.pyramid_step_pct = pyramid_step_pct
        
        self.trades: List[Trade] = []
        self.current_trade: Optional[Trade] = None
        self.capital = initial_capital
        self.portfolio_value = initial_capital
        self.equity_curve: List[Dict] = []
        
    def calculate_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        기술적 지표 계산 (pandas_ta 사용)
        
        Parameters:
        -----------
        df : pd.DataFrame
            OHLCV 데이터
            
        Returns:
        --------
        pd.DataFrame
            지표가 추가된 데이터프레임
        """
        df = df.copy()
        
        # 20일/60일 최고가 (Pivot Point)
        df['high_20'] = df['High'].rolling(self.pivot_period).max()
        df['high_60'] = df['High'].rolling(60).max()
        
        # 20일 평균 거래량
        df['volume_ma20'] = df['Volume'].rolling(20).mean()
        df['volume_ratio'] = df['Volume'] / df['volume_ma20']
        
        # 당일 종가가 전환점 돌파 여부
        df['pivot_break'] = (df['Close'] > df['high_20'].shift(1)) | (df['Close'] > df['high_60'].shift(1))
        
        # 거래량 조건 확인
        df['volume_confirm'] = df['volume_ratio'] >= self.volume_threshold
        
        # 진입 신호: 전환점 돌파 + 거래량 확인
        df['entry_signal'] = df['pivot_break'] & df['volume_confirm']
        
        # ATR (변동성) - 수동 계산
        df['tr1'] = df['High'] - df['Low']
        df['tr2'] = abs(df['High'] - df['Close'].shift(1))
        df['tr3'] = abs(df['Low'] - df['Close'].shift(1))
        df['tr'] = df[['tr1', 'tr2', 'tr3']].max(axis=1)
        df['atr'] = df['tr'].rolling(14).mean()
        
        return df
    
    def backtest(self, code: str, start_date: str, end_date: str) -> Dict:
        """
        단일 종목 백테스팅
        
        Parameters:
        -----------
        code : str
            종목 코드
        start_date : str
            시작일 (YYYY-MM-DD)
        end_date : str
            종료일 (YYYY-MM-DD)
            
        Returns:
        --------
        Dict
            백테스트 결과
        """
        # 데이터 수집
        df = fdr.DataReader(code, start_date, end_date)
        if df is None or len(df) < self.pivot_period + 20:
            return {'error': 'Insufficient data'}
        
        # 종목명 가져오기
        try:
            stock_info = fdr.StockListing('KOSPI')
            name = stock_info[stock_info['Code'] == code]['Name'].values[0]
        except:
            try:
                stock_info = fdr.StockListing('KOSDAQ')
                name = stock_info[stock_info['Code'] == code]['Name'].values[0]
            except:
                name = code
        
        # 지표 계산
        df = self.calculate_indicators(df)
        
        # 백테스팅 시뮬레이션
        self.current_trade = None
        self.capital = self.initial_capital
        self.trades = []
        self.equity_curve = []
        
        highest_price = 0  # 트레일링 스톱용
        
        for idx, row in df.iterrows():
            current_price = row['Close']
            current_date = idx
            
            # 자본 업데이트
            if self.current_trade:
                position_value = self.current_trade.total_shares * current_price
                self.portfolio_value = self.capital + position_value
            else:
                self.portfolio_value = self.capital
            
            self.equity_curve.append({
                'date': current_date,
                'portfolio_value': self.portfolio_value,
                'cash': self.capital,
                'position_value': position_value if self.current_trade else 0
            })
            
            # 현재 포지션이 있는 경우
            if self.current_trade:
                avg_price = self.current_trade.avg_entry_price
                position_count = len(self.current_trade.entries)
                
                # 최고가 업데이트 (트레일링 스톱용)
                highest_price = max(highest_price, current_price)
                
                # 1. 손절 체크 (-10%)
                if current_price <= avg_price * (1 - self.stop_loss_pct):
                    self._close_position(
                        current_date, current_price, 
                        f"Stop Loss (-{self.stop_loss_pct*100:.0f}%)"
                    )
                    highest_price = 0
                    continue
                
                # 2. 트레일링 스톱 체크 (-15% from high)
                if current_price <= highest_price * (1 - self.trailing_stop_pct):
                    self._close_position(
                        current_date, current_price,
                        f"Trailing Stop (-{self.trailing_stop_pct*100:.0f}% from high)"
                    )
                    highest_price = 0
                    continue
                
                # 3. 피라미딩 체크
                if position_count < 3:
                    next_entry_price = avg_price * (1 + self.pyramid_step_pct * position_count)
                    
                    if current_price >= next_entry_price:
                        self._add_position(
                            current_date, current_price, 
                            self.pyramid_levels[position_count],
                            position_count + 1
                        )
            
            # 새로운 진입 신호 확인
            elif row['entry_signal'] and self.capital > 0:
                self._open_position(code, name, current_date, current_price)
                highest_price = current_price
        
        # 미청산 포지션이 있으면 마지막 날에 청산
        if self.current_trade:
            last_price = df['Close'].iloc[-1]
            last_date = df.index[-1]
            self._close_position(last_date, last_price, "End of Backtest")
        
        # 결과 계산
        return self._calculate_results(df, code, name)
    
    def _open_position(self, code: str, name: str, date: datetime, price: float):
        """1차 포지션 진입"""
        self.current_trade = Trade(
            entry_date=date,
            code=code,
            name=name,
            status=TradeStatus.POSITION_1
        )
        
        # 1차 진입 (30%)
        invest_amount = self.capital * self.pyramid_levels[0]
        shares = int(invest_amount / price)
        
        if shares > 0:
            self.current_trade.entries.append({
                'date': date,
                'price': price,
                'shares': shares,
                'level': 1,
                'amount': shares * price
            })
            self.capital -= shares * price
    
    def _add_position(self, date: datetime, price: float, ratio: float, level: int):
        """피라미딩 추가 진입"""
        if not self.current_trade:
            return
        
        invest_amount = self.initial_capital * ratio
        shares = int(invest_amount / price)
        
        if shares > 0 and self.capital >= shares * price:
            self.current_trade.entries.append({
                'date': date,
                'price': price,
                'shares': shares,
                'level': level,
                'amount': shares * price
            })
            self.capital -= shares * price
            self.current_trade.status = getattr(TradeStatus, f'POSITION_{level}')
    
    def _close_position(self, date: datetime, price: float, reason: str):
        """포지션 청산"""
        if not self.current_trade:
            return
        
        self.current_trade.exit_date = date
        self.current_trade.exit_price = price
        self.current_trade.exit_reason = reason
        self.current_trade.status = TradeStatus.CLOSED
        
        # 자본 회복
        proceeds = self.current_trade.total_shares * price
        self.capital += proceeds
        
        self.trades.append(self.current_trade)
        self.current_trade = None
    
    def _calculate_results(self, df: pd.DataFrame, code: str, name: str) -> Dict:
        """백테스트 결과 계산"""
        if not self.trades:
            return {
                'code': code,
                'name': name,
                'total_trades': 0,
                'win_rate': 0,
                'final_return': 0,
                'mdd': 0
            }
        
        # 승률 계산
        wins = sum(1 for t in self.trades if t.exit_price > t.avg_entry_price)
        win_rate = wins / len(self.trades) * 100
        
        # 최종 수익률
        final_value = self.equity_curve[-1]['portfolio_value'] if self.equity_curve else self.initial_capital
        total_return = (final_value - self.initial_capital) / self.initial_capital * 100
        
        # MDD 계산
        equity_df = pd.DataFrame(self.equity_curve)
        equity_df['peak'] = equity_df['portfolio_value'].cummax()
        equity_df['drawdown'] = (equity_df['portfolio_value'] - equity_df['peak']) / equity_df['peak'] * 100
        mdd = equity_df['drawdown'].min()
        
        # 거래 내역 DataFrame
        trades_df = pd.DataFrame([
            {
                '진입일': t.entry_date,
                '종목': t.name,
                '코드': t.code,
                '진입단가': t.avg_entry_price,
                '청산일': t.exit_date,
                '청산가': t.exit_price,
                '수익률': (t.exit_price - t.avg_entry_price) / t.avg_entry_price * 100,
                '청산사유': t.exit_reason,
                '진입횟수': len(t.entries)
            }
            for t in self.trades
        ])
        
        return {
            'code': code,
            'name': name,
            'total_trades': len(self.trades),
            'winning_trades': wins,
            'losing_trades': len(self.trades) - wins,
            'win_rate': win_rate,
            'initial_capital': self.initial_capital,
            'final_capital': final_value,
            'total_return_pct': total_return,
            'mdd_pct': mdd,
            'trades_df': trades_df,
            'equity_curve': equity_df
        }
    
    def plot_results(self, results: Dict, df: pd.DataFrame = None):
        """
        백테스트 결과 시각화
        
        Parameters:
        -----------
        results : Dict
            백테스트 결과
        df : pd.DataFrame
            원본 가격 데이터
        """
        fig, axes = plt.subplots(3, 1, figsize=(14, 12))
        
        # 1. 가격 차트 + 매매 시점
        if df is not None:
            ax1 = axes[0]
            ax1.plot(df.index, df['Close'], label='Close Price', color='black', linewidth=1)
            
            # 매수/매도 시점 표시
            for trade in self.trades:
                # 진입점
                for entry in trade.entries:
                    ax1.scatter(entry['date'], entry['price'], 
                              marker='^', color='green', s=100, zorder=5)
                
                # 청산점
                ax1.scatter(trade.exit_date, trade.exit_price,
                          marker='v', color='red', s=100, zorder=5)
            
            ax1.set_title(f"{results['name']} ({results['code']}) - Livermore Strategy", fontsize=14)
            ax1.set_ylabel('Price')
            ax1.legend()
            ax1.grid(True, alpha=0.3)
        
        # 2. 자본 곡선
        ax2 = axes[1]
        if 'equity_curve' in results and not results['equity_curve'].empty:
            equity = results['equity_curve']
            ax2.plot(equity['date'], equity['portfolio_value'], label='Portfolio Value', color='blue')
            ax2.axhline(y=self.initial_capital, color='gray', linestyle='--', label='Initial Capital')
            ax2.set_title('Equity Curve', fontsize=14)
            ax2.set_ylabel('Value (KRW)')
            ax2.legend()
            ax2.grid(True, alpha=0.3)
        
        # 3. 낙폭 (Drawdown)
        ax3 = axes[2]
        if 'equity_curve' in results and not results['equity_curve'].empty:
            equity = results['equity_curve']
            ax3.fill_between(equity['date'], equity['drawdown'], 0, color='red', alpha=0.3)
            ax3.plot(equity['date'], equity['drawdown'], color='red', linewidth=1)
            ax3.set_title(f'Drawdown (MDD: {results["mdd_pct"]:.2f}%)', fontsize=14)
            ax3.set_ylabel('Drawdown (%)')
            ax3.set_xlabel('Date')
            ax3.grid(True, alpha=0.3)
        
        plt.tight_layout()
        plt.savefig(f"reports/livermore_backtest_{results['code']}.png", dpi=150, bbox_inches='tight')
        plt.show()
        
        print(f"📊 차트 저장됨: reports/livermore_backtest_{results['code']}.png")


def run_single_backtest(code: str = '005930', days: int = 500):
    """
    단일 종목 백테스트 실행 예시
    
    Parameters:
    -----------
    code : str
        종목 코드 (기본값: 삼성전자 005930)
    days : int
        백테스트 기간 (일)
    """
    end_date = datetime.now()
    start_date = end_date - timedelta(days=days)
    
    print("="*70)
    print("🚀 Jesse Livermore Pivot Point Backtest")
    print("="*70)
    print(f"종목: {code}")
    print(f"기간: {start_date.strftime('%Y-%m-%d')} ~ {end_date.strftime('%Y-%m-%d')}")
    print("="*70)
    
    # 백테스터 생성
    backtester = LivermoreBacktester(
        initial_capital=100_000_000,  # 1억원
        pivot_period=20,
        volume_threshold=1.5,
        stop_loss_pct=0.10,
        trailing_stop_pct=0.15
    )
    
    # 백테스트 실행
    results = backtester.backtest(
        code=code,
        start_date=start_date.strftime('%Y-%m-%d'),
        end_date=end_date.strftime('%Y-%m-%d')
    )
    
    if 'error' in results:
        print(f"❌ 오류: {results['error']}")
        return
    
    # 결과 출력
    print("\n📊 백테스트 결과")
    print("-"*70)
    print(f"종목: {results['name']} ({results['code']})")
    print(f"총 거래 횟수: {results['total_trades']}")
    print(f"승리: {results['winning_trades']} | 패배: {results['losing_trades']}")
    print(f"승률: {results['win_rate']:.1f}%")
    print(f"초기 자본: ₩{results['initial_capital']:,.0f}")
    print(f"최종 자본: ₩{results['final_capital']:,.0f}")
    print(f"총 수익률: {results['total_return_pct']:+.2f}%")
    print(f"최대 낙폭 (MDD): {results['mdd_pct']:.2f}%")
    print("="*70)
    
    # 거래 내역 출력
    if not results['trades_df'].empty:
        print("\n📋 거래 내역:")
        print(results['trades_df'].to_string(index=False))
    
    # 차트 생성
    df = fdr.DataReader(code, start_date.strftime('%Y-%m-%d'), end_date.strftime('%Y-%m-%d'))
    backtester.plot_results(results, df)
    
    return results


if __name__ == '__main__':
    import sys
    
    # 예시 실행
    if len(sys.argv) > 1:
        code = sys.argv[1]
        days = int(sys.argv[2]) if len(sys.argv) > 2 else 500
    else:
        code = '005930'  # 삼성전자
        days = 500
    
    run_single_backtest(code, days)
