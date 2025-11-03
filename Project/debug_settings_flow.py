#!/usr/bin/env python3
"""
Debug script to trace settings flow from JSON → SystemController → RelayWorker → Strategy

Run this before starting the app to verify settings are correctly propagated.
"""

import json
import sys

def main():
    print("=" * 80)
    print("SETTINGS FLOW DIAGNOSTIC")
    print("=" * 80)
    
    # Step 1: Read settings.json directly
    print("\n[STEP 1] Reading settings.json directly...")
    try:
        with open('settings.json', 'r') as f:
            json_settings = json.load(f)
        
        pulse_keys = ['use_pulse_delivery', 'pulse_width_ms', 'pulse_settling_ms', 
                      'max_pulses_per_delivery', 'max_pulse_delivery_time_s']
        
        print(f"  ✓ Loaded {len(json_settings)} keys from JSON")
        print(f"\n  Pulse mode keys in JSON:")
        for key in pulse_keys:
            value = json_settings.get(key)
            status = "✓" if value is not None else "✗"
            print(f"    {status} {key}: {value}")
    except Exception as e:
        print(f"  ✗ Failed to load JSON: {e}")
        sys.exit(1)
    
    # Step 2: Initialize SystemController
    print("\n[STEP 2] Initializing SystemController...")
    try:
        from models.database_handler import DatabaseHandler
        from controllers.system_controller import SystemController
        
        db_handler = DatabaseHandler()
        system_controller = SystemController(db_handler)
        
        print(f"  ✓ SystemController initialized")
        print(f"  ✓ system_controller.settings has {len(system_controller.settings)} keys")
        
        print(f"\n  Pulse mode keys in system_controller.settings:")
        for key in pulse_keys:
            value = system_controller.settings.get(key)
            status = "✓" if value is not None else "✗"
            print(f"    {status} {key}: {value}")
            
            # Compare with JSON
            json_value = json_settings.get(key)
            if value != json_value:
                print(f"      ⚠️  MISMATCH: JSON={json_value}, Memory={value}")
    except Exception as e:
        print(f"  ✗ Failed to initialize SystemController: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    
    # Step 3: Simulate strategy creation
    print("\n[STEP 3] Simulating strategy creation...")
    try:
        # This simulates what RelayWorker does
        system_settings = system_controller.settings
        
        print(f"  ✓ Got reference to system_controller.settings")
        print(f"  ✓ system_settings has {len(system_settings)} keys")
        
        print(f"\n  Pulse mode keys in system_settings (passed to strategy):")
        for key in pulse_keys:
            value = system_settings.get(key)
            status = "✓" if value is not None else "✗"
            print(f"    {status} {key}: {value}")
    except Exception as e:
        print(f"  ✗ Failed to access settings: {e}")
        sys.exit(1)
    
    # Step 4: Check for DB override
    print("\n[STEP 4] Checking database settings...")
    try:
        db_settings = system_controller._load_database_settings()
        print(f"  ✓ Database returned {len(db_settings)} keys")
        
        if db_settings:
            print(f"\n  Database settings (these override JSON):")
            for key, value in db_settings.items():
                print(f"    • {key}: {value}")
                if key in pulse_keys:
                    print(f"      ⚠️  WARNING: Pulse key being overridden by database!")
        else:
            print(f"  ✓ Database settings empty (not overriding JSON)")
    except Exception as e:
        print(f"  ⚠️  Could not load database settings: {e}")
    
    # Final verdict
    print("\n" + "=" * 80)
    print("DIAGNOSTIC SUMMARY")
    print("=" * 80)
    
    all_present = all(system_settings.get(key) is not None for key in pulse_keys)
    
    if all_present:
        print("✅ SUCCESS: All pulse mode keys are correctly propagated to strategy")
        print(f"\n   use_pulse_delivery = {system_settings.get('use_pulse_delivery')}")
        print(f"   pulse_width_ms = {system_settings.get('pulse_width_ms')}")
        print("\n   The system SHOULD be in pulse mode.")
        print("\n   If the app still shows pulse_mode=False, there's a timing issue.")
    else:
        print("❌ FAILURE: Pulse mode keys are NOT being propagated correctly")
        missing = [k for k in pulse_keys if system_settings.get(k) is None]
        print(f"\n   Missing keys: {missing}")
        print("\n   This explains why pulse mode is not activating.")
    
    print("=" * 80)

if __name__ == '__main__':
    main()

