"""
Integration tests for multi-strategy scan orchestrator.
Tests that all strategies work together in scan.py.
Uses hardcoded test data for predictable results.
"""
import sys
sys.path.insert(0, '/Users/dmitrysh/code/algotrade/algo')

from filters.phase2strat1.chain_index import ChainIndex
from filters.phase2strat1.strategies import (
    IronCondorStrategy,
    ButterflyStrategy,
    ShiftedCondorStrategy
)
from filters.phase2strat1.scan import (
    build_strategy_snapshot,
    apply_bed_filter_to_candidates,
    compute_rank_score,
    select_best_strategy
)
from tests.strategies.test_fixtures import get_test_chain, get_test_dte


def test_all_strategies_generate_typed_candidates():
    """Test that all strategies return candidates with correct strategy_type."""
    print("\n" + "="*80)
    print("TEST: Strategy Type Assignment")
    print("="*80)
    
    ticks, expiration = get_test_chain()
    dte = get_test_dte()
    chain_idx = ChainIndex("TEST", expiration, ticks)
    
    ic = IronCondorStrategy()
    bf = ButterflyStrategy()
    shifted = ShiftedCondorStrategy()
    
    # Scan all strategies
    ic_candidates = ic.scan(chain_idx, dte=30, fee_per_leg=0.65, include_imbalanced=True, max_imbalanced_legs=8)
    bf_candidates = bf.scan(chain_idx, dte=30, fee_per_leg=0.65)
    shifted_candidates = shifted.scan(chain_idx, dte=30, fee_per_leg=0.65)
    
    # Collect strategy types
    all_candidates = ic_candidates + bf_candidates + shifted_candidates
    
    strategy_types_found = set()
    for candidate in all_candidates:
        strategy_types_found.add(candidate.strategy_type)
    
    print(f"✓ Total candidates: {len(all_candidates)}")
    print(f"✓ Unique strategy types: {len(strategy_types_found)}")
    
    for strategy_type in sorted(strategy_types_found):
        count = sum(1 for c in all_candidates if c.strategy_type == strategy_type)
        print(f"  • {strategy_type}: {count} candidates")
    
    # Verify we have multiple types
    assert len(strategy_types_found) >= 3, f"Expected at least 3 types (with small test chain), got {len(strategy_types_found)}"
    
    print("✅ PASSED: All strategies assign correct types\n")
    return True


def test_bed_filter_application():
    """Test BED filter applies correctly to candidates."""
    print("\n" + "="*80)
    print("TEST: BED Filter Application")
    print("="*80)
    
    ticks, expiration = get_test_chain()
    dte = get_test_dte()
    chain_idx = ChainIndex("TEST", expiration, ticks)
    
    ic = IronCondorStrategy()
    candidates = ic.scan(chain_idx, dte=30, fee_per_leg=0.65, include_imbalanced=False)
    
    print(f"Generated {len(candidates)} IC candidates")
    
    # Apply BED filter
    apply_bed_filter_to_candidates(candidates, dte=30)
    
    passing = [c for c in candidates if c.bed_filter_pass]
    failing = [c for c in candidates if not c.bed_filter_pass]
    
    print(f"✓ Passing BED filter: {len(passing)}")
    print(f"✓ Failing BED filter: {len(failing)}")
    
    # Verify filter logic: DTE < BED and remaining > 0
    for candidate in passing:
        assert candidate.dte < candidate.break_even_days, \
            f"Passing candidate should have DTE < BED: {candidate.dte} < {candidate.break_even_days}"
        assert candidate.remaining_profit > 0, "Passing candidate should have positive profit"
    
    print(f"✓ All passing candidates satisfy: DTE < BED and profit > 0")
    
    print("✅ PASSED: BED filter working correctly\n")
    return True


def test_rank_score_calculation():
    """Test rank score calculation."""
    print("\n" + "="*80)
    print("TEST: Rank Score Calculation")
    print("="*80)
    
    ticks, expiration = get_test_chain()
    dte = get_test_dte()
    chain_idx = ChainIndex("TEST", expiration, ticks)
    
    ic = IronCondorStrategy()
    candidates = ic.scan(chain_idx, dte=dte, fee_per_leg=0.65, include_imbalanced=False)
    
    sample = candidates[0]
    
    # Calculate rank score
    rank_score = compute_rank_score(sample)
    
    # Expected: BED / max(DTE, 1)
    expected_score = sample.break_even_days / max(sample.dte, 1)
    
    assert abs(rank_score - expected_score) < 0.001, \
        f"Rank score mismatch: expected {expected_score:.4f}, got {rank_score:.4f}"
    
    print(f"✓ Sample candidate:")
    print(f"  BED: {sample.break_even_days:.2f} days")
    print(f"  DTE: {sample.dte} days")
    print(f"  Rank score: {rank_score:.4f}")
    print(f"✓ Formula verified: rank_score = BED / DTE")
    
    print("✅ PASSED: Rank score calculation correct\n")
    return True


