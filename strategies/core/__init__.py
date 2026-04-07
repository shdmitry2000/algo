"""
Unified Strategy Core Library

This module provides the foundation for all option trading strategies in the system.
Used by:
- Filter pipeline (Phase 2)
- Arbitrage system (Phase 3 / open_trade)
- Option_X optimizer (future)

Key components:
- BaseStrategy: Abstract base class for all strategies
- StrategyCandidate: Universal strategy representation
- ChainData: Unified option chain data model
- Registry: Strategy type registration
- Utils: Common calculations (BED, spread cap, annual return, etc.)
"""

from .base import BaseStrategy
from .models import (
    StrategyCandidate,
    Leg,
    ChainData,
)
from .registry import STRATEGY_TYPES, register_strategy, get_strategy_class
from .utils import (
    compute_bed,
    compute_annual_return,
    apply_spread_cap,
    check_liquidity_basic,
    generate_imbalanced_quantities,
)

__all__ = [
    # Base classes
    "BaseStrategy",
    
    # Data models
    "StrategyCandidate",
    "Leg",
    "ChainData",
    
    # Registry
    "STRATEGY_TYPES",
    "register_strategy",
    "get_strategy_class",
    
    # Utilities
    "compute_bed",
    "compute_annual_return",
    "apply_spread_cap",
    "check_liquidity_basic",
    "generate_imbalanced_quantities",
]
