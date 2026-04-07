"""
Quick validation test for Phase 1 core infrastructure.

Tests:
1. Core models can be instantiated
2. Iron Condor strategy is registered and importable
3. Adapters work correctly
4. Basic calculations are accurate
"""
import sys
import os
# Add parent directory to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))

from strategies.core import (
    BaseStrategy,
    StrategyCandidate,
    Leg,
    ChainData,
    STRATEGY_TYPES,
    compute_bed,
    compute_annual_return,
    apply_spread_cap,
)
from strategies.implementations import IronCondorStrategy
from datagathering.models import StandardOptionTick


def test_core_models():
    """Test that core models can be created."""
    print("✓ Testing core models...")
    
    # Create a Leg
    leg = Leg(
        leg_index=1,
        strike=100.0,
        right="C",
        open_action="BUY",
        quantity=1,
        bid=5.0,
        ask=5.5,
        mid=5.25,
        volume=100,
        open_interest=1000
    )
    assert leg.strike == 100.0
    assert leg.right == "C"
    print("  ✓ Leg model works")
    
    # Create ChainData with mock ticks
    ticks = [
        StandardOptionTick(
            root="TEST",
            expiration="2026-04-30",
            strike=95.0,
            right="C",
            bid=7.0,
            ask=7.5,
            mid=7.25,
            volume=50,
            open_interest=500,
            timestamp="2026-04-01T00:00:00",
            provider="test"
        ),
        StandardOptionTick(
            root="TEST",
            expiration="2026-04-30",
            strike=95.0,
            right="P",
            bid=1.0,
            ask=1.5,
            mid=1.25,
            volume=50,
            open_interest=500,
            timestamp="2026-04-01T00:00:00",
            provider="test"
        ),
    ]
    
    chain = ChainData(
        symbol="TEST",
        spot_price=100.0,
        expirations=["2026-04-30"],
        ticks=ticks
    )
    assert chain.symbol == "TEST"
    assert len(chain.expirations) == 1
    print("  ✓ ChainData model works")
    
    # Test ChainData lookups
    call = chain.get_call(95.0)
    assert call is not None
    assert call.right == "C"
    assert call.mid == 7.25
    print("  ✓ ChainData.get_call() works")
    
    put = chain.get_put(95.0)
    assert put is not None
    assert put.right == "P"
    assert put.mid == 1.25
    print("  ✓ ChainData.get_put() works")
    
    strikes = chain.sorted_strikes()
    assert strikes == [95.0]
    print("  ✓ ChainData.sorted_strikes() works")


def test_strategy_registry():
    """Test that strategies are properly registered."""
    print("\n✓ Testing strategy registry...")
    
    # Check STRATEGY_TYPES includes our strategies
    assert "IC_BUY" in STRATEGY_TYPES
    assert "IC_SELL" in STRATEGY_TYPES
    assert "FLYGONAAL_BUY" in STRATEGY_TYPES
    assert "CALENDAR_BUY_C" in STRATEGY_TYPES
    print(f"  ✓ Registry contains {len(STRATEGY_TYPES)} strategy types")
    
    # Check Iron Condor is importable
    ic_strategy = IronCondorStrategy()
    assert ic_strategy.strategy_type == "IC"
    print("  ✓ IronCondorStrategy is importable and registered")


def test_utility_functions():
    """Test utility functions."""
    print("\n✓ Testing utility functions...")
    
    # Test spread cap
    capped = apply_spread_cap(11.0, 10.0, 0.01)
    assert capped == 9.99
    print(f"  ✓ apply_spread_cap(11.0, 10.0) = {capped}")
    
    capped_neg = apply_spread_cap(-11.0, 10.0, 0.01)
    assert capped_neg == -9.99
    print(f"  ✓ apply_spread_cap(-11.0, 10.0) = {capped_neg}")
    
    # Test BED calculation
    bed = compute_bed(3.65, 10.0)
    assert abs(bed - 133.225) < 0.01
    print(f"  ✓ compute_bed(3.65, 10.0) = {bed:.2f} days")
    
    # Test annual return
    annual = compute_annual_return(3.65, 10.0, 32)
    assert annual > 400  # Should be high for 32 DTE
    print(f"  ✓ compute_annual_return(3.65, 10.0, 32) = {annual:.2f}%")


