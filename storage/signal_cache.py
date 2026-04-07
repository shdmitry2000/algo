"""
Redis cache for Phase 2 signals, gates, history, and scan metadata.
Separate namespace from CHAIN:* (Phase 1).
"""
import json
import logging
import os
import redis
from typing import List, Optional, Dict, Any
from datetime import datetime
from dotenv import load_dotenv

# Import Phase 2 models
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from filters.phase2strat1.models import Signal, HistoryEvent, GateStatus

load_dotenv()
logger = logging.getLogger(__name__)

# Singleton Redis client to avoid connection exhaustion
_redis_client = None

def get_redis_client() -> redis.Redis:
    """Get Redis client (singleton to avoid connection pool exhaustion)."""
    global _redis_client
    if _redis_client is None:
        host = os.getenv("REDIS_HOST", "127.0.0.1")
        port = int(os.getenv("REDIS_PORT", "6379"))
        _redis_client = redis.Redis(
            host=host, 
            port=port, 
            decode_responses=True,
            max_connections=50,
            socket_keepalive=True,
            socket_connect_timeout=5
        )
    return _redis_client


# ===== ACTIVE SIGNALS =====

def set_active_signal(signal: Signal) -> None:
    """Write or update SIGNAL:ACTIVE:{symbol}:{expiration}."""
    client = get_redis_client()
    key = f"SIGNAL:ACTIVE:{signal.symbol}:{signal.expiration}"
    client.set(key, signal.to_json())
    logger.info(f"[signal_cache] Upserted active signal: {key} (signal_id={signal.signal_id})")


def get_active_signal(symbol: str, expiration: str) -> Optional[Signal]:
    """Retrieve active signal for (symbol, expiration)."""
    client = get_redis_client()
    key = f"SIGNAL:ACTIVE:{symbol}:{expiration}"
    data = client.get(key)
    if data:
        return Signal.from_json(data)
    return None


def delete_active_signal(symbol: str, expiration: str) -> None:
    """Clear active signal for (symbol, expiration)."""
    client = get_redis_client()
    key = f"SIGNAL:ACTIVE:{symbol}:{expiration}"
    client.delete(key)
    logger.info(f"[signal_cache] Deleted active signal: {key}")


def list_active_signals() -> List[Signal]:
    """List all active signals (SIGNAL:ACTIVE:*)."""
    client = get_redis_client()
    keys = client.keys("SIGNAL:ACTIVE:*")
    signals = []
    for key in keys:
        data = client.get(key)
        if data:
            try:
                signals.append(Signal.from_json(data))
            except Exception as e:
                logger.warning(f"[signal_cache] Failed to parse {key}: {e}")
    return signals


# ===== GATE =====

def get_gate(symbol: str, expiration: str) -> Optional[GateStatus]:
    """Get gate status for (symbol, expiration)."""
    client = get_redis_client()
    key = f"SIGNAL:GATE:{symbol}:{expiration}"
    data = client.get(key)
    if data:
        return GateStatus.from_json(data)
    return None


def set_gate(symbol: str, expiration: str, gate: GateStatus) -> None:
    """Set gate status."""
    client = get_redis_client()
    key = f"SIGNAL:GATE:{symbol}:{expiration}"
    client.set(key, gate.to_json())
    logger.debug(f"[signal_cache] Set gate: {key} -> {gate.status}")


def is_gate_open(symbol: str, expiration: str) -> bool:
    """Check if gate allows Phase 2 scan for (symbol, expiration)."""
    gate = get_gate(symbol, expiration)
    if not gate:
        return True  # No gate = allowed
    return gate.status in ["idle", "cleared_after_open", "cleared_after_fail"]


def lock_gate(symbol: str, expiration: str, signal_id: str) -> None:
    """Lock gate after signal is created (awaiting Phase 3)."""
    gate = GateStatus(
        status="signal_pending_open",
        locked_signal_id=signal_id,
        updated_at=datetime.utcnow().isoformat()
    )
    set_gate(symbol, expiration, gate)


def clear_gate_after_phase3(symbol: str, expiration: str, success: bool) -> None:
    """Clear gate after Phase 3 open success or failure."""
    gate = GateStatus(
        status="cleared_after_open" if success else "cleared_after_fail",
        locked_signal_id=None,
        updated_at=datetime.utcnow().isoformat()
    )
    set_gate(symbol, expiration, gate)


# ===== HISTORY =====

