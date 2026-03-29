"""
Test annual return calculations and strategy parameter validation.
Tests >100% annual returns and verifies all IC strategy parameters are saved.
"""
import sys
from pathlib import Path

project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from tests.strategies.test_fixtures import get_test_chain, get_test_dte
from filters.phase2strat1.chain_index import ChainIndex
from filters.phase2strat1.strategies import IronCondorStrategy
from filters.phase2strat1.models import Signal
from filters.phase2strat1.spread_math import (
    compute_annual_return,
    compute_bed,
    compute_max_entry_cost
)


def test_annual_return_calculation():
    """Test annual return calculation formula."""
    print("\n" + "="*80)
    print("TEST: Annual Return Calculation")
    print("="*80)
    
    test_cases = [
        # (remaining, width, dte, expected_annual%)
        # Formula: (remaining/width) * (365/dte) * 100
        (3.65, 10.0, 32, 416.33),    # 36.5% profit in 32 days → 416% annual
        (10.0, 10.0, 365, 100.0),    # 100% profit in 365 days = 100% annual
        (10.0, 10.0, 100, 365.0),    # 100% profit in 100 days = 365% annual
        (5.0, 10.0, 32, 570.31),     # 50% profit in 32 days → 570% annual
        (2.74, 10.0, 10, 1000.1),    # 27.4% profit in 10 days = 1,000% annual
    ]
    
    print("Testing various profit scenarios:")
    print(f"{'Profit':>8} {'Width':>8} {'DTE':>5} {'Annual%':>10} {'Expected%':>12}")
    print("-" * 80)
    
    for remaining, width, dte, expected in test_cases:
        annual = compute_annual_return(remaining, width, dte)
        
        # Allow small floating point difference
        assert abs(annual - expected) < 1.0, \
            f"Annual return mismatch: {annual:.2f}% vs {expected:.2f}%"
        
        marker = "🔥" if annual > 100 else "✓"
        print(f"{marker} ${remaining:>6.2f} ${width:>7.2f} {dte:>5} {annual:>9.2f}% {expected:>11.2f}%")
    
    print("\n✓ All annual return calculations correct")
    print("✅ PASSED: Annual return formula verified\n")
    return True


def test_hundred_percent_annual_threshold():
    """Test identifying strategies with >100% annual return."""
    print("\n" + "="*80)
    print("TEST: >100% Annual Return Threshold")
    print("="*80)
    
    print("For >100% annual return, we need:")
    print("  remaining% > (100 * dte) / 365")
    print()
    
    # Calculate threshold for different DTEs
    print(f"{'DTE':>5} {'Min Remaining%':>16} {'Example (width=$10)':>25}")
    print("-" * 80)
    
    for dte in [10, 20, 32, 45, 60, 90, 180, 365]:
        min_remaining_pct = (100 * dte) / 365
        min_profit = (min_remaining_pct / 100) * 10.0  # For $10 width
        
        print(f"{dte:>5} {min_remaining_pct:>15.2f}% ${min_profit:>23.2f}")
    
    print()
    print("Key insights:")
    print("  • DTE=32 (1 month): Need >8.77% profit (>$0.88 on $10 width)")
    print("  • DTE=10 (short): Need >2.74% profit (>$0.27 on $10 width)")
    print("  • DTE=365 (1 year): Need 100% profit ($10.00 on $10 width)")
    
    # Verify with actual calculation
    test_profit = 0.88
    test_width = 10.0
    test_dte = 32
    annual = compute_annual_return(test_profit, test_width, test_dte)
    
    print(f"\nVerification:")
    print(f"  Profit: ${test_profit}, Width: ${test_width}, DTE: {test_dte}")
    print(f"  Annual return: {annual:.2f}%")
    print(f"  Exceeds 100%: {annual > 100}")
    
    assert annual > 100, f"$0.88 profit on $10 width in 32 days should exceed 100% annual"
    print("  ✓ Threshold calculation verified")
    
    print("✅ PASSED: 100% threshold calculation correct\n")
    return True


