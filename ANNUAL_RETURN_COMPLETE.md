# Annual Return Calculation - Implementation Complete

## Overview

Added comprehensive annual return calculations to the Phase 2 filter system. Every strategy candidate now includes `annual_return_percent` field, enabling filtering by time-adjusted profitability.

## Implementation

### 1. Utility Functions (`filters/phase2strat1/spread_math.py`)

Added three new utility functions:

```python
def compute_bed(remaining_profit: float, strike_width: float) -> float:
    """
    Break-Even Days = 365 * (remaining% / 100)
    """
    remaining_percent = (remaining_profit / strike_width) * 100
    return (365 / 100) * remaining_percent


def compute_annual_return(remaining_profit: float, strike_width: float, dte: int) -> float:
    """
    Annualized return% = (remaining% / dte) * 365
    Or: annual% = (BED / DTE) * 100
    """
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
    Calculate max entry cost to achieve target annual return.
    
    For 100% annual: max_cost = width - ((100*dte/365)/100)*width - fees
    """
    min_remaining_pct = (target_annual_return * dte) / 365
    min_remaining = (min_remaining_pct / 100) * strike_width
    max_cost = strike_width - min_remaining - fees_total
    return max_cost
```

### 2. StrategyCandidate Model (`filters/phase2strat1/strategies/base.py`)

Added new field:

```python
@dataclass
class StrategyCandidate:
    # ... existing fields ...
    remaining_profit: float
    remaining_percent: float
    break_even_days: float
    annual_return_percent: float  # NEW: Annualized return
```

### 3. Strategy Implementations

Updated all three strategy implementations to compute and include `annual_return_percent`:

**Iron Condor** (`iron_condor.py`):
- Both standard IC and imbalanced IC variants
- Computed during candidate creation

**Butterfly** (`butterfly.py`):
- Standard and shifted variants

**Shifted Condor** (`shifted_condor.py`):
- All shifted IC variants

Each strategy now calls:
```python
from filters.phase2strat1.spread_math import compute_annual_return
annual_return = compute_annual_return(remaining_profit, width, dte)

candidate = StrategyCandidate(
    # ... other fields ...
    annual_return_percent=annual_return,
    # ... rest of fields ...
)
```

## Formula Deep Dive

### Annual Return Calculation

```
remaining% = (remaining_profit / strike_width) * 100
annual_return% = (remaining% / dte) * 365

Simplified:
annual_return% = (remaining_profit / strike_width) * (365 / dte) * 100
```

### Relationship to BED

```
BED = 365 * (remaining% / 100)
annual_return% = (BED / DTE) * 100

Therefore:
• BED > DTE → >100% annual return
• BED = DTE → 100% annual return (breakeven)
• BED < DTE → <100% annual return
```

## Key Thresholds

### For >100% Annual Return

**DTE = 32 days (1 month)**:
- Need: `remaining% > 8.77%`
- For $10 width: `profit > $0.88`
- Max entry cost: `≤ $6.52` (4-leg IC with $2.60 fees)

**DTE = 10 days (short-term)**:
- Need: `remaining% > 2.74%`
- For $10 width: `profit > $0.27`
- Very achievable threshold

**DTE = 365 days (1 year)**:
- Need: `remaining% > 100%`
- For $10 width: `profit > $10.00`
- Full width as profit

### Max Entry Price Table

For DTE=32, width=$10, fees=$2.60 (4-leg IC):

| Target Annual% | Min Remaining% | Max Entry Cost |
|---------------|----------------|----------------|
| 100%          | 8.77%          | $6.52          |
| 150%          | 13.15%         | $6.08          |
| 200%          | 17.53%         | $5.65          |
| 300%          | 26.30%         | $4.77          |
| 500%          | 43.84%         | $3.02          |

## Test Results with Real Data

Using hardcoded `TEST_CHAIN_BUY` (DTE=32):

```
All 9 IC_BUY candidates have >100% annual return:

     Strikes   Width   Profit    BED    Annual%
      80/100 $  20.0 $   7.30  133.2    416.33%  🔥
      80/105 $  25.0 $   9.80  143.1    447.13%  🔥
      80/110 $  30.0 $  17.80  216.6    676.77%  🔥
      80/115 $  35.0 $  27.50  286.8    896.21%  🔥
      85/100 $  15.0 $   7.20  175.2    547.50%  🔥
      85/105 $  20.0 $   9.70  177.0    553.20%  🔥
      85/110 $  25.0 $  17.70  258.4    807.56%  🔥
      90/100 $  10.0 $   6.90  251.8    787.03%  🔥
      90/105 $  15.0 $   9.40  228.7    714.79%  🔥

Top opportunity: 80/115 with 896% annual return!
```

## Usage

### In Strategy Candidates

```python
candidate = ic_scanner.scan(chain_idx, dte=32, fee_per_leg=0.65)[0]

print(f"Strategy: {candidate.strategy_type}")
print(f"Profit: ${candidate.remaining_profit:.2f}")
print(f"Width: ${candidate.strike_difference:.2f}")
print(f"BED: {candidate.break_even_days:.1f} days")
print(f"Annual Return: {candidate.annual_return_percent:.1f}%")
```

