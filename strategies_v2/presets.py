"""
Configuration Presets for V2 Strategies

Each preset maps to a legacy scanner configuration.
"""

# ==================== MOMENTUM STRATEGIES ====================

LIVERMORE_PRESET = {
    "name": "Livermore New High Breakout",
    "description": "52-week high breakout with volume confirmation",
    "type": "momentum",
    "entry": {
        "rsi": {"enabled": True, "min": 50, "max": 70},
        "ma_alignment": {"enabled": True, "fast": 20, "slow": 60},
        "volume": {"enabled": True, "min_ratio": 1.5, "comparison_period": 20},
        "breakout": {"enabled": True, "lookback_days": 252, "threshold_pct": 0.99},
        "price_gain": {"min_pct": 0}
    },
    "risk": {
        "stop_loss": {"type": "atr", "value": 1.5},
        "take_profit": {"type": "percent", "value": 25},
        "trailing_stop": {"enabled": True, "activation_pct": 25, "trail_pct": 10},
        "position_sizing": {"type": "fixed", "base_pct": 10},
        "max_hold_days": 90,
        "max_positions": 10
    },
    "scoring": {"threshold": 60}
}

ONEIL_PRESET = {
    "name": "William O'Neil Volume Spike",
    "description": "CAN SLIM volume spike pattern with breakout",
    "type": "momentum",
    "entry": {
        "rsi": {"enabled": True, "min": 50, "max": 70},
        "ma_alignment": {"enabled": True, "fast": 20, "slow": 50},
        "volume": {"enabled": True, "min_ratio": 2.0, "comparison_period": 50},
        "breakout": {"enabled": True, "lookback_days": 50, "threshold_pct": 0.98},
        "price_gain": {"min_pct": 3}
    },
    "risk": {
        "stop_loss": {"type": "percent", "value": 7},
        "take_profit": {"type": "percent", "value": 25},
        "trailing_stop": {"enabled": True, "activation_pct": 25, "trail_pct": 10},
        "position_sizing": {"type": "fixed", "base_pct": 10},
        "max_hold_days": 60,
        "max_positions": 20
    },
    "scoring": {
        "threshold": 50,
        "weights": {
            "volume": 40,
            "price": 30,
            "breakout": 15,
            "accumulation": 10,
            "rs": 5
        }
    }
}

NB_STRATEGY_PRESET = {
    "name": "N-Strategy + B-Strategy",
    "description": "Buy strength with Fibonacci and ATR targets",
    "type": "momentum",
    "entry": {
        "rsi": {"enabled": True, "min": 40, "max": 70},
        "ma_alignment": {"enabled": True, "fast": 20, "slow": 60},
        "volume": {"enabled": True, "min_ratio": 1.0, "comparison_period": 20},
        "breakout": {"enabled": False},
        "price_gain": {"min_pct": 0},
        "use_fibonacci": True
    },
    "risk": {
        "stop_loss": {"type": "atr", "value": 1.5},
        "take_profit": {"type": "fibonacci"},
        "trailing_stop": {"enabled": False},
        "position_sizing": {"type": "fixed", "base_pct": 10},
        "min_rr_ratio": 1.5,
        "max_hold_days": 90,
        "max_positions": 10
    },
    "scoring": {"threshold": 60}
}

EXPLOSIVE_PRESET = {
    "name": "Explosive Growth Strategy",
    "description": "High momentum with sector rotation and tiered sizing",
    "type": "momentum",
    "entry": {
        "rsi": {"enabled": True, "min": 40, "max": 70},
        "ma_alignment": {"enabled": True, "fast": 5, "slow": 20},
        "adx": {"enabled": True, "min": 20},
        "volume": {"enabled": True, "min_ratio": 2.0, "comparison_period": 20},
        "breakout": {"enabled": False},
        "price_gain": {"min_pct": 0},
        "sector_rotation": {"enabled": True}
    },
    "risk": {
        "stop_loss": {"type": "percent", "value": 7},
        "take_profit": {"type": "percent", "value": 25},
        "trailing_stop": {"enabled": True, "activation_pct": 25, "trail_pct": 10},
        "position_sizing": {
            "type": "score_tiered",
            "tiers": [
                {"min_score": 90, "weight": 20},
                {"min_score": 85, "weight": 8}
            ]
        },
        "max_hold_days": 90,
        "max_positions": 10,
        "max_sector_exposure": 25
    },
    "scoring": {
        "threshold": 85,
        "components": {
            "volume": 35,
            "technical": 20,
            "market_cap": 10,
            "foreign": 5,
            "news": 10,
            "theme": 10
        }
    }
}


