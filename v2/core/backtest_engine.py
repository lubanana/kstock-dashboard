"""
V2 Core - Backtest Engine
백테스팅 프레임워크
"""
import pandas as pd
import numpy as np
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
from datetime import datetime, timedelta


@dataclass
class Trade:
    """개별 거래 기록"""
    entry_date: str
    exit_date: str
    code: str
    entry_price: float
    exit_price: float
    shares: int
    pnl: float
    pnl_pct: float
    exit_reason: str  # 'target', 'stop', 'time_limit'
    metadata: Dict[str, Any]


@dataclass
class BacktestResult:
    """백테스트 결과"""
    strategy_name: str
    start_date: str
    end_date: str
    total_trades: int
    winning_trades: int
    losing_trades: int
    win_rate: float
    total_return: float
    avg_return: float
    max_drawdown: float
    sharpe_ratio: float
    profit_factor: float
    trades: List[Trade]


class BacktestEngine:
    """백테스팅 엔진"""
    
    def __init__(self, 
                 data_manager,
                 stop_loss: float = -0.07,
                 take_profit: float = 0.25,
                 trailing_stop: float = 0.10,
                 max_holding_days: int = 7):
        self.data_manager = data_manager
        self.stop_loss = stop_loss
        self.take_profit = take_profit
        self.trailing_stop = trailing_stop
        self.max_holding_days = max_holding_days
        self.trades: List[Trade] = []
    
    def run(self, 
            strategy,
            start_date: str,
            end_date: str,
            codes: Optional[List[str]] = None) -> BacktestResult:
        """
        백테스트 실행
        
        Args:
            strategy: StrategyBase 인스턴스
            start_date: 시작일 (YYYY-MM-DD)
            end_date: 종료일 (YYYY-MM-DD)
            codes: 테스트할 종목 리스트 (None=전체)
        """
        self.trades = []
        
        # 날짜 범위 생성
        date_range = pd.date_range(start=start_date, end=end_date, freq='B')  # Business days
        
        print(f"🔍 백테스트 기간: {start_date} ~ {end_date}")
        print(f"📅 거래일 수: {len(date_range)}일")
        
        for current_date in date_range:
            date_str = current_date.strftime('%Y-%m-%d')
            
            # 전략 실행
            signals = strategy.run(self.data_manager, date_str, codes)
            
            # 각 신호에 대해 시뮬레이션
            for signal in signals:
                if signal.signal_type == 'buy':
                    trade = self._simulate_trade(
                        signal.code, 
                        signal.date,
                        signal.metadata
                    )
                    if trade:
                        self.trades.append(trade)
        
        return self._calculate_stats(strategy.config.name, start_date, end_date)
    
    def _simulate_trade(self, 
                       code: str, 
                       entry_date: str,
                       metadata: Dict) -> Optional[Trade]:
        """단일 거래 시뮬레이션"""
        # 진입일 데이터
        entry_df = self.data_manager.load_stock_data(code, entry_date, days=90)
        if entry_df is None or len(entry_df) < 5:
            return None
        
        entry_row = entry_df[entry_df['date'] == entry_date]
        if len(entry_row) == 0:
            return None
        
        entry_price = entry_row.iloc[0]['close']
        entry_idx = entry_df.index[entry_df['date'] == entry_date][0]
        
        # 목표가/손절가 계산
        target_price = entry_price * (1 + self.take_profit)
        stop_price = entry_price * (1 + self.stop_loss)
        
        # 보유 기간 시뮬레이션
        max_idx = min(entry_idx + self.max_holding_days + 1, len(entry_df))
        
        for i in range(entry_idx + 1, max_idx):
            current_price = entry_df.iloc[i]['close']
            current_date = entry_df.iloc[i]['date']
            
            # 손절 체크
            if current_price <= stop_price:
                return Trade(
                    entry_date=entry_date,
                    exit_date=current_date,
                    code=code,
                    entry_price=entry_price,
                    exit_price=current_price,
                    shares=100,  # 표준화
                    pnl=(current_price - entry_price) * 100,
                    pnl_pct=(current_price / entry_price - 1) * 100,
                    exit_reason='stop',
                    metadata=metadata
                )
            
            # 익절 체크
            if current_price >= target_price:
                return Trade(
                    entry_date=entry_date,
                    exit_date=current_date,
                    code=code,
                    entry_price=entry_price,
                    exit_price=current_price,
                    shares=100,
                    pnl=(current_price - entry_price) * 100,
                    pnl_pct=(current_price / entry_price - 1) * 100,
                    exit_reason='target',
                    metadata=metadata
                )
        
        # 시간제한 도달
        last_price = entry_df.iloc[max_idx - 1]['close']
        last_date = entry_df.iloc[max_idx - 1]['date']
        
        return Trade(
            entry_date=entry_date,
            exit_date=last_date,
            code=code,
            entry_price=entry_price,
            exit_price=last_price,
            shares=100,
            pnl=(last_price - entry_price) * 100,
            pnl_pct=(last_price / entry_price - 1) * 100,
            exit_reason='time_limit',
            metadata=metadata
        )
    
    def _calculate_stats(self, 
                        strategy_name: str,
                        start_date: str, 
                        end_date: str) -> BacktestResult:
        """통계 계산"""
        if not self.trades:
            return BacktestResult(
                strategy_name=strategy_name,
                start_date=start_date,
                end_date=end_date,
                total_trades=0,
                winning_trades=0,
                losing_trades=0,
                win_rate=0.0,
                total_return=0.0,
                avg_return=0.0,
                max_drawdown=0.0,
                sharpe_ratio=0.0,
                profit_factor=0.0,
                trades=[]
            )
        
        returns = [t.pnl_pct for t in self.trades]
        winning = [r for r in returns if r > 0]
        losing = [r for r in returns if r <= 0]
        
        # 누적 수익률
        total_return = sum(returns)
        
        # 최대 낙폭 (MDD)
        cumulative = np.cumsum(returns)
        running_max = np.maximum.accumulate(cumulative)
        drawdown = cumulative - running_max
        max_drawdown = abs(min(drawdown)) if len(drawdown) > 0 else 0
        
        # 샤프 비율 (단순화)
        avg_return = np.mean(returns)
        std_return = np.std(returns) if len(returns) > 1 else 1
        sharpe = (avg_return / std_return) * np.sqrt(252) if std_return > 0 else 0
        
        # Profit Factor
        gross_profit = sum(w for w in winning)
        gross_loss = abs(sum(l for l in losing))
        profit_factor = gross_profit / gross_loss if gross_loss > 0 else 0
        
        return BacktestResult(
            strategy_name=strategy_name,
            start_date=start_date,
            end_date=end_date,
            total_trades=len(self.trades),
            winning_trades=len(winning),
            losing_trades=len(losing),
            win_rate=len(winning) / len(returns) * 100,
            total_return=total_return,
            avg_return=avg_return,
            max_drawdown=max_drawdown,
            sharpe_ratio=sharpe,
            profit_factor=profit_factor,
            trades=self.trades
        )
    
    def generate_report(self, result: BacktestResult) -> str:
        """백테스트 리포트 생성"""
        lines = [
            "=" * 60,
            f"📊 백테스트 결과: {result.strategy_name}",
            "=" * 60,
            f"📅 기간: {result.start_date} ~ {result.end_date}",
            "",
            "📈 성과 지표",
            f"   총 거래: {result.total_trades}회",
            f"   승률: {result.win_rate:.1f}%",
            f"   총 수익률: {result.total_return:+.2f}%",
            f"   평균 수익률: {result.avg_return:+.2f}%",
            f"   최대 낙폭: {result.max_drawdown:.2f}%",
            f"   샤프 비율: {result.sharpe_ratio:.2f}",
            f"   Profit Factor: {result.profit_factor:.2f}",
            "",
        ]
        
        if result.trades:
            lines.append("📋 거래 내역 (Top 10)")
            for i, trade in enumerate(result.trades[:10], 1):
                emoji = "🟢" if trade.pnl_pct > 0 else "🔴"
                lines.append(f"   {i}. {trade.code}: {trade.pnl_pct:+.2f}% ({trade.exit_reason})")
        
        lines.append("=" * 60)
        return "\n".join(lines)
