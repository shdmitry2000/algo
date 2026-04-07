"""
Open Trade — Phase 3 Simulation Tests.

All tests use MockOrderExecutor — no real broker connections.
Uses test fixtures from tests/strategies/test_fixtures.py.
"""
import sys
import os
import time
import pytest
from unittest.mock import patch, MagicMock

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from datagathering.models import StandardOptionTick
from datagathering.providers.base_provider import BaseProvider
from filters.phase2strat1.chain_index import ChainIndex
from filters.phase2strat1.strategies import (
    IronCondorStrategy,
    StrategyCandidate,
)
from open_trade.models import (
    TradeSession,
    TradeSessionState,
    OrderAttempt,
    OrderStatus,
    StrategySubset,
    ProfitabilityScore,
    get_allowed_strategy_types,
    IC_FAMILY_TYPES,
    BF_FAMILY_TYPES,
)
from open_trade.executors.mock_executor import MockOrderExecutor, MockFillBehavior
from open_trade.executors.base_executor import OrderExecutionError
from open_trade.profitability_index import (
    compute_moneyness_score,
    score_candidate,
    scan_and_rank_strategies,
)
from open_trade.data_refresh import DataRefreshService
from open_trade.strategies.arbitrage import (
    ArbitrageStrategy,
    select_starting_side,
    extract_spread_legs,
    compute_spread_limit_price,
)
from open_trade.runner import StrategyRunner

# Reuse existing test fixtures
from tests.strategies.test_fixtures import (
    get_test_chain,
    get_test_dte,
    TEST_CHAIN_BUY,
    TEST_CHAIN_SELL,
)


# ===== FIXTURES =====

class MockProvider(BaseProvider):
    """Mock provider that returns hardcoded chain data."""

    def __init__(self, chain_type: str = "buy"):
        self._chain_type = chain_type
        self.fetch_count = 0

    @property
    def name(self) -> str:
        return "mock_provider"

    def fetch_chain(self, ticker: str):
        self.fetch_count += 1
        ticks, _ = get_test_chain(self._chain_type)
        return ticks


def make_chain_index(chain_type: str = "buy") -> ChainIndex:
    """Build a ChainIndex from test data."""
    ticks, exp = get_test_chain(chain_type)
    data = TEST_CHAIN_BUY if chain_type == "buy" else TEST_CHAIN_SELL
    return ChainIndex(data["symbol"], exp, ticks)


# ===== TEST 1: Models =====

class TestModels:
    def test_trade_session_create(self):
        session = TradeSession.create("AAPL", "2026-04-30")
        assert session.symbol == "AAPL"
        assert session.expiration == "2026-04-30"
        assert session.state == TradeSessionState.INITIAL.value
        assert session.signal_id is None
        assert session.started_at is not None

    def test_trade_session_state_transitions(self):
        session = TradeSession.create("AAPL", "2026-04-30")
        session.set_state(TradeSessionState.FIRST_SPREAD)
        assert session.state == "first_spread"
        assert session.completed_at is None  # Not terminal

        session.set_state(TradeSessionState.COMPLETED)
        assert session.state == "completed"
        assert session.completed_at is not None  # Terminal state

    def test_trade_session_serialization(self):
        session = TradeSession.create("AAPL", "2026-04-30")
        json_str = session.to_json()
        restored = TradeSession.from_json(json_str)
        assert restored.symbol == "AAPL"
        assert restored.session_id == session.session_id

    def test_order_attempt_create(self):
        legs = [{"strike": 95.0, "right": "C", "open_action": "BUY", "quantity": 1}]
        attempt = OrderAttempt.create("IC_BUY", "call", legs, 5.00)
        assert attempt.strategy_type == "IC_BUY"
        assert attempt.spread_side == "call"
        assert attempt.limit_price == 5.00
        assert attempt.status == OrderStatus.PENDING.value

    def test_strategy_subset_filter(self):
        assert get_allowed_strategy_types(StrategySubset.ALL) is None
        ic_types = get_allowed_strategy_types(StrategySubset.IC_FAMILY)
        assert "IC_BUY" in ic_types
        assert "BF_BUY" not in ic_types
        bf_types = get_allowed_strategy_types(StrategySubset.BF_FAMILY)
        assert "BF_BUY" in bf_types
        assert "IC_BUY" not in bf_types

    def test_session_record_fill(self):
        session = TradeSession.create("AAPL", "2026-04-30")
        legs = [{"strike": 95.0, "right": "C", "open_action": "BUY", "quantity": 1}]
        attempt = OrderAttempt.create("IC_BUY", "call", legs, 5.00)
        attempt.fill_price = 4.95
        attempt.filled_at = "2026-04-01T10:00:00"
        session.record_fill(attempt)
        assert session.has_fills()
        assert len(session.filled_spreads) == 1


