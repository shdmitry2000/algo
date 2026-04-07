"""
Filter adapter - Bridge between legacy ChainIndex and unified ChainData.

This adapter allows existing filter code (filters/phase2strat1/) to work
with the new unified strategy library without breaking changes.
"""
from typing import List
from strategies.core.models import ChainData
from datagathering.models import StandardOptionTick


def convert_chain_index_to_chain_data(chain_idx) -> ChainData:
    """
    Convert legacy ChainIndex to unified ChainData.
    
    Args:
        chain_idx: ChainIndex instance from filters/phase2strat1/chain_index.py
    
    Returns:
        ChainData instance compatible with new unified strategies
    """
    # Extract all ticks from ChainIndex
    ticks: List[StandardOptionTick] = []
    
    # Get all strikes
    strikes = chain_idx.sorted_strikes()
    
    # Collect all calls and puts
    for strike in strikes:
        call_tick = chain_idx.get_call(strike)
        if call_tick:
            ticks.append(call_tick)
        
        put_tick = chain_idx.get_put(strike)
        if put_tick:
            ticks.append(put_tick)
    
    # Create ChainData
    return ChainData(
        symbol=chain_idx.symbol,
        spot_price=chain_idx.spot_price if hasattr(chain_idx, 'spot_price') else 0.0,
        expirations=[chain_idx.expiration],
        ticks=ticks
    )


def convert_chain_data_to_chain_index(chain_data: ChainData):
    """
    Convert unified ChainData back to legacy ChainIndex (if needed).
    
    Args:
        chain_data: ChainData instance
    
    Returns:
        ChainIndex instance (requires importing ChainIndex)
    """
    from filters.phase2strat1.chain_index import ChainIndex
    
    # ChainIndex expects (symbol, expiration, ticks)
    return ChainIndex(
        symbol=chain_data.symbol,
        expiration=chain_data.expirations[0],
        ticks=chain_data.ticks
    )
