"""
Synthetic test data fixtures for strategy testing.

This module provides predictable, hardcoded option chain data for comprehensive testing.

Fixtures include:
- Single-expiration chains for IC, BF, Shifted strategies
- Multi-expiration chains for Calendar spreads
- ATM, OTM, and deep OTM scenarios
- Various strike spacings ($1, $5, $10)
- Multiple DTE scenarios (7, 30, 60, 365 days)
"""
from datetime import date, timedelta, datetime
from typing import Dict, List
from dataclasses import dataclass, asdict
from strategies.core import ChainData


@dataclass
class StandardOptionTick:
    """Unified option quote tick."""
    root: str
    expiration: str
    strike: float
    right: str  # "C" or "P"
    bid: float
    ask: float
    mid: float
    volume: int
    open_interest: int
    timestamp: str = ""
    provider: str = "synthetic"
    
    def to_dict(self) -> dict:
        return asdict(self)


class SyntheticChainBuilder:
    """
    Builder for creating synthetic option chains with predictable pricing.
    """
    
    def __init__(
        self,
        symbol: str,
        spot_price: float,
        expiration_date: date,
        strike_spacing: float = 1.0,
        num_strikes: int = 20
    ):
        self.symbol = symbol
        self.spot_price = spot_price
        self.expiration_date = expiration_date
        self.strike_spacing = strike_spacing
        self.num_strikes = num_strikes
        
        # Generate strikes centered around spot
        self.strikes = self._generate_strikes()
    
    def _generate_strikes(self) -> List[float]:
        """Generate strikes centered around spot price."""
        half_range = self.num_strikes // 2
        center_strike = round(self.spot_price / self.strike_spacing) * self.strike_spacing
        
        strikes = []
        for i in range(-half_range, half_range + 1):
            strike = center_strike + i * self.strike_spacing
            if strike > 0:  # Only positive strikes
                strikes.append(strike)
        
        return sorted(strikes)
    
    def _calculate_option_price(
        self,
        strike: float,
        right: str,
        dte: int
    ) -> tuple[float, float, float, int, int]:
        """
        Calculate synthetic option pricing (bid, ask, mid).
        
        Uses simple heuristic:
        - Intrinsic value + time value
        - Time value decays with sqrt(dte)
        - OTM options have only time value
        
        Returns:
            (bid, ask, mid, volume, open_interest)
        """
        # Intrinsic value
        if right == "C":
            intrinsic = max(0, self.spot_price - strike)
        else:  # Put
            intrinsic = max(0, strike - self.spot_price)
        
        # Time value (decreases with sqrt of time)
        moneyness = abs(self.spot_price - strike) / self.spot_price
        time_factor = (dte / 30) ** 0.5  # Normalize to ~30 days
        volatility_factor = 0.2  # Assumed 20% IV
        
        time_value = self.spot_price * volatility_factor * time_factor * (1 - moneyness)
        time_value = max(0.05, time_value)  # Minimum time value
        
        # Total option value
        mid = intrinsic + time_value
        
        # Bid-ask spread (1-2% of mid)
        spread = max(0.05, mid * 0.015)
        bid = mid - spread / 2
        ask = mid + spread / 2
        
        # Round to cents
        bid = round(bid, 2)
        ask = round(ask, 2)
        mid = round((bid + ask) / 2, 2)
        
        # Synthetic volume and OI (higher for ATM)
        volume = int(1000 * (1 - moneyness * 2))
        open_interest = int(5000 * (1 - moneyness * 2))
        
        return bid, ask, mid, max(0, volume), max(0, open_interest)
    
    def build_single_expiration(self) -> ChainData:
        """Build a ChainData with single expiration."""
        expiration_str = self.expiration_date.strftime("%Y-%m-%d")
        timestamp = datetime.utcnow().isoformat()
        
        ticks = []
        dte = (self.expiration_date - date.today()).days
        
        for strike in self.strikes:
            # Call
            call_bid, call_ask, call_mid, call_vol, call_oi = self._calculate_option_price(
                strike, "C", dte
            )
            call_tick = StandardOptionTick(
                root=self.symbol,
                expiration=expiration_str,
                strike=strike,
                right="C",
                bid=call_bid,
                ask=call_ask,
                mid=call_mid,
                volume=call_vol,
                open_interest=call_oi,
                timestamp=timestamp,
                provider="synthetic"
            )
            ticks.append(call_tick)
            
            # Put
            put_bid, put_ask, put_mid, put_vol, put_oi = self._calculate_option_price(
                strike, "P", dte
            )
            put_tick = StandardOptionTick(
                root=self.symbol,
                expiration=expiration_str,
                strike=strike,
                right="P",
                bid=put_bid,
                ask=put_ask,
                mid=put_mid,
                volume=put_vol,
                open_interest=put_oi,
                timestamp=timestamp,
                provider="synthetic"
            )
            ticks.append(put_tick)
        
        chain_data = ChainData(
            symbol=self.symbol,
            expirations=[expiration_str],
            ticks=ticks,
            spot_price=self.spot_price
        )
        
        return chain_data


