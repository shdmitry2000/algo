"""
Phase 2 Strategy 1 — Signal Engine (Anomaly / Expiration Filter)

Scans CHAIN:* Redis data for structural profit opportunities (IC, Shifted IC, BF, Shifted BF)
and persists the single best signal per (symbol, expiration) to SIGNAL:ACTIVE:*.

To use: from filters.phase2strat1.scan import run_scan
"""

__all__ = []
