"""
Basic unit tests for Phase 2 signal engine.
"""
import pytest
from filters.phase2strat1.spread_math import apply_spread_cap
from filters.phase2strat1.chain_index import compute_dte
from filters.phase2strat1.bed import compute_rank_score
from filters.phase2strat1.models import Signal, Leg
from datetime import date


def test_spread_cap():
    """Test spread cap boundary conditions."""
    # Normal case
    assert apply_spread_cap(5.0, 10.0, 0.01) == 5.0
    
    # Cap at upper bound
    assert apply_spread_cap(10.0, 10.0, 0.01) == 9.99
    
    # Cap at lower bound
    assert apply_spread_cap(0.0, 10.0, 0.01) == 0.01
    assert apply_spread_cap(-1.0, 10.0, 0.01) == 0.01
    
    # Edge: exactly at bounds
    assert apply_spread_cap(0.01, 10.0, 0.01) == 0.01
    assert apply_spread_cap(9.99, 10.0, 0.01) == 9.99


def test_compute_dte():
    """Test DTE calculation."""
    today = date.today()
    
    # Today
    assert compute_dte(today.isoformat()) == 0
    
    # Future
    future = date(today.year, 12, 31)
    dte = compute_dte(future.isoformat())
    assert dte >= 0
    
    # Invalid format returns 0
    assert compute_dte("invalid") == 0


def test_bed_formula():
    """Test BED calculation via compute_rank_score."""
    # Mock signal
    signal = Signal(
        signal_id="test",
        symbol="TEST",
        expiration="2024-12-31",
        structure_kind="IC",
        open_side="buy",
        structure_label="IC (buy)",
        dte=30,
        strike_difference=10.0,
        legs=[],
        mid_entry=5.0,
        spread_cost=5.0,
        net_credit=-5.0,
        fees_total=2.6,
        fee_per_leg=0.65,
        leg_count=4,
        remaining_profit=2.4,
        remaining_percent=0.24,
        break_even_days=365 * 0.24,  # ~87.6
        bed_filter_pass=True,
        liquidity_pass=True,
        liquidity_detail="pass",
        structural_pass=True,
        rank_score=0.0,
        run_id=None,
        computed_at="2024-01-01T00:00:00"
    )
    
    # BED = 365 * remaining_percent = 365 * 0.24 = 87.6
    assert abs(signal.break_even_days - 87.6) < 0.1
    
    # Rank score = BED / max(DTE, 1) = 87.6 / 30 = 2.92
    score = compute_rank_score(signal)
    assert abs(score - 2.92) < 0.1


def test_bed_filter_condition():
    """Test BED filter pass/fail."""
    # Pass: DTE < BED
    signal_pass = Signal(
        signal_id="pass",
        symbol="TEST",
        expiration="2024-12-31",
        structure_kind="IC",
        open_side="buy",
        structure_label="IC (buy)",
        dte=30,
        strike_difference=10.0,
        legs=[],
        mid_entry=5.0,
        spread_cost=5.0,
        net_credit=-5.0,
        fees_total=2.6,
        fee_per_leg=0.65,
        leg_count=4,
        remaining_profit=2.4,
        remaining_percent=0.24,
        break_even_days=87.6,  # > 30
        bed_filter_pass=False,
        liquidity_pass=True,
        liquidity_detail="pass",
        structural_pass=True,
        rank_score=0.0,
        run_id=None,
        computed_at="2024-01-01T00:00:00"
    )
    
    # Should pass: 30 < 87.6
    assert signal_pass.dte < signal_pass.break_even_days
    
    # Fail: DTE >= BED
    signal_fail = Signal(
        signal_id="fail",
        symbol="TEST",
        expiration="2024-12-31",
        structure_kind="IC",
        open_side="buy",
        structure_label="IC (buy)",
        dte=100,
        strike_difference=10.0,
        legs=[],
        mid_entry=5.0,
        spread_cost=5.0,
        net_credit=-5.0,
        fees_total=2.6,
        fee_per_leg=0.65,
        leg_count=4,
        remaining_profit=2.4,
        remaining_percent=0.24,
        break_even_days=87.6,  # < 100
        bed_filter_pass=False,
        liquidity_pass=True,
        liquidity_detail="pass",
        structural_pass=True,
        rank_score=0.0,
        run_id=None,
        computed_at="2024-01-01T00:00:00"
    )
    
    # Should fail: 100 >= 87.6
    assert signal_fail.dte >= signal_fail.break_even_days


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
