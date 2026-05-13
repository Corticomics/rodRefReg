#!/usr/bin/env python3
"""
Emergency Sensor Recovery Script for RRR
========================================

Purpose: Recover flow sensor from I²C hang state per SLF3S-0600F datasheet.

Usage:
    sudo python3 emergency_sensor_recovery.py

Per Sensirion SLF3S-0600F datasheet Section 2.2:
- Soft reset time: max 25ms (§2.2, Table 4)
- Warm-up time: typical 60ms (§2.2, Table 4)  
- I²C clock: 100-1000 kHz (§4.1, Table 7)

Reference: https://sensirion.com/media/documents/C4F8D965/66F56F53/LQ_DS_SLF3S-0600F_Datasheet.pdf
"""

import sys
import time
import json

try:
    import serial
except ImportError:
    print("ERROR: pyserial not installed")
    print("Install with: pip install pyserial")
    sys.exit(1)


def main():
    print("="*70)
    print("🚨 EMERGENCY SENSOR RECOVERY")
    print("="*70)
    print("\nThis script will attempt to recover the flow sensor from hang state.")
    print("Recovery procedure follows Sensirion SLF3S-0600F datasheet §2.2\n")
    
    port = '/dev/teensy_flow'
    baud = 115200
    
    # Step 1: Close any existing connections
    print("[1] Attempting to close any existing serial connections...")
    try:
        # Kill any processes holding the port
        import subprocess
        result = subprocess.run(['lsof', port], capture_output=True, text=True)
        if result.stdout:
            print(f"    Found processes using {port}:")
            print(f"    {result.stdout}")
            print("    ⚠️  Please stop the RRR application first!")
            return 1
    except Exception as e:
        pass  # lsof might not be available
    
    # Step 2: Open serial connection
    print(f"\n[2] Opening serial port {port}...")
    try:
        ser = serial.Serial(port, baud, timeout=2.0)
        print(f"    ✅ Port opened")
    except Exception as e:
        print(f"    ❌ Failed: {e}")
        print("\n💡 Troubleshooting:")
        print("    1. Check if Teensy is powered (LED on)")
        print("    2. Check USB cable connection")
        print("    3. Run: ls -l /dev/teensy_flow")
        print("    4. Try: sudo chmod 666 /dev/teensy_flow")
        return 1
    
    # Step 3: Wait for Teensy USB CDC re-enumeration
    print("\n[3] Waiting for Teensy USB CDC initialization...")
    time.sleep(4.0)  # Extended wait per Teensy best practices
    print("    ✅ Wait complete")
    
    # Step 4: Flush buffers
    print("\n[4] Flushing serial buffers...")
    try:
        ser.reset_input_buffer()
        ser.reset_output_buffer()
        print("    ✅ Buffers cleared")
    except Exception as e:
        print(f"    ⚠️  Warning: {e}")
    
    # Step 5: Send soft reset command to Teensy firmware
    print("\n[5] Sending sensor soft reset command...")
    print("    (Per SLF3S-0600F datasheet §2.2: reset address 0x00, command 0x06)")
    try:
        reset_cmd = json.dumps({"cmd": "reset"}) + "\n"
        ser.write(reset_cmd.encode('utf-8'))
        ser.flush()
        print(f"    📤 Sent: {reset_cmd.strip()}")
        time.sleep(0.5)
        
        # Read response
        if ser.in_waiting:
            response = ser.readline().decode('utf-8', errors='ignore').strip()
            print(f"    📥 Response: {response}")
            try:
                msg = json.loads(response)
                if msg.get('type') == 'status' and 'reset' in msg.get('message', '').lower():
                    print("    ✅ Sensor reset command acknowledged")
                else:
                    print(f"    ⚠️  Unexpected response type: {msg.get('type')}")
            except:
                pass
        else:
            print("    ⚠️  No response from Teensy")
    except Exception as e:
        print(f"    ❌ Reset failed: {e}")
    
    # Step 6: Wait for sensor reset completion (datasheet: min 25ms)
    print("\n[6] Waiting for sensor reset completion...")
    print("    (Per datasheet §2.2: soft reset time max 25ms)")
    time.sleep(0.1)  # 100ms for safety margin
    print("    ✅ Reset complete")
    
    # Step 7: Send start command
    print("\n[7] Starting sensor measurement...")
    print("    (Per datasheet: command 0x3608 for water mode)")
    try:
        start_cmd = json.dumps({"cmd": "start", "rate": 20}) + "\n"
        ser.write(start_cmd.encode('utf-8'))
        ser.flush()
        print(f"    📤 Sent: {start_cmd.strip()}")
        time.sleep(0.5)
        
        if ser.in_waiting:
            response = ser.readline().decode('utf-8', errors='ignore').strip()
            print(f"    📥 Response: {response}")
    except Exception as e:
        print(f"    ❌ Start failed: {e}")
    
    # Step 8: Verify sensor is streaming measurements
    print("\n[8] Verifying sensor stream...")
    print("    (Waiting for 5 measurements at 20 Hz = 250ms)")
    
    measurement_count = 0
    start_time = time.time()
    timeout = 5.0
    
    while time.time() - start_time < timeout:
        if ser.in_waiting:
            try:
                line = ser.readline().decode('utf-8', errors='ignore').strip()
                if line:
                    msg = json.loads(line)
                    if msg.get('type') == 'measurement':
                        measurement_count += 1
                        flow = msg.get('flow', 'N/A')
                        temp = msg.get('temp', 'N/A')
                        print(f"    ✅ Measurement {measurement_count}: {flow} mL/min, {temp}°C")
                        
                        if measurement_count >= 5:
                            break
            except:
                pass
        time.sleep(0.01)
    
    # Step 9: Stop sensor and close connection
    print("\n[9] Stopping sensor...")
    try:
        stop_cmd = json.dumps({"cmd": "stop"}) + "\n"
        ser.write(stop_cmd.encode('utf-8'))
        ser.flush()
        time.sleep(0.2)
        print("    ✅ Stop command sent")
    except:
        pass
    
    try:
        ser.close()
        print("    ✅ Port closed")
    except:
        pass
    
    # Final result
    print("\n" + "="*70)
    if measurement_count >= 5:
        print("✅ SUCCESS - Sensor recovery complete!")
        print(f"   Received {measurement_count} measurements")
        print("\n💡 Next steps:")
        print("   1. You can now restart the RRR application")
        print("   2. Try running a test schedule with 1 cage")
        print("   3. If issues persist, power cycle the Teensy (unplug/replug)")
        return 0
    else:
        print("❌ FAILURE - Sensor did not recover")
        print(f"   Only received {measurement_count} measurements")
        print("\n💡 Troubleshooting:")
        print("   1. Check I²C wiring: SDA, SCL, GND to Teensy")
        print("   2. Check pullup resistors (2kΩ on SDA/SCL)")
        print("   3. Check sensor power (3.3V)")
        print("   4. Try power cycling Teensy (unplug/replug USB)")
        print("   5. If all else fails, sensor may be physically damaged")
        return 1


if __name__ == '__main__':
    sys.exit(main())

