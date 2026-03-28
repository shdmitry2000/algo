#!/bin/bash
# start_all.sh

echo "========================================"
echo "Starting AlgoTrade System..."
echo "========================================"

# Make sure scripts are executable
chmod +x stop_all.sh start_backend.sh start_frontend.sh

# 1. Stop everything first
./stop_all.sh
echo ""

# 2. Start backend
./start_backend.sh
if [ $? -ne 0 ]; then
    echo "Aborting due to backend failure."
    exit 1
fi
echo ""

# 3. Start frontend
./start_frontend.sh
if [ $? -ne 0 ]; then
    echo "Aborting due to frontend failure."
    exit 1
fi

echo ""
echo "🚀 All modules started and healthy!"
echo "   Backend:  http://localhost:5001"
echo "   Frontend: http://localhost:8000"
echo "========================================"
echo "To fetch option ticks into Redis, run:"
echo "  ./.conda/bin/python datagathering/pipeline.py"
