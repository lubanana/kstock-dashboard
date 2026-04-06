"""
D+ Leading Stock Trading Strategy (D플러스 주도주 매매법)
Based on 대왕개미 홍인기's YouTube Video Analysis
Video: https://youtu.be/cI9XTnBS5JQ

Core Strategy:
- Trade the strongest leader stocks in dominant themes for 2-3 days
- Enter after confirming theme and leader around 9:30 AM
- Take partial profits, hold overnight, swing trade D+1 and D+2
- Use market crashes as buying opportunities for leaders
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Optional
import sqlite3


class DPlusLeadingStockStrategy:
    """
    D+ 주도주 매매법
    
    Key Rules:
    1. Theme Detection: Multiple stocks in same sector hit limit up
    2. Leader Selection: Pick the strongest leader (not small caps)
    3. Entry: Around 9:30 AM after confirming theme
    4. Management: Partial profit at limit up, overnight hold
    5. D+1/D+2: Continue trading with profit-taking and re-entry
    """
    
    def __init__(self, 
                 initial_capital: float = 100_000_000,  # 1억원
                 max_positions: int = 3,
                 position_size_pct: float = 0.20,  # 20% per trade
                 stop_loss_pct: float = -0.07,  # -7% stop loss
                 profit_take_1: float = 0.10,  # 10% partial
                 profit_take_2: float = 0.20,  # 20% more
                 overnight_hold: bool = True):
        
        self.initial_capital = initial_capital
        self.cash = initial_capital
        self.max_positions = max_positions
        self.position_size_pct = position_size_pct
        self.stop_loss_pct = stop_loss_pct
        self.profit_take_1 = profit_take_1
        self.profit_take_2 = profit_take_2
        self.overnight_hold = overnight_hold
        
        self.positions = {}  # symbol -> position info
        self.trades = []
        self.daily_stats = []
        
    def detect_dominant_theme(self, 
                             market_data: pd.DataFrame,
                             date: datetime,
                             min_limit_up_stocks: int = 5,
                             sector_col: str = 'sector') -> List[str]:
        """
        Detect dominant themes with multiple limit-up stocks
        
        Args:
            market_data: DataFrame with all stocks for the day
            date: Trading date
            min_limit_up_stocks: Minimum stocks hitting limit up in theme
            
        Returns:
            List of dominant theme sectors
        """
        daily_data = market_data[market_data['date'] == date].copy()
        
        # Find stocks that hit limit up (typically +30% for KOSDAQ, +15% for KOSPI)
        daily_data['hit_limit_up'] = daily_data['change_pct'] >= 29.5  # Approximate
        
        # Group by sector and count
        sector_stats = daily_data.groupby(sector_col).agg({
            'hit_limit_up': 'sum',
            'code': 'count'
        }).rename(columns={'code': 'total_stocks'})
        
        # Filter sectors with multiple limit-ups
        dominant_themes = sector_stats[
            sector_stats['hit_limit_up'] >= min_limit_up_stocks
        ].index.tolist()
        
        return dominant_themes
    
    def select_leader_stock(self,
                           market_data: pd.DataFrame,
                           theme_sectors: List[str],
                           date: datetime,
                           min_volume: float = 1_000_000_000,  # 10억 거래대금
                           min_price: float = 1000) -> Optional[str]:
        """
        Select the strongest leader stock in dominant theme
        
        Criteria:
        - Highest price increase in theme
        - Adequate trading volume (not too small)
        - Strong momentum (끼)
        """
        daily_data = market_data[
            (market_data['date'] == date) & 
            (market_data['sector'].isin(theme_sectors))
        ].copy()
        
        # Filter by minimum volume and price
        candidates = daily_data[
            (daily_data['volume'] * daily_data['close'] >= min_volume) &
            (daily_data['close'] >= min_price)
        ].copy()
        
        if candidates.empty:
            return None
        
        # Score stocks based on multiple factors
        candidates['score'] = (
            candidates['change_pct'] * 0.4 +  # Price change weight
            (candidates['volume'] / candidates['volume'].max()) * 30 +  # Volume
            candidates['high'] / candidates['close'] * 20  # Intraday strength
        )
        
        # Select top scorer
        leader = candidates.loc[candidates['score'].idxmax(), 'code']
        return leader
    
    def check_entry_conditions(self,
                              stock_data: pd.DataFrame,
                              market_data: pd.DataFrame,
                              date: datetime,
                              entry_time: str = "09:30") -> bool:
        """
        Check if entry conditions are met
        
        Entry Rules:
        1. Stock is leader in dominant theme
        2. Around 9:30 AM (after initial volatility settles)
        3. Theme confirmed strong
        4. Market direction not against (optional)
        """
        # Check if already in position
        stock_code = stock_data['code'].iloc[0]
        if stock_code in self.positions:
            return False
        
        # Check position limit
        if len(self.positions) >= self.max_positions:
            return False
        
        # Check if stock has risen significantly (can enter even after big rise)
        daily_change = stock_data[stock_data['date'] == date]['change_pct'].iloc[0]
        
        # Enter if stock has risen >10% and theme is strong
        if daily_change < 10:
            return False
        
        return True
    
    def calculate_position_size(self, stock_price: float) -> int:
        """Calculate number of shares to buy"""
        position_value = self.cash * self.position_size_pct
        shares = int(position_value / stock_price)
        return shares
    
    def enter_position(self,
                      stock_code: str,
                      entry_date: datetime,
                      entry_price: float,
                      is_overnight: bool = False) -> Dict:
        """Enter a new position"""
        
        shares = self.calculate_position_size(entry_price)
        if shares == 0:
            return None
        
        cost = shares * entry_price
        if cost > self.cash:
            return None
        
        self.cash -= cost
        
        position = {
            'code': stock_code,
            'entry_date': entry_date,
            'entry_price': entry_price,
            'shares': shares,
            'cost': cost,
            'partial_sold': 0,
            'profit_taken': 0,
            'is_overnight': is_overnight,
            'day_count': 0  # D+0, D+1, D+2
        }
        
        self.positions[stock_code] = position
        
        self.trades.append({
            'date': entry_date,
            'code': stock_code,
            'action': 'BUY',
            'price': entry_price,
            'shares': shares,
            'value': cost
        })
        
        return position
    
    def manage_position(self,
                       stock_code: str,
                       current_date: datetime,
                       current_price: float,
                       high_price: float,
                       low_price: float) -> str:
        """
        Manage open position
        
        Rules:
        1. Partial profit at +10%
        2. More profit at +20%
        3. Stop loss at -7%
        4. Can hold overnight for D+1/D+2 continuation
        """
        if stock_code not in self.positions:
            return 'NO_POSITION'
        
        pos = self.positions[stock_code]
        entry_price = pos['entry_price']
        current_return = (current_price - entry_price) / entry_price
        
        # Check stop loss
        if current_return <= self.stop_loss_pct:
            self.close_position(stock_code, current_date, current_price, 'STOP_LOSS')
            return 'STOPPED'
        
        # Partial profit taking at +10% (if not already done)
        if current_return >= self.profit_take_1 and pos['partial_sold'] == 0:
            self.take_partial_profit(stock_code, current_date, current_price, 0.5)
            pos['partial_sold'] = 1
            return 'PARTIAL_1'
        
        # More profit taking at +20%
        if current_return >= self.profit_take_2 and pos['partial_sold'] == 1:
            self.take_partial_profit(stock_code, current_date, current_price, 0.5)
            pos['partial_sold'] = 2
            return 'PARTIAL_2'
        
        # If hit limit up (+30%), take more profits
        if current_return >= 0.29 and pos['partial_sold'] < 2:
            self.take_partial_profit(stock_code, current_date, current_price, 0.3)
            pos['partial_sold'] = 2
            return 'LIMIT_UP_PARTIAL'
        
        return 'HOLD'
    
    def take_partial_profit(self,
                           stock_code: str,
                           date: datetime,
                           price: float,
                           portion: float):
        """Take partial profits"""
        pos = self.positions[stock_code]
        shares_to_sell = int(pos['shares'] * portion)
        
        if shares_to_sell == 0:
            return
        
        value = shares_to_sell * price
        self.cash += value
        pos['shares'] -= shares_to_sell
        pos['profit_taken'] += value - (shares_to_sell * pos['entry_price'])
        
        self.trades.append({
            'date': date,
            'code': stock_code,
            'action': 'SELL_PARTIAL',
            'price': price,
            'shares': shares_to_sell,
            'value': value
        })
    
    def close_position(self,
                      stock_code: str,
                      date: datetime,
                      price: float,
                      reason: str):
        """Close entire position"""
        pos = self.positions[stock_code]
        
        if pos['shares'] > 0:
            value = pos['shares'] * price
            self.cash += value
            
            # Calculate profit
            cost_basis = pos['shares'] * pos['entry_price']
            profit = value - cost_basis
            
            self.trades.append({
                'date': date,
                'code': stock_code,
                'action': 'SELL_ALL',
                'price': price,
                'shares': pos['shares'],
                'value': value,
                'profit': profit,
                'reason': reason,
                'total_return': (price - pos['entry_price']) / pos['entry_price']
            })
        
        del self.positions[stock_code]
    
    def check_overnight_hold(self,
                            stock_code: str,
                            current_date: datetime,
                            current_price: float) -> bool:
        """
        Decide whether to hold overnight
        
        Hold overnight if:
        1. Stock is leader in strong theme
        2. Has shown strength throughout day
        3. Market conditions favorable
        """
        pos = self.positions[stock_code]
        
        # If D+0 and strong performance, hold for D+1
        if pos['day_count'] == 0 and pos['partial_sold'] >= 1:
            return True
        
        return False
    
    def run_backtest(self,
                    market_data: pd.DataFrame,
                    start_date: datetime,
                    end_date: datetime) -> pd.DataFrame:
        """
        Run backtest of the strategy
        
        Args:
            market_data: DataFrame with columns:
                - date, code, name, sector, open, high, low, close, volume, change_pct
            start_date: Backtest start date
            end_date: Backtest end date
        """
        dates = pd.date_range(start=start_date, end=end_date, freq='B')  # Business days
        
        for date in dates:
            date_str = date.strftime('%Y-%m-%d')
            
            # Skip if no data for this date
            day_data = market_data[market_data['date'] == date_str]
            if day_data.empty:
                continue
            
            # 1. Detect dominant themes
            dominant_themes = self.detect_dominant_theme(market_data, date_str)
            
            if dominant_themes:
                # 2. Select leader stock
                leader = self.select_leader_stock(market_data, dominant_themes, date_str)
                
                if leader:
                    leader_data = day_data[day_data['code'] == leader]
                    if not leader_data.empty:
                        # 3. Check entry conditions and enter
                        if self.check_entry_conditions(leader_data, market_data, date_str):
                            entry_price = leader_data.iloc[0]['open'] * 1.05  # Enter after some rise
                            self.enter_position(leader, date_str, entry_price)
            
            # 4. Manage existing positions
            for stock_code in list(self.positions.keys()):
                stock_day_data = day_data[day_data['code'] == stock_code]
                if not stock_day_data.empty:
                    self.manage_position(
                        stock_code,
                        date_str,
                        stock_day_data.iloc[0]['close'],
                        stock_day_data.iloc[0]['high'],
                        stock_day_data.iloc[0]['low']
                    )
            
            # 5. Record daily stats
            portfolio_value = self.cash + sum(
                pos['shares'] * day_data[day_data['code'] == code]['close'].iloc[0]
                for code, pos in self.positions.items()
                if not day_data[day_data['code'] == code].empty
            )
            
            self.daily_stats.append({
                'date': date_str,
                'cash': self.cash,
                'positions': len(self.positions),
                'portfolio_value': portfolio_value,
                'return_pct': (portfolio_value - self.initial_capital) / self.initial_capital * 100
            })
        
        return pd.DataFrame(self.daily_stats)
    
    def get_trade_summary(self) -> pd.DataFrame:
        """Get summary of all completed trades"""
        completed_trades = [
            t for t in self.trades 
            if t['action'] == 'SELL_ALL'
        ]
        return pd.DataFrame(completed_trades)
    
    def calculate_performance_metrics(self) -> Dict:
        """Calculate key performance metrics"""
        if not self.daily_stats:
            return {}
        
        df = pd.DataFrame(self.daily_stats)
        trades_df = self.get_trade_summary()
        
        metrics = {
            'total_return_pct': df['return_pct'].iloc[-1] if len(df) > 0 else 0,
            'max_drawdown_pct': (df['portfolio_value'].cummax() - df['portfolio_value']).max() / df['portfolio_value'].cummax().max() * 100,
            'trading_days': len(df),
            'total_trades': len(trades_df),
        }
        
        if not trades_df.empty:
            metrics['win_rate'] = (trades_df['profit'] > 0).mean() * 100
            metrics['avg_profit'] = trades_df[trades_df['profit'] > 0]['profit'].mean()
            metrics['avg_loss'] = trades_df[trades_df['profit'] < 0]['profit'].mean()
            metrics['profit_factor'] = abs(
                trades_df[trades_df['profit'] > 0]['profit'].sum() / 
                trades_df[trades_df['profit'] < 0]['profit'].sum()
            ) if trades_df[trades_df['profit'] < 0]['profit'].sum() != 0 else float('inf')
        
        return metrics


# Example usage and backtest runner
def run_dplus_backtest_example():
    """Example of running the D+ strategy backtest"""
    
    # Initialize strategy
    strategy = DPlusLeadingStockStrategy(
        initial_capital=100_000_000,  # 1억원
        max_positions=3,
        position_size_pct=0.20,  # 20% per position
        stop_loss_pct=-0.07,  # -7% stop
        profit_take_1=0.10,  # 10% partial
        profit_take_2=0.20   # 20% partial
    )
    
    # Note: Actual market data would need to be loaded from database
    # This is just the strategy framework
    
    print("D+ Leading Stock Strategy Initialized")
    print("=" * 50)
    print("Core Rules:")
    print("1. Detect themes with 5+ limit-up stocks")
    print("2. Select strongest leader (high volume, strong momentum)")
    print("3. Enter around 9:30 AM after confirming theme")
    print("4. Partial profit at +10%, +20%, limit up")
    print("5. Hold overnight for D+1/D+2 continuation")
    print("6. Stop loss at -7%")
    print("=" * 50)
    
    return strategy


if __name__ == "__main__":
    strategy = run_dplus_backtest_example()
