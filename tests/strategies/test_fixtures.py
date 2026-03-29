"""
Shared fixtures and test data for strategy tests.
Uses hardcoded, predictable option chain data designed to generate ALL strategy types.
"""
import sys
sys.path.insert(0, '/Users/dmitrysh/code/algotrade/algo')

from typing import List
from datagathering.models import StandardOptionTick


# TEST CHAIN 1: Standard pricing for BUY strategies
TEST_CHAIN_BUY = {
    "symbol": "TEST_BUY",
    "expiration": "2026-04-30",
    "spot_price": 100.0,
    "ticks": [
        # Strike 80
        {"root": "TEST_BUY", "expiration": "2026-04-30", "strike": 80.0, "right": "C",
         "bid": 21.50, "ask": 22.50, "mid": 22.00, "volume": 50, "open_interest": 500,
         "timestamp": "2026-03-29T00:00:00", "provider": "test"},
        {"root": "TEST_BUY", "expiration": "2026-04-30", "strike": 80.0, "right": "P",
         "bid": 0.05, "ask": 0.15, "mid": 0.10, "volume": 50, "open_interest": 500,
         "timestamp": "2026-03-29T00:00:00", "provider": "test"},
        
        # Strike 85
        {"root": "TEST_BUY", "expiration": "2026-04-30", "strike": 85.0, "right": "C",
         "bid": 16.80, "ask": 17.20, "mid": 17.00, "volume": 80, "open_interest": 800,
         "timestamp": "2026-03-29T00:00:00", "provider": "test"},
        {"root": "TEST_BUY", "expiration": "2026-04-30", "strike": 85.0, "right": "P",
         "bid": 0.18, "ask": 0.22, "mid": 0.20, "volume": 80, "open_interest": 800,
         "timestamp": "2026-03-29T00:00:00", "provider": "test"},
        
        # Strike 90
        {"root": "TEST_BUY", "expiration": "2026-04-30", "strike": 90.0, "right": "C",
         "bid": 11.80, "ask": 12.20, "mid": 12.00, "volume": 100, "open_interest": 1000,
         "timestamp": "2026-03-29T00:00:00", "provider": "test"},
        {"root": "TEST_BUY", "expiration": "2026-04-30", "strike": 90.0, "right": "P",
         "bid": 0.45, "ask": 0.55, "mid": 0.50, "volume": 100, "open_interest": 1000,
         "timestamp": "2026-03-29T00:00:00", "provider": "test"},
        
        # Strike 95
        {"root": "TEST_BUY", "expiration": "2026-04-30", "strike": 95.0, "right": "C",
         "bid": 7.50, "ask": 8.50, "mid": 8.00, "volume": 150, "open_interest": 1500,
         "timestamp": "2026-03-29T00:00:00", "provider": "test"},
        {"root": "TEST_BUY", "expiration": "2026-04-30", "strike": 95.0, "right": "P",
         "bid": 1.40, "ask": 1.60, "mid": 1.50, "volume": 150, "open_interest": 1500,
         "timestamp": "2026-03-29T00:00:00", "provider": "test"},
        
        # Strike 100 (ATM)
        {"root": "TEST_BUY", "expiration": "2026-04-30", "strike": 100.0, "right": "C",
         "bid": 5.40, "ask": 6.60, "mid": 6.00, "volume": 500, "open_interest": 5000,
         "timestamp": "2026-03-29T00:00:00", "provider": "test"},
        {"root": "TEST_BUY", "expiration": "2026-04-30", "strike": 100.0, "right": "P",
         "bid": 5.40, "ask": 6.60, "mid": 6.00, "volume": 500, "open_interest": 5000,
         "timestamp": "2026-03-29T00:00:00", "provider": "test"},
        
        # Strike 105
        {"root": "TEST_BUY", "expiration": "2026-04-30", "strike": 105.0, "right": "C",
         "bid": 1.40, "ask": 1.60, "mid": 1.50, "volume": 200, "open_interest": 2000,
         "timestamp": "2026-03-29T00:00:00", "provider": "test"},
        {"root": "TEST_BUY", "expiration": "2026-04-30", "strike": 105.0, "right": "P",
         "bid": 7.50, "ask": 8.50, "mid": 8.00, "volume": 200, "open_interest": 2000,
         "timestamp": "2026-03-29T00:00:00", "provider": "test"},
        
        # Strike 110
        {"root": "TEST_BUY", "expiration": "2026-04-30", "strike": 110.0, "right": "C",
         "bid": 0.45, "ask": 0.55, "mid": 0.50, "volume": 100, "open_interest": 1000,
         "timestamp": "2026-03-29T00:00:00", "provider": "test"},
        {"root": "TEST_BUY", "expiration": "2026-04-30", "strike": 110.0, "right": "P",
         "bid": 11.80, "ask": 12.20, "mid": 12.00, "volume": 100, "open_interest": 1000,
         "timestamp": "2026-03-29T00:00:00", "provider": "test"},
        
        # Strike 115
        {"root": "TEST_BUY", "expiration": "2026-04-30", "strike": 115.0, "right": "C",
         "bid": 0.18, "ask": 0.22, "mid": 0.20, "volume": 50, "open_interest": 500,
         "timestamp": "2026-03-29T00:00:00", "provider": "test"},
        {"root": "TEST_BUY", "expiration": "2026-04-30", "strike": 115.0, "right": "P",
         "bid": 16.80, "ask": 17.20, "mid": 17.00, "volume": 50, "open_interest": 500,
         "timestamp": "2026-03-29T00:00:00", "provider": "test"},
        
        # Strike 120
        {"root": "TEST_BUY", "expiration": "2026-04-30", "strike": 120.0, "right": "C",
         "bid": 0.05, "ask": 0.15, "mid": 0.10, "volume": 25, "open_interest": 250,
         "timestamp": "2026-03-29T00:00:00", "provider": "test"},
        {"root": "TEST_BUY", "expiration": "2026-04-30", "strike": 120.0, "right": "P",
         "bid": 21.50, "ask": 22.50, "mid": 22.00, "volume": 25, "open_interest": 250,
         "timestamp": "2026-03-29T00:00:00", "provider": "test"},
        
        # Strike 125
        {"root": "TEST_BUY", "expiration": "2026-04-30", "strike": 125.0, "right": "C",
         "bid": 0.01, "ask": 0.05, "mid": 0.03, "volume": 10, "open_interest": 100,
         "timestamp": "2026-03-29T00:00:00", "provider": "test"},
        {"root": "TEST_BUY", "expiration": "2026-04-30", "strike": 125.0, "right": "P",
         "bid": 26.50, "ask": 27.50, "mid": 27.00, "volume": 10, "open_interest": 100,
         "timestamp": "2026-03-29T00:00:00", "provider": "test"},
        
        # Strike 130
        {"root": "TEST_BUY", "expiration": "2026-04-30", "strike": 130.0, "right": "C",
         "bid": 0.00, "ask": 0.02, "mid": 0.01, "volume": 5, "open_interest": 50,
         "timestamp": "2026-03-29T00:00:00", "provider": "test"},
        {"root": "TEST_BUY", "expiration": "2026-04-30", "strike": 130.0, "right": "P",
         "bid": 31.50, "ask": 32.50, "mid": 32.00, "volume": 5, "open_interest": 50,
         "timestamp": "2026-03-29T00:00:00", "provider": "test"},
    ]
}


