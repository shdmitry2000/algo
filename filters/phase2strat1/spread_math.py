"""
Spread cap math, annual return calculations, and shared utilities.
"""


def apply_spread_cap(raw_spread: float, strike_diff: float, bound: float = 0.01) -> float:
    """
    Cap spread to prevent zero or exceeding strike width, while preserving sign.
    
    For POSITIVE spreads: cap to [bound, width - bound]
    For NEGATIVE spreads: cap to [-(width - bound), -bound]
    
    This ensures:
    - Spreads never exactly equal ±width (leaves room for profit)
    - Spreads are never exactly zero (minimum magnitude)
    - Sign is preserved (negative spreads stay negative)
    
    Args:
        raw_spread: Uncapped spread value (can be positive or negative)
        strike_diff: Strike difference (width)
        bound: Minimum magnitude from zero and from width (default 0.01)
    
    Returns:
        Capped spread value with sign preserved
    
    Examples:
        >>> apply_spread_cap(11.0, 10.0, 0.01)  # Positive spread
        9.99
        >>> apply_spread_cap(-11.0, 10.0, 0.01)  # Negative spread
        -9.99
        >>> apply_spread_cap(0.005, 10.0, 0.01)  # Too small positive
        0.01
        >>> apply_spread_cap(-0.005, 10.0, 0.01)  # Too small negative
        -0.01
    """
    if raw_spread >= 0:
        # Positive spread: cap to [bound, width - bound]
        return max(bound, min(raw_spread, strike_diff - bound))
    else:
        # Negative spread: cap to [-(width - bound), -bound]
        return min(-bound, max(raw_spread, -(strike_diff - bound)))


def compute_bed(remaining_profit: float, strike_width: float) -> float:
    """
    Compute Break-Even Days.
    
    Formula: BED = 365 * (remaining% / 100) = 365 * (remaining$ / width$)
    
    Args:
        remaining_profit: Remaining profit after costs
        strike_width: Strike width (difference)
    
    Returns:
        Break-even days (BED)
    
    Examples:
        >>> compute_bed(3.65, 10.0)
        133.225
        >>> compute_bed(10.0, 10.0)
        365.0
    """
    if strike_width <= 0:
        return float('inf')
    remaining_percent = (remaining_profit / strike_width) * 100
    return (365 / 100) * remaining_percent


def compute_annual_return(remaining_profit: float, strike_width: float, dte: int) -> float:
    """
    Calculate annualized return percentage.
    
    Formula:
      remaining% = (remaining_profit / strike_width) * 100
      annual_return% = (remaining% / dte) * 365
    
    Or simplified:
      annual_return% = (remaining_profit / strike_width) * (365 / dte) * 100
    
    Relationship to BED:
      annual_return% = (BED / DTE) * 100
    
    Args:
        remaining_profit: Remaining profit after costs
        strike_width: Strike width (difference)
        dte: Days to expiration
    
    Returns:
        Annualized return percentage
    
    Examples:
        >>> compute_annual_return(3.65, 10.0, 32)
        416.33
        >>> compute_annual_return(10.0, 10.0, 365)
        100.0
        >>> compute_annual_return(10.0, 10.0, 100)
        365.0
    
    For >100% annual return:
      annual_return% > 100
      remaining% > (100 * dte) / 365
    
    For DTE=32: need remaining% > 8.77% (>$0.88 on $10 width)
    For DTE=10: need remaining% > 2.74% (>$0.27 on $10 width)
    """
    if strike_width <= 0 or dte <= 0:
        return 0.0
    
    remaining_percent = (remaining_profit / strike_width) * 100
    annual_return = (remaining_percent / dte) * 365
    
    return annual_return


def compute_max_entry_cost(
    strike_width: float,
    dte: int,
    target_annual_return: float,
    fees_total: float
) -> float:
    """
    Calculate maximum entry cost to achieve target annual return.
    
    Formula:
      For target annual return: remaining% = (target * dte) / 365
      remaining$ = (remaining% / 100) * width
      max_cost = width - remaining$ - fees
    
    Args:
        strike_width: Strike width (difference)
        dte: Days to expiration
        target_annual_return: Target annual return percentage (e.g., 100 for 100%)
        fees_total: Total fees for all legs
    
    Returns:
        Maximum entry cost to achieve target return
    
    Examples:
        >>> compute_max_entry_cost(10.0, 32, 100, 2.6)
        6.52  # For 100% annual return on $10 width IC in 32 days
        >>> compute_max_entry_cost(10.0, 32, 200, 2.6)
        5.65  # For 200% annual return
    """
    if strike_width <= 0 or dte <= 0:
        return 0.0
    
    # Calculate minimum remaining profit for target return
    min_remaining_pct = (target_annual_return * dte) / 365
    min_remaining = (min_remaining_pct / 100) * strike_width
    
    # Max cost = width - min_remaining - fees
    max_cost = strike_width - min_remaining - fees_total
    
    return max_cost