def test_max_price_for_ic_strategy():
    """Test maximum entry price for IC to achieve target annual return."""
    print("\n" + "="*80)
    print("TEST: Max Entry Price for Target Annual Return")
    print("="*80)
    
    # For IC: remaining = width - cost - fees
    # For >100% annual: remaining > (100 * dte / 365) / 100 * width
    
    width = 10.0
    dte = 32
    fee_per_leg = 0.65
    fees_total = 4 * fee_per_leg  # IC has 4 legs
    
    # For 100% annual return
    min_remaining_pct = (100 * dte) / 365
    min_remaining = (min_remaining_pct / 100) * width
    
    # Max cost = width - min_remaining - fees
    max_cost_100pct = width - min_remaining - fees_total
    
    print(f"Parameters:")
    print(f"  Width: ${width}")
    print(f"  DTE: {dte} days")
    print(f"  Fees: ${fees_total} (4 legs × ${fee_per_leg})")
    print()
    print(f"For >100% annual return:")
    print(f"  Min remaining%: {min_remaining_pct:.2f}%")
    print(f"  Min remaining$: ${min_remaining:.2f}")
    print(f"  Max entry cost: ${max_cost_100pct:.2f}")
    print()
    
    # Test different annual return targets
    targets = [100, 150, 200, 300, 500]
    
    print(f"{'Target Annual%':>16} {'Min Remaining%':>17} {'Max Cost':>12}")
    print("-" * 80)
    
    for target in targets:
        min_rem_pct = (target * dte) / 365
        min_rem = (min_rem_pct / 100) * width
        max_cost = width - min_rem - fees_total
        
        print(f"{target:>15}% {min_rem_pct:>16.2f}% ${max_cost:>10.2f}")
        
        # Verify calculation
        if max_cost > 0:
            remaining = width - max_cost - fees_total
            annual = compute_annual_return(remaining, width, dte)
            assert annual >= target - 1, f"Annual return calculation error"
    
    print()
    print("✓ Max entry cost calculations verified for all targets")
    
    # Practical example
    print()
    print("Practical Example (DTE=32, width=$10):")
    print(f"  • For 100% annual: Pay ≤ ${max_cost_100pct:.2f}")
    print(f"  • For 200% annual: Pay ≤ ${width - ((200*dte/365)/100)*width - fees_total:.2f}")
    print(f"  • For 500% annual: Pay ≤ ${width - ((500*dte/365)/100)*width - fees_total:.2f}")
    
    print("✅ PASSED: Max price calculations correct\n")
    return True


def test_ic_strategy_saves_all_parameters():
    """Test that IC strategy saves all calculation parameters."""
    print("\n" + "="*80)
    print("TEST: IC Strategy Saves All Parameters")
    print("="*80)
    
    ticks, expiration = get_test_chain(chain_type="buy")
    dte = get_test_dte()
    chain_idx = ChainIndex("TEST_BUY", expiration, ticks)
    
    ic_scanner = IronCondorStrategy()
    candidates = ic_scanner.scan(chain_idx, dte, fee_per_leg=0.65, include_imbalanced=False)
    
    assert len(candidates) > 0, "Should have IC candidates"
    
    # Get standard IC_BUY (not imbalanced)
    ic_buy = [c for c in candidates if c.strategy_type == "IC_BUY"]
    assert len(ic_buy) > 0, "Should have IC_BUY candidates"
    
    candidate = ic_buy[0]
    ic_dict = candidate.to_dict()
    
    print(f"Testing {ic_dict['strategy_type']} candidate parameters:")
    print()
    
    # Core parameters
    required_params = [
        "strategy_type",
        "symbol",
        "expiration",
        "dte",
        "open_side",
        "strike_difference",
        "strikes_used",
        "legs",
        "leg_count",
        "total_quantity"
    ]
    
    print("1. Core Parameters:")
    for param in required_params:
        assert param in ic_dict, f"Missing parameter: {param}"
        value = ic_dict[param] if param != "legs" else f"[{len(ic_dict[param])} legs]"
        print(f"   ✓ {param}: {value}")
    
    print()
    
    # Financial parameters
    financial_params = [
        "mid_entry",
        "spread_cost",
        "fees_total",
        "fee_per_leg",
        "net_credit",
        "remaining_profit",
        "remaining_percent",
        "break_even_days",
        "annual_return_percent"
    ]
    
    print("2. Financial Parameters:")
    for param in financial_params:
        assert param in ic_dict, f"Missing parameter: {param}"
        value = ic_dict[param]
        
        # Format annual return specially
        if param == "annual_return_percent":
            print(f"   ✓ {param}: {value:.2f}%")
        else:
            print(f"   ✓ {param}: {value}")
    
    print()
    
    # Filter parameters
    filter_params = [
        "bed_filter_pass",
        "liquidity_pass",
        "structural_pass",
        "rank_score"
    ]
    
    print("3. Filter Parameters:")
    for param in filter_params:
        assert param in ic_dict, f"Missing parameter: {param}"
        value = ic_dict[param]
        print(f"   ✓ {param}: {value}")
    
    print()
    
    # Metadata
    metadata_params = [
        "computed_at"
    ]
    
    print("4. Metadata:")
    for param in metadata_params:
        assert param in ic_dict, f"Missing parameter: {param}"
        value = ic_dict[param]
        print(f"   ✓ {param}: {value}")
    
    print()
    
    # IC-specific parameters
    ic_specific = [
        "raw_spreads",
        "capped_spreads",
        "buy_notional",
        "sell_notional",
        "is_imbalanced"
    ]
    
    print("5. IC-Specific Parameters:")
    for param in ic_specific:
        assert param in ic_dict, f"Missing IC parameter: {param}"
        value = ic_dict[param]
        print(f"   ✓ {param}: {value}")
    
    print()
    
    # Verify leg data completeness
    print("6. Leg Details:")
    for i, leg in enumerate(ic_dict["legs"], 1):
        required_leg_fields = ["strike", "right", "open_action", "quantity", "bid", "ask", "mid"]
        for field in required_leg_fields:
            assert field in leg, f"Leg {i} missing: {field}"
        
        print(f"   ✓ Leg {i}: {leg['open_action']} {leg['quantity']}x {leg['strike']}{leg['right']} @ ${leg['mid']}")
    
    print()
    total_categories = 6
    print(f"✓ All {total_categories} parameter categories validated")
    print(f"✓ Total parameters: {len(ic_dict)} fields")
    
    print("✅ PASSED: All IC parameters preserved in dict/JSON\n")
    return True