# ==================== MEAN REVERSION STRATEGIES ====================

QUALITY_OVERSOLD_PRESET = {
    "name": "Quality Oversold",
    "description": "Strong fundamentals + technical oversold conditions",
    "type": "mean_reversion",
    "entry": {
        "rsi": {"enabled": True, "min": 0, "max": 40},
        "stochastic": {"enabled": True, "max": 30},
        "bollinger": {"enabled": True, "position_max": 0.2},
        "price_decline": {"enabled": True, "min_vs_52w_high": 15},
        "volume": {"enabled": True, "min_ratio": 0.8, "comparison_period": 20}
    },
    "fundamental_filters": {
        "roe_min": 10,
        "debt_ratio_max": 200,
        "operating_margin_min": 5
    },
    "risk": {
        "stop_loss": {"type": "percent", "value": 5},
        "take_profit": {"type": "percent", "value": 15},
        "trailing_stop": {"enabled": False},
        "position_sizing": {"type": "fixed", "base_pct": 10},
        "max_hold_days": 30,
        "max_positions": 10
    },
    "scoring": {
        "threshold": 50,
        "weights": {
            "oversold": 40,
            "price_decline": 30,
            "volume": 20,
            "trend": 10
        }
    }
}

GLOBAL_RSI_BB_PRESET = {
    "name": "RSI + Bollinger Bands",
    "description": "Global oversold scanner for stocks and crypto",
    "type": "mean_reversion",
    "entry": {
        "rsi": {"enabled": True, "min": 20, "max": 40},
        "bollinger": {"enabled": True, "position_max": 0.02},
        "volume": {"enabled": True, "min_ratio": 1.3, "comparison_period": 20},
        "candlestick": {"enabled": True, "require_bullish": True}
    },
    "risk": {
        "stop_loss": {"type": "percent", "value": 5},
        "take_profit": {"type": "percent", "value": 10},
        "trailing_stop": {"enabled": False},
        "position_sizing": {"type": "fixed", "base_pct": 5},
        "max_hold_days": 5,
        "max_positions": 5
    },
    "scoring": {"threshold": 60}
}

SHORT_TERM_MOMENTUM_PRESET = {
    "name": "Short-term Reversal",
    "description": "1-5 day oversold reversal signals",
    "type": "mean_reversion",
    "entry": {
        "rsi": {"enabled": True, "min": 0, "max": 35},
        "bollinger": {"enabled": True, "position_max": 0.1},
        "volume": {"enabled": True, "min_ratio": 1.5, "comparison_period": 20},
        "candlestick": {"enabled": True, "patterns": ["hammer", "engulfing"]},
        "price_position": {"enabled": True, "max": 0.2}
    },
    "risk": {
        "stop_loss": {"type": "percent", "value": 5},
        "take_profit": {"type": "percent", "value": 10},
        "trailing_stop": {"enabled": False},
        "position_sizing": {"type": "fixed", "base_pct": 5},
        "max_hold_days": 5,
        "max_positions": 5
    },
    "scoring": {
        "threshold": 60,
        "weights": {
            "rsi": 20,
            "bb": 15,
            "volume": 20,
            "candlestick": 15,
            "ma": 10,
            "price_position": 10,
            "obv": 10
        }
    }
}


# ==================== BREAKOUT STRATEGIES ====================

MINERVINI_VCP_PRESET = {
    "name": "Mark Minervini VCP",
    "description": "Volatility Contraction Pattern with A-B-C structure",
    "type": "breakout",
    "entry": {
        "vcp": {
            "enabled": True,
            "lookback_periods": 3,
            "period_days": 10,
            "contraction_threshold": 0.8
        },
        "volume_contraction": {"enabled": True, "threshold": 0.8},
        "price_compression": {"enabled": True, "max_range_pct": 15},
        "trend": {"enabled": True, "require_above_ma50": True},
        "breakout_setup": {"enabled": True, "proximity_to_resistance": 0.97}
    },
    "risk": {
        "stop_loss": {"type": "atr", "value": 1.0},
        "take_profit": {"type": "atr", "value": 3.0},
        "trailing_stop": {"enabled": True, "activation_pct": 20, "trail_pct": 10},
        "position_sizing": {"type": "fixed", "base_pct": 10},
        "max_hold_days": 60,
        "max_positions": 10
    },
    "scoring": {
        "threshold": 50,
        "weights": {
            "volatility_contraction": 30,
            "volume_dry_up": 25,
            "price_compression": 20,
            "pullback_shallow": 15,
            "breakout_setup": 10
        }
    }
}

