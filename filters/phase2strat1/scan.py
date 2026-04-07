"""
Phase 2 scan orchestrator — main entry point.
Multi-strategy scanner: IC, BF, Shifted IC, Shifted BF.
"""
import logging
import yaml
import os
from typing import Dict, Any, List, Optional
from datetime import datetime
import uuid

from storage.cache_manager import get_chain, get_chain_metadata
from storage.signal_cache import (
    set_active_signal,
    get_active_signal,
    lock_gate,
    is_gate_open,
    append_history,
    save_run_metadata,
    set_latest_run,
    get_scan_metadata,
    set_scan_metadata
)
from filters.phase2strat1.precheck import precheck_symbols
from filters.phase2strat1.chain_index import ChainIndex, compute_dte, group_by_expiration

# UPDATED: Use unified strategies from strategies/implementations
from strategies.implementations import (
    IronCondorStrategy,
    ButterflyStrategy,
    CondorStrategy,
    ShiftedCondorStrategy
)
from strategies.core import StrategyCandidate
from strategies.adapters import convert_chain_index_to_chain_data

# Still use legacy models for Signal/HistoryEvent (for now)
from filters.phase2strat1.models import HistoryEvent, Signal
from datagathering.models import StandardOptionTick

logger = logging.getLogger(__name__)


def build_strategy_snapshot(
    strategies: Dict[str, StrategyCandidate],
    all_ticks: List[StandardOptionTick]
) -> Dict[str, Any]:
    """
    Build minimal chain snapshot with ONLY strikes used across ALL strategies.
    Also include complete calculation details for all strategies.
    
    Args:
        strategies: Dict of strategy_type -> StrategyCandidate
        all_ticks: Full option chain ticks
    
    Returns:
        {
            "chain": [...only used strikes...],
            "strategies": {...all strategy details...}
        }
    """
    # Collect all strikes used across ALL strategies
    used_strikes = set()
    for strategy in strategies.values():
        used_strikes.update(strategy.strikes_used)
    
    # Filter ticks to only used strikes
    relevant_ticks = [t for t in all_ticks if t.strike in used_strikes]
    
    # Serialize chain data (only used strikes)
    chain_data = [
        {
            "strike": t.strike,
            "right": t.right,
            "bid": t.bid,
            "ask": t.ask,
            "mid": t.mid,
            "volume": t.volume,
            "open_interest": t.open_interest,
            "root": t.root
        }
        for t in relevant_ticks
    ]
    
    # Serialize all strategies with complete details
    strategy_details = {}
    for strategy_type, candidate in strategies.items():
        strategy_details[strategy_type] = candidate.to_dict()
    
    return {
        "chain": chain_data,
        "strategies": strategy_details
    }


def apply_bed_filter_to_candidates(
    candidates: List[StrategyCandidate],
    dte: int
) -> None:
    """
    Apply BED filter to candidates in-place.
    Sets bed_filter_pass attribute.
    """
    for candidate in candidates:
        if dte < candidate.break_even_days and candidate.remaining_profit > 0:
            candidate.bed_filter_pass = True
        else:
            candidate.bed_filter_pass = False


def compute_rank_score(candidate: StrategyCandidate) -> float:
    """
    Compute rank score for candidate.
    Higher score = better.
    
    Formula: BreakEvenDays / max(DTE, 1)
    """
    return candidate.break_even_days / max(candidate.dte, 1)