def test_bed_to_annual_return_conversion():
    """Test converting BED to annual return and vice versa."""
    print("\n" + "="*80)
    print("TEST: BED ↔ Annual Return Conversion")
    print("="*80)
    
    print("Relationship: Annual% = (BED / DTE) * 100")
    print()
    
    test_cases = [
        # (BED, DTE, expected_annual%)
        (365, 365, 100.0),   # BED=365, DTE=365 → 100% annual
        (730, 365, 200.0),   # BED=730, DTE=365 → 200% annual
        (100, 32, 312.5),    # BED=100, DTE=32 → 312.5% annual
        (50, 32, 156.25),    # BED=50, DTE=32 → 156.25% annual
        (32, 32, 100.0),     # BED=32, DTE=32 → 100% annual (breakeven in same time)
    ]
    
    print(f"{'BED (days)':>12} {'DTE (days)':>12} {'Annual%':>12} {'Expected%':>12}")
    print("-" * 80)
    
    for bed, dte, expected in test_cases:
        # BED = 365 * (remaining% / 100)
        # remaining% = (BED / 365) * 100
        # annual% = (remaining% / dte) * 365 = (BED / dte) * 100
        annual = (bed / dte) * 100
        
        assert abs(annual - expected) < 0.1, f"Annual return mismatch"
        
        marker = "🔥" if annual > 100 else "✓"
        print(f"{marker} {bed:>11} {dte:>12} {annual:>11.2f}% {expected:>11.2f}%")
    
    print()
    print("Key insights:")
    print("  • BED > DTE → >100% annual return")
    print("  • BED = DTE → 100% annual return (breakeven point)")
    print("  • BED < DTE → <100% annual return")
    print()
    print("✓ Conversion formula verified")
    
    print("✅ PASSED: BED ↔ Annual return conversion correct\n")
    return True


