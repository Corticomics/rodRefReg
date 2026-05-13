#!/usr/bin/env python3
"""
Force Pulse Mode Configuration Script
=====================================

One-time script to force-enable pulse mode and verify settings persistence.

Usage:
    cd ~/rodent-refreshment-regulator/Project
    python3 force_pulse_mode.py
    cat settings.json  # Verify pulse keys present
"""

import sys
import json
from pathlib import Path

# Add Project to path
sys.path.insert(0, str(Path(__file__).parent))

from controllers.system_controller import SystemController
from models.database_handler import DatabaseHandler

def main():
    print("="*70)
    print("FORCE PULSE MODE CONFIGURATION")
    print("="*70)
    print()
    
    # Initialize system controller
    print("[1/4] Initializing system controller...")
    db = DatabaseHandler()
    sc = SystemController(db)
    print("✓ Controller initialized")
    print()
    
    # Show current settings
    print("[2/4] Current settings:")
    print(f"  hardware_mode: {sc.settings.get('hardware_mode')}")
    print(f"  use_pulse_delivery: {sc.settings.get('use_pulse_delivery')}")
    print(f"  pulse_width_ms: {sc.settings.get('pulse_width_ms')}")
    print(f"  flow_sampling_hz: {sc.settings.get('flow_sampling_hz')}")
    print()
    
    # Force pulse mode configuration
    print("[3/4] Running ensure_solenoid_defaults()...")
    sc.ensure_solenoid_defaults()
    print("✓ Configuration complete")
    print()
    
    # Verify changes
    print("[4/4] Verifying settings after update:")
    # Reload from disk to confirm persistence
    settings_path = Path(__file__).parent / 'settings.json'
    with open(settings_path, 'r') as f:
        persisted = json.load(f)
    
    print(f"  hardware_mode: {persisted.get('hardware_mode')}")
    print(f"  use_pulse_delivery: {persisted.get('use_pulse_delivery')}")
    print(f"  pulse_width_ms: {persisted.get('pulse_width_ms')}")
    print(f"  pulse_settling_ms: {persisted.get('pulse_settling_ms')}")
    print(f"  max_pulses_per_delivery: {persisted.get('max_pulses_per_delivery')}")
    print(f"  max_pulse_delivery_time_s: {persisted.get('max_pulse_delivery_time_s')}")
    print(f"  flow_sampling_hz: {persisted.get('flow_sampling_hz')}")
    print()
    
    # Validation
    missing_keys = []
    required_keys = [
        'use_pulse_delivery',
        'pulse_width_ms',
        'pulse_settling_ms',
        'max_pulses_per_delivery',
        'max_pulse_delivery_time_s'
    ]
    
    for key in required_keys:
        if key not in persisted:
            missing_keys.append(key)
    
    if missing_keys:
        print(f"❌ FAILED: Missing keys: {missing_keys}")
        print()
        print("TROUBLESHOOTING:")
        print("1. Check that SystemController.save_settings() is working")
        print("2. Check that _get_json_settings_keys() includes pulse mode keys")
        print("3. Check file permissions on settings.json")
        return 1
    else:
        print("✅ SUCCESS: All pulse mode keys present in settings.json")
        print()
        print("NEXT STEPS:")
        print("1. Restart the RRR application")
        print("2. Run a test schedule")
        print("3. You should see '[DEBUG] ✓ Strategy created' with pulse mode enabled")
        print("4. Logs should show 'Starting pulse delivery...' not 'No flow detected'")
        return 0

if __name__ == "__main__":
    sys.exit(main())

