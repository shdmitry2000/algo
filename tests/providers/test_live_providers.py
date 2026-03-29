"""
Live provider integration tests.
Only run when credentials are configured in .env

These tests make REAL API calls to verify providers work end-to-end.
Run manually when credentials are available.

Usage:
    # Test specific provider
    python tests/providers/test_live_providers.py --provider yfinance
    python tests/providers/test_live_providers.py --provider tradier
    python tests/providers/test_live_providers.py --provider theta
    
    # Test all configured providers
    python tests/providers/test_live_providers.py --all
"""
import sys
import os
import argparse
from pathlib import Path
from typing import List

project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from datagathering.models import StandardOptionTick
from datagathering.providers.base_provider import BaseProvider


def check_provider_credentials(provider_name: str) -> bool:
    """Check if credentials are configured for provider."""
    credentials_map = {
        'yfinance': [],  # No credentials needed
        'tradier': ['TRADIER_ACCESS_TOKEN'],
        'theta': ['THETA_USERNAME', 'THETA_PASSWORD'],
        'schwab': []  # Stub - not used for data gathering
    }
    
    required = credentials_map.get(provider_name, [])
    
    if not required:
        return True
    
    missing = [cred for cred in required if not os.getenv(cred)]
    
    if missing:
        print(f"❌ Missing credentials for {provider_name}: {', '.join(missing)}")
        return False
    
    return True


