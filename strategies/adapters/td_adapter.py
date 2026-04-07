"""
TD Ameritrade adapter - Convert TD API responses to unified ChainData.

This adapter bridges the gap between strategies/estimators/ (ZerroLoss pattern)
and the new unified strategy library.
"""
from typing import List, Dict, Any
from strategies.core.models import ChainData
from datagathering.models import StandardOptionTick


def convert_td_response_to_chain_data(symbol: str, td_market_data: Dict[str, Any]) -> ChainData:
    """
    Convert TD Ameritrade API response to unified ChainData.
    
    Args:
        symbol: Stock symbol
        td_market_data: Raw TD API response with callExpDateMap and putExpDateMap
    
    Returns:
        ChainData instance
    """
    ticks: List[StandardOptionTick] = []
    expirations = set()
    
    # Extract calls
    if 'callExpDateMap' in td_market_data:
        for expiration_key, strikes_dict in td_market_data['callExpDateMap'].items():
            # Extract just the date part (format: "2026-04-30:32")
            expiration = expiration_key.split(':')[0]
            expirations.add(expiration)
            
            for strike_key, option_list in strikes_dict.items():
                for option_data in option_list:
                    # Convert TD option to StandardOptionTick
                    tick = _td_option_to_tick(option_data, expiration)
                    if tick:
                        ticks.append(tick)
    
    # Extract puts
    if 'putExpDateMap' in td_market_data:
        for expiration_key, strikes_dict in td_market_data['putExpDateMap'].items():
            expiration = expiration_key.split(':')[0]
            expirations.add(expiration)
            
            for strike_key, option_list in strikes_dict.items():
                for option_data in option_list:
                    tick = _td_option_to_tick(option_data, expiration)
                    if tick:
                        ticks.append(tick)
    
    # Get spot price from underlying data if available
    spot_price = 0.0
    if 'underlying' in td_market_data:
        spot_price = td_market_data['underlying'].get('last', 0.0)
    
    return ChainData(
        symbol=symbol,
        spot_price=spot_price,
        expirations=sorted(expirations),
        ticks=ticks
    )


def _td_option_to_tick(option_data: Dict[str, Any], expiration: str) -> StandardOptionTick:
    """
    Convert single TD option data to StandardOptionTick.
    
    Args:
        option_data: TD option data dict
        expiration: Expiration date string
    
    Returns:
        StandardOptionTick or None if invalid
    """
    try:
        return StandardOptionTick(
            root=option_data.get('symbol', '').split('_')[0],  # Extract root from OCC symbol
            expiration=expiration,
            strike=option_data.get('strikePrice', 0.0),
            right=option_data.get('putCall', 'C'),
            bid=option_data.get('bid', 0.0),
            ask=option_data.get('ask', 0.0),
            mid=option_data.get('mark', 0.0),
            volume=option_data.get('totalVolume', 0),
            open_interest=option_data.get('openInterest', 0),
            timestamp=option_data.get('quoteTimeInLong', ''),
            provider="td_ameritrade"
        )
    except (KeyError, ValueError) as e:
        # Log error and return None for invalid data
        return None