def select_best_strategy(
    all_strategies: Dict[str, List[StrategyCandidate]]
) -> Optional[Dict[str, StrategyCandidate]]:
    """
    Select best candidate from each strategy type, return dict of best candidates.
    
    Priority (per doc page 5):
        1. Dual-use candidates (valid for both IC and BF) - NOT IMPLEMENTED YET
        2. Butterfly / Shifted Butterfly (preferred over IC when score equal)
        3. Iron Condor
        4. Shifted IC
    
    Args:
        all_strategies: Dict of strategy_type -> List[StrategyCandidate]
    
    Returns:
        Dict of strategy_type -> best StrategyCandidate, or None if no passing candidates
    """
    best_per_strategy = {}
    
    # For each strategy type, find best passing candidate
    for strategy_type, candidates in all_strategies.items():
        passing = [c for c in candidates if c.bed_filter_pass]
        if not passing:
            continue
        
        # Compute rank scores
        for candidate in passing:
            candidate.rank_score = compute_rank_score(candidate)
        
        # Sort by rank_score descending
        passing.sort(key=lambda c: c.rank_score, reverse=True)
        best_per_strategy[strategy_type] = passing[0]
    
    if not best_per_strategy:
        return None
    
    return best_per_strategy


def _log_all_bed_failures(
    symbol: str,
    expiration: str,
    run_id: str,
    all_strategy_candidates: Dict[str, List[StrategyCandidate]],
    ticks: List[StandardOptionTick]
) -> None:
    """
    Log BED failures grouped by (symbol, expiration) with all failed strategies.
    """
    failed_strategies = {}
    
    for strategy_type, candidates in all_strategy_candidates.items():
        failed = [c for c in candidates if not c.bed_filter_pass]
        if failed:
            failed_strategies[strategy_type] = {
                "failed_count": len(failed),
                "best_bed": min(c.break_even_days for c in failed) if failed else None
            }
    
    if not failed_strategies:
        return
    
    event = HistoryEvent(
        ts=datetime.utcnow().isoformat(),
        event_type="bed_fail",
        symbol=symbol,
        expiration=expiration,
        run_id=run_id,
        payload={
            "failed_strategies": failed_strategies,
            "total_failed": sum(s["failed_count"] for s in failed_strategies.values())
        }
    )
    append_history(event)


def _log_signal_upserted(
    signal: Signal,
    all_strategy_candidates: Dict[str, List[StrategyCandidate]]
) -> None:
    """
    Log signal upsert with all strategy details (passed and failed).
    """
    strategies_calculated = list(all_strategy_candidates.keys())
    strategies_passed_bed = list(signal.strategies.keys())
    strategies_failed_bed = [s for s in strategies_calculated if s not in strategies_passed_bed]
    
    best_strategy_details = signal.get_best_strategy()
    
    event = HistoryEvent(
        ts=datetime.utcnow().isoformat(),
        event_type="signal_upserted",
        symbol=signal.symbol,
        expiration=signal.expiration,
        signal_id=signal.signal_id,
        run_id=signal.run_id,
        payload={
            "strategies_calculated": strategies_calculated,
            "strategies_passed_bed": strategies_passed_bed,
            "strategies_failed_bed": strategies_failed_bed,
            "best_strategy_type": signal.best_strategy_type,
            "best_bed": best_strategy_details.get("break_even_days") if best_strategy_details else None,
            "best_rank_score": signal.best_rank_score,
            "dte": signal.dte,
            "all_strategy_details": signal.strategies,
            "chain_snapshot": signal.chain_snapshot
        }
    )
    append_history(event)


def load_config() -> Dict[str, Any]:
    """Load settings.yaml."""
    config_path = os.path.join(os.path.dirname(__file__), "..", "..", "config", "settings.yaml")
    with open(config_path) as f:
        return yaml.safe_load(f)


