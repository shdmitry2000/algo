"""
Calendar (Time) Spread strategy scanner.

NEW STRATEGY - Implements multi-expiration time spreads.

Structure:
    Near-term expiration: T1 (e.g., 30 days)
    Far-term expiration: T2 (e.g., 60 days)
    Same strike K
    
    Standard Calendar:
        - Sell near-term option (T1)
        - Buy far-term option (T2)
        - Profit from theta decay (near expires faster)
    
    Diagonal Calendar:
        - Different strikes K1, K2
        - Combines directional bias with time decay

Characteristics:
    - Benefits from time decay
    - Sensitive to volatility changes
    - Lower risk than outright long options
    - Ideal for range-bound markets with expected IV expansion

Supports:
    - Call calendars (CALENDAR_BUY_C, CALENDAR_SELL_C)
    - Put calendars (CALENDAR_BUY_P, CALENDAR_SELL_P)
    - Diagonal spreads (DIAGONAL_BUY_C/P, DIAGONAL_SELL_C/P)
"""
import logging
from typing import List, Optional, Dict, Tuple
from datetime import datetime, timedelta

from strategies.core import (
    BaseStrategy,
    StrategyCandidate,
    Leg,
    ChainData,
    apply_spread_cap,
    compute_bed,
    compute_annual_return,
)
from strategies.core.registry import register_strategy

logger = logging.getLogger(__name__)


