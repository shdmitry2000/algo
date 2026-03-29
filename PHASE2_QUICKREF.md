# Phase 2 Quick Reference

## Run Phase 2 Scan
```bash
python cli/run_phase2_scan.py
```

## Check Results
```bash
# Redis
redis-cli KEYS "SIGNAL:ACTIVE:*"
redis-cli GET "SIGNAL:ACTIVE:AAPL:2024-01-19"
redis-cli LRANGE "SIGNAL:HISTORY" 0 10

# API
curl http://localhost:5001/api/signals/active | jq .
curl http://localhost:5001/api/signals/history?symbol=AAPL | jq .
```

## Key Redis Keys
```
SIGNAL:ACTIVE:{symbol}:{expiration}  # Active signal (one per pair)
SIGNAL:GATE:{symbol}:{expiration}    # Lock state
SIGNAL:HISTORY                       # Event log
```

## API Endpoints
```
GET  /api/signals/active
GET  /api/signals/active/<symbol>/<expiration>
GET  /api/signals/history?symbol=&expiration=&signal_id=&event_type=
POST /api/signal-scan
POST /api/signals/phase3-outcome
```

## Config
```yaml
# config/settings.yaml
parameters:
  fee_per_leg: 0.65
  spread_cap_bound: 0.01
```

## Tests
```bash
pytest tests/filters/test_phase2strat1_core.py -v
python verify_phase2.py
```

## Files
```
filters/phase2strat1/    # Core implementation
storage/signal_cache.py  # Redis I/O
cli/run_phase2_scan.py   # CLI runner
api/data_inspector.py    # API endpoints
```

## Docs
- `filters/phase2strat1/README.md` — Architecture
- `frontend/SIGNALS_UI_SPEC.md` — UI spec
- `PHASE2_COMPLETE.md` — Usage guide
- `PHASE2_SUMMARY.md` — Implementation summary

## Status
✅ All Phase 2 todos complete
✅ All verifications passing
✅ Ready for Phase 3 integration
