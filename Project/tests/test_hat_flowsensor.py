#!/usr/bin/env python3
"""
Test script: Open relay 1, stream flow sensor data for 5 seconds, then close relay 1.
Assumes:
- Sequent Microsystems 16-relay HAT with SM16relind installed
- Teensy firmware streaming JSON over UART1 connected to /dev/serial0
- Python3, pyserial installed
"""

import time
import json
import serial
import SM16relind

# Configuration
RELAY_STACK = 0          # Relay HAT stack address (0 if single HAT)
RELAY_NUM = 1            # Relay channel to test (1-based index)
TEENSY_PORT = "/dev/serial0"
BAUD_RATE = 115200
STREAM_DURATION = 5.0    # seconds

def main():
    # Initialize relay HAT object
    rel = SM16relind.SM16relind(RELAY_STACK)

    # Open relay 1
    rel.set(RELAY_NUM, 1)
    print(f"Relay {RELAY_NUM} set to {rel.get(RELAY_NUM)}")

    # Connect to Teensy UART
    try:
        ser = serial.Serial(TEENSY_PORT, BAUD_RATE, timeout=1.0)
        time.sleep(2.5)  # Wait for UART to be ready
        ser.reset_input_buffer()
    except Exception as e:
        print(f"Error: Cannot open serial port {TEENSY_PORT}: {e}")
        rel.set(RELAY_NUM, 0)
        return

    # Read and print flow data for STREAM_DURATION
    print(f"Streaming flow data for {STREAM_DURATION} seconds...")
    end_time = time.time() + STREAM_DURATION
    while time.time() < end_time:
        try:
            line = ser.readline().decode('utf-8').strip()
            if not line:
                continue
            data = json.loads(line)
            if 'flow_rate' in data:
                timestamp = time.strftime("%H:%M:%S")
                print(f"{timestamp} Flow rate: {data['flow_rate']}")
        except json.JSONDecodeError:
            continue  # skip partial frames
        except Exception as e:
            print(f"Serial read error: {e}")
            break

    # Close relay 1
    rel.set(RELAY_NUM, 0)
    print(f"Relay {RELAY_NUM} set to {rel.get(RELAY_NUM)}")

    # Cleanup
    ser.close()

if __name__ == "__main__":
    main()