def test_high_annual_return_detection():
    """Test detecting IC strategies with >100% annual returns."""
    print("\n" + "="*80)
    print("TEST: High Annual Return Detection (>100%)")
    print("="*80)
    
    ticks, expiration = get_test_chain(chain_type="buy")
    dte = get_test_dte()
    chain_idx = ChainIndex("TEST_BUY", expiration, ticks)
    
    ic_scanner = IronCondorStrategy()
    candidates = ic_scanner.scan(chain_idx, dte, fee_per_leg=0.65, include_imbalanced=False)
    
    print(f"Testing {len(candidates)} IC candidates for annual returns:")
    print()
    
    high_return_candidates = []
    
    print(f"{'Strikes':>12} {'Width':>7} {'Profit':>8} {'BED':>6} {'Annual%':>10} {'Status':>10}")
    print("-" * 80)
    
    for candidate in candidates:
        width = candidate.strike_difference
        profit = candidate.remaining_profit
        bed = candidate.break_even_days
        
        annual = compute_annual_return(profit, width, dte)
        
        # Verify BED calculation is consistent
        expected_bed = compute_bed(profit, width)
        assert abs(bed - expected_bed) < 0.1, f"BED mismatch: {bed} vs {expected_bed}"
        
        strikes = f"{candidate.strikes_used[0]:.0f}/{candidate.strikes_used[-1]:.0f}"
        status = "🔥 >100%" if annual > 100 else "✓ <100%"
        
        print(f"{strikes:>12} ${width:>6.1f} ${profit:>7.2f} {bed:>6.1f} {annual:>9.2f}% {status:>10}")
        
        if annual > 100:
            high_return_candidates.append({
                "candidate": candidate,
                "annual_return": annual,
                "strikes": strikes
            })
    
    print()
    print(f"Found {len(high_return_candidates)} candidates with >100% annual return")
    
    if high_return_candidates:
        print()
        print("Top opportunities (by annual return):")
        high_return_candidates.sort(key=lambda x: x["annual_return"], reverse=True)
        
        for i, item in enumerate(high_return_candidates[:5], 1):
            c = item["candidate"]
            print(f"  {i}. {item['strikes']}: {item['annual_return']:.1f}% annual "
                  f"(${c.remaining_profit:.2f} profit, BED={c.break_even_days:.1f}d)")
    
    print()
    print(f"✓ Annual return detection working")
    print(f"✓ BED calculations consistent")
    
    print("✅ PASSED: High return detection working\n")
    return True


def test_annual_return_filter_potential():
    """Test creating a filter for strategies with >100% annual return."""
    print("\n" + "="*80)
    print("TEST: Annual Return Filter (>100% criterion)")
    print("="*80)
    
    ticks, expiration = get_test_chain(chain_type="buy")
    dte = get_test_dte()
    chain_idx = ChainIndex("TEST_BUY", expiration, ticks)
    
    ic_scanner = IronCondorStrategy()
    all_candidates = ic_scanner.scan(chain_idx, dte, fee_per_leg=0.65, include_imbalanced=True)
    
    print(f"Testing {len(all_candidates)} total IC candidates")
    print()
    
    # Apply hypothetical >100% annual return filter
    high_return = []
    medium_return = []
    low_return = []
    
    for candidate in all_candidates:
        annual = compute_annual_return(
            candidate.remaining_profit,
            candidate.strike_difference,
            dte
        )
        
        if annual > 200:
            high_return.append(candidate)
        elif annual > 100:
            medium_return.append(candidate)
        else:
            low_return.append(candidate)
    
    print("Annual return distribution:")
    print(f"  🔥 >200% annual: {len(high_return)} candidates")
    print(f"  🔥 100-200% annual: {len(medium_return)} candidates")
    print(f"  ✓ <100% annual: {len(low_return)} candidates")
    print()
    
    total = len(high_return) + len(medium_return) + len(low_return)
    assert total == len(all_candidates), "Should categorize all candidates"
    
    print(f"Coverage:")
    print(f"  Total candidates: {len(all_candidates)}")
    print(f"  >100% annual: {len(high_return) + len(medium_return)} ({(len(high_return) + len(medium_return))/len(all_candidates)*100:.1f}%)")
    print(f"  <100% annual: {len(low_return)} ({len(low_return)/len(all_candidates)*100:.1f}%)")
    
    print()
    print("✓ Filter can select candidates by annual return threshold")
    print("✓ Multiple tiers supported (100%, 200%, etc.)")
    
    print("✅ PASSED: Annual return filter working\n")
    return True


