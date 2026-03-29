"""
Redis Cache Manager for Phase 1 → Phase 2 handoff.

Redis key structure:
  HSET "CHAIN:{TICKER}:{EXPIRATION}" "{STRIKE}:{RIGHT}" "{JSON}"
  SET "CHAIN:META:{TICKER}:{EXPIRATION}" '{"updated_at":"2026-03-29T...", "tick_count":156}'

Example:
  HSET "CHAIN:AAPL:2024-01-19" "150.0:C"  '{"root":"AAPL", "bid":1.5, ...}'
  SET "CHAIN:META:AAPL:2024-01-19" '{"updated_at":"2026-03-29T02:00:00Z", "tick_count":156}'

Phase 2 will scan CHAIN:{TICKER}:* keys and read all strikes/rights to build
the spread matrix and apply the anomaly filter.
"""
import json
import logging
import os
from typing import List, Optional, Dict, Any
from datetime import datetime
import redis
from dotenv import load_dotenv
from datagathering.models import StandardOptionTick

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


def push_tick(client: redis.Redis, tick: StandardOptionTick) -> None:
    """Store a single tick into Redis."""
    key = f"CHAIN:{tick.root}:{tick.expiration}"
    field = f"{tick.strike}:{tick.right}"
    client.hset(key, field, tick.to_json())


def push_chain(ticks: List[StandardOptionTick]) -> int:
    """Push a full option chain (list of ticks) into Redis. Returns count of stored ticks."""
    if not ticks:
        return 0
    client = get_redis_client()
    pipe = client.pipeline()
    
    # Store option ticks
    for tick in ticks:
        key = f"CHAIN:{tick.root}:{tick.expiration}"
        field = f"{tick.strike}:{tick.right}"
        pipe.hset(key, field, tick.to_json())
    
    # Store metadata for freshness tracking
    from datetime import datetime
    meta_key = f"CHAIN:META:{ticks[0].root}:{ticks[0].expiration}"
    meta = {
        "updated_at": datetime.utcnow().isoformat(),
        "tick_count": len(ticks),
        "provider": ticks[0].provider
    }
    pipe.set(meta_key, json.dumps(meta))
    
    pipe.execute()
    logger.info(f"Pushed {len(ticks)} ticks to Redis for {ticks[0].root}")
    return len(ticks)


def get_chain(ticker: str, expiration: Optional[str] = None) -> List[StandardOptionTick]:
    """Retrieve option chain ticks from Redis for a given ticker (and optional expiration)."""
    client = get_redis_client()
    pattern = f"CHAIN:{ticker}:{expiration}" if expiration else f"CHAIN:{ticker}:*"
    keys = client.keys(pattern)
    ticks = []
    for key in keys:
        raw = client.hgetall(key)
        for field, value in raw.items():
            try:
                ticks.append(StandardOptionTick.from_json(value))
            except Exception as e:
                logger.warning(f"Could not deserialize tick from key={key} field={field}: {e}")
    return ticks


def get_chain_metadata(ticker: str, expiration: str) -> Optional[Dict[str, Any]]:
    """Get metadata for a specific chain (timestamp, tick count)."""
    client = get_redis_client()
    key = f"CHAIN:META:{ticker}:{expiration}"
    data = client.get(key)
    if data:
        return json.loads(data)
    return None


def get_all_tickers() -> List[str]:
    """Get list of all tickers currently in cache."""
    client = get_redis_client()
    keys = client.keys("CHAIN:*")
    tickers = set()
    for key in keys:
        parts = key.split(":")
        if len(parts) >= 2:
            tickers.add(parts[1])
    return sorted(tickers)
