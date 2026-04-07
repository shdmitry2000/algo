"""
Butterfly strategy scanner.

CORRECT DEFINITION:
- Butterfly = 3 STRIKES, 4 LEGS (middle strike has 2x quantity)
- Structure: Long 1 @ K1, Short 2 @ K2, Long 1 @ K3
- All options are same type (all calls OR all puts)
- Strikes are typically equidistant

Example:
    Call Butterfly: Buy 95C, Sell 2x 100C, Buy 105C
    Put Butterfly: Buy 105P, Sell 2x 100P, Buy 95P

Max profit occurs when underlying price = middle strike at expiration.

Supports BUY, SELL, and imbalanced quantity variants.
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


@register_strategy("BF")
class ButterflyStrategy(BaseStrategy):
    """
    Butterfly scanner (3 strikes: K1 < K2 < K3, with 2x quantity at K2).
    Supports BUY, SELL, and imbalanced quantities.
    """
    
    @property
    def strategy_type(self) -> str:
        return "BF"
    
    def scan(
        self,
        chain_data: ChainData,
        dte: int,
        fee_per_leg: float,
        spread_cap_bound: float = 0.01,
        min_liquidity_bid: float = 0.0,
        min_liquidity_ask: float = 0.0,
        include_imbalanced: bool = False,
        **kwargs
    ) -> List[StrategyCandidate]:
        """
        Scan for Butterfly candidates (3 strikes, symmetric).
        
        Standard Butterfly:
            - 3 strikes: K1, K2, K3 where K2 - K1 = K3 - K2
            - Long 1 @ K1, Short 2 @ K2, Long 1 @ K3
        """
        candidates = []
        strikes = chain_data.sorted_strikes()
        
        # Enumerate 3-strike symmetric combinations
        for i in range(len(strikes) - 2):
            low_strike = strikes[i]
            mid_strike = strikes[i + 1]
            high_strike = strikes[i + 2]
            
            # Check symmetry (equidistant strikes)
            left_width = mid_strike - low_strike
            right_width = high_strike - mid_strike
            
            if left_width != right_width:
                continue
            
            width = left_width
            
            # Call BF (BUY side)
            call_buy = self._build_butterfly(
                chain_data, dte, fee_per_leg, spread_cap_bound,
                "call", "buy", "BF_BUY",
                low_strike, mid_strike, high_strike, width,
                min_liquidity_bid, min_liquidity_ask
            )
            if call_buy:
                candidates.append(call_buy)
            
            # Call BF (SELL side)
            call_sell = self._build_butterfly(
                chain_data, dte, fee_per_leg, spread_cap_bound,
                "call", "sell", "BF_SELL",
                low_strike, mid_strike, high_strike, width,
                min_liquidity_bid, min_liquidity_ask
            )
            if call_sell:
                candidates.append(call_sell)
            
            # Put BF (BUY side)
            put_buy = self._build_butterfly(
                chain_data, dte, fee_per_leg, spread_cap_bound,
                "put", "buy", "BF_BUY",
                low_strike, mid_strike, high_strike, width,
                min_liquidity_bid, min_liquidity_ask
            )
            if put_buy:
                candidates.append(put_buy)
            
            # Put BF (SELL side)
            put_sell = self._build_butterfly(
                chain_data, dte, fee_per_leg, spread_cap_bound,
                "put", "sell", "BF_SELL",
                low_strike, mid_strike, high_strike, width,
                min_liquidity_bid, min_liquidity_ask
            )
            if put_sell:
                candidates.append(put_sell)
        
        logger.info(
            f"[Butterfly] {chain_data.symbol} {chain_data.expirations[0]}: "
            f"{len(candidates)} butterfly candidates (3 strikes)"
        )
        return candidates
    
    def _build_butterfly(
        self,
        chain_data: ChainData,
        dte: int,
        fee_per_leg: float,
        spread_cap_bound: float,
        side: str,  # "call" or "put"
        open_side: str,  # "buy" or "sell"
        strategy_type: str,
        low_strike: float,
        mid_strike: float,
        high_strike: float,
        width: float,
        min_liquidity_bid: float,
        min_liquidity_ask: float
    ) -> Optional[StrategyCandidate]:
        """Build butterfly candidate (3 strikes: low, mid, high with 2x at mid)."""
        
        # Get ticks
        if side == "call":
            low_tick = chain_data.get_call(low_strike)
            mid_tick = chain_data.get_call(mid_strike)
            high_tick = chain_data.get_call(high_strike)
            right = "C"
        else:  # put
            low_tick = chain_data.get_put(low_strike)
            mid_tick = chain_data.get_put(mid_strike)
            high_tick = chain_data.get_put(high_strike)
            right = "P"
        
        if not all([low_tick, mid_tick, high_tick]):
            return None
        
        # Liquidity check
        if not self.check_liquidity_basic([low_tick, mid_tick, high_tick], min_liquidity_bid, min_liquidity_ask):
            return None
        
        # Calculate spreads
        # Butterfly = (Long low + Long high) - (Short 2x mid)
        buy_spread_raw = low_tick.mid - mid_tick.mid
        buy_spread_capped = apply_spread_cap(buy_spread_raw, width, spread_cap_bound)
        
        sell_spread_raw = mid_tick.mid - high_tick.mid
        sell_spread_capped = apply_spread_cap(sell_spread_raw, width, spread_cap_bound)
        
        # Net cost/credit
        net = buy_spread_capped - sell_spread_capped
        
        # BUY BF: net > 0 (we pay)
        # SELL BF: net < 0 (we receive)
        if open_side == "buy" and net <= 0:
            return None
        if open_side == "sell" and net >= 0:
            return None
        
        # Use absolute value for calculations
        net_abs = abs(net)
        
        leg_count = 3  # Butterfly has 3 unique strikes
        total_quantity = 4  # 1 + 2 + 1
        fees_total = total_quantity * fee_per_leg
        
        # Remaining profit
        if open_side == "buy":
            remaining_profit = width - net_abs - fees_total
        else:
            remaining_profit = net_abs - width - fees_total
        
        if remaining_profit <= 0:
            return None
        
        break_even_days = compute_bed(remaining_profit, width)
        
        # Build legs (butterfly structure: 1x, 2x, 1x)
        if open_side == "buy":
            low_action, mid_action, high_action = "BUY", "SELL", "BUY"
        else:
            low_action, mid_action, high_action = "SELL", "BUY", "SELL"
        
        legs = [
            Leg(
                leg_index=1,
                strike=low_tick.strike,
                right=right,
                open_action=low_action,
                quantity=1,
                bid=low_tick.bid,
                ask=low_tick.ask,
                mid=low_tick.mid,
                volume=low_tick.volume,
                open_interest=low_tick.open_interest
            ),
            Leg(
                leg_index=2,
                strike=mid_tick.strike,
                right=right,
                open_action=mid_action,
                quantity=2,  # BUTTERFLY: 2x at middle strike
                bid=mid_tick.bid,
                ask=mid_tick.ask,
                mid=mid_tick.mid,
                volume=mid_tick.volume,
                open_interest=mid_tick.open_interest
            ),
            Leg(
                leg_index=3,
                strike=high_tick.strike,
                right=right,
                open_action=high_action,
                quantity=1,
                bid=high_tick.bid,
                ask=high_tick.ask,
                mid=high_tick.mid,
                volume=high_tick.volume,
                open_interest=high_tick.open_interest
            )
        ]
        
        strikes_used = sorted(set([low_tick.strike, mid_tick.strike, high_tick.strike]))
        annual_return = compute_annual_return(remaining_profit, width, dte)
        
        candidate = StrategyCandidate(
            strategy_type=strategy_type,
            symbol=chain_data.symbol,
            expiration=chain_data.expirations[0],
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
                "buy_spread": buy_spread_raw,
                "sell_spread": sell_spread_raw,
                "net": buy_spread_raw - sell_spread_raw
            },
            capped_spreads={
                "buy_spread": buy_spread_capped,
                "sell_spread": sell_spread_capped,
                "net": net
            },
            mid_entry=net_abs,
            spread_cost=net_abs,
            net_credit=-net_abs if open_side == "buy" else net_abs,
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
