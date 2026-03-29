# AlgoTrade System — Complete Flow with Phase 3 Terminator

## System Architecture (3 Phases + UI)

### Phase 1: Data Collection (Auto-Running)
**Purpose**: Fetch latest option data from market

**Flow**:
```
1. Load from provider (yfinance/tradier/theta)
   ↓
2. For each symbol:
   - Fetch all expirations
   - Save to Redis: CHAIN:{symbol}:{expiration}
   ↓
3. ✨ AUTO-TRIGGER Phase 2 scan for that symbol
```

**Run manually**:
```bash
./.conda/bin/python datagathering/pipeline.py
```

**Data structure**:
```
CHAIN:AAPL:2026-04-17 → HSET
  "150.0:C" → {"bid": 2.50, "ask": 2.55, "mid": 2.525, volume: 100, ...}
  "155.0:C" → {"bid": 1.20, "ask": 1.25, "mid": 1.225, volume: 80, ...}
  ...
```

---

### Phase 2: Signal Detection (Auto-Triggered)
**Purpose**: Identify profitable Iron Condor opportunities

**Trigger**: Automatically runs after each symbol loads in Phase 1

**Flow**:
```
For each (symbol, expiration):
1. Check gate lock
   - If LOCKED (awaiting Phase 3) → SKIP, log "gate_skip_scan"
   - If OPEN (idle/cleared) → PROCEED
   ↓
2. Scan for IC opportunities
   - Build strike map
   - Generate IC candidates
   - Apply spread cap rule
   - Calculate fees, BED, profit
   ↓
3. Apply BED filter
   - Keep only: DTE < BreakEvenDays
   - Log "bed_fail" for rejected
   ↓
4. Rank by capital efficiency
   - Score = BED / max(DTE, 1)
   - Select BEST per (symbol, expiration)
   ↓
5. Save signal & lock gate
   - Save: SIGNAL:ACTIVE:{symbol}:{expiration}
   - Lock gate: status = "signal_pending_open"
   - Log: "signal_upserted" event
```

**Run manually** (scans all symbols):
```bash
./.conda/bin/python cli/run_phase2_scan.py
```

**Data structure**:
```
SIGNAL:ACTIVE:AAPL:2026-04-17 → JSON
  {
    "signal_id": "uuid",
    "structure_label": "IC (buy)",
    "dte": 19,
    "break_even_days": 45.2,
    "rank_score": 2.3789,
    "legs": [4 leg objects with strikes/prices/actions],
    "remaining_profit": 123.45,
    ...
  }

SIGNAL:GATE:AAPL:2026-04-17 → JSON
  {
    "status": "signal_pending_open",
    "locked_signal_id": "uuid",
    "updated_at": "2026-03-28T22:15:00Z"
  }
```

---

### Phase 3: Order Execution (Terminator Stub)
**Purpose**: Execute trades (currently simulated with terminator)

**Current Implementation**: Terminator stub that:
- Monitors `SIGNAL:ACTIVE:*` keys
- Waits 5 seconds per signal (simulating order execution)
- Unlocks gate with `open_fail` status
- Deletes signal
- Logs `phase3_open_fail` event

**Run terminator**:
```bash
# Single cycle (process all signals once)
./.conda/bin/python cli/phase3_terminator.py --mode once

# Continuous mode (keep running, process new signals as they appear)
./.conda/bin/python cli/phase3_terminator.py --mode continuous

# Or use the start script
./start_terminator.sh
```

**What happens**:
```
For each active signal:
1. Wait 5 seconds
   ↓
2. Record Phase 3 failure:
   - Clear gate: status = "cleared_after_fail"
   - Delete active signal
   - Log: "phase3_open_fail" event
   ↓
3. Gate UNLOCKED
   → Next Phase 2 scan can create new signal
```

**Future real Phase 3**:
```python
# When order execution is implemented, replace terminator with:
1. Read signal legs
2. Send order to broker API
3. If success:
   - POST /api/signals/phase3-outcome {"status": "open_ok", ...}
   - Gate cleared with "cleared_after_open"
4. If failure:
   - POST /api/signals/phase3-outcome {"status": "open_fail", ...}
   - Gate cleared with "cleared_after_fail"
```

---

## UI Dashboard (3 Tabs)

### Tab 1: Chains
**Purpose**: Inspect raw Phase 1 option data

**View**: One symbol at a time, one expiration at a time (dropdown)

**Use case**: Debug data quality, verify provider data

---