def run_scan(run_id: Optional[str] = None) -> Dict[str, Any]:
    """
    Main Phase 2 scan orchestrator (Multi-strategy version).
    Scans ALL strategies: IC, BF, Shifted IC, Shifted BF.
    
    Returns summary dict including run_id, scanned_pairs, skipped_gate, candidates_total,
    passed_bed, signals_upserted, etc.
    """
    if not run_id:
        run_id = str(uuid.uuid4())
    
    logger.info(f"[scan] Starting Multi-Strategy Phase 2 scan: run_id={run_id}")
    
    config = load_config()
    tickers = config.get("tickers", [])
    params = config.get("parameters", {})
    
    fee_per_leg = params.get("fee_per_leg", 0.65)
    spread_cap_bound = params.get("spread_cap_bound", 0.01)
    
    started_at = datetime.utcnow().isoformat()
    
    # Precheck
    passing_symbols, precheck_report = precheck_symbols(tickers)
    
    scanned_pairs = 0
    skipped_gate = 0
    skipped_fresh = 0
    skipped_unchanged = 0
    signals_upserted = 0
    candidates_total = 0
    passed_bed = 0
    
    # Initialize strategy scanners
    # Instantiate unified strategy scanners
    ic_scanner = IronCondorStrategy()
    bf_scanner = ButterflyStrategy()
    condor_scanner = CondorStrategy()
    shifted_ic_scanner = ShiftedCondorStrategy()
    
    # Scan each symbol
    for symbol in passing_symbols:
        chain_ticks = get_chain(symbol)
        if not chain_ticks:
            logger.warning(f"[scan] {symbol}: no chain data")
            continue
        
        exp_groups = group_by_expiration(chain_ticks)
        
        for expiration, ticks in exp_groups.items():
            # Gate check
            if not is_gate_open(symbol, expiration):
                logger.debug(f"[scan] {symbol} {expiration}: GATE LOCKED, skipping")
                skipped_gate += 1
                
                event = HistoryEvent(
                    ts=datetime.utcnow().isoformat(),
                    event_type="gate_skip_scan",
                    symbol=symbol,
                    expiration=expiration,
                    run_id=run_id,
                    payload={}
                )
                append_history(event)
                continue
            
            # Data freshness check
            chain_meta = get_chain_metadata(symbol, expiration)
            scan_meta = get_scan_metadata(symbol, expiration)
            
            if chain_meta and scan_meta:
                chain_timestamp = chain_meta.get("updated_at")
                last_chain_timestamp = scan_meta.get("last_chain_timestamp")
                
                if chain_timestamp == last_chain_timestamp:
                    logger.debug(f"[scan] {symbol} {expiration}: DATA UNCHANGED, skipping")
                    skipped_fresh += 1
                    continue
            
            # NEW: Check if active signal exists with same chain_timestamp (prevent duplicates)
            existing_signal = get_active_signal(symbol, expiration)
            if existing_signal and chain_meta:
                existing_ts = existing_signal.chain_timestamp if hasattr(existing_signal, 'chain_timestamp') else None
                current_ts = chain_meta.get("updated_at")
                
                if existing_ts == current_ts:
                    logger.debug(
                        f"[scan] {symbol} {expiration}: SIGNAL EXISTS with same data timestamp, skipping"
                    )
                    skipped_unchanged += 1
                    continue
            
            # Log scan start
            event = HistoryEvent(
                ts=datetime.utcnow().isoformat(),
                event_type="scan_pair_start",
                symbol=symbol,
                expiration=expiration,
                run_id=run_id,
                payload={"tick_count": len(ticks)}
            )
            append_history(event)
            
            scanned_pairs += 1
            
            # Build chain index (legacy)
            chain_idx = ChainIndex(symbol, expiration, ticks)
            
            # UPDATED: Convert to unified ChainData for new strategies
            chain_data = convert_chain_index_to_chain_data(chain_idx)
            
            dte = compute_dte(expiration)
            
            # Scan ALL strategies (using unified implementations)
            logger.info(f"[scan] {symbol} {expiration}: Scanning all strategies...")
            
            all_strategy_candidates = {}
            
            # 1. Iron Condor (returns IC_BUY, IC_SELL, IC_BUY_IMBAL, IC_SELL_IMBAL)
            ic_candidates = ic_scanner.scan(
                chain_data, dte, fee_per_leg, spread_cap_bound
            )
            # Group by strategy_type
            for candidate in ic_candidates:
                if candidate.strategy_type not in all_strategy_candidates:
                    all_strategy_candidates[candidate.strategy_type] = []
                all_strategy_candidates[candidate.strategy_type].append(candidate)
            
            # 2. Butterfly (returns BF_BUY, BF_SELL) - 3 strikes
            bf_candidates = bf_scanner.scan(
                chain_data, dte, fee_per_leg, spread_cap_bound
            )
            for candidate in bf_candidates:
                if candidate.strategy_type not in all_strategy_candidates:
                    all_strategy_candidates[candidate.strategy_type] = []
                all_strategy_candidates[candidate.strategy_type].append(candidate)
            
            # 3. Condor (returns CONDOR_BUY, CONDOR_SELL) - 4 distinct strikes
            condor_candidates = condor_scanner.scan(
                chain_data, dte, fee_per_leg, spread_cap_bound
            )
            for candidate in condor_candidates:
                if candidate.strategy_type not in all_strategy_candidates:
                    all_strategy_candidates[candidate.strategy_type] = []
                all_strategy_candidates[candidate.strategy_type].append(candidate)
            
            # 4. Shifted Iron Condor (returns SHIFTED_IC_BUY, SHIFTED_IC_SELL)
            shifted_ic_candidates = shifted_ic_scanner.scan(
                chain_data, dte, fee_per_leg, spread_cap_bound
            )
            for candidate in shifted_ic_candidates:
                if candidate.strategy_type not in all_strategy_candidates:
                    all_strategy_candidates[candidate.strategy_type] = []
                all_strategy_candidates[candidate.strategy_type].append(candidate)
            
            # Apply BED filter to all candidates
            for strategy_type, candidates in all_strategy_candidates.items():
                apply_bed_filter_to_candidates(candidates, dte)
                
                passing_count = sum(1 for c in candidates if c.bed_filter_pass)
                candidates_total += len(candidates)
                passed_bed += passing_count
                logger.info(
                    f"[scan] {symbol} {expiration} {strategy_type}: "
                    f"{passing_count}/{len(candidates)} passed BED"
                )
            
            # Select best candidate per strategy
            best_per_strategy = select_best_strategy(all_strategy_candidates)
            
            if not best_per_strategy:
                # No passing strategies - log BED failures
                _log_all_bed_failures(
                    symbol, expiration, run_id,
                    all_strategy_candidates, ticks
                )
                continue
            
            # Find overall best strategy
            # Priority (UPDATED - using correct Condor naming):
            # 1. BF/CONDOR (BUY/SELL) - single-side strategies
            # 2. IC/SHIFTED_IC (BUY/SELL) - dual-side strategies
            # 3. Imbalanced variants (lower priority)
            priority_order = [
                "BF_BUY", "BF_SELL",
                "CONDOR_BUY", "CONDOR_SELL",
                "IC_BUY", "IC_SELL",
                "SHIFTED_IC_BUY", "SHIFTED_IC_SELL",
                "BF_BUY_IMBAL", "BF_SELL_IMBAL",
                "CONDOR_BUY_IMBAL", "CONDOR_SELL_IMBAL",
                "IC_BUY_IMBAL", "IC_SELL_IMBAL",
                "SHIFTED_IC_BUY_IMBAL", "SHIFTED_IC_SELL_IMBAL"
            ]
            best_strategy_type = None
            best_candidate = None
            
            for strategy_type in priority_order:
                if strategy_type in best_per_strategy:
                    best_strategy_type = strategy_type
                    best_candidate = best_per_strategy[strategy_type]
                    break
            
            if not best_candidate:
                # Fallback: pick first available
                best_strategy_type = list(best_per_strategy.keys())[0]
                best_candidate = best_per_strategy[best_strategy_type]
            
            # Build multi-strategy Signal
            chain_timestamp = chain_meta.get("updated_at") if chain_meta else datetime.utcnow().isoformat()
            
            # Serialize all strategies
            strategies_dict = {k: v.to_dict() for k, v in best_per_strategy.items()}
            
            # Build minimal snapshot (only used strikes)
            chain_snapshot = build_strategy_snapshot(best_per_strategy, ticks)
            
            signal = Signal(
                signal_id=str(uuid.uuid4()),
                symbol=symbol,
                expiration=expiration,
                dte=dte,
                strategies=strategies_dict,
                best_strategy_type=best_strategy_type,
                best_rank_score=best_candidate.rank_score,
                chain_timestamp=chain_timestamp,
                run_id=run_id,
                computed_at=datetime.utcnow().isoformat(),
                chain_snapshot=chain_snapshot
            )
            
            # Upsert signal and lock gate
            set_active_signal(signal)
            lock_gate(symbol, expiration, signal.signal_id)
            signals_upserted += 1
            
            # Log to history with all strategy details
            _log_signal_upserted(signal, all_strategy_candidates)
            
            # Update scan metadata
            if chain_meta:
                set_scan_metadata(symbol, expiration, chain_meta.get("updated_at"))
    
    finished_at = datetime.utcnow().isoformat()
    
    # Save run metadata
    run_meta = {
        "run_id": run_id,
        "started_at": started_at,
        "finished_at": finished_at,
        "config_snapshot": {
            "fee_per_leg": fee_per_leg,
            "spread_cap_bound": spread_cap_bound
        },
        "precheck_report": precheck_report,
        "scanned_pairs": scanned_pairs,
        "skipped_gate": skipped_gate,
        "skipped_fresh": skipped_fresh,
        "skipped_unchanged": skipped_unchanged,
        "candidates_total": candidates_total,
        "passed_bed": passed_bed,
        "signals_upserted": signals_upserted
    }
    save_run_metadata(run_id, run_meta)
    set_latest_run(run_id)
    
    logger.info(
        f"[scan] Complete: run_id={run_id} | scanned={scanned_pairs} | "
        f"skipped_gate={skipped_gate} | skipped_fresh={skipped_fresh} | "
        f"skipped_unchanged={skipped_unchanged} | upserted={signals_upserted}"
    )
    
    return run_meta


