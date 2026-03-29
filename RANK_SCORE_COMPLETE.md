# Rank Score Testing - Phase 3 Ready

## Overview

Comprehensive testing of the `rank_score` calculation that determines:
1. Which strategies pass the BED filter
2. Best candidate selection within each strategy type
3. **Phase 3 opening priority order** (most important!)

## Implementation

### Formula

```python
def compute_rank_score(candidate: StrategyCandidate) -> float:
    """
    rank_score = BED / max(DTE, 1)
    
    Higher score = Better capital efficiency
    """
    return candidate.break_even_days / max(candidate.dte, 1)
```

### Relationship to Annual Return

```
rank_score = annual_return% / 100

Examples:
  Annual = 416% → rank_score = 4.16
  Annual = 896% → rank_score = 8.96
  Annual = 100% → rank_score = 1.0
```

**Key Insight**: Ranking by `rank_score` is equivalent to ranking by `annual_return_percent`.

## Test Results

### All 7 Tests Pass ✅

1. **Rank Score Formula**: Verified BED/DTE calculation
2. **Relationship to Annual Return**: Confirmed score = annual%/100
3. **Real Candidates**: Tested on 9 IC candidates
4. **Best Strategy Selection**: Selected best from IC, BF, Shifted IC
5. **Cross-Strategy Comparison**: Compared scores across types
6. **BED Filter Integration**: Only passing candidates get scores
7. **Phase 3 Opening Order**: Simulated capital allocation

### Test Data Highlights

**IC_BUY Candidates (sorted by rank_score)**:

| Rank | Strikes | BED   | DTE | Score | Annual% |
|------|---------|-------|-----|-------|---------|
| 1    | 80/115  | 286.8 | 32  | 8.962 | 896.2%  |
| 2    | 85/110  | 258.4 | 32  | 8.076 | 807.6%  |
| 3    | 90/100  | 251.8 | 32  | 7.870 | 787.0%  |
| 4    | 90/105  | 228.7 | 32  | 7.148 | 714.8%  |
| 5    | 80/110  | 216.6 | 32  | 6.768 | 676.8%  |

**Best Per Strategy Type**:

| Strategy       | Strikes | BED   | Score | Annual% |
|---------------|---------|-------|-------|---------|
| SHIFTED_IC_BUY | 80/115  | 308.4 | 9.638 | 963.8%  |
| IC_BUY        | 80/115  | 286.8 | 8.962 | 896.2%  |
| BF_BUY        | 115/125 | 173.0 | 5.407 | 540.7%  |

**Winner**: SHIFTED_IC_BUY with score 9.638 (963% annual!)

### Phase 3 Opening Order (Top 10)

**With Imbalanced Strategies Included**:

| Priority | Strategy      | Strikes | BED   | Score  | Annual%  |
|----------|--------------|---------|-------|--------|----------|
| 1        | IC_BUY_IMBAL | 80/120  | 349.2 | 10.912 | 1091.2%  |
| 2        | IC_BUY_IMBAL | 80/120  | 349.2 | 10.912 | 1091.2%  |
| 3        | IC_BUY_IMBAL | 80/120  | 348.4 | 10.887 | 1088.7%  |
| 4        | IC_BUY_IMBAL | 80/120  | 347.2 | 10.850 | 1085.0%  |
| 5        | IC_BUY_IMBAL | 80/120  | 347.2 | 10.850 | 1085.0%  |

**Total qualified**: 361 candidates  
**Top score**: 10.912 (over 1000% annual return!)

## Phase 3 Integration

### How Phase 3 Uses rank_score

```python
# 1. Get all active signals from Redis
signals = get_all_active_signals()

# 2. Sort by best_rank_score (highest first)
signals.sort(key=lambda s: s.best_rank_score, reverse=True)

# 3. Allocate capital in order
capital_available = 100000
capital_per_trade = 10000

for signal in signals:
    if capital_available >= capital_per_trade:
        # Open position for this signal
        open_position(signal)
        capital_available -= capital_per_trade
    else:
        # Out of capital, remaining signals wait
        break
```

### Example: Capital Allocation

**Available**: $50,000  
**Per Trade**: $10,000

| Priority | Symbol | Score | Annual% | Allocated | Status |
|----------|--------|-------|---------|-----------|--------|
| 1        | NDX    | 6.2   | 620%    | $10,000   | ✅ OPEN |
| 2        | SPX    | 4.5   | 450%    | $10,000   | ✅ OPEN |
| 3        | IWM    | 3.7   | 370%    | $10,000   | ✅ OPEN |
| 4        | RUT    | 2.8   | 280%    | $10,000   | ✅ OPEN |
| 5        | QQQ    | 1.5   | 150%    | $10,000   | ✅ OPEN |
| 6        | DIA    | 1.2   | 120%    | $0        | ⏸️ WAIT |