### Tab 2: Signals ⭐
**Purpose**: View ALL active trading signals at once

**View**: Unified table showing ALL symbols × ALL expirations

**Columns**:
- Symbol | Expiration | DTE | Type | BED | Rank | Gate Status | Profit $ | Profit %

**Example**: See 170+ signals across 11 symbols in one scrollable table

**Click row**: Opens detail modal with:
- Full metrics
- Legs breakdown (4-leg table with strikes/prices/actions)
- Raw JSON

---

### Tab 3: History
**Purpose**: Audit log for algorithm validation

**View**: Filterable event stream (570K+ events)

**Filters**:
- Symbol (text input)
- Event Type (dropdown)

**Event types**:
- `scan_pair_start` - Scan began for (symbol, expiration)
- `bed_fail` - Candidate rejected by BED filter (DTE >= BreakEvenDays)
- `signal_upserted` - Signal created and saved
- `gate_skip_scan` - Scan skipped (gate locked, awaiting Phase 3)
- `phase3_open_fail` - Terminator cleared signal (gate unlocked)
- `phase3_open_ok` - (Future) Position opened successfully

**Click row**: Expands to show full payload JSON

---

## Complete System Lifecycle

### Initial Setup
```bash
# Start all services
./start_all.sh

# This starts:
# - Backend API (port 5001)
# - Frontend UI (port 8000)
# - Phase 3 Terminator (continuous mode)
```

### Continuous Operation Loop

```
┌──────────────────────────────────────────────────┐
│ 1. Phase 1: Data Pipeline Runs                  │
│    - Fetches latest option data                 │
│    - Saves to CHAIN:* in Redis                  │
└──────────────────────────────────────────────────┘
                    ↓
┌──────────────────────────────────────────────────┐
│ 2. Phase 2: Auto-Triggered per Symbol           │
│    - Scans for IC opportunities                  │
│    - Checks gate locks (skips if locked)         │
│    - Creates best signal per (symbol, exp)       │
│    - Locks gate → "signal_pending_open"          │
│    - Saves to SIGNAL:ACTIVE:*                    │
└──────────────────────────────────────────────────┘
                    ↓
┌──────────────────────────────────────────────────┐
│ 3. UI: Signals Tab Updates                      │
│    - Shows all active signals                    │
│    - Gate status: "signal_pending_open"          │
└──────────────────────────────────────────────────┘
                    ↓
┌──────────────────────────────────────────────────┐
│ 4. Phase 3: Terminator Processes Signal         │
│    - Waits 5 seconds                             │
│    - Records open_fail                           │
│    - Clears gate → "cleared_after_fail"          │
│    - Deletes signal                              │
│    - Logs: "phase3_open_fail" event              │
└──────────────────────────────────────────────────┘
                    ↓
┌──────────────────────────────────────────────────┐
│ 5. Gate Unlocked — Ready for Next Scan          │
│    - Next Phase 1 run → Phase 2 can scan again  │
│    - New signal can be created for that pair     │
└──────────────────────────────────────────────────┘
                    ↓ (cycle repeats)
```

---

## Key Features

### ✅ Auto-Trigger Phase 2
- Phase 2 runs automatically after each symbol loads
- No manual intervention needed
- Real-time signal generation

### ✅ Gate Lock System
- Prevents duplicate scans while Phase 3 pending
- One signal per (symbol, expiration) at a time
- Status flow: `idle` → `signal_pending_open` → `cleared_after_fail` → `idle`
- Visible in UI as colored badges

### ✅ Phase 3 Terminator (Stub)
- Simulates order execution with 5-second delay
- Automatically unlocks gates
- System can continuously cycle through signals
- Easy to replace with real Phase 3 when ready

### ✅ Append-Only History
- Every decision logged with timestamp
- 570K+ events captured
- Full audit trail for validation
- Filterable in UI by symbol/event type

### ✅ Unified Signal View
- See ALL 170+ signals across ALL symbols/expirations
- Sort by any metric (DTE, BED, Rank, Profit)
- Click for detailed legs breakdown
- Real-time updates as terminator clears signals

---

## Quick Start Commands

### Start System
```bash
./start_all.sh
# Starts: Backend + Frontend + Terminator
```

### Load Data + Auto-Generate Signals
```bash
./.conda/bin/python datagathering/pipeline.py
# Phase 2 auto-triggers per symbol
# Terminator auto-clears signals after 5s
```

### Stop System
```bash
./stop_all.sh
# Stops: Backend + Frontend + Terminator + Pipeline
```

