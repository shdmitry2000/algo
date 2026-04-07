"""
Iron Condor strategy scanner.

Migrated from filters/phase2strat1/strategies/iron_condor.py to use unified core library.

Generates IC buy/sell candidates with standard and imbalanced quantities.
Supports: BUY, SELL, BUY_IMBAL, SELL_IMBAL

Structure:
    - Call spread + Put spread at SAME strikes
    - Buy IC: total_spread < width (pay debit, max profit = width - spread - fees)
    - Sell IC: total_spread > width (receive credit, max profit = spread - width - fees)
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


@register_strategy("IC")
class IronCondorStrategy(BaseStrategy):
    """
    Iron Condor scanner (Standard IC at same strikes).
    Supports: BUY, SELL, BUY_IMBAL, SELL_IMBAL
    """
    
    @property
    def strategy_type(self) -> str:
        return "IC"
    
    def scan(
        self,
        chain_data: ChainData,
        dte: int,
        fee_per_leg: float,
        spread_cap_bound: float = 0.01,
        min_liquidity_bid: float = 0.0,
        min_liquidity_ask: float = 0.0,
        include_imbalanced: bool = False,
        max_imbalanced_legs: int = 8,
        **kwargs
    ) -> List[StrategyCandidate]:
        """
        Enumerate Iron Condor candidates (BUY, SELL, and imbalanced variants).
        
        Args:
            chain_data: Unified chain data
            dte: Days to expiration
            fee_per_leg: Commission per contract
            spread_cap_bound: Spread cap bound (default 0.01)
            min_liquidity_bid: Minimum bid for liquidity check
            min_liquidity_ask: Minimum ask for liquidity check
            include_imbalanced: Include imbalanced quantity variants
            max_imbalanced_legs: Maximum total legs for imbalanced
            **kwargs: Additional strategy-specific parameters
        
        Returns:
            List of StrategyCandidate objects (not yet filtered by BED)
        """
        candidates = []
        strikes = chain_data.sorted_strikes()
        
        # Enumerate all strike pairs
        for i, low_strike in enumerate(strikes):
            for j in range(i+1, len(strikes)):
                high_strike = strikes[j]
                width = high_strike - low_strike
                
                if width <= 0:
                    continue
                
                # Get all 4 legs for IC
                call_low = chain_data.get_call(low_strike)
                call_high = chain_data.get_call(high_strike)
                put_low = chain_data.get_put(low_strike)
                put_high = chain_data.get_put(high_strike)
                
                if not all([call_low, call_high, put_low, put_high]):
                    continue
                
                # Liquidity check
                if not self.check_liquidity_basic(
                    [call_low, call_high, put_low, put_high],
                    min_liquidity_bid,
                    min_liquidity_ask
                ):
                    continue
                
                # Build vertical spreads
                call_spread_raw = call_low.mid - call_high.mid
                call_spread_capped = apply_spread_cap(call_spread_raw, width, spread_cap_bound)
                
                put_spread_raw = put_low.mid - put_high.mid
                put_spread_capped = apply_spread_cap(put_spread_raw, width, spread_cap_bound)
                
                total_mid_entry = call_spread_capped + put_spread_capped
                
                # Standard 1x1 IC candidates
                
                # Buy IC: cost < width (debit)
                if total_mid_entry > 0 and total_mid_entry < width:
                    candidate = self._build_standard_ic(
                        chain_data, dte, "buy", "IC_BUY",
                        call_low, call_high, put_low, put_high,
                        width, call_spread_raw, call_spread_capped,
                        put_spread_raw, put_spread_capped,
                        total_mid_entry, fee_per_leg
                    )
                    if candidate:
                        candidates.append(candidate)
                
                # Sell IC: credit > width (credit)
                if total_mid_entry > width:
                    candidate = self._build_standard_ic(
                        chain_data, dte, "sell", "IC_SELL",
                        call_low, call_high, put_low, put_high,
                        width, call_spread_raw, call_spread_capped,
                        put_spread_raw, put_spread_capped,
                        total_mid_entry, fee_per_leg
                    )
                    if candidate:
                        candidates.append(candidate)
                
                # Imbalanced IC variants
                if include_imbalanced:
                    imbal_candidates = self._scan_imbalanced_ic(
                        chain_data, dte, fee_per_leg, spread_cap_bound,
                        call_low, call_high, put_low, put_high,
                        width, max_imbalanced_legs
                    )
                    candidates.extend(imbal_candidates)
        
        logger.info(
            f"[IronCondor] {chain_data.symbol} {chain_data.expirations[0]}: "
            f"{len(candidates)} candidates generated (BUY/SELL/IMBAL)"
        )
        return candidates
    
    def _build_standard_ic(
        self,
        chain_data: ChainData,
        dte: int,
        open_side: str,
        strategy_type: str,
        call_low,
        call_high,
        put_low,
        put_high,
        width: float,
        call_spread_raw: float,
        call_spread_capped: float,
        put_spread_raw: float,
        put_spread_capped: float,
        total_mid_entry: float,
        fee_per_leg: float
    ) -> Optional[StrategyCandidate]:
        """Build standard 1x1 IC candidate (BUY or SELL side)."""
        
        # For SELL IC, reverse leg actions
        if open_side == "sell":
            call_low_action, call_high_action = "SELL", "BUY"
            put_low_action, put_high_action = "SELL", "BUY"
        else:  # buy
            call_low_action, call_high_action = "BUY", "SELL"
            put_low_action, put_high_action = "BUY", "SELL"
        
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
        
        leg_count = 4
        fees_total = leg_count * fee_per_leg
        
        # Remaining profit calculation differs by side
        if open_side == "buy":
            # Buy IC: remaining = width - cost - fees
            remaining_profit = width - total_mid_entry - fees_total
        else:
            # Sell IC: remaining = credit - width - fees
            remaining_profit = total_mid_entry - width - fees_total
        
        # Check structural validity
        if remaining_profit <= 0:
            return None
        
        remaining_percent = (remaining_profit / width) * 100
        break_even_days = compute_bed(remaining_profit, width)
        
        # Structural pass
        if open_side == "buy":
            structural_pass = total_mid_entry < width
        else:
            structural_pass = total_mid_entry > width
        
        # Net credit: negative for debit (buy), positive for credit (sell)
        net_credit = -total_mid_entry if open_side == "buy" else total_mid_entry
        
        # Strikes used
        strikes_used = sorted(set([call_low.strike, call_high.strike, put_low.strike, put_high.strike]))
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
            total_quantity=4,
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
            net_credit=net_credit,
            fee_per_leg=fee_per_leg,
            fees_total=fees_total,
            remaining_profit=remaining_profit,
            remaining_percent=remaining_percent,
            break_even_days=break_even_days,
            annual_return_percent=annual_return,
            bed_filter_pass=False,
            liquidity_pass=True,
            liquidity_detail="basic_check_pass",
            structural_pass=structural_pass,
            rank_score=0.0,
            computed_at=datetime.utcnow().isoformat()
        )
        
        return candidate
    
    def _scan_imbalanced_ic(
        self,
        chain_data: ChainData,
        dte: int,
        fee_per_leg: float,
        spread_cap_bound: float,
        call_low,
        call_high,
        put_low,
        put_high,
        width: float,
        max_total_legs: int
    ) -> List[StrategyCandidate]:
        """
        Generate imbalanced IC candidates for this strike pair.
        Per doc page 9: buy_notional >= sell_notional.
        """
        candidates = []
        
        # Generate imbalanced quantity combos
        imbal_combos = self.generate_imbalanced_quantities(
            max_total_legs=max_total_legs,
            max_ratio=3
        )
        
        for buy_qty, sell_qty in imbal_combos:
            # Try BUY imbalanced IC
            buy_candidate = self._build_imbalanced_ic(
                chain_data, dte, "buy", "IC_BUY_IMBAL",
                call_low, call_high, put_low, put_high,
                width, buy_qty, sell_qty, fee_per_leg, spread_cap_bound
            )
            if buy_candidate:
                candidates.append(buy_candidate)
            
            # Try SELL imbalanced IC
            sell_candidate = self._build_imbalanced_ic(
                chain_data, dte, "sell", "IC_SELL_IMBAL",
                call_low, call_high, put_low, put_high,
                width, buy_qty, sell_qty, fee_per_leg, spread_cap_bound
            )
            if sell_candidate:
                candidates.append(sell_candidate)
        
        return candidates
    
    def _build_imbalanced_ic(
        self,
        chain_data: ChainData,
        dte: int,
        open_side: str,
        strategy_type: str,
        call_low,
        call_high,
        put_low,
        put_high,
        width: float,
        buy_qty: int,
        sell_qty: int,
        fee_per_leg: float,
        spread_cap_bound: float
    ) -> Optional[StrategyCandidate]:
        """
        Build imbalanced IC candidate.
        Doc page 9: buy_notional >= sell_notional, BED uses buy side width.
        """
        # For imbalanced IC: buy_qty applies to long legs, sell_qty to short legs
        if open_side == "buy":
            call_low_action, call_low_qty = "BUY", buy_qty
            call_high_action, call_high_qty = "SELL", sell_qty
            put_low_action, put_low_qty = "BUY", buy_qty
            put_high_action, put_high_qty = "SELL", sell_qty
        else:  # sell
            call_low_action, call_low_qty = "SELL", buy_qty
            call_high_action, call_high_qty = "BUY", sell_qty
            put_low_action, put_low_qty = "SELL", buy_qty
            put_high_action, put_high_qty = "BUY", sell_qty
        
        # Build legs
        legs = [
            Leg(
                leg_index=1,
                strike=call_low.strike,
                right="C",
                open_action=call_low_action,
                quantity=call_low_qty,
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
                quantity=call_high_qty,
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
                quantity=put_low_qty,
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
                quantity=put_high_qty,
                bid=put_high.bid,
                ask=put_high.ask,
                mid=put_high.mid,
                volume=put_high.volume,
                open_interest=put_high.open_interest
            )
        ]
        
        # Calculate total cost/credit with quantities
        call_spread_raw = call_low.mid - call_high.mid
        call_spread_capped = apply_spread_cap(call_spread_raw, width, spread_cap_bound)
        put_spread_raw = put_low.mid - put_high.mid
        put_spread_capped = apply_spread_cap(put_spread_raw, width, spread_cap_bound)
        
        # Total with quantities - cost per unit * net quantity
        net_call_qty = buy_qty - sell_qty
        net_put_qty = buy_qty - sell_qty
        total_mid_entry = call_spread_capped * net_call_qty + put_spread_capped * net_put_qty
        
        # Notional dominance check (doc page 9)
        buy_notional = buy_qty * width
        sell_notional = sell_qty * width
        
        if buy_notional < sell_notional:
            return None  # INVALID: sell side larger
        
        # Total legs and fees
        total_quantity = call_low_qty + call_high_qty + put_low_qty + put_high_qty
        leg_count = 4  # Still 4 legs, just different quantities
        fees_total = total_quantity * fee_per_leg
        
        # Remaining profit (uses buy side width per doc page 9)
        if open_side == "buy":
            remaining_profit = buy_notional - abs(total_mid_entry) - fees_total
        else:
            remaining_profit = abs(total_mid_entry) - buy_notional - fees_total
        
        if remaining_profit <= 0:
            return None
        
        break_even_days = compute_bed(remaining_profit, buy_notional)
        
        # Net credit
        net_credit = -total_mid_entry if open_side == "buy" else total_mid_entry
        
        strikes_used = sorted(set([call_low.strike, call_high.strike, put_low.strike, put_high.strike]))
        annual_return = compute_annual_return(remaining_profit, buy_notional, dte)
        
        candidate = StrategyCandidate(
            strategy_type=strategy_type,
            symbol=chain_data.symbol,
            expiration=chain_data.expirations[0],
            dte=dte,
            open_side=open_side,
            is_imbalanced=True,
            legs=legs,
            leg_count=leg_count,
            strike_difference=width,
            strikes_used=strikes_used,
            buy_notional=buy_notional,
            sell_notional=sell_notional,
            total_quantity=total_quantity,
            raw_spreads={
                "call_spread": call_spread_raw,
                "put_spread": put_spread_raw,
                "buy_qty": buy_qty,
                "sell_qty": sell_qty
            },
            capped_spreads={
                "call_spread": call_spread_capped,
                "put_spread": put_spread_capped,
                "total": total_mid_entry
            },
            mid_entry=total_mid_entry,
            spread_cost=total_mid_entry,
            net_credit=net_credit,
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
