"""
pytest configuration and shared fixtures.

This file is automatically loaded by pytest and provides:
- Shared fixtures available to all tests
- Test configuration
- Custom marks
"""
import pytest
from tests.fixtures import (
    ic_test_chain,
    bf_test_chain,
    flygonaal_test_chain,
    calendar_test_chain,
    short_dte_chain,
    long_dte_chain,
    wide_spread_chain,
    low_liquidity_chain,
    high_iv_chain,
    narrow_range_chain,
    get_all_test_fixtures,
)


# ============================================================================
# Chain Fixtures
# ============================================================================

@pytest.fixture
def ic_chain():
    """Iron Condor test chain."""
    return ic_test_chain()


@pytest.fixture
def bf_chain():
    """Butterfly test chain."""
    return bf_test_chain()


@pytest.fixture
def flygonaal_chain():
    """Flygonaal test chain."""
    return flygonaal_test_chain()


@pytest.fixture
def calendar_chain():
    """Calendar spread test chain (multi-expiration)."""
    return calendar_test_chain()


@pytest.fixture
def short_dte():
    """Short DTE chain (7 days)."""
    return short_dte_chain()


@pytest.fixture
def long_dte():
    """Long DTE chain (365 days / LEAP)."""
    return long_dte_chain()


@pytest.fixture
def wide_spread():
    """Wide spread chain ($10 strikes)."""
    return wide_spread_chain()


@pytest.fixture
def low_liquidity():
    """Low liquidity chain."""
    return low_liquidity_chain()


@pytest.fixture
def high_iv():
    """High IV chain."""
    return high_iv_chain()


@pytest.fixture
def narrow_range():
    """Narrow range chain."""
    return narrow_range_chain()


@pytest.fixture
def all_chains():
    """All test chains as a dictionary."""
    return get_all_test_fixtures()


# ============================================================================
# Strategy Fixtures
# ============================================================================

@pytest.fixture
def ic_strategy():
    """Iron Condor strategy instance."""
    from strategies.implementations import IronCondorStrategy
    return IronCondorStrategy()


@pytest.fixture
def bf_strategy():
    """Butterfly strategy instance."""
    from strategies.implementations import ButterflyStrategy
    return ButterflyStrategy()


@pytest.fixture
def condor_strategy():
    """Condor strategy instance."""
    from strategies.implementations import CondorStrategy
    return CondorStrategy()


@pytest.fixture
def shifted_strategy():
    """Shifted Condor strategy instance."""
    from strategies.implementations import ShiftedCondorStrategy
    return ShiftedCondorStrategy()


@pytest.fixture
def flygonaal_strategy():
    """Flygonaal strategy instance."""
    from strategies.implementations import FlygonaalStrategy
    return FlygonaalStrategy()


@pytest.fixture
def calendar_strategy():
    """Calendar spread strategy instance."""
    from strategies.implementations import CalendarSpreadStrategy
    return CalendarSpreadStrategy()


# ============================================================================
# Parameter Fixtures
# ============================================================================

@pytest.fixture
def standard_params():
    """Standard test parameters for strategy scanning."""
    return {
        "fee_per_leg": 0.50,
        "spread_cap_bound": 0.01,
        "min_liquidity_bid": 0.05,
        "min_liquidity_ask": 0.05,
    }


@pytest.fixture
def high_fee_params():
    """High fee parameters for edge case testing."""
    return {
        "fee_per_leg": 2.00,
        "spread_cap_bound": 0.01,
        "min_liquidity_bid": 0.05,
        "min_liquidity_ask": 0.05,
    }


@pytest.fixture
def strict_liquidity_params():
    """Strict liquidity parameters."""
    return {
        "fee_per_leg": 0.50,
        "spread_cap_bound": 0.01,
        "min_liquidity_bid": 0.50,
        "min_liquidity_ask": 0.50,
    }


# ============================================================================
# pytest Configuration
# ============================================================================

def pytest_configure(config):
    """Register custom markers."""
    config.addinivalue_line(
        "markers", "unit: Unit tests for individual components"
    )
    config.addinivalue_line(
        "markers", "integration: Integration tests across modules"
    )
    config.addinivalue_line(
        "markers", "slow: Slow-running tests (skip with -m 'not slow')"
    )
    config.addinivalue_line(
        "markers", "adapter: Tests for legacy adapter layer"
    )
