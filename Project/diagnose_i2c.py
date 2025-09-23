#!/usr/bin/env python3
"""
I2C Diagnostic Tool for RRR Flow Sensor and Relay HAT Conflicts
================================================================

This tool helps diagnose and resolve I2C bus conflicts between:
- Flow sensor (SLF3S-0600F) at address 0x08
- Relay HATs (SM16relind) at address 0x27

Usage:
    python3 diagnose_i2c.py                    # Full diagnostic
    python3 diagnose_i2c.py --bus 13           # Test specific bus
    python3 diagnose_i2c.py --recommend        # Get bus recommendation only
"""

import os
import sys
import argparse
from smbus2 import SMBus, i2c_msg
import time

def scan_all_buses():
    """Scan all available I2C buses and report devices."""
    print("=" * 60)
    print("I2C BUS SCAN")
    print("=" * 60)
    
    buses_found = []
    
    for bus_id in range(0, 21):
        bus_path = f"/dev/i2c-{bus_id}"
        if not os.path.exists(bus_path):
            continue
            
        print(f"\nBus {bus_id}: ", end="")
        
        try:
            with SMBus(bus_id) as bus:
                devices = []
                for addr in range(0x03, 0x78):  # Standard I2C address range
                    try:
                        bus.read_byte(addr)
                        devices.append(f"0x{addr:02X}")
                    except:
                        pass
                
                if devices:
                    print(f"Devices found: {', '.join(devices)}")
                    buses_found.append({
                        'id': bus_id, 
                        'devices': devices,
                        'has_flow_sensor': '0x08' in devices,
                        'has_relay_hat': '0x27' in devices
                    })
                else:
                    print("No devices found")
                    
        except Exception as e:
            print(f"Error: {e}")
    
    return buses_found

def test_flow_sensor_on_bus(bus_id):
    """Test flow sensor communication on specific bus."""
    print(f"\nTesting flow sensor on bus {bus_id}:")
    print("-" * 40)
    
    try:
        with SMBus(bus_id) as bus:
            # Test 1: Basic connectivity
            print("1. Connectivity test...", end=" ")
            try:
                bus.read_byte(0x08)
                print("✓ Device responds")
            except:
                print("✗ No response")
                return False
            
            # Test 2: Start command
            print("2. Start command (0x3608)...", end=" ")
            try:
                write = i2c_msg.write(0x08, [0x36, 0x08])
                bus.i2c_rdwr(write)
                time.sleep(0.01)  # Sensor init time
                print("✓ Command accepted")
            except Exception as e:
                print(f"✗ Failed: {e}")
                return False
            
            # Test 3: Data read
            print("3. Data read (9 bytes)...", end=" ")
            try:
                read = i2c_msg.read(0x08, 9)
                bus.i2c_rdwr(read)
                data = list(read)
                print(f"✓ Got data: {' '.join(f'{b:02X}' for b in data)}")
            except Exception as e:
                print(f"✗ Failed: {e}")
                return False
            
            # Test 4: Stop command
            print("4. Stop command (0x3FF9)...", end=" ")
            try:
                write = i2c_msg.write(0x08, [0x3F, 0xF9])
                bus.i2c_rdwr(write)
                print("✓ Command sent")
            except Exception as e:
                print(f"✗ Failed: {e}")
                return False
            
            print("✅ Flow sensor working correctly on this bus!")
            return True
            
    except Exception as e:
        print(f"Bus access error: {e}")
        return False

def recommend_best_bus(buses_found):
    """Recommend the best I2C bus for flow sensor."""
    print("\n" + "=" * 60)
    print("BUS RECOMMENDATION")
    print("=" * 60)
    
    # Find buses with flow sensor
    flow_sensor_buses = [b for b in buses_found if b['has_flow_sensor']]
    
    if not flow_sensor_buses:
        print("❌ No flow sensor detected on any bus!")
        print("Check wiring and power connections.")
        return None
    
    # Prioritize isolated buses (no relay HAT)
    isolated_buses = [b for b in flow_sensor_buses if not b['has_relay_hat']]
    shared_buses = [b for b in flow_sensor_buses if b['has_relay_hat']]
    
    if isolated_buses:
        best = isolated_buses[0]
        print(f"✅ RECOMMENDED: Bus {best['id']} (isolated, no conflicts)")
        print(f"   Devices: {', '.join(best['devices'])}")
        
        if len(isolated_buses) > 1:
            alternatives = [str(b['id']) for b in isolated_buses[1:]]
            print(f"   Alternatives: Bus {', '.join(alternatives)}")
        
        if shared_buses:
            shared_ids = [str(b['id']) for b in shared_buses]
            print(f"   ⚠️  Avoid: Bus {', '.join(shared_ids)} (shared with relay HAT)")
        
        return best['id']
    
    elif shared_buses:
        best = shared_buses[0]
        print(f"⚠️  BEST AVAILABLE: Bus {best['id']} (shared with relay HAT)")
        print(f"   Devices: {', '.join(best['devices'])}")
        print("   May experience occasional communication conflicts.")
        print("   Consider hardware changes for production use.")
        return best['id']
    
    return None

def main():
    parser = argparse.ArgumentParser(description="I2C diagnostic tool for RRR")
    parser.add_argument("--bus", type=int, help="Test specific bus only")
    parser.add_argument("--recommend", action="store_true", help="Get bus recommendation only")
    
    args = parser.parse_args()
    
    print("RRR I2C Diagnostic Tool")
    print("Flow Sensor (0x08) and Relay HAT (0x27) Conflict Analysis")
    
    if args.bus:
        # Test specific bus
        success = test_flow_sensor_on_bus(args.bus)
        sys.exit(0 if success else 1)
    
    # Full diagnostic
    buses_found = scan_all_buses()
    
    if not buses_found:
        print("\n❌ No I2C buses with devices found!")
        print("Check I2C is enabled: sudo raspi-config")
        sys.exit(1)
    
    # Test flow sensor on working buses
    working_buses = []
    for bus_info in buses_found:
        if bus_info['has_flow_sensor']:
            if test_flow_sensor_on_bus(bus_info['id']):
                working_buses.append(bus_info['id'])
    
    # Recommendation
    recommended = recommend_best_bus(buses_found)
    
    if not args.recommend and recommended:
        print(f"\n💡 UPDATE YOUR SETTINGS:")
        print(f"   Edit settings.json: \"i2c_bus\": {recommended}")
        print(f"   Or run: python3 test_solenoid_flow.py --bus {recommended}")

if __name__ == "__main__":
    main()