TRIPLE_SIGNAL_PRESET = {
    "name": "Triple Signal Confluence",
    "description": "Livermore + O'Neil + Minervini signals alignment",
    "type": "breakout",
    "entry": {
        "signals": [
            {"type": "52w_high", "enabled": True, "lookback": 252, "threshold": 0.99},
            {"type": "volume_spike", "enabled": True, "ratio": 2.0, "price_gain": 3},
            {"type": "vcp", "enabled": True, "atr_contraction": True}
        ],
        "confluence": {"required_count": 3, "time_window_days": 5}
    },
    "risk": {
        "stop_loss": {"type": "atr", "value": 1.5},
        "take_profit": {"type": "percent", "value": 25},
        "trailing_stop": {"enabled": True, "activation_pct": 25, "trail_pct": 10},
        "position_sizing": {"type": "fixed", "base_pct": 10},
        "max_hold_days": 90,
        "max_positions": 10
    },
    "scoring": {"threshold": 70}
}

DOUBLE_SIGNAL_PRESET = {
    "name": "Double Signal Confluence",
    "description": "Any 2 of 3 signals (Livermore, O'Neil, Minervini)",
    "type": "breakout",
    "entry": {
        "signals": [
            {"type": "52w_high", "enabled": True, "lookback": 252, "threshold": 0.99},
            {"type": "volume_spike", "enabled": True, "ratio": 2.0, "price_gain": 3},
            {"type": "vcp", "enabled": True, "atr_contraction": True}
        ],
        "confluence": {"required_count": 2, "time_window_days": 60}
    },
    "risk": {
        "stop_loss": {"type": "atr", "value": 1.5},
        "take_profit": {"type": "percent", "value": 20},
        "trailing_stop": {"enabled": False},
        "position_sizing": {"type": "fixed", "base_pct": 10},
        "max_hold_days": 60,
        "max_positions": 20
    },
    "scoring": {"threshold": 50}
}


# ==================== MULTI-FACTOR STRATEGIES ====================

V_SERIES_PRESET = {
    "name": "V-Series (Value + Fibonacci + ATR)",
    "description": "Value score with Fibonacci entries and ATR risk management",
    "type": "multi_factor",
    "entry": {
        "value_score": {
            "enabled": True,
            "threshold": 65,
            "components": {
                "per": {"weight": 50, "thresholds": [5, 8, 10, 15, 20, 30]},
                "pbr": {"weight": 30, "thresholds": [0.5, 0.8, 1.0, 1.5, 2.0]},
                "roe": {"weight": 20, "thresholds": [5, 8, 12, 15, 20]}
            }
        },
        "fibonacci": {
            "enabled": True,
            "levels": [0.382, 0.5, 0.618],
            "tolerance": 0.05
        }
    },
    "risk": {
        "stop_loss": {"type": "atr", "value": 1.5},
        "take_profit": {"type": "fibonacci", "level": 1.618},
        "trailing_stop": {"enabled": False},
        "position_sizing": {"type": "fixed", "base_pct": 10},
        "min_rr_ratio": 1.5,
        "max_hold_days": 90,
        "max_positions": 10
    },
    "scoring": {
        "threshold": 65,
        "weights": {
            "value": 40,
            "technical": 30,
            "risk": 30
        }
    }
}

