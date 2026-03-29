#!/bin/bash
# start_terminator.sh - Start Phase 3 Terminator in continuous mode

echo "Starting Phase 3 Terminator..."

CONDA_PY="./.conda/bin/python"

# Kill old instances
pkill -f "phase3_terminator.py"

# Start the terminator in continuous mode
nohup $CONDA_PY cli/phase3_terminator.py --mode continuous > terminator.log 2>&1 &

echo "Waiting for terminator to start..."
sleep 2

if pgrep -f "phase3_terminator.py" > /dev/null; then
    echo "✅ Phase 3 Terminator is running (continuous mode)"
    echo "   - Monitors SIGNAL:ACTIVE:* keys"
    echo "   - Waits 5s per signal, then unlocks with open_fail"
    echo "   - Logs: terminator.log"
    exit 0
else
    echo "❌ Terminator failed to start"
    exit 1
fi