def append_history(event: HistoryEvent) -> None:
    """Append event to global SIGNAL:HISTORY list."""
    client = get_redis_client()
    client.lpush("SIGNAL:HISTORY", event.to_json())
    logger.debug(f"[signal_cache] History: {event.event_type} | {event.symbol} | {event.expiration}")


def get_history(
    limit: int = 100,
    offset: int = 0,
    symbol: Optional[str] = None,
    expiration: Optional[str] = None,
    signal_id: Optional[str] = None,
    event_type: Optional[str] = None
) -> List[HistoryEvent]:
    """
    Query history (newest first). Supports filtering.
    
    Note: When filters are applied, we retrieve more events from Redis to ensure
    we return up to `limit` matching events after filtering.
    """
    client = get_redis_client()
    
    # If filters are applied, retrieve significantly more events to ensure matches
    # signal_upserted events may be buried deep (e.g., position 300+) after many phase3_open_fail
    has_filters = any([symbol, expiration, signal_id, event_type])
    if has_filters:
        # Fetch up to 2000 events when filtering to ensure we find matches
        fetch_limit = min(2000, max(1000, (limit + offset) * 10))
    else:
        fetch_limit = limit + offset
    
    # LRANGE returns index 0 = newest
    raw = client.lrange("SIGNAL:HISTORY", 0, fetch_limit - 1)
    events = []
    skipped = 0
    
    for item in raw:
        try:
            evt = HistoryEvent.from_json(item)
            
            # Apply filters
            if symbol and evt.symbol != symbol:
                continue
            if expiration and evt.expiration != expiration:
                continue
            if signal_id and evt.signal_id != signal_id:
                continue
            if event_type and evt.event_type != event_type:
                continue
            
            # Apply offset after filtering
            if skipped < offset:
                skipped += 1
                continue
            
            events.append(evt)
            
            # Stop when we have enough results
            if len(events) >= limit:
                break
                
        except Exception as e:
            logger.warning(f"[signal_cache] Failed to parse history event: {e}")
    
    return events


# ===== BATCH RUN METADATA (optional) =====

def save_run_metadata(run_id: str, metadata: Dict[str, Any]) -> None:
    """Save batch run metadata SIGNAL:RUN:{run_id}."""
    client = get_redis_client()
    key = f"SIGNAL:RUN:{run_id}"
    client.set(key, json.dumps(metadata))
    logger.info(f"[signal_cache] Saved run metadata: {key}")


def get_run_metadata(run_id: str) -> Optional[Dict[str, Any]]:
    """Retrieve run metadata."""
    client = get_redis_client()
    key = f"SIGNAL:RUN:{run_id}"
    data = client.get(key)
    return json.loads(data) if data else None


def set_latest_run(run_id: str) -> None:
    """Point SIGNAL:LATEST_RUN to this run_id."""
    client = get_redis_client()
    client.set("SIGNAL:LATEST_RUN", run_id)


def get_latest_run() -> Optional[str]:
    """Get latest run_id."""
    client = get_redis_client()
    return client.get("SIGNAL:LATEST_RUN")


# ===== PHASE 3 HOOKS =====

def record_phase3_open_success(signal_id: str, symbol: str, expiration: str, detail: Optional[Dict] = None) -> None:
    """Called by Phase 3 when open succeeds."""
    clear_gate_after_phase3(symbol, expiration, success=True)
    delete_active_signal(symbol, expiration)  # Position exists; clear active
    
    event = HistoryEvent(
        ts=datetime.utcnow().isoformat(),
        event_type="phase3_open_ok",
        symbol=symbol,
        expiration=expiration,
        signal_id=signal_id,
        payload=detail or {}
    )
    append_history(event)
    logger.info(f"[signal_cache] Phase 3 open OK: {signal_id} ({symbol} {expiration})")


def record_phase3_open_failure(signal_id: str, symbol: str, expiration: str, reason: str, detail: Optional[Dict] = None) -> None:
    """Called by Phase 3 when open fails (can't buy)."""
    clear_gate_after_phase3(symbol, expiration, success=False)
    delete_active_signal(symbol, expiration)  # Clear so new signal can appear
    
    payload = {"reason": reason}
    if detail:
        payload.update(detail)
    
    event = HistoryEvent(
        ts=datetime.utcnow().isoformat(),
        event_type="phase3_open_fail",
        symbol=symbol,
        expiration=expiration,
        signal_id=signal_id,
        payload=payload
    )
    append_history(event)
    logger.warning(f"[signal_cache] Phase 3 open FAIL: {signal_id} ({symbol} {expiration}) — {reason}")


