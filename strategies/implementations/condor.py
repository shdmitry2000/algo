"""
Condor strategy scanner.

CORRECT DEFINITION:
- Condor = 4 DISTINCT STRIKES, 4 LEGS (1x quantity each)
- Structure: Long 1 @ K1, Short 1 @ K2, Short 1 @ K3, Long 1 @ K4
- All options are same type (all calls OR all puts)
- Wider profit zone than butterfly (between K2 and K3)

Example:
    Call Condor: Buy 90C, Sell 95C, Sell 100C, Buy 105C
    Put Condor: Buy 105P, Sell 100P, Sell 95P, Buy 90P

Max profit occurs when underlying price is between K2 and K3 at expiration.

Difference from Butterfly:
    - Butterfly: 3 strikes (middle has 2x), narrow profit peak
    - Condor: 4 strikes (all 1x), wider profit plateau

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


@register_strategy("CONDOR")
class CondorStrategy(BaseStrategy):
    """
    Condor scanner (4 distinct strikes: K1 < K2 < K3 < K4).
    Wider profit zone than butterfly.
    """
    
    @property
    def strategy_type(self) -> str:
        return "CONDOR"
    
    def scan(
        self,
        chain_data: ChainData,
        dte: int,
        fee_per_leg: float,
        spread_cap_bound: float = 0.01,
        min_liquidity_bid: float = 0.0,
        min_liquidity_ask: float = 0.0,
        max_strike_gap: int = 3,
        **kwargs
    ) -> List[StrategyCandidate]:
        """
        Scan for Condor candidates (4 distinct strikes).
        
        Standard Condor:
            - 4 strikes: K1, K2, K3, K4 (typically equidistant or near-equidistant)
            - Long 1 @ K1, Short 1 @ K2, Short 1 @ K3, Long 1 @ K4
            - Max profit between K2 and K3
        """
        candidates = []
        strikes = chain_data.sorted_strikes()
        
        # Limit strike gap to avoid excessive candidates
        for i in range(len(strikes)):
            for j in range(i + 1, min(i + 1 + max_strike_gap, len(strikes))):
                for k in range(j + 1, min(j + 1 + max_strike_gap, len(strikes))):
                    for m in range(k + 1, min(k + 1 + max_strike_gap, len(strikes))):
                        K1, K2, K3, K4 = strikes[i], strikes[j], strikes[k], strikes[m]
                        
                        # Calculate widths
                        left_width = K2 - K1
                        right_width = K4 - K3
                        
                        # For standard condor, left and right widths should match
                        # (though this can be relaxed)
                        if left_width != right_width:
                            continue
                        
                        width = left_width
                        
                        # Call Condor (BUY)
                        call_buy = self._build_condor(
                            chain_data, dte, fee_per_leg, spread_cap_bound,
                            "call", "buy", "CONDOR_BUY",
                            K1, K2, K3, K4, width,
                            min_liquidity_bid, min_liquidity_ask
                        )
                        if call_buy:
                            candidates.append(call_buy)
                        
                        # Call Condor (SELL)
                        call_sell = self._build_condor(
                            chain_data, dte, fee_per_leg, spread_cap_bound,
                            "call", "sell", "CONDOR_SELL",
                            K1, K2, K3, K4, width,
                            min_liquidity_bid, min_liquidity_ask
                        )
                        if call_sell:
                            candidates.append(call_sell)
                        
                        # Put Condor (BUY)
                        put_buy = self._build_condor(
                            chain_data, dte, fee_per_leg, spread_cap_bound,
                            "put", "buy", "CONDOR_BUY",
                            K1, K2, K3, K4, width,
                            min_liquidity_bid, min_liquidity_ask
                        )
                        if put_buy:
                            candidates.append(put_buy)
                        
                        # Put Condor (SELL)
                        put_sell = self._build_condor(
                            chain_data, dte, fee_per_leg, spread_cap_bound,
                            "put", "sell", "CONDOR_SELL",
                            K1, K2, K3, K4, width,
                            min_liquidity_bid, min_liquidity_ask
                        )
                        if put_sell:
                            candidates.append(put_sell)
        
        logger.info(
            f"[Condor] {chain_data.symbol} {chain_data.expirations[0]}: "
            f"{len(candidates)} condor candidates (4 distinct strikes)"
        )
        return candidates
    
    def _build_condor(
        self,
        chain_data: ChainData,
        dte: int,
        fee_per_leg: float,
        spread_cap_bound: float,
        side: str,  # "call" or "put"
        open_side: str,  # "buy" or "sell"
        strategy_type: str,
        K1: float,
        K2: float,
        K3: float,
        K4: float,
        width: float,
        min_liquidity_bid: float,
        min_liquidity_ask: float
    ) -> Optional[StrategyCandidate]:
        """Build condor candidate (4 distinct strikes, 1x quantity each)."""
        
        # Get ticks
        if side == "call":
            tick1 = chain_data.get_call(K1)
            tick2 = chain_data.get_call(K2)
            tick3 = chain_data.get_call(K3)
            tick4 = chain_data.get_call(K4)
            right = "C"
        else:  # put
            tick1 = chain_data.get_put(K1)
            tick2 = chain_data.get_put(K2)
            tick3 = chain_data.get_put(K3)
            tick4 = chain_data.get_put(K4)
            right = "P"
        
        if not all([tick1, tick2, tick3, tick4]):
            return None
        
        # Liquidity check
        if not self.check_liquidity_basic([tick1, tick2, tick3, tick4], min_liquidity_bid, min_liquidity_ask):
            return None
        
        # Calculate spreads
        # Condor = (Long K1 + Long K4) - (Short K2 + Short K3)
        buy_spread_raw = tick1.mid - tick2.mid  # Left spread
        buy_spread_capped = apply_spread_cap(buy_spread_raw, width, spread_cap_bound)
        
        sell_spread_raw = tick3.mid - tick4.mid  # Right spread
        sell_spread_capped = apply_spread_cap(sell_spread_raw, width, spread_cap_bound)
        
        # Net cost/credit
        net = buy_spread_capped - sell_spread_capped
        
        # BUY Condor: net > 0 (we pay)
        # SELL Condor: net < 0 (we receive)
        if open_side == "buy" and net <= 0:
            return None
        if open_side == "sell" and net >= 0:
            return None
        
        # Use absolute value for calculations
        net_abs = abs(net)
        
        leg_count = 4  # Condor has 4 unique strikes
        total_quantity = 4  # 1 + 1 + 1 + 1
        fees_total = total_quantity * fee_per_leg
        
        # Remaining profit
        if open_side == "buy":
            remaining_profit = width - net_abs - fees_total
        else:
            remaining_profit = net_abs - width - fees_total
        
        if remaining_profit <= 0:
            return None
        
        break_even_days = compute_bed(remaining_profit, width)
        
        # Build legs (condor structure: 1x each)
        if open_side == "buy":
            action1, action2, action3, action4 = "BUY", "SELL", "SELL", "BUY"
        else:
            action1, action2, action3, action4 = "SELL", "BUY", "BUY", "SELL"
        
        legs = [
            Leg(
                leg_index=1,
                strike=K1,
                right=right,
                open_action=action1,
                quantity=1,
                bid=tick1.bid,
                ask=tick1.ask,
                mid=tick1.mid,
                volume=tick1.volume,
                open_interest=tick1.open_interest
            ),
            Leg(
                leg_index=2,
                strike=K2,
                right=right,
                open_action=action2,
                quantity=1,  # CONDOR: 1x at each strike
                bid=tick2.bid,
                ask=tick2.ask,
                mid=tick2.mid,
                volume=tick2.volume,
                open_interest=tick2.open_interest
            ),
            Leg(
                leg_index=3,
                strike=K3,
                right=right,
                open_action=action3,
                quantity=1,  # CONDOR: 1x at each strike
                bid=tick3.bid,
                ask=tick3.ask,
                mid=tick3.mid,
                volume=tick3.volume,
                open_interest=tick3.open_interest
            ),
            Leg(
                leg_index=4,
                strike=K4,
                right=right,
                open_action=action4,
                quantity=1,
                bid=tick4.bid,
                ask=tick4.ask,
                mid=tick4.mid,
                volume=tick4.volume,
                open_interest=tick4.open_interest
            )
        ]
        
        strikes_used = [K1, K2, K3, K4]
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
                "left_spread": buy_spread_raw,
                "right_spread": sell_spread_raw,
                "net": buy_spread_raw - sell_spread_raw
            },
            capped_spreads={
                "left_spread": buy_spread_capped,
                "right_spread": sell_spread_capped,
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