# TEST CHAIN 2: MISPRICED options for SELL strategies
# Pricing designed to create credit > max_loss for SELL strategies
TEST_CHAIN_SELL = {
    "symbol": "TEST_SELL",
    "expiration": "2026-04-30",
    "spot_price": 100.0,
    "ticks": [
        # Strike 85
        {"root": "TEST_SELL", "expiration": "2026-04-30", "strike": 85.0, "right": "C",
         "bid": 16.00, "ask": 17.00, "mid": 16.50, "volume": 100, "open_interest": 1000,
         "timestamp": "2026-03-29T00:00:00", "provider": "test"},
        {"root": "TEST_SELL", "expiration": "2026-04-30", "strike": 85.0, "right": "P",
         "bid": 0.40, "ask": 0.60, "mid": 0.50, "volume": 100, "open_interest": 1000,
         "timestamp": "2026-03-29T00:00:00", "provider": "test"},
        
        # Strike 90
        {"root": "TEST_SELL", "expiration": "2026-04-30", "strike": 90.0, "right": "C",
         "bid": 12.50, "ask": 13.50, "mid": 13.00, "volume": 150, "open_interest": 1500,
         "timestamp": "2026-03-29T00:00:00", "provider": "test"},
        {"root": "TEST_SELL", "expiration": "2026-04-30", "strike": 90.0, "right": "P",
         "bid": 0.70, "ask": 0.90, "mid": 0.80, "volume": 150, "open_interest": 1500,
         "timestamp": "2026-03-29T00:00:00", "provider": "test"},
        
        # Strike 95 - BOTH C and P EXPENSIVE (violates parity, creates IC_SELL)
        {"root": "TEST_SELL", "expiration": "2026-04-30", "strike": 95.0, "right": "C",
         "bid": 11.00, "ask": 12.00, "mid": 11.50, "volume": 200, "open_interest": 2000,
         "timestamp": "2026-03-29T00:00:00", "provider": "test"},
        {"root": "TEST_SELL", "expiration": "2026-04-30", "strike": 95.0, "right": "P",
         "bid": 11.00, "ask": 12.00, "mid": 11.50, "volume": 200, "open_interest": 2000,
         "timestamp": "2026-03-29T00:00:00", "provider": "test"},
        
        # Strike 100 (ATM) - CHEAP (for BF SELL, buy 2x)
        {"root": "TEST_SELL", "expiration": "2026-04-30", "strike": 100.0, "right": "C",
         "bid": 1.40, "ask": 1.60, "mid": 1.50, "volume": 500, "open_interest": 5000,
         "timestamp": "2026-03-29T00:00:00", "provider": "test"},
        {"root": "TEST_SELL", "expiration": "2026-04-30", "strike": 100.0, "right": "P",
         "bid": 1.40, "ask": 1.60, "mid": 1.50, "volume": 500, "open_interest": 5000,
         "timestamp": "2026-03-29T00:00:00", "provider": "test"},
        
        # Strike 105 - BOTH C and P CHEAP (violates parity, creates IC_SELL)
        {"root": "TEST_SELL", "expiration": "2026-04-30", "strike": 105.0, "right": "C",
         "bid": 0.40, "ask": 0.60, "mid": 0.50, "volume": 200, "open_interest": 2000,
         "timestamp": "2026-03-29T00:00:00", "provider": "test"},
        {"root": "TEST_SELL", "expiration": "2026-04-30", "strike": 105.0, "right": "P",
         "bid": 0.40, "ask": 0.60, "mid": 0.50, "volume": 200, "open_interest": 2000,
         "timestamp": "2026-03-29T00:00:00", "provider": "test"},
        
        # Strike 110
        {"root": "TEST_SELL", "expiration": "2026-04-30", "strike": 110.0, "right": "C",
         "bid": 0.70, "ask": 0.90, "mid": 0.80, "volume": 150, "open_interest": 1500,
         "timestamp": "2026-03-29T00:00:00", "provider": "test"},
        {"root": "TEST_SELL", "expiration": "2026-04-30", "strike": 110.0, "right": "P",
         "bid": 12.50, "ask": 13.50, "mid": 13.00, "volume": 150, "open_interest": 1500,
         "timestamp": "2026-03-29T00:00:00", "provider": "test"},
        
        # Strike 115
        {"root": "TEST_SELL", "expiration": "2026-04-30", "strike": 115.0, "right": "C",
         "bid": 0.40, "ask": 0.60, "mid": 0.50, "volume": 100, "open_interest": 1000,
         "timestamp": "2026-03-29T00:00:00", "provider": "test"},
        {"root": "TEST_SELL", "expiration": "2026-04-30", "strike": 115.0, "right": "P",
         "bid": 16.00, "ask": 17.00, "mid": 16.50, "volume": 100, "open_interest": 1000,
         "timestamp": "2026-03-29T00:00:00", "provider": "test"},
    ]
}