# ===== SCAN METADATA (for freshness tracking) =====

def get_scan_metadata(symbol: str, expiration: str) -> Optional[Dict[str, Any]]:
    """Get scan metadata for (symbol, expiration) - tracks last scan timestamp."""
    client = get_redis_client()
    key = f"SCAN:META:{symbol}:{expiration}"
    data = client.get(key)
    if data:
        return json.loads(data)
    return None


def set_scan_metadata(symbol: str, expiration: str, chain_timestamp: str) -> None:
    """Record that we scanned this (symbol, expiration) with given chain timestamp."""
    client = get_redis_client()
    key = f"SCAN:META:{symbol}:{expiration}"
    meta = {
        "last_scan_at": datetime.utcnow().isoformat(),
        "last_chain_timestamp": chain_timestamp
    }
    client.set(key, json.dumps(meta))
    logger.debug(f"[signal_cache] Updated scan metadata: {key}")


# ===== PHASE 3 TRADE SESSION PERSISTENCE =====

def save_trade_session(session_dict: Dict[str, Any]) -> None:
    """
    Save/update a trade session to Redis.
    Called after every state change for real-time monitoring.

    Keys:
      TRADE:SESSION:{session_id} — full session JSON
      TRADE:ACTIVE:{symbol}:{expiration} — session_id pointer
    """
    client = get_redis_client()
    session_id = session_dict["session_id"]
    symbol = session_dict["symbol"]
    expiration = session_dict["expiration"]

    # Save full session
    key = f"TRADE:SESSION:{session_id}"
    client.set(key, json.dumps(session_dict))

    # Update active trade pointer
    active_key = f"TRADE:ACTIVE:{symbol}:{expiration}"
    state = session_dict.get("state", "")
    if state in ("completed", "failed", "timeout", "reverted"):
        # Terminal state — remove from active
        client.delete(active_key)

        # Add to history
        client.rpush("TRADE:HISTORY", json.dumps({
            "session_id": session_id,
            "symbol": symbol,
            "expiration": expiration,
            "state": state,
            "completed_at": session_dict.get("completed_at"),
            "strategy_type": session_dict.get("current_strategy_type"),
        }))
    else:
        client.set(active_key, session_id)

    logger.debug(f"[signal_cache] Saved trade session: {session_id[:8]}... ({state})")


def get_trade_session(session_id: str) -> Optional[Dict[str, Any]]:
    """Get a trade session by ID."""
    client = get_redis_client()
    data = client.get(f"TRADE:SESSION:{session_id}")
    if data:
        return json.loads(data)
    return None


def get_active_trade_session(symbol: str, expiration: str) -> Optional[Dict[str, Any]]:
    """Get the active trade session for a symbol+expiration."""
    client = get_redis_client()
    session_id = client.get(f"TRADE:ACTIVE:{symbol}:{expiration}")
    if session_id:
        sid = session_id.decode() if isinstance(session_id, bytes) else session_id
        return get_trade_session(sid)
    return None


def list_active_trade_sessions() -> List[Dict[str, Any]]:
    """List all currently active trade sessions."""
    client = get_redis_client()
    sessions = []
    for key in client.scan_iter("TRADE:ACTIVE:*"):
        session_id = client.get(key)
        if session_id:
            sid = session_id.decode() if isinstance(session_id, bytes) else session_id
            session = get_trade_session(sid)
            if session:
                sessions.append(session)
    return sessions


def get_trade_history(limit: int = 50, offset: int = 0) -> List[Dict[str, Any]]:
    """Get trade session history (most recent first)."""
    client = get_redis_client()
    total = client.llen("TRADE:HISTORY")
    start = max(0, total - offset - limit)
    end = total - offset - 1
    items = client.lrange("TRADE:HISTORY", start, end)
    result = [json.loads(item) for item in reversed(items)]
    return result


def complete_trade_session(session_id: str, state: str, detail: Optional[Dict] = None) -> None:
    """Mark a trade session as complete (success, failure, or timeout)."""
    session = get_trade_session(session_id)
    if session is None:
        logger.warning(f"[signal_cache] Trade session {session_id} not found")
        return
    session["state"] = state
    session["completed_at"] = datetime.utcnow().isoformat()
    if detail:
        session["result_detail"] = detail
    save_trade_session(session)