# ===== TEST 2: Mock Executor =====

class TestMockExecutor:
    def test_immediate_fill(self):
        executor = MockOrderExecutor(
            default_behavior=MockFillBehavior(fill_after_checks=0)
        )
        legs = [{"strike": 95.0, "right": "C", "open_action": "BUY", "quantity": 1}]
        order_id = executor.place_spread_order("AAPL", "2026-04-30", legs, 5.00)
        status = executor.check_order_status(order_id)
        assert status.status == OrderStatus.FILLED

    def test_delayed_fill(self):
        executor = MockOrderExecutor(
            default_behavior=MockFillBehavior(fill_after_checks=3)
        )
        legs = [{"strike": 95.0, "right": "C", "open_action": "BUY", "quantity": 1}]
        order_id = executor.place_spread_order("AAPL", "2026-04-30", legs, 5.00)

        # First 2 checks: still pending
        for _ in range(2):
            status = executor.check_order_status(order_id)
            assert status.status == OrderStatus.PENDING

        # 3rd check: filled
        status = executor.check_order_status(order_id)
        assert status.status == OrderStatus.FILLED

    def test_rejection(self):
        executor = MockOrderExecutor(
            default_behavior=MockFillBehavior(reject=True)
        )
        legs = [{"strike": 95.0, "right": "C", "open_action": "BUY", "quantity": 1}]
        with pytest.raises(OrderExecutionError):
            executor.place_spread_order("AAPL", "2026-04-30", legs, 5.00)

    def test_cancel(self):
        executor = MockOrderExecutor(
            default_behavior=MockFillBehavior(fill_after_checks=100)
        )
        legs = [{"strike": 95.0, "right": "C", "open_action": "BUY", "quantity": 1}]
        order_id = executor.place_spread_order("AAPL", "2026-04-30", legs, 5.00)
        assert executor.cancel_order(order_id) is True
        status = executor.check_order_status(order_id)
        assert status.status == OrderStatus.CANCELLED

    def test_behavior_sequence(self):
        executor = MockOrderExecutor()
        executor.set_behavior_sequence([
            MockFillBehavior(fill_after_checks=0),  # First order: immediate fill
            MockFillBehavior(fill_after_checks=100),  # Second order: never fill
        ])
        legs = [{"strike": 95.0, "right": "C", "open_action": "BUY", "quantity": 1}]

        # First order fills
        id1 = executor.place_spread_order("AAPL", "2026-04-30", legs, 5.00)
        assert executor.check_order_status(id1).status == OrderStatus.FILLED

        # Second stays pending
        id2 = executor.place_spread_order("AAPL", "2026-04-30", legs, 5.00)
        assert executor.check_order_status(id2).status == OrderStatus.PENDING


# ===== TEST 3: Profitability Index =====

class TestProfitabilityIndex:
    def test_moneyness_score(self):
        # Deep ITM (strikes at 80–90, ATM at 100)
        deep_itm = compute_moneyness_score([80.0, 90.0], 100.0)
        # Near ATM (strikes at 95–105, ATM at 100)
        near_atm = compute_moneyness_score([95.0, 105.0], 100.0)
        assert deep_itm > near_atm

    def test_scan_and_rank(self):
        chain_idx = make_chain_index("buy")
        dte = get_test_dte()
        scores = scan_and_rank_strategies(chain_idx, dte)
        # Should find at least one viable strategy
        assert len(scores) > 0
        # Scores should be sorted descending
        for i in range(len(scores) - 1):
            assert scores[i].combined_rank >= scores[i + 1].combined_rank


# ===== TEST 4: Starting Side Selection =====

class TestStartingSide:
    def test_call_side_deep_itm(self):
        """Strikes below ATM → start with calls."""
        chain_idx = make_chain_index("buy")
        dte = get_test_dte()
        ic_scanner = IronCondorStrategy()
        candidates = ic_scanner.scan(chain_idx, dte, 0.65, 0.01)
        if candidates:
            # Find a candidate with strikes below ATM
            for c in candidates:
                center = (min(c.strikes_used) + max(c.strikes_used)) / 2.0
                if center < 100.0:
                    side = select_starting_side(c, 100.0)
                    assert side == "call"
                    break

    def test_put_side_deep_itm(self):
        """Strikes above ATM → start with puts."""
        chain_idx = make_chain_index("buy")
        dte = get_test_dte()
        ic_scanner = IronCondorStrategy()
        candidates = ic_scanner.scan(chain_idx, dte, 0.65, 0.01)
        if candidates:
            for c in candidates:
                center = (min(c.strikes_used) + max(c.strikes_used)) / 2.0
                if center > 100.0:
                    side = select_starting_side(c, 100.0)
                    assert side == "put"
                    break


