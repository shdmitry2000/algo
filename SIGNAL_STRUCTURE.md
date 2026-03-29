# Signal JSON Structure - Visual Reference

## Complete Signal Object Saved to Redis Cache

```
Signal (per symbol+expiration pair)
├── signal_id: "uuid"
├── symbol: "SPY"
├── expiration: "2026-04-30"
├── dte: 32
├── chain_timestamp: "2026-03-29T10:00:00" ⚡ UNIQUENESS KEY
├── run_id: "run-uuid"
├── computed_at: "2026-03-29T10:05:00"
│
├── best_strategy_type: "BF_BUY" ⭐ TOP PICK
├── best_rank_score: 5.42
│
├── strategies: { 📦 ALL CALCULATED STRATEGIES
│   │
│   ├── "IC_BUY": {
│   │   ├── strategy_type: "IC_BUY"
│   │   ├── open_side: "buy"
│   │   ├── is_imbalanced: false
│   │   ├── dte: 32
│   │   ├── strike_difference: 10.0
│   │   ├── strikes_used: [95.0, 105.0]
│   │   │
│   │   ├── legs: [ 🦵 COMPLETE LEG DATA
│   │   │   ├── {leg_index: 1, strike: 95.0, right: "C", open_action: "BUY", 
│   │   │   │    quantity: 1, bid: 11.0, ask: 12.0, mid: 11.5, volume: 200, OI: 2000}
│   │   │   ├── {leg_index: 2, strike: 105.0, right: "C", open_action: "SELL", ...}
│   │   │   ├── {leg_index: 3, strike: 95.0, right: "P", open_action: "BUY", ...}
│   │   │   └── {leg_index: 4, strike: 105.0, right: "P", open_action: "SELL", ...}
│   │   │   ]
│   │   │
│   │   ├── 🧮 FILTER CALCULATIONS
│   │   ├── remaining_profit: 7.30
│   │   ├── remaining_percent: 36.5
│   │   ├── break_even_days: 133.23
│   │   ├── bed_filter_pass: true ✅
│   │   ├── rank_score: 4.16
│   │   ├── liquidity_pass: true
│   │   │
│   │   └── 💰 COST BREAKDOWN
│   │       ├── mid_entry: 0.0
│   │       ├── spread_cost: 0.0
│   │       ├── fees_total: 2.60
│   │       ├── net_credit: 0.0
│   │       └── computed_at: "..."
│   │   }
│   │
│   ├── "IC_SELL": {
│   │   ├── strategy_type: "IC_SELL"
│   │   ├── open_side: "sell" ⚡ SELL SIDE
│   │   ├── legs: [
│   │   │   ├── {open_action: "SELL", ...} ⬅️ ACTIONS REVERSED
│   │   │   ├── {open_action: "BUY", ...}
│   │   │   └── ...
│   │   │   ]
│   │   └── remaining_profit: 2.38 (credit > width) ✅
│   │   }
│   │
│   ├── "IC_BUY_IMBAL": {
│   │   ├── strategy_type: "IC_BUY_IMBAL"
│   │   ├── is_imbalanced: true 🔢 IMBALANCED
│   │   ├── buy_notional: 20.0
│   │   ├── sell_notional: 10.0 ⬅️ DOMINANCE: 20.0 >= 10.0 ✅
│   │   ├── total_quantity: 6 (not 4)
│   │   ├── legs: [
│   │   │   ├── {quantity: 2, ...} ⬅️ VARYING QUANTITIES
│   │   │   ├── {quantity: 1, ...}
│   │   │   ├── {quantity: 2, ...}
│   │   │   └── {quantity: 1, ...}
│   │   │   ]
│   │   └── ...
│   │   }
│   │
│   ├── "BF_BUY": { ... }
│   ├── "BF_SELL": { ... }
│   ├── "SHIFTED_IC_BUY": { ... }
│   ├── "SHIFTED_IC_SELL": { ... }
│   └── ... (up to 9+ strategy types)
│   }
│
└── chain_snapshot: { 📸 OPTIMIZED SNAPSHOT
    │
    ├── chain: [ 🔗 ONLY USED STRIKES
    │   ├── {strike: 95.0, right: "C", bid: 11.0, ask: 12.0, mid: 11.5, ...}
    │   ├── {strike: 95.0, right: "P", bid: 11.5, ask: 12.0, mid: 11.75, ...}
    │   ├── {strike: 100.0, right: "C", ...}
    │   └── ... (5 strikes = 10 ticks, not all 11 strikes = 22 ticks)
    │   ]
    │
    └── strategies: { 📋 ALL STRATEGY DETAILS
        ├── "IC_BUY": { ... full data ... }
        ├── "BF_BUY": { ... full data ... }
        └── ... (all strategies with complete calculations)
        }
    }
```

