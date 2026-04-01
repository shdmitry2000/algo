#!/bin/bash
# start_backend.sh
cd "$(dirname "$0")"

CONDA_PY="./.conda/bin/python"

wait_for_health() {
    local max_attempts=3
    local attempt=1
    echo "Waiting for backend healthcheck..."
    while [ $attempt -le $max_attempts ]; do
        if curl -s http://localhost:5001/api/health | grep -q 'ok'; then
            echo "✅ Backend is healthy! (http://localhost:5001)"
            return 0
        fi
        echo "Attempt $attempt: Backend not ready, waiting..."
        sleep 1
        attempt=$((attempt + 1))
    done
    return 1
}

echo "Starting Backend API..."

# Kill old instances
pkill -f "api/data_inspector.py" || true

# Start the API (Conda env, same as before)
echo "Trying primary: $CONDA_PY api/data_inspector.py"
nohup $CONDA_PY api/data_inspector.py > api.log 2>&1 &

if wait_for_health; then
    exit 0
fi

echo "Primary start failed healthcheck; trying fallback: python api/data_inspector.py"
pkill -f "api/data_inspector.py" || true
sleep 1

nohup python api/data_inspector.py > api.log 2>&1 &

if wait_for_health; then
    exit 0
fi

echo "❌ Backend healthcheck failed after fallback (20 seconds total)."
exit 1