# Verified calculation for IC_SELL at 95/105 in TEST_CHAIN_SELL:
# IC_SELL legs: SELL 95C, BUY 105C, SELL 105P, BUY 95P
# Call spread: 95C ($11.50) - 105C ($0.50) = $11.00
# Put spread: 105P ($11.50) - 95P ($1.00) = $10.50
# Total mid entry: $11.00 + $10.50 = $21.50
# For IC_SELL, remaining = total_mid_entry - width - fees
#                        = $21.50 - $10.00 - $2.60 = $8.90 > 0 ✅
#
# BF_SELL at 95/100/105 in TEST_CHAIN_SELL (calls):
# SELL BF legs: SELL 95C, BUY 2x 100C, SELL 105C
# Lower spread: 95C ($11.50) - 100C ($7.50) = $4.00
# Upper spread: 100C ($7.50) - 105C ($0.50) = $7.00
# Net: $4.00 - $7.00 = -$3.00 (receive credit)
# Remaining: abs($3.00) - fees = $3.00 - $2.60 = $0.40 > 0 ✅


def get_test_chain(chain_type: str = "buy") -> tuple[List[StandardOptionTick], str]:
    """
    Get hardcoded test option chain.
    
    Args:
        chain_type: "buy" for BUY strategies, "sell" for SELL strategies
    
    Returns:
        (ticks, expiration) tuple
    """
    data = TEST_CHAIN_SELL if chain_type == "sell" else TEST_CHAIN_BUY
    ticks = []
    
    for tick_data in data["ticks"]:
        ticks.append(StandardOptionTick(**tick_data))
    
    return ticks, data["expiration"]


