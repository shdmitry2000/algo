#!/bin/bash
# start_backend.sh
echo "Starting Backend API..."

CONDA_PY="./.conda/bin/python"

# Kill old instances
pkill -f "api/data_inspector.py"

# Start the API
nohup $CONDA_PY api/data_inspector.py > api.log 2>&1 &

echo "Waiting for backend healthcheck..."
max_attempts=10
attempt=1

while [ $attempt -le $max_attempts ]; do
    if curl -s http://localhost:5001/api/health | grep -q 'ok'; then
        echo "✅ Backend is healthy! (http://localhost:5001)"
        exit 0
    fi
    echo "Attempt $attempt: Backend not ready, waiting..."
    sleep 1
    attempt=$((attempt + 1))
done

echo "❌ Backend healthcheck failed after 10 seconds."
exit 1
