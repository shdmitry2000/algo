"""
Unified data models for all strategies.

These models are used across the entire system:
- Filter pipeline (filters/phase2strat1/)
- Arbitrage system (open_trade/)
- Option_X optimizer (option_x/)
"""
from dataclasses import dataclass, asdict
from typing import List, Dict, Optional, Any
from datetime import datetime
import json


@dataclass
class Leg:
    """
    Single option leg within a strategy.
    """
    leg_index: int
    strike: float
    right: str  # "C" or "P"
    open_action: str  # "BUY" or "SELL"
    quantity: int
    bid: float
    ask: float
    mid: float
    volume: int = 0
    open_interest: int = 0
    
    # Optional fields
    symbol: Optional[str] = None  # OCC symbol when available
    expiration: Optional[str] = None  # For calendar spreads (multi-expiration)

    def to_dict(self) -> dict:
        return asdict(self)
    
    @staticmethod
    def from_dict(d: dict) -> "Leg":
        return Leg(**d)


@dataclass
class StrategyCandidate:
    """
    Universal strategy candidate representation.
    
    Supports:
    - All strategy types (IC, BF, Shifted, Flygonaal, Calendar)
    - BUY/SELL sides
    - Standard and imbalanced quantities
    - Single and multi-expiration strategies
    """
    # Identity
    strategy_type: str  # "IC_BUY", "FLYGONAAL_BUY", "CALENDAR_BUY_C", etc.
    symbol: str
    expiration: str  # Primary expiration
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
    
    # Optional fields (with defaults - must come after required fields)
    is_imbalanced: bool = False  # True if quantities differ from standard 1x1
    buy_notional: Optional[float] = None  # Sum of buy side notional
    sell_notional: Optional[float] = None  # Sum of sell side notional
    total_quantity: Optional[int] = None  # Sum of all leg quantities
    
    # Multi-expiration support (for calendar spreads)
    expirations: Optional[List[str]] = None  # All expirations used
    dte_range: Optional[tuple] = None  # (min_dte, max_dte) for calendar spreads
    
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
    
    @staticmethod
    def from_json(s: str) -> "StrategyCandidate":
        """Deserialize from JSON."""
        return StrategyCandidate.from_dict(json.loads(s))


@dataclass
class ChainData:
    """
    Unified option chain data model.
    
    Supports both single and multi-expiration chains.
    Provides efficient lookup by strike and expiration.
    """
    symbol: str
    spot_price: float
    expirations: List[str]  # One or more expirations
    ticks: List  # List[StandardOptionTick] - avoid circular import
    
    # Cached indices for performance (built on first access)
    _call_index: Optional[Dict] = None
    _put_index: Optional[Dict] = None
    _strikes_by_exp: Optional[Dict] = None
    
    def __post_init__(self):
        """Build indices for fast lookup."""
        self._build_indices()
    
    def _build_indices(self):
        """Build call/put indices by strike and expiration."""
        self._call_index = {}
        self._put_index = {}
        self._strikes_by_exp = {}
        
        for tick in self.ticks:
            key = (tick.strike, tick.expiration)
            
            if tick.right == "C":
                self._call_index[key] = tick
            elif tick.right == "P":
                self._put_index[key] = tick
            
            # Track strikes by expiration
            if tick.expiration not in self._strikes_by_exp:
                self._strikes_by_exp[tick.expiration] = set()
            self._strikes_by_exp[tick.expiration].add(tick.strike)
    
    def get_call(self, strike: float, expiration: Optional[str] = None):
        """
        Get call option at strike.
        
        Args:
            strike: Strike price
            expiration: Optional expiration filter. If None, uses first expiration.
        
        Returns:
            StandardOptionTick or None
        """
        if expiration is None:
            expiration = self.expirations[0]
        return self._call_index.get((strike, expiration))
    
    def get_put(self, strike: float, expiration: Optional[str] = None):
        """
        Get put option at strike.
        
        Args:
            strike: Strike price
            expiration: Optional expiration filter. If None, uses first expiration.
        
        Returns:
            StandardOptionTick or None
        """
        if expiration is None:
            expiration = self.expirations[0]
        return self._put_index.get((strike, expiration))
    
    def sorted_strikes(self, expiration: Optional[str] = None) -> List[float]:
        """
        Get sorted strikes.
        
        Args:
            expiration: Optional expiration filter. If None, uses all strikes.
        
        Returns:
            Sorted list of strikes
        """
        if expiration is None:
            # Return all unique strikes across all expirations
            all_strikes = set()
            for strikes in self._strikes_by_exp.values():
                all_strikes.update(strikes)
            return sorted(all_strikes)
        else:
            return sorted(self._strikes_by_exp.get(expiration, set()))
    
    def filter_by_expiration(self, expiration: str) -> "ChainData":
        """
        Create a new ChainData with only ticks from specified expiration.
        
        Args:
            expiration: Expiration to filter by
        
        Returns:
            New ChainData instance
        """
        filtered_ticks = [t for t in self.ticks if t.expiration == expiration]
        return ChainData(
            symbol=self.symbol,
            spot_price=self.spot_price,
            expirations=[expiration],
            ticks=filtered_ticks
        )
    
    @staticmethod
    def from_chain_index(chain_idx) -> "ChainData":
        """
        Convert from legacy ChainIndex to new ChainData.
        
        Args:
            chain_idx: ChainIndex instance from filters/phase2strat1/chain_index.py
        
        Returns:
            ChainData instance
        """
        # This will be implemented in the adapter
        from strategies.adapters.filter_adapter import convert_chain_index_to_chain_data
        return convert_chain_index_to_chain_data(chain_idx)
