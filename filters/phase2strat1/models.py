"""
Data models for Phase 2 signals and legs.
"""
from dataclasses import dataclass, asdict, field
from typing import List, Optional, Dict, Any
from datetime import datetime
import json


@dataclass
class Leg:
    """Single option leg within a structure."""
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
    symbol: Optional[str] = None  # OCC symbol when available

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class Signal:
    """
    Multi-strategy Phase 2 signal — one active per (symbol, expiration).
    Contains ALL calculated strategies (IC, BF, Shifted IC, Shifted BF) with best strategy selected.
    """
    signal_id: str
    symbol: str
    expiration: str
    dte: int
    
    # All strategies calculated for this symbol+expiration pair
    # Key: strategy_type ("IC", "BF", "SHIFTED_IC", "SHIFTED_BF")
    # Value: StrategyCandidate dict (serialized)
    strategies: Dict[str, Dict[str, Any]]
    
    # Best strategy (after ranking all strategies)
    best_strategy_type: str  # Key into strategies dict
    best_rank_score: float
    
    # Metadata
    chain_timestamp: str  # From chain metadata - used for uniqueness check
    run_id: Optional[str]
    computed_at: str
    
    # Minimal chain snapshot: only strikes used across ALL strategies
    # Format: {"chain": [...used strikes only...], "strategies": {...all strategy details...}}
    chain_snapshot: Optional[Dict[str, Any]] = None
    
    def to_dict(self) -> dict:
        """Serialize to dict."""
        return asdict(self)
    
    def to_json(self) -> str:
        """Serialize to JSON."""
        return json.dumps(self.to_dict())
    
    @staticmethod
    def from_dict(d: dict) -> "Signal":
        """Deserialize from dict."""
        return Signal(**d)
    
    @staticmethod
    def from_json(s: str) -> "Signal":
        """Deserialize from JSON."""
        return Signal.from_dict(json.loads(s))
    
    def get_best_strategy(self) -> Optional[Dict[str, Any]]:
        """Get the best strategy details."""
        return self.strategies.get(self.best_strategy_type)
    
    def get_strategy(self, strategy_type: str) -> Optional[Dict[str, Any]]:
        """Get specific strategy details."""
        return self.strategies.get(strategy_type)


@dataclass
class HistoryEvent:
    """Append-only history log entry."""
    ts: str  # ISO timestamp
    event_type: str  # e.g. "precheck_fail", "signal_upserted", "phase3_open_ok"
    symbol: str
    expiration: Optional[str] = None
    signal_id: Optional[str] = None
    run_id: Optional[str] = None
    payload: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> dict:
        return asdict(self)
    
    def to_json(self) -> str:
        return json.dumps(self.to_dict())
    
    @staticmethod
    def from_json(s: str) -> "HistoryEvent":
        return HistoryEvent(**json.loads(s))


@dataclass
class GateStatus:
    """Gate state for (symbol, expiration) pair."""
    status: str  # "idle", "signal_pending_open", "cleared_after_open", "cleared_after_fail"
    locked_signal_id: Optional[str]
    updated_at: str
    
    def to_dict(self) -> dict:
        return asdict(self)
    
    def to_json(self) -> str:
        return json.dumps(self.to_dict())
    
    @staticmethod
    def from_json(s: str) -> "GateStatus":
        return GateStatus(**json.loads(s))
