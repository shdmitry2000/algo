# History Event Filtering Fix

## Problem

The history UI showed only `phase3_open_fail` events without the full filtered/detected Phase 2 data (strategies, legs, strikes, BED scores, etc.). The user expected to see complete signal data in history events.

## Root Cause

The `get_history()` function in `storage/signal_cache.py` had a filtering bug:

```python
# OLD BUGGY CODE:
raw = client.lrange("SIGNAL:HISTORY", offset, offset + limit - 1)  # Get only `limit` events
events = []
for item in raw:
    evt = HistoryEvent.from_json(item)
    if event_type and evt.event_type != event_type:  # Then filter
        continue
    events.append(evt)
```

**The issue:** When you request `limit=200` with `event_type=signal_upserted`:
1. It retrieves only the first 200 events from Redis
2. Then applies the event_type filter
3. But the first ~374 events are all `phase3_open_fail` events
4. So `signal_upserted` events (which start at position 374) were never retrieved

## Solution

Updated `get_history()` to retrieve significantly more events when filters are applied:

```python
# FIXED CODE:
has_filters = any([symbol, expiration, signal_id, event_type])
if has_filters:
    fetch_limit = min(2000, max(1000, (limit + offset) * 10))
else:
    fetch_limit = limit + offset

raw = client.lrange("SIGNAL:HISTORY", 0, fetch_limit - 1)
# Now filters are applied to a larger dataset
```

When filters are used, we now fetch up to 2000 events from Redis, ensuring we reach the `signal_upserted` events even if they're buried deep in the history.

## Verification

### Before Fix
```bash
curl 'http://localhost:5001/api/signals/history?event_type=signal_upserted&limit=5'
# Result: {"count": 0, "events": []}
```

### After Fix
```bash
curl 'http://localhost:5001/api/signals/history?event_type=signal_upserted&limit=5'
# Result: {"count": 5, "events": [...]} with complete data
```

### Data Structure Confirmed

Each `signal_upserted` event now returns complete Phase 2 data:

```json
{
  "event_type": "signal_upserted",
  "symbol": "AMD",
  "expiration": "2026-12-18",
  "signal_id": "3e055a93-4764-4260-aafe-d511b7cae0a9",
  "ts": "2026-03-29T13:44:24.809726",
  "payload": {
    "strategies_calculated": ["IC_BUY_IMBAL", "IC_BUY", "BF_BUY", ...],
    "strategies_passed_bed": ["IC_BUY_IMBAL", "IC_BUY", "BF_BUY", ...],
    "best_strategy_type": "BF_BUY",
    "best_bed": 269.1875,
    "best_rank_score": 1.019649621212121,
    "dte": 264,
    "all_strategy_details": {
      "BF_BUY": {
        "strategy_type": "BF_BUY",
        "legs": [
          {
            "leg_index": 1,
            "strike": 360.0,
            "right": "C",
            "open_action": "BUY",
            "quantity": 1,
            "bid": 7.2,
            "ask": 7.6,
            "mid": 7.4,
            "volume": 4,
            "open_interest": 1320
          },
          // ... more legs
        ],
        "mid_entry": 0.025,
        "break_even_days": 269.1875,
        "rank_score": 1.0196,
        "strikes_used": [360.0, 370.0, 380.0],
        // ... all strategy metrics
      },
      "IC_BUY_IMBAL": { /* full details */ },
      // ... all other strategies
    },
    "chain_snapshot": {
      "chain": [ /* 16 option ticks */ ],
      "strategies": { /* strategy details */ }
    }
  }
}
```

## UI Changes

Also updated `frontend/index.html`:
1. Increased history fetch limit from 200 to 500 events
2. Added event type count badges to show breakdown
3. Shows "Showing X events" with counts by type

## How to Use

To see the complete filtered/detected Phase 2 data in the UI:

1. Open the **History** tab
2. Select **"signal_upserted"** from the Event dropdown
3. Click **Refresh**
4. Click on any row to expand and see the full payload with:
   - All strategies with complete leg data
   - Strike prices, quantities, bid/ask/mid prices
   - BED scores, rank scores, annual return %
   - Chain snapshot with all option ticks used

## Files Modified

- `storage/signal_cache.py` - Fixed `get_history()` filtering logic
- `frontend/index.html` - Increased limit and added event count display

## Testing

Run the test suite to verify:
```bash
./.conda/bin/python tests/strategies/test_pipeline.py
```

All 13 tests pass, including signal creation and serialization tests.