## Key Features

### 1. Uniqueness (Prevents Duplicates)
```
Unique ID = symbol + expiration + chain_timestamp
Example: SPY_2026-04-30_2026-03-29T10:00:00

If chain data hasn't changed:
  ✅ Same timestamp → Skip scan (prevents duplicate)

If chain data updated:
  ✅ New timestamp → Create new signal
```

### 2. Multi-Strategy Storage
```
All calculated strategies saved in ONE Signal:
  - IC_BUY, IC_SELL, IC_BUY_IMBAL, IC_SELL_IMBAL
  - BF_BUY, BF_SELL
  - SHIFTED_IC_BUY, SHIFTED_IC_SELL
  - SHIFTED_BF_BUY, SHIFTED_BF_SELL
  - ... (up to 16 variants)

History shows ALL strategies, not just the best!
```

### 3. Complete Leg Data
```
Each strategy contains ALL legs with:
  ✓ Strike price
  ✓ Right (Call/Put)
  ✓ Action (BUY/SELL)
  ✓ Quantity (1+ for imbalanced)
  ✓ Bid/Ask/Mid prices
  ✓ Volume and Open Interest

No missing data - everything needed for trade execution!
```

### 4. Filter Metadata
```
Each strategy includes:
  ✓ remaining_profit: Profit after all costs
  ✓ remaining_percent: Profit as % of max loss
  ✓ break_even_days: Days until breakeven (BED)
  ✓ bed_filter_pass: Whether DTE < BED
  ✓ rank_score: BED/DTE ratio (for ranking)
  ✓ liquidity_pass: Liquidity check result

History can show WHY strategies passed/failed!
```

### 5. Memory Optimization
```
Chain snapshot includes ONLY used strikes:
  Original: 11 strikes = 22 ticks
  Snapshot: 5 strikes = 10 ticks
  Savings: ~50% memory reduction

But still contains ALL data needed for reconstruction!
```

## Data Flow

```
1. Option Chain → Filter Scan
                  ↓
2. Calculate ALL Strategies (IC, BF, Shifted variants)
   ├── Standard (BUY/SELL)
   └── Imbalanced (BUY_IMBAL/SELL_IMBAL)
                  ↓
3. Apply BED Filter (DTE < BED)
                  ↓
4. Select Best per Strategy Type (highest rank_score)
                  ↓
5. Choose Overall Best (priority: BF > SHIFTED_BF > IC > SHIFTED_IC > IMBAL)
                  ↓
6. Build Signal with:
   ├── ALL strategies (not just best)
   ├── Complete leg data
   ├── Filter metadata
   └── Optimized chain snapshot
                  ↓
7. Save to Redis: `signal:{symbol}:{expiration}`
                  ↓
8. Uniqueness check: symbol+expiration+chain_timestamp
   ├── If exists with same timestamp → SKIP (no duplicate)
   └── If new timestamp → UPSERT signal
```

## Testing Validation

All 8 Signal JSON tests verify:
- ✅ Structure complete (11 fields)
- ✅ All strategies included
- ✅ All legs with complete data
- ✅ Filter metadata present
- ✅ Snapshot optimized
- ✅ Best strategy selection
- ✅ SELL strategies (reversed actions)
- ✅ Imbalanced strategies (notional dominance)

**Result**: Signal JSON is production-ready! 🎉
