# Duplicate Prevention - Complete Validation

## Overview

Tests that verify the filter runs **only once per unique data timestamp**, preventing duplicate signals for the same `(symbol, expiration, chain_timestamp)` combination.

## The Problem

Without duplicate prevention:
- Filter runs every time it's triggered
- Creates duplicate signals for unchanged data
- Wastes compute resources
- Pollutes history with redundant entries

## The Solution

**Two-layer duplicate prevention**:

### Layer 1: Scan Metadata Freshness Check
```python
chain_meta = get_chain_metadata(symbol, expiration)
scan_meta = get_scan_metadata(symbol, expiration)

if chain_meta and scan_meta:
    chain_timestamp = chain_meta.get("updated_at")
    last_chain_timestamp = scan_meta.get("last_chain_timestamp")
    
    if chain_timestamp == last_chain_timestamp:
        # SKIP: Data unchanged since last scan
        skipped_fresh += 1
        continue
```

### Layer 2: Signal Timestamp Check
```python
existing_signal = get_active_signal(symbol, expiration)
if existing_signal and chain_meta:
    existing_ts = existing_signal.chain_timestamp
    current_ts = chain_meta.get("updated_at")
    
    if existing_ts == current_ts:
        # SKIP: Signal already exists with this data
        skipped_unchanged += 1
        continue
```

## Uniqueness Identifier

**Format**: `symbol + expiration + chain_timestamp`

**Example**: `SPY_2026-04-30_2026-03-29T10:00:00`

### Components

1. **symbol**: Stock ticker (e.g., "SPY")
2. **expiration**: Option expiration date (e.g., "2026-04-30")
3. **chain_timestamp**: Data update timestamp from chain metadata

### Why This Works

- Same data → Same timestamp → Same unique ID → **SKIP**
- New data → New timestamp → New unique ID → **PROCEED**

## Test Suite (6 tests)

### 1. Same Timestamp Prevention ✅
**Scenario**: Existing signal with timestamp `10:00:00`, new scan with same timestamp

**Result**: 
- Check 1 (scan metadata): SKIP ✅
- Check 2 (signal timestamp): SKIP ✅
- **Final: SKIPPED** (duplicate prevented)

### 2. New Timestamp Proceed ✅
**Scenario**: Existing signal with timestamp `10:00:00`, new scan with timestamp `12:00:00`

**Result**:
- Check 1: Data changed (10:00 ≠ 12:00)
- Check 2: Timestamps differ
- **Final: PROCEED** (create new signal)

### 3. No Existing Signal ✅
**Scenario**: First scan (no existing signal)

**Result**:
- No signal in cache
- **Final: PROCEED** (create first signal)

### 4. Scan Metadata Freshness ✅
**Scenario**: Scan metadata shows `last_chain_timestamp = 10:00:00`, chain has `10:00:00`

**Result**:
- Timestamps match
- **Final: SKIP** (data unchanged)

### 5. Uniqueness Identifier Format ✅
Tests that different combinations produce different IDs:
- `SPY_2026-04-30_10:00:00` ≠ `SPY_2026-04-30_12:00:00` (different time)
- `SPY_2026-04-30_10:00:00` ≠ `SPY_2026-05-30_10:00:00` (different expiration)
- `SPY_2026-04-30_10:00:00` ≠ `QQQ_2026-04-30_10:00:00` (different symbol)

All 4 combinations produce unique IDs ✅

### 6. Skip Counter Tracking ✅
Tests that scan counters correctly track skip reasons:
- `skipped_gate`: Gate locked
- `skipped_fresh`: Data unchanged (scan metadata)
- `skipped_unchanged`: Signal exists with same timestamp
- `scanned_pairs`: Successfully scanned

## Complete Flow Simulation

