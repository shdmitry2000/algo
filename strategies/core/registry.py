"""
Strategy type registry.

Maintains central registry of all strategy types and their implementations.
"""
from typing import Dict, Type, Optional


# Strategy type identifiers
# Format: STRATEGY_SIDE[_IMBAL]
# Examples: IC_BUY, FLYGONAAL_SELL_IMBAL, CALENDAR_BUY_C
STRATEGY_TYPES = {
    # Iron Condor (IC) - Same strikes for call and put spreads
    "IC_BUY": "Iron Condor (Buy)",
    "IC_SELL": "Iron Condor (Sell)",
    "IC_BUY_IMBAL": "Iron Condor (Buy Imbalanced)",
    "IC_SELL_IMBAL": "Iron Condor (Sell Imbalanced)",
    
    # Butterfly (BF) - 3 strikes, middle has 2x quantity
    "BF_BUY": "Butterfly (Buy)",
    "BF_SELL": "Butterfly (Sell)",
    "BF_BUY_IMBAL": "Butterfly (Buy Imbalanced)",
    "BF_SELL_IMBAL": "Butterfly (Sell Imbalanced)",
    
    # Condor - 4 distinct strikes, 1x quantity each
    "CONDOR_BUY": "Condor (Buy)",
    "CONDOR_SELL": "Condor (Sell)",
    "CONDOR_BUY_IMBAL": "Condor (Buy Imbalanced)",
    "CONDOR_SELL_IMBAL": "Condor (Sell Imbalanced)",
    
    # Shifted Iron Condor - Different strikes for call/put spreads  
    "SHIFTED_IC_BUY": "Shifted Iron Condor (Buy)",
    "SHIFTED_IC_SELL": "Shifted Iron Condor (Sell)",
    "SHIFTED_IC_BUY_IMBAL": "Shifted Iron Condor (Buy Imbalanced)",
    "SHIFTED_IC_SELL_IMBAL": "Shifted Iron Condor (Sell Imbalanced)",
    
    # Flygonaal (3:2:2:3 wing configuration)
    "FLYGONAAL_BUY": "Flygonaal (3:2:2:3 Buy)",
    "FLYGONAAL_SELL": "Flygonaal (3:2:2:3 Sell)",
    "FLYGONAAL_BUY_IMBAL": "Flygonaal (Buy Imbalanced)",
    "FLYGONAAL_SELL_IMBAL": "Flygonaal (Sell Imbalanced)",
    
    # Calendar Spreads (multi-expiration time spreads)
    "CALENDAR_BUY_C": "Calendar Spread (Buy Call)",
    "CALENDAR_BUY_P": "Calendar Spread (Buy Put)",
    "CALENDAR_SELL_C": "Calendar Spread (Sell Call)",
    "CALENDAR_SELL_P": "Calendar Spread (Sell Put)",
    
    # Diagonal Spreads (different strikes + different expirations)
    "DIAGONAL_BUY_C": "Diagonal Spread (Buy Call)",
    "DIAGONAL_BUY_P": "Diagonal Spread (Buy Put)",
    "DIAGONAL_SELL_C": "Diagonal Spread (Sell Call)",
    "DIAGONAL_SELL_P": "Diagonal Spread (Sell Put)",
}


# Strategy class registry
# Maps strategy_type to implementation class
_STRATEGY_CLASSES: Dict[str, Type] = {}


def register_strategy(strategy_type: str):
    """
    Decorator to register a strategy implementation.
    
    Usage:
        @register_strategy("IC")
        class IronCondorStrategy(BaseStrategy):
            ...
    
    Args:
        strategy_type: Base strategy type identifier (without _BUY/_SELL suffix)
    """
    def decorator(cls):
        _STRATEGY_CLASSES[strategy_type] = cls
        return cls
    return decorator


def get_strategy_class(strategy_type: str) -> Optional[Type]:
    """
    Get strategy implementation class by type.
    
    Args:
        strategy_type: Strategy type identifier
    
    Returns:
        Strategy class or None if not found
    """
    # Try exact match first
    if strategy_type in _STRATEGY_CLASSES:
        return _STRATEGY_CLASSES[strategy_type]
    
    # Try base type (remove _BUY/_SELL/_IMBAL suffixes)
    base_type = strategy_type.split("_")[0]
    if "_IC_" in strategy_type:
        base_type = "SHIFTED_IC" if "SHIFTED" in strategy_type else "IC"
    elif "_BF_" in strategy_type:
        base_type = "SHIFTED_BF" if "SHIFTED" in strategy_type else "BF"
    
    return _STRATEGY_CLASSES.get(base_type)


def get_all_strategy_types() -> Dict[str, str]:
    """
    Get all registered strategy types.
    
    Returns:
        Dict mapping strategy type IDs to human-readable names
    """
    return STRATEGY_TYPES.copy()


def get_all_strategy_classes() -> Dict[str, Type]:
    """
    Get all registered strategy classes.
    
    Returns:
        Dict mapping strategy type IDs to implementation classes
    """
    return _STRATEGY_CLASSES.copy()
