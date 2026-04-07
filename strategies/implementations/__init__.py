"""
Implementations package - All strategy implementations.

This package contains all concrete strategy implementations that inherit from BaseStrategy.

Strategy Definitions:
- Iron Condor (IC): Same strikes for call+put spreads, 4 legs
- Butterfly (BF): 3 strikes with 2x quantity at middle, 4 legs  
- Condor: 4 distinct strikes with 1x quantity each, 4 legs
- Shifted IC: Different strikes for call+put spreads, 4 legs
- Flygonaal: Custom 3:2:2:3 ratio strategy, 4 legs
- Calendar: Multi-expiration time spreads, 2 legs
"""

from .iron_condor import IronCondorStrategy
from .butterfly import ButterflyStrategy
from .condor import CondorStrategy
from .shifted_condor import ShiftedCondorStrategy
from .flygonaal import FlygonaalStrategy
from .calendar import CalendarSpreadStrategy

__all__ = [
    "IronCondorStrategy",
    "ButterflyStrategy",
    "CondorStrategy",
    "ShiftedCondorStrategy",
    "FlygonaalStrategy",
    "CalendarSpreadStrategy",
]
