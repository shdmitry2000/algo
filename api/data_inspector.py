"""
Lightweight Flask API to serve Redis cache data to the frontend dashboard.
Endpoints:
  GET /api/tickers              — list all tickers in cache
  GET /api/chain/<ticker>       — all ticks for ticker
  GET /api/chain/<ticker>/<exp> — ticks for a specific expiration
  
  Phase 2 Signal endpoints:
  GET /api/signals/active       — list all active signals
  GET /api/signals/active/<symbol>/<expiration> — one active signal
  GET /api/signals/history      — query history (with filters)
  POST /api/signal-scan         — trigger Phase 2 scan
  POST /api/signals/phase3-outcome — record Phase 3 open success/failure
"""
import os
import sys
from flask import Flask, jsonify, request
from flask_cors import CORS
from dotenv import dotenv_values

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from datagathering.providers.file_folder_provider import (
    filename_updated_at_iso,
    load_ticks_from_csv,
    resolve_chain_files_dir,
    resolve_inventory_file,
    scan_inventory,
)
from storage.cache_manager import get_chain, push_chain
from storage.signal_cache import (
    list_active_signals,
    get_active_signal,
    get_history,
    get_latest_run,
    get_run_metadata,
    record_phase3_open_success,
    record_phase3_open_failure,
    get_gate
)

app = Flask(__name__)
# Include API routes on errors so browsers still see Access-Control-Allow-Origin
# (Flask skips after_request when an unhandled exception is turned into a 500 page.)
CORS(app, resources={r"/api/*": {"origins": "*"}})


def _project_root() -> str:
    return os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))


def _python_for_subprocess() -> str:
    root = _project_root()
    conda_py = os.path.join(root, ".conda", "bin", "python")
    if os.path.isfile(conda_py):
        return conda_py
    return sys.executable


def _chain_files_dir_and_error():
    env = dotenv_values(os.path.join(_project_root(), ".env"))
    config_value = env.get("CHAIN_FILES_DIR", "")
    if not config_value:
        return None, "CHAIN_FILES_DIR is not configured"
    try:
        base_dir = resolve_chain_files_dir(config_value, _project_root())
    except Exception as e:
        return None, str(e)
    if not base_dir.exists() or not base_dir.is_dir():
        return None, f"CHAIN_FILES_DIR does not exist or is not a directory: {base_dir}"
    return base_dir, None


def _run_scan_symbol_bg(symbol: str) -> None:
    import logging
    import sys as _sys

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        stream=_sys.stdout,
    )
    logger = logging.getLogger(__name__)
    try:
        from filters.phase2strat1.scan import run_scan_for_symbol

        logger.info(f"[api] Background: Triggering Phase 2 scan for {symbol}...")
        result = run_scan_for_symbol(symbol)
        logger.info(
            f"[api] Background: Phase 2 scan complete for {symbol}: {result.get('signals_upserted', 0)} signals"
        )
    except Exception as e:
        logger.error(f"[api] Background: Phase 2 scan failed for {symbol}: {e}")


@app.route("/api/health")
def health():
    return jsonify({"status": "ok", "message": "Backend API is running"})


@app.route("/api/status")
def status():
    """Returns currently configured provider from .env — independent of cached data."""
    env = dotenv_values(os.path.join(_project_root(), ".env"))
    _, chain_files_error = _chain_files_dir_and_error()
    return jsonify({
        "configured_provider": env.get("DATA_PROVIDER", "yfinance"),
        "redis_host": env.get("REDIS_HOST", "127.0.0.1"),
        "redis_port": env.get("REDIS_PORT", "6379"),
        "chain_files_dir_configured": chain_files_error is None,
        "chain_files_error": chain_files_error,
    })


@app.route("/api/run-pipeline", methods=["POST"])
def run_pipeline():
    """Triggers the data gathering pipeline in the background."""
    import subprocess

    root = _project_root()
    py = _python_for_subprocess()
    try:
        subprocess.Popen([py, "datagathering/pipeline.py"], cwd=root)
    except OSError as e:
        return jsonify({"status": "error", "message": str(e)}), 500
    env = dotenv_values(os.path.join(root, ".env"))
    return jsonify({"status": "started", "provider": env.get("DATA_PROVIDER", "yfinance")})


@app.route("/api/settings", methods=["GET"])
def get_settings():
    env = dotenv_values(os.path.join(_project_root(), ".env"))
    return jsonify({
        "DATA_PROVIDER": env.get("DATA_PROVIDER", "yfinance"),
        "TRADIER_ACCESS_TOKEN": "***" if env.get("TRADIER_ACCESS_TOKEN") else "",
        "THETA_USERNAME": env.get("THETA_USERNAME", ""),
        "CHAIN_FILES_DIR": env.get("CHAIN_FILES_DIR", ""),
        "REDIS_HOST": env.get("REDIS_HOST", "127.0.0.1"),
        "REDIS_PORT": env.get("REDIS_PORT", "6379"),
    })


