# Strategy Test Suite

Comprehensive test suite for all 16 strategy variants using synthetic data.

## Test Structure

```
tests/strategies/
├── __init__.py                     # Package init
├── test_fixtures.py                # Hardcoded test data
├── test_spread_math.py             # Spread cap utility tests (5 tests)
├── test_base.py                   # Base strategy class tests (4 tests)
├── test_iron_condor.py            # Iron Condor tests (4 tests)
├── test_butterfly.py              # Butterfly tests (4 tests)
├── test_shifted_condor.py         # Shifted IC tests (3 tests)
├── test_integration.py            # Integration tests (5 tests)
├── test_filter.py                 # Filter scan tests (5 tests)
├── test_signal_json.py            # Signal JSON structure tests (8 tests)
├── test_duplicate_prevention.py   # Duplicate prevention tests (6 tests)
├── test_annual_returns.py         # Annual return & parameter tests (7 tests)
├── test_rank_score.py             # Rank score & Phase 3 tests (7 tests)
├── test_pipeline.py               # End-to-end pipeline tests (11 tests)
└── run_all_tests.py               # Master test runner
```

## Running Tests

### Run All Test Suites
```bash
python tests/strategies/run_all_tests.py
```

### Run Individual Test Suites
```bash
# Spread math tests
python tests/strategies/test_spread_math.py

# Base strategy tests
python tests/strategies/test_base.py

# Iron Condor tests
python tests/strategies/test_iron_condor.py

# Butterfly tests
python tests/strategies/test_butterfly.py

# Shifted Condor tests
python tests/strategies/test_shifted_condor.py

# Integration tests
python tests/strategies/test_integration.py

# Filter tests
python tests/strategies/test_filter.py

# Signal JSON tests
python tests/strategies/test_signal_json.py

# Annual return tests
python tests/strategies/test_annual_returns.py

# Rank score tests
python tests/strategies/test_rank_score.py

# Pipeline tests
python tests/strategies/test_pipeline.py

# Duplicate prevention tests
python tests/strategies/test_duplicate_prevention.py
```

## Test Coverage

### Spread Math Tests (5 tests)
- ✅ Positive spread capping to [0.01, width - 0.01]
- ✅ Negative spread capping to [-(width - 0.01), -0.01]
- ✅ Sign preservation (symmetry between positive/negative)
- ✅ Multiple strike widths (5, 10, 20)
- ✅ Custom bound values

### Base Strategy Tests (4 tests)
- ✅ Strategy type registration (16 types)
- ✅ Imbalanced quantity generator
- ✅ Generator limits and constraints
- ✅ BED calculation formula

### Iron Condor Tests (4 tests)
- ✅ IC_BUY generates candidates with correct structure
- ✅ IC_SELL has reversed leg actions
- ✅ IC_BUY_IMBAL satisfies notional dominance
- ✅ Profit and BED calculations correct

### Butterfly Tests (4 tests)
- ✅ BF_BUY generates standard butterflies (1-2-1 structure)
- ✅ BF_SELL has reversed actions when opportunities exist
- ✅ SHIFTED_BF generates non-adjacent variants
- ✅ Profit calculations correct

### Shifted Condor Tests (3 tests)
- ✅ SHIFTED_IC_BUY generates shifted spreads
- ✅ SHIFTED_IC_SELL has reversed leg actions
- ✅ Notional matching between call and put spreads

### Integration Tests (5 tests)
- ✅ All strategies assign correct strategy_type values
- ✅ BED filter applies correctly to candidates
- ✅ Rank score calculation uses correct formula
- ✅ Strategy selection respects priority order
- ✅ Strategy snapshots only include used strikes

### Filter Tests (5 tests)
- ✅ Filter catches all BUY strategies (IC, BF, SHIFTED variants)
- ✅ Filter catches all SELL strategies with mispriced data
- ✅ Priority ranking selects highest-priority strategy
- ✅ BED filter applied correctly across all strategies
- ✅ Snapshot optimization verified (only used strikes)

### Signal JSON Tests (8 tests)
- ✅ Signal JSON structure has all required fields
- ✅ Strategies field contains all detected strategy types
- ✅ All strategies include complete leg data (strike, right, action, qty, prices)
- ✅ Filter metadata included (profit, BED, rank_score, bed_filter_pass)
- ✅ Chain snapshot optimized (only used strikes)
- ✅ Best strategy correctly selected and accessible
- ✅ SELL strategies properly included with reversed actions
- ✅ Imbalanced strategies include notional dominance data

### Duplicate Prevention Tests (6 tests)
- ✅ Same timestamp prevents duplicate scan (SKIP)
- ✅ New timestamp allows signal update (PROCEED)
- ✅ No existing signal allows first scan (PROCEED)
- ✅ Scan metadata freshness check working
- ✅ Uniqueness identifier format validated (symbol+expiration+datetime)
- ✅ Skip counter tracking verified

### Annual Return Tests (7 tests)
- ✅ Annual return calculation formula verified
- ✅ >100% annual return threshold calculations
- ✅ Max entry price for target annual returns
- ✅ BED ↔ Annual return conversion
- ✅ High return detection (>100% strategies)
- ✅ IC strategy saves annual_return_percent field
- ✅ Signal JSON includes annual return data

### Rank Score Tests (7 tests)
- ✅ Rank score formula verified (BED / DTE)
- ✅ Relationship to annual return (score = annual% / 100)
- ✅ Rank score computed on real candidates
- ✅ Best strategy selection by rank_score
- ✅ Cross-strategy rank_score comparison
- ✅ BED filter integration with ranking
- ✅ Phase 3 opening order determined by rank_score

