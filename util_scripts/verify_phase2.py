#!/usr/bin/env python3
"""
Quick verification script for Phase 2 implementation.
Checks that all modules import correctly and basic flow works.
"""
import sys
import os

sys.path.insert(0, os.path.dirname(__file__))

def test_imports():
    """Verify all Phase 2 modules import without errors."""
    print("✓ Testing imports...")
    
    try:
        from filters.phase2strat1.scan import run_scan, run_scan_for_symbol
        from filters.phase2strat1.models import Signal, Leg, HistoryEvent, GateStatus
        from filters.phase2strat1.spread_math import apply_spread_cap
        from filters.phase2strat1.precheck import precheck_symbols
        from filters.phase2strat1.chain_index import ChainIndex, compute_dte
        from filters.phase2strat1.strategies import (
            IronCondorStrategy,
            ButterflyStrategy,
            ShiftedCondorStrategy,
            StrategyCandidate
        )
        from filters.phase2strat1.strategies.base import STRATEGY_TYPES
        from storage.signal_cache import (
            set_active_signal,
            get_active_signal,
            list_active_signals,
            get_gate,
            set_gate,
            append_history,
            get_history
        )
        print(f"  ✓ All imports successful")
        print(f"  ✓ {len(STRATEGY_TYPES)} strategy types registered")
        return True
    except Exception as e:
        print(f"  ✗ Import failed: {e}")
        return False


def test_spread_cap():
    """Test spread cap function."""
    print("✓ Testing spread_cap...")
    from filters.phase2strat1.spread_math import apply_spread_cap
    
    assert apply_spread_cap(5.0, 10.0, 0.01) == 5.0, "Normal case failed"
    assert apply_spread_cap(10.0, 10.0, 0.01) == 9.99, "Upper bound failed"
    assert apply_spread_cap(0.0, 10.0, 0.01) == 0.01, "Lower bound failed"
    print("  ✓ Spread cap math correct")


def test_dte():
    """Test DTE calculation."""
    print("✓ Testing DTE...")
    from filters.phase2strat1.chain_index import compute_dte
    from datetime import date
    
    today = date.today()
    dte = compute_dte(today.isoformat())
    assert dte == 0, "Today DTE should be 0"
    
    future = date(today.year, 12, 31)
    dte = compute_dte(future.isoformat())
    assert dte >= 0, "Future DTE should be >= 0"
    print("  ✓ DTE calculation correct")


def test_models():
    """Test data model serialization."""
    print("✓ Testing models...")
    from filters.phase2strat1.models import Signal, Leg
    from datetime import datetime
    
    leg = Leg(
        leg_index=1,
        strike=150.0,
        right="C",
        open_action="BUY",
        quantity=1,
        bid=2.5,
        ask=2.55,
        mid=2.525
    )
    
    signal = Signal(
        signal_id="test",
        symbol="TEST",
        expiration="2024-12-31",
        structure_kind="IC",
        open_side="buy",
        structure_label="IC (buy)",
        dte=30,
        strike_difference=10.0,
        legs=[leg],
        mid_entry=5.0,
        spread_cost=5.0,
        net_credit=-5.0,
        fees_total=2.6,
        fee_per_leg=0.65,
        leg_count=4,
        remaining_profit=2.4,
        remaining_percent=0.24,
        break_even_days=87.6,
        bed_filter_pass=True,
        liquidity_pass=True,
        liquidity_detail="pass",
        structural_pass=True,
        rank_score=2.92,
        run_id=None,
        computed_at=datetime.utcnow().isoformat()
    )
    
    # Test serialization
    json_str = signal.to_json()
    signal_back = Signal.from_json(json_str)
    assert signal_back.signal_id == "test", "Signal serialization failed"
    assert signal_back.legs[0].strike == 150.0, "Leg serialization failed"
    print("  ✓ Model serialization correct")


def main():
    """Run all verification tests."""
    print("\n" + "=" * 60)
    print("Phase 2 Signal Engine — Verification")
    print("=" * 60 + "\n")
    
    success = True
    
    if not test_imports():
        success = False
    
    try:
        test_spread_cap()
        test_dte()
        test_models()
    except AssertionError as e:
        print(f"  ✗ Test failed: {e}")
        success = False
    except Exception as e:
        print(f"  ✗ Unexpected error: {e}")
        success = False
    
    print("\n" + "=" * 60)
    if success:
        print("✓ ALL VERIFICATIONS PASSED")
        print("\nPhase 2 is ready to use:")
        print("  1. Run Phase 1: python datagathering/pipeline.py")
        print("  2. Run Phase 2: python cli/run_phase2_scan.py")
        print("  3. Check results: redis-cli KEYS 'SIGNAL:ACTIVE:*'")
    else:
        print("✗ SOME VERIFICATIONS FAILED")
        print("Check error messages above.")
    print("=" * 60 + "\n")
    
    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(main())