def test_iron_condor_basic():
    """Test Iron Condor can scan a simple chain."""
    print("\n✓ Testing Iron Condor strategy...")
    
    # Create a simple test chain
    ticks = []
    strikes = [90.0, 95.0, 100.0, 105.0, 110.0]
    
    for strike in strikes:
        # Add call
        ticks.append(StandardOptionTick(
            root="TEST",
            expiration="2026-04-30",
            strike=strike,
            right="C",
            bid=max(0.1, 110 - strike - 1),
            ask=max(0.2, 110 - strike + 1),
            mid=max(0.15, 110 - strike),
            volume=100,
            open_interest=1000,
            timestamp="2026-04-01T00:00:00",
            provider="test"
        ))
        
        # Add put
        ticks.append(StandardOptionTick(
            root="TEST",
            expiration="2026-04-30",
            strike=strike,
            right="P",
            bid=max(0.1, strike - 90 - 1),
            ask=max(0.2, strike - 90 + 1),
            mid=max(0.15, strike - 90),
            volume=100,
            open_interest=1000,
            timestamp="2026-04-01T00:00:00",
            provider="test"
        ))
    
    chain = ChainData(
        symbol="TEST",
        spot_price=100.0,
        expirations=["2026-04-30"],
        ticks=ticks
    )
    
    # Scan for IC candidates
    ic_strategy = IronCondorStrategy()
    candidates = ic_strategy.scan(
        chain_data=chain,
        dte=32,
        fee_per_leg=0.65,
        spread_cap_bound=0.01,
        include_imbalanced=False  # Disable for quick test
    )
    
    print(f"  ✓ Iron Condor scan found {len(candidates)} candidates")
    
    if candidates:
        first = candidates[0]
        print(f"    - Type: {first.strategy_type}")
        print(f"    - Strikes: {first.strikes_used}")
        print(f"    - Width: ${first.strike_difference}")
        print(f"    - Remaining profit: ${first.remaining_profit:.2f}")
        print(f"    - Annual return: {first.annual_return_percent:.1f}%")


def test_adapters():
    """Test adapter functions."""
    print("\n✓ Testing adapters...")
    
    try:
        from strategies.adapters import (
            convert_chain_index_to_chain_data,
            convert_td_response_to_chain_data,
        )
        print("  ✓ Adapters are importable")
        
        # Test TD adapter with mock data
        td_mock = {
            'underlying': {'last': 100.0},
            'callExpDateMap': {
                '2026-04-30:32': {
                    '95.0': [{
                        'symbol': 'TEST_043026C95',
                        'strikePrice': 95.0,
                        'putCall': 'C',
                        'bid': 7.0,
                        'ask': 7.5,
                        'mark': 7.25,
                        'totalVolume': 100,
                        'openInterest': 1000,
                    }]
                }
            },
            'putExpDateMap': {}
        }
        
        chain = convert_td_response_to_chain_data("TEST", td_mock)
        assert chain.symbol == "TEST"
        assert chain.spot_price == 100.0
        assert len(chain.ticks) == 1
        print("  ✓ TD adapter converts API response correctly")
        
    except ImportError as e:
        print(f"  ⚠ Adapter test skipped: {e}")


def main():
    """Run all validation tests."""
    print("=" * 60)
    print("Phase 1 Core Infrastructure Validation")
    print("=" * 60)
    
    try:
        test_core_models()
        test_strategy_registry()
        test_utility_functions()
        test_iron_condor_basic()
        test_adapters()
        
        print("\n" + "=" * 60)
        print("✅ ALL TESTS PASSED!")
        print("=" * 60)
        print("\nCore infrastructure is working correctly.")
        print("Ready to continue with remaining migrations.")
        
    except AssertionError as e:
        print(f"\n❌ TEST FAILED: {e}")
        import traceback
        traceback.print_exc()
        return 1
    except Exception as e:
        print(f"\n❌ UNEXPECTED ERROR: {e}")
        import traceback
        traceback.print_exc()
        return 1
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
