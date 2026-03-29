# Phase 2 Strike Filtering Implementation

## Summary
Implemented **configurable** strike filtering to limit Phase 2 calculations to strikes around ATM, improving performance while keeping Phase 1 data gathering comprehensive.

## Configuration

Strike filtering is controlled via `.env` variables:

```bash
# Default: 25 ITM + 25 OTM = 50 total strikes (fast)
MAX_STRIKES_ITM=25
MAX_STRIKES_OTM=25

# For more comprehensive calculations (slower)
MAX_STRIKES_ITM=50
MAX_STRIKES_OTM=50

# For unlimited (calculate all strikes, slowest)
MAX_STRIKES_ITM=-1
MAX_STRIKES_OTM=-1
```

**How to Change:**
1. Edit `.env` file
2. Set `MAX_STRIKES_ITM` and `MAX_STRIKES_OTM` to desired values
3. Use `-1` for unlimited (no filtering)
4. Restart pipeline for changes to take effect

## Changes Made

### 1. `filters/phase2strat1/chain_index.py`
Added strike filtering logic to `ChainIndex`:

- **Configuration from .env:**
  - `MAX_STRIKES_ITM` - ITM strikes to keep (default: 25, -1 = unlimited)
  - `MAX_STRIKES_OTM` - OTM strikes to keep (default: 25, -1 = unlimited)
  - `_get_strike_limit()` helper to read env vars with defaults

- **New methods:**
  - `_estimate_atm_strike()` - Estimates ATM using put-call parity (finds strike where call and put prices are closest)
  - `_apply_strike_filter()` - Filters strikes to keep only N ITM + ATM + N OTM closest to estimated ATM

- **Behavior:**
  - Automatically applies when `ChainIndex` is constructed (if limits != -1)
  - Logs filtering results (e.g., "100 strikes -> 51 strikes")
  - All data remains in Redis cache; filtering only affects calculations

### 2. `.env` and `.env.example`
Added configuration with documentation:

```bash
# Phase 2 Strike Filtering (Performance Optimization)
# Limits Phase 2 calculations to N strikes around ATM
# Set to -1 for unlimited (calculate all strikes)
# Default: 25 ITM + 25 OTM = 50 total strikes
MAX_STRIKES_ITM=25
MAX_STRIKES_OTM=25
```

### 3. `config/settings.yaml`
Added comment referencing the `.env` configuration.

### 4. `tests/strategies/test_pipeline.py`
Added comprehensive test: `test_pipeline_strike_filtering()`

- Creates chain with 100 strikes
- Tests with filtering enabled (25/25)
- Tests with filtering disabled (-1/-1)
- Verifies strikes are centered around ATM
- Validates balanced calls/puts

## Test Results
```
✅ ALL 13 PIPELINE TESTS PASSED
✓ Strike count: 100 -> 51 (49 strikes removed)
✓ Range: $75 to $125 (centered around ATM $100)
✓ Balanced: 51 calls = 51 puts
✓ Unlimited mode (-1): All 100 strikes used
```

## Performance Impact

### Before (no filtering):
- **SPY**: ~170 strikes per expiration
- **Calculation time**: Hours for 4 strategies (IC, BF, Shifted IC, Shifted BF)
- **Combinations**: 170² = 28,900 pairs per strategy

### After (50 strikes):
- **SPY**: ~50 strikes per expiration
- **Calculation time**: Minutes for 4 strategies
- **Combinations**: 50² = 2,500 pairs per strategy
- **Speedup**: ~11x reduction in calculations

## Configuration

To disable strike filtering (use all strikes):
```python
# In filters/phase2strat1/chain_index.py
STRIKE_LIMIT_ENABLED = False
```

To adjust the number of strikes:
```python
# In filters/phase2strat1/chain_index.py
MAX_STRIKES_ITM = 30  # Increase to 30 ITM
MAX_STRIKES_OTM = 30  # Increase to 30 OTM
MAX_TOTAL_STRIKES = 60  # Total becomes 60
```

## Notes

- Phase 1 data gathering remains unchanged (fetches all strikes)
- All data stored in Redis cache
- Filtering only affects Phase 2 calculations
- Strategies calculate on relevant strikes around current price
- Deep ITM/OTM strikes are typically not useful for IC/BF strategies anyway
