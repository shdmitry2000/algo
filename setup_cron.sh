#!/bin/bash
# Setup cron job for daily Redis maintenance
# Runs backup + cleanup at 00:00 (midnight) every day

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CRON_CMD="0 0 * * * cd $SCRIPT_DIR && ./.conda/bin/python cli/daily_maintenance.py >> logs/maintenance.log 2>&1"

echo "Setting up daily Redis maintenance cron job..."
echo "  Schedule: Every day at 00:00 (midnight)"
echo "  Command: $CRON_CMD"
echo ""

# Check if cron job already exists
if crontab -l 2>/dev/null | grep -q "daily_maintenance.py"; then
    echo "⚠️  Cron job already exists:"
    crontab -l | grep "daily_maintenance.py"
    echo ""
    read -p "Replace existing cron job? (y/N): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        echo "Aborted."
        exit 0
    fi
    
    # Remove old cron job
    crontab -l 2>/dev/null | grep -v "daily_maintenance.py" | crontab -
fi

# Add new cron job
(crontab -l 2>/dev/null; echo "$CRON_CMD") | crontab -

echo "✅ Cron job added successfully"
echo ""
echo "To verify:"
echo "  crontab -l | grep daily_maintenance"
echo ""
echo "To remove:"
echo "  crontab -l | grep -v daily_maintenance.py | crontab -"
echo ""
echo "To test manually:"
echo "  ./.conda/bin/python cli/daily_maintenance.py"