**Result**: Best 5 opportunities opened, $50k deployed with 374% average annual return.

## Verification

### Signal JSON Structure

```json
{
  "signal_id": "SPX-20260430-abc123",
  "best_strategy_type": "IC_BUY",
  "best_rank_score": 8.962,  ← Used for Phase 3 priority ✅
  "strategies": {
    "IC_BUY": {
      "rank_score": 8.962,  ← Also saved here ✅
      "break_even_days": 286.8,
      "annual_return_percent": 896.21,
      "remaining_profit": 27.50,
      ...
    }
  }
}
```

### Test Coverage

✅ **Formula Validation**: BED / DTE correctly computed  
✅ **Annual Return Link**: score = annual% / 100  
✅ **Real Data Testing**: 9 IC candidates ranked  
✅ **Multi-Strategy**: Compared IC, BF, Shifted IC  
✅ **BED Filter**: Only passing candidates ranked  
✅ **Signal Persistence**: rank_score saved in JSON  
✅ **Phase 3 Order**: Capital allocation simulated  

## Key Insights

### 1. Simple Formula, Powerful Results

```
rank_score = BED / DTE
```

This single number tells you:
- Capital efficiency (how fast you break even)
- Relative value vs time commitment
- Priority for opening positions

### 2. Score > 1.0 = Good Trade

- **Score > 1.0**: BED > DTE (>100% annual return)
- **Score = 1.0**: BED = DTE (100% annual return) ← Minimum acceptable
- **Score < 1.0**: BED < DTE (<100% annual return) ← Filtered out

### 3. Imbalanced Strategies Can Score Highest

From tests:
- Best standard IC: score 8.962 (896% annual)
- Best imbalanced IC: score 10.912 (1091% annual)

**Imbalanced strategies win** when they increase notional risk appropriately.

### 4. Phase 3 Uses This Score Exclusively

Phase 3 doesn't need to know:
- Strategy type
- Strikes used
- Profit amount

It only needs:
- `best_rank_score` to determine priority
- Higher score = Opens first

## Production Usage

### 1. Filter by Minimum Score

```python
# Only accept strategies with score > 2.0 (>200% annual)
qualified = [
    signal for signal in all_signals 
    if signal.best_rank_score > 2.0
]
```

### 2. Allocate Capital by Score

```python
# Sort signals by rank_score
sorted_signals = sorted(
    all_signals,
    key=lambda s: s.best_rank_score,
    reverse=True
)

# Open best opportunities first
for signal in sorted_signals:
    if has_capital():
        open_position(signal)
```

### 3. Monitor Performance

```python
# Track opened positions by initial rank_score
opened = get_opened_positions()

avg_score = sum(p.initial_rank_score for p in opened) / len(opened)
print(f"Average rank_score of opened positions: {avg_score:.2f}")
print(f"Expected avg annual return: {avg_score * 100:.1f}%")
```

## Status

**✅ COMPLETE AND PHASE 3 READY**

### What's Validated

✅ rank_score formula correct (BED / DTE)  
✅ Computed for all passing candidates  
✅ Saved in Signal JSON (best_rank_score)  
✅ Enables cross-strategy comparison  
✅ Determines Phase 3 opening order  
✅ 7 comprehensive tests pass  
✅ Integration with BED filter working  

### Test Evidence

```
================================================================================
Rank Score Tests: 7 passed, 0 failed
================================================================================

🎉 ALL RANK SCORE TESTS PASSED!

✓ Rank score formula verified (BED / DTE)
✓ Relationship to annual return validated
✓ Best strategy selection working
✓ Cross-strategy comparison enabled
✓ BED filter integration confirmed
✓ rank_score persisted in Signal JSON
✓ Phase 3 opening order determined correctly

✅ Rank score calculations ready for Phase 3!
```

## Files Created/Modified

1. **Tests**:
   - `tests/strategies/test_rank_score.py` - NEW (7 tests)
   - `tests/strategies/run_all_tests.py` - Added rank_score suite
   - `tests/strategies/README.md` - Updated documentation

2. **Documentation**:
   - `RANK_SCORE_COMPLETE.md` - This file

## Next: Phase 3 Implementation

With rank_score fully tested, Phase 3 can:

1. **Retrieve Signals**:
   ```python
   signals = get_all_active_signals()
   ```

2. **Sort by rank_score**:
   ```python
   signals.sort(key=lambda s: s.best_rank_score, reverse=True)
   ```

3. **Open Positions in Order**:
   ```python
   for signal in signals:
       if can_allocate_capital():
           open_position(signal)
   ```

**The ranking is validated and ready to use!** 🎉
