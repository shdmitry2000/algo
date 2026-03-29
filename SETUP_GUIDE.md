# System Setup Guide

Quick guide to get the algorithmic trading system running.

---

## Step 1: Clone and Setup

```bash
# Navigate to project
cd /Users/dmitrysh/code/algotrade/algo

# Install dependencies
pip install -r requirements.txt
```

---

## Step 2: Configure Environment

```bash
# Copy example configuration
cp .env.example .env

# Edit with your credentials (optional)
nano .env
```

### Quick Start (No Credentials)

For immediate testing, use the default yfinance provider:

```bash
# .env
DATA_PROVIDER=yfinance
REDIS_HOST=127.0.0.1
REDIS_PORT=6379
```

That's it! No other configuration needed.

---

## Step 3: Start Redis

```bash
# Start Redis server
redis-server

# Or if using Homebrew on macOS:
brew services start redis

# Verify Redis is running
redis-cli ping
# Should return: PONG
```

---

## Step 4: Run Tests

```bash
# Run all tests (strategies + providers)
python tests/run_all_tests.py

# Expected output:
# 13 suites, 83 tests, 100% passing
```

---

## Step 5: Run Phase 2 Scan

```bash
# Run a single scan
python cli/run_phase2_scan.py

# Check results in Redis
redis-cli
> KEYS signal:*
> GET signal:SPY:2026-05-15:20260329120000
```

---

## Provider Configuration

### Option 1: YFinance (Default - No Setup)

Already configured! Just use it:

```bash
export DATA_PROVIDER=yfinance
python cli/run_phase2_scan.py
```

**Pros**:
- Free
- No credentials
- Works immediately

**Cons**:
- ~15 minute delay
- Lower data quality

---

### Option 2: Tradier (Recommended for Testing)

```bash
# 1. Get free sandbox token
# Go to: https://developer.tradier.com
# Sign up → Create App → Get Sandbox Token

# 2. Add to .env
echo "TRADIER_ACCESS_TOKEN=your_sandbox_token" >> .env
echo "TRADIER_SANDBOX=true" >> .env

# 3. Test it
python tests/providers/test_live_providers.py --provider tradier

# 4. Use it
export DATA_PROVIDER=tradier
python cli/run_phase2_scan.py
```

**Pros**:
- Real-time data
- Free sandbox
- Production-like behavior
- Excellent quality

**Cons**:
- Requires registration
- Needs token management

---

### Option 3: Theta (Recommended for Production)

```bash
# 1. Get ThetaData account
# Go to: https://thetadata.com
# Subscribe to plan

# 2. Install SDK
pip install thetadata

# 3. Add to .env
echo "THETA_USERNAME=your_username" >> .env
echo "THETA_PASSWORD=your_password" >> .env

# 4. Test it
python tests/providers/test_live_providers.py --provider theta

# 5. Use it
export DATA_PROVIDER=theta
python cli/run_phase2_scan.py
```

**Pros**:
- Professional-grade data
- Real-time
- Excellent quality
- High reliability

**Cons**:
- Paid subscription
- Requires credentials

---

## Verify Installation

### Check Python Dependencies
```bash
python -c "import redis; import dotenv; print('✅ Core dependencies OK')"

# Optional: Check provider dependencies
python -c "import yfinance; print('✅ yfinance OK')"
python -c "import requests; print('✅ requests OK (for tradier)')"
python -c "import thetadata; print('✅ thetadata OK')"
```

### Check Redis Connection
```bash
python -c "
import redis
r = redis.Redis(host='127.0.0.1', port=6379)
r.ping()
print('✅ Redis connection OK')
"
```

### Check Provider Configuration
```bash
python -c "
import os
from dotenv import load_dotenv
load_dotenv()
provider = os.getenv('DATA_PROVIDER', 'yfinance')
print(f'✅ Provider set to: {provider}')
"
```

---

## Run the System

### Development Mode (Manual Scan)
```bash
# Single scan
python cli/run_phase2_scan.py

# View signals in Redis
redis-cli KEYS signal:*
```

### Production Mode (Scheduled)
```bash
# Start all services (pipeline + web API)
./start_all.sh

# Check status
./stop_all.sh
```

---

## Testing

### Test Providers
```bash
# Stub tests (no credentials)
python tests/providers/test_all_providers.py
# Output: 14 tests passing

# Live test (with credentials)
python tests/providers/test_live_providers.py --provider yfinance
```

### Test Strategies
```bash
# All strategy tests
python tests/strategies/run_all_tests.py
# Output: 69 tests passing
```

### Test Everything
```bash
# Complete system test
python tests/run_all_tests.py
# Output: 83 tests passing
```

---

## Troubleshooting

### Redis Not Running
```bash
# Error: "Connection refused" or "Redis not available"

# Fix: Start Redis
redis-server

# Or on macOS with Homebrew:
brew services start redis
```

### Provider Import Error
```bash
# Error: "ModuleNotFoundError: No module named 'yfinance'"

# Fix: Install dependency
pip install yfinance
```

### Tradier 401 Unauthorized
```bash
# Error: "401: Unauthorized"

# Fix: Check token in .env
cat .env | grep TRADIER_ACCESS_TOKEN

# Verify token is valid at:
# https://developer.tradier.com/dashboard
```

