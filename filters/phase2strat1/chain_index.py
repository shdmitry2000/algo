"""
Chain indexing and DTE calculation.
"""
import os
import logging
from typing import List, Dict, Optional
from datetime import date, datetime
from collections import defaultdict
from dotenv import load_dotenv

from datagathering.models import StandardOptionTick

load_dotenv()
logger = logging.getLogger(__name__)

# Phase 2 performance optimization: limit strikes to reduce calculation time
# Read from .env: -1 means unlimited (no filtering)
def _get_strike_limit(env_var: str, default: int) -> int:
    """Get strike limit from env, -1 means unlimited."""
    try:
        value = int(os.getenv(env_var, str(default)))
        return value
    except ValueError:
        return default

MAX_STRIKES_ITM = _get_strike_limit("MAX_STRIKES_ITM", 25)
MAX_STRIKES_OTM = _get_strike_limit("MAX_STRIKES_OTM", 25)


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
        
        # Apply strike filtering if enabled (Phase 2 performance optimization)
        if MAX_STRIKES_ITM != -1 and MAX_STRIKES_OTM != -1:
            self._apply_strike_filter()
        
        logger.debug(f"[chain_index] {symbol} {expiration}: {len(self.calls)} calls, {len(self.puts)} puts")
    
    def _estimate_atm_strike(self) -> Optional[float]:
        """
        Estimate ATM (at-the-money) strike from option prices.
        
        Uses put-call parity approximation: at ATM, call and put prices should be similar.
        Finds strike where |call_mid - put_mid| is minimized.
        
        Returns:
            ATM strike, or None if cannot determine
        """
        strikes = self.sorted_strikes()
        if not strikes:
            return None
        
        # Find strike where call and put prices are closest (put-call parity at ATM)
        min_diff = float('inf')
        atm_strike = strikes[0]
        
        for strike in strikes:
            call = self.calls.get(strike)
            put = self.puts.get(strike)
            
            # Need both call and put to compare
            if not call or not put:
                continue
            
            # At ATM, call and put should have similar extrinsic value
            diff = abs(call.mid - put.mid)
            
            if diff < min_diff:
                min_diff = diff
                atm_strike = strike
        
        return atm_strike
    
    def _apply_strike_filter(self) -> None:
        """
        Filter strikes to limit Phase 2 calculations to strikes around ATM.
        Number of strikes controlled by MAX_STRIKES_ITM and MAX_STRIKES_OTM env vars.
        
        Set MAX_STRIKES_ITM=-1 or MAX_STRIKES_OTM=-1 for unlimited (no filtering).
        
        This improves performance without affecting data gathering (Phase 1).
        All data remains in cache; we only calculate on relevant strikes.
        """
        if not self.calls and not self.puts:
            return
        
        atm_strike = self._estimate_atm_strike()
        if not atm_strike:
            logger.warning(f"[chain_index] {self.symbol} {self.expiration}: Cannot estimate ATM, no filtering")
            return
        
        all_strikes = self.sorted_strikes()
        
        # Split into ITM and OTM relative to ATM
        itm_strikes = [s for s in all_strikes if s < atm_strike]
        otm_strikes = [s for s in all_strikes if s > atm_strike]
        atm_strikes = [s for s in all_strikes if s == atm_strike]
        
        # Keep closest N ITM and OTM strikes
        # ITM: keep highest (closest to ATM)
        # OTM: keep lowest (closest to ATM)
        kept_itm = sorted(itm_strikes, reverse=True)[:MAX_STRIKES_ITM] if MAX_STRIKES_ITM > 0 else itm_strikes
        kept_otm = sorted(otm_strikes)[:MAX_STRIKES_OTM] if MAX_STRIKES_OTM > 0 else otm_strikes
        kept_strikes = set(kept_itm + kept_otm + atm_strikes)
        
        # Filter out strikes not in kept set
        original_call_count = len(self.calls)
        original_put_count = len(self.puts)
        
        self.calls = {k: v for k, v in self.calls.items() if k in kept_strikes}
        self.puts = {k: v for k, v in self.puts.items() if k in kept_strikes}
        
        logger.info(
            f"[chain_index] {self.symbol} {self.expiration}: Strike filter applied "
            f"(ATM: ${atm_strike:.2f}, ITM limit: {MAX_STRIKES_ITM}, OTM limit: {MAX_STRIKES_OTM}) - "
            f"Calls: {original_call_count} -> {len(self.calls)}, "
            f"Puts: {original_put_count} -> {len(self.puts)}, "
            f"Total strikes: {len(all_strikes)} -> {len(kept_strikes)}"
        )
    
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
