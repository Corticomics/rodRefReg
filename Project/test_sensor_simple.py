#!/usr/bin/env python3
"""
Simple Teensy Flow Sensor Test - Raw Serial Dump
=================================================

Dead simple script to:
1. Open serial port
2. Send start command
3. Print EVERYTHING received for 30 seconds

Based on pyserial documentation:
https://pyserial.readthedocs.io/en/latest/pyserial_api.html
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
    port = '/dev/ttyACM0'
    baud = 115200
    duration = 30  # seconds
    
    print("="*70)
    print("🔬 SIMPLE TEENSY FLOW SENSOR TEST")
    print("="*70)
    print(f"\nPort: {port}")
    print(f"Baud: {baud}")
    print(f"Duration: {duration}s")
    print("\n" + "="*70)
    
    # Step 1: Open serial port
    print("\n[1] Opening serial port...")
    try:
        ser = serial.Serial(port, baud, timeout=1.0)
        print(f"    ✅ Port opened: {ser.name}")
        print(f"    ✅ Is open: {ser.is_open}")
    except Exception as e:
        print(f"    ❌ Failed to open port: {e}")
        return 1
    
    # Step 2: Wait for Teensy USB re-enumeration
    print("\n[2] Waiting for Teensy to initialize...")
    print("    (Teensy resets when serial port opens)")
    time.sleep(3.5)
    print("    ✅ Wait complete")
    
    # Step 3: Flush any startup messages
    print("\n[3] Flushing input buffer...")
    try:
        bytes_waiting = ser.in_waiting
        print(f"    📊 Bytes in buffer: {bytes_waiting}")
        if bytes_waiting > 0:
            flushed = ser.read(bytes_waiting)
            print(f"    🗑️  Flushed {len(flushed)} bytes")
            try:
                print(f"    📝 Content: {flushed.decode('utf-8', errors='ignore')[:100]}")
            except:
                pass
        ser.reset_input_buffer()
        ser.reset_output_buffer()
        print("    ✅ Buffers cleared")
    except Exception as e:
        print(f"    ⚠️  Flush failed: {e}")
    
    # Step 4: Send ping to verify connection
    print("\n[4] Testing connection with ping...")
    try:
        ping_cmd = json.dumps({"cmd": "ping"}) + "\n"
        ser.write(ping_cmd.encode('utf-8'))
        ser.flush()
        print(f"    📤 Sent: {ping_cmd.strip()}")
        
        # Wait for pong
        time.sleep(0.5)
        if ser.in_waiting:
            line = ser.readline().decode('utf-8', errors='ignore').strip()
            print(f"    📥 Received: {line}")
            try:
                msg = json.loads(line)
                if msg.get('type') == 'pong':
                    print("    ✅ Ping successful!")
                else:
                    print(f"    ⚠️  Unexpected response: {msg.get('type')}")
            except:
                print("    ⚠️  Not JSON")
        else:
            print("    ⚠️  No response")
    except Exception as e:
        print(f"    ❌ Ping failed: {e}")
    
    # Step 5: Send start command
    print("\n[5] Sending start command...")
    try:
        start_cmd = json.dumps({"cmd": "start", "rate": 10}) + "\n"
        ser.write(start_cmd.encode('utf-8'))
        ser.flush()
        print(f"    📤 Sent: {start_cmd.strip()}")
        print("    ✅ Command sent")
    except Exception as e:
        print(f"    ❌ Send failed: {e}")
        ser.close()
        return 1
    
    # Step 6: Read and print EVERYTHING for duration
    print("\n[6] Reading sensor data for " + str(duration) + " seconds...")
    print("    (Printing ALL messages received)\n")
    print("="*70)
    
    start_time = time.time()
    message_count = 0
    measurement_count = 0
    error_count = 0
    status_count = 0
    
    try:
        while time.time() - start_time < duration:
            # Check if data is available
            if ser.in_waiting > 0:
                # Read one line
                try:
                    line = ser.readline().decode('utf-8', errors='ignore').strip()
                    
                    if not line:
                        continue
                    
                    # Print timestamp and raw message
                    elapsed = time.time() - start_time
                    print(f"[{elapsed:6.2f}s] RAW: {line}")
                    
                    # Try to parse as JSON
                    try:
                        msg = json.loads(line)
                        msg_type = msg.get('type', 'unknown')
                        message_count += 1
                        
                        if msg_type == 'measurement':
                            measurement_count += 1
                            flow = msg.get('flow', 'N/A')
                            temp = msg.get('temp', 'N/A')
                            count = msg.get('count', 'N/A')
                            print(f"          ✅ MEASUREMENT #{count}: flow={flow} mL/min, temp={temp}°C")
                        
                        elif msg_type == 'error':
                            error_count += 1
                            error_msg = msg.get('error', 'unknown')
                            print(f"          ⚠️  ERROR: {error_msg}")
                        
                        elif msg_type == 'status':
                            status_count += 1
                            status_msg = msg.get('message', 'unknown')
                            print(f"          📋 STATUS: {status_msg}")
                        
                        else:
                            print(f"          ❓ {msg_type.upper()}: {msg}")
                    
                    except json.JSONDecodeError:
                        print(f"          ⚠️  NOT JSON")
                
                except UnicodeDecodeError as e:
                    print(f"[{elapsed:6.2f}s] ⚠️  Decode error: {e}")
                
                except Exception as e:
                    print(f"[{elapsed:6.2f}s] ❌ Read error: {e}")
            
            else:
                # No data available, small delay
                time.sleep(0.01)
    
    except KeyboardInterrupt:
        print("\n\n⚠️  Interrupted by user")
    
    finally:
        # Step 7: Send stop command
        print("\n" + "="*70)
        print("[7] Stopping sensor...")
        try:
            stop_cmd = json.dumps({"cmd": "stop"}) + "\n"
            ser.write(stop_cmd.encode('utf-8'))
            ser.flush()
            print("    ✅ Stop command sent")
            time.sleep(0.2)
        except:
            pass
        
        # Step 8: Close port
        print("\n[8] Closing serial port...")
        try:
            ser.close()
            print("    ✅ Port closed")
        except:
            pass
    
    # Summary
    print("\n" + "="*70)
    print("SUMMARY")
    print("="*70)
    print(f"Total messages:    {message_count}")
    print(f"Measurements:      {measurement_count}")
    print(f"Errors:            {error_count}")
    print(f"Status messages:   {status_count}")
    print("="*70)
    
    if measurement_count > 0:
        print("\n✅ SUCCESS - Sensor is streaming data!")
        print(f"   Received {measurement_count} measurements in {duration:.1f} seconds")
        expected = duration * 10  # 10 Hz rate
        loss_pct = ((expected - measurement_count) / expected) * 100
        print(f"   Expected ~{expected} at 10 Hz")
        print(f"   Frame loss: {loss_pct:.1f}%")
        return 0
    else:
        print("\n❌ FAILURE - No measurements received")
        print("   Check wiring and firmware")
        return 1


if __name__ == '__main__':
    sys.exit(main())

