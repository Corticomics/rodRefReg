#!/usr/bin/env python3
"""
Enhanced Teensy Flow Sensor Diagnostic
======================================

Comprehensive test with detailed data decoding and analysis.
Tests both idle state (no flow) and active communication.
"""

import serial
import json
import time
import sys
from datetime import datetime

def test_enhanced_teensy(port='/dev/ttyACM0', duration=10):
    """Enhanced Teensy communication test with full data decoding."""
    
    print("🔬 Enhanced Teensy Flow Sensor Diagnostic")
    print("=" * 50)
    print(f"Port: {port}")
    print(f"Test duration: {duration} seconds")
    print(f"Expected: Temperature readings + zero flow (tubes not primed)")
    print()
    
    try:
        # Open connection with same parameters as RRR
        with serial.Serial(port, 115200, timeout=1.0) as ser:
            print("✓ Serial connection opened")
            
            # Wait for Teensy initialization (same as our production code)
            print("⏳ Waiting for Teensy initialization (2.5s)...")
            time.sleep(2.5)
            
            # Test 1: Ping test
            print("\n📡 Test 1: Communication Test")
            print("-" * 30)
            ser.write(b'{"cmd":"ping"}\n')
            ser.flush()
            
            response = ser.readline().decode('utf-8').strip()
            if response:
                try:
                    data = json.loads(response)
                    if data.get("type") == "pong":
                        print("✓ Ping successful - Teensy responding")
                    else:
                        print(f"⚠ Unexpected ping response: {data}")
                except json.JSONDecodeError:
                    print(f"⚠ Non-JSON ping response: {response}")
            else:
                print("✗ No ping response")
                return False
            
            # Test 2: Start sensor at 1 Hz for detailed observation
            print(f"\n🌊 Test 2: Flow Sensor Data Collection ({duration}s @ 1Hz)")
            print("-" * 50)
            ser.write(b'{"cmd":"start","rate":1}\n')
            ser.flush()
            
            start_time = time.time()
            message_count = 0
            error_count = 0
            measurement_count = 0
            status_count = 0
            
            temp_readings = []
            flow_readings = []
            
            print("⏳ Collecting data...")
            print("Format: [TIME] TYPE: details")
            print()
            
            while time.time() - start_time < duration:
                if ser.in_waiting:
                    try:
                        line = ser.readline().decode('utf-8').strip()
                        if line:
                            message_count += 1
                            timestamp = datetime.now().strftime("%H:%M:%S.%f")[:-3]
                            
                            try:
                                data = json.loads(line)
                                msg_type = data.get("type", "unknown")
                                
                                if msg_type == "measurement":
                                    measurement_count += 1
                                    flow = data.get("flow", 0)
                                    temp = data.get("temp", 0)
                                    teensy_time = data.get("time", 0)
                                    count = data.get("count", 0)
                                    
                                    flow_readings.append(flow)
                                    temp_readings.append(temp)
                                    
                                    print(f"[{timestamp}] MEASUREMENT: Flow={flow:.4f} mL/min, Temp={temp:.1f}°C, Count={count}, TeensyTime={teensy_time}")
                                
                                elif msg_type == "error":
                                    error_count += 1
                                    error_msg = data.get("error", "unknown")
                                    teensy_time = data.get("time", 0)
                                    print(f"[{timestamp}] ERROR: {error_msg} (TeensyTime={teensy_time})")
                                
                                elif msg_type == "status":
                                    status_count += 1
                                    message = data.get("message", "")
                                    running = data.get("running", False)
                                    rate = data.get("rate", 0)
                                    errors = data.get("errors", 0)
                                    print(f"[{timestamp}] STATUS: {message} (Running={running}, Rate={rate}Hz, Errors={errors})")
                                
                                else:
                                    print(f"[{timestamp}] UNKNOWN: {data}")
                                    
                            except json.JSONDecodeError:
                                print(f"[{timestamp}] RAW: {line}")
                                
                    except Exception as e:
                        print(f"[{timestamp}] EXCEPTION: {e}")
                
                time.sleep(0.01)  # Small delay to prevent CPU spinning
            
            # Test 3: Stop sensor
            print(f"\n🛑 Test 3: Stopping Sensor")
            print("-" * 30)
            ser.write(b'{"cmd":"stop"}\n')
            ser.flush()
            time.sleep(0.5)
            
            # Final status check
            ser.write(b'{"cmd":"ping"}\n')
            ser.flush()
            response = ser.readline().decode('utf-8').strip()
            if response:
                try:
                    data = json.loads(response)
                    if data.get("type") == "pong":
                        print("✓ Final ping successful - Teensy still responsive")
                except:
                    pass
            
            # Results summary
            print(f"\n📊 Test Results Summary")
            print("=" * 30)
            print(f"Total messages received: {message_count}")
            print(f"├─ Measurements: {measurement_count}")
            print(f"├─ Errors: {error_count}")
            print(f"├─ Status messages: {status_count}")
            print(f"└─ Other: {message_count - measurement_count - error_count - status_count}")
            print()
            
            if temp_readings:
                avg_temp = sum(temp_readings) / len(temp_readings)
                min_temp = min(temp_readings)
                max_temp = max(temp_readings)
                print(f"🌡️ Temperature Analysis:")
                print(f"   Average: {avg_temp:.1f}°C")
                print(f"   Range: {min_temp:.1f}°C - {max_temp:.1f}°C")
                print(f"   Readings: {len(temp_readings)}")
            
            if flow_readings:
                avg_flow = sum(flow_readings) / len(flow_readings)
                min_flow = min(flow_readings)
                max_flow = max(flow_readings)
                print(f"🌊 Flow Analysis:")
                print(f"   Average: {avg_flow:.4f} mL/min")
                print(f"   Range: {min_flow:.4f} - {max_flow:.4f} mL/min")
                print(f"   Readings: {len(flow_readings)}")
                print(f"   Expected: ~0.0000 mL/min (no flow, tubes not primed)")
            
            # Interpretation
            print(f"\n🎯 Interpretation:")
            if measurement_count > 0:
                print("✓ Sensor communication working")
            if temp_readings and all(20 < t < 35 for t in temp_readings):
                print("✓ Temperature readings realistic (room temperature)")
            if flow_readings and all(abs(f) < 0.01 for f in flow_readings):
                print("✓ Flow readings correct for no-flow condition")
            if error_count > 0:
                print(f"⚠ {error_count} sensor errors (normal for idle/no-flow state)")
            
            success = measurement_count > 0 and temp_readings
            return success
            
    except Exception as e:
        print(f"✗ Test failed: {e}")
        return False

def main():
    """Main test execution."""
    if len(sys.argv) > 1:
        port = sys.argv[1]
    else:
        port = '/dev/ttyACM0'
    
    if len(sys.argv) > 2:
        duration = int(sys.argv[2])
    else:
        duration = 10
    
    success = test_enhanced_teensy(port, duration)
    
    print(f"\n{'='*50}")
    if success:
        print("🎉 Enhanced test PASSED")
        print("   Teensy flow sensor is ready for RRR integration!")
        print("\n🚀 Next steps:")
        print("   1. Start RRR application")
        print("   2. Create test schedule")
        print("   3. Monitor for '✓ Flow sensor started' message")
    else:
        print("❌ Enhanced test FAILED")
        print("   Check Teensy connection and firmware")
    
    return 0 if success else 1

if __name__ == "__main__":
    sys.exit(main())
