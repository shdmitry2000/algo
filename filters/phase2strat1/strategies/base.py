"""
Base abstract class for strategy scanners.
All strategies (IC, BF, Shifted IC, Shifted BF) inherit from this.
Includes SELL side and imbalanced quantity support.
"""
from abc import ABC, abstractmethod
from dataclasses import dataclass, asdict
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime
import json

from filters.phase2strat1.models import Leg


# Strategy type identifiers (16 total variants)
STRATEGY_TYPES = {
    "IC_BUY": "Iron Condor (Buy)",
    "IC_SELL": "Iron Condor (Sell)",
    "IC_BUY_IMBAL": "Iron Condor (Buy Imbalanced)",
    "IC_SELL_IMBAL": "Iron Condor (Sell Imbalanced)",
    
    "BF_BUY": "Butterfly (Buy)",
    "BF_SELL": "Butterfly (Sell)",
    "BF_BUY_IMBAL": "Butterfly (Buy Imbalanced)",
    "BF_SELL_IMBAL": "Butterfly (Sell Imbalanced)",
    
    "SHIFTED_IC_BUY": "Shifted Condor (Buy)",
    "SHIFTED_IC_SELL": "Shifted Condor (Sell)",
    "SHIFTED_IC_BUY_IMBAL": "Shifted Condor (Buy Imbalanced)",
    "SHIFTED_IC_SELL_IMBAL": "Shifted Condor (Sell Imbalanced)",
    
    "SHIFTED_BF_BUY": "Shifted Butterfly (Buy)",
    "SHIFTED_BF_SELL": "Shifted Butterfly (Sell)",
    "SHIFTED_BF_BUY_IMBAL": "Shifted Butterfly (Buy Imbalanced)",
    "SHIFTED_BF_SELL_IMBAL": "Shifted Butterfly (Sell Imbalanced)",
}


