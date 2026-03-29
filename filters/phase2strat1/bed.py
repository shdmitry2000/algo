"""
BED filter and ranking.
"""
import logging
from typing import List
from filters.phase2strat1.models import Signal

logger = logging.getLogger(__name__)


def apply_bed_filter(candidates: List[Signal]) -> List[Signal]:
    """
    Apply Break-Even Days filter: DTE < BED (Section 13.2).
    Sets bed_filter_pass on each signal.
    
    Returns: signals that pass the filter.
    """
    passing = []
    for signal in candidates:
        # BED filter: DTE < BreakEvenDays
        if signal.dte < signal.break_even_days and signal.remaining_profit > 0:
            signal.bed_filter_pass = True
            passing.append(signal)
        else:
            signal.bed_filter_pass = False
            logger.debug(
                f"[bed_filter] REJECT {signal.symbol} {signal.expiration} {signal.structure_label}: "
                f"DTE={signal.dte} vs BED={signal.break_even_days:.2f}"
            )
    
    logger.info(f"[bed_filter] {len(passing)}/{len(candidates)} candidates passed BED filter")
    return passing


def compute_rank_score(signal: Signal) -> float:
    """
    Compute rank score for capital efficiency (Section 17).
    Higher score = better.
    
    v1: BreakEvenDays / max(DTE, 1)
    """
    return signal.break_even_days / max(signal.dte, 1)


def rank_signals(signals: List[Signal]) -> List[Signal]:
    """
    Compute rank_score for all signals and sort descending.
    """
    for signal in signals:
        signal.rank_score = compute_rank_score(signal)
    
    signals.sort(key=lambda s: s.rank_score, reverse=True)
    return signals


def select_best_signal(signals: List[Signal]) -> List[Signal]:
    """
    For each (symbol, expiration), keep only the highest rank_score.
    
    Returns: list of winning signals (one per pair).
    """
    if not signals:
        return []
    
    # Group by (symbol, expiration)
    groups = {}
    for sig in signals:
        key = (sig.symbol, sig.expiration)
        if key not in groups:
            groups[key] = []
        groups[key].append(sig)
    
    winners = []
    for key, group in groups.items():
        # Sort by rank_score descending
        group.sort(key=lambda s: s.rank_score, reverse=True)
        best = group[0]
        winners.append(best)
        logger.info(
            f"[ranking] Best for {key}: {best.structure_label} score={best.rank_score:.4f} "
            f"BED={best.break_even_days:.2f} DTE={best.dte}"
        )
    
    return winners
