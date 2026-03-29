#!/usr/bin/env python3
"""
Verification script for Memory Optimization implementation.
Tests data freshness tracking, minimal snapshots, and backup/cleanup.
"""
import redis
import json
import os
from pathlib import Path

def get_redis_client():
    return redis.Redis(host='127.0.0.1', port=6379, decode_responses=True)

def test_chain_metadata():
    """Test CHAIN:META keys exist and have correct structure."""
    print("\n1. Testing CHAIN:META (freshness tracking)...")
    r = get_redis_client()
    keys = r.keys("CHAIN:META:*")
    
    if not keys:
        print("  ❌ No CHAIN:META keys found")
        return False
    
    print(f"  ✓ Found {len(keys)} CHAIN:META keys")
    
    # Check structure of first key
    sample = r.get(keys[0])
    data = json.loads(sample)
    required_fields = ['updated_at', 'tick_count', 'provider']
    
    if all(f in data for f in required_fields):
        print(f"  ✓ Structure correct: {data}")
        return True
    else:
        print(f"  ❌ Missing fields in: {data}")
        return False

def test_scan_metadata():
    """Test SCAN:META keys exist and have correct structure."""
    print("\n2. Testing SCAN:META (scan freshness)...")
    r = get_redis_client()
    keys = r.keys("SCAN:META:*")
    
    if not keys:
        print("  ❌ No SCAN:META keys found")
        return False
    
    print(f"  ✓ Found {len(keys)} SCAN:META keys")
    
    # Check structure
    sample = r.get(keys[0])
    data = json.loads(sample)
    required_fields = ['last_scan_at', 'last_chain_timestamp']
    
    if all(f in data for f in required_fields):
        print(f"  ✓ Structure correct: {data}")
        return True
    else:
        print(f"  ❌ Missing fields in: {data}")
        return False

def test_minimal_snapshots():
    """Test that history events have minimal snapshots with calculations."""
    print("\n3. Testing Minimal Snapshots...")
    r = get_redis_client()
    
    # Get recent history events
    events = r.lrange("SIGNAL:HISTORY", -100, -1)
    
    # Find a signal_upserted event
    for event_str in reversed(events):
        event = json.loads(event_str)
        if event.get('event_type') == 'signal_upserted':
            snapshot = event.get('payload', {}).get('chain_snapshot', {})
            
            if isinstance(snapshot, dict):
                chain = snapshot.get('chain', [])
                calculations = snapshot.get('calculations', {})
                
                print(f"  ✓ Found signal_upserted event")
                print(f"  ✓ Chain snapshot has {len(chain)} options (expected ~12)")
                print(f"  ✓ Calculations has {len(calculations)} fields")
                
                # Verify calculations has key fields
                key_fields = ['structure', 'dte', 'mid_entry', 'break_even_days', 'legs']
                if all(f in calculations for f in key_fields):
                    print(f"  ✓ Calculations structure correct")
                    return True
                else:
                    print(f"  ❌ Calculations missing key fields")
                    return False
            else:
                print(f"  ⚠️  Old format snapshot (list) - expected dict with chain/calculations")
                continue
    
    print("  ❌ No signal_upserted events found in recent history")
    return False

def test_backup_system():
    """Test that backup system files exist."""
    print("\n4. Testing Backup System...")
    
    files = [
        'cli/redis_backup.py',
        'cli/redis_cleanup.py',
        'cli/daily_maintenance.py',
        'setup_cron.sh'
    ]
    
    all_exist = True
    for f in files:
        path = Path(f)
        if path.exists():
            print(f"  ✓ {f}")
        else:
            print(f"  ❌ {f} not found")
            all_exist = False
    
    # Check if backups directory exists or can be created
    backup_dir = Path("backups")
    if backup_dir.exists():
        archives = list(backup_dir.glob("*.tar.gz"))
        print(f"  ✓ backups/ directory exists ({len(archives)} archives)")
    else:
        print(f"  ℹ️  backups/ directory will be created on first backup")
    
    return all_exist

def main():
    print("=" * 70)
    print("Memory Optimization Verification")
    print("=" * 70)
    
    results = []
    
    results.append(("CHAIN:META", test_chain_metadata()))
    results.append(("SCAN:META", test_scan_metadata()))
    results.append(("Minimal Snapshots", test_minimal_snapshots()))
    results.append(("Backup System", test_backup_system()))
    
    print("\n" + "=" * 70)
    print("Summary")
    print("=" * 70)
    
    for name, passed in results:
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"{status}: {name}")
    
    all_passed = all(r[1] for r in results)
    
    print("\n" + "=" * 70)
    if all_passed:
        print("✅ All tests passed!")
    else:
        print("❌ Some tests failed. Review output above.")
    print("=" * 70)
    
    return 0 if all_passed else 1

if __name__ == "__main__":
    exit(main())
