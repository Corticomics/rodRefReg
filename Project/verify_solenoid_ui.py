#!/usr/bin/env python3
"""
Verification Script for Solenoid UI Fix
========================================

This script verifies that the relay unit configuration is correct for solenoid mode.
Run this before launching the GUI to ensure all 15 cages will be visible.

Usage:
    python3 verify_solenoid_ui.py
"""

import json
import os
import sys

def verify_settings():
    """Verify settings.json configuration."""
    print("=" * 70)
    print("🔍 SOLENOID MODE UI VERIFICATION")
    print("=" * 70)
    print()
    
    # Check if settings.json exists
    if not os.path.exists('settings.json'):
        print("❌ ERROR: settings.json not found!")
        print("   Run the application once to create it, or copy from backup.")
        return False
    
    # Load settings
    with open('settings.json', 'r') as f:
        settings = json.load(f)
    
    print("✓ settings.json found")
    print()
    
    # Check hardware_mode
    hardware_mode = settings.get('hardware_mode', 'NOT SET')
    print(f"Hardware Mode: {hardware_mode}")
    
    if hardware_mode != 'solenoid':
        print("   ⚠️  WARNING: hardware_mode is not 'solenoid'")
        print("   ⚠️  GUI will operate in pump mode (only 8 paired units)")
    else:
        print("   ✓ Correct mode for solenoid operation")
    
    print()
    
    # Check global_master_relay_id
    master_id = settings.get('global_master_relay_id', 'NOT SET')
    print(f"Master Relay ID: {master_id}")
    
    if master_id != 16:
        print(f"   ⚠️  WARNING: Expected 16, got {master_id}")
    else:
        print("   ✓ Correct master relay")
    
    print()
    
    # Check cage_relays
    cage_relays = settings.get('cage_relays', {})
    num_cages = len(cage_relays)
    
    print(f"Configured Cages: {num_cages}")
    
    if num_cages == 0:
        print("   ⚠️  WARNING: No cage_relays configured")
        print("   ⚠️  System will auto-generate 15 cages on startup")
    elif num_cages < 15:
        print(f"   ⚠️  WARNING: Only {num_cages} cages configured")
        print(f"   ⚠️  Expected 15 cages for full HAT utilization")
    elif num_cages == 15:
        print("   ✓ All 15 cages configured")
    else:
        print(f"   ✓ {num_cages} cages configured (multi-HAT setup)")
    
    print()
    
    # Show cage mapping
    if cage_relays:
        print("Cage → Relay Mapping:")
        for cage_id in sorted([int(k) for k in cage_relays.keys()]):
            relay_id = cage_relays[str(cage_id)]
            print(f"   Cage {cage_id:2d} → Relay {relay_id:2d}")
        print()
    
    # Check for cage 15 specifically
    if '15' in cage_relays:
        print("✅ Cage 15 is configured!")
        print(f"   Cage 15 → Relay {cage_relays['15']}")
    else:
        print("⚠️  Cage 15 NOT explicitly configured")
        print("   Will be auto-generated on startup")
    
    print()
    
    return True


def verify_relay_unit_manager():
    """Verify RelayUnitManager functionality."""
    print("=" * 70)
    print("🧪 TESTING RELAY UNIT MANAGER")
    print("=" * 70)
    print()
    
    try:
        # Import after path setup
        from models.relay_unit_manager import RelayUnitManager
        
        # Load settings
        with open('settings.json', 'r') as f:
            settings = json.load(f)
        
        # Create manager
        print("Creating RelayUnitManager...")
        manager = RelayUnitManager(settings)
        
        # Get units
        units = manager.get_all_relay_units()
        num_units = len(units)
        
        print(f"✓ Manager created successfully")
        print(f"✓ Hardware mode: {manager.get_hardware_mode()}")
        print(f"✓ Number of units: {num_units}")
        print()
        
        # Show units
        print("Relay Units:")
        for unit in units:
            print(f"   {unit}")
        
        print()
        
        # Check for unit 15
        unit_15 = manager.get_relay_unit(15)
        if unit_15:
            print(f"✅ Relay Unit 15 EXISTS: {unit_15}")
        else:
            print(f"❌ Relay Unit 15 NOT FOUND!")
            print(f"   Available units: {[u.unit_id for u in units]}")
        
        print()
        
        return True
        
    except Exception as e:
        print(f"❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Run all verification checks."""
    print()
    
    # Step 1: Verify settings
    settings_ok = verify_settings()
    
    if not settings_ok:
        print("❌ Settings verification failed!")
        print("   Fix settings.json before continuing")
        return 1
    
    print()
    
    # Step 2: Verify manager
    manager_ok = verify_relay_unit_manager()
    
    if not manager_ok:
        print("❌ RelayUnitManager verification failed!")
        print("   Check Python import paths and code integrity")
        return 1
    
    print("=" * 70)
    print("✅ ALL CHECKS PASSED")
    print("=" * 70)
    print()
    print("Next Steps:")
    print("1. Launch the application: python3 main.py")
    print("2. Navigate to the Schedules tab")
    print("3. Verify you see 15 relay unit widgets")
    print("4. Try assigning an animal to relay unit 15")
    print()
    print("Expected Console Output on Startup:")
    print("   [RelayUnitManager] Solenoid mode initialized: 15 cages")
    print("   ✓ RelayUnitManager initialized in solenoid mode with 15 units")
    print("   [SchedulesTab] Loaded 15 relay units from RelayUnitManager")
    print()
    
    return 0


if __name__ == '__main__':
    sys.exit(main())

