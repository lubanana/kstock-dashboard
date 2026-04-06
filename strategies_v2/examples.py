"""
V2 Strategy Usage Examples

Demonstrates how to use the unified strategy framework.
"""

import pandas as pd
from datetime import datetime, timedelta

# Import V2 strategies
from strategies_v2.base import BaseStrategy, Signal
from strategies_v2.momentum import MomentumStrategy, create_livermore_config, create_oneil_config
from strategies_v2.presets import get_preset, list_presets


def example_1_basic_usage():
    """Example 1: Basic momentum scan with default config"""
    print("=" * 70)
    print("Example 1: Basic Momentum Strategy")
    print("=" * 70)
    
    # Create strategy with default configuration
    config = {
        'type': 'momentum',
        'entry': {
            'rsi': {'enabled': True, 'min': 50, 'max': 70},
            'ma_alignment': {'enabled': True, 'fast': 20, 'slow': 60},
            'volume': {'enabled': True, 'min_ratio': 2.0, 'comparison_period': 20},
            'breakout': {'enabled': True, 'lookback_days': 252, 'threshold_pct': 0.99}
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
    
    strategy = MomentumStrategy(config)
    
    # Example: Scan a single stock
    # In practice, you would load real data from your data source
    print(f"\nStrategy Type: {strategy.get_strategy_name()}")
    print(f"RSI Range: {strategy.rsi_min} - {strategy.rsi_max}")
    print(f"Volume Threshold: {strategy.volume_min_ratio}x")
    print(f"Max Positions: {strategy.max_positions}")
    print(f"Max Hold Days: {strategy.max_hold_days}")


def example_2_preset_usage():
    """Example 2: Using legacy scanner presets"""
    print("\n" + "=" * 70)
    print("Example 2: Using Legacy Scanner Presets")
    print("=" * 70)
    
    # List available presets
    presets = list_presets()
    print(f"\nAvailable Presets ({len(presets)} total):")
    for p in presets[:5]:
        print(f"  • {p['name']} ({p['type']})")
    print("  ...")
    
    # Use Livermore preset (52-week high breakout)
    livermore_config = get_preset('livermore')
    strategy = MomentumStrategy(livermore_config)
    
    print(f"\nLoaded: {livermore_config['name']}")
    print(f"Description: {livermore_config['description']}")
    print(f"Breakout Enabled: {strategy.breakout_enabled}")
    print(f"52W Threshold: {strategy.breakout_threshold}")


def example_3_unified_indicators():
    """Example 3: Unified indicator calculations"""
    print("\n" + "=" * 70)
    print("Example 3: Unified Technical Indicators")
    print("=" * 70)
    
    # Create sample data
    import numpy as np
    np.random.seed(42)
    
    dates = pd.date_range(end=datetime.now(), periods=100, freq='D')
    prices = 100 + np.cumsum(np.random.randn(100) * 2)
    
    df = pd.DataFrame({
        'Open': prices * 0.99,
        'High': prices * 1.02,
        'Low': prices * 0.98,
        'Close': prices,
        'Volume': np.random.randint(1000000, 5000000, 100)
    }, index=dates)
    
    # Create strategy (just for indicator access)
    config = {'type': 'momentum'}
    strategy = MomentumStrategy(config)
    
    # Calculate indicators
    rsi = strategy.calculate_rsi(df['Close'])
    atr = strategy.calculate_atr(df)
    upper, middle, lower = strategy.calculate_bollinger_bands(df)
    bb_pos = strategy.calculate_bb_position(df)
    macd, signal, hist = strategy.calculate_macd(df['Close'])
    
    print(f"\nLatest Indicators:")
    print(f"  RSI(14): {rsi.iloc[-1]:.2f}")
    print(f"  ATR(14): {atr.iloc[-1]:.2f}")
    print(f"  BB Position: {bb_pos.iloc[-1]:.2f}")
    print(f"  MACD: {macd.iloc[-1]:.2f}")
    print(f"  MACD Signal: {signal.iloc[-1]:.2f}")


def example_4_risk_management():
    """Example 4: Unified risk management"""
    print("\n" + "=" * 70)
    print("Example 4: Unified Risk Management")
    print("=" * 70)
    
    config = create_livermore_config()
    strategy = MomentumStrategy(config)
    
    # Example trade parameters
    entry_price = 100000
    atr = 2500
    
    stop_loss = strategy.calculate_stop_loss(entry_price, atr)
    take_profit = strategy.calculate_take_profit(entry_price, atr)
    
    risk = entry_price - stop_loss
    reward = take_profit - entry_price
    rr_ratio = reward / risk
    
    print(f"\nEntry Price: ₩{entry_price:,.0f}")
    print(f"ATR: ₩{atr:,.0f}")
    print(f"Stop Loss: ₩{stop_loss:,.0f} ({(stop_loss/entry_price-1)*100:.1f}%)")
    print(f"Take Profit: ₩{take_profit:,.0f} ({(take_profit/entry_price-1)*100:.1f}%)")
    print(f"Risk/Reward Ratio: 1:{rr_ratio:.2f}")
    
    # Position sizing
    available_capital = 100_000_000
    score = 85
    
    shares, position_pct = strategy.calculate_position_size(
        score, available_capital, entry_price
    )
    
    print(f"\nPosition Sizing (Score {score}):")
    print(f"  Position %: {position_pct}%")
    print(f"  Shares: {shares}")
    print(f"  Position Value: ₩{shares * entry_price:,.0f}")


def example_5_migrating_legacy():
    """Example 5: Migrating from legacy scanner"""
    print("\n" + "=" * 70)
    print("Example 5: Migration from Legacy Scanner")
    print("=" * 70)
    
    print("""
# BEFORE (Legacy - livermore_scanner.py):
------------------------------------------
class LivermoreScanner:
    def __init__(self):
        self.watchlist = [...]
        
    def calculate_indicators(self, df):
        # Duplicate RSI implementation
        delta = df['Close'].diff()
        gain = delta.where(delta > 0, 0).rolling(14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
        rs = gain / loss
        df['RSI'] = 100 - (100 / (1 + rs))
        
    def analyze_breakout(self, df, symbol):
        # Specific logic for 52w breakout
        high_52w = df['High'].tail(252).max()
        if price >= high_52w * 0.99:
            # Score calculation
            score = 0
            ...
        return result

scanner = LivermoreScanner()
results = scanner.scan()

# AFTER (V2 Unified):
------------------------------------------
from strategies_v2.momentum import MomentumStrategy
from strategies_v2.presets import get_preset

# Use preset or custom config
config = get_preset('livermore')  # or create custom config
strategy = MomentumStrategy(config)

# Unified scan method (same for all strategies)
signals = []
for symbol in watchlist:
    df = load_data(symbol)
    signal = strategy.scan_stock(symbol, df)
    if signal:
        signals.append(signal)

# Benefits:
# - Single RSI/ATR/MA implementation (no duplication)
# - Unified risk management
# - Consistent interface across all strategies
# - Easy to modify parameters without changing code
""")


def example_6_custom_strategy():
    """Example 6: Creating custom strategy configuration"""
    print("\n" + "=" * 70)
    print("Example 6: Custom Strategy Configuration")
    print("=" * 70)
    
    # Custom momentum strategy with specific parameters
    custom_config = {
        'type': 'momentum',
        'name': 'Custom Aggressive Breakout',
        'entry': {
            'rsi': {'enabled': True, 'min': 55, 'max': 75},  # Higher RSI for momentum
            'ma_alignment': {'enabled': True, 'fast': 10, 'slow': 30},
            'volume': {'enabled': True, 'min_ratio': 2.5, 'comparison_period': 20},
            'breakout': {'enabled': True, 'lookback_days': 60, 'threshold_pct': 0.98},
            'price_gain': {'min_pct': 5}
        },
        'risk': {
            'stop_loss': {'type': 'atr', 'value': 2.0},  # Wider stop for volatility
            'take_profit': {'type': 'percent', 'value': 30},  # Higher target
            'trailing_stop': {'enabled': True, 'activation_pct': 20, 'trail_pct': 8},
            'position_sizing': {
                'type': 'score_tiered',
                'tiers': [
                    {'min_score': 90, 'weight': 25},
                    {'min_score': 80, 'weight': 15},
                    {'min_score': 70, 'weight': 8}
                ]
            },
            'max_hold_days': 45,  # Shorter hold
            'max_positions': 15
        },
        'scoring': {'threshold': 70}
    }
    
    strategy = MomentumStrategy(custom_config)
    
    print("\nCustom Strategy Created:")
    print(f"  Name: {custom_config['name']}")
    print(f"  RSI: {strategy.rsi_min}-{strategy.rsi_max} (tighter range for momentum)")
    print(f"  Volume: {strategy.volume_min_ratio}x (higher conviction)")
    print(f"  SL: {strategy.sl_value} ATR (wider stop)")
    print(f"  Sizing: Tiered based on score")


if __name__ == '__main__':
    example_1_basic_usage()
    example_2_preset_usage()
    example_3_unified_indicators()
    example_4_risk_management()
    example_5_migrating_legacy()
    example_6_custom_strategy()
    
    print("\n" + "=" * 70)
    print("Summary: V2 Strategy Framework Benefits")
    print("=" * 70)
    print("""
1. CODE REDUCTION: ~85% fewer files, ~77% fewer lines
2. MAINTAINABILITY: One implementation per indicator
3. CONSISTENCY: Same risk management across all strategies
4. FLEXIBILITY: YAML configs instead of code changes
5. TESTABILITY: Unified interface makes testing easier
6. EXTENSIBILITY: Easy to add new strategy variants

Migration Path:
- Phase 1: Copy config from legacy scanner to preset
- Phase 2: Use preset with unified strategy class
- Phase 3: Gradually replace legacy scanner calls
- Phase 4: Remove legacy scanners when validated
""")