# ===== TEST 5: Spread Leg Extraction =====

class TestSpreadLegs:
    def test_extract_call_legs(self):
        chain_idx = make_chain_index("buy")
        dte = get_test_dte()
        ic_scanner = IronCondorStrategy()
        candidates = ic_scanner.scan(chain_idx, dte, 0.65, 0.01)
        if candidates:
            c = candidates[0]
            call_legs = extract_spread_legs(c, "call")
            assert all(leg["right"] == "C" for leg in call_legs)

    def test_extract_put_legs(self):
        chain_idx = make_chain_index("buy")
        dte = get_test_dte()
        ic_scanner = IronCondorStrategy()
        candidates = ic_scanner.scan(chain_idx, dte, 0.65, 0.01)
        if candidates:
            c = candidates[0]
            put_legs = extract_spread_legs(c, "put")
            assert all(leg["right"] == "P" for leg in put_legs)

    def test_limit_price_positive(self):
        chain_idx = make_chain_index("buy")
        dte = get_test_dte()
        ic_scanner = IronCondorStrategy()
        candidates = ic_scanner.scan(chain_idx, dte, 0.65, 0.01)
        if candidates:
            c = candidates[0]
            call_legs = extract_spread_legs(c, "call")
            price = compute_spread_limit_price(call_legs)
            assert price > 0


# ===== TEST 6: Data Refresh Service =====

class TestDataRefresh:
    def test_refresh_increments_count(self):
        provider = MockProvider("buy")
        drs = DataRefreshService(provider)
        assert drs.refresh_count == 0
        # Patch push_chain to avoid Redis dependency
        with patch("open_trade.data_refresh.push_chain"), \
             patch("open_trade.data_refresh.get_chain"):
            chain_idx = drs.refresh_chain("TEST_BUY", "2026-04-30")
        assert drs.refresh_count == 1
        assert provider.fetch_count == 1


# ===== TEST 7: Happy Path Full Open =====

class TestHappyPath:
    @patch("open_trade.strategies.arbitrage.time.sleep", return_value=None)
    @patch("open_trade.data_refresh.push_chain")
    @patch("open_trade.data_refresh.get_chain")
    def test_full_open_immediate_fills(self, mock_get_chain, mock_push_chain, mock_sleep):
        """Both spreads fill immediately → session completed."""
        executor = MockOrderExecutor(
            default_behavior=MockFillBehavior(fill_after_checks=0)
        )
        provider = MockProvider("buy")

        runner = StrategyRunner(
            executor=executor,
            provider=provider,
            config={
                "initial_timeout_seconds": 10,
                "poll_interval_seconds": 0.01,
                "fallback_wait_seconds": 1,
                "fee_per_leg": 0.65,
                "spread_cap_bound": 0.01,
                "max_fallback_cycles": 5,
            },
        )

        session = runner.run_from_params("TEST_BUY", "2026-04-30")

        assert session.state == TradeSessionState.COMPLETED.value
        assert len(session.filled_spreads) == 2
        assert session.completed_at is not None
        assert len(executor.order_history) >= 2


# ===== TEST 8: First Leg Timeout =====

class TestTimeout:
    @patch("open_trade.strategies.arbitrage.time.sleep", return_value=None)
    @patch("open_trade.data_refresh.push_chain")
    @patch("open_trade.data_refresh.get_chain")
    def test_first_leg_timeout(self, mock_get_chain, mock_push_chain, mock_sleep):
        """No fills within timeout → session timeout."""
        executor = MockOrderExecutor(
            default_behavior=MockFillBehavior(fill_after_checks=999, fill_probability=0.0)
        )
        provider = MockProvider("buy")

        runner = StrategyRunner(
            executor=executor,
            provider=provider,
            config={
                "initial_timeout_seconds": 0.1,  # Very short for test
                "poll_interval_seconds": 0.01,
                "fallback_wait_seconds": 0.1,
                "fee_per_leg": 0.65,
                "spread_cap_bound": 0.01,
                "max_fallback_cycles": 3,
            },
        )

        session = runner.run_from_params("TEST_BUY", "2026-04-30")

        assert session.state == TradeSessionState.TIMEOUT.value
        assert not session.has_fills()


