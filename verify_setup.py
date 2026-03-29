#!/usr/bin/env python3
"""
System verification script.
Checks that all components are properly configured and working.
"""
import sys
import os
from pathlib import Path

project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

def check_python_version():
    """Check Python version is 3.9+"""
    print("Checking Python version...")
    version = sys.version_info
    if version.major >= 3 and version.minor >= 9:
        print(f"  ✅ Python {version.major}.{version.minor}.{version.micro}")
        return True
    else:
        print(f"  ❌ Python {version.major}.{version.minor}.{version.micro} (need 3.9+)")
        return False


def check_dependencies():
    """Check required Python packages."""
    print("\nChecking dependencies...")
    
    packages = {
        'redis': 'Redis client',
        'dotenv': 'Environment loader',
    }
    
    optional_packages = {
        'yfinance': 'YFinance provider',
        'requests': 'Tradier provider',
        'thetadata': 'Theta provider',
    }
    
    all_ok = True
    
    for package, description in packages.items():
        try:
            __import__(package)
            print(f"  ✅ {package} ({description})")
        except ImportError:
            print(f"  ❌ {package} ({description}) - pip install {package}")
            all_ok = False
    
    print("\nOptional dependencies:")
    for package, description in optional_packages.items():
        try:
            __import__(package)
            print(f"  ✅ {package} ({description})")
        except ImportError:
            print(f"  ⚠️  {package} ({description}) - pip install {package}")
    
    return all_ok


def check_env_file():
    """Check .env file exists."""
    print("\nChecking .env configuration...")
    
    env_path = project_root / '.env'
    example_path = project_root / '.env.example'
    
    if not example_path.exists():
        print(f"  ❌ .env.example not found")
        return False
    else:
        print(f"  ✅ .env.example exists")
    
    if not env_path.exists():
        print(f"  ⚠️  .env not found")
        print(f"     Run: cp .env.example .env")
        return False
    else:
        print(f"  ✅ .env exists")
    
    # Load and check key variables
    from dotenv import load_dotenv
    load_dotenv()
    
    provider = os.getenv('DATA_PROVIDER', 'yfinance')
    print(f"  ✅ DATA_PROVIDER={provider}")
    
    redis_host = os.getenv('REDIS_HOST', '127.0.0.1')
    redis_port = os.getenv('REDIS_PORT', '6379')
    print(f"  ✅ REDIS_HOST={redis_host}")
    print(f"  ✅ REDIS_PORT={redis_port}")
    
    return True


def check_redis_connection():
    """Check Redis is running and accessible."""
    print("\nChecking Redis connection...")
    
    try:
        import redis
        from dotenv import load_dotenv
        load_dotenv()
        
        host = os.getenv('REDIS_HOST', '127.0.0.1')
        port = int(os.getenv('REDIS_PORT', '6379'))
        
        r = redis.Redis(host=host, port=port, socket_connect_timeout=2)
        r.ping()
        
        print(f"  ✅ Redis connected at {host}:{port}")
        
        # Check some stats
        info = r.info()
        print(f"  ✅ Redis version: {info.get('redis_version', 'unknown')}")
        print(f"  ✅ Keys in DB: {r.dbsize()}")
        
        return True
        
    except Exception as e:
        print(f"  ❌ Redis connection failed: {e}")
        print(f"     Run: redis-server")
        return False


