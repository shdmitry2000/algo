# Phase 3 Terminator — Robust Timeout Implementation

## Overview

The Phase 3 Terminator is a robust timeout-based mechanism that automatically clears signals that haven't been executed within a configurable timeout period. This prevents signals from being locked indefinitely and allows the system to continuously cycle through opportunities.

## How It Works

### Timeout-Based Termination (Not Delay-Based)

**OLD Approach (5-second delay)**:
- Wait 5 seconds for every signal
- Always terminate after delay
- Sequential processing (slow)

**NEW Approach (60-second timeout)** ✅:
- Check signal age from gate timestamp
- Only terminate if age > TIMEOUT_SECONDS
- Parallel processing (instant)
- Respects actual signal lifecycle

### Algorithm

```python
TIMEOUT_SECONDS = 60  # Configurable threshold

For each active signal:
1. Get gate.updated_at timestamp
2. Calculate age = now - gate.updated_at
3. If age >= TIMEOUT_SECONDS:
   - Terminate signal with reason "phase3_timeout"
   - Clear gate with status "cleared_after_fail"
   - Delete active signal
   - Log phase3_open_fail event with age details
4. Else:
   - Skip (signal still has time)
   - Log remaining time
```

### Continuous Mode

Runs in a loop:
```
Every 5 seconds:
1. List all active signals
2. Check each signal's age
3. Terminate only signals > 60s old
4. Skip signals still within timeout window
5. Log: terminated=X, skipped=Y
6. Wait 5s, repeat
```

## Usage

### Start Terminator

**Continuous mode** (recommended for production):
```bash
./.conda/bin/python cli/phase3_terminator.py --mode continuous

# Or use the start script:
./start_terminator.sh

# Or start entire system (includes terminator):
./start_all.sh
```

**Single run** (for testing):
```bash
./.conda/bin/python cli/phase3_terminator.py --mode once
```

### Configuration

Edit `cli/phase3_terminator.py`:
```python
# Change timeout threshold (in seconds)
TIMEOUT_SECONDS = 60  # Default: 60 seconds

# Change polling interval for continuous mode
POLL_INTERVAL = 5  # Check every 5 seconds
```

## Lifecycle Example

### Timeline: Signal Creation to Termination

```
T=0s:   Phase 2 creates signal
        └─ SIGNAL:ACTIVE:AAPL:2026-04-17 created
        └─ Gate locked: status = "signal_pending_open"
        └─ Gate timestamp: 2026-03-28T22:37:00Z

T=5s:   Terminator checks (Cycle 1)
        └─ Age = 5s < 60s → SKIP

T=10s:  Terminator checks (Cycle 2)
        └─ Age = 10s < 60s → SKIP

T=15s:  Terminator checks (Cycle 3)
        └─ Age = 15s < 60s → SKIP

... (continues checking every 5s) ...

T=60s:  Terminator checks (Cycle 12)
        └─ Age = 60s >= 60s → TERMINATE
        └─ Record phase3_open_fail
        └─ Clear gate: status = "cleared_after_fail"
        └─ Delete signal
        └─ Log event with age=60.2s, reason="phase3_timeout"

T=65s:  Gate is now unlocked
        └─ Next Phase 2 scan can create new signal
```

## Benefits

### 1. Robust Timeout Management
- Signals don't stay locked forever
- Automatic cleanup after timeout
- Configurable timeout threshold

### 2. No Wasted Delays
- OLD: 5s × 170 signals = 14 minutes sequential
- NEW: Check all 170 signals instantly, only wait for timeout

### 3. Graceful Handling
- Checks signal age before terminating
- Respects active Phase 3 execution window
- Logs detailed timeout information

### 4. Production-Ready
- Handles timezone-aware timestamps
- Handles missing gates (inconsistent state cleanup)
- Continuous mode for 24/7 operation
- Graceful shutdown (Ctrl+C)

### 5. Detailed Logging
- Logs age, threshold, and remaining time
- Distinguishes between timeout and immediate termination
- Separate log file: `terminator.log`

## Monitoring

### Check Terminator Status
```bash
# See if terminator is running
ps aux | grep phase3_terminator

# Watch live logs
tail -f terminator.log

# Count signals being processed
redis-cli KEYS "SIGNAL:ACTIVE:*" | wc -l
```

### Logs Output Example
```
[INFO] [terminator] === Cycle 14 ===
[INFO] [terminator] Found 170 active signals, checking timeouts...
[INFO] [terminator] Cycle 14 complete: terminated=0, skipped=170 (not yet timed out)
[INFO] [terminator] Waiting 5s before next check...

... (60 seconds later) ...

[INFO] [terminator] === Cycle 26 ===
[INFO] [terminator] Found 170 active signals, checking timeouts...
[INFO] [terminator] TIMEOUT: AAPL 2026-07-17 (age=61.2s, threshold=60s, signal_id=105b35cf...)
[INFO] [terminator] ✓ Terminated AAPL 2026-07-17 (gate unlocked, signal deleted)
[INFO] [terminator] TIMEOUT: PLTR 2026-04-10 (age=61.3s, threshold=60s, signal_id=ee75d328...)
[INFO] [terminator] ✓ Terminated PLTR 2026-04-10 (gate unlocked, signal deleted)
...
[INFO] [terminator] Cycle 26 complete: terminated=170, skipped=0 (not yet timed out)
```

## Integration with Real Phase 3

When you implement real order execution:

### Option A: Replace Terminator Entirely
Remove terminator and implement real Phase 3 that:
1. Reads signal legs
2. Sends orders to broker
3. Calls `/api/signals/phase3-outcome` with actual result

### Option B: Keep Terminator as Safety Net
Keep terminator running alongside Phase 3:
- Phase 3 executes orders within 60s window
- If Phase 3 succeeds: calls API, gate cleared
- If Phase 3 fails/hangs: terminator clears after 60s (safety timeout)

**Recommended**: Option B provides fail-safe mechanism

## History Events

The terminator logs detailed events to `SIGNAL:HISTORY`:

```json
{
  "ts": "2026-03-28T22:38:00Z",
  "event_type": "phase3_open_fail",
  "symbol": "AAPL",
  "expiration": "2026-04-17",
  "signal_id": "uuid",
  "payload": {
    "reason": "phase3_timeout",
    "timeout_seconds": 60,
    "age_seconds": 61.23,
    "gate_updated_at": "2026-03-28T22:37:00Z",
    "terminator": "auto"
  }
}
```

Visible in UI History tab with all details!

## Summary

**Terminator is now production-ready** with:
- ✅ 60-second timeout threshold (configurable)
- ✅ Age-based termination (not delay-based)
- ✅ Instant processing (checks all signals in <1s)
- ✅ Continuous monitoring (5-second poll interval)
- ✅ Detailed logging (age, threshold, remaining time)
- ✅ Robust error handling (missing gates, timezone parsing)
- ✅ Graceful shutdown (Ctrl+C)
- ✅ Ready for real Phase 3 integration

**The system can now run fully automated:**
1. Phase 1 loads data → auto-triggers Phase 2
2. Phase 2 creates signals → locks gates
3. Terminator waits 60s → auto-clears timeouts
4. Gates unlocked → cycle repeats

🎉 **Fully autonomous signal generation and lifecycle management!**
