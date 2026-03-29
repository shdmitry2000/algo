"""
Tests for spread_math.py utilities.
"""
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from filters.phase2strat1.spread_math import apply_spread_cap


def test_positive_spread_capping():
    """Test spread cap with positive spreads."""
    print("\n" + "="*80)
    print("TEST: Positive Spread Capping")
    print("="*80)
    
    width = 10.0
    
    # Too large - should cap to width - 0.01
    result = apply_spread_cap(11.0, width)
    assert result == 9.99, f"Expected 9.99, got {result}"
    print(f"✓ Large positive: 11.0 → {result} (capped to width - 0.01)")
    
    # Within bounds - should pass through
    result = apply_spread_cap(5.0, width)
    assert result == 5.0, f"Expected 5.0, got {result}"
    print(f"✓ Normal positive: 5.0 → {result} (unchanged)")
    
    # Too small - should cap to 0.01
    result = apply_spread_cap(0.005, width)
    assert result == 0.01, f"Expected 0.01, got {result}"
    print(f"✓ Tiny positive: 0.005 → {result} (capped to minimum)")
    
    # Exactly zero - should cap to 0.01
    result = apply_spread_cap(0.0, width)
    assert result == 0.01, f"Expected 0.01, got {result}"
    print(f"✓ Zero: 0.0 → {result} (capped to minimum)")
    
    print("✅ PASSED: Positive spread capping working correctly\n")
    return True


def test_negative_spread_capping():
    """Test spread cap with negative spreads (sign preserving)."""
    print("\n" + "="*80)
    print("TEST: Negative Spread Capping")
    print("="*80)
    
    width = 10.0
    
    # Too large (in magnitude) - should cap to -(width - 0.01)
    result = apply_spread_cap(-11.0, width)
    assert result == -9.99, f"Expected -9.99, got {result}"
    print(f"✓ Large negative: -11.0 → {result} (capped to -(width - 0.01))")
    
    # Within bounds - should pass through
    result = apply_spread_cap(-5.0, width)
    assert result == -5.0, f"Expected -5.0, got {result}"
    print(f"✓ Normal negative: -5.0 → {result} (unchanged)")
    
    # Too small (in magnitude) - should cap to -0.01
    result = apply_spread_cap(-0.005, width)
    assert result == -0.01, f"Expected -0.01, got {result}"
    print(f"✓ Tiny negative: -0.005 → {result} (capped to -minimum)")
    
    print("✅ PASSED: Negative spread capping working correctly\n")
    return True


def test_spread_cap_symmetry():
    """Test that spread cap is symmetric for positive and negative values."""
    print("\n" + "="*80)
    print("TEST: Spread Cap Symmetry")
    print("="*80)
    
    width = 10.0
    test_values = [
        (11.0, -11.0, 9.99, -9.99),
        (5.0, -5.0, 5.0, -5.0),
        (0.005, -0.005, 0.01, -0.01),
    ]
    
    for pos, neg, expected_pos, expected_neg in test_values:
        result_pos = apply_spread_cap(pos, width)
        result_neg = apply_spread_cap(neg, width)
        
        assert result_pos == expected_pos, f"Positive: expected {expected_pos}, got {result_pos}"
        assert result_neg == expected_neg, f"Negative: expected {expected_neg}, got {result_neg}"
        assert result_pos == -result_neg, f"Not symmetric: {result_pos} vs {result_neg}"
        
        print(f"✓ {pos:>6} → {result_pos:>6} | {neg:>7} → {result_neg:>7} (symmetric)")
    
    print("✅ PASSED: Spread cap is symmetric\n")
    return True


def test_spread_cap_different_widths():
    """Test spread cap with different strike widths."""
    print("\n" + "="*80)
    print("TEST: Spread Cap with Different Widths")
    print("="*80)
    
    test_cases = [
        # (raw_spread, width, expected)
        (5.0, 5.0, 4.99),    # Positive, caps to width - 0.01
        (-5.0, 5.0, -4.99),  # Negative, caps to -(width - 0.01)
        (2.0, 5.0, 2.0),     # Positive, within bounds
        (-2.0, 5.0, -2.0),   # Negative, within bounds
        (20.0, 20.0, 19.99), # Large width
        (-20.0, 20.0, -19.99),
    ]
    
    for raw, width, expected in test_cases:
        result = apply_spread_cap(raw, width)
        assert abs(result - expected) < 0.001, f"Raw={raw}, width={width}: expected {expected}, got {result}"
        print(f"✓ Raw={raw:>6}, width={width:>4} → {result:>7} (expected {expected:>7})")
    
    print("✅ PASSED: Spread cap handles different widths correctly\n")
    return True


def test_spread_cap_custom_bound():
    """Test spread cap with custom bound values."""
    print("\n" + "="*80)
    print("TEST: Spread Cap with Custom Bound")
    print("="*80)
    
    width = 10.0
    custom_bound = 0.05
    
    # Positive
    result = apply_spread_cap(11.0, width, bound=custom_bound)
    expected = width - custom_bound  # 9.95
    assert abs(result - expected) < 0.001, f"Expected {expected}, got {result}"
    print(f"✓ Positive with bound=0.05: 11.0 → {result} (capped to 9.95)")
    
    # Negative
    result = apply_spread_cap(-11.0, width, bound=custom_bound)
    expected = -(width - custom_bound)  # -9.95
    assert abs(result - expected) < 0.001, f"Expected {expected}, got {result}"
    print(f"✓ Negative with bound=0.05: -11.0 → {result} (capped to -9.95)")
    
    # Small positive
    result = apply_spread_cap(0.02, width, bound=custom_bound)
    assert result == custom_bound, f"Expected {custom_bound}, got {result}"
    print(f"✓ Tiny positive with bound=0.05: 0.02 → {result} (capped to 0.05)")
    
    # Small negative
    result = apply_spread_cap(-0.02, width, bound=custom_bound)
    assert result == -custom_bound, f"Expected {-custom_bound}, got {result}"
    print(f"✓ Tiny negative with bound=0.05: -0.02 → {result} (capped to -0.05)")
    
    print("✅ PASSED: Custom bound working correctly\n")
    return True


def run_all_tests():
    """Run all spread_math tests."""
    print("\n" + "="*80)
    print("SPREAD MATH TEST SUITE")
    print("="*80)
    
    tests = [
        ("Positive Spread Capping", test_positive_spread_capping),
        ("Negative Spread Capping", test_negative_spread_capping),
        ("Spread Cap Symmetry", test_spread_cap_symmetry),
        ("Different Widths", test_spread_cap_different_widths),
        ("Custom Bound", test_spread_cap_custom_bound),
    ]
    
    passed = 0
    failed = 0
    
    for name, test_func in tests:
        try:
            test_func()
            passed += 1
        except AssertionError as e:
            print(f"❌ FAILED: {name}")
            print(f"   Error: {e}\n")
            failed += 1
        except Exception as e:
            print(f"❌ ERROR: {name}")
            print(f"   {type(e).__name__}: {e}\n")
            failed += 1
    
    print("="*80)
    print("SPREAD MATH TEST RESULTS")
    print("="*80)
    print(f"Passed: {passed}")
    print(f"Failed: {failed}")
    print("="*80)
    
    if failed == 0:
        print("🎉 ALL SPREAD MATH TESTS PASSED!")
    else:
        print(f"⚠️  {failed} test(s) failed")
    
    return failed == 0


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