### Pipeline Tests (11 tests)
- ✅ Chain index build from raw data
- ✅ Multi-strategy scanning (IC, BF, Shifted)
- ✅ BED filter application to all candidates
- ✅ Rank score computation and sorting
- ✅ Best candidate selection per strategy type
- ✅ Signal object creation with all strategies
- ✅ Signal serialization to JSON (Redis format)
- ✅ Phase 3 data availability verification
- ✅ Duplicate prevention flow
- ✅ Multi-symbol pipeline simulation
- ✅ Complete end-to-end flow validation

## Test Results Summary

**Total Test Suites**: 12  
**Total Tests**: 69  
**Status**: ✅ **ALL TESTS PASSING**

### Sample Test Run Output

```
Spread Math Tests: 5 passed, 0 failed
Base Strategy Tests: 4 passed, 0 failed
Iron Condor Tests: 4 passed, 0 failed
Butterfly Tests: 4 passed, 0 failed
Shifted Condor Tests: 3 passed, 0 failed
Integration Tests: 5 passed, 0 failed
Filter Integration Tests: 5 passed, 0 failed
Signal JSON Tests: 8 passed, 0 failed
Duplicate Prevention Tests: 6 passed, 0 failed
Annual Return Tests: 7 passed, 0 failed
Rank Score Tests: 7 passed, 0 failed
Pipeline Tests: 11 passed, 0 failed
```

### Strategies Verified (with hardcoded data)

**BUY Chain (TEST_BUY)**:
- **IC_BUY**: 9 candidates
- **IC_BUY_IMBAL**: 358 candidates (with fixed max_total_legs logic)
- **BF_BUY**: 9 candidates  
- **SHIFTED_IC_BUY**: 54 candidates
- **SHIFTED_BF_BUY**: 17 candidates

**SELL Chain (TEST_SELL)** - Mispriced options:
- **IC_SELL**: 2 candidates ✅
- **IC_SELL_IMBAL**: 3 candidates ✅
- **BF_SELL**: 1 candidate ✅
- **SHIFTED_IC_SELL**: 3 candidates ✅

**Note**: SELL strategies require extreme mispricing (credit > max_loss) and are intentionally rare.
Imbalanced candidate counts increased significantly after fixing the `max_total_legs // 4` bug.

## Key Validations

### Notional Dominance (Doc Page 9)
- All 358+ imbalanced candidates satisfy: `buy_notional >= sell_notional`
- Example: buy=$10.00, sell=$5.00 (2:1 ratio) ✅

### Leg Actions
- **BUY side**: [BUY, SELL, BUY, SELL] ✅
- **SELL side**: [SELL, BUY, SELL, BUY] ✅
- Actions correctly reversed for SELL strategies

### Profit Calculations
- All candidates have `remaining_profit > 0`
- BED formula verified: `BED = (365/100) * remaining_percent`
- Remaining percent: `(remaining_profit / width) * 100`

### Data Efficiency
- Snapshots only include used strikes
- Example: 2 strikes used out of 7 available (71% reduction)

## Test Data

All tests use **hardcoded, predictable test data** defined in `test_fixtures.py`.

### Two Test Chains

**1. TEST_CHAIN_BUY** - Normal arbitrage opportunities (BUY strategies):
- Expiration: 2026-04-30 (DTE=32)
- Strikes: 80, 85, 90, 95, 100, 105, 110, 115, 120, 125, 130 (11 strikes)
- Realistic pricing following put-call parity
- Generates: IC_BUY, BF_BUY, SHIFTED_IC_BUY, IC_BUY_IMBAL

**2. TEST_CHAIN_SELL** - Mispriced options (SELL strategies):
- Expiration: 2026-04-30 (DTE=32)
- Strikes: 85, 90, 95, 100, 105, 110, 115 (7 strikes)
- **Extreme mispricing**: 95C and 95P BOTH expensive ($11.50), 105C and 105P BOTH cheap ($0.50)
- Violates put-call parity intentionally to create SELL opportunities
- Generates: IC_SELL, BF_SELL, SHIFTED_IC_SELL

### Why Two Chains?

SELL strategies require extreme market conditions:
- **IC_SELL**: Needs credit > max_loss (both spreads positive)
- **BF_SELL**: Needs net < 0 and abs(net) > width + fees

These conditions rarely occur in normal markets, so we use artificially mispriced data to verify SELL logic works correctly.

### No Randomness

All test results are **100% deterministic** - same candidates, same counts, same profits every run.

## What's Tested

✅ Strategy type constants (16 total)  
✅ Imbalanced quantity generation  
✅ BUY side strategies (all 4 types)  
✅ SELL side strategies (all 4 types)  
✅ Imbalanced variants (when enabled)  
✅ Leg action reversal for SELL  
✅ Notional dominance validation  
✅ Profit calculations  
✅ BED formula  
✅ Rank score formula  
✅ Strategy selection priority  
✅ Data snapshot optimization  
✅ Duplicate prevention (timestamp-based)  
✅ Annual return calculations  
✅ Max entry price for target returns  
✅ Parameter preservation in Signal JSON  

## Notes

- SELL and imbalanced candidates may be 0 with certain data (this is normal and expected)
- SHIFTED_IC generates many candidates due to combinatorial explosion
- Tests complete in <1 second with hardcoded data
- Tests verify structure and logic, not market-specific edge cases
- All test data is predictable and deterministic for reliable CI/CD
