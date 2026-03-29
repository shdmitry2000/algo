#!/usr/bin/env python3
"""
Daily Maintenance Script
Orchestrates Redis backup followed by cleanup.

Usage:
  python cli/daily_maintenance.py
  
Designed to run via cron at 00:00 daily.
"""
import subprocess
import sys
import logging
from datetime import datetime
from pathlib import Path

# Setup logging
log_dir = Path("logs")
log_dir.mkdir(exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.FileHandler(log_dir / "maintenance.log"),
        logging.StreamHandler(sys.stdout)
    ]
)

logger = logging.getLogger(__name__)


def run_command(cmd: list[str], description: str) -> bool:
    """Run a command and return success status."""
    logger.info(f"Starting: {description}")
    try:
        result = subprocess.run(
            cmd,
            check=True,
            capture_output=True,
            text=True
        )
        logger.info(f"✓ {description} completed")
        if result.stdout:
            for line in result.stdout.strip().split('\n'):
                logger.info(f"  {line}")
        return True
    except subprocess.CalledProcessError as e:
        logger.error(f"✗ {description} failed with exit code {e.returncode}")
        if e.stdout:
            logger.error(f"STDOUT: {e.stdout}")
        if e.stderr:
            logger.error(f"STDERR: {e.stderr}")
        return False


def main():
    logger.info("=" * 70)
    logger.info(f"Daily Maintenance Started: {datetime.utcnow().isoformat()}")
    logger.info("=" * 70)
    
    # Step 1: Backup
    backup_success = run_command(
        ["./.conda/bin/python", "cli/redis_backup.py"],
        "Redis Backup"
    )
    
    if not backup_success:
        logger.error("❌ Backup failed, aborting cleanup for safety")
        sys.exit(1)
    
    # Step 2: Cleanup
    cleanup_success = run_command(
        ["./.conda/bin/python", "cli/redis_cleanup.py", "--all"],
        "Redis Cleanup"
    )
    
    if not cleanup_success:
        logger.error("❌ Cleanup failed")
        sys.exit(1)
    
    logger.info("=" * 70)
    logger.info("✅ Daily maintenance completed successfully")
    logger.info("=" * 70)


if __name__ == "__main__":
    main()
