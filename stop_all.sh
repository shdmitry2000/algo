#!/bin/bash
echo "Stopping all AlgoTrade modules..."

# Kill the API server
pkill -f "api/data_inspector.py"
echo "Killed data_inspector.py (if running)"

# Kill the frontend web server (if we use python -m http.server)
pkill -f "http.server 8000"
echo "Killed frontend server (if running)"

# Kill the pipeline
pkill -f "datagathering/pipeline.py"
echo "Killed datagathering/pipeline.py (if running)"

echo "All modules stopped."