def get_test_dte() -> int:
    """Get DTE for test chain (hardcoded)."""
    return 32  # ~1 month


# Expected results for the hardcoded test chains
EXPECTED_RESULTS = {
    "buy_chain": {
        "symbol": "TEST_BUY",
        "expiration": "2026-04-30",
        "dte": 32,
        "num_strikes": 11,
        "spot_price": 100.0,
        
        "ic_buy_example": {
            "strikes": [95.0, 105.0],
            "width": 10.0,
            "description": "BUY IC: Standard arbitrage"
        },
        
        "bf_buy_example": {
            "strikes": [95.0, 100.0, 105.0],
            "width": 5.0,
            "description": "BUY BF: Butterfly centered at 100"
        },
        
        "min_candidates": {
            "IC_BUY": 3,
            "BF_BUY": 1,
            "SHIFTED_IC_BUY": 5,
            "IC_BUY_IMBAL": 5,
        }
    },
    
    "sell_chain": {
        "symbol": "TEST_SELL",
        "expiration": "2026-04-30",
        "dte": 32,
        "num_strikes": 7,
        "spot_price": 100.0,
        
        "ic_sell_example": {
            "strikes": [95.0, 105.0],
            "width": 10.0,
            "description": "SELL IC: Inner strikes overpriced, outer underpriced"
        },
        
        "bf_sell_example": {
            "strikes": [95.0, 100.0, 105.0],
            "width": 5.0,
            "description": "SELL BF: Upper spread wider than lower"
        },
        
        "min_candidates": {
            "IC_SELL": 1,
            "BF_SELL": 1,
            "SHIFTED_IC_SELL": 1,
        }
    }
}
