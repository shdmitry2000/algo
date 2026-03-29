"""
CLI runner for Phase 2 signal scan.
"""
import sys
import os
import logging

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from filters.phase2strat1.scan import run_scan

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s'
)

logger = logging.getLogger(__name__)


def main():
    """Run Phase 2 scan and print summary."""
    logger.info("=" * 60)
    logger.info("Phase 2 Signal Scan — Strategy 1 (IC)")
    logger.info("=" * 60)
    
    result = run_scan()
    
    print("\n" + "=" * 60)
    print("PHASE 2 SCAN COMPLETE")
    print("=" * 60)
    print(f"Run ID:              {result['run_id']}")
    print(f"Pairs scanned:       {result['scanned_pairs']}")
    print(f"Pairs skipped (gate):{result['skipped_gate']}")
    print(f"Candidates found:    {result['candidates_total']}")
    print(f"Passed BED filter:   {result['passed_bed']}")
    print(f"Signals upserted:    {result['signals_upserted']}")
    print("=" * 60)
    
    if result['signals_upserted'] > 0:
        print("\n✓ New signals available in SIGNAL:ACTIVE:*")
        print("  View in UI at http://localhost:5000 (signals tab)")
    else:
        print("\n⚠ No signals passed filters")
    print()


if __name__ == "__main__":
    main()