### Theta Connection Timeout
```bash
# Error: Connection timeout

# Fix 1: Check credentials
cat .env | grep THETA

# Fix 2: Wait longer (first connection can be slow)
# Wait 60 seconds and retry

# Fix 3: Check ThetaData subscription status
```

### No Signals Generated
```bash
# Issue: Pipeline runs but no signals created

# Check 1: Verify data was fetched
# Should see log: "Fetched X ticks for SYMBOL"

# Check 2: Check BED filter
# Strategies must pass: DTE < BED

# Check 3: Check Redis
redis-cli KEYS signal:*
```

---

## Development Workflow

### 1. Initial Setup (Once)
```bash
cp .env.example .env
pip install -r requirements.txt
redis-server &
```

### 2. Development Cycle
```bash
# Edit code
nano filters/phase2strat1/strategies/iron_condor.py

# Run tests
python tests/run_all_tests.py

# Run pipeline
python cli/run_phase2_scan.py

# Check results
redis-cli KEYS signal:*
```

### 3. Before Commit
```bash
# Run all tests
python tests/run_all_tests.py

# Verify no errors
echo $?  # Should be 0
```

---

## Production Deployment

### 1. Server Setup
```bash
# Install Python 3.9+
python3 --version

# Install Redis
sudo apt install redis-server  # Ubuntu/Debian
brew install redis             # macOS

# Clone repository
git clone <repo_url>
cd algo
```

### 2. Configure Production
```bash
# Copy and edit .env
cp .env.example .env
nano .env

# Set production provider
# DATA_PROVIDER=theta
# THETA_USERNAME=production_username
# THETA_PASSWORD=production_password

# Set Redis
# REDIS_HOST=127.0.0.1
# REDIS_PORT=6379
```

### 3. Install Dependencies
```bash
pip install -r requirements.txt

# Install production provider SDK
pip install thetadata  # If using Theta
```

### 4. Test Production Config
```bash
# Test provider
python tests/providers/test_live_providers.py --provider theta

# Test complete system
python tests/run_all_tests.py
```

### 5. Start Services
```bash
# Start all services
./start_all.sh

# Verify running
ps aux | grep python
```

### 6. Monitor
```bash
# Check logs
tail -f *.log

# Check Redis
redis-cli
> KEYS signal:*
> KEYS history:*

# Check signals count
redis-cli DBSIZE
```

---

## Environment Variables Reference

### Required (Minimum)
```bash
DATA_PROVIDER=yfinance    # Provider selection
REDIS_HOST=127.0.0.1      # Redis host
REDIS_PORT=6379           # Redis port
```

### Provider-Specific

**Tradier**:
```bash
TRADIER_ACCESS_TOKEN=your_token
TRADIER_SANDBOX=true      # Optional: use sandbox
```

**Theta**:
```bash
THETA_USERNAME=your_username
THETA_PASSWORD=your_password
```

**IBKR (Optional)**:
```bash
IBKR_HOST=127.0.0.1
IBKR_PORT=7497
IBKR_CLIENT_ID=1
```

### See `.env.example` for complete list

---

## Quick Commands

```bash
# Setup
cp .env.example .env                              # Configure environment
pip install -r requirements.txt                   # Install dependencies
redis-server &                                    # Start Redis

# Testing
python tests/run_all_tests.py                     # All tests (83)
python tests/providers/test_all_providers.py      # Provider tests (14)
python tests/strategies/run_all_tests.py          # Strategy tests (69)

# Running
python cli/run_phase2_scan.py                     # Single scan
./start_all.sh                                    # Start services
./stop_all.sh                                     # Stop services

# Monitoring
redis-cli KEYS signal:*                           # View signals
redis-cli KEYS history:*                          # View history
tail -f *.log                                     # View logs
```

---

## Next Steps

### After Setup
1. ✅ Run tests: `python tests/run_all_tests.py`
2. ✅ Run scan: `python cli/run_phase2_scan.py`
3. ✅ Check signals: `redis-cli KEYS signal:*`

### For Production
1. Add production provider credentials
2. Run live tests
3. Deploy to server
4. Set up monitoring
5. Configure scheduled scans

### For Phase 3
1. Implement Schwab OAuth
2. Build order execution
3. Create Phase 3 tests
4. Connect to signals

---

## Support

- **Documentation**: See `README.md`, `PROVIDER_QUICKREF.md`
- **Provider Help**: See `tests/providers/README.md`
- **Templates**: See `tests/providers/PROVIDER_TEMPLATES.md`
- **Testing**: See `COMPLETE_SYSTEM_TESTING.md`

---

## Status Checklist

After setup, verify:

- [ ] `.env` file created from `.env.example`
- [ ] Redis running (`redis-cli ping` returns `PONG`)
- [ ] Dependencies installed (`pip list`)
- [ ] Tests passing (`python tests/run_all_tests.py`)
- [ ] Provider configured (check `DATA_PROVIDER` in `.env`)
- [ ] Pipeline runs (`python cli/run_phase2_scan.py`)
- [ ] Signals stored (check `redis-cli KEYS signal:*`)

When all checked: ✅ System ready!

---

**Last Updated**: 2026-03-29  
**Version**: Phase 1 & 2 Complete  
**Status**: ✅ Production Ready
