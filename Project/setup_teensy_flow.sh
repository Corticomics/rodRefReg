#!/bin/bash

# Teensy 4.1 Flow Sensor Setup for RRR Production
# This script configures UART flow sensor mode using Teensy bridge

echo "=== RRR Teensy Flow Sensor Setup ==="
echo "Configuring UART flow sensor mode with Teensy 4.1 bridge"
echo ""

# Check if we're in the Project directory
if [ ! -f "settings.json" ]; then
    echo "Error: settings.json not found. Please run from Project directory."
    exit 1
fi

# Install required Python packages
echo "Installing required Python packages..."
pip install pyserial ArduinoJson

# Auto-detect Teensy USB port
echo "Detecting Teensy USB port..."
TEENSY_PORT=""

# Try common Teensy device patterns
for port in /dev/ttyACM* /dev/ttyUSB*; do
    if [ -e "$port" ]; then
        echo "Found potential USB device: $port"
        # Try to communicate with device
        if timeout 2 bash -c "echo '{\"cmd\":\"ping\"}' > $port && read -r line < $port" 2>/dev/null; then
            if echo "$line" | grep -q "pong"; then
                TEENSY_PORT="$port"
                echo "✓ Teensy detected at $port"
                break
            fi
        fi
    fi
done

if [ -z "$TEENSY_PORT" ]; then
    echo "⚠️  Teensy not detected. Using default /dev/ttyACM0"
    echo "   Make sure Teensy is connected and programmed with flow reader firmware"
    TEENSY_PORT="/dev/ttyACM0"
fi

# Update RRR settings for UART flow sensor
echo "Updating RRR settings for UART flow sensor..."

python3 << EOF
import json
import sys

try:
    # Read current settings
    with open('settings.json', 'r') as f:
        settings = json.load(f)
    
    # Update for UART flow sensor
    settings['flow_sensor_type'] = 'uart'
    settings['uart_port'] = '$TEENSY_PORT'
    settings['hardware_mode'] = 'solenoid'
    
    # Keep I2C settings for relay HAT
    if 'i2c_bus' not in settings:
        settings['i2c_bus'] = 1  # Relay HAT stays on bus 1
    
    # Write updated settings
    with open('settings.json', 'w') as f:
        json.dump(settings, f, indent=4)
    
    print("✓ Settings updated for UART flow sensor")
    print(f"  - Flow sensor type: uart")
    print(f"  - UART port: $TEENSY_PORT")
    print(f"  - Hardware mode: solenoid")
    
except Exception as e:
    print(f"✗ Error updating settings: {e}")
    sys.exit(1)
EOF

if [ $? -ne 0 ]; then
    echo "Failed to update settings"
    exit 1
fi

# Create Teensy test script
echo "Creating Teensy test script..."

cat > test_teensy_flow.py << 'EOF'
#!/usr/bin/env python3
"""
Test script for Teensy flow sensor communication
"""

import json
import serial
import time
import sys

def test_teensy_communication(port='/dev/ttyACM0'):
    """Test basic communication with Teensy flow sensor."""
    
    print(f"Testing Teensy communication on {port}")
    print("=" * 50)
    
    try:
        # Open serial connection
        ser = serial.Serial(port, 115200, timeout=2.0)
        time.sleep(2)  # Wait for Teensy to initialize
        
        print("✓ Serial connection established")
        
        # Test ping
        print("Testing ping...")
        ser.write(b'{"cmd":"ping"}\n')
        ser.flush()
        
        response = ser.readline().decode('utf-8').strip()
        if response:
            data = json.loads(response)
            if data.get("type") == "pong":
                print("✓ Ping successful")
            else:
                print(f"✗ Unexpected response: {data}")
                return False
        else:
            print("✗ No response to ping")
            return False
        
        # Test sensor start
        print("Testing sensor start...")
        ser.write(b'{"cmd":"start","rate":10}\n')
        ser.flush()
        
        # Wait for measurement data
        print("Waiting for measurement data...")
        start_time = time.time()
        measurements = 0
        
        while time.time() - start_time < 10 and measurements < 5:
            if ser.in_waiting:
                line = ser.readline().decode('utf-8').strip()
                if line:
                    try:
                        data = json.loads(line)
                        if data.get("type") == "measurement":
                            flow = data.get("flow", 0)
                            temp = data.get("temp", 0)
                            print(f"  Flow: {flow:.2f} mL/min, Temp: {temp:.1f}°C")
                            measurements += 1
                        elif data.get("type") == "error":
                            print(f"  Sensor error: {data.get('error')}")
                    except json.JSONDecodeError:
                        print(f"  Invalid JSON: {line}")
            time.sleep(0.1)
        
        # Stop sensor
        ser.write(b'{"cmd":"stop"}\n')
        ser.flush()
        
        ser.close()
        
        if measurements > 0:
            print(f"✓ Received {measurements} measurements")
            print("✓ Teensy flow sensor is working correctly")
            return True
        else:
            print("✗ No measurements received")
            return False
            
    except Exception as e:
        print(f"✗ Test failed: {e}")
        return False

if __name__ == "__main__":
    port = sys.argv[1] if len(sys.argv) > 1 else '/dev/ttyACM0'
    success = test_teensy_communication(port)
    
    if success:
        print("\n🎉 Teensy flow sensor ready for RRR!")
        print("   Next steps:")
        print("   1. Run RRR application")
        print("   2. Test solenoid delivery schedule")
    else:
        print("\n⚠️  Teensy test failed")
        print("   Troubleshooting:")
        print("   1. Check Teensy USB connection")
        print("   2. Verify firmware is loaded") 
        print("   3. Check flow sensor wiring to Teensy")
        sys.exit(1)
EOF

chmod +x test_teensy_flow.py

# Test Teensy communication
echo ""
echo "Testing Teensy communication..."
if python3 test_teensy_flow.py "$TEENSY_PORT"; then
    echo ""
    echo "=== Setup Complete! ==="
    echo "✓ UART flow sensor configured"
    echo "✓ Teensy communication verified"
    echo "✓ RRR ready for solenoid delivery"
    echo ""
    echo "Hardware Configuration:"
    echo "  • Relay HAT: I2C bus 1 (pins 3/5)"
    echo "  • Flow sensor: Teensy bridge via $TEENSY_PORT"
    echo "  • Master solenoid: Relay 16"
    echo ""
    echo "Next steps:"
    echo "  1. Run RRR: python3 main.py"
    echo "  2. Test delivery schedule"
    echo "  3. Monitor for 'uart on $TEENSY_PORT' message"
else
    echo ""
    echo "⚠️  Teensy test failed. Check connections and firmware."
    echo ""
    echo "Required connections:"
    echo "  • Teensy USB to Pi"
    echo "  • Flow sensor SDA to Teensy pin 18 (I2C0_SDA)"
    echo "  • Flow sensor SCL to Teensy pin 19 (I2C0_SCL)"
    echo "  • Flow sensor VDD to Teensy 3.3V"
    echo "  • Flow sensor GND to Teensy GND"
fi
