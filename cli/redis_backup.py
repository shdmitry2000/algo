#!/usr/bin/env python3
"""
Redis Backup Script
Exports all Redis data to JSON files before cleanup.

Usage:
  python cli/redis_backup.py [--retention-days 30]
"""
import argparse
import json
import os
import redis
import tarfile
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Any
from dotenv import load_dotenv

load_dotenv()

BACKUP_DIR = Path("backups")


def get_redis_client() -> redis.Redis:
    """Get Redis client."""
    host = os.getenv("REDIS_HOST", "127.0.0.1")
    port = int(os.getenv("REDIS_PORT", "6379"))
    return redis.Redis(host=host, port=port, decode_responses=True)


def backup_keys_by_pattern(client: redis.Redis, pattern: str, filename: str, backup_path: Path) -> int:
    """Backup all keys matching a pattern to a JSON file."""
    keys = client.keys(pattern)
    data = {}
    
    for key in keys:
        key_type = client.type(key)
        
        if key_type == "string":
            data[key] = client.get(key)
        elif key_type == "hash":
            data[key] = client.hgetall(key)
        elif key_type == "list":
            data[key] = client.lrange(key, 0, -1)
        elif key_type == "set":
            data[key] = list(client.smembers(key))
        elif key_type == "zset":
            data[key] = client.zrange(key, 0, -1, withscores=True)
    
    output_file = backup_path / filename
    with open(output_file, 'w') as f:
        json.dump(data, f, indent=2)
    
    print(f"  ✓ {filename}: {len(keys)} keys ({output_file.stat().st_size / 1024:.1f} KB)")
    return len(keys)


def create_backup(retention_days: int = 30) -> None:
    """Create a complete backup of Redis data."""
    # Create backup directory with timestamp
    timestamp = datetime.utcnow().strftime("%Y-%m-%d_%H-%M-%S")
    backup_path = BACKUP_DIR / timestamp
    backup_path.mkdir(parents=True, exist_ok=True)
    
    print(f"\n📦 Creating Redis backup: {backup_path}")
    print("=" * 60)
    
    client = get_redis_client()
    
    # Backup by namespace
    total_keys = 0
    manifest = {
        "timestamp": datetime.utcnow().isoformat(),
        "namespaces": {}
    }
    
    namespaces = [
        ("CHAIN:*", "chains.json", "Phase 1 option chain data"),
        ("CHAIN:META:*", "chain_meta.json", "Chain metadata (timestamps)"),
        ("SIGNAL:ACTIVE:*", "signals.json", "Active signals"),
        ("SIGNAL:GATE:*", "gates.json", "Gate status"),
        ("SIGNAL:HISTORY", "history.json", "Signal history log"),
        ("SIGNAL:RUN:*", "run_metadata.json", "Scan run metadata"),
        ("SIGNAL:LATEST_RUN", "latest_run.json", "Latest run ID"),
        ("SCAN:META:*", "scan_meta.json", "Scan metadata (freshness tracking)")
    ]
    
    for pattern, filename, description in namespaces:
        count = backup_keys_by_pattern(client, pattern, filename, backup_path)
        total_keys += count
        manifest["namespaces"][pattern] = {
            "description": description,
            "filename": filename,
            "key_count": count
        }
    
    # Save manifest
    manifest_file = backup_path / "manifest.json"
    with open(manifest_file, 'w') as f:
        json.dump(manifest, f, indent=2)
    
    print(f"\n  ✓ manifest.json: backup metadata")
    print(f"\n📊 Total: {total_keys} keys backed up")
    
    # Create compressed archive
    archive_name = f"{timestamp}.tar.gz"
    archive_path = BACKUP_DIR / archive_name
    
    print(f"\n🗜️  Compressing to {archive_name}...")
    with tarfile.open(archive_path, "w:gz") as tar:
        tar.add(backup_path, arcname=timestamp)
    
    archive_size_mb = archive_path.stat().st_size / (1024 * 1024)
    print(f"  ✓ Archive created: {archive_size_mb:.2f} MB")
    
    # Cleanup old backups
    cleanup_old_backups(retention_days)
    
    print(f"\n✅ Backup complete: {archive_path}")


def cleanup_old_backups(retention_days: int) -> None:
    """Remove backups older than retention period."""
    if not BACKUP_DIR.exists():
        return
    
    cutoff_date = datetime.utcnow() - timedelta(days=retention_days)
    removed = 0
    
    for item in BACKUP_DIR.iterdir():
        if item.is_dir():
            # Check directory timestamp
            try:
                dir_date = datetime.strptime(item.name.split('_')[0], "%Y-%m-%d")
                if dir_date < cutoff_date:
                    import shutil
                    shutil.rmtree(item)
                    removed += 1
                    print(f"  🗑️  Removed old backup: {item.name}")
            except (ValueError, IndexError):
                pass  # Not a timestamped backup directory
        
        elif item.suffix == '.gz':
            # Check archive timestamp
            try:
                archive_date = datetime.strptime(item.stem.split('_')[0], "%Y-%m-%d")
                if archive_date < cutoff_date:
                    item.unlink()
                    removed += 1
                    print(f"  🗑️  Removed old archive: {item.name}")
            except (ValueError, IndexError):
                pass
    
    if removed > 0:
        print(f"\n🧹 Cleaned up {removed} old backups (retention: {retention_days} days)")


def main():
    parser = argparse.ArgumentParser(description="Backup Redis data to JSON files")
    parser.add_argument(
        "--retention-days",
        type=int,
        default=30,
        help="Number of days to retain old backups (default: 30)"
    )
    args = parser.parse_args()
    
    create_backup(args.retention_days)


if __name__ == "__main__":
    main()
