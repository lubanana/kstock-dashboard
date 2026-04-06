"""
Momentum Strategy - V2 Implementation
Consolidates: livermore_scanner, oneil_scanner, nb_strategy_scanner, explosive_strategy
"""

from typing import Dict, List, Optional, Tuple
import pandas as pd
import numpy as np
from datetime import datetime

from .base import BaseStrategy, Signal


class MomentumStrategy(BaseStrategy):
    """
    Momentum/Trend Following Strategy
    
    Entry Conditions (Configurable):
    - Price above key MAs (20/50/60)
    - Volume spike (configurable threshold)
    - Breakout patterns (52-week high, resistance)
    - RSI in optimal range (not overbought)
    
    Legacy Consolidation:
    - livermore_scanner: 52w high breakout, volume confirmation
    - oneil_scanner: volume spike + price gain + breakout
    - nb_strategy_scanner: buy strength + fibonacci + ATR targets
    - explosive_strategy: momentum + sector rotation
    """
    
    def __init__(self, config: Dict):
        super().__init__(config)
        
        # Entry configuration
        entry_config = config.get('entry', {})
        
        # RSI settings
        self.rsi_enabled = entry_config.get('rsi', {}).get('enabled', True)
        self.rsi_min = entry_config.get('rsi', {}).get('min', 50)
        self.rsi_max = entry_config.get('rsi', {}).get('max', 70)
        
        # MA settings
        self.ma_enabled = entry_config.get('ma_alignment', {}).get('enabled', True)
        self.ma_fast = entry_config.get('ma_alignment', {}).get('fast', 20)
        self.ma_slow = entry_config.get('ma_alignment', {}).get('slow', 60)
        
        # Volume settings
        self.volume_enabled = entry_config.get('volume', {}).get('enabled', True)
        self.volume_min_ratio = entry_config.get('volume', {}).get('min_ratio', 2.0)
        self.volume_period = entry_config.get('volume', {}).get('comparison_period', 50)
        
        # Breakout settings
        breakout_config = entry_config.get('breakout', {})
        self.breakout_enabled = breakout_config.get('enabled', False)
        self.breakout_lookback = breakout_config.get('lookback_days', 252)
        self.breakout_threshold = breakout_config.get('threshold_pct', 0.99)
        
        # Additional settings
        self.price_gain_min = entry_config.get('price_gain', {}).get('min_pct', 3.0)
        self.use_fibonacci = entry_config.get('use_fibonacci', False)
    
    def calculate_score(self, df: pd.DataFrame) -> Tuple[float, List[str]]:
        """
        Calculate momentum score (0-100)
        Returns score and list of signals
        """
        score = 0
        signals = []
        
        if len(df) < self.ma_slow + 10:
            return 0, []
        
        latest = df.iloc[-1]
        
        # 1. RSI Score (0-20)
        if self.rsi_enabled:
            rsi = self.calculate_rsi(df['Close']).iloc[-1]
            if pd.isna(rsi):
                return 0, []
            
            if self.rsi_min <= rsi <= self.rsi_max:
                score += 20
                signals.append(f'RSI_OPTIMAL_{rsi:.1f}')
            elif 40 <= rsi < self.rsi_min:
                score += 10
                signals.append(f'RSI_BUILDING_{rsi:.1f}')
            elif self.rsi_max < rsi <= 75:
                score += 5
                signals.append(f'RSI_STRONG_{rsi:.1f}')
        
        # 2. MA Alignment Score (0-30)
        if self.ma_enabled:
            ma_fast = self.calculate_ma(df['Close'], self.ma_fast).iloc[-1]
            ma_slow = self.calculate_ma(df['Close'], self.ma_slow).iloc[-1]
            
            if latest['Close'] > ma_fast:
                score += 10
                signals.append(f'ABOVE_MA{self.ma_fast}')
                
                if ma_fast > ma_slow:
                    score += 20
                    signals.append('GOLDEN_CROSS_ALIGNED')
                elif latest['Close'] > ma_slow:
                    score += 10
                    signals.append(f'ABOVE_MA{self.ma_slow}')
        
        # 3. Volume Score (0-30)
        if self.volume_enabled:
            vol_ratio = self.calculate_volume_ratio(df, self.volume_period).iloc[-1]
            
            if vol_ratio >= 3.0:
                score += 30
                signals.append('VOLUME_SPIKE_3X')
            elif vol_ratio >= 2.0:
                score += 25
                signals.append('VOLUME_SPIKE_2X')
            elif vol_ratio >= 1.5:
                score += 15
                signals.append('VOLUME_INCREASE_1.5X')
            elif vol_ratio >= 1.0:
                score += 5
                signals.append('VOLUME_NORMAL')
        
        # 4. Breakout Score (0-20)
        if self.breakout_enabled:
            high_period = df['High'].tail(self.breakout_lookback).max()
            breakout_pct = (latest['Close'] / high_period) * 100
            
            if breakout_pct >= 100:
                score += 20
                signals.append('BREAKOUT_NEW_HIGH')
            elif breakout_pct >= self.breakout_threshold * 100:
                score += 15
                signals.append('NEAR_52W_HIGH')
            elif breakout_pct >= 95:
                score += 10
                signals.append('APPROACHING_HIGH')
        
        # 5. Price Gain (bonus, 0-10)
        if len(df) > 1:
            price_change = (latest['Close'] - df['Close'].iloc[-2]) / df['Close'].iloc[-2] * 100
            if price_change >= 10:
                score += 10
                signals.append('PRICE_SURGE_10PCT')
            elif price_change >= 5:
                score += 8
                signals.append('PRICE_SURGE_5PCT')
            elif price_change >= self.price_gain_min:
                score += 5
                signals.append(f'PRICE_GAIN_{self.price_gain_min}PCT')
        
        return score, signals
    
    def scan_stock(self, symbol: str, df: pd.DataFrame, name: str = "") -> Optional[Signal]:
        """Scan a single stock for momentum signals"""
        
        df = self.normalize_columns(df)
        if len(df) < self.ma_slow + 10:
            return None
        
        score, signals = self.calculate_score(df)
        
        # Minimum score threshold
        min_score = self.config.get('scoring', {}).get('threshold', 60)
        if score < min_score:
            return None
        
        latest = df.iloc[-1]
        current_price = latest['Close']
        
        # Calculate ATR for risk management
        atr = self.calculate_atr(df).iloc[-1]
        
        # Calculate targets
        if self.use_fibonacci:
            fib_levels = self.calculate_fibonacci_levels(df)
            target_price = fib_levels['fib_1618']
        else:
            target_price = self.calculate_take_profit(current_price, atr)
        
        stop_loss = self.calculate_stop_loss(current_price, atr)
        
        # Calculate risk/reward
        risk = current_price - stop_loss
        reward = target_price - current_price
        rr_ratio = reward / risk if risk > 0 else 0
        
        # Minimum RR ratio check
        min_rr = self.config.get('risk', {}).get('min_rr_ratio', 1.5)
        if rr_ratio < min_rr:
            return None
        
        return Signal(
            symbol=symbol,
            name=name or symbol,
            score=score,
            current_price=round(current_price, 0),
            entry_price=round(current_price, 0),
            target_price=round(target_price, 0),
            stop_loss=round(stop_loss, 0),
            rr_ratio=round(rr_ratio, 2),
            signals=signals,
            metadata={
                'atr': round(atr, 2),
                'strategy_type': 'momentum',
                'signals': signals
            }
        )
    
    def get_strategy_name(self) -> str:
        """Return strategy name based on configuration"""
        if self.breakout_enabled:
            return "Momentum-Breakout"
        elif self.use_fibonacci:
            return "Momentum-Fibonacci"
        else:
            return "Momentum-Trend"


