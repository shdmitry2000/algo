"""
Lightweight Flask API to serve Redis cache data to the frontend dashboard.
Endpoints:
  GET /api/tickers              — list all tickers in cache
  GET /api/chain/<ticker>       — all ticks for ticker
  GET /api/chain/<ticker>/<exp> — ticks for a specific expiration
"""
from flask import Flask, jsonify
from flask_cors import CORS
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from storage.cache_manager import get_all_tickers, get_chain

app = Flask(__name__)
CORS(app)  # Allow all origins — frontend runs on a different port


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
    conda_py = os.path.join(os.path.dirname(__file__), "..", ".conda", "bin", "python")
    subprocess.Popen([conda_py, "datagathering/pipeline.py"],
                     cwd=os.path.join(os.path.dirname(__file__), ".."))
    from dotenv import dotenv_values
    env = dotenv_values(os.path.join(os.path.dirname(__file__), "..", ".env"))
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
    tickers = get_all_tickers()
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


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5001, debug=True)
