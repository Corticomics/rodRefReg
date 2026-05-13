#!/bin/bash
# Emergency diagnostic launcher for RRR
# This will show ALL output including Qt errors

cd ~/rodent-refreshment-regulator
source venv/bin/activate
cd Project

# Run with ALL output redirected to both screen and log
echo "=== RRR Diagnostic Mode ==="
echo "All output will be shown and logged to ~/rrr_diagnostic.log"
echo "Press Ctrl+C to stop"
echo ""

# Set Python to unbuffered mode and capture everything
export PYTHONUNBUFFERED=1
export QT_LOGGING_RULES="*.debug=true"
export QT_DEBUG_PLUGINS=1

python3 -u main.py 2>&1 | tee ~/rrr_diagnostic.log

