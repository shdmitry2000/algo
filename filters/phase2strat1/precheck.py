"""
Symbol precheck — cheap gate before expensive scanning.
"""
import logging
from typing import List, Dict, Any
from datetime import datetime
import redis

from storage.cache_manager import get_redis_client
from filters.phase2strat1.models import HistoryEvent
from storage.signal_cache import append_history

logger = logging.getLogger(__name__)


def precheck_symbols(tickers: List[str]) -> tuple[List[str], Dict[str, str]]:
    """
    Check which tickers have chain data and can be scanned.
    
    Returns:
        (passing_symbols, report) where report maps symbol -> "pass" or reason for failure
    """
    client = get_redis_client()
    passing = []
    report = {}
    
    for ticker in tickers:
        # Check if at least one CHAIN key exists for this ticker
        pattern = f"CHAIN:{ticker}:*"
        # Use SCAN for production; keys() is acceptable for v1 with small ticker counts
        keys = client.keys(pattern)
        
        if not keys:
            reason = "no_chain_data"
            report[ticker] = reason
            logger.debug(f"[precheck] {ticker}: SKIP ({reason})")
            
            # Append history
            event = HistoryEvent(
                ts=datetime.utcnow().isoformat(),
                event_type="precheck_fail",
                symbol=ticker,
                payload={"reason": reason}
            )
            append_history(event)
            continue
        
        # Optional: check for staleness, min expirations, etc. (future)
        
        passing.append(ticker)
        report[ticker] = "pass"
        logger.debug(f"[precheck] {ticker}: PASS ({len(keys)} chain keys)")
        
        event = HistoryEvent(
            ts=datetime.utcnow().isoformat(),
            event_type="precheck_symbol",
            symbol=ticker,
            payload={"chain_keys": len(keys)}
        )
        append_history(event)
    
    logger.info(f"[precheck] {len(passing)}/{len(tickers)} symbols passed")
    return passing, report