def create_single_expiration_chain(
    symbol: str = "TEST",
    spot_price: float = 100.0,
    dte: int = 30,
    strike_spacing: float = 1.0,
    num_strikes: int = 20
) -> ChainData:
    """
    Create a simple single-expiration synthetic chain.
    
    Args:
        symbol: Ticker symbol
        spot_price: Current stock price
        dte: Days to expiration
        strike_spacing: Distance between strikes
        num_strikes: Total number of strikes
    
    Returns:
        ChainData with single expiration
    """
    expiration_date = date.today() + timedelta(days=dte)
    
    builder = SyntheticChainBuilder(
        symbol=symbol,
        spot_price=spot_price,
        expiration_date=expiration_date,
        strike_spacing=strike_spacing,
        num_strikes=num_strikes
    )
    
    return builder.build_single_expiration()


def create_multi_expiration_chain(
    symbol: str = "TEST",
    spot_price: float = 100.0,
    dte_list: List[int] = [30, 60, 90],
    strike_spacing: float = 1.0,
    num_strikes: int = 20
) -> ChainData:
    """
    Create a multi-expiration synthetic chain for calendar spreads.
    
    Args:
        symbol: Ticker symbol
        spot_price: Current stock price
        dte_list: List of DTEs for different expirations
        strike_spacing: Distance between strikes
        num_strikes: Total number of strikes
    
    Returns:
        ChainData with multiple expirations
    """
    # Build multiple single-expiration chains and merge ticks
    all_ticks = []
    expirations = []
    
    for dte in dte_list:
        expiration_date = date.today() + timedelta(days=dte)
        builder = SyntheticChainBuilder(
            symbol=symbol,
            spot_price=spot_price,
            expiration_date=expiration_date,
            strike_spacing=strike_spacing,
            num_strikes=num_strikes
        )
        chain = builder.build_single_expiration()
        
        # Collect all ticks
        all_ticks.extend(chain.ticks)
        expirations.append(chain.expirations[0])
    
    # Create multi-expiration ChainData
    multi_chain = ChainData(
        symbol=symbol,
        expirations=expirations,
        ticks=all_ticks,
        spot_price=spot_price
    )
    
    return multi_chain


# ============================================================================
# Standard Test Fixtures
# ============================================================================

def ic_test_chain() -> ChainData:
    """Standard chain for Iron Condor testing (30 DTE, $100 spot, $1 strikes)."""
    return create_single_expiration_chain(
        symbol="IC_TEST",
        spot_price=100.0,
        dte=30,
        strike_spacing=1.0,
        num_strikes=20
    )


def bf_test_chain() -> ChainData:
    """Standard chain for Butterfly testing (30 DTE, $100 spot, $1 strikes)."""
    return create_single_expiration_chain(
        symbol="BF_TEST",
        spot_price=100.0,
        dte=30,
        strike_spacing=1.0,
        num_strikes=20
    )


def flygonaal_test_chain() -> ChainData:
    """Standard chain for Flygonaal testing (45 DTE, $100 spot, $5 strikes)."""
    return create_single_expiration_chain(
        symbol="FLYG_TEST",
        spot_price=100.0,
        dte=45,
        strike_spacing=5.0,
        num_strikes=20
    )


def calendar_test_chain() -> ChainData:
    """Multi-expiration chain for Calendar spread testing."""
    return create_multi_expiration_chain(
        symbol="CAL_TEST",
        spot_price=100.0,
        dte_list=[30, 60, 90],
        strike_spacing=5.0,
        num_strikes=20
    )


def short_dte_chain() -> ChainData:
    """Short DTE chain for testing near-expiration behavior (7 DTE)."""
    return create_single_expiration_chain(
        symbol="SHORT_TEST",
        spot_price=50.0,
        dte=7,
        strike_spacing=0.5,
        num_strikes=20
    )