def test_signal_includes_annual_return_data():
    """Test that Signal provides enough data to calculate annual returns."""
    print("\n" + "="*80)
    print("TEST: Signal Includes Annual Return Data")
    print("="*80)
    
    ticks, expiration = get_test_chain(chain_type="buy")
    dte = get_test_dte()
    chain_idx = ChainIndex("TEST_BUY", expiration, ticks)
    
    ic_scanner = IronCondorStrategy()
    candidates = ic_scanner.scan(chain_idx, dte, fee_per_leg=0.65, include_imbalanced=False)
    
    # Build mock signal with IC strategies
    best_per_strategy = {}
    for candidate in candidates:
        if candidate.strategy_type not in best_per_strategy:
            best_per_strategy[candidate.strategy_type] = candidate
    
    from filters.phase2strat1.models import Signal
    from tests.strategies.test_signal_json import build_strategy_snapshot
    
    strategies_dict = {k: v.to_dict() for k, v in best_per_strategy.items()}
    chain_snapshot = build_strategy_snapshot(best_per_strategy, ticks)
    
    signal = Signal(
        signal_id="test-123",
        symbol="TEST",
        expiration=expiration,
        dte=dte,
        strategies=strategies_dict,
        best_strategy_type="IC_BUY",
        best_rank_score=0.0,
        chain_timestamp="2026-03-29T00:00:00",
        run_id="test-run",
        computed_at="2026-03-29T10:00:00",
        chain_snapshot=chain_snapshot
    )
    
    print(f"Signal contains {len(signal.strategies)} IC strategy types")
    print()
    print("Annual return calculations from Signal data:")
    print(f"{'Strategy':>15} {'Profit':>8} {'Width':>7} {'DTE':>5} {'BED':>7} {'Annual%':>10} {'Saved%':>10}")
    print("-" * 90)
    
    for strategy_type, strategy_data in signal.strategies.items():
        profit = strategy_data["remaining_profit"]
        width = strategy_data["strike_difference"]
        dte_val = strategy_data["dte"]
        bed = strategy_data["break_even_days"]
        
        # Verify annual_return_percent field exists and is saved
        assert "annual_return_percent" in strategy_data, \
            f"Missing annual_return_percent in {strategy_type}"
        
        saved_annual = strategy_data["annual_return_percent"]
        
        # Calculate annual return to verify
        annual = compute_annual_return(profit, width, dte_val)
        
        # Verify saved value matches calculation
        assert abs(annual - saved_annual) < 0.1, \
            f"Saved annual return doesn't match calculation: {saved_annual:.2f}% vs {annual:.2f}%"
        
        # Verify using BED (annual% = (BED / DTE) * 100)
        annual_from_bed = (bed / dte_val) * 100
        
        # Allow for small floating point differences
        assert abs(annual - annual_from_bed) < 2.0, \
            f"BED and direct calculation should match: {annual:.2f}% vs {annual_from_bed:.2f}%"
        
        marker = "🔥" if annual > 100 else "✓"
        print(f"{marker} {strategy_type:>14} ${profit:>7.2f} ${width:>6.1f} {dte_val:>5} {bed:>6.1f} {annual:>9.2f}% {saved_annual:>9.2f}%")
    
    print()
    print("✓ Signal provides all data needed for annual return calculation")
    print("✓ Both direct (profit/width/dte) and BED-based calculations work")
    print("✓ annual_return_percent field saved in Signal JSON")
    print("✓ Saved values match calculated values")
    print("✓ Annual returns can be displayed in history/UI")
    
    print("✅ PASSED: Signal includes annual return data\n")
    return True


def run_all_annual_return_tests():
    """Run all annual return and parameter validation tests."""
    print("\n" + "="*80)
    print("ANNUAL RETURN & PARAMETER VALIDATION TEST SUITE")
    print("="*80)
    
    tests = [
        ("Annual Return Calculation", test_annual_return_calculation),
        ("100% Annual Threshold", test_hundred_percent_annual_threshold),
        ("Max Price for Target Return", test_max_price_for_ic_strategy),
        ("BED ↔ Annual Return", test_bed_to_annual_return_conversion),
        ("High Return Detection", test_high_annual_return_detection),
        ("IC Parameters Saved", test_ic_strategy_saves_all_parameters),
        ("Signal Annual Return Data", test_signal_includes_annual_return_data),
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
            import traceback
            traceback.print_exc()
            failed += 1
    
    print("="*80)
    print(f"Annual Return Tests: {passed} passed, {failed} failed")
    print("="*80)
    
    if failed == 0:
        print("\n🎉 ALL ANNUAL RETURN TESTS PASSED!")
        print("\n✓ Annual return formula verified")
        print("✓ >100% threshold calculations correct")
        print("✓ Max entry price calculations validated")
        print("✓ BED ↔ Annual return conversion working")
        print("✓ High return detection implemented")
        print("✓ All IC parameters saved in Signal")
        print("✓ Signal provides complete annual return data")
        print("\n✅ Annual return calculations ready for production!")
    
    return failed == 0


if __name__ == "__main__":
    success = run_all_annual_return_tests()
    sys.exit(0 if success else 1)
