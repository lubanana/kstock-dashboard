"""
V2 Unified Strategy Framework

Consolidates 39 legacy scanners into 5 core strategy types
with configurable parameters.

Usage:
    from strategies_v2 import MomentumStrategy, get_preset
    
    config = get_preset('livermore')
    strategy = MomentumStrategy(config)
    
    for symbol in watchlist:
        df = load_data(symbol)
        signal = strategy.scan_stock(symbol, df)
        if signal:
            print(f"Signal: {signal.symbol}, Score: {signal.score}")
"""

from .base import BaseStrategy, StrategyType, Signal, Trade
from .momentum import MomentumStrategy, create_livermore_config, create_oneil_config
from .presets import get_preset, list_presets, PRESETS

__all__ = [
    # Base classes
    'BaseStrategy',
    'StrategyType',
    'Signal',
    'Trade',
    
    # Strategy implementations
    'MomentumStrategy',
    
    # Configuration helpers
    'get_preset',
    'list_presets',
    'PRESETS',
    'create_livermore_config',
    'create_oneil_config',
]

__version__ = '2.0.0'