def long_dte_chain() -> ChainData:
    """Long DTE chain for testing LEAP behavior (365 DTE)."""
    return create_single_expiration_chain(
        symbol="LEAP_TEST",
        spot_price=200.0,
        dte=365,
        strike_spacing=10.0,
        num_strikes=30
    )


def wide_spread_chain() -> ChainData:
    """Wide strike spacing for testing shifted strategies ($10 strikes)."""
    return create_single_expiration_chain(
        symbol="WIDE_TEST",
        spot_price=500.0,
        dte=45,
        strike_spacing=10.0,
        num_strikes=30
    )


# ============================================================================
# Edge Case Fixtures
# ============================================================================

def low_liquidity_chain() -> ChainData:
    """Chain with low liquidity for testing liquidity filters."""
    chain = create_single_expiration_chain(
        symbol="ILLIQ_TEST",
        spot_price=10.0,
        dte=30,
        strike_spacing=0.5,
        num_strikes=10
    )
    
    # Reduce volume and OI to simulate illiquidity
    for tick in chain.ticks:
        tick.volume = 5
        tick.open_interest = 10
    
    return chain


def high_iv_chain() -> ChainData:
    """Chain with high implied volatility (expensive options)."""
    # Use custom builder with adjusted pricing
    builder = SyntheticChainBuilder(
        symbol="HIGHIV_TEST",
        spot_price=100.0,
        expiration_date=date.today() + timedelta(days=30),
        strike_spacing=2.0,
        num_strikes=20
    )
    
    chain = builder.build_single_expiration()
    
    # Inflate all option prices by 50% to simulate high IV
    for tick in chain.ticks:
        tick.bid *= 1.5
        tick.ask *= 1.5
        tick.mid *= 1.5
    
    return chain


def narrow_range_chain() -> ChainData:
    """Chain with narrow strike range (limited spread options)."""
    return create_single_expiration_chain(
        symbol="NARROW_TEST",
        spot_price=100.0,
        dte=30,
        strike_spacing=0.25,
        num_strikes=10
    )


# ============================================================================
# Utility Functions
# ============================================================================

def get_all_test_fixtures() -> Dict[str, ChainData]:
    """
    Get all test fixtures as a dictionary.
    
    Returns:
        Dict mapping fixture name to ChainData
    """
    return {
        "ic_test": ic_test_chain(),
        "bf_test": bf_test_chain(),
        "flygonaal_test": flygonaal_test_chain(),
        "calendar_test": calendar_test_chain(),
        "short_dte": short_dte_chain(),
        "long_dte": long_dte_chain(),
        "wide_spread": wide_spread_chain(),
        "low_liquidity": low_liquidity_chain(),
        "high_iv": high_iv_chain(),
        "narrow_range": narrow_range_chain(),
    }


def print_chain_summary(chain: ChainData, name: str = ""):
    """Print a summary of a ChainData for debugging."""
    print(f"\n{'='*60}")
    print(f"Chain Summary: {name or chain.symbol}")
    print(f"{'='*60}")
    print(f"Symbol: {chain.symbol}")
    print(f"Spot Price: ${chain.spot_price:.2f}")
    print(f"Expirations: {len(chain.expirations)}")
    for exp in chain.expirations:
        print(f"  - {exp}")
    print(f"Strikes: {len(chain.sorted_strikes())}")
    strikes = chain.sorted_strikes()
    if strikes:
        print(f"  Range: ${strikes[0]:.2f} - ${strikes[-1]:.2f}")
        print(f"  Spacing: ${strikes[1] - strikes[0]:.2f}")
    
    # Show ATM option pricing
    strikes_sorted = chain.sorted_strikes()
    if strikes_sorted:
        atm_strike = min(strikes_sorted, key=lambda s: abs(s - chain.spot_price))
        print(f"\nATM Strike ${atm_strike:.2f}:")
        
        if chain.expirations:
            exp = chain.expirations[0]
            call = chain.get_call(atm_strike, exp)
            put = chain.get_put(atm_strike, exp)
            
            if call:
                print(f"  Call: ${call.bid:.2f} / ${call.mid:.2f} / ${call.ask:.2f}")
            if put:
                print(f"  Put:  ${put.bid:.2f} / ${put.mid:.2f} / ${put.ask:.2f}")
    print(f"{'='*60}\n")
