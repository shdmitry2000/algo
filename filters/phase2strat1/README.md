# Phase 2 Signal Engine — Implementation Summary

## Overview

Phase 2 ("Anomaly / Expiration Filter") scans option chains cached by Phase 1 and identifies structural profit opportunities using the algorithms from `docs/Options_Arbitrage_System_Step1.txt`.

**Key principle:** One active signal per `(symbol, expiration)`. Gates prevent re-determination until Phase 3 (buy) resolves.

---

## Architecture

```
filters/phase2strat1/
  ├── __init__.py          # Package entry
  ├── models.py            # Signal, Leg, HistoryEvent, GateStatus dataclasses
  ├── spread_math.py       # apply_spread_cap (Section 11)
  ├── precheck.py          # Symbol-level filter before scanning
  ├── chain_index.py       # Per-expiration index + DTE calc
  ├── iron_condor.py       # IC scanner (v1: buy IC)
  ├── bed.py               # BED filter + ranking (Section 13, 17)
  └── scan.py              # Main orchestrator

storage/signal_cache.py    # Redis SIGNAL:* I/O (active, gate, history)
cli/run_phase2_scan.py     # CLI runner
api/data_inspector.py      # Extended with /api/signals/* endpoints
```

---

## Redis Keys

| Namespace | Key | Purpose |
|-----------|-----|---------|
| **CHAIN** | `CHAIN:{ticker}:{expiration}` | Phase 1 data (read-only for Phase 2) |
| **SIGNAL:ACTIVE** | `SIGNAL:ACTIVE:{symbol}:{expiration}` | Current signal JSON (one per pair) |
| **SIGNAL:GATE** | `SIGNAL:GATE:{symbol}:{expiration}` | Lock state (`idle` / `signal_pending_open` / ...) |
| **SIGNAL:HISTORY** | `SIGNAL:HISTORY` | Append-only event log (LPUSH) |
| **SIGNAL:RUN** | `SIGNAL:RUN:{run_id}` | Batch run metadata (optional) |
| **SIGNAL:LATEST_RUN** | `SIGNAL:LATEST_RUN` | Pointer to most recent `run_id` |

---

## Signal JSON Schema

```json
{
  "signal_id": "uuid",
  "symbol": "AAPL",
  "expiration": "2024-01-19",
  "structure_kind": "IC",
  "open_side": "buy",
  "structure_label": "IC (buy)",
  "dte": 30,
  "strike_difference": 10.0,
  "legs": [
    {
      "leg_index": 1,
      "strike": 145.0,
      "right": "C",
      "open_action": "BUY",
      "quantity": 1,
      "bid": 2.50,
      "ask": 2.55,
      "mid": 2.525,
      "volume": 100,
      "open_interest": 500
    }
    // ... 3 more legs
  ],
  "mid_entry": 5.05,
  "spread_cost": 5.05,
  "net_credit": -5.05,
  "fees_total": 2.60,
  "fee_per_leg": 0.65,
  "leg_count": 4,
  "remaining_profit": 2.35,
  "remaining_percent": 0.235,
  "break_even_days": 85.775,
  "bed_filter_pass": true,
  "liquidity_pass": true,
  "liquidity_detail": "basic_check_pass",
  "structural_pass": true,
  "rank_score": 2.859,
  "run_id": "...",
  "computed_at": "2024-01-01T12:00:00"
}
```

---

## Flow

1. **Precheck** — Filter configured tickers by Redis `CHAIN:*` presence.
2. **Gate check** — Skip `(symbol, expiration)` pairs locked by Phase 3.
3. **Scan** — For each open pair:
   - Build `ChainIndex` (strike → tick for C/P)
   - Compute DTE
   - Enumerate IC candidates (v1: buy IC only)
   - Apply spread cap (Section 11)
   - Check liquidity (non-zero bid/ask)
4. **BED filter** — Keep candidates where `DTE < BreakEvenDays` (Section 13.2)
5. **Rank** — Compute `rank_score = BED / max(DTE, 1)` (Section 17)
6. **Select** — Per `(symbol, expiration)`, keep the **single** highest-scoring signal
7. **Upsert** — Write to `SIGNAL:ACTIVE:*`, lock gate, append history `signal_upserted`

---

## Usage

### CLI

```bash
# Run scan
python cli/run_phase2_scan.py

# View results
redis-cli KEYS "SIGNAL:ACTIVE:*"
redis-cli GET "SIGNAL:ACTIVE:AAPL:2024-01-19"
```

### API

```bash
# List active signals
curl http://localhost:5001/api/signals/active

# Get one signal
curl http://localhost:5001/api/signals/active/AAPL/2024-01-19

# Query history
curl "http://localhost:5001/api/signals/history?symbol=AAPL&limit=50"

# Trigger scan
curl -X POST http://localhost:5001/api/signal-scan

# Record Phase 3 outcome (when Phase 3 is implemented)
curl -X POST http://localhost:5001/api/signals/phase3-outcome \
  -H "Content-Type: application/json" \
  -d '{"signal_id":"...", "symbol":"AAPL", "expiration":"2024-01-19", "status":"open_ok"}'
```

### Python

```python
from filters.phase2strat1 import run_scan

result = run_scan()
print(result)  # {'run_id': '...', 'signals_upserted': 3, ...}
```

---

## Configuration

`config/settings.yaml`:

```yaml
parameters:
  fee_per_leg: 0.65         # Per-contract fee (Section 12)
  spread_cap_bound: 0.01    # Cap boundary (Section 11)
```

---

## Testing

```bash
pytest tests/filters/test_phase2strat1_core.py -v
```

---

## Extension: Additional Structures

To add **Shifted IC**, **Butterfly**, **Shifted BF**:

1. Create `filters/phase2strat1/shifted_ic.py` (etc.) — scan functions
2. Import in `scan.py`, call after `scan_iron_condor`
3. Append candidates to the same list
4. BED filter + ranking work across all structure kinds
5. UI already supports `structure_label` ("Shifted IC (buy)", "BF (sell)", ...)

No breaking changes to Signal JSON or API.

---

## Phase 3 Integration

Phase 3 (Buy / Open) will:

1. Read `SIGNAL:ACTIVE:{symbol}:{expiration}`
2. Execute order for `legs` (buy/sell actions, strikes)
3. On **success**: call `record_phase3_open_success(signal_id, symbol, expiration)` — clears gate, deletes active
4. On **failure**: call `record_phase3_open_failure(signal_id, symbol, expiration, reason)` — clears gate, deletes active

Phase 2 scanner may run again for that `(symbol, expiration)` after gate clears.

---

## History Event Types

- `precheck_symbol`, `precheck_fail`
- `scan_pair_start`
- `liquidity_fail`, `structural_fail`, `bed_fail`
- `signal_upserted`
- `gate_skip_scan`
- `phase3_open_ok`, `phase3_open_fail`

Query via `/api/signals/history` with filters.
