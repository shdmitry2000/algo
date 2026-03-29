"""
Phase 3 Terminator — Robust timeout-based signal termination.

Monitors SIGNAL:ACTIVE:* keys and terminates signals that exceed timeout threshold.
If Phase 3 order execution is not performed within TIMEOUT_SECONDS, the signal is
cleared with open_fail status to unlock the gate.

This allows the system to continuously cycle through signals until Phase 3 is implemented.

Run with: python cli/phase3_terminator.py
"""
import time
import logging
import sys
import os
from datetime import datetime, timezone

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from storage.signal_cache import (
    list_active_signals,
    record_phase3_open_failure,
    get_gate
)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s'
)
logger = logging.getLogger(__name__)

# Timeout threshold in seconds
TIMEOUT_SECONDS = 60


def parse_iso_timestamp(ts_str: str) -> datetime:
    """Parse ISO timestamp string to datetime object (UTC, timezone-aware)."""
    # Remove 'Z' suffix if present and replace with +00:00
    ts_str = ts_str.replace('Z', '+00:00')
    
    # Parse as timezone-aware datetime
    try:
        dt = datetime.fromisoformat(ts_str)
    except ValueError:
        # If no timezone info, assume UTC
        if '+' not in ts_str and ts_str[-6:-3] != '-':
            dt = datetime.fromisoformat(ts_str).replace(tzinfo=timezone.utc)
        else:
            raise
    
    # Ensure it's UTC
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    
    return dt


def calculate_signal_age_seconds(gate_updated_at: str) -> float:
    """Calculate how long a signal has been pending (in seconds)."""
    gate_time = parse_iso_timestamp(gate_updated_at)
    now = datetime.now(timezone.utc)
    return (now - gate_time).total_seconds()


def run_terminator_cycle():
    """
    One terminator cycle:
    1. List all active signals
    2. Check each signal's age via gate timestamp
    3. Terminate only signals that exceed TIMEOUT_SECONDS
    
    Returns: (processed_count, skipped_count)
    """
    signals = list_active_signals()
    
    if not signals:
        logger.debug("[terminator] No active signals to process")
        return 0, 0
    
    logger.info(f"[terminator] Found {len(signals)} active signals, checking timeouts...")
    
    processed = 0
    skipped = 0
    
    for signal in signals:
        # Get gate to check timestamp
        gate = get_gate(signal.symbol, signal.expiration)
        
        if not gate:
            logger.warning(
                f"[terminator] {signal.symbol} {signal.expiration}: "
                f"Signal exists but gate missing (inconsistent state)"
            )
            # Terminate anyway to clean up
            record_phase3_open_failure(
                signal_id=signal.signal_id,
                symbol=signal.symbol,
                expiration=signal.expiration,
                reason="missing_gate",
                detail={"terminator": "auto", "timeout_seconds": TIMEOUT_SECONDS}
            )
            processed += 1
            continue
        
        # Calculate age
        age_seconds = calculate_signal_age_seconds(gate.updated_at)
        
        if age_seconds >= TIMEOUT_SECONDS:
            logger.info(
                f"[terminator] TIMEOUT: {signal.symbol} {signal.expiration} "
                f"(age={age_seconds:.1f}s, threshold={TIMEOUT_SECONDS}s, signal_id={signal.signal_id[:8]}...)"
            )
            
            # Record failure and unlock gate
            record_phase3_open_failure(
                signal_id=signal.signal_id,
                symbol=signal.symbol,
                expiration=signal.expiration,
                reason="phase3_timeout",
                detail={
                    "terminator": "auto",
                    "timeout_seconds": TIMEOUT_SECONDS,
                    "age_seconds": round(age_seconds, 2),
                    "gate_updated_at": gate.updated_at
                }
            )
            
            logger.info(
                f"[terminator] ✓ Terminated {signal.symbol} {signal.expiration} "
                f"(gate unlocked, signal deleted)"
            )
            processed += 1
        else:
            time_remaining = TIMEOUT_SECONDS - age_seconds
            logger.debug(
                f"[terminator] SKIP: {signal.symbol} {signal.expiration} "
                f"(age={age_seconds:.1f}s, remaining={time_remaining:.1f}s)"
            )
            skipped += 1
    
    return processed, skipped


def run_continuous():
    """
    Run terminator in continuous mode.
    Checks signals every POLL_INTERVAL seconds and terminates timeouts.
    """
    POLL_INTERVAL = 5  # Check every 5 seconds
    
    logger.info("[terminator] Starting Phase 3 Terminator (continuous mode)")
    logger.info(f"[terminator] Timeout threshold: {TIMEOUT_SECONDS}s")
    logger.info(f"[terminator] Poll interval: {POLL_INTERVAL}s")
    logger.info("[terminator] Press Ctrl+C to stop")
    
    cycle = 0
    try:
        while True:
            cycle += 1
            logger.info(f"[terminator] === Cycle {cycle} ===")
            
            processed, skipped = run_terminator_cycle()
            
            if processed == 0 and skipped == 0:
                logger.info("[terminator] No signals to process")
            else:
                logger.info(
                    f"[terminator] Cycle {cycle} complete: "
                    f"terminated={processed}, skipped={skipped} (not yet timed out)"
                )
            
            logger.info(f"[terminator] Waiting {POLL_INTERVAL}s before next check...")
            time.sleep(POLL_INTERVAL)
                
    except KeyboardInterrupt:
        logger.info("[terminator] Stopped by user")


def run_once():
    """
    Run terminator once and exit.
    Useful for testing or scheduled runs.
    """
    logger.info("[terminator] Starting Phase 3 Terminator (single run)")
    logger.info(f"[terminator] Timeout threshold: {TIMEOUT_SECONDS}s")
    processed, skipped = run_terminator_cycle()
    logger.info(
        f"[terminator] Complete: terminated={processed}, "
        f"skipped={skipped} (not yet timed out)"
    )


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Phase 3 Terminator")
    parser.add_argument(
        "--mode",
        choices=["once", "continuous"],
        default="continuous",
        help="Run mode: 'once' for single cycle, 'continuous' for infinite loop"
    )
    
    args = parser.parse_args()
    
    if args.mode == "once":
        run_once()
    else:
        run_continuous()
