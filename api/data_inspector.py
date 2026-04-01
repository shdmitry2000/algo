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
from flask import Flask, jsonify, request
from flask_cors import CORS
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from storage.cache_manager import get_chain
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


@app.route("/api/health")
def health():
    return jsonify({"status": "ok", "message": "Backend API is running"})


@app.route("/api/status")
def status():
    """Returns currently configured provider from .env — independent of cached data."""
    from dotenv import dotenv_values
    env_path = os.path.join(os.path.dirname(__file__), "..", ".env")
    env = dotenv_values(env_path)
    return jsonify({
        "configured_provider": env.get("DATA_PROVIDER", "yfinance"),
        "redis_host": env.get("REDIS_HOST", "127.0.0.1"),
        "redis_port": env.get("REDIS_PORT", "6379"),
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
    from dotenv import dotenv_values
    env = dotenv_values(os.path.join(root, ".env"))
    return jsonify({"status": "started", "provider": env.get("DATA_PROVIDER", "yfinance")})


@app.route("/api/settings", methods=["GET"])
def get_settings():
    from dotenv import dotenv_values
    env_path = os.path.join(os.path.dirname(__file__), "..", ".env")
    env = dotenv_values(env_path)
    return jsonify({
        "DATA_PROVIDER": env.get("DATA_PROVIDER", "yfinance"),
        "TRADIER_ACCESS_TOKEN": "***" if env.get("TRADIER_ACCESS_TOKEN") else "",
        "THETA_USERNAME": env.get("THETA_USERNAME", ""),
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


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5001, debug=True)
