"""
Chain indexing and DTE calculation.
"""
import logging
from typing import List, Dict, Optional
from datetime import date, datetime
from collections import defaultdict

from datagathering.models import StandardOptionTick

logger = logging.getLogger(__name__)


class ChainIndex:
    """Index for (symbol, expiration) — maps strike -> tick for C and P."""
    
    def __init__(self, symbol: str, expiration: str, ticks: List[StandardOptionTick]):
        self.symbol = symbol
        self.expiration = expiration
        self.ticks = ticks
        
        # Build indices
        self.calls: Dict[float, StandardOptionTick] = {}
        self.puts: Dict[float, StandardOptionTick] = {}
        
        for tick in ticks:
            if tick.right == "C":
                self.calls[tick.strike] = tick
            elif tick.right == "P":
                self.puts[tick.strike] = tick
        
        logger.debug(f"[chain_index] {symbol} {expiration}: {len(self.calls)} calls, {len(self.puts)} puts")
    
    def get_call(self, strike: float) -> Optional[StandardOptionTick]:
        return self.calls.get(strike)
    
    def get_put(self, strike: float) -> Optional[StandardOptionTick]:
        return self.puts.get(strike)
    
    def sorted_strikes(self) -> List[float]:
        """All strikes (union of calls and puts), sorted."""
        strikes = set(self.calls.keys()) | set(self.puts.keys())
        return sorted(strikes)


def compute_dte(expiration_str: str) -> int:
    """
    Compute calendar days to expiration from today.
    Expiration format: ISO date string (e.g. "2024-01-19").
    """
    try:
        exp_date = date.fromisoformat(expiration_str)
        today = date.today()
        delta = (exp_date - today).days
        return max(0, delta)  # Never negative
    except Exception as e:
        logger.warning(f"[chain_index] Failed to parse expiration '{expiration_str}': {e}")
        return 0


def group_by_expiration(ticks: List[StandardOptionTick]) -> Dict[str, List[StandardOptionTick]]:
    """Group ticks by expiration."""
    groups = defaultdict(list)
    for tick in ticks:
        groups[tick.expiration].append(tick)
    return dict(groups)
