"""
Standardized data model for option ticks across all providers.
All providers (ThetaData, yfinance, Tradier, Schwab) MUST convert
their raw data to this format before pushing to the cache.
"""
from dataclasses import dataclass, asdict
from datetime import datetime
import json


@dataclass
class StandardOptionTick:
    """Unified option quote tick — the single contract between Phase 1 and Phase 2."""
    root: str            # Underlying ticker e.g. "AAPL"
    expiration: str      # ISO date string e.g. "2024-01-19"
    strike: float        # Strike price e.g. 150.0
    right: str           # "C" or "P"
    bid: float
    ask: float
    mid: float           # (bid + ask) / 2 — used by all Phase 1 calculations
    volume: int          # Contract volume (0 if unavailable)
    open_interest: int   # Open interest (0 if unavailable)
    timestamp: str       # ISO datetime string of when tick was captured
    provider: str        # Source provider name e.g. "yfinance", "theta", "tradier"

    def to_dict(self) -> dict:
        return asdict(self)

    def to_json(self) -> str:
        return json.dumps(self.to_dict())

    @staticmethod
    def from_dict(d: dict) -> "StandardOptionTick":
        return StandardOptionTick(**d)

    @staticmethod
    def from_json(s: str) -> "StandardOptionTick":
        return StandardOptionTick.from_dict(json.loads(s))

    @staticmethod
    def make(root, expiration, strike, right, bid, ask, volume=0,
             open_interest=0, provider="unknown") -> "StandardOptionTick":
        bid = round(float(bid), 4)
        ask = round(float(ask), 4)
        mid = round((bid + ask) / 2, 4)
        return StandardOptionTick(
            root=root.upper(),
            expiration=str(expiration),
            strike=float(strike),
            right=right.upper(),
            bid=bid,
            ask=ask,
            mid=mid,
            volume=int(volume),
            open_interest=int(open_interest),
            timestamp=datetime.utcnow().isoformat(),
            provider=provider,
        )