### Manual Phase 2 Scan (Optional)
```bash
./.conda/bin/python cli/run_phase2_scan.py
# Scans all symbols at once
```

### Check Status
```bash
# Active signals
redis-cli KEYS "SIGNAL:ACTIVE:*" | wc -l

# Gate status
redis-cli GET "SIGNAL:GATE:AAPL:2026-04-17"

# Recent history
redis-cli LRANGE "SIGNAL:HISTORY" 0 10
```

---

## Configuration

### Symbols
Edit `config/settings.yaml`:
```yaml
tickers:
- AAPL
- SPY
- TSLA
# ... add more symbols
```

### Provider
Edit `.env`:
```bash
DATA_PROVIDER=yfinance  # or tradier or theta
```

### Phase 2 Parameters
Edit `config/settings.yaml`:
```yaml
parameters:
  fee_per_leg: 0.65  # $ per contract
  min_break_even_days: 10  # BED filter threshold
  spread_cap_bound: 0.01  # Spread cap boundary
```

### Terminator Delay
Edit `cli/phase3_terminator.py`:
```python
time.sleep(5)  # Change to desired delay in seconds
```

---

## Monitoring

### UI Dashboard
- **URL**: http://localhost:8000
- **Signals tab**: Real-time view of all active signals
- **History tab**: Filter events by symbol/type
- **Chains tab**: Raw option data

### Logs
```bash
# Backend API
tail -f api.log

# Frontend
tail -f frontend.log

# Terminator
tail -f terminator.log

# Pipeline (when running)
tail -f pipeline_test.log
```

---

## Current State

### Running Services
- ✅ Backend API: http://localhost:5001
- ✅ Frontend UI: http://localhost:8000
- ✅ Phase 3 Terminator: Running in background

### Data Loaded
- **11 symbols**: AAPL, SPY, TSLA, MSFT, GOOGL, AMZN, NFLX, ASTS, PLTR, NVDA, AMD
- **37,276 option ticks** across all expirations
- **170 signals** being processed by terminator

### Processing Rate
- **Terminator**: 5 seconds per signal
- **Total time**: ~14 minutes to clear all 170 signals
- **Gates unlocking**: Continuously as terminator processes

---

## Next Steps

### To replace terminator with real Phase 3:

1. Implement order execution logic
2. Use signal legs data to construct orders
3. Send to broker API
4. Call `/api/signals/phase3-outcome` with result
5. System will automatically unlock gates and continue cycling

### The infrastructure is ready:
- ✅ Signal payload has full leg details
- ✅ API endpoints exist
- ✅ Gate system tested and working
- ✅ History logging complete
- ✅ UI shows real-time status

Just replace `cli/phase3_terminator.py` with real broker integration!

---

## Architecture Benefits

1. **Decoupled phases** - Each phase independent, easy to test/replace
2. **Gate system** - Prevents race conditions and duplicates
3. **Auto-triggering** - No manual intervention needed
4. **Full audit trail** - Every decision logged to history
5. **Unified UI** - See everything at once (170+ signals, all symbols)
6. **Real-time updates** - UI reflects current state instantly
7. **Easy Phase 3 swap** - Terminator stub → real execution (drop-in replacement)

---

## Files Reference

### Core Modules
- `datagathering/pipeline.py` - Phase 1 data loader (auto-triggers Phase 2)
- `filters/phase2strat1/scan.py` - Phase 2 scanner (checks gates, creates signals)
- `cli/phase3_terminator.py` - Phase 3 stub (unlocks gates after 5s)
- `api/data_inspector.py` - Backend API (serves signals/history)
- `frontend/index.html` - UI dashboard (3 tabs)

### Storage Layer
- `storage/cache_manager.py` - Phase 1 cache (CHAIN:*)
- `storage/signal_cache.py` - Phase 2 cache (SIGNAL:*)

### Scripts
- `start_all.sh` - Start backend + frontend + terminator
- `stop_all.sh` - Stop all services
- `start_terminator.sh` - Start terminator only

### Configuration
- `config/settings.yaml` - Symbols, fees, BED threshold
- `.env` - Provider selection, API keys, Redis config

---

## System is Ready ✅

All three phases are working:
- ✅ Phase 1: Auto-loads data
- ✅ Phase 2: Auto-scans and creates signals
- ✅ Phase 3: Auto-clears signals (terminator stub)
- ✅ UI: Shows unified view of all signals/expirations
- ✅ History: Tracks all events for validation

**The system can now run continuously**, cycling through signals automatically!