def check_provider_availability():
    """Check which providers are available."""
    print("\nChecking provider availability...")
    
    from dotenv import load_dotenv
    load_dotenv()
    
    providers_status = {}
    
    # YFinance
    try:
        from datagathering.providers.yfinance_provider import YFinanceProvider
        providers_status['yfinance'] = '✅ Available (no credentials needed)'
    except ImportError:
        providers_status['yfinance'] = '⚠️ Not installed (pip install yfinance)'
    
    # Tradier
    try:
        from datagathering.providers.tradier_provider import TradierProvider
        token = os.getenv('TRADIER_ACCESS_TOKEN', '')
        if token and token != 'your_tradier_token_here':
            providers_status['tradier'] = '✅ Available with token'
        else:
            providers_status['tradier'] = '⚠️ Available (needs TRADIER_ACCESS_TOKEN)'
    except ImportError:
        providers_status['tradier'] = '⚠️ Not installed (pip install requests)'
    
    # Theta
    try:
        from datagathering.providers.theta_provider import ThetaProvider
        username = os.getenv('THETA_USERNAME', '')
        password = os.getenv('THETA_PASSWORD', '')
        if username and password and username != 'your_theta_username':
            providers_status['theta'] = '✅ Available with credentials'
        else:
            providers_status['theta'] = '⚠️ Available (needs THETA_USERNAME/PASSWORD)'
    except ImportError:
        providers_status['theta'] = '⚠️ Not installed (pip install thetadata)'
    
    # Schwab
    try:
        from datagathering.providers.schwab_provider import SchwabProvider
        providers_status['schwab'] = '⚠️ Stub only (Phase 3/4)'
    except ImportError:
        providers_status['schwab'] = '❌ Not found'
    
    for provider, status in providers_status.items():
        print(f"  {status:50} ({provider})")
    
    return True


def check_tests():
    """Check that tests can run."""
    print("\nChecking test framework...")
    
    test_files = [
        'tests/providers/test_all_providers.py',
        'tests/strategies/run_all_tests.py',
        'tests/run_all_tests.py'
    ]
    
    all_exist = True
    for test_file in test_files:
        path = project_root / test_file
        if path.exists():
            print(f"  ✅ {test_file}")
        else:
            print(f"  ❌ {test_file} not found")
            all_exist = False
    
    return all_exist


def check_file_structure():
    """Check critical files exist."""
    print("\nChecking file structure...")
    
    critical_paths = [
        'datagathering/providers/base_provider.py',
        'datagathering/pipeline.py',
        'filters/phase2strat1/scan.py',
        'filters/phase2strat1/strategies/iron_condor.py',
        'cli/run_phase2_scan.py',
        'storage/cache_manager.py',
        'README.md'
    ]
    
    all_exist = True
    for path_str in critical_paths:
        path = project_root / path_str
        if path.exists():
            print(f"  ✅ {path_str}")
        else:
            print(f"  ❌ {path_str} not found")
            all_exist = False
    
    return all_exist


def main():
    """Run all verification checks."""
    print("="*80)
    print(" "*25 + "SYSTEM VERIFICATION")
    print("="*80)
    
    checks = [
        ("Python Version", check_python_version),
        ("Dependencies", check_dependencies),
        ("Environment Config", check_env_file),
        ("Redis Connection", check_redis_connection),
        ("Provider Availability", check_provider_availability),
        ("Test Framework", check_tests),
        ("File Structure", check_file_structure),
    ]
    
    results = {}
    
    for check_name, check_func in checks:
        try:
            result = check_func()
            results[check_name] = result
        except Exception as e:
            print(f"\n❌ {check_name} check crashed: {e}")
            results[check_name] = False
    
    # Summary
    print("\n" + "="*80)
    print(" "*30 + "VERIFICATION RESULTS")
    print("="*80)
    
    for check_name, result in results.items():
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status:10} {check_name}")
    
    print("="*80)
    
    passed = sum(1 for r in results.values() if r)
    total = len(results)
    
    print(f"\nChecks: {passed}/{total} passed")
    
    if passed == total:
        print("\n🎉 ALL CHECKS PASSED!")
        print("\n✅ System is properly configured and ready to use")
        print("\nNext steps:")
        print("  1. Run tests: python tests/run_all_tests.py")
        print("  2. Run scan: python cli/run_phase2_scan.py")
        print("  3. Check results: redis-cli KEYS signal:*")
        return True
    else:
        print(f"\n❌ {total - passed} check(s) failed")
        print("\nPlease fix the issues above and run again.")
        return False


if __name__ == '__main__':
    success = main()
    sys.exit(0 if success else 1)