# ===== TEST 9: IC Subset Only =====

class TestSubsets:
    @patch("open_trade.strategies.arbitrage.time.sleep", return_value=None)
    @patch("open_trade.data_refresh.push_chain")
    @patch("open_trade.data_refresh.get_chain")
    def test_ic_subset(self, mock_get_chain, mock_push_chain, mock_sleep):
        """IC subset → only IC family strategies tried."""
        executor = MockOrderExecutor(
            default_behavior=MockFillBehavior(fill_after_checks=0)
        )
        provider = MockProvider("buy")

        runner = StrategyRunner(
            executor=executor,
            provider=provider,
            config={
                "initial_timeout_seconds": 10,
                "poll_interval_seconds": 0.01,
                "fallback_wait_seconds": 1,
                "fee_per_leg": 0.65,
                "spread_cap_bound": 0.01,
                "max_fallback_cycles": 5,
            },
        )

        session = runner.run_from_params(
            "TEST_BUY", "2026-04-30", subset=StrategySubset.IC_FAMILY
        )

        # If completed, should be an IC strategy
        if session.state == TradeSessionState.COMPLETED.value:
            assert session.current_strategy_type is not None
            assert any(
                session.current_strategy_type.startswith(prefix)
                for prefix in ("IC_", "SHIFTED_IC_")
            )


# ===== TEST 10: Data Refresh After Order =====

class TestDataRefreshDuringTrade:
    @patch("open_trade.strategies.arbitrage.time.sleep", return_value=None)
    @patch("open_trade.data_refresh.push_chain")
    @patch("open_trade.data_refresh.get_chain")
    def test_data_refresh_called(self, mock_get_chain, mock_push_chain, mock_sleep):
        """Verify data is refreshed during polling."""
        executor = MockOrderExecutor(
            default_behavior=MockFillBehavior(fill_after_checks=0)
        )
        provider = MockProvider("buy")

        runner = StrategyRunner(
            executor=executor,
            provider=provider,
            config={
                "initial_timeout_seconds": 10,
                "poll_interval_seconds": 0.01,
                "fallback_wait_seconds": 1,
                "fee_per_leg": 0.65,
                "spread_cap_bound": 0.01,
                "max_fallback_cycles": 5,
            },
        )

        session = runner.run_from_params("TEST_BUY", "2026-04-30")
        # Provider should have been called at least once for initial data
        assert provider.fetch_count >= 1


# ===== TEST 11: CLI Entry Point =====

class TestCLIEntry:
    @patch("open_trade.strategies.arbitrage.time.sleep", return_value=None)
    @patch("open_trade.data_refresh.push_chain")
    @patch("open_trade.data_refresh.get_chain")
    def test_run_from_params_works(self, mock_get_chain, mock_push_chain, mock_sleep):
        """Verify run_from_params works without Phase 2 signal."""
        executor = MockOrderExecutor(
            default_behavior=MockFillBehavior(fill_after_checks=0)
        )
        provider = MockProvider("buy")

        runner = StrategyRunner(executor=executor, provider=provider, config={
            "initial_timeout_seconds": 10,
            "poll_interval_seconds": 0.01,
            "fallback_wait_seconds": 1,
            "fee_per_leg": 0.65,
            "spread_cap_bound": 0.01,
            "max_fallback_cycles": 5,
        })

        session = runner.run_from_params("TEST_BUY", "2026-04-30")
        assert session.symbol == "TEST_BUY"
        assert session.signal_id is None  # No phase 2 signal
        assert session.state in (
            TradeSessionState.COMPLETED.value,
            TradeSessionState.TIMEOUT.value,
            TradeSessionState.FAILED.value,
        )


# ===== TEST 12: Mid Price Movement =====

class TestMidPriceMovement:
    def test_mock_executor_tracks_operations(self):
        """Verify mock executor records all operations for assertions."""
        executor = MockOrderExecutor(
            default_behavior=MockFillBehavior(fill_after_checks=0, price_improvement=0.05)
        )
        legs = [{"strike": 95.0, "right": "C", "open_action": "BUY", "quantity": 1}]

        order_id = executor.place_spread_order("AAPL", "2026-04-30", legs, 5.00)
        status = executor.check_order_status(order_id)

        assert status.status == OrderStatus.FILLED
        assert status.fill_price == 4.95  # 5.00 - 0.05 improvement
        assert len(executor.order_history) == 1


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
