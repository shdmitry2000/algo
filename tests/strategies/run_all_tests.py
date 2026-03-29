"""
Master test runner for all strategy tests.
Runs all test suites and provides comprehensive results.
"""
import sys
import os

sys.path.insert(0, '/Users/dmitrysh/code/algotrade/algo')

from tests.strategies import test_base, test_iron_condor, test_butterfly, test_shifted_condor, test_integration, test_spread_math, test_filter, test_signal_json, test_duplicate_prevention, test_annual_returns, test_rank_score, test_pipeline


def main():
    """Run all test suites."""
    print("\n" + "="*100)
    print(" "*30 + "STRATEGY TEST MASTER SUITE")
    print(" "*20 + "Testing All 16 Strategy Variants with Synthetic Data")
    print("="*100)
    
    test_suites = [
        ("Spread Math", test_spread_math.run_all_tests),
        ("Base Strategy", test_base.run_all_base_tests),
        ("Iron Condor", test_iron_condor.run_all_iron_condor_tests),
        ("Butterfly", test_butterfly.run_all_butterfly_tests),
        ("Shifted Condor", test_shifted_condor.run_all_shifted_condor_tests),
        ("Integration", test_integration.run_all_integration_tests),
        ("Filter", test_filter.run_all_filter_tests),
        ("Signal JSON", test_signal_json.run_all_signal_tests),
        ("Duplicate Prevention", test_duplicate_prevention.run_all_duplicate_tests),
        ("Annual Returns", test_annual_returns.run_all_annual_return_tests),
        ("Rank Score", test_rank_score.run_all_rank_score_tests),
        ("Pipeline", test_pipeline.run_all_pipeline_tests)
    ]
    
    results = {}
    total_passed = 0
    total_failed = 0
    
    for suite_name, test_func in test_suites:
        print(f"\n{'='*100}")
        print(f"Running {suite_name} Test Suite...")
        print(f"{'='*100}")
        
        try:
            success = test_func()
            results[suite_name] = "PASSED" if success else "FAILED"
            
            if success:
                total_passed += 1
            else:
                total_failed += 1
                
        except Exception as e:
            print(f"\n❌ {suite_name} suite crashed: {e}")
            import traceback
            traceback.print_exc()
            results[suite_name] = "ERROR"
            total_failed += 1
    
    # Final summary
    print("\n" + "="*100)
    print(" "*40 + "FINAL TEST RESULTS")
    print("="*100)
    
    for suite_name, result in results.items():
        status_symbol = "✅" if result == "PASSED" else "❌"
        print(f"{status_symbol} {suite_name:.<50} {result}")
    
    print("="*100)
    print(f"Total Suites: {len(test_suites)}")
    print(f"Passed: {total_passed}")
    print(f"Failed: {total_failed}")
    print("="*100)
    
    if total_failed == 0:
        print("\n🎉 ALL TEST SUITES PASSED!")
        print("\n✓ 16 strategy variants implemented and verified")
        print("✓ BUY/SELL sides working correctly")
        print("✓ Imbalanced quantities working correctly")
        print("✓ Notional dominance validated")
        print("✓ Profit calculations verified")
        print("✓ Integration with scan orchestrator working")
        print("\n✅ Implementation ready for production!")
        return True
    else:
        print(f"\n❌ {total_failed} test suite(s) failed")
        return False


if __name__ == '__main__':
    success = main()
    sys.exit(0 if success else 1)
