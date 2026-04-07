"""
Flygonaal (3:2:2:3) strategy scanner.

NEW STRATEGY - Implements the 3:2:2:3 wing configuration.

Structure:
    4 strikes: K_A < K_B < K_C < K_D
    
    Leg 1: Put K_A,  Q=3 (Long outer put wing)
    Leg 2: Put K_B,  Q=2 (Short inner put wing)
    Leg 3: Call K_C, Q=2 (Short inner call wing)
    Leg 4: Call K_D, Q=3 (Long outer call wing)

Characteristics:
    - Wider protective wings than standard IC (3x vs 1x)
    - More capital required but better risk/reward in tails
    - Ideal for high-volatility environments
    - Can handle larger price movements

Supports:
    - BUY side (pay debit, profit from movement)
    - SELL side (receive credit, profit from range-bound)
    - Imbalanced quantities (4:3:3:4, 5:3:3:5, etc.)
"""
import logging
from typing import List, Optional
from datetime import datetime

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


@register_strategy("FLYGONAAL")
class FlygonaalStrategy(BaseStrategy):
    """
    Flygonaal strategy scanner (3:2:2:3 wing configuration).
    """
    
    @property
    def strategy_type(self) -> str:
        return "FLYGONAAL"
    
    def scan(
        self,
        chain_data: ChainData,
        dte: int,
        fee_per_leg: float,
        spread_cap_bound: float = 0.01,
        min_liquidity_bid: float = 0.0,
        min_liquidity_ask: float = 0.0,
        min_wing_width: float = 5.0,
        max_wing_width: float = 20.0,
        include_imbalanced: bool = True,
        max_imbalanced_legs: int = 16,  # Higher than IC due to 3:2 ratio
        **kwargs
    ) -> List[StrategyCandidate]:
        """
        Generate Flygonaal (3:2:2:3) candidates.
        
        Args:
            chain_data: Unified chain data
            dte: Days to expiration
            fee_per_leg: Commission per contract
            spread_cap_bound: Spread cap bound (default 0.01)
            min_liquidity_bid: Minimum bid for liquidity check
            min_liquidity_ask: Minimum ask for liquidity check
            min_wing_width: Minimum distance between K_A and K_B (or K_C and K_D)
            max_wing_width: Maximum wing width
            include_imbalanced: Include non-3:2 ratios (e.g., 4:3:3:4)
            max_imbalanced_legs: Maximum total legs for imbalanced
        
        Returns:
            List of StrategyCandidate objects
        """
        candidates = []
        strikes = chain_data.sorted_strikes()
        
        # Need at least 4 strikes
        if len(strikes) < 4:
            return candidates
        
        # Enumerate all 4-strike combinations where K_A < K_B < K_C < K_D
        for i in range(len(strikes)):
            for j in range(i + 1, len(strikes)):
                for k in range(j + 1, len(strikes)):
                    for m in range(k + 1, len(strikes)):
                        K_A, K_B, K_C, K_D = strikes[i], strikes[j], strikes[k], strikes[m]
                        
                        put_wing_width = K_B - K_A
                        call_wing_width = K_D - K_C
                        
                        # Wing width constraints
                        if not (min_wing_width <= put_wing_width <= max_wing_width):
                            continue
                        if not (min_wing_width <= call_wing_width <= max_wing_width):
                            continue
                        
                        # Build standard 3:2:2:3 candidate
                        standard_candidate = self._build_flygonaal(
                            chain_data, dte, fee_per_leg, spread_cap_bound,
                            K_A, K_B, K_C, K_D,
                            outer_qty=3, inner_qty=2,
                            min_liquidity_bid=min_liquidity_bid,
                            min_liquidity_ask=min_liquidity_ask
                        )
                        if standard_candidate:
                            candidates.append(standard_candidate)
                        
                        # Build imbalanced variants
                        if include_imbalanced:
                            # Try variations: 4:3, 5:3, 4:2, 5:4, etc.
                            imbal_combos = [
                                (4, 3), (5, 3), (4, 2), (5, 4), (6, 4)
                            ]
                            
                            for outer_qty, inner_qty in imbal_combos:
                                # Check total legs constraint
                                total_legs = 2 * (outer_qty + inner_qty)
                                if total_legs > max_imbalanced_legs:
                                    continue
                                
                                imbal_candidate = self._build_flygonaal(
                                    chain_data, dte, fee_per_leg, spread_cap_bound,
                                    K_A, K_B, K_C, K_D,
                                    outer_qty=outer_qty, inner_qty=inner_qty,
                                    min_liquidity_bid=min_liquidity_bid,
                                    min_liquidity_ask=min_liquidity_ask
                                )
                                if imbal_candidate:
                                    candidates.append(imbal_candidate)
        
        logger.info(
            f"[Flygonaal] {chain_data.symbol} {chain_data.expirations[0]}: "
            f"{len(candidates)} candidates generated (BUY/SELL/IMBAL)"
        )
        return candidates
    
    def _build_flygonaal(
        self,
        chain_data: ChainData,
        dte: int,
        fee_per_leg: float,
        spread_cap_bound: float,
        K_A: float,
        K_B: float,
        K_C: float,
        K_D: float,
        outer_qty: int,
        inner_qty: int,
        min_liquidity_bid: float,
        min_liquidity_ask: float
    ) -> Optional[StrategyCandidate]:
        """
        Build a single Flygonaal candidate.
        
        Args:
            K_A, K_B, K_C, K_D: Four strikes (ascending)
            outer_qty: Quantity for outer wings (K_A and K_D)
            inner_qty: Quantity for inner wings (K_B and K_C)
        """
        # Get option ticks
        put_A = chain_data.get_put(K_A)
        put_B = chain_data.get_put(K_B)
        call_C = chain_data.get_call(K_C)
        call_D = chain_data.get_call(K_D)
        
        if not all([put_A, put_B, call_C, call_D]):
            return None
        
        # Liquidity check
        if not self.check_liquidity_basic(
            [put_A, put_B, call_C, call_D],
            min_liquidity_bid,
            min_liquidity_ask
        ):
            return None
        
        # Calculate wing widths
        put_wing_width = K_B - K_A
        call_wing_width = K_D - K_C
        
        # Calculate spreads with quantities
        # Put wing: Long outer_qty at K_A, Short inner_qty at K_B
        put_spread_raw = outer_qty * put_A.mid - inner_qty * put_B.mid
        put_spread_capped = apply_spread_cap(
            put_spread_raw / outer_qty,  # Normalize for capping
            put_wing_width,
            spread_cap_bound
        ) * outer_qty  # Re-apply quantity
        
        # Call wing: Short inner_qty at K_C, Long outer_qty at K_D
        call_spread_raw = outer_qty * call_D.mid - inner_qty * call_C.mid
        call_spread_capped = apply_spread_cap(
            call_spread_raw / outer_qty,
            call_wing_width,
            spread_cap_bound
        ) * outer_qty
        
        # Total entry cost/credit
        total_mid_entry = put_spread_capped + call_spread_capped
        
        # Build legs (note: inner_qty is NEGATIVE for short positions)
        legs = [
            Leg(
                leg_index=1,
                strike=K_A,
                right="P",
                open_action="BUY",
                quantity=outer_qty,
                bid=put_A.bid,
                ask=put_A.ask,
                mid=put_A.mid,
                volume=put_A.volume,
                open_interest=put_A.open_interest
            ),
            Leg(
                leg_index=2,
                strike=K_B,
                right="P",
                open_action="SELL",
                quantity=inner_qty,
                bid=put_B.bid,
                ask=put_B.ask,
                mid=put_B.mid,
                volume=put_B.volume,
                open_interest=put_B.open_interest
            ),
            Leg(
                leg_index=3,
                strike=K_C,
                right="C",
                open_action="SELL",
                quantity=inner_qty,
                bid=call_C.bid,
                ask=call_C.ask,
                mid=call_C.mid,
                volume=call_C.volume,
                open_interest=call_C.open_interest
            ),
            Leg(
                leg_index=4,
                strike=K_D,
                right="C",
                open_action="BUY",
                quantity=outer_qty,
                bid=call_D.bid,
                ask=call_D.ask,
                mid=call_D.mid,
                volume=call_D.volume,
                open_interest=call_D.open_interest
            )
        ]
        
        # Calculate notionals (buy = outer wings, sell = inner wings)
        buy_notional = outer_qty * (put_wing_width + call_wing_width)
        sell_notional = inner_qty * (put_wing_width + call_wing_width)
        
        # Must satisfy: buy_notional >= sell_notional
        if buy_notional < sell_notional:
            return None
        
        # Total legs and fees
        total_quantity = 2 * (outer_qty + inner_qty)
        leg_count = 4
        fees_total = total_quantity * fee_per_leg
        
        # Determine side based on total_mid_entry
        # For Flygonaal, max risk is the larger wing width * inner_qty
        max_risk = max(put_wing_width, call_wing_width) * inner_qty
        
        if total_mid_entry < 0:
            # Credit received (SELL side)
            open_side = "sell"
            remaining_profit = abs(total_mid_entry) - max_risk - fees_total
        else:
            # Debit paid (BUY side)
            open_side = "buy"
            remaining_profit = max_risk - total_mid_entry - fees_total
        
        # Check profitability
        if remaining_profit <= 0:
            return None
        
        # Calculate metrics using buy_notional (per doc)
        break_even_days = compute_bed(remaining_profit, buy_notional)
        annual_return = compute_annual_return(remaining_profit, buy_notional, dte)
        
        # Build strategy type
        strategy_type = f"FLYGONAAL_{open_side.upper()}"
        if outer_qty != 3 or inner_qty != 2:
            strategy_type += "_IMBAL"
        
        strikes_used = [K_A, K_B, K_C, K_D]
        
        candidate = StrategyCandidate(
            strategy_type=strategy_type,
            symbol=chain_data.symbol,
            expiration=chain_data.expirations[0],
            dte=dte,
            open_side=open_side,
            is_imbalanced=(outer_qty != 3 or inner_qty != 2),
            legs=legs,
            leg_count=leg_count,
            strike_difference=(put_wing_width + call_wing_width) / 2,  # Average wing width
            strikes_used=strikes_used,
            buy_notional=buy_notional,
            sell_notional=sell_notional,
            total_quantity=total_quantity,
            raw_spreads={
                "put_wing": put_spread_raw / outer_qty,
                "call_wing": call_spread_raw / outer_qty,
                "put_wing_total": put_spread_raw,
                "call_wing_total": call_spread_raw,
                "outer_qty": outer_qty,
                "inner_qty": inner_qty
            },
            capped_spreads={
                "put_wing": put_spread_capped / outer_qty,
                "call_wing": call_spread_capped / outer_qty,
                "total": total_mid_entry
            },
            mid_entry=abs(total_mid_entry),
            spread_cost=abs(total_mid_entry),
            net_credit=total_mid_entry if open_side == "sell" else -total_mid_entry,
            fee_per_leg=fee_per_leg,
            fees_total=fees_total,
            remaining_profit=remaining_profit,
            remaining_percent=(remaining_profit / buy_notional) * 100,
            break_even_days=break_even_days,
            annual_return_percent=annual_return,
            bed_filter_pass=False,
            liquidity_pass=True,
            liquidity_detail="basic_check_pass",
            structural_pass=True,
            rank_score=0.0,
            computed_at=datetime.utcnow().isoformat()
        )
        
        return candidate
