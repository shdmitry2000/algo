#!/bin/bash
# start_frontend.sh
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
pkill -f "http.server 8000"

# Serve using python's http module
CONDA_PY="../.conda/bin/python"
nohup $CONDA_PY -m http.server 8000 > ../frontend.log 2>&1 &

echo "Waiting for frontend healthcheck..."
max_attempts=10
attempt=1

while [ $attempt -le $max_attempts ]; do
    if curl -s -o /dev/null -w "%{http_code}" http://localhost:8000/ | grep -q "200"; then
        echo "✅ Frontend is healthy! (http://localhost:8000)"
        exit 0
    fi
    echo "Attempt $attempt: Frontend not ready, waiting..."
    sleep 1
    attempt=$((attempt + 1))
done

echo "❌ Frontend healthcheck failed after 10 seconds."
exit 1
