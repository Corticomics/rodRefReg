#!/usr/bin/env python3
"""
SLF3S-0600F Sensor Wiring Diagnostic Tool
==========================================

Tests Teensy → Sensor I²C communication and visualizes flow data.

Based on Sensirion SLF3S-0600F Datasheet:
- I²C Address: 0x08
- Power: 3.2-3.8V (3.3V nominal)
- SCL Clock: 100-400 kHz
- Warm-up time: ~60ms
- Update rate: 500 Hz max

Teensy 4.1 I²C (Wire library):
- SDA: Pin 18 (GPIO 18)
- SCL: Pin 19 (GPIO 19)
- 3.3V: 250mA max output
- Internal pullups: 2.2kΩ (may need external 2kΩ)

This script:
1. Tests serial connection to Teensy
2. Requests sensor diagnostics from Teensy firmware
3. Visualizes real-time flow data if available
4. Provides wiring verification checklist
"""

import sys
import time
import json
import threading
from collections import deque
from datetime import datetime

try:
    import serial
except ImportError:
    print("ERROR: pyserial not installed")
    print("Install with: pip install pyserial")
    sys.exit(1)


class SensorDiagnostic:
    def __init__(self, port='/dev/ttyACM0', baud=115200):
        self.port = port
        self.baud = baud
        self.serial = None
        self.running = False
        self.reader_thread = None
        
        # Data collection
        self.flow_history = deque(maxlen=100)  # Last 100 readings
        self.temp_history = deque(maxlen=100)
        self.error_log = []
        self.frame_count = 0
        self.last_frame_time = None
        
    def connect(self):
        """Connect to Teensy"""
        print("🔌 Connecting to Teensy...")
        try:
            self.serial = serial.Serial(self.port, self.baud, timeout=2.0)
            print(f"  ⏳ Waiting for Teensy USB re-enumeration...")
            time.sleep(3.5)  # Extended wait for Pi (slower than Mac)
            
            # Flush any startup messages from buffer
            try:
                self.serial.reset_input_buffer()
                self.serial.reset_output_buffer()
            except:
                pass
            
            print(f"  ✅ Connected to {self.port}")
            return True
        except Exception as e:
            print(f"  ❌ Connection failed: {e}")
            print("\n💡 Troubleshooting:")
            print("   1. Check Teensy is plugged in")
            print("   2. Check USB cable (data cable, not power-only)")
            print("   3. Try: ls -l /dev/ttyACM* or /dev/ttyUSB*")
            print("   4. Try replugging Teensy (may enumerate as ACM1)")
            return False
    
    def send_command(self, cmd_dict):
        """Send JSON command to Teensy"""
        try:
            cmd_str = json.dumps(cmd_dict) + "\n"
            self.serial.write(cmd_str.encode('utf-8'))
            self.serial.flush()
            return True
        except Exception as e:
            print(f"  ❌ Command send failed: {e}")
            return False
    
    def test_ping(self):
        """Test basic Teensy communication"""
        print("\n📡 Testing Teensy communication...")
        
        if not self.send_command({"cmd": "ping"}):
            return False
        
        # Wait for pong
        start = time.time()
        while time.time() - start < 2.0:
            if self.serial.in_waiting:
                line = self.serial.readline().decode('utf-8', errors='ignore').strip()
                if line:
                    try:
                        msg = json.loads(line)
                        if msg.get('type') == 'pong':
                            latency = (time.time() - start) * 1000
                            print(f"  ✅ Teensy responding (latency: {latency:.1f}ms)")
                            return True
                    except json.JSONDecodeError:
                        pass
            time.sleep(0.01)
        
        print("  ❌ No response from Teensy")
        return False
    
    def request_status(self):
        """Request detailed sensor status from Teensy"""
        print("\n🔍 Requesting sensor status from Teensy...")
        
        if not self.send_command({"cmd": "status"}):
            return False
        
        # Wait for status response
        start = time.time()
        while time.time() - start < 2.0:
            if self.serial.in_waiting:
                line = self.serial.readline().decode('utf-8', errors='ignore').strip()
                if line:
                    try:
                        msg = json.loads(line)
                        if msg.get('type') in ['status', 'sensor_status']:
                            print(f"  📊 Teensy Status:")
                            print(f"     Running: {msg.get('running', 'unknown')}")
                            print(f"     Rate: {msg.get('rate', 'unknown')} Hz")
                            print(f"     Samples: {msg.get('samples', 0)}")
                            print(f"     Errors: {msg.get('errors', 0)}")
                            print(f"     Uptime: {msg.get('uptime', 0)}ms")
                            return msg
                        elif msg.get('type') == 'error':
                            print(f"  ⚠️  Teensy error: {msg.get('error', 'unknown')}")
                            self.error_log.append(msg.get('error', 'unknown'))
                    except json.JSONDecodeError:
                        print(f"  ⚠️  Invalid JSON: {line[:50]}...")
            time.sleep(0.01)
        
        print("  ❌ No status response")
        return None
    
    def start_streaming(self, rate_hz=10):
        """Start sensor streaming at specified rate"""
        print(f"\n🌊 Starting sensor streaming at {rate_hz} Hz...")
        
        if not self.send_command({"cmd": "start", "rate": rate_hz}):
            return False
        
        # Wait for sensor initialization (reset 30ms + warm-up ~60ms + first reading)
        print(f"  ⏳ Waiting for sensor initialization (reset + warm-up)...")
        time.sleep(0.2)  # 200ms to ensure sensor is ready
        
        # Wait for first measurement or error
        start = time.time()
        while time.time() - start < 5.0:  # Increased from 3s to 5s
            if self.serial.in_waiting:
                line = self.serial.readline().decode('utf-8', errors='ignore').strip()
                if line:
                    try:
                        msg = json.loads(line)
                        msg_type = msg.get('type')
                        
                        if msg_type == 'status':
                            # Status message confirming start - keep waiting for measurement
                            status_msg = msg.get('message', '')
                            if 'started' in status_msg.lower():
                                print(f"  📋 {status_msg}")
                            continue
                        elif msg_type == 'measurement':
                            print(f"  ✅ Sensor streaming! First reading:")
                            print(f"     Flow: {msg.get('flow', 'N/A')} mL/min")
                            print(f"     Temp: {msg.get('temp', 'N/A')} °C")
                            return True
                        elif msg_type == 'error':
                            error_msg = msg.get('error', 'unknown')
                            self.error_log.append(error_msg)
                            
                            # Ignore "0 bytes" errors - these are normal during sensor startup
                            # (transient frame during soft reset, per Sensirion datasheet)
                            if 'received 0 bytes' in error_msg.lower() or 'bytes' in error_msg.lower():
                                print(f"  ℹ️  Startup transient: {error_msg} (ignoring)")
                                continue  # Keep waiting for first measurement
                            
                            # Parse critical I²C errors (hardware issues)
                            print(f"  ❌ Sensor error: {error_msg}")
                            if 'I2C error' in error_msg or 'NACK' in error_msg:
                                print("\n  🔌 I²C Communication Failure Detected!")
                                self.print_i2c_troubleshooting()
                                return False
                    except json.JSONDecodeError:
                        pass
            time.sleep(0.01)
        
        print("  ❌ No sensor data received within 3 seconds")
        print("\n  💡 This usually means:")
        print("     1. Sensor not connected to Teensy I²C pins")
        print("     2. Sensor not powered (3.3V missing)")
        print("     3. Wrong I²C address (should be 0x08)")
        print("     4. I²C pullup resistors missing or wrong value")
        return False
    
    def visualize_stream(self, duration_s=30):
        """Real-time visualization of sensor data"""
        print(f"\n📊 Visualizing sensor stream for {duration_s} seconds...")
        print("   (Press Ctrl+C to stop early)\n")
        
        # Start background reader
        self.running = True
        self.reader_thread = threading.Thread(target=self._reader_loop, daemon=True)
        self.reader_thread.start()
        
        start = time.time()
        last_update = start
        
        try:
            while time.time() - start < duration_s:
                now = time.time()
                
                # Update display every 0.5s
                if now - last_update >= 0.5:
                    self._print_visualization()
                    last_update = now
                
                time.sleep(0.1)
        
        except KeyboardInterrupt:
            print("\n\n⚠️  Stopped by user")
        
        finally:
            self.running = False
            if self.reader_thread:
                self.reader_thread.join(timeout=1.0)
            
            # Final summary
            self._print_summary()
    
    def _reader_loop(self):
        """Background thread to read sensor data"""
        while self.running:
            try:
                if self.serial and self.serial.in_waiting:
                    line = self.serial.readline().decode('utf-8', errors='ignore').strip()
                    if line:
                        try:
                            msg = json.loads(line)
                            if msg.get('type') == 'measurement':
                                self.frame_count += 1
                                self.flow_history.append(float(msg.get('flow', 0.0)))
                                self.temp_history.append(float(msg.get('temp', 0.0)))
                                self.last_frame_time = time.time()
                            elif msg.get('type') == 'error':
                                self.error_log.append(msg.get('error', 'unknown'))
                        except (json.JSONDecodeError, ValueError):
                            pass
                else:
                    time.sleep(0.001)
            except Exception as e:
                self.error_log.append(f"Reader error: {e}")
                time.sleep(0.1)
    
    def _print_visualization(self):
        """Print current sensor readings"""
        if not self.flow_history:
            print("⏳ Waiting for sensor data...", end='\r')
            return
        
        # Calculate stats
        flow_current = self.flow_history[-1]
        flow_avg = sum(self.flow_history) / len(self.flow_history)
        flow_min = min(self.flow_history)
        flow_max = max(self.flow_history)
        
        temp_current = self.temp_history[-1] if self.temp_history else 0
        
        # Create simple bar graph for flow (scale to ±5 mL/min)
        bar_width = 40
        flow_scaled = int((flow_current / 5.0) * (bar_width / 2)) + (bar_width // 2)
        flow_scaled = max(0, min(bar_width, flow_scaled))
        
        bar = ['─'] * bar_width
        bar[bar_width // 2] = '┼'
        bar[flow_scaled] = '█'
        bar_str = ''.join(bar)
        
        # Print update (overwrite previous line)
        print(f"📊 Frames: {self.frame_count:4d} | "
              f"Flow: {flow_current:+6.3f} mL/min | "
              f"Temp: {temp_current:5.2f}°C | "
              f"[{bar_str}]", end='\r')
    
    def _print_summary(self):
        """Print final summary"""
        print("\n\n" + "="*70)
        print("📊 SENSOR STREAM SUMMARY")
        print("="*70)
        
        if self.frame_count == 0:
            print("\n❌ NO DATA RECEIVED")
            print("\n🔧 Wiring Check Required:")
            self.print_wiring_checklist()
            return
        
        # Calculate stats
        flow_avg = sum(self.flow_history) / len(self.flow_history) if self.flow_history else 0
        flow_min = min(self.flow_history) if self.flow_history else 0
        flow_max = max(self.flow_history) if self.flow_history else 0
        temp_avg = sum(self.temp_history) / len(self.temp_history) if self.temp_history else 0
        
        print(f"\n✅ Total Frames: {self.frame_count}")
        print(f"\n📊 Flow Statistics:")
        print(f"   Average: {flow_avg:+.4f} mL/min")
        print(f"   Range:   {flow_min:+.4f} to {flow_max:+.4f} mL/min")
        print(f"\n🌡️  Temperature: {temp_avg:.2f}°C average")
        
        if self.error_log:
            print(f"\n⚠️  Errors Logged: {len(self.error_log)}")
            for i, err in enumerate(self.error_log[:5], 1):
                print(f"   {i}. {err}")
            if len(self.error_log) > 5:
                print(f"   ... and {len(self.error_log) - 5} more")
        
        # Data quality assessment
        print(f"\n✅ Data Quality Assessment:")
        if flow_min == flow_max == flow_avg:
            print("   ⚠️  Flow readings are constant (sensor may be stuck)")
        elif abs(flow_avg) < 0.001:
            print("   ✅ Zero flow detected (expected when no liquid flowing)")
        else:
            print(f"   ✅ Dynamic flow detected ({abs(flow_max - flow_min):.3f} mL/min range)")
        
        print("="*70 + "\n")
    
    def print_wiring_checklist(self):
        """Print detailed wiring verification checklist"""
        print("\n" + "="*70)
        print("🔌 SENSOR WIRING CHECKLIST")
        print("="*70)
        print("\nBased on SLF3S-0600F Datasheet + Teensy 4.1 Pinout:\n")
        
        print("Step 1: Power Connections")
        print("  [ ] Sensor VDD (Red) → Teensy 3V3 pin")
        print("  [ ] Sensor GND (Black) → Terminal block star point")
        print("  [ ] Measure: VDD to GND should read 3.25-3.35V")
        print()
        
        print("Step 2: I²C Data Lines")
        print("  [ ] Sensor SDA (White/Green) → Teensy Pin 18")
        print("  [ ] Sensor SCL (Yellow/Blue) → Teensy Pin 19")
        print("  [ ] Check: No short between SDA and SCL (>10kΩ)")
        print()
        
        print("Step 3: Pullup Resistors (CRITICAL)")
        print("  [ ] 2kΩ resistor from SDA to 3V3")
        print("  [ ] 2kΩ resistor from SCL to 3V3")
        print("  [ ] Measure: SDA/SCL to 3V3 should read ~2kΩ")
        print("  [ ] Measure: SDA/SCL to GND should read >10kΩ (high impedance)")
        print()
        
        print("Step 4: Teensy Firmware Check")
        print("  [ ] Teensy uploaded with teensy_flow_reader.ino")
        print("  [ ] Wire.begin() called in setup()")
        print("  [ ] Wire.setClock(100000) for 100kHz I²C")
        print("  [ ] Sensor address = 0x08")
        print()
        
        print("Step 5: Physical Inspection")
        print("  [ ] All connections tight (no loose dupont wires)")
        print("  [ ] No crossed wires (SDA ≠ SCL)")
        print("  [ ] Sensor not damaged (visual inspection)")
        print("  [ ] Breadboard connections clean (no corrosion)")
        print()
        
        print("💡 Common Issues:")
        print("   1. Missing pullup resistors (most common!)")
        print("   2. Wrong resistor value (should be 2kΩ, not 10kΩ)")
        print("   3. Sensor powered from breadboard instead of Teensy 3V3")
        print("   4. Ground not connected to star point")
        print("   5. I²C pins swapped (SDA ↔ SCL)")
        print("="*70 + "\n")
    
    def print_i2c_troubleshooting(self):
        """Print I²C-specific troubleshooting"""
        print("\n  🔧 I²C Troubleshooting Steps:")
        print("     1. Verify pullup resistors present (2kΩ each)")
        print("     2. Check SDA/SCL not swapped")
        print("     3. Measure voltage on SDA/SCL (should be ~3.3V at idle)")
        print("     4. Try lower I²C speed in Teensy firmware: Wire.setClock(50000)")
        print("     5. Check sensor address: should be 0x08")
    
    def print_sensor_troubleshooting(self):
        """Print sensor-specific troubleshooting"""
        print("\n  🔧 Sensor Troubleshooting Steps:")
        print("     1. Verify 3.3V power present on sensor VDD pin")
        print("     2. Check sensor ground connected")
        print("     3. Wait 100ms after power-on before I²C communication")
        print("     4. Verify sensor not damaged (visual inspection)")
        print("     5. Try different sensor if available")
    
    def stop_streaming(self):
        """Stop sensor streaming"""
        if self.serial:
            try:
                self.send_command({"cmd": "stop"})
                time.sleep(0.2)
            except:
                pass
    
    def close(self):
        """Cleanup"""
        self.running = False
        self.stop_streaming()
        if self.serial:
            try:
                self.serial.close()
            except:
                pass


def main():
    import argparse
    parser = argparse.ArgumentParser(description="SLF3S-0600F Sensor Wiring Diagnostic")
    parser.add_argument('--port', default='/dev/ttyACM0', help='Teensy serial port')
    parser.add_argument('--rate', type=int, default=10, help='Streaming rate (Hz)')
    parser.add_argument('--duration', type=int, default=30, help='Visualization duration (s)')
    args = parser.parse_args()
    
    print("="*70)
    print("🔬 SLF3S-0600F SENSOR WIRING DIAGNOSTIC")
    print("="*70)
    print("\nThis tool will:")
    print("  1. Test Teensy communication")
    print("  2. Check sensor I²C connection")
    print("  3. Visualize real-time flow data")
    print("  4. Provide wiring troubleshooting if needed")
    print()
    
    diag = SensorDiagnostic(port=args.port)
    
    try:
        # Step 1: Connect to Teensy
        if not diag.connect():
            return 1
        
        # Step 2: Test basic communication
        if not diag.test_ping():
            print("\n❌ Basic communication failed")
            return 1
        
        # Step 3: Request status
        diag.request_status()
        
        # Step 4: Start streaming
        if not diag.start_streaming(rate_hz=args.rate):
            print("\n❌ Sensor streaming failed")
            print("\n🔧 NEXT STEPS:")
            diag.print_wiring_checklist()
            return 1
        
        # Step 5: Visualize data
        diag.visualize_stream(duration_s=args.duration)
        
        return 0
    
    except KeyboardInterrupt:
        print("\n\n⚠️  Interrupted by user")
        return 1
    
    finally:
        diag.close()


if __name__ == '__main__':
    sys.exit(main())

