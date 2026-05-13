#!/bin/bash
# EMERGENCY DIAGNOSTIC LAUNCHER
# This captures EVERYTHING including segfaults

cd ~/rodent-refreshment-regulator
source venv/bin/activate
cd Project

echo "==========================================================================="
echo "RRR EMERGENCY DIAGNOSTIC MODE"
echo "==========================================================================="
echo "This will show ALL output including low-level Qt/C++ errors"
echo "Log file: ~/rrr_emergency_diagnostic.log"
echo ""
echo "To test calibration:"
echo "1. Log in (or use guest mode)"
echo "2. Go to Settings → Valve Calibration tab"
echo "3. Click 'Calibrate' for any cage"
echo "4. Watch THIS TERMINAL for [WIZARD] and [SETTINGS] messages"
echo ""
echo "Press Ctrl+C to stop"
echo "==========================================================================="
echo ""

# Set ALL debugging flags
export PYTHONUNBUFFERED=1
export QT_LOGGING_RULES="*.debug=true"
export QT_DEBUG_PLUGINS=1
export PYTHONFAULTHANDLER=1

# Run with strace to catch segfaults (comment out if too verbose)
# strace -e trace=none -o ~/rrr_strace.log python3 -u main.py 2>&1 | tee ~/rrr_emergency_diagnostic.log

# Or run without strace (use this first)
python3 -u main.py 2>&1 | tee ~/rrr_emergency_diagnostic.log

EXIT_CODE=$?
echo ""
echo "==========================================================================="
echo "Application exited with code: $EXIT_CODE"
echo "Log saved to: ~/rrr_emergency_diagnostic.log"
echo "==========================================================================="