@app.route("/api/settings", methods=["POST"])
def save_settings():
    """Update one or more keys in the .env file."""
    from flask import request
    data = request.get_json() or {}
    env_path = os.path.join(os.path.dirname(__file__), "..", ".env")

    # Read existing lines
    with open(env_path) as f:
        lines = f.readlines()

    updated_keys = set()
    new_lines = []
    for line in lines:
        key = line.split("=")[0].strip()
        if key in data:
            new_lines.append(f"{key}={data[key]}\n")
            updated_keys.add(key)
        else:
            new_lines.append(line)

    # Append any new keys not already in file
    for key, val in data.items():
        if key not in updated_keys:
            new_lines.append(f"{key}={val}\n")

    with open(env_path, "w") as f:
        f.writelines(new_lines)

    return jsonify({"status": "saved", "updated": list(data.keys())})



@app.route("/api/tickers")
def list_tickers():
    """Return configured tickers from settings.yaml."""
    import yaml
    settings_path = os.path.join(os.path.dirname(__file__), "..", "config", "settings.yaml")
    with open(settings_path) as f:
        config = yaml.safe_load(f)
    tickers = config.get("tickers", [])
    return jsonify({"tickers": tickers})


@app.route("/api/chain/<ticker>")
def chain(ticker):
    ticks = get_chain(ticker.upper())
    return jsonify({"ticker": ticker.upper(), "count": len(ticks),
                    "ticks": [t.to_dict() for t in ticks]})


@app.route("/api/chain/<ticker>/<expiration>")
def chain_exp(ticker, expiration):
    ticks = get_chain(ticker.upper(), expiration)
    return jsonify({"ticker": ticker.upper(), "expiration": expiration,
                    "count": len(ticks), "ticks": [t.to_dict() for t in ticks]})


@app.route("/api/chain-files/inventory")
def chain_files_inventory():
    base_dir, err = _chain_files_dir_and_error()
    if err:
        return jsonify({"tickers": [], "by_ticker": {}, "message": err})
    by_ticker = scan_inventory(base_dir)
    return jsonify({
        "tickers": sorted(by_ticker.keys()),
        "by_ticker": by_ticker,
        "base_dir": str(base_dir),
    })


@app.route("/api/chain-files/import", methods=["POST"])
def chain_files_import():
    data = request.get_json() or {}
    ticker = str(data.get("ticker", "")).strip().upper()
    date_str = str(data.get("date", "")).strip()
    time_str = str(data.get("time", "")).strip()

    if not all([ticker, date_str, time_str]):
        return jsonify({"status": "error", "message": "ticker, date, and time are required"}), 400

    base_dir, err = _chain_files_dir_and_error()
    if err:
        return jsonify({"status": "error", "message": err}), 400

    try:
        csv_path = resolve_inventory_file(base_dir, ticker, date_str, time_str)
        ticks = load_ticks_from_csv(csv_path, provider_name="file_folder")
        updated_at = filename_updated_at_iso(date_str, time_str)
        count = push_chain(ticks, updated_at=updated_at)
    except FileNotFoundError as e:
        return jsonify({"status": "error", "message": str(e)}), 404
    except ValueError as e:
        return jsonify({"status": "error", "message": str(e)}), 400
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

    try:
        import multiprocessing

        p = multiprocessing.Process(target=_run_scan_symbol_bg, args=(ticker,))
        p.start()
    except Exception:
        pass

    return jsonify({
        "status": "ok",
        "ticker": ticker,
        "ticks": count,
        "updated_at": updated_at,
        "file": str(csv_path),
    })


# ===== PHASE 2 SIGNAL ENDPOINTS =====

@app.route("/api/signals/active")
def get_active_signals_list():
    """List all active signals (one per symbol+expiration)."""
    signals = list_active_signals()
    
    # Enrich with gate status
    result = []
    for sig in signals:
        gate = get_gate(sig.symbol, sig.expiration)
        result.append({
            **sig.to_dict(),
            "gate_status": gate.status if gate else "idle",
            "gate_locked_signal_id": gate.locked_signal_id if gate else None
        })
    
    return jsonify({
        "count": len(result),
        "signals": result
    })


@app.route("/api/signals/active/<symbol>/<expiration>")
def get_single_active_signal(symbol, expiration):
    """Get single active signal + gate."""
    signal = get_active_signal(symbol, expiration)
    gate = get_gate(symbol, expiration)
    
    if not signal:
        return jsonify({"signal": None, "gate": gate.to_dict() if gate else None}), 404
    
    return jsonify({
        "signal": signal.to_dict(),
        "gate": gate.to_dict() if gate else None
    })


