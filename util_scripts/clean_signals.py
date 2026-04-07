#!/usr/bin/env python3
"""
Clean all Phase 2 signals from Redis.

This script removes:
- All active signals (SIGNAL:ACTIVE:*)
- All gate locks (SIGNAL:GATE:*)
- Signal history (SIGNAL:HISTORY)
- Run metadata (SIGNAL:RUN:*, SIGNAL:LATEST_RUN)

Keeps:
- Phase 1 data (CHAIN:*)
"""
import redis
import sys
from typing import List

def connect_redis():
    """Connect to Redis."""
    try:
        client = redis.Redis(host='localhost', port=6379, decode_responses=True)
        client.ping()
        return client
    except redis.ConnectionError:
        print("❌ Error: Cannot connect to Redis")
        print("   Make sure Redis is running: docker compose up -d")
        sys.exit(1)

def get_keys_by_pattern(client: redis.Redis, pattern: str) -> List[str]:
    """Get all keys matching pattern."""
    return client.keys(pattern)

def clean_signals(dry_run: bool = False):
    """Clean all Phase 2 signals from Redis."""
    print("\n" + "="*60)
    print("REDIS SIGNAL CLEANUP")
    print("="*60 + "\n")
    
    if dry_run:
        print("🔍 DRY RUN MODE - No data will be deleted\n")
    else:
        print("⚠️  LIVE MODE - Data will be permanently deleted\n")
    
    client = connect_redis()
    
    # Patterns to clean
    patterns = [
        ("SIGNAL:ACTIVE:*", "Active signals"),
        ("SIGNAL:GATE:*", "Gate locks"),
        ("SIGNAL:HISTORY", "Signal history"),
        ("SIGNAL:RUN:*", "Run metadata"),
        ("SIGNAL:LATEST_RUN", "Latest run pointer"),
    ]
    
    total_deleted = 0
    
    for pattern, description in patterns:
        if pattern == "SIGNAL:HISTORY" or pattern == "SIGNAL:LATEST_RUN":
            # Single key
            if client.exists(pattern):
                if pattern == "SIGNAL:HISTORY":
                    count = client.llen(pattern)
                    print(f"📋 {description}: {count} events")
                else:
                    print(f"📋 {description}: 1 key")
                
                if not dry_run:
                    client.delete(pattern)
                    total_deleted += 1
            else:
                print(f"📋 {description}: 0 keys (already clean)")
        else:
            # Pattern match
            keys = get_keys_by_pattern(client, pattern)
            count = len(keys)
            print(f"📋 {description}: {count} keys")
            
            if count > 0 and not dry_run:
                for key in keys:
                    client.delete(key)
                total_deleted += count
    
    # Verify CHAIN data is still there
    chain_keys = get_keys_by_pattern(client, "CHAIN:*")
    print(f"\n✅ Phase 1 data preserved: {len(chain_keys)} CHAIN:* keys")
    
    print("\n" + "="*60)
    if dry_run:
        print(f"🔍 DRY RUN COMPLETE - Would delete {total_deleted} keys")
        print("\nRun without --dry-run to actually delete:")
        print("  python util_scripts/clean_signals.py")
    else:
        print(f"✅ CLEANUP COMPLETE - Deleted {total_deleted} keys")
        print("\nRedis is now clean and ready for fresh signals!")
    print("="*60 + "\n")

def main():
    """Main entry point."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Clean Phase 2 signals from Redis")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be deleted without actually deleting"
    )
    
    args = parser.parse_args()
    
    if not args.dry_run:
        print("\n⚠️  WARNING: This will permanently delete all Phase 2 signals!")
        print("   - Active signals (SIGNAL:ACTIVE:*)")
        print("   - Gate locks (SIGNAL:GATE:*)")
        print("   - Signal history (SIGNAL:HISTORY)")
        print("   - Run metadata (SIGNAL:RUN:*)")
        print("\n   Phase 1 data (CHAIN:*) will be preserved.\n")
        
        response = input("Are you sure? Type 'yes' to continue: ")
        if response.lower() != 'yes':
            print("\n❌ Cleanup cancelled")
            sys.exit(0)
    
    clean_signals(dry_run=args.dry_run)

if __name__ == "__main__":
    main()