@dataclass
class StrategyCandidate:
    """
    Single strategy calculation result with complete details.
    Supports BUY/SELL sides and imbalanced quantities.
    """
    strategy_type: str  # "IC_BUY", "IC_SELL", "BF_BUY_IMBAL", etc.
    symbol: str
    expiration: str
    dte: int
    
    # Side and balance
    open_side: str  # "buy" or "sell"
    
    # Leg details
    legs: List[Leg]
    leg_count: int
    
    # Strike details
    strike_difference: float  # Width of primary spread
    strikes_used: List[float]  # All unique strikes in this strategy
    
    # Pricing breakdown (raw and capped)
    raw_spreads: Dict[str, float]  # e.g. {"call_spread": 1.36, "put_spread": 0.12}
    capped_spreads: Dict[str, float]  # After spread cap applied
    mid_entry: float  # Total entry cost/credit
    spread_cost: float
    net_credit: float  # Positive for credit received, negative for debit paid
    
    # Fees
    fee_per_leg: float
    fees_total: float
    
    # Profitability metrics
    remaining_profit: float
    remaining_percent: float
    break_even_days: float
    annual_return_percent: float  # Annualized return: (remaining% / dte) * 365
    
    # Filter results
    bed_filter_pass: bool
    liquidity_pass: bool
    liquidity_detail: str
    structural_pass: bool
    
    # Ranking
    rank_score: float
    
    # Metadata
    computed_at: str
    
    # Fields with defaults must come after non-default fields
    is_imbalanced: bool = False  # True if quantities differ from standard 1x1
    buy_notional: Optional[float] = None  # Sum of buy side notional
    sell_notional: Optional[float] = None  # Sum of sell side notional
    total_quantity: Optional[int] = None  # Sum of all leg quantities
    
    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dict."""
        d = asdict(self)
        # Convert Leg objects to dicts
        d['legs'] = [leg.to_dict() if isinstance(leg, Leg) else leg for leg in d['legs']]
        return d
    
    def to_json(self) -> str:
        """Serialize to JSON."""
        return json.dumps(self.to_dict())
    
    @staticmethod
    def from_dict(d: Dict[str, Any]) -> "StrategyCandidate":
        """Deserialize from dict."""
        if 'legs' in d and d['legs']:
            d['legs'] = [Leg(**leg) if isinstance(leg, dict) else leg for leg in d['legs']]
        return StrategyCandidate(**d)


class BaseStrategy(ABC):
    """
    Abstract base class for all strategy scanners.
    Each strategy implements scan() to generate candidates.
    """
    
    @abstractmethod
    def scan(
        self,
        chain_idx,  # ChainIndex
        dte: int,
        fee_per_leg: float,
        spread_cap_bound: float = 0.01,
        **kwargs
    ) -> List[StrategyCandidate]:
        """
        Scan chain and generate strategy candidates.
        
        Args:
            chain_idx: ChainIndex with calls/puts indexed
            dte: Days to expiration
            fee_per_leg: Commission per contract
            spread_cap_bound: Spread cap bound (default 0.01)
            **kwargs: Strategy-specific parameters
        
        Returns:
            List of StrategyCandidate objects (not yet BED filtered)
        """
        pass
    
    @property
    @abstractmethod
    def strategy_type(self) -> str:
        """Return strategy type identifier (IC, BF, SHIFTED_IC, SHIFTED_BF)."""
        pass
    
    def compute_bed(self, remaining_profit: float, strike_width: float) -> float:
        """
        Compute Break-Even Days.
        Formula: BED = 365 * (remaining% / 100) = 365 * (remaining$ / width$)
        """
        if strike_width <= 0:
            return float('inf')
        remaining_percent = (remaining_profit / strike_width) * 100
        return (365 / 100) * remaining_percent
    
    def check_liquidity_basic(self, ticks: List, min_bid: float = 0.0, min_ask: float = 0.0) -> bool:
        """
        Basic liquidity check: all ticks must have bid > min_bid and ask > min_ask.
        """
        for tick in ticks:
            if tick.bid <= min_bid or tick.ask <= min_ask:
                return False
        return True
    
    def generate_imbalanced_quantities(
        self,
        max_total_legs: int = 10,
        max_ratio: int = 4
    ) -> List[Tuple[int, int]]:
        """
        Generate valid imbalanced quantity combinations.
        Per doc page 9: buy_notional >= sell_notional.
        
        Args:
            max_total_legs: Maximum total legs (buy + sell)
            max_ratio: Maximum ratio between buy and sell qty
        
        Returns:
            List of (buy_qty, sell_qty) tuples where buy_qty > sell_qty
        
        Examples:
            [(2, 1), (3, 1), (3, 2), (4, 1), (4, 2), (4, 3), ...]
        """
        combos = []
        
        # Generate combinations where buy_qty > sell_qty
        for buy_qty in range(2, max_total_legs):  # Start at 2 (1x1 is standard)
            for sell_qty in range(1, buy_qty):
                # Check total legs
                if buy_qty + sell_qty > max_total_legs:
                    continue
                
                # Check ratio (avoid extreme imbalances like 10x1)
                if buy_qty / sell_qty > max_ratio:
                    continue
                
                # Buy must dominate (already guaranteed by buy_qty > sell_qty)
                combos.append((buy_qty, sell_qty))
        
        return combos
    
    def compute_imbalanced_notionals(
        self,
        buy_legs: List[Leg],
        sell_legs: List[Leg],
        width: float
    ) -> Tuple[float, float]:
        """
        Compute buy and sell notionals for imbalanced strategies.
        Per doc page 9: sum(qty_buy x strikeWidth_buy).
        
        Args:
            buy_legs: Legs with BUY action
            sell_legs: Legs with SELL action
            width: Strike width
        
        Returns:
            (buy_notional, sell_notional) tuple
        """
        buy_notional = sum(leg.quantity * width for leg in buy_legs)
        sell_notional = sum(leg.quantity * width for leg in sell_legs)
        
        return buy_notional, sell_notional
