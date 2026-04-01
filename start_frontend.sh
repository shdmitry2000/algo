#!/bin/bash
# start_frontend.sh
cd "$(dirname "$0")"

CONDA_PY="../.conda/bin/python"

wait_for_health() {
    local max_attempts=3
    local attempt=1
    echo "Waiting for frontend healthcheck..."
    while [ $attempt -le $max_attempts ]; do
        if curl -s -o /dev/null -w "%{http_code}" http://localhost:8000/ | grep -q "200"; then
            echo "✅ Frontend is healthy! (http://localhost:8000)"
            return 0
        fi
        echo "Attempt $attempt: Frontend not ready, waiting..."
        sleep 1
        attempt=$((attempt + 1))
    done
    return 1
}

echo "Starting Frontend..."

cd frontend

# Install dependencies if a package.json exists (for future migration)
if [ -f "package.json" ]; then
    echo "package.json found, running npm install..."
    npm install
else
    echo "No package.json found. Skipping npm install."
fi

# Kill old instances
pkill -f "http.server 8000" || true

echo "Trying primary: $CONDA_PY -m http.server 8000"
nohup $CONDA_PY -m http.server 8000 > ../frontend.log 2>&1 &

if wait_for_health; then
    exit 0
fi

echo "Primary start failed healthcheck; trying fallback: python -m http.server 8000"
pkill -f "http.server 8000" || true
sleep 1

nohup python -m http.server 8000 > ../frontend.log 2>&1 &

if wait_for_health; then
    exit 0
fi

echo "❌ Frontend healthcheck failed after fallback (20 seconds total)."
exit 1