# ==================== Pre-configured Variants ====================

def create_livermore_config() -> Dict:
    """Configuration matching livermore_scanner.py"""
    return {
        'type': 'momentum',
        'entry': {
            'rsi': {'enabled': True, 'min': 50, 'max': 70},
            'ma_alignment': {'enabled': True, 'fast': 20, 'slow': 60},
            'volume': {'enabled': True, 'min_ratio': 1.5, 'comparison_period': 20},
            'breakout': {'enabled': True, 'lookback_days': 252, 'threshold_pct': 0.99},
            'price_gain': {'min_pct': 0}
        },
        'risk': {
            'stop_loss': {'type': 'atr', 'value': 1.5},
            'take_profit': {'type': 'percent', 'value': 25},
            'trailing_stop': {'enabled': True, 'activation_pct': 25, 'trail_pct': 10},
            'position_sizing': {'type': 'fixed', 'base_pct': 10},
            'max_hold_days': 90,
            'max_positions': 10
        },
        'scoring': {'threshold': 60}
    }


def create_oneil_config() -> Dict:
    """Configuration matching oneil_scanner.py"""
    return {
        'type': 'momentum',
        'entry': {
            'rsi': {'enabled': True, 'min': 50, 'max': 70},
            'ma_alignment': {'enabled': True, 'fast': 20, 'slow': 50},
            'volume': {'enabled': True, 'min_ratio': 2.0, 'comparison_period': 50},
            'breakout': {'enabled': True, 'lookback_days': 50, 'threshold_pct': 0.98},
            'price_gain': {'min_pct': 3}
        },
        'risk': {
            'stop_loss': {'type': 'percent', 'value': 7},
            'take_profit': {'type': 'percent', 'value': 25},
            'trailing_stop': {'enabled': True, 'activation_pct': 25, 'trail_pct': 10},
            'position_sizing': {'type': 'fixed', 'base_pct': 10},
            'max_hold_days': 60,
            'max_positions': 20
        },
        'scoring': {
            'threshold': 50,
            'weights': {
                'volume': 40,
                'price': 30,
                'breakout': 15,
                'accumulation': 10,
                'rs': 5
            }
        }
    }


def create_nb_strategy_config() -> Dict:
    """Configuration matching nb_strategy_scanner.py"""
    return {
        'type': 'momentum',
        'entry': {
            'rsi': {'enabled': True, 'min': 40, 'max': 70},
            'ma_alignment': {'enabled': True, 'fast': 20, 'slow': 60},
            'volume': {'enabled': True, 'min_ratio': 1.0, 'comparison_period': 20},
            'breakout': {'enabled': False},
            'price_gain': {'min_pct': 0},
            'use_fibonacci': True
        },
        'risk': {
            'stop_loss': {'type': 'atr', 'value': 1.5},
            'take_profit': {'type': 'atr', 'value': 3.0},
            'trailing_stop': {'enabled': False},
            'position_sizing': {'type': 'fixed', 'base_pct': 10},
            'min_rr_ratio': 1.5,
            'max_hold_days': 90,
            'max_positions': 10
        },
        'scoring': {'threshold': 60}
    }
