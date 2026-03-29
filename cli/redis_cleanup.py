#!/usr/bin/env python3
"""
Redis Cleanup Script
Selectively remove Redis keys by namespace.

Usage:
  python cli/redis_cleanup.py --all
  python cli/redis_cleanup.py --chains --signals
  python cli/redis_cleanup.py --dry-run --all
"""
import argparse
import os
import redis
from dotenv import load_dotenv

load_dotenv()


def get_redis_client() -> redis.Redis:
    """Get Redis client."""
    host = os.getenv("REDIS_HOST", "127.0.0.1")
    port = int(os.getenv("REDIS_PORT", "6379"))
    return redis.Redis(host=host, port=port, decode_responses=True)


def cleanup_namespace(client: redis.Redis, pattern: str, description: str, dry_run: bool = False) -> int:
    """Remove all keys matching a pattern."""
    keys = client.keys(pattern)
    
    if not keys:
        print(f"  • {description}: no keys found")
        return 0
    
    if dry_run:
        print(f"  • {description}: {len(keys)} keys (DRY RUN - not deleted)")
        return len(keys)
    
    # Delete in batches for performance
    deleted = 0
    batch_size = 1000
    
    for i in range(0, len(keys), batch_size):
        batch = keys[i:i + batch_size]
        deleted += client.delete(*batch)
    
    print(f"  ✓ {description}: {deleted} keys deleted")
    return deleted


def main():
    parser = argparse.ArgumentParser(description="Clean up Redis data by namespace")
    parser.add_argument("--chains", action="store_true", help="Remove CHAIN:* keys (Phase 1 data)")
    parser.add_argument("--signals", action="store_true", help="Remove SIGNAL:ACTIVE:* keys")
    parser.add_argument("--gates", action="store_true", help="Remove SIGNAL:GATE:* keys")
    parser.add_argument("--history", action="store_true", help="Remove SIGNAL:HISTORY")
    parser.add_argument("--scan-meta", action="store_true", help="Remove SCAN:META:* keys")
    parser.add_argument("--all", action="store_true", help="Remove all keys (all namespaces)")
    parser.add_argument("--dry-run", action="store_true", help="Show what would be deleted without deleting")
    
    args = parser.parse_args()
    
    # Validate arguments
    if not any([args.chains, args.signals, args.gates, args.history, args.scan_meta, args.all]):
        parser.error("At least one cleanup option must be specified")
    
    client = get_redis_client()
    
    mode = "DRY RUN" if args.dry_run else "CLEANUP"
    print(f"\n🧹 Redis {mode}")
    print("=" * 60)
    
    total_deleted = 0
    
    if args.all or args.chains:
        total_deleted += cleanup_namespace(client, "CHAIN:*", "Option chain data (CHAIN:*)", args.dry_run)
        total_deleted += cleanup_namespace(client, "CHAIN:META:*", "Chain metadata (CHAIN:META:*)", args.dry_run)
    
    if args.all or args.signals:
        total_deleted += cleanup_namespace(client, "SIGNAL:ACTIVE:*", "Active signals (SIGNAL:ACTIVE:*)", args.dry_run)
        total_deleted += cleanup_namespace(client, "SIGNAL:RUN:*", "Run metadata (SIGNAL:RUN:*)", args.dry_run)
        total_deleted += cleanup_namespace(client, "SIGNAL:LATEST_RUN", "Latest run ID", args.dry_run)
    
    if args.all or args.gates:
        total_deleted += cleanup_namespace(client, "SIGNAL:GATE:*", "Gate status (SIGNAL:GATE:*)", args.dry_run)
    
    if args.all or args.history:
        total_deleted += cleanup_namespace(client, "SIGNAL:HISTORY", "Signal history (SIGNAL:HISTORY)", args.dry_run)
    
    if args.all or args.scan_meta:
        total_deleted += cleanup_namespace(client, "SCAN:META:*", "Scan metadata (SCAN:META:*)", args.dry_run)
    
    print("=" * 60)
    if args.dry_run:
        print(f"📊 {total_deleted} keys would be deleted (dry run)")
    else:
        print(f"✅ {total_deleted} keys deleted")


if __name__ == "__main__":
    main()