```
┌─────────────────────────────────────────────────────────────┐
│ SCAN 1: First scan (10:00:00)                               │
├─────────────────────────────────────────────────────────────┤
│ • No existing signal                                         │
│ • No scan metadata                                          │
│ → PROCEED ✅                                                │
│ → Create signal with timestamp 10:00:00                     │
│ → Save scan metadata: last_chain_timestamp = 10:00:00      │
└─────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────┐
│ SCAN 2: Duplicate attempt (10:00:00 - SAME)                │
├─────────────────────────────────────────────────────────────┤
│ • Existing signal: timestamp = 10:00:00                     │
│ • Scan metadata: last_chain_timestamp = 10:00:00           │
│ • Chain metadata: updated_at = 10:00:00                    │
│ → CHECK 1: 10:00:00 == 10:00:00 → SKIP (freshness) ✅      │
│ → CHECK 2: Would also skip (signal timestamp) ✅            │
│ → Result: SKIPPED (duplicate prevented) 🛑                  │
└─────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────┐
│ SCAN 3: Data updated (12:00:00 - NEW)                      │
├─────────────────────────────────────────────────────────────┤
│ • Existing signal: timestamp = 10:00:00 (old)              │
│ • Scan metadata: last_chain_timestamp = 10:00:00 (old)     │
│ • Chain metadata: updated_at = 12:00:00 (NEW!)             │
│ → CHECK 1: 12:00:00 ≠ 10:00:00 → PROCEED ✅                │
│ → CHECK 2: 12:00:00 ≠ 10:00:00 → PROCEED ✅                │
│ → Result: PROCEED and create new signal ✅                  │
│ → New signal with timestamp 12:00:00                       │
│ → Update scan metadata: last_chain_timestamp = 12:00:00    │
└─────────────────────────────────────────────────────────────┘
```

## Key Benefits

### 1. Prevents Duplicate Processing
- ✅ Same data scanned only once
- ✅ No redundant computations
- ✅ No duplicate signals in cache

### 2. Allows Updates
- ✅ New data triggers new scan
- ✅ Signal updated with latest calculations
- ✅ Old signal replaced by new one

### 3. Efficient Tracking
- ✅ Two-layer check (fast rejection)
- ✅ Skip counters for monitoring
- ✅ History logs skip events

### 4. Robust Uniqueness
- ✅ Symbol-specific (SPY ≠ QQQ)
- ✅ Expiration-specific (April ≠ May)
- ✅ Time-specific (10:00 ≠ 12:00)

## Test Results

```
================================================================================
Duplicate Prevention Tests: 6 passed, 0 failed
================================================================================

✅ Same timestamp → SKIP (prevents duplicates)
✅ New timestamp → PROCEED (allows updates)
✅ Scan metadata freshness check working
✅ Signal timestamp check working
✅ Uniqueness identifier validated
✅ Skip counters tracked correctly

✅ Duplicate prevention ready for production!
```

## Edge Cases Handled

### Case 1: Chain data unchanged
- Chain timestamp: `10:00:00`
- Last scan timestamp: `10:00:00`
- **Result**: SKIP ✅

### Case 2: Chain data updated
- Chain timestamp: `12:00:00`
- Last scan timestamp: `10:00:00`
- **Result**: PROCEED ✅

### Case 3: First scan (no metadata)
- No scan metadata
- No existing signal
- **Result**: PROCEED ✅

### Case 4: Signal exists but metadata missing
- Existing signal: timestamp `10:00:00`
- No scan metadata (edge case)
- Chain timestamp: `10:00:00`
- **Result**: Signal check catches it → SKIP ✅

### Case 5: Multiple expirations
- SPY April signal (timestamp `10:00:00`)
- SPY May scan (timestamp `10:00:00`)
- Different expirations → Different unique IDs
- **Result**: Both proceed independently ✅

## Production Monitoring

The scan returns detailed counters:
```python
{
    "scanned_pairs": 5,        # Successfully scanned
    "skipped_gate": 2,         # Gate locked (positions open)
    "skipped_fresh": 3,        # Data unchanged (scan metadata)
    "skipped_unchanged": 1     # Signal exists (timestamp match)
}
```

Monitor these to ensure:
- `skipped_fresh` + `skipped_unchanged` should be high (efficient)
- `scanned_pairs` should only increase when data changes
- Zero duplicates in history

## Implementation

The duplicate prevention is implemented in `scan.py` lines 295-319:
1. First checks scan metadata (fast path)
2. Then checks existing signal timestamp (backup check)
3. Both use `chain_timestamp` from chain metadata
4. Counters track each skip reason separately

## Next Steps

With duplicate prevention validated:
1. ✅ Deploy to production
2. ✅ Monitor skip counters
3. ✅ Verify no duplicate signals in Redis
4. ✅ Confirm history shows unique entries only

**Status**: Duplicate prevention is production-ready! 🎉
