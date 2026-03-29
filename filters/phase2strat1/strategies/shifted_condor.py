"""
Shifted Iron Condor strategy scanner (BUY/SELL, Imbalanced).
Doc reference: Page 8, 9
"""
import logging
from typing import List
from datetime import datetime

from filters.phase2strat1.models import Leg
from filters.phase2strat1.chain_index import ChainIndex
from filters.phase2strat1.spread_math import apply_spread_cap
from filters.phase2strat1.strategies.base import BaseStrategy, StrategyCandidate, STRATEGY_TYPES

logger = logging.getLogger(__name__)


class ShiftedCondorStrategy(BaseStrategy):
    """
    Shifted Iron Condor scanner.
    Supports BUY, SELL, and imbalanced quantities.
    
    Structure:
        - First spread at one set of strikes
        - Second spread at DIFFERENT strikes but same notional
        - Example: Call spread 79/80 + Put spread 81/80 (puts ABOVE calls)
    """
    
    @property
    def strategy_type(self) -> str:
        return "SHIFTED_IC"
    
    def scan(
        self,
        chain_idx: ChainIndex,
        dte: int,
        fee_per_leg: float,
        spread_cap_bound: float = 0.01,
        min_liquidity_bid: float = 0.0,
        min_liquidity_ask: float = 0.0,
        include_imbalanced: bool = False,
        **kwargs
    ) -> List[StrategyCandidate]:
        """
        Scan for Shifted IC candidates (BUY/SELL).
        
        Returns:
            List of StrategyCandidate objects
        """
        candidates = []
        strikes = chain_idx.sorted_strikes()
        
        # Enumerate all pairs of spreads with matching notional
        for i in range(len(strikes) - 1):
            for j in range(i + 1, len(strikes)):
                call_low = strikes[i]
                call_high = strikes[j]
                call_width = call_high - call_low
                
                # Try shifted put spreads ABOVE or BELOW call spread
                for k in range(len(strikes) - 1):
                    for l in range(k + 1, len(strikes)):
                        put_low = strikes[k]
                        put_high = strikes[l]
                        put_width = put_high - put_low
                        
                        # Match notional (same width for standard qty)
                        if put_width != call_width:
                            continue
                        
                        # Skip standard IC (same strikes)
                        if call_low == put_low and call_high == put_high:
                            continue
                        
                        # Build BUY side
                        buy_candidate = self._build_shifted_ic(
                            chain_idx, dte, fee_per_leg, spread_cap_bound,
                            "buy", "SHIFTED_IC_BUY",
                            call_low, call_high, put_low, put_high,
                            call_width, min_liquidity_bid, min_liquidity_ask
                        )
                        if buy_candidate:
                            candidates.append(buy_candidate)
                        
                        # Build SELL side
                        sell_candidate = self._build_shifted_ic(
                            chain_idx, dte, fee_per_leg, spread_cap_bound,
                            "sell", "SHIFTED_IC_SELL",
                            call_low, call_high, put_low, put_high,
                            call_width, min_liquidity_bid, min_liquidity_ask
                        )
                        if sell_candidate:
                            candidates.append(sell_candidate)
        
        logger.info(
            f"[ShiftedCondor] {chain_idx.symbol} {chain_idx.expiration}: "
            f"{len(candidates)} shifted IC candidates (BUY/SELL)"
        )
        return candidates
    
    def _build_shifted_ic(
        self,
        chain_idx: ChainIndex,
        dte: int,
        fee_per_leg: float,
        spread_cap_bound: float,
        open_side: str,
        strategy_type: str,
        call_low_strike: float,
        call_high_strike: float,
        put_low_strike: float,
        put_high_strike: float,
        width: float,
        min_liquidity_bid: float,
        min_liquidity_ask: float
    ) -> StrategyCandidate:
        """Build Shifted IC candidate (BUY or SELL side)."""
        
        # Get all ticks
        call_low = chain_idx.get_call(call_low_strike)
        call_high = chain_idx.get_call(call_high_strike)
        put_low = chain_idx.get_put(put_low_strike)
        put_high = chain_idx.get_put(put_high_strike)
        
        if not all([call_low, call_high, put_low, put_high]):
            return None
        
        # Liquidity check
        if not self.check_liquidity_basic(
            [call_low, call_high, put_low, put_high],
            min_liquidity_bid,
            min_liquidity_ask
        ):
            return None
        
        # Build spreads
        call_spread_raw = call_low.mid - call_high.mid
        call_spread_capped = apply_spread_cap(call_spread_raw, width, spread_cap_bound)
        
        put_spread_raw = put_low.mid - put_high.mid
        put_spread_capped = apply_spread_cap(put_spread_raw, width, spread_cap_bound)
        
        total_mid_entry = call_spread_capped + put_spread_capped
        
        # Validate based on side
        if open_side == "buy":
            if total_mid_entry <= 0 or total_mid_entry >= width:
                return None
        else:  # sell
            if total_mid_entry <= width:
                return None
        
        # Determine leg actions based on side
        if open_side == "buy":
            call_low_action, call_high_action = "BUY", "SELL"
            put_low_action, put_high_action = "BUY", "SELL"
        else:
            call_low_action, call_high_action = "SELL", "BUY"
            put_low_action, put_high_action = "SELL", "BUY"
        
        leg_count = 4
        total_quantity = 4
        fees_total = total_quantity * fee_per_leg
        
        # Remaining profit
        if open_side == "buy":
            remaining_profit = width - total_mid_entry - fees_total
        else:
            remaining_profit = total_mid_entry - width - fees_total
        
        if remaining_profit <= 0:
            return None
        
        break_even_days = self.compute_bed(remaining_profit, width)
        
        # Build legs
        legs = [
            Leg(
                leg_index=1,
                strike=call_low.strike,
                right="C",
                open_action=call_low_action,
                quantity=1,
                bid=call_low.bid,
                ask=call_low.ask,
                mid=call_low.mid,
                volume=call_low.volume,
                open_interest=call_low.open_interest
            ),
            Leg(
                leg_index=2,
                strike=call_high.strike,
                right="C",
                open_action=call_high_action,
                quantity=1,
                bid=call_high.bid,
                ask=call_high.ask,
                mid=call_high.mid,
                volume=call_high.volume,
                open_interest=call_high.open_interest
            ),
            Leg(
                leg_index=3,
                strike=put_low.strike,
                right="P",
                open_action=put_low_action,
                quantity=1,
                bid=put_low.bid,
                ask=put_low.ask,
                mid=put_low.mid,
                volume=put_low.volume,
                open_interest=put_low.open_interest
            ),
            Leg(
                leg_index=4,
                strike=put_high.strike,
                right="P",
                open_action=put_high_action,
                quantity=1,
                bid=put_high.bid,
                ask=put_high.ask,
                mid=put_high.mid,
                volume=put_high.volume,
                open_interest=put_high.open_interest
            )
        ]
        
        strikes_used = sorted(set([
            call_low.strike, call_high.strike,
            put_low.strike, put_high.strike
        ]))
        
        from filters.phase2strat1.spread_math import compute_annual_return
        annual_return = compute_annual_return(remaining_profit, width, dte)
        
        candidate = StrategyCandidate(
            strategy_type=strategy_type,
            symbol=chain_idx.symbol,
            expiration=chain_idx.expiration,
            dte=dte,
            open_side=open_side,
            is_imbalanced=False,
            legs=legs,
            leg_count=leg_count,
            strike_difference=width,
            strikes_used=strikes_used,
            buy_notional=width,
            sell_notional=width,
            total_quantity=total_quantity,
            raw_spreads={
                "call_spread": call_spread_raw,
                "put_spread": put_spread_raw,
                "total": call_spread_raw + put_spread_raw
            },
            capped_spreads={
                "call_spread": call_spread_capped,
                "put_spread": put_spread_capped,
                "total": total_mid_entry
            },
            mid_entry=total_mid_entry,
            spread_cost=total_mid_entry,
            net_credit=-total_mid_entry if open_side == "buy" else total_mid_entry,
            fee_per_leg=fee_per_leg,
            fees_total=fees_total,
            remaining_profit=remaining_profit,
            remaining_percent=(remaining_profit / width) * 100,
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
