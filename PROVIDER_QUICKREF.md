# Provider Quick Reference

Fast reference for working with data providers.

---

## Switch Provider (1 line)

```bash
export DATA_PROVIDER=yfinance  # or tradier, theta
```

---

## Test Providers

```bash
# All provider tests (stubs, no credentials)
python tests/providers/test_all_providers.py

# Live test (requires credentials)
python tests/providers/test_live_providers.py --provider yfinance
```

---

## Provider Status

| Provider | Status | Needs |
|----------|--------|-------|
| yfinance | ✅ Working | Nothing |
| tradier | ⚠️ Needs token | `TRADIER_ACCESS_TOKEN` |
| theta | ⚠️ Needs creds | `THETA_USERNAME`, `THETA_PASSWORD` |
| schwab | ⚠️ Phase 3 only | OAuth (Phase 3) |

---

## Add Tradier

```bash
# Get token: https://developer.tradier.com
echo "TRADIER_ACCESS_TOKEN=your_token" >> .env
echo "TRADIER_SANDBOX=true" >> .env
export DATA_PROVIDER=tradier
python cli/run_phase2_scan.py
```

---

## Add Theta

```bash
# Get credentials from ThetaData
echo "THETA_USERNAME=your_username" >> .env
echo "THETA_PASSWORD=your_password" >> .env
export DATA_PROVIDER=theta
python cli/run_phase2_scan.py
```

---

## Provider Interface

All providers must implement:

```python
class YourProvider(BaseProvider):
    @property
    def name(self) -> str:
        return "your_provider"
    
    def fetch_chain(self, ticker: str) -> List[StandardOptionTick]:
        # Fetch and return option chain
        return ticks
```

---

## StandardOptionTick Format

All providers must return:

```python
StandardOptionTick.make(
    root="SPY",
    expiration="2026-05-15",
    strike=500.0,
    right="C",
    bid=10.40,
    ask=10.60,
    volume=1000,
    open_interest=5000,
    provider="your_provider"
)
```

---

## Add New Provider

1. Create: `datagathering/providers/your_provider.py`
2. Inherit from `BaseProvider`
3. Implement `name` + `fetch_chain()`
4. Add to `pipeline.py::get_provider()`
5. Test: `python tests/providers/test_all_providers.py`

Full template: `tests/providers/PROVIDER_TEMPLATES.md`

---

## Common Issues

**Issue**: `ModuleNotFoundError: No module named 'yfinance'`
**Fix**: `pip install yfinance`

**Issue**: Tradier returns 401
**Fix**: Check `TRADIER_ACCESS_TOKEN` in `.env`

**Issue**: Theta hangs
**Fix**: Use `get_last_option()` not `get_strikes()` for active expirations

**Issue**: No data returned
**Fix**: Check market hours, verify ticker symbol, check credentials

---

## Files

```
tests/providers/
├── test_all_providers.py      # Stub tests (no credentials)
├── test_live_providers.py     # Live tests (with credentials)
├── README.md                  # Full documentation
├── PROVIDER_TEMPLATES.md      # Implementation templates
└── ../run_all_tests.py        # Master runner (strategies + providers)

datagathering/providers/
├── base_provider.py           # Abstract base
├── yfinance_provider.py       # YFinance (working)
├── tradier_provider.py        # Tradier (working)
├── theta_provider.py          # Theta (working)
├── schwab_provider.py         # Schwab (Phase 3 stub)
└── ibkr_provider_stub.py      # IBKR example stub
```

---

## Quick Commands

```bash
# Test everything
python tests/run_all_tests.py

# Test strategies only
python tests/strategies/run_all_tests.py

# Test providers only
python tests/providers/test_all_providers.py

# Live provider test
python tests/providers/test_live_providers.py --provider yfinance

# Run pipeline with specific provider
DATA_PROVIDER=yfinance python cli/run_phase2_scan.py
```

---

## Status: ✅ COMPLETE

- 4 providers tested
- 14 provider tests passing
- Template for new providers ready
- Live testing framework ready
- Documentation complete

**Next**: Add credentials for live testing OR build Phase 3