VALUE_STOCK_PRESET = {
    "name": "Value Stock Scanner",
    "description": "1000-point system: Value + Financial Health + Momentum + Risk",
    "type": "multi_factor",
    "entry": {
        "value_score": {
            "enabled": True,
            "threshold": 550,
            "max_results": 30,
            "components": {
                "per": {"weight": 150, "optimal": 8},
                "pbr": {"weight": 100, "optimal": 0.8},
                "roe": {"weight": 100, "optimal": 15},
                "position_52w": {"weight": 50}
            }
        },
        "financial_health": {
            "enabled": True,
            "components": {
                "debt_ratio": {"weight": 100},
                "market_cap": {"weight": 100},
                "stability": {"weight": 100}
            }
        },
        "momentum": {
            "enabled": True,
            "components": {
                "trend": {"weight": 80},
                "rsi": {"weight": 60},
                "return_20d": {"weight": 60}
            }
        }
    },
    "risk": {
        "stop_loss": {"type": "atr", "value": 1.5},
        "take_profit": {"type": "atr", "value": 3.0},
        "trailing_stop": {"enabled": False},
        "position_sizing": {"type": "fixed", "base_pct": 10},
        "max_hold_days": 60,
        "max_positions": 30
    },
    "scoring": {
        "threshold": 550,
        "risk_min": 40
    }
}


# ==================== HYBRID STRATEGIES ====================

DART_INTEGRATED_PRESET = {
    "name": "DART Integrated",
    "description": "DART fundamentals + ICT technical + multi-factor scoring",
    "type": "hybrid",
    "data_sources": {
        "dart": {"enabled": True},
        "technical": {"enabled": True}
    },
    "entry": {
        "fundamental_filters": {
            "roe_min": 5,
            "debt_ratio_max": 300,
            "per_max": 30
        },
        "technical_signals": {
            "ict": {"enabled": True, "fvg": True, "ob": True},
            "vp": {"enabled": True},
            "fibonacci": {"enabled": True}
        },
        "scoring": {
            "enabled": True,
            "threshold": 70
        }
    },
    "risk": {
        "stop_loss": {"type": "atr", "value": 1.5},
        "take_profit": {"type": "fibonacci", "level": 1.618},
        "trailing_stop": {"enabled": False},
        "position_sizing": {"type": "fixed", "base_pct": 10},
        "max_hold_days": 90,
        "max_positions": 10
    }
}

B01_BUFFETT_PRESET = {
    "name": "B01 Buffett Style",
    "description": "Buffett value criteria + technical timing",
    "type": "hybrid",
    "entry": {
        "fundamental_filters": {
            "roe_min": 15,
            "debt_ratio_max": 100,
            "per_max": 15,
            "pbr_max": 1.5,
            "operating_margin_min": 10
        },
        "technical_timing": {
            "enabled": True,
            "rsi_max": 50,
            "bb_position_max": 0.3
        }
    },
    "risk": {
        "stop_loss": {"type": "percent", "value": 10},
        "take_profit": {"type": "percent", "value": 50},
        "trailing_stop": {"enabled": True, "activation_pct": 30, "trail_pct": 15},
        "position_sizing": {"type": "fixed", "base_pct": 15},
        "max_hold_days": 365,
        "max_positions": 10
    },
    "scoring": {
        "threshold": 70,
        "quality_score_min": 70
    }
}


# ==================== PRESET REGISTRY ====================

PRESETS = {
    # Momentum
    'livermore': LIVERMORE_PRESET,
    'oneil': ONEIL_PRESET,
    'nb_strategy': NB_STRATEGY_PRESET,
    'explosive': EXPLOSIVE_PRESET,
    
    # Mean Reversion
    'quality_oversold': QUALITY_OVERSOLD_PRESET,
    'global_rsi_bb': GLOBAL_RSI_BB_PRESET,
    'short_term_momentum': SHORT_TERM_MOMENTUM_PRESET,
    
    # Breakout
    'minervini_vcp': MINERVINI_VCP_PRESET,
    'triple_signal': TRIPLE_SIGNAL_PRESET,
    'double_signal': DOUBLE_SIGNAL_PRESET,
    
    # Multi-Factor
    'v_series': V_SERIES_PRESET,
    'value_stock': VALUE_STOCK_PRESET,
    
    # Hybrid
    'dart_integrated': DART_INTEGRATED_PRESET,
    'b01_buffett': B01_BUFFETT_PRESET,
}


def get_preset(name: str) -> dict:
    """Get a preset configuration by name"""
    if name not in PRESETS:
        raise ValueError(f"Unknown preset: {name}. Available: {list(PRESETS.keys())}")
    return PRESETS[name].copy()


def list_presets() -> list:
    """List all available presets"""
    return [
        {
            'name': name,
            'description': preset['description'],
            'type': preset['type']
        }
        for name, preset in PRESETS.items()
    ]
