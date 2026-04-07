# Quick Command Reference

## ⚡ Common Commands (Updated Paths)

All utility scripts are now in `util_scripts/` folder.

---

## Before UI Testing:

```bash
# 1. Verify system is ready
python util_scripts/verify_phase1.py

# 2. Check what would be deleted (dry run)
python util_scripts/clean_signals.py --dry-run

# 3. Clean Redis (requires confirmation)
python util_scripts/clean_signals.py

# 4. Run fresh scan
python cli/run_phase2_scan.py

# 5. Start UI and test!
```

---

## Daily Development:

```bash
# Quick verification
python util_scripts/verify_phase1.py

# Run all tests
pytest tests/test_*.py -v

# Clean and rescan
python util_scripts/clean_signals.py
python cli/run_phase2_scan.py
```

---

## System Health Check:

```bash
# Check setup
python util_scripts/verify_setup.py

# Check Phase 1
python util_scripts/verify_phase1.py

# Check Phase 2
python util_scripts/verify_phase2.py

# Check memory
python util_scripts/verify_memory_optimization.py
```

---

## Redis Operations:

```bash
# Dry run (safe - see what would be deleted)
python util_scripts/clean_signals.py --dry-run

# Actually clean (asks for confirmation)
python util_scripts/clean_signals.py

# View Redis keys
redis-cli KEYS "*"
redis-cli KEYS "SIGNAL:*"
redis-cli KEYS "CHAIN:*"
```

---

## Testing:

```bash
# All tests
pytest tests/test_*.py -v

# Specific test files
pytest tests/test_iron_condor.py -v
pytest tests/test_integration.py -v
pytest tests/test_filter_integration.py -v

# Phase 1 core tests
python util_scripts/test_phase1_core.py

# Phase 2 integration
python util_scripts/test_phase2_integration.py
```

---

## Useful Aliases (Optional):

Add these to your `~/.zshrc` or `~/.bashrc`:

```bash
# Navigate to project
alias algo='cd /Users/dmitrysh/code/algotrade/algo'

# Quick verification
alias verify='python util_scripts/verify_phase1.py'

# Clean Redis
alias clean-redis='python util_scripts/clean_signals.py'

# Run scan
alias scan='python cli/run_phase2_scan.py'

# Run tests
alias test-all='pytest tests/test_*.py -v'
```

Then reload: `source ~/.zshrc`

---

## File Locations:

```
/Users/dmitrysh/code/algotrade/algo/
├── util_scripts/          # ← All utility scripts here
│   ├── verify_phase1.py
│   ├── clean_signals.py
│   └── ...
├── cli/                   # ← Production scripts
│   └── run_phase2_scan.py
└── tests/                 # ← Test suite
    ├── test_iron_condor.py
    ├── test_integration.py
    └── ...
```

---

## Common Mistakes:

### ❌ Wrong:
```bash
python clean_signals.py          # Old location
python verify_phase1.py          # Old location
```

### ✅ Correct:
```bash
python util_scripts/clean_signals.py
python util_scripts/verify_phase1.py
```

---

## Quick Test:

```bash
# This should work:
cd /Users/dmitrysh/code/algotrade/algo
python util_scripts/verify_phase1.py
```

If you get "No such file", you might be in the wrong directory. Use `pwd` to check.

---

**Last Updated**: 2026-04-07  
**Scripts Location**: `util_scripts/`
