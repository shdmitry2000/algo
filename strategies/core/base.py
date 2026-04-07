"""
Abstract base class for all option strategies.

All strategies (IC, BF, Shifted, Flygonaal, Calendar) inherit from BaseStrategy.
"""
from abc import ABC, abstractmethod
from typing import List, Dict, Optional, Tuple
from .models import StrategyCandidate, ChainData


class BaseStrategy(ABC):
    """
    Abstract base class for all strategy scanners.
    
    Each strategy implements scan() to generate candidates across the option chain.
    Provides common utility methods for liquidity checks, imbalanced quantities, etc.
    """
    
    @property
    @abstractmethod
    def strategy_type(self) -> str:
        """
        Return strategy type identifier.
        
        Examples: "IC", "BF", "SHIFTED_IC", "FLYGONAAL", "CALENDAR"
        """
        pass
    
    @abstractmethod
    def scan(
        self,
        chain_data: ChainData,
        dte: int,
        fee_per_leg: float,
        spread_cap_bound: float = 0.01,
        **kwargs
    ) -> List[StrategyCandidate]:
        """
        Scan option chain and generate strategy candidates.
        
        Args:
            chain_data: Unified chain data (supports single or multi-expiration)
            dte: Days to expiration (primary expiration)
            fee_per_leg: Commission per contract
            spread_cap_bound: Spread cap bound (default 0.01)
            **kwargs: Strategy-specific parameters
        
        Returns:
            List of StrategyCandidate objects (not yet filtered by BED or other criteria)
        """
        pass
    
    def validate(self, candidate: StrategyCandidate) -> bool:
        """
        Validate strategy structural integrity.
        
        Override in subclass for strategy-specific validation.
        
        Args:
            candidate: Strategy candidate to validate
        
        Returns:
            True if valid, False otherwise
        """
        # Basic validation: must have legs, positive fees, etc.
        if not candidate.legs:
            return False
        if candidate.fees_total < 0:
            return False
        return True
    
    def check_liquidity_basic(
        self,
        ticks: List,
        min_bid: float = 0.0,
        min_ask: float = 0.0
    ) -> bool:
        """
        Basic liquidity check: all ticks must have bid > min_bid and ask > min_ask.
        
        Args:
            ticks: List of StandardOptionTick objects
            min_bid: Minimum bid price
            min_ask: Minimum ask price
        
        Returns:
            True if all ticks pass liquidity check
        """
        for tick in ticks:
            if tick.bid <= min_bid or tick.ask <= min_ask:
                return False
        return True
    
    def generate_imbalanced_quantities(
        self,
        max_total_legs: int = 10,
        max_ratio: int = 4
    ) -> List[Tuple[int, int]]:
        """
        Generate valid imbalanced quantity combinations.
        
        Per documentation: buy_notional >= sell_notional.
        
        Args:
            max_total_legs: Maximum total legs (buy + sell)
            max_ratio: Maximum ratio between buy and sell qty
        
        Returns:
            List of (buy_qty, sell_qty) tuples where buy_qty > sell_qty
        
        Examples:
            [(2, 1), (3, 1), (3, 2), (4, 1), (4, 2), (4, 3), ...]
        """
        combos = []
        
        # Generate combinations where buy_qty > sell_qty
        for buy_qty in range(2, max_total_legs):  # Start at 2 (1x1 is standard)
            for sell_qty in range(1, buy_qty):
                # Check total legs
                if buy_qty + sell_qty > max_total_legs:
                    continue
                
                # Check ratio (avoid extreme imbalances like 10x1)
                if buy_qty / sell_qty > max_ratio:
                    continue
                
                # Buy must dominate (already guaranteed by buy_qty > sell_qty)
                combos.append((buy_qty, sell_qty))
        
        return combos
