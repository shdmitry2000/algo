"""
Adapter package - Bridges between legacy code and unified strategy library.

Provides adapters for:
- Filter pipeline (filters/phase2strat1/)
- TD Ameritrade data (strategies/estimators/)
"""

from .filter_adapter import (
    convert_chain_index_to_chain_data,
    convert_chain_data_to_chain_index,
)
from .td_adapter import (
    convert_td_response_to_chain_data,
)

__all__ = [
    # Filter adapter
    "convert_chain_index_to_chain_data",
    "convert_chain_data_to_chain_index",
    
    # TD adapter
    "convert_td_response_to_chain_data",
]