@register_strategy("CALENDAR")
class CalendarSpreadStrategy(BaseStrategy):
    """
    Calendar spread (time spread) strategy scanner.
    """
    
    @property
    def strategy_type(self) -> str:
        return "CALENDAR"
    
    def scan(
        self,
        chain_data: ChainData,
        dte: int,  # Primary DTE (near-term)
        fee_per_leg: float,
        spread_cap_bound: float = 0.01,
        min_liquidity_bid: float = 0.0,
        min_liquidity_ask: float = 0.0,
        min_dte_difference: int = 20,
        max_dte_difference: int = 90,
        include_diagonal: bool = True,
        max_strike_gap: int = 2,
        **kwargs
    ) -> List[StrategyCandidate]:
        """
        Generate calendar spread candidates.
        
        Requires chain_data with multiple expirations.
        
        Args:
            chain_data: Unified chain data with multiple expirations
            dte: Primary DTE (near-term expiration)
            fee_per_leg: Commission per contract
            spread_cap_bound: Spread cap bound
            min_liquidity_bid: Minimum bid for liquidity
            min_liquidity_ask: Minimum ask for liquidity
            min_dte_difference: Minimum days between near and far expiration
            max_dte_difference: Maximum days between expirations
            include_diagonal: Include diagonal spreads (different strikes)
            max_strike_gap: Maximum strike gap for diagonals
        
        Returns:
            List of StrategyCandidate objects
        """
        if len(chain_data.expirations) < 2:
            logger.warning(
                f"[Calendar] {chain_data.symbol}: Requires at least 2 expirations, "
                f"found {len(chain_data.expirations)}"
            )
            return []
        
        candidates = []
        
        # Group expirations by DTE
        exp_by_dte = self._group_expirations_by_dte(chain_data)
        
        # Find near-term and far-term pairs
        for near_exp, near_dte in exp_by_dte.items():
            for far_exp, far_dte in exp_by_dte.items():
                if near_exp == far_exp:
                    continue
                
                dte_diff = far_dte - near_dte
                
                if not (min_dte_difference <= dte_diff <= max_dte_difference):
                    continue
                
                # Generate same-strike calendars
                same_strike_candidates = self._scan_same_strike_calendars(
                    chain_data, near_exp, far_exp, near_dte, far_dte,
                    fee_per_leg, spread_cap_bound,
                    min_liquidity_bid, min_liquidity_ask
                )
                candidates.extend(same_strike_candidates)
                
                # Generate diagonal calendars
                if include_diagonal:
                    diagonal_candidates = self._scan_diagonal_calendars(
                        chain_data, near_exp, far_exp, near_dte, far_dte,
                        fee_per_leg, spread_cap_bound,
                        min_liquidity_bid, min_liquidity_ask,
                        max_strike_gap
                    )
                    candidates.extend(diagonal_candidates)
        
        logger.info(
            f"[Calendar] {chain_data.symbol}: "
            f"{len(candidates)} calendar/diagonal candidates generated"
        )
        return candidates
    
    def _group_expirations_by_dte(self, chain_data: ChainData) -> Dict[str, int]:
        """
        Group expirations by DTE.
        
        Returns:
            Dict mapping expiration string to DTE
        """
        from datetime import date
        
        exp_by_dte = {}
        today = date.today()
        
        for expiration in chain_data.expirations:
            # Parse expiration date
            exp_date = datetime.strptime(expiration, "%Y-%m-%d").date()
            dte_val = (exp_date - today).days
            exp_by_dte[expiration] = dte_val
        
        return exp_by_dte
    
    def _scan_same_strike_calendars(
        self,
        chain_data: ChainData,
        near_exp: str,
        far_exp: str,
        near_dte: int,
        far_dte: int,
        fee_per_leg: float,
        spread_cap_bound: float,
        min_liquidity_bid: float,
        min_liquidity_ask: float
    ) -> List[StrategyCandidate]:
        """Generate calendars at same strike across expirations."""
        candidates = []
        
        # Find strikes available in both expirations
        near_strikes = set(chain_data.sorted_strikes(near_exp))
        far_strikes = set(chain_data.sorted_strikes(far_exp))
        common_strikes = near_strikes.intersection(far_strikes)
        
        for strike in common_strikes:
            # Try both calls and puts
            for right in ["C", "P"]:
                # Get options
                if right == "C":
                    near_opt = chain_data.get_call(strike, near_exp)
                    far_opt = chain_data.get_call(strike, far_exp)
                else:
                    near_opt = chain_data.get_put(strike, near_exp)
                    far_opt = chain_data.get_put(strike, far_exp)
                
                if not near_opt or not far_opt:
                    continue
                
                # Liquidity check
                if not self.check_liquidity_basic(
                    [near_opt, far_opt],
                    min_liquidity_bid,
                    min_liquidity_ask
                ):
                    continue
                
                # Calendar spread: sell near, buy far (BUY side)
                # Far option should have more time value
                time_spread_cost = far_opt.mid - near_opt.mid
                
                if time_spread_cost <= 0:
                    continue  # Invalid calendar (far should be more expensive)
                
                # Build BUY calendar (standard: sell near, buy far)
                buy_candidate = self._build_calendar(
                    chain_data, near_exp, far_exp, near_dte, far_dte,
                    strike, strike, right, "buy",
                    near_opt, far_opt, time_spread_cost,
                    fee_per_leg, is_diagonal=False
                )
                if buy_candidate:
                    candidates.append(buy_candidate)
                
                # Build SELL calendar (reverse: buy near, sell far)
                sell_candidate = self._build_calendar(
                    chain_data, near_exp, far_exp, near_dte, far_dte,
                    strike, strike, right, "sell",
                    near_opt, far_opt, time_spread_cost,
                    fee_per_leg, is_diagonal=False
                )
                if sell_candidate:
                    candidates.append(sell_candidate)
        
        return candidates
    
    def _scan_diagonal_calendars(
        self,
        chain_data: ChainData,
        near_exp: str,
        far_exp: str,
        near_dte: int,
        far_dte: int,
        fee_per_leg: float,
        spread_cap_bound: float,
        min_liquidity_bid: float,
        min_liquidity_ask: float,
        max_strike_gap: int
    ) -> List[StrategyCandidate]:
        """Generate diagonal calendars (different strikes + different expirations)."""
        candidates = []
        
        near_strikes = chain_data.sorted_strikes(near_exp)
        far_strikes = chain_data.sorted_strikes(far_exp)
        
        # Try adjacent and near-adjacent strikes
        for near_strike in near_strikes:
            for far_strike in far_strikes:
                strike_diff = abs(far_strike - near_strike)
                
                # Limit to reasonable gaps
                if strike_diff == 0 or strike_diff > max_strike_gap * 5:
                    continue
                
                # Try both calls and puts
                for right in ["C", "P"]:
                    if right == "C":
                        near_opt = chain_data.get_call(near_strike, near_exp)
                        far_opt = chain_data.get_call(far_strike, far_exp)
                    else:
                        near_opt = chain_data.get_put(near_strike, near_exp)
                        far_opt = chain_data.get_put(far_strike, far_exp)
                    
                    if not near_opt or not far_opt:
                        continue
                    
                    # Liquidity check
                    if not self.check_liquidity_basic(
                        [near_opt, far_opt],
                        min_liquidity_bid,
                        min_liquidity_ask
                    ):
                        continue
                    
                    # Diagonal spread cost
                    diagonal_cost = far_opt.mid - near_opt.mid
                    
                    if diagonal_cost <= 0:
                        continue
                    
                    # Build BUY diagonal
                    buy_candidate = self._build_calendar(
                        chain_data, near_exp, far_exp, near_dte, far_dte,
                        near_strike, far_strike, right, "buy",
                        near_opt, far_opt, diagonal_cost,
                        fee_per_leg, is_diagonal=True
                    )
                    if buy_candidate:
                        candidates.append(buy_candidate)
        
        return candidates
    
    def _build_calendar(
        self,
        chain_data: ChainData,
        near_exp: str,
        far_exp: str,
        near_dte: int,
        far_dte: int,
        near_strike: float,
        far_strike: float,
        right: str,
        open_side: str,
        near_opt,
        far_opt,
        spread_cost: float,
        fee_per_leg: float,
        is_diagonal: bool
    ) -> Optional[StrategyCandidate]:
        """Build a calendar spread candidate."""
        
        # Determine leg actions
        if open_side == "buy":
            near_action, far_action = "SELL", "BUY"
        else:
            near_action, far_action = "BUY", "SELL"
        
        # Build legs (note: legs have expiration field for multi-expiration)
        legs = [
            Leg(
                leg_index=1,
                strike=near_strike,
                right=right,
                open_action=near_action,
                quantity=1,
                bid=near_opt.bid,
                ask=near_opt.ask,
                mid=near_opt.mid,
                volume=near_opt.volume,
                open_interest=near_opt.open_interest,
                expiration=near_exp
            ),
            Leg(
                leg_index=2,
                strike=far_strike,
                right=right,
                open_action=far_action,
                quantity=1,
                bid=far_opt.bid,
                ask=far_opt.ask,
                mid=far_opt.mid,
                volume=far_opt.volume,
                open_interest=far_opt.open_interest,
                expiration=far_exp
            )
        ]
        
        leg_count = 2
        total_quantity = 2
        fees_total = total_quantity * fee_per_leg
        
        # For calendars, max profit is typically the spread cost minus fees
        # (occurs when near expires worthless and far retains value)
        if open_side == "buy":
            remaining_profit = spread_cost - fees_total
            # Use spread cost as "width" for BED calculation
            width = spread_cost
        else:
            # Sell calendar: reverse logic (less common)
            remaining_profit = spread_cost - fees_total
            width = spread_cost
        
        if remaining_profit <= 0:
            return None
        
        break_even_days = compute_bed(remaining_profit, width)
        annual_return = compute_annual_return(remaining_profit, width, near_dte)
        
        # Build strategy type
        if is_diagonal:
            strategy_type = f"DIAGONAL_{open_side.upper()}_{right}"
        else:
            strategy_type = f"CALENDAR_{open_side.upper()}_{right}"
        
        strike_diff = abs(far_strike - near_strike)
        strikes_used = [near_strike, far_strike] if is_diagonal else [near_strike]
        
        candidate = StrategyCandidate(
            strategy_type=strategy_type,
            symbol=chain_data.symbol,
            expiration=near_exp,  # Primary expiration is near-term
            dte=near_dte,
            open_side=open_side,
            is_imbalanced=False,
            legs=legs,
            leg_count=leg_count,
            strike_difference=strike_diff,
            strikes_used=strikes_used,
            buy_notional=spread_cost,
            sell_notional=spread_cost,
            total_quantity=total_quantity,
            raw_spreads={
                "time_spread": spread_cost,
                "near_mid": near_opt.mid,
                "far_mid": far_opt.mid
            },
            capped_spreads={
                "time_spread": spread_cost,
                "total": spread_cost
            },
            mid_entry=spread_cost,
            spread_cost=spread_cost,
            net_credit=-spread_cost if open_side == "buy" else spread_cost,
            fee_per_leg=fee_per_leg,
            fees_total=fees_total,
            remaining_profit=remaining_profit,
            remaining_percent=(remaining_profit / spread_cost) * 100,
            break_even_days=break_even_days,
            annual_return_percent=annual_return,
            bed_filter_pass=False,
            liquidity_pass=True,
            liquidity_detail="basic_check_pass",
            structural_pass=True,
            rank_score=0.0,
            expirations=[near_exp, far_exp],
            dte_range=(near_dte, far_dte),
            computed_at=datetime.utcnow().isoformat()
        )
        
        return candidate
