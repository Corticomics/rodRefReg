#!/usr/bin/env python3
"""
Quick test for flow sensor on I2C bus 3
Tests basic connectivity and data reading
"""

import time
from smbus2 import SMBus, i2c_msg

def test_sensor_bus3():
    """Test SLF3S-0600F on I2C bus 3"""
    
    print("=== Testing Flow Sensor on I2C Bus 3 ===")
    
    # Check if bus 3 exists
    try:
        import os
        if not os.path.exists("/dev/i2c-3"):
            print("❌ /dev/i2c-3 does not exist")
            print("   Run: ls /dev/i2c-* to see available buses")
            print("   If bus 3 missing, check config.txt overlay and reboot")
            return False
        else:
            print("✅ /dev/i2c-3 exists")
    except Exception as e:
        print(f"❌ Error checking bus: {e}")
        return False
    
    # Test connectivity
    print("\nTesting I2C connectivity to address 0x08...")
    try:
        with SMBus(3) as bus:
            # Send start command as connectivity test
            write_msg = i2c_msg.write(0x08, [0x36, 0x08])
            bus.i2c_rdwr(write_msg)
            print("✅ Sensor responds to start command")
            
            # Wait for sensor initialization
            time.sleep(0.02)
            
            # Try to read data
            read_msg = i2c_msg.read(0x08, 9)
            bus.i2c_rdwr(read_msg)
            data = bytes(read_msg)
            
            if len(data) == 9:
                print(f"✅ Read 9 bytes: {data.hex()}")
                
                # Basic CRC check for first measurement (flow)
                fmsb, flsb, fcrc = data[0], data[1], data[2]
                calculated_crc = crc8(bytes([fmsb, flsb]))
                
                if calculated_crc == fcrc:
                    print("✅ Flow measurement CRC valid")
                    
                    # Convert to flow value
                    flow_raw = (fmsb << 8) | flsb
                    if flow_raw & 0x8000:
                        flow_raw -= 0x10000
                    flow_ul_min = flow_raw / 10.0
                    print(f"✅ Flow reading: {flow_ul_min:.1f} μL/min")
                    
                    return True
                else:
                    print(f"❌ Flow CRC mismatch: calculated {calculated_crc:02x}, received {fcrc:02x}")
                    return False
            else:
                print(f"❌ Expected 9 bytes, got {len(data)}")
                return False
                
    except Exception as e:
        print(f"❌ Communication failed: {e}")
        return False

def crc8(data: bytes) -> int:
    """Calculate CRC-8 for SLF3S data validation"""
    crc = 0xFF
    for byte in data:
        crc ^= byte
        for _ in range(8):
            crc = ((crc << 1) & 0xFF) ^ 0x31 if (crc & 0x80) else ((crc << 1) & 0xFF)
    return crc

if __name__ == "__main__":
    success = test_sensor_bus3()
    
    print("\n=== Summary ===")
    if success:
        print("🎉 Flow sensor working on I2C bus 3!")
        print("   • Sensor communication OK")
        print("   • Data reading successful") 
        print("   • CRC validation passed")
        print("\nNext: Test RRR delivery with fixed logger")
    else:
        print("⚠️  Flow sensor test failed")
        print("   • Check wiring to pins 32/33")
        print("   • Verify bus 3 overlay enabled")
        print("   • Run: sudo i2cdetect -y 3")