def test_live_provider(provider_name: str, ticker: str = "SPY") -> bool:
    """
    Test a provider with a live API call.
    
    Args:
        provider_name: Provider to test (yfinance, tradier, theta)
        ticker: Ticker to fetch (default: SPY)
    
    Returns:
        True if test passed
    """
    print("\n" + "="*80)
    print(f"LIVE TEST: {provider_name.upper()} Provider")
    print("="*80)
    print(f"Ticker: {ticker}")
    print()
    
    # Check credentials
    if not check_provider_credentials(provider_name):
        print(f"⚠️  SKIPPED: Missing credentials")
        return False
    
    # Import and instantiate provider
    try:
        if provider_name == 'yfinance':
            from datagathering.providers.yfinance_provider import YFinanceProvider
            provider = YFinanceProvider()
        elif provider_name == 'tradier':
            from datagathering.providers.tradier_provider import TradierProvider
            provider = TradierProvider(sandbox=True)
        elif provider_name == 'theta':
            from datagathering.providers.theta_provider import ThetaProvider
            provider = ThetaProvider()
        elif provider_name == 'schwab':
            print("⚠️  SKIPPED: Schwab is for Phase 3/4 only")
            return False
        else:
            print(f"❌ Unknown provider: {provider_name}")
            return False
    except ImportError as e:
        print(f"❌ Failed to import provider: {e}")
        return False
    
    print(f"Provider: {provider.name}")
    print(f"Class: {provider.__class__.__name__}")
    print()
    
    # Make live API call
    print(f"🌐 Fetching live data for {ticker}...")
    try:
        ticks = provider.fetch_chain(ticker)
    except Exception as e:
        print(f"❌ FAILED: API call error: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    # Validate response
    if not ticks:
        print(f"⚠️  WARNING: No ticks returned (may be market closed or no options)")
        return True
    
    print(f"✓ Received {len(ticks)} ticks")
    print()
    
    # Validate data structure
    print("Validating data structure:")
    
    calls = [t for t in ticks if t.right == 'C']
    puts = [t for t in ticks if t.right == 'P']
    
    print(f"  Calls: {len(calls)}")
    print(f"  Puts: {len(puts)}")
    
    assert len(ticks) > 0, "Should have at least one tick"
    
    # Check first tick
    tick = ticks[0]
    
    print(f"\nSample tick:")
    print(f"  {tick.root} {tick.expiration} {tick.strike}{tick.right}")
    print(f"  Bid: ${tick.bid}, Ask: ${tick.ask}, Mid: ${tick.mid}")
    print(f"  Volume: {tick.volume}, OI: {tick.open_interest}")
    print(f"  Provider: {tick.provider}")
    print(f"  Timestamp: {tick.timestamp}")
    
    # Validate required fields
    assert tick.root == ticker, f"Root should be {ticker}, got {tick.root}"
    assert tick.provider == provider_name, f"Provider should be {provider_name}"
    assert tick.right in ['C', 'P'], "Right should be C or P"
    assert tick.bid >= 0, "Bid should be non-negative"
    assert tick.ask >= tick.bid, "Ask should be >= bid"
    assert tick.mid == (tick.bid + tick.ask) / 2, "Mid should be average"
    
    print()
    
    # Check expiration distribution
    expirations = sorted(set(t.expiration for t in ticks))
    print(f"Expirations: {len(expirations)}")
    if expirations:
        print(f"  First: {expirations[0]}")
        print(f"  Last: {expirations[-1]}")
    
    # Check strike distribution
    strikes = sorted(set(t.strike for t in ticks))
    print(f"Strikes: {len(strikes)}")
    if strikes:
        print(f"  Min: ${strikes[0]}")
        print(f"  Max: ${strikes[-1]}")
    
    print()
    
    # Test with pipeline
    print("Testing pipeline compatibility:")
    try:
        from filters.phase2strat1.chain_index import ChainIndex
        
        # Group by expiration (test first one)
        first_exp = expirations[0]
        exp_ticks = [t for t in ticks if t.expiration == first_exp]
        
        chain_idx = ChainIndex(ticker, first_exp, exp_ticks)
        print(f"  ✓ ChainIndex built: {len(chain_idx.calls)} calls, {len(chain_idx.puts)} puts")
        
        # Try scanning
        from filters.phase2strat1.strategies import IronCondorStrategy
        ic_scanner = IronCondorStrategy()
        candidates = ic_scanner.scan(chain_idx, dte=30, fee_per_leg=0.65, include_imbalanced=False)
        
        print(f"  ✓ IC scan: {len(candidates)} candidates")
        
        if candidates:
            best = max(candidates, key=lambda c: c.rank_score)
            print(f"  ✓ Best rank: {best.rank_score:.2f}")
            print(f"  ✓ Best BED: {best.break_even_days:.1f} days")
            print(f"  ✓ Best annual: {best.annual_return_percent:.1f}%")
        
    except Exception as e:
        print(f"  ❌ Pipeline error: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    print()
    print(f"✅ PASSED: {provider_name} live integration test")
    print()
    
    return True


def run_live_tests(providers: List[str], ticker: str = "SPY"):
    """Run live tests for specified providers."""
    print("\n" + "="*80)
    print("LIVE PROVIDER INTEGRATION TESTS")
    print("="*80)
    print("⚠️  These tests make REAL API calls")
    print(f"Testing ticker: {ticker}")
    print("="*80)
    
    results = {}
    
    for provider_name in providers:
        try:
            passed = test_live_provider(provider_name, ticker)
            results[provider_name] = passed
        except Exception as e:
            print(f"\n❌ ERROR in {provider_name}: {e}")
            import traceback
            traceback.print_exc()
            results[provider_name] = False
    
    # Summary
    print("\n" + "="*80)
    print("LIVE TEST SUMMARY")
    print("="*80)
    
    for provider, passed in results.items():
        status = "✅ PASSED" if passed else "❌ FAILED"
        print(f"{provider:>10}: {status}")
    
    print("="*80)
    
    passed_count = sum(1 for p in results.values() if p)
    total_count = len(results)
    
    print(f"\nResult: {passed_count}/{total_count} providers passed")
    
    if passed_count == total_count:
        print("\n🎉 ALL LIVE TESTS PASSED!")
    
    return passed_count == total_count


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Live provider integration tests")
    parser.add_argument(
        '--provider',
        choices=['yfinance', 'tradier', 'theta', 'schwab'],
        help='Test specific provider'
    )
    parser.add_argument(
        '--all',
        action='store_true',
        help='Test all configured providers'
    )
    parser.add_argument(
        '--ticker',
        default='SPY',
        help='Ticker to test (default: SPY)'
    )
    
    args = parser.parse_args()
    
    if args.all:
        providers = ['yfinance', 'tradier', 'theta']
    elif args.provider:
        providers = [args.provider]
    else:
        print("Usage:")
        print("  python tests/providers/test_live_providers.py --provider yfinance")
        print("  python tests/providers/test_live_providers.py --all")
        print("  python tests/providers/test_live_providers.py --provider tradier --ticker RUT")
        sys.exit(1)
    
    success = run_live_tests(providers, args.ticker)
    sys.exit(0 if success else 1)
