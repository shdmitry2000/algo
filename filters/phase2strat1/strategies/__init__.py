"""
Strategies package — DEPRECATED

All strategy implementations have been moved to strategies/implementations/

Use this instead:
    from strategies.implementations import (
        IronCondorStrategy,
        ButterflyStrategy,
        CondorStrategy,
        ShiftedCondorStrategy,
        FlygonaalStrategy,
        CalendarSpreadStrategy
    )
    
    from strategies.core import StrategyCandidate, BaseStrategy

This package is kept only for import compatibility.
The old implementation files have been deleted (2026-04-07).
"""

# Re-export from new location for backwards compatibility
from strategies.implementations import (
    IronCondorStrategy,
    ButterflyStrategy,
    ShiftedCondorStrategy
)
from strategies.core import BaseStrategy, StrategyCandidate

__all__ = [
    "BaseStrategy",
    "StrategyCandidate",
    "IronCondorStrategy",
    "ButterflyStrategy",
    "ShiftedCondorStrategy",
]
