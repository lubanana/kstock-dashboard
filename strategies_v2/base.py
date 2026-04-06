"""
Unified Strategy Framework - Base Strategy Class
V2 Architecture for Consolidated Scanner System
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple, Any
from datetime import datetime
import pandas as pd
import numpy as np
from enum import Enum


class StrategyType(Enum):
    MOMENTUM = "momentum"
    MEAN_REVERSION = "mean_reversion"
    BREAKOUT = "breakout"
    MULTI_FACTOR = "multi_factor"
    HYBRID = "hybrid"


@dataclass
class Trade:
    """Trade record data class"""
    symbol: str
    name: str
    entry_date: str
    entry_price: float
    shares: int
    position_pct: float
    score_at_entry: float = 0.0
    sector: str = ""
    
    exit_date: Optional[str] = None
    exit_price: Optional[float] = None
    return_pct: float = 0.0
    exit_reason: str = ""
    max_profit_pct: float = 0.0
    max_loss_pct: float = 0.0
    hold_days: int = 0
    
    # Trailing stop tracking
    highest_price: float = 0.0
    trailing_activated: bool = False
    
    def calculate_return(self) -> float:
        if self.exit_price and self.entry_price:
            self.return_pct = ((self.exit_price - self.entry_price) / self.entry_price) * 100
        return self.return_pct


@dataclass
class Signal:
    """Trading signal data class"""
    symbol: str
    name: str
    score: float
    current_price: float
    entry_price: float
    target_price: float
    stop_loss: float
    rr_ratio: float
    signals: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)


class BaseStrategy(ABC):
    """
    Abstract base class for all V2 strategies.
    
    All legacy scanners consolidate into 5 strategy types:
    - MomentumStrategy (trend following, breakouts)
    - MeanReversionStrategy (oversold, RSI-BB)
    - BreakoutStrategy (VCP, volatility expansion)
    - MultiFactorStrategy (scoring-based)
    - HybridStrategy (fundamental + technical)
    """
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.strategy_type = StrategyType(config.get('type', 'momentum'))
        
        # Initialize risk parameters
        self._init_risk_params()
        
        # State
        self.positions: Dict[str, Trade] = {}
        self.signals: List[Signal] = []
        self.price_cache: Dict[str, pd.DataFrame] = {}
    
    def _init_risk_params(self):
        """Initialize risk management parameters from config"""
        risk_config = self.config.get('risk', {})
        
        # Stop loss
        sl_config = risk_config.get('stop_loss', {})
        self.sl_type = sl_config.get('type', 'atr')
        self.sl_value = sl_config.get('value', 1.5)
        
        # Take profit
        tp_config = risk_config.get('take_profit', {})
        self.tp_type = tp_config.get('type', 'atr')
        self.tp_value = tp_config.get('value', 3.0)
        
        # Trailing stop
        ts_config = risk_config.get('trailing_stop', {})
        self.trailing_enabled = ts_config.get('enabled', True)
        self.trailing_activation = ts_config.get('activation_pct', 25)
        self.trailing_pct = ts_config.get('trail_pct', 10)
        
        # Position sizing
        ps_config = risk_config.get('position_sizing', {})
        self.ps_type = ps_config.get('type', 'fixed')
        self.ps_base_pct = ps_config.get('base_pct', 10)
        self.ps_tiers = ps_config.get('tiers', [
            {'min_score': 90, 'weight': 20},
            {'min_score': 85, 'weight': 8}
        ])
        
        # Limits
        self.max_hold_days = risk_config.get('max_hold_days', 90)
        self.max_positions = risk_config.get('max_positions', 10)
    
    # ==================== Technical Indicators (Unified) ====================
    
    def calculate_rsi(self, prices: pd.Series, period: int = 14) -> pd.Series:
        """Calculate RSI - Single implementation for all strategies"""
        delta = prices.diff()
        gain = delta.where(delta > 0, 0).rolling(window=period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
        rs = gain / loss
        return 100 - (100 / (1 + rs))
    
    def calculate_atr(self, df: pd.DataFrame, period: int = 14) -> pd.Series:
        """Calculate ATR - Single implementation for all strategies"""
        high_low = df['High'] - df['Low']
        high_close = np.abs(df['High'] - df['Close'].shift(1))
        low_close = np.abs(df['Low'] - df['Close'].shift(1))
        ranges = pd.concat([high_low, high_close, low_close], axis=1)
        true_range = ranges.max(axis=1)
        return true_range.rolling(window=period).mean()
    
    def calculate_bollinger_bands(self, df: pd.DataFrame, period: int = 20, 
                                   std_dev: float = 2) -> Tuple[pd.Series, pd.Series, pd.Series]:
        """Calculate Bollinger Bands"""
        middle = df['Close'].rolling(window=period).mean()
        std = df['Close'].rolling(window=period).std()
        upper = middle + (std * std_dev)
        lower = middle - (std * std_dev)
        return upper, middle, lower
    
    def calculate_bb_position(self, df: pd.DataFrame) -> pd.Series:
        """Calculate price position within Bollinger Bands (0-1)"""
        upper, middle, lower = self.calculate_bollinger_bands(df)
        return (df['Close'] - lower) / (upper - lower)
    
    def calculate_ma(self, prices: pd.Series, period: int) -> pd.Series:
        """Calculate simple moving average"""
        return prices.rolling(window=period).mean()
    
    def calculate_ema(self, prices: pd.Series, period: int) -> pd.Series:
        """Calculate exponential moving average"""
        return prices.ewm(span=period, adjust=False).mean()
    
    def calculate_macd(self, prices: pd.Series, fast: int = 12, 
                       slow: int = 26, signal: int = 9) -> Tuple[pd.Series, pd.Series, pd.Series]:
        """Calculate MACD, Signal line, and Histogram"""
        exp1 = prices.ewm(span=fast, adjust=False).mean()
        exp2 = prices.ewm(span=slow, adjust=False).mean()
        macd = exp1 - exp2
        signal_line = macd.ewm(span=signal, adjust=False).mean()
        histogram = macd - signal_line
        return macd, signal_line, histogram
    
    def calculate_volume_ratio(self, df: pd.DataFrame, period: int = 20) -> pd.Series:
        """Calculate volume ratio vs moving average"""
        vol_ma = df['Volume'].rolling(window=period).mean()
        return df['Volume'] / vol_ma
    
    def calculate_stochastic(self, df: pd.DataFrame, k_period: int = 14, 
                             d_period: int = 3) -> Tuple[pd.Series, pd.Series]:
        """Calculate Stochastic Oscillator"""
        lowest_low = df['Low'].rolling(window=k_period).min()
        highest_high = df['High'].rolling(window=k_period).max()
        k = 100 * (df['Close'] - lowest_low) / (highest_high - lowest_low)
        d = k.rolling(window=d_period).mean()
        return k, d
    
    def calculate_fibonacci_levels(self, df: pd.DataFrame, lookback: int = 20) -> Dict[str, float]:
        """Calculate Fibonacci retracement and extension levels"""
        recent_high = df['High'].rolling(window=lookback).max().iloc[-1]
        recent_low = df['Low'].rolling(window=lookback).min().iloc[-1]
        price_range = recent_high - recent_low
        current = df['Close'].iloc[-1]
        
        return {
            'high': recent_high,
            'low': recent_low,
            'range': price_range,
            'fib_0': recent_high,
            'fib_236': recent_high - price_range * 0.236,
            'fib_382': recent_high - price_range * 0.382,
            'fib_50': recent_high - price_range * 0.5,
            'fib_618': recent_high - price_range * 0.618,
            'fib_786': recent_high - price_range * 0.786,
            'fib_100': recent_low,
            'fib_1382': recent_high + price_range * 0.382,
            'fib_1618': recent_high + price_range * 0.618,
            'current': current
        }
    
    # ==================== Abstract Methods ====================
    
    @abstractmethod
    def scan_stock(self, symbol: str, df: pd.DataFrame) -> Optional[Signal]:
        """
        Scan a single stock and return Signal if criteria met.
        Must be implemented by each strategy.
        """
        pass
    
    @abstractmethod
    def calculate_score(self, df: pd.DataFrame) -> Tuple[float, List[str]]:
        """
        Calculate strategy-specific score and signals.
        Must be implemented by each strategy.
        """
        pass
    
    # ==================== Risk Management (Unified) ====================
    
    def calculate_stop_loss(self, entry_price: float, atr: float = 0) -> float:
        """Calculate stop loss based on configuration"""
        if self.sl_type == 'atr' and atr > 0:
            return entry_price - (atr * self.sl_value)
        elif self.sl_type == 'percent':
            return entry_price * (1 - self.sl_value / 100)
        else:
            return entry_price * 0.93  # Default 7%
    
    def calculate_take_profit(self, entry_price: float, atr: float = 0,
                              fib_levels: Optional[Dict] = None) -> float:
        """Calculate take profit based on configuration"""
        if self.tp_type == 'atr' and atr > 0:
            return entry_price + (atr * self.tp_value)
        elif self.tp_type == 'percent':
            return entry_price * (1 + self.tp_value / 100)
        elif self.tp_type == 'fibonacci' and fib_levels:
            return fib_levels.get('fib_1618', entry_price * 1.25)
        else:
            return entry_price * 1.25  # Default 25%
    
    def calculate_position_size(self, score: float, available_capital: float,
                                 current_price: float) -> Tuple[int, float]:
        """Calculate position size based on configuration"""
        if self.ps_type == 'fixed':
            position_pct = self.ps_base_pct
        elif self.ps_type == 'score_tiered':
            position_pct = 0
            for tier in sorted(self.ps_tiers, key=lambda x: x['min_score'], reverse=True):
                if score >= tier['min_score']:
                    position_pct = tier['weight']
                    break
            if position_pct == 0:
                position_pct = self.ps_base_pct
        else:
            position_pct = self.ps_base_pct
        
        position_value = available_capital * (position_pct / 100)
        shares = int(position_value / current_price)
        
        return shares, position_pct
    
    def check_exit_conditions(self, trade: Trade, current_price: float,
                               current_date: str) -> Optional[str]:
        """Check if position should be closed - unified for all strategies"""
        current_return = ((current_price - trade.entry_price) / trade.entry_price) * 100
        trade.max_profit_pct = max(trade.max_profit_pct, current_return)
        trade.max_loss_pct = min(trade.max_loss_pct, current_return)
        
        # Update highest price for trailing stop
        if trade.highest_price == 0:
            trade.highest_price = max(trade.entry_price, current_price)
        else:
            trade.highest_price = max(trade.highest_price, current_price)
        
        # Trailing stop check
        if self.trailing_enabled and current_return >= self.trailing_activation:
            trade.trailing_activated = True
            trailing_stop_price = trade.highest_price * (1 - self.trailing_pct / 100)
            if current_price <= trailing_stop_price:
                return 'trailing_stop'
        
        # Stop loss
        stop_price = self.calculate_stop_loss(trade.entry_price)
        if current_price <= stop_price:
            return 'stop_loss'
        
        # Take profit (if trailing not enabled or not yet activated)
        take_profit_price = self.calculate_take_profit(trade.entry_price)
        if not self.trailing_enabled and current_price >= take_profit_price:
            return 'take_profit'
        
        # Max hold days
        if trade.hold_days >= self.max_hold_days:
            return 'max_hold'
        
        return None
    
    # ==================== Utility Methods ====================
    
    def get_price_data(self, symbol: str, start_date: str, end_date: str,
                       data_source: Any) -> pd.DataFrame:
        """Fetch and cache price data"""
        cache_key = f"{symbol}_{start_date}_{end_date}"
        if cache_key in self.price_cache:
            return self.price_cache[cache_key]
        
        # Implementation depends on data source (yfinance, fdr, db, etc.)
        df = self._fetch_from_source(symbol, start_date, end_date, data_source)
        
        if df is not None and not df.empty:
            self.price_cache[cache_key] = df
        
        return df
    
    def _fetch_from_source(self, symbol: str, start_date: str, end_date: str,
                           data_source: Any) -> pd.DataFrame:
        """Override this to implement specific data fetching"""
        # Placeholder - implement based on your data source
        return pd.DataFrame()
    
    def normalize_columns(self, df: pd.DataFrame) -> pd.DataFrame:
        """Normalize column names to standard format"""
        column_map = {}
        for col in df.columns:
            col_cap = col.capitalize()
            if col_cap in ['Open', 'High', 'Low', 'Close', 'Volume']:
                column_map[col] = col_cap
        return df.rename(columns=column_map)
