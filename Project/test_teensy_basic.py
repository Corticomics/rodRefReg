#!/usr/bin/env python3
"""
Basic Teensy Communication Test
===============================

Tests direct communication with Teensy 4.1 to diagnose UART issues.
"""

import serial
import json
import time
import sys

def test_teensy_basic(port='/dev/ttyACM0', baudrate=115200):
    """Test basic communication with Teensy."""
    
    print(f"Testing Teensy communication on {port} at {baudrate} baud")
    print("=" * 60)
    
    try:
        # Open serial connection with longer timeout
        print("Opening serial connection...")
        ser = serial.Serial(port, baudrate, timeout=5.0)
        time.sleep(3)  # Give Teensy time to initialize
        
        print(f"✓ Serial port opened: {ser.name}")
        print(f"  Baudrate: {ser.baudrate}")
        print(f"  Timeout: {ser.timeout}")
        print(f"  Is open: {ser.is_open}")
        
        # Clear any existing data
        ser.reset_input_buffer()
        ser.reset_output_buffer()
        
        # Test 1: Send ping command
        print("\n--- Test 1: Ping Command ---")
        ping_cmd = '{"cmd":"ping"}\n'
        print(f"Sending: {ping_cmd.strip()}")
        
        ser.write(ping_cmd.encode('utf-8'))
        ser.flush()
        
        # Wait for response
        print("Waiting for response...")
        response = ser.readline().decode('utf-8').strip()
        
        if response:
            print(f"Received: {response}")
            try:
                data = json.loads(response)
                if data.get("type") == "pong":
                    print("✓ Ping successful!")
                else:
                    print(f"? Unexpected response: {data}")
            except json.JSONDecodeError:
                print(f"? Non-JSON response: {response}")
        else:
            print("✗ No response received")
        
        # Test 2: Check if any data is coming
        print("\n--- Test 2: Listen for Any Data ---")
        print("Listening for 5 seconds...")
        
        start_time = time.time()
        received_anything = False
        
        while time.time() - start_time < 5:
            if ser.in_waiting > 0:
                data = ser.read(ser.in_waiting)
                print(f"Raw data: {data}")
                received_anything = True
            time.sleep(0.1)
        
        if not received_anything:
            print("No data received during listening period")
        
        # Test 3: Try sensor commands
        print("\n--- Test 3: Sensor Commands ---")
        start_cmd = '{"cmd":"start","rate":1}\n'
        print(f"Sending: {start_cmd.strip()}")
        
        ser.write(start_cmd.encode('utf-8'))
        ser.flush()
        
        print("Waiting for sensor data...")
        for i in range(10):  # Wait up to 10 seconds
            if ser.in_waiting > 0:
                line = ser.readline().decode('utf-8').strip()
                if line:
                    print(f"Sensor data: {line}")
                    try:
                        data = json.loads(line)
                        if "flow" in data:
                            print("✓ Flow sensor data received!")
                            break
                    except json.JSONDecodeError:
                        pass
            time.sleep(1)
        
        # Stop sensor
        stop_cmd = '{"cmd":"stop"}\n'
        ser.write(stop_cmd.encode('utf-8'))
        ser.flush()
        
        ser.close()
        print("\n✓ Test completed")
        return True
        
    except serial.SerialException as e:
        print(f"✗ Serial error: {e}")
        return False
    except Exception as e:
        print(f"✗ Unexpected error: {e}")
        return False

def find_teensy_port():
    """Auto-detect Teensy device port."""
    import glob
    import os
    
    # Common Teensy device patterns
    potential_ports = []
    
    # Check common serial device patterns
    patterns = [
        '/dev/ttyACM*',
        '/dev/ttyUSB*', 
        '/dev/cu.usbmodem*',  # macOS
        '/dev/ttyS*'
    ]
    
    for pattern in patterns:
        potential_ports.extend(glob.glob(pattern))
    
    # Also check by-id directory for Teensy
    try:
        by_id_devices = glob.glob('/dev/serial/by-id/*')
        for device in by_id_devices:
            if 'teensy' in device.lower() or 'arduino' in device.lower():
                # Resolve symlink to actual device
                actual_device = os.path.realpath(device)
                potential_ports.append(actual_device)
    except:
        pass
    
    print(f"Found potential serial ports: {potential_ports}")
    
    # Filter existing devices
    existing_ports = [p for p in potential_ports if os.path.exists(p)]
    print(f"Existing ports: {existing_ports}")
    
    if existing_ports:
        return existing_ports[0]  # Return first available
    else:
        return '/dev/ttyACM0'  # Fallback

if __name__ == "__main__":
    print("Teensy 4.1 Communication Test")
    print("Make sure:")
    print("1. Teensy is connected via USB")
    print("2. Teensy has flow sensor firmware loaded")
    print("3. Flow sensor is connected to Teensy I2C pins")
    print()
    
    # Auto-detect or use provided port
    if len(sys.argv) > 1:
        port = sys.argv[1]
    else:
        port = find_teensy_port()
        print(f"Auto-detected port: {port}")
    
    success = test_teensy_basic(port)
    
    if not success:
        print("\n🔧 Troubleshooting suggestions:")
        print("1. Check USB connection")
        print("2. Verify Teensy firmware is loaded")
        print("3. Try different USB port")
        print("4. Check flow sensor wiring to Teensy")
        print("5. Verify /dev/ttyACM0 permissions")
        sys.exit(1)
    else:
        print("\n🎉 Teensy communication working!")