@app.route("/api/signals/history")
def get_signals_history():
    """Query history with optional filters."""
    limit = int(request.args.get("limit", 100))
    offset = int(request.args.get("offset", 0))
    symbol = request.args.get("symbol")
    expiration = request.args.get("expiration")
    signal_id = request.args.get("signal_id")
    event_type = request.args.get("event_type")
    
    events = get_history(
        limit=limit,
        offset=offset,
        symbol=symbol,
        expiration=expiration,
        signal_id=signal_id,
        event_type=event_type
    )
    
    return jsonify({
        "count": len(events),
        "events": [e.to_dict() for e in events]
    })


@app.route("/api/signal-scan", methods=["POST"])
def trigger_signal_scan():
    """Trigger Phase 2 scan."""
    import subprocess
    script_path = os.path.join(os.path.dirname(__file__), "..", "cli", "run_phase2_scan.py")
    conda_py = os.path.join(os.path.dirname(__file__), "..", ".conda", "bin", "python")
    
    # Run async
    subprocess.Popen([conda_py, script_path], cwd=os.path.join(os.path.dirname(__file__), ".."))
    
    return jsonify({"status": "started", "message": "Phase 2 scan triggered"})


@app.route("/api/signals/phase3-outcome", methods=["POST"])
def record_phase3_outcome():
    """Record Phase 3 open success or failure."""
    data = request.get_json() or {}
    signal_id = data.get("signal_id")
    symbol = data.get("symbol")
    expiration = data.get("expiration")
    status = data.get("status")  # "open_ok" or "open_fail"
    detail = data.get("detail", {})
    
    if not all([signal_id, symbol, expiration, status]):
        return jsonify({"error": "Missing required fields"}), 400
    
    if status == "open_ok":
        record_phase3_open_success(signal_id, symbol, expiration, detail)
    elif status == "open_fail":
        reason = data.get("reason", "unknown")
        record_phase3_open_failure(signal_id, symbol, expiration, reason, detail)
    else:
        return jsonify({"error": f"Invalid status: {status}"}), 400
    
    return jsonify({"status": "recorded"})


@app.route("/api/signal-runs")
def list_signal_runs():
    """List recent run metadata."""
    # Optional batch run support
    latest = get_latest_run()
    if not latest:
        return jsonify({"runs": []})
    
    latest_meta = get_run_metadata(latest)
    return jsonify({"runs": [latest_meta] if latest_meta else []})


@app.route("/api/signal-runs/<run_id>")
def get_signal_run(run_id):
    """Get run metadata by ID."""
    meta = get_run_metadata(run_id)
    if not meta:
        return jsonify({"error": "Run not found"}), 404
    return jsonify(meta)


# ===== PHASE 3 OPEN TRADE ENDPOINTS =====

@app.route("/api/open-trade", methods=["POST"])
def trigger_open_trade():
    """
    Trigger Phase 3 open trade from the UI.
    Runs asynchronously in a background process.

    POST body:
    {
        "symbol": "AAPL",
        "expiration": "2026-04-30",
        "subset": "all",        // "all" | "ic" | "bf"
        "executor": "mock",     // "mock" | "schwab"
        "provider": "yfinance"  // optional
    }
    """
    import subprocess

    data = request.get_json() or {}
    symbol = data.get("symbol")
    expiration = data.get("expiration")

    if not symbol or not expiration:
        return jsonify({"error": "symbol and expiration are required"}), 400

    subset = data.get("subset", "all")
    executor = data.get("executor", "mock")
    provider = data.get("provider", "yfinance")

    root = _project_root()
    py = _python_for_subprocess()

    cmd = [
        py, "-m", "open_trade.cli",
        "--symbol", symbol.upper(),
        "--expiration", expiration,
        "--subset", subset,
        "--executor", executor,
        "--provider", provider,
    ]

    try:
        subprocess.Popen(cmd, cwd=root)
    except OSError as e:
        return jsonify({"status": "error", "message": str(e)}), 500

    return jsonify({
        "status": "started",
        "symbol": symbol.upper(),
        "expiration": expiration,
        "subset": subset,
        "executor": executor,
        "provider": provider,
    })


@app.route("/api/trade-sessions/active")
def list_trade_sessions():
    """List all active trade sessions."""
    from storage.signal_cache import list_active_trade_sessions
    sessions = list_active_trade_sessions()
    return jsonify({"count": len(sessions), "sessions": sessions})


@app.route("/api/trade-sessions/<session_id>")
def get_trade_session_detail(session_id):
    """Get a specific trade session by ID."""
    from storage.signal_cache import get_trade_session
    session = get_trade_session(session_id)
    if not session:
        return jsonify({"error": "Session not found"}), 404
    return jsonify(session)


@app.route("/api/trade-sessions/history")
def get_trade_session_history():
    """Get trade session history."""
    from storage.signal_cache import get_trade_history
    limit = int(request.args.get("limit", 50))
    offset = int(request.args.get("offset", 0))
    history = get_trade_history(limit=limit, offset=offset)
    return jsonify({"count": len(history), "history": history})


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5001, debug=True)

