# Provider Stub Templates

Quick reference templates for adding new data providers.

## Table of Contents
1. [Basic Provider Template](#basic-provider-template)
2. [REST API Provider Template](#rest-api-provider-template)
3. [Python SDK Provider Template](#python-sdk-provider-template)
4. [Testing Template](#testing-template)
5. [Common Patterns](#common-patterns)

---

## Basic Provider Template

Minimal provider implementation:

```python
# datagathering/providers/example_provider.py
"""
ExampleProvider - brief description of what this provider does.
"""
import logging
from typing import List
from datagathering.models import StandardOptionTick
from datagathering.providers.base_provider import BaseProvider

logger = logging.getLogger(__name__)


class ExampleProvider(BaseProvider):
    
    @property
    def name(self) -> str:
        return "example"
    
    def fetch_chain(self, ticker: str) -> List[StandardOptionTick]:
        """
        Fetch option chain for the given ticker.
        Returns list of StandardOptionTick.
        """
        logger.warning("[example] Provider not implemented yet")
        return []
```

---

## REST API Provider Template

For providers using REST APIs (like Tradier):

```python
# datagathering/providers/rest_example_provider.py
"""
RestExampleProvider - fetches option chains via REST API.

Environment (.env):
  REST_API_KEY — required; API key from provider
  REST_BASE_URL — optional; override default URL
"""
import os
import logging
import requests
from typing import List, Dict, Any
from dotenv import load_dotenv
from datagathering.models import StandardOptionTick
from datagathering.providers.base_provider import BaseProvider

load_dotenv()
logger = logging.getLogger(__name__)

DEFAULT_BASE_URL = "https://api.example.com/v1"


class RestExampleProvider(BaseProvider):
    
    def __init__(self):
        self.api_key = os.getenv("REST_API_KEY", "").strip()
        self.base_url = os.getenv("REST_BASE_URL", DEFAULT_BASE_URL)
        
        if not self.api_key:
            logger.warning("[rest_example] REST_API_KEY not set in .env")
    
    @property
    def name(self) -> str:
        return "rest_example"
    
    def fetch_chain(self, ticker: str) -> List[StandardOptionTick]:
        """
        Fetch option chain via REST API.
        """
        if not self.api_key:
            logger.error("[rest_example] API key not configured")
            return []
        
        ticks = []
        
        try:
            # 1. Get expirations
            expirations = self._get_expirations(ticker)
            
            # 2. For each expiration, get option chain
            for exp in expirations:
                options = self._get_options_for_expiration(ticker, exp)
                
                # 3. Convert to StandardOptionTick
                for opt in options:
                    tick = self._convert_to_standard_tick(ticker, opt)
                    if tick:
                        ticks.append(tick)
            
            logger.info(f"[rest_example] Fetched {len(ticks)} ticks for {ticker}")
            
        except Exception as e:
            logger.error(f"[rest_example] Error fetching chain for {ticker}: {e}")
        
        return ticks
    
    def _get_expirations(self, ticker: str) -> List[str]:
        """Get list of expiration dates."""
        url = f"{self.base_url}/options/expirations"
        headers = {"Authorization": f"Bearer {self.api_key}"}
        params = {"symbol": ticker}
        
        response = requests.get(url, headers=headers, params=params, timeout=10)
        response.raise_for_status()
        
        data = response.json()
        return data.get("expirations", [])
    
    def _get_options_for_expiration(self, ticker: str, expiration: str) -> List[Dict[str, Any]]:
        """Get all options for a specific expiration."""
        url = f"{self.base_url}/options/chain"
        headers = {"Authorization": f"Bearer {self.api_key}"}
        params = {
            "symbol": ticker,
            "expiration": expiration
        }
        
        response = requests.get(url, headers=headers, params=params, timeout=10)
        response.raise_for_status()
        
        data = response.json()
        return data.get("options", [])
    
    def _convert_to_standard_tick(self, ticker: str, option_data: Dict[str, Any]) -> StandardOptionTick:
        """
        Convert API response to StandardOptionTick.
        
        Example API response:
        {
            "expiration": "2026-05-15",
            "strike": 500.0,
            "type": "call",
            "bid": 10.40,
            "ask": 10.60,
            "volume": 1000,
            "open_interest": 5000
        }
        """
        try:
            return StandardOptionTick.make(
                root=ticker,
                expiration=option_data["expiration"],
                strike=float(option_data["strike"]),
                right="C" if option_data["type"].lower() == "call" else "P",
                bid=float(option_data.get("bid", 0)),
                ask=float(option_data.get("ask", 0)),
                volume=int(option_data.get("volume", 0) or 0),
                open_interest=int(option_data.get("open_interest", 0) or 0),
                provider=self.name
            )
        except (KeyError, ValueError) as e:
            logger.debug(f"[rest_example] Skipping invalid option: {e}")
            return None
```

---

## Python SDK Provider Template

For providers using Python SDKs (like Theta):

```python
# datagathering/providers/sdk_example_provider.py
"""
SdkExampleProvider - uses native Python SDK.

Environment (.env):
  SDK_API_KEY — required; API key
  SDK_SECRET — optional; API secret if needed
"""
import os
import logging
from typing import List
from datetime import date
from dotenv import load_dotenv
from datagathering.models import StandardOptionTick
from datagathering.providers.base_provider import BaseProvider

load_dotenv()
logger = logging.getLogger(__name__)


def _make_client():
    """Create SDK client instance."""
    try:
        from example_sdk import Client
        api_key = os.getenv("SDK_API_KEY", "")
        api_secret = os.getenv("SDK_SECRET", "")
        
        if api_key:
            return Client(api_key=api_key, api_secret=api_secret)
        return Client()  # Use default/demo credentials
        
    except ImportError:
        logger.error("[sdk_example] SDK not installed: pip install example-sdk")
        return None


class SdkExampleProvider(BaseProvider):
    
    @property
    def name(self) -> str:
        return "sdk_example"
    
    def fetch_chain(self, ticker: str) -> List[StandardOptionTick]:
        """
        Fetch option chain using Python SDK.
        """
        ticks = []
        client = _make_client()
        
        if not client:
            logger.error("[sdk_example] Client not available")
            return []
        
        try:
            # 1. Get expirations
            expirations = client.get_expirations(ticker)
            
            # 2. For each expiration
            for exp in expirations:
                # 3. Get strikes
                strikes = client.get_strikes(ticker, exp)
                
                # 4. For each strike and right (call/put)
                for strike in strikes:
                    for right in ["C", "P"]:
                        # 5. Get quote
                        quote = client.get_option_quote(
                            ticker, exp, strike, right
                        )
                        
                        # 6. Convert to StandardOptionTick
                        if quote:
                            tick = StandardOptionTick.make(
                                root=ticker,
                                expiration=str(exp),
                                strike=float(strike),
                                right=right,
                                bid=float(quote.get("bid", 0)),
                                ask=float(quote.get("ask", 0)),
                                volume=int(quote.get("volume", 0) or 0),
                                open_interest=int(quote.get("open_interest", 0) or 0),
                                provider=self.name
                            )
                            ticks.append(tick)
            
            logger.info(f"[sdk_example] Fetched {len(ticks)} ticks for {ticker}")
            
        except Exception as e:
            logger.error(f"[sdk_example] Error fetching chain for {ticker}: {e}")
        
        return ticks
```

---

## Testing Template

Create tests for your new provider:

```python
# tests/providers/test_new_provider.py
"""
Tests for NewProvider - structure and stub validation.
"""
import sys
from pathlib import Path

project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from tests.providers.test_all_providers import create_mock_option_chain


def test_new_provider_structure():
    """Test new provider structure (stub)."""
    try:
        from datagathering.providers.new_provider import NewProvider
    except ImportError:
        print("⚠️  NewProvider not available - SKIPPED")
        return True
    
    provider = NewProvider()
    
    print("Provider details:")
    print(f"  Name: {provider.name}")
    print(f"  Class: {provider.__class__.__name__}")
    print(f"  Has fetch_chain: {hasattr(provider, 'fetch_chain')}")
    
    # Test with mock data
    mock_ticks = create_mock_option_chain("SPY", provider.name)
    
    print(f"\nMock response:")
    print(f"  Total ticks: {len(mock_ticks)}")
    print(f"  Provider: {mock_ticks[0].provider}")
    
    assert mock_ticks[0].provider == provider.name
    
    print("\n✓ Provider structure validated")
    print("✅ PASSED")
    return True


def test_new_provider_api_format():
    """Document expected API response format."""
    print("\nExpected API response:")
    print("""
    {
      "options": [
        {
          "symbol": "SPY",
          "expiration": "2026-05-15",
          "strike": 500.0,
          "type": "call",
          "bid": 10.40,
          "ask": 10.60,
          "volume": 1000,
          "open_interest": 5000
        }
      ]
    }
    """)
    
    print("Mapping to StandardOptionTick:")
    print("  root → symbol")
    print("  expiration → expiration")
    print("  strike → strike")
    print("  right → 'C' if type=='call' else 'P'")
    print("  bid → bid")
    print("  ask → ask")
    print("  volume → volume")
    print("  open_interest → open_interest")
    
    print("\n✓ API format documented")
    print("✅ PASSED")
    return True


if __name__ == "__main__":
    test_new_provider_structure()
    test_new_provider_api_format()
```

---

## Common Patterns

### Pattern 1: Handle Missing API Keys

```python
def __init__(self):
    self.api_key = os.getenv("PROVIDER_API_KEY", "").strip()
    if not self.api_key:
        logger.warning("[provider] PROVIDER_API_KEY not set in .env")

def fetch_chain(self, ticker: str) -> List[StandardOptionTick]:
    if not self.api_key:
        logger.error("[provider] API key not configured")
        return []
    # ... rest of implementation
```

### Pattern 2: Handle Single Item or Array Response

Some APIs return a single object when there's one result, array when multiple:

```python
def _as_list(value: Any) -> List[Any]:
    """Convert single item or array to list."""
    if value is None:
        return []
    if isinstance(value, list):
        return value
    return [value]

# Usage
options = _as_list(response.get("option", []))
```

### Pattern 3: Robust Type Conversion

```python
try:
    tick = StandardOptionTick.make(
        root=ticker,
        expiration=str(data["expiration"]),
        strike=float(data["strike"]),
        right="C" if data["type"].lower() == "call" else "P",
        bid=float(data.get("bid", 0)),
        ask=float(data.get("ask", 0)),
        volume=int(data.get("volume", 0) or 0),  # Handle None
        open_interest=int(data.get("open_interest", 0) or 0),  # Handle None
        provider=self.name
    )
    ticks.append(tick)
except (KeyError, ValueError, TypeError) as e:
    logger.debug(f"[provider] Skipping invalid option: {e}")
    continue
```

### Pattern 4: Request Timeouts

Always set timeouts for API requests:

```python
response = requests.get(url, headers=headers, params=params, timeout=10)
```

### Pattern 5: Environment Configuration

```python
# .env
PROVIDER_API_KEY=your_key_here
PROVIDER_BASE_URL=https://api.example.com
PROVIDER_TIMEOUT=10
PROVIDER_SANDBOX=false

# In provider
from dotenv import load_dotenv
load_dotenv()

api_key = os.getenv("PROVIDER_API_KEY", "")
base_url = os.getenv("PROVIDER_BASE_URL", "https://api.example.com")
timeout = int(os.getenv("PROVIDER_TIMEOUT", "10"))
sandbox = os.getenv("PROVIDER_SANDBOX", "false").lower() in ("1", "true", "yes")
```

### Pattern 6: Logging Best Practices

```python
# Log at appropriate levels
logger.debug(f"[provider] Detailed debug info: {response}")
logger.info(f"[provider] Fetched {len(ticks)} ticks for {ticker}")
logger.warning(f"[provider] Configuration issue: API key not set")
logger.error(f"[provider] Failed to fetch chain: {error}")

# Use provider name as prefix
# [provider] for consistent log filtering
```

---

## Integration Checklist

When adding a new provider:

### Code
- [ ] Create provider class in `datagathering/providers/`
- [ ] Inherit from `BaseProvider`
- [ ] Implement `name` property
- [ ] Implement `fetch_chain()` method
- [ ] Add to `datagathering/pipeline.py::get_provider()`
- [ ] Handle errors gracefully
- [ ] Add logging

### Configuration
- [ ] Document required environment variables
- [ ] Add to `.env.example`
- [ ] Add credentials to `.gitignore` if needed

### Testing
- [ ] Create test file in `tests/providers/`
- [ ] Add structure test (validates interface)
- [ ] Add format test (validates API response mapping)
- [ ] Add to provider test suite
- [ ] Create mock data generator

### Documentation
- [ ] Update provider feature matrix
- [ ] Document API authentication flow
- [ ] Add usage examples
- [ ] Document rate limits if applicable

---

## Example: Adding Interactive Brokers

Step-by-step example of adding IBKR:

### 1. Create Provider

```python
# datagathering/providers/ibkr_provider.py
"""
Interactive Brokers provider via IB API.

Requires:
  - IB Gateway or TWS running
  - ib_insync installed: pip install ib_insync
"""
import logging
from typing import List
from datagathering.models import StandardOptionTick
from datagathering.providers.base_provider import BaseProvider

logger = logging.getLogger(__name__)


class IBKRProvider(BaseProvider):
    
    def __init__(self, host='127.0.0.1', port=7497, client_id=1):
        self.host = host
        self.port = port
        self.client_id = client_id
        self.ib = None
    
    @property
    def name(self) -> str:
        return "ibkr"
    
    def _connect(self):
        """Connect to IB Gateway."""
        if self.ib is None:
            try:
                from ib_insync import IB
                self.ib = IB()
                self.ib.connect(self.host, self.port, clientId=self.client_id)
                logger.info(f"[ibkr] Connected to {self.host}:{self.port}")
            except Exception as e:
                logger.error(f"[ibkr] Connection failed: {e}")
    
    def fetch_chain(self, ticker: str) -> List[StandardOptionTick]:
        """Fetch option chain from IBKR."""
        self._connect()
        
        if not self.ib or not self.ib.isConnected():
            logger.error("[ibkr] Not connected to IB Gateway")
            return []
        
        ticks = []
        
        try:
            from ib_insync import Stock, Option
            
            # 1. Define underlying
            stock = Stock(ticker, 'SMART', 'USD')
            self.ib.qualifyContracts(stock)
            
            # 2. Get option chains
            chains = self.ib.reqSecDefOptParams(
                stock.symbol, '', stock.secType, stock.conId
            )
            
            # 3. For each expiration
            for chain in chains:
                for exp in chain.expirations:
                    for strike in chain.strikes:
                        for right in ['C', 'P']:
                            # 4. Create option contract
                            contract = Option(
                                ticker, exp, strike, right, chain.exchange
                            )
                            
                            # 5. Request market data
                            self.ib.qualifyContracts(contract)
                            ticker_data = self.ib.reqMktData(contract)
                            self.ib.sleep(0.1)  # Rate limit
                            
                            # 6. Convert to StandardOptionTick
                            if ticker_data.bid and ticker_data.ask:
                                tick = StandardOptionTick.make(
                                    root=ticker,
                                    expiration=exp,
                                    strike=float(strike),
                                    right=right,
                                    bid=float(ticker_data.bid),
                                    ask=float(ticker_data.ask),
                                    volume=int(ticker_data.volume or 0),
                                    open_interest=0,  # IBKR doesn't provide real-time OI
                                    provider=self.name
                                )
                                ticks.append(tick)
            
            logger.info(f"[ibkr] Fetched {len(ticks)} ticks for {ticker}")
            
        except Exception as e:
            logger.error(f"[ibkr] Error fetching chain: {e}")
        
        return ticks
```

### 2. Update Pipeline

```python
# datagathering/pipeline.py

def get_provider() -> BaseProvider:
    provider_name = os.getenv("DATA_PROVIDER", "yfinance").lower()
    
    if provider_name == "yfinance":
        from datagathering.providers.yfinance_provider import YFinanceProvider
        return YFinanceProvider()
    
    elif provider_name == "tradier":
        from datagathering.providers.tradier_provider import TradierProvider
        return TradierProvider()
    
    elif provider_name == "theta":
        from datagathering.providers.theta_provider import ThetaProvider
        return ThetaProvider()
    
    elif provider_name == "ibkr":
        from datagathering.providers.ibkr_provider import IBKRProvider
        return IBKRProvider()
    
    else:
        logger.warning(f"Unknown provider {provider_name}, using yfinance")
        from datagathering.providers.yfinance_provider import YFinanceProvider
        return YFinanceProvider()
```

### 3. Add Tests

```python
# tests/providers/test_all_providers.py

# In imports section:
try:
    from datagathering.providers.ibkr_provider import IBKRProvider
    providers_available['ibkr'] = IBKRProvider
except ImportError as e:
    print(f"⚠️  IBKR provider not available: {e}")
    providers_available['ibkr'] = None

# Add test function:
def test_ibkr_provider_stub():
    """Test IBKR provider structure (stub)."""
    print("\n" + "="*80)
    print("TEST: IBKR Provider Structure (STUB)")
    print("="*80)
    
    if not providers_available['ibkr']:
        print("⚠️  IBKR provider not available - SKIPPED")
        return True
    
    provider = providers_available['ibkr']()
    
    print("Provider details:")
    print(f"  Name: {provider.name}")
    print(f"  Primary Role: Data + Order Execution")
    
    mock_ticks = create_mock_option_chain("SPY", provider.name)
    assert mock_ticks[0].provider == "ibkr"
    
    print("✓ IBKR provider structure validated")
    print("✅ PASSED")
    return True

# Add to test suite:
tests = [
    # ... existing tests ...
    ("IBKR Structure (STUB)", test_ibkr_provider_stub),
]
```

### 4. Update Documentation

```markdown
# README.md or feature matrix

| Provider | Status | Type | Notes |
|----------|--------|------|-------|
| ibkr | ⚠️ Stub | Data + Orders | Requires IB Gateway running |
```

---

## Quick Start: Add Your Provider

1. **Copy template** (REST or SDK) to `datagathering/providers/your_provider.py`
2. **Implement `name` property** - return your provider name as string
3. **Implement `fetch_chain()`** - fetch option chain, return `List[StandardOptionTick]`
4. **Add to pipeline** - update `get_provider()` in `datagathering/pipeline.py`
5. **Create tests** - add stub tests to `tests/providers/test_all_providers.py`
6. **Document** - update README with status and requirements
7. **Test** - run `python tests/providers/test_all_providers.py`

---

## Notes

- **Always return `StandardOptionTick`** - this ensures pipeline compatibility
- **Handle errors gracefully** - log errors, return empty list, don't crash
- **Log at appropriate levels** - debug for details, info for success, error for failures
- **Use provider name prefix** - `[provider]` in all log messages
- **Validate credentials** - check API keys/tokens before making requests
- **Set timeouts** - prevent hanging on slow/failed API requests
- **Test without credentials** - use mock data to validate structure
- **Document requirements** - clearly specify what credentials/setup is needed

---

## Related Files

- `datagathering/providers/base_provider.py` - Abstract base class
- `datagathering/models.py` - StandardOptionTick definition
- `datagathering/pipeline.py` - Provider factory and integration
- `tests/providers/test_all_providers.py` - Master test suite
- `tests/providers/README.md` - Testing documentation