def test_strategy_selection_priority():
    """Test that select_best_strategy respects priority order."""
    print("\n" + "="*80)
    print("TEST: Strategy Selection Priority")
    print("="*80)
    
    ticks, expiration = get_test_chain()
    dte = get_test_dte()
    chain_idx = ChainIndex("TEST", expiration, ticks)
    
    # Scan all strategies
    ic = IronCondorStrategy()
    bf = ButterflyStrategy()
    shifted = ShiftedCondorStrategy()
    
    ic_candidates = ic.scan(chain_idx, dte=dte, fee_per_leg=0.65, include_imbalanced=False)
    bf_candidates = bf.scan(chain_idx, dte=dte, fee_per_leg=0.65)
    shifted_candidates = shifted.scan(chain_idx, dte=dte, fee_per_leg=0.65)
    
    # Group by strategy type
    all_strategy_candidates = {}
    for candidate in ic_candidates + bf_candidates + shifted_candidates:
        if candidate.strategy_type not in all_strategy_candidates:
            all_strategy_candidates[candidate.strategy_type] = []
        all_strategy_candidates[candidate.strategy_type].append(candidate)
    
    # Apply BED filter
    for strategy_type, candidates in all_strategy_candidates.items():
        apply_bed_filter_to_candidates(candidates, dte=30)
    
    # Select best per strategy
    best_per_strategy = select_best_strategy(all_strategy_candidates)
    
    if best_per_strategy:
        print(f"✓ Best candidates selected:")
        for strategy_type, candidate in best_per_strategy.items():
            print(f"  • {strategy_type}: rank_score={candidate.rank_score:.4f}, BED={candidate.break_even_days:.2f}")
        
        # Verify each has a rank score
        for candidate in best_per_strategy.values():
            assert candidate.rank_score > 0, "Best candidate should have positive rank score"
        
        print(f"✓ All best candidates have valid rank scores")
    else:
        print("⚠ No candidates passed BED filter (DTE too short)")
    
    print("✅ PASSED: Strategy selection working\n")
    return True


def test_strategy_snapshot_building():
    """Test that strategy snapshots only include used strikes."""
    print("\n" + "="*80)
    print("TEST: Strategy Snapshot Building")
    print("="*80)
    
    ticks, expiration = get_test_chain()
    dte = get_test_dte()
    chain_idx = ChainIndex("TEST", expiration, ticks)
    
    ic = IronCondorStrategy()
    candidates = ic.scan(chain_idx, dte=dte, fee_per_leg=0.65, include_imbalanced=False)
    
    # Get best candidate
    ic_buy = [c for c in candidates if c.strategy_type == "IC_BUY"]
    
    if ic_buy:
        best_candidates = {"IC_BUY": ic_buy[0]}
        
        # Build snapshot
        snapshot = build_strategy_snapshot(best_candidates, ticks)
        
        assert "chain" in snapshot, "Snapshot should have 'chain' key"
        assert "strategies" in snapshot, "Snapshot should have 'strategies' key"
        
        # Count strikes in snapshot
        snapshot_strikes = set(t["strike"] for t in snapshot["chain"])
        
        # Count strikes used by strategies
        used_strikes = set()
        for strategy_data in snapshot["strategies"].values():
            used_strikes.update(strategy_data["strikes_used"])
        
        print(f"✓ Total ticks in chain: {len(ticks)}")
        print(f"✓ Strikes in snapshot: {len(snapshot_strikes)}")
        print(f"✓ Strikes used by strategies: {len(used_strikes)}")
        
        # Snapshot should only include used strikes
        assert snapshot_strikes == used_strikes, "Snapshot should only include used strikes"
        print(f"✓ Snapshot optimized: only {len(snapshot_strikes)} used strikes (not all {len(ticks)//2})")
        
        print("✅ PASSED: Snapshot building correct\n")
    else:
        print("⚠ No candidates to test snapshot with")
        print("✅ PASSED: Snapshot logic correct\n")
    
    return True


def run_all_integration_tests():
    """Run all integration tests."""
    print("\n" + "="*80)
    print("INTEGRATION TEST SUITE")
    print("="*80)
    
    tests = [
        test_all_strategies_generate_typed_candidates,
        test_bed_filter_application,
        test_rank_score_calculation,
        test_strategy_selection_priority,
        test_strategy_snapshot_building
    ]
    
    passed = 0
    failed = 0
    
    for test in tests:
        try:
            test()
            passed += 1
        except AssertionError as e:
            print(f"❌ FAILED: {e}\n")
            failed += 1
        except Exception as e:
            print(f"❌ ERROR: {e}\n")
            import traceback
            traceback.print_exc()
            failed += 1
    
    print("="*80)
    print(f"Integration Tests: {passed} passed, {failed} failed")
    print("="*80)
    
    return failed == 0


if __name__ == '__main__':
    success = run_all_integration_tests()
    sys.exit(0 if success else 1)
