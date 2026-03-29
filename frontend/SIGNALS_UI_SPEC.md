# Frontend Extension for Phase 2 Signals UI

## Overview
The existing `frontend/index.html` needs a **Signals** tab and **History** tab added alongside the current chain inspector.

---

## UI Structure

```
Header: AlgoTrade — Option Chain Inspector
├── Tab: Chains (existing)
├── Tab: Signals (NEW)
└── Tab: History (NEW)
```

---

## Tab 1: Signals

### Main Grid (one row per symbol + expiration)

**Columns:**
- Symbol
- Expiration
- DTE
- **Type** (e.g. "IC (buy)", "IC (sell)", "Shifted IC (buy)", "BF (buy)", etc.)
- BED
- Rank Score
- **Status** badge (idle / locked awaiting Phase 3 / cleared after open / cleared after fail)
- Actions: [View Detail]

**API:**
```js
fetch('/api/signals/active')
  .then(r => r.json())
  .then(data => {
    // data.signals = [{signal_id, symbol, expiration, structure_label, dte, break_even_days, rank_score, gate_status, ...}, ...]
    renderSignalsTable(data.signals);
  });
```

---

### Detail Panel (on row click)

**Sections:**

1. **Signal Header**
   - Signal ID
   - Symbol / Expiration
   - Type (structure_label)
   - Gate status

2. **Metrics Card**
   - DTE
   - BED
   - Rank Score
   - Mid Entry / Spread Cost / Net Credit
   - Fees Total
   - Remaining Profit / Percent

3. **Legs Table**

| Leg | Strike | C/P | Action | Qty | Bid | Ask | Mid | Vol | OI |
|-----|--------|-----|--------|-----|-----|-----|-----|-----|-----|
| 1   | 145.0  | C   | BUY    | 1   | 2.50| 2.55| 2.525| 100| 500|
| 2   | 155.0  | C   | SELL   | 1   | 1.20| 1.25| 1.225| 80 | 300|
| ... | ...    | ... | ...    | ... | ... | ... | ... | ... | ...|

4. **Recent History** (last 5 events for this pair)
   - Event type, timestamp, payload summary
   - Link: **"Open full history for this signal"** → History tab with filters pre-filled

5. **Raw JSON** (collapsible)
   ```json
   { signal JSON }
   ```

---

## Tab 2: History

### Event Log Table

**Columns:**
- Timestamp
- Event Type
- Symbol / Expiration
- Signal ID (if present)
- Payload Summary
- Actions: [Expand JSON]

**Filters (top bar):**
- Symbol (dropdown or text input)
- Expiration (text input or dropdown)
- Signal ID (text input)
- Event Type (dropdown: all | precheck_* | scan_* | bed_fail | signal_upserted | phase3_* | gate_skip_scan)
- Limit (default 100)

**API:**
```js
fetch(`/api/signals/history?symbol=${symbol}&expiration=${exp}&signal_id=${sig_id}&event_type=${type}&limit=100`)
  .then(r => r.json())
  .then(data => {
    // data.events = [{ts, event_type, symbol, expiration, signal_id, payload}, ...]
    renderHistoryTable(data.events);
  });
```

**Expandable row:**
- Click row to toggle full `payload` JSON display

**Export:**
- Button: "Copy as JSON" → copies filtered events to clipboard

---

## Styling

Reuse existing:
- Dark theme variables (`--bg`, `--surface`, `--border`, `--accent`, `--text`, ...)
- Badge styles (`.badge`)
- Table styles (`thead`, `tbody tr:hover`)
- Button styles (`.refresh-btn`, `.sidebar-run`)

**New badges:**
```css
.badge.gate-idle { color: var(--muted); background: #21262d; }
.badge.gate-locked { color: #f78166; background: rgba(247,129,102,.15); }
.badge.gate-cleared { color: #3fb950; background: rgba(63,185,80,.15); }
```

---

## JavaScript Pseudo-Implementation

```js
// Tab switching
const tabs = { chains: ..., signals: ..., history: ... };
function showTab(name) {
  Object.keys(tabs).forEach(t => tabs[t].style.display = 'none');
  tabs[name].style.display = 'block';
  if (name === 'signals') loadSignals();
  if (name === 'history') loadHistory();
}

// Signals
async function loadSignals() {
  const res = await fetch('/api/signals/active');
  const {signals} = await res.json();
  
  const tbody = document.querySelector('#signals-table tbody');
  tbody.innerHTML = signals.map(sig => `
    <tr onclick="showSignalDetail('${sig.signal_id}')">
      <td>${sig.symbol}</td>
      <td>${sig.expiration}</td>
      <td>${sig.dte}</td>
      <td>${sig.structure_label}</td>
      <td>${sig.break_even_days.toFixed(2)}</td>
      <td>${sig.rank_score.toFixed(4)}</td>
      <td><span class="badge gate-${sig.gate_status}">${sig.gate_status}</span></td>
      <td><button>Detail</button></td>
    </tr>
  `).join('');
}

function showSignalDetail(signalId) {
  // Fetch full signal + gate
  fetch(`/api/signals/active/${symbol}/${expiration}`)
    .then(r => r.json())
    .then(data => {
      // Populate detail panel: metrics, legs table, raw JSON, recent history
    });
}

// History
async function loadHistory(filters = {}) {
  const params = new URLSearchParams(filters);
  const res = await fetch(`/api/signals/history?${params}`);
  const {events} = await res.json();
  
  const tbody = document.querySelector('#history-table tbody');
  tbody.innerHTML = events.map(evt => `
    <tr onclick="togglePayload('${evt.ts}')">
      <td>${evt.ts}</td>
      <td>${evt.event_type}</td>
      <td>${evt.symbol} / ${evt.expiration || 'N/A'}</td>
      <td>${evt.signal_id || 'N/A'}</td>
      <td>${JSON.stringify(evt.payload).slice(0, 50)}...</td>
    </tr>
    <tr id="payload-${evt.ts}" style="display:none">
      <td colspan="5"><pre>${JSON.stringify(evt.payload, null, 2)}</pre></td>
    </tr>
  `).join('');
}

function togglePayload(ts) {
  const row = document.getElementById(`payload-${ts}`);
  row.style.display = row.style.display === 'none' ? 'table-row' : 'none';
}
```

---

## Implementation Notes

1. **Existing `frontend/index.html`** contains the chain inspector (~328 lines).
2. Add **three nav tabs** at the top: Chains, Signals, History.
3. Each tab is a `<div>` with `display: none` by default; JavaScript toggles visibility.
4. **Signals tab** = grid + detail modal/panel (reuse existing modal structure from settings).
5. **History tab** = filterable table + expandable rows.
6. Minimal JavaScript (~150 lines for Signals + History).
7. No external dependencies beyond existing Fetch API.

---

## Testing

1. Run Phase 1 pipeline to populate `CHAIN:*`
2. Run Phase 2 scan: `python cli/run_phase2_scan.py`
3. Check Redis: `redis-cli KEYS "SIGNAL:ACTIVE:*"`
4. Open `http://localhost:5000`
5. Navigate to **Signals** tab → should show active signals
6. Click row → detail panel with legs table
7. Navigate to **History** tab → should show events
8. Filter by symbol/event type → updates table

---

## Future: Phase 3 Integration

When Phase 3 (buy) is implemented:

- Add **"Execute Phase 3"** button on signal detail
- Calls `/api/signals/phase3-outcome` after order execution
- UI polls or listens for gate status change → updates badge to "cleared_after_open" or "cleared_after_fail"
- History tab shows new `phase3_open_ok` / `phase3_open_fail` events