def run_scan_for_symbol(symbol: str, run_id: Optional[str] = None) -> Dict[str, Any]:
    """
    Run Phase 2 multi-strategy scan for a single symbol (all its expirations).
    Auto-triggered by Phase 1 pipeline after data load.
    
    Returns summary dict including run_id, scanned_pairs, skipped_gate, candidates_total,
    passed_bed, signals_upserted, etc.
    """
    if not run_id:
        run_id = str(uuid.uuid4())
    
    logger.info(f"[scan] Starting Multi-Strategy Phase 2 scan for {symbol}: run_id={run_id}")
    
    config = load_config()
    params = config.get("parameters", {})
    
    fee_per_leg = params.get("fee_per_leg", 0.65)
    spread_cap_bound = params.get("spread_cap_bound", 0.01)
    
    started_at = datetime.utcnow().isoformat()
    
    scanned_pairs = 0
    skipped_gate = 0
    skipped_fresh = 0
    skipped_unchanged = 0
    signals_upserted = 0
    candidates_total = 0
    passed_bed = 0
    
    # Initialize strategy scanners
    ic_scanner = IronCondorStrategy()
    bf_scanner = ButterflyStrategy()
    shifted_ic_scanner = ShiftedCondorStrategy()
    
    # Get all expirations for this symbol
    chain_ticks = get_chain(symbol)
    if not chain_ticks:
        logger.warning(f"[scan] {symbol}: no chain data")
        return {"run_id": run_id, "error": "no_data"}
    
    exp_groups = group_by_expiration(chain_ticks)
    
    for expiration, ticks in exp_groups.items():
        # Gate check
        if not is_gate_open(symbol, expiration):
            logger.debug(f"[scan] {symbol} {expiration}: GATE LOCKED, skipping")
            skipped_gate += 1
            
            event = HistoryEvent(
                ts=datetime.utcnow().isoformat(),
                event_type="gate_skip_scan",
                symbol=symbol,
                expiration=expiration,
                run_id=run_id,
                payload={}
            )
            append_history(event)
            continue
        
        # Data freshness check
        chain_meta = get_chain_metadata(symbol, expiration)
        scan_meta = get_scan_metadata(symbol, expiration)
        
        if chain_meta and scan_meta:
            chain_timestamp = chain_meta.get("updated_at")
            last_chain_timestamp = scan_meta.get("last_chain_timestamp")
            
            if chain_timestamp == last_chain_timestamp:
                logger.debug(f"[scan] {symbol} {expiration}: DATA UNCHANGED, skipping")
                skipped_fresh += 1
                continue
        
        # Check for existing signal with same chain_timestamp
        existing_signal = get_active_signal(symbol, expiration)
        if existing_signal and chain_meta:
            existing_ts = existing_signal.chain_timestamp if hasattr(existing_signal, 'chain_timestamp') else None
            current_ts = chain_meta.get("updated_at")
            
            if existing_ts == current_ts:
                logger.debug(f"[scan] {symbol} {expiration}: SIGNAL EXISTS with same data, skipping")
                skipped_unchanged += 1
                continue
        
        # Log scan start
        event = HistoryEvent(
            ts=datetime.utcnow().isoformat(),
            event_type="scan_pair_start",
            symbol=symbol,
            expiration=expiration,
            run_id=run_id,
            payload={"tick_count": len(ticks)}
        )
        append_history(event)
        
        scanned_pairs += 1
        
        # Build chain index
        chain_idx = ChainIndex(symbol, expiration, ticks)
        dte = compute_dte(expiration)
        
        # Scan ALL strategies
        logger.info(f"[scan] {symbol} {expiration}: Scanning all strategies...")
        
        all_strategy_candidates = {}
        
        # 1. Iron Condor (returns IC_BUY, IC_SELL, IC_BUY_IMBAL, IC_SELL_IMBAL)
        ic_candidates = ic_scanner.scan(chain_idx, dte, fee_per_leg, spread_cap_bound)
        for candidate in ic_candidates:
            if candidate.strategy_type not in all_strategy_candidates:
                all_strategy_candidates[candidate.strategy_type] = []
            all_strategy_candidates[candidate.strategy_type].append(candidate)
        
        # 2. Standard Butterfly (returns BF_BUY, BF_SELL)
        bf_candidates = bf_scanner.scan(chain_idx, dte, fee_per_leg, spread_cap_bound)
        for candidate in bf_candidates:
            if candidate.strategy_type not in all_strategy_candidates:
                all_strategy_candidates[candidate.strategy_type] = []
            all_strategy_candidates[candidate.strategy_type].append(candidate)
        
        # 3. Shifted Butterfly (returns SHIFTED_BF_BUY, SHIFTED_BF_SELL)
        shifted_bf_candidates = bf_scanner.scan_shifted(chain_idx, dte, fee_per_leg, spread_cap_bound)
        for candidate in shifted_bf_candidates:
            if candidate.strategy_type not in all_strategy_candidates:
                all_strategy_candidates[candidate.strategy_type] = []
            all_strategy_candidates[candidate.strategy_type].append(candidate)
        
        # 4. Shifted Iron Condor (returns SHIFTED_IC_BUY, SHIFTED_IC_SELL)
        shifted_ic_candidates = shifted_ic_scanner.scan(chain_idx, dte, fee_per_leg, spread_cap_bound)
        for candidate in shifted_ic_candidates:
            if candidate.strategy_type not in all_strategy_candidates:
                all_strategy_candidates[candidate.strategy_type] = []
            all_strategy_candidates[candidate.strategy_type].append(candidate)
        
        # Apply BED filter
        for strategy_type, candidates in all_strategy_candidates.items():
            apply_bed_filter_to_candidates(candidates, dte)
            passing_count = sum(1 for c in candidates if c.bed_filter_pass)
            candidates_total += len(candidates)
            passed_bed += passing_count
            logger.info(f"[scan] {symbol} {expiration} {strategy_type}: {passing_count}/{len(candidates)} passed BED")
        
        # Select best per strategy
        best_per_strategy = select_best_strategy(all_strategy_candidates)
        
        if not best_per_strategy:
            _log_all_bed_failures(symbol, expiration, run_id, all_strategy_candidates, ticks)
            continue
        
        # Find overall best strategy
        # Priority (per doc + plan):
        priority_order = [
            "BF_BUY", "BF_SELL",
            "SHIFTED_BF_BUY", "SHIFTED_BF_SELL",
            "IC_BUY", "IC_SELL",
            "SHIFTED_IC_BUY", "SHIFTED_IC_SELL",
            "BF_BUY_IMBAL", "BF_SELL_IMBAL",
            "SHIFTED_BF_BUY_IMBAL", "SHIFTED_BF_SELL_IMBAL",
            "IC_BUY_IMBAL", "IC_SELL_IMBAL",
            "SHIFTED_IC_BUY_IMBAL", "SHIFTED_IC_SELL_IMBAL"
        ]
        best_strategy_type = None
        best_candidate = None
        
        for strategy_type in priority_order:
            if strategy_type in best_per_strategy:
                best_strategy_type = strategy_type
                best_candidate = best_per_strategy[strategy_type]
                break
        
        if not best_candidate:
            best_strategy_type = list(best_per_strategy.keys())[0]
            best_candidate = best_per_strategy[best_strategy_type]
        
        # Build multi-strategy Signal
        chain_timestamp = chain_meta.get("updated_at") if chain_meta else datetime.utcnow().isoformat()
        strategies_dict = {k: v.to_dict() for k, v in best_per_strategy.items()}
        chain_snapshot = build_strategy_snapshot(best_per_strategy, ticks)
        
        signal = Signal(
            signal_id=str(uuid.uuid4()),
            symbol=symbol,
            expiration=expiration,
            dte=dte,
            strategies=strategies_dict,
            best_strategy_type=best_strategy_type,
            best_rank_score=best_candidate.rank_score,
            chain_timestamp=chain_timestamp,
            run_id=run_id,
            computed_at=datetime.utcnow().isoformat(),
            chain_snapshot=chain_snapshot
        )
        
        # Upsert signal and lock gate
        set_active_signal(signal)
        lock_gate(symbol, expiration, signal.signal_id)
        signals_upserted += 1
        
        # Log to history
        _log_signal_upserted(signal, all_strategy_candidates)
        
        # Update scan metadata
        if chain_meta:
            set_scan_metadata(symbol, expiration, chain_meta.get("updated_at"))
    
    finished_at = datetime.utcnow().isoformat()
    
    # Save run metadata
    run_meta = {
        "run_id": run_id,
        "symbol": symbol,
        "started_at": started_at,
        "finished_at": finished_at,
        "config_snapshot": {
            "fee_per_leg": fee_per_leg,
            "spread_cap_bound": spread_cap_bound
        },
        "scanned_pairs": scanned_pairs,
        "skipped_gate": skipped_gate,
        "skipped_fresh": skipped_fresh,
        "skipped_unchanged": skipped_unchanged,
        "candidates_total": candidates_total,
        "passed_bed": passed_bed,
        "signals_upserted": signals_upserted
    }
    save_run_metadata(run_id, run_meta)
    
    logger.info(
        f"[scan] Complete for {symbol}: run_id={run_id} | scanned={scanned_pairs} | "
        f"skipped_gate={skipped_gate} | skipped_fresh={skipped_fresh} | "
        f"skipped_unchanged={skipped_unchanged} | upserted={signals_upserted}"
    )
    
    return run_meta
