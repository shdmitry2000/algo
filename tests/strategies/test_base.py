"""
Tests for base strategy classes and common functionality.
"""
import sys
sys.path.insert(0, '/Users/dmitrysh/code/algotrade/algo')

from filters.phase2strat1.strategies.base import STRATEGY_TYPES, BaseStrategy
from filters.phase2strat1.strategies import IronCondorStrategy


def test_strategy_types_registered():
    """Test that all 16 strategy types are registered."""
    print("\n" + "="*80)
    print("TEST: Strategy Type Registration")
    print("="*80)
    
    assert len(STRATEGY_TYPES) == 16, f"Expected 16 types, got {len(STRATEGY_TYPES)}"
    print(f"✓ {len(STRATEGY_TYPES)} strategy types registered")
    
    expected_types = [
        "IC_BUY", "IC_SELL", "IC_BUY_IMBAL", "IC_SELL_IMBAL",
        "BF_BUY", "BF_SELL", "BF_BUY_IMBAL", "BF_SELL_IMBAL",
        "SHIFTED_IC_BUY", "SHIFTED_IC_SELL", "SHIFTED_IC_BUY_IMBAL", "SHIFTED_IC_SELL_IMBAL",
        "SHIFTED_BF_BUY", "SHIFTED_BF_SELL", "SHIFTED_BF_BUY_IMBAL", "SHIFTED_BF_SELL_IMBAL"
    ]
    
    missing = []
    for expected_type in expected_types:
        if expected_type not in STRATEGY_TYPES:
            missing.append(expected_type)
        else:
            print(f"  ✓ {expected_type}: {STRATEGY_TYPES[expected_type]}")
    
    assert len(missing) == 0, f"Missing strategy types: {missing}"
    print("✅ PASSED: All strategy types registered\n")
    return True


def test_imbalanced_generator():
    """Test imbalanced quantity generator."""
    print("\n" + "="*80)
    print("TEST: Imbalanced Quantity Generator")
    print("="*80)
    
    strategy = IronCondorStrategy()
    combos = strategy.generate_imbalanced_quantities(max_total_legs=10, max_ratio=3)
    
    assert len(combos) > 0, "Should generate at least some combos"
    print(f"✓ Generated {len(combos)} combinations")
    print(f"  Combos: {combos}")
    
    for buy_qty, sell_qty in combos:
        # Buy must be greater than sell
        assert buy_qty > sell_qty, f"Buy qty {buy_qty} must be > sell qty {sell_qty}"
        
        # Total legs should be reasonable
        total = buy_qty + sell_qty
        assert total <= 10, f"Total legs {total} exceeds max_total_legs"
        
        # Ratio check
        ratio = buy_qty / sell_qty
        assert ratio <= 3, f"Ratio {ratio:.2f} exceeds max_ratio"
    
    print(f"✓ All {len(combos)} combos satisfy constraints:")
    print(f"  • buy_qty > sell_qty")
    print(f"  • buy_qty + sell_qty <= max_total_legs")
    print(f"  • buy_qty / sell_qty <= max_ratio")
    
    print("✅ PASSED: Imbalanced generator working correctly\n")
    return True


def test_imbalanced_generator_limits():
    """Test generator respects limits."""
    print("\n" + "="*80)
    print("TEST: Imbalanced Generator Limits")
    print("="*80)
    
    strategy = IronCondorStrategy()
    
    # With max_total_legs=4, should only get (2,1) and (3,1)
    combos = strategy.generate_imbalanced_quantities(max_total_legs=4, max_ratio=3)
    
    print(f"Generated {len(combos)} combos with max_total_legs=4: {combos}")
    
    assert len(combos) == 2, f"Expected 2 combos, got {len(combos)}"
    assert (2, 1) in combos, "Should have (2,1)"
    assert (3, 1) in combos, "Should have (3,1)"
    
    print(f"✓ Correct combos for max_total_legs=4")
    
    # With max_ratio=2, should exclude high ratios
    combos_ratio = strategy.generate_imbalanced_quantities(max_total_legs=10, max_ratio=2)
    
    for buy_qty, sell_qty in combos_ratio:
        ratio = buy_qty / sell_qty
        assert ratio <= 2, f"Ratio {ratio:.2f} exceeds max_ratio=2"
    
    print(f"✓ All combos respect max_ratio=2")
    print("✅ PASSED: Generator limits working\n")
    return True


def test_bed_calculation():
    """Test BED calculation formula."""
    print("\n" + "="*80)
    print("TEST: BED Calculation Formula")
    print("="*80)
    
    strategy = IronCondorStrategy()
    
    # Test with known values
    remaining_profit = 3.5
    width = 10.0
    
    bed = strategy.compute_bed(remaining_profit, width)
    
    # Expected: BED = (365/100) * (remaining / width * 100)
    expected_remaining_percent = (remaining_profit / width) * 100
    expected_bed = (365 / 100) * expected_remaining_percent
    
    assert abs(bed - expected_bed) < 0.01, f"BED mismatch: expected {expected_bed:.2f}, got {bed:.2f}"
    
    print(f"✓ Input: remaining=${remaining_profit}, width=${width}")
    print(f"✓ Calculated BED: {bed:.2f} days")
    print(f"✓ Expected BED: {expected_bed:.2f} days")
    print(f"✓ Formula verified: BED = (365/100) * (remaining% / 100)")
    
    print("✅ PASSED: BED calculation correct\n")
    return True


def run_all_base_tests():
    """Run all base strategy tests."""
    print("\n" + "="*80)
    print("BASE STRATEGY TEST SUITE")
    print("="*80)
    
    tests = [
        test_strategy_types_registered,
        test_imbalanced_generator,
        test_imbalanced_generator_limits,
        test_bed_calculation
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
            failed += 1
    
    print("="*80)
    print(f"Base Strategy Tests: {passed} passed, {failed} failed")
    print("="*80)
    
    return failed == 0


if __name__ == '__main__':
    success = run_all_base_tests()
    sys.exit(0 if success else 1)
