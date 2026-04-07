# Utility Scripts

This folder contains utility scripts for system verification, testing, and maintenance.

---

## Verification Scripts

### `verify_phase1.py`
**Purpose**: Verify Phase 1 (unified strategy architecture) completion

**What it checks**:
- ✅ All unified strategy imports work
- ✅ Backwards compatibility maintained
- ✅ Old duplicate files deleted
- ✅ All 6 strategies instantiate correctly
- ✅ Strategy registry populated
- ✅ Synthetic test data generation works
- ✅ ChainIndex ↔ ChainData adapters work

**Usage**:
```bash
python util_scripts/verify_phase1.py
```

**Expected output**: All 7 verification checks passing

---

### `verify_phase2.py`
**Purpose**: Verify Phase 2 (signal generation) functionality

**What it checks**:
- Signal generation pipeline
- Filter integration
- Strategy scanning

**Usage**:
```bash
python util_scripts/verify_phase2.py
```

---

### `verify_setup.py`
**Purpose**: Verify initial system setup

**What it checks**:
- Python version
- Required packages installed
- Redis connection
- Environment variables
- Basic functionality

**Usage**:
```bash
python util_scripts/verify_setup.py
```

---

### `verify_memory_optimization.py`
**Purpose**: Verify memory optimizations for chain snapshots

**What it checks**:
- Memory usage optimization
- Snapshot size reduction
- Only used strikes included

**Usage**:
```bash
python util_scripts/verify_memory_optimization.py
```

---

## Maintenance Scripts

### `clean_signals.py` ⚠️
**Purpose**: Clean all Phase 2 signals from Redis

**What it deletes**:
- ✅ Active signals (SIGNAL:ACTIVE:*)
- ✅ Gate locks (SIGNAL:GATE:*)
- ✅ Signal history (SIGNAL:HISTORY)
- ✅ Run metadata (SIGNAL:RUN:*)

**What it preserves**:
- ✅ Phase 1 data (CHAIN:*) - Your option chain data

**Usage**:
```bash
# Dry run (see what would be deleted)
python util_scripts/clean_signals.py --dry-run

# Actually clean (requires confirmation)
python util_scripts/clean_signals.py
```

**Use cases**:
- Before testing UI with fresh signals
- After major strategy changes
- When resetting the system

---

## Test Scripts

### `test_phase1_core.py`
**Purpose**: Core Phase 1 unit tests

**What it tests**:
- Strategy implementations
- Core models
- Registry functionality

**Usage**:
```bash
python util_scripts/test_phase1_core.py
```

---

### `test_phase2_integration.py`
**Purpose**: Phase 2 integration tests

**What it tests**:
- Filter pipeline integration
- Signal generation end-to-end
- Multi-strategy scanning

**Usage**:
```bash
python util_scripts/test_phase2_integration.py
```

---

## Quick Reference

### Before Testing UI:
```bash
# 1. Verify system is ready
python util_scripts/verify_phase1.py

# 2. Clean old signals
python util_scripts/clean_signals.py

# 3. Run fresh scan
python cli/run_phase2_scan.py

# 4. Test UI!
```

### After Code Changes:
```bash
# 1. Verify changes
python util_scripts/verify_phase1.py

# 2. Run tests
pytest tests/test_*.py -v

# 3. Clean and rescan
python util_scripts/clean_signals.py
python cli/run_phase2_scan.py
```

### System Health Check:
```bash
# Check setup
python util_scripts/verify_setup.py

# Check Phase 1
python util_scripts/verify_phase1.py

# Check Phase 2
python util_scripts/verify_phase2.py

# Check memory optimization
python util_scripts/verify_memory_optimization.py
```

---

## Script Summary

| Script | Purpose | Safe to Run | Output |
|--------|---------|-------------|--------|
| `verify_phase1.py` | ✅ Verify Phase 1 | Yes | Pass/Fail checks |
| `verify_phase2.py` | ✅ Verify Phase 2 | Yes | Pass/Fail checks |
| `verify_setup.py` | ✅ Verify setup | Yes | System status |
| `verify_memory_optimization.py` | ✅ Check memory | Yes | Memory stats |
| `clean_signals.py` | ⚠️ Clean Redis | **Requires confirmation** | Keys deleted |
| `test_phase1_core.py` | ✅ Run tests | Yes | Test results |
| `test_phase2_integration.py` | ✅ Run tests | Yes | Test results |

---

## Notes

### Safety:
- All verification scripts are **safe** to run anytime
- Test scripts are **safe** to run anytime
- `clean_signals.py` **requires confirmation** and **deletes data** (but preserves CHAIN:* data)

### When to Use:
- **verify_phase1.py**: After installation, after code changes, before deployment
- **clean_signals.py**: Before UI testing, after strategy changes, when resetting
- **verify_setup.py**: Initial setup, troubleshooting environment issues
- **test scripts**: During development, before commits

### Exit Codes:
- `0` = Success
- `1` = Failure (verification failed or user cancelled)

---

## Adding New Scripts

When adding new utility scripts to this folder:

1. **Name clearly**: `verb_noun.py` (e.g., `verify_filters.py`, `clean_cache.py`)
2. **Add help text**: Use `argparse` with `--help` support
3. **Document here**: Update this README with script details
4. **Make executable**: `chmod +x util_scripts/your_script.py`
5. **Test it**: Run and verify it works as expected

---

## See Also

- `/cli/` - Production CLI scripts (run_phase2_scan.py, etc.)
- `/tests/` - Full test suite (pytest-based)
- `verify_phase1.py` - **Recommended** for Phase 1 verification

---

**Last Updated**: 2026-04-07