Output:
```
Strategy: IC_BUY
Profit: $7.30
Width: $20.00
BED: 133.2 days
Annual Return: 416.3%
```

### In Signal JSON

The `annual_return_percent` field is automatically included when strategies are serialized:

```json
{
  "signal_id": "TEST-20260430-123",
  "strategies": {
    "IC_BUY": {
      "remaining_profit": 7.30,
      "remaining_percent": 36.5,
      "break_even_days": 133.2,
      "annual_return_percent": 416.33,
      "strike_difference": 20.0,
      ...
    }
  }
}
```

### Filtering by Annual Return

```python
# Filter candidates by annual return threshold
high_return = [
    c for c in candidates 
    if c.annual_return_percent > 200
]

# Sort by annual return
sorted_candidates = sorted(
    candidates, 
    key=lambda c: c.annual_return_percent, 
    reverse=True
)
```

## Test Coverage

### Test Suite: `test_annual_returns.py` (7 tests)

1. **Annual Return Calculation**: Verifies formula across various scenarios
   - 416% annual for 36.5% profit in 32 days ✅
   - 1,000% annual for 27.4% profit in 10 days ✅

2. **100% Threshold**: Calculates minimum profit needed for >100% annual
   - DTE=32: Need >8.77% remaining
   - DTE=10: Need >2.74% remaining

3. **Max Entry Price**: Determines max cost for target returns
   - 100% annual @ DTE=32: Pay ≤$6.52
   - 500% annual @ DTE=32: Pay ≤$3.02

4. **BED ↔ Annual Conversion**: Validates relationship
   - `annual% = (BED / DTE) * 100`
   - BED=100, DTE=32 → 312.5% annual ✅

5. **High Return Detection**: Finds strategies with >100% annual
   - All 9 IC_BUY candidates exceed 100%
   - Top: 896% annual return

6. **IC Parameters Saved**: Verifies `annual_return_percent` in dict
   - Field present in all candidates ✅
   - Correct value: 416.33% ✅

7. **Signal JSON Data**: Confirms Signal includes annual data
   - Available in strategies dict ✅
   - Can calculate from BED/DTE ✅
   - Ready for UI display ✅

## Benefits

### 1. Better Trade Selection
- Identify high-ROI opportunities quickly
- Filter by minimum annual return threshold
- Compare strategies on time-adjusted basis

### 2. Risk Management
- Set maximum entry prices for target returns
- Know exact profitability requirements
- Make informed capital allocation decisions

### 3. UI/History Display
- Show annual returns in signal history
- Sort by annual return
- Highlight >100% opportunities

### 4. Production Ready
- Field automatically included in all candidates
- Saved to cache with every signal
- Available in Signal JSON for API/UI

## Example Insights

### Short-term Opportunities (DTE < 30)
Even modest profits become exceptional annual returns:
- 10% profit in 10 days = 365% annual
- 20% profit in 20 days = 365% annual
- 9% profit in 32 days = 103% annual

### Practical Guidance

**For 200% annual return on $10 IC (DTE=32)**:
- Need: $1.75 remaining profit (17.5%)
- Max entry: $5.65
- With fees: $2.60
- Total width: $10.00

**For 500% annual return**:
- Need: $4.38 remaining profit (43.8%)
- Max entry: $3.02
- Much harder to find, but possible in volatile markets

## Files Modified

1. `filters/phase2strat1/spread_math.py`
   - Added `compute_bed()`
   - Added `compute_annual_return()`
   - Added `compute_max_entry_cost()`

2. `filters/phase2strat1/strategies/base.py`
   - Added `annual_return_percent` field to `StrategyCandidate`

3. `filters/phase2strat1/strategies/iron_condor.py`
   - Compute annual return for all IC candidates
   - Include in both standard and imbalanced variants

4. `filters/phase2strat1/strategies/butterfly.py`
   - Compute annual return for all BF candidates

5. `filters/phase2strat1/strategies/shifted_condor.py`
   - Compute annual return for all Shifted IC candidates

6. `tests/strategies/test_annual_returns.py`
   - 7 comprehensive tests
   - Validates formula, thresholds, and parameter saving

7. `tests/strategies/run_all_tests.py`
   - Integrated annual return test suite

## Status

✅ **COMPLETE**

- Annual return utility functions implemented
- All strategies compute and save annual_return_percent
- 7 comprehensive tests pass
- Documentation complete
- Ready for production use

## Next Steps (Optional Enhancements)

1. **UI Display**: Show annual return % in signal history table
2. **Filter Threshold**: Add configurable min annual return filter (e.g., only show >150% strategies)
3. **Sorting**: Allow sorting signals by annual return in UI
4. **Alerts**: Highlight exceptional opportunities (>500% annual)
5. **Analytics**: Track average annual returns over time
