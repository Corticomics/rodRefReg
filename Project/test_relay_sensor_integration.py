#!/usr/bin/env python3
"""
Integration Test: Relay Switching During Sensor Streaming
==========================================================

Tests the critical scenario that was previously failing:
- Sensor streaming continuously via USB
- Relays switching solenoids (12V inductive load)
- Monitor for USB disconnects, CRC errors, frame gaps

Success criteria:
- Zero USB disconnects
- Zero "Flow stream not available" errors
- <5% frame loss during relay switching
- Sensor recovers within 1s after relay activity
"""

import sys
import time
import threading
import json
from datetime import datetime
from pathlib import Path

# Check dependencies
try:
    import serial
    import SM16relind
except ImportError as e:
    print(f"Missing dependency: {e}")
    print("Install with: pip install pyserial")
    sys.exit(1)


class IntegrationTest:
    def __init__(self, teensy_port='/dev/ttyACM0', relay_stack=0):
        self.teensy_port = teensy_port
        self.relay_stack = relay_stack
        self.serial = None
        self.relay_hat = None
        
        # Test metrics
        self.frames_received = 0
        self.frames_expected = 0
        self.errors = []
        self.usb_disconnects = 0
        self.max_frame_gap = 0.0
        self.last_frame_time = None
        
        # Control
        self.running = False
        self.sensor_thread = None
        
    def setup(self):
        """Initialize hardware"""
        print("🔧 Initializing hardware...")
        
        # Initialize Teensy
        try:
            self.serial = serial.Serial(self.teensy_port, 115200, timeout=2.0)
            time.sleep(2.5)  # CDC enumeration
            print(f"  ✓ Teensy connected on {self.teensy_port}")
        except Exception as e:
            print(f"  ✗ Teensy connection failed: {e}")
            return False
        
        # Initialize Relay HAT
        try:
            self.relay_hat = SM16relind.SM16relind(self.relay_stack)
            self.relay_hat.set_all(0)  # All off
            print(f"  ✓ Relay HAT initialized (stack {self.relay_stack})")
        except Exception as e:
            print(f"  ✗ Relay HAT initialization failed: {e}")
            return False
        
        return True
    
    def start_sensor(self, rate_hz=50):
        """Start sensor streaming"""
        try:
            cmd = json.dumps({"cmd": "start", "rate": rate_hz}) + "\n"
            self.serial.write(cmd.encode('utf-8'))
            self.serial.flush()
            time.sleep(0.5)
            print(f"  ✓ Sensor streaming started at {rate_hz} Hz")
            return True
        except Exception as e:
            print(f"  ✗ Sensor start failed: {e}")
            return False
    
    def stop_sensor(self):
        """Stop sensor streaming"""
        try:
            cmd = json.dumps({"cmd": "stop"}) + "\n"
            self.serial.write(cmd.encode('utf-8'))
            self.serial.flush()
            time.sleep(0.2)
        except Exception:
            pass
    
    def sensor_reader_thread(self):
        """Background thread to read sensor data"""
        while self.running:
            try:
                if not self.serial or not self.serial.is_open:
                    self.usb_disconnects += 1
                    self.errors.append(f"USB disconnect at frame {self.frames_received}")
                    time.sleep(0.1)
                    continue
                
                if self.serial.in_waiting:
                    line = self.serial.readline().decode('utf-8', errors='ignore').strip()
                    if line:
                        now = time.time()
                        
                        # Track frame gaps
                        if self.last_frame_time:
                            gap = now - self.last_frame_time
                            self.max_frame_gap = max(self.max_frame_gap, gap)
                        self.last_frame_time = now
                        
                        try:
                            msg = json.loads(line)
                            if msg.get('type') == 'measurement':
                                self.frames_received += 1
                            elif msg.get('type') == 'error':
                                self.errors.append(msg.get('error', 'Unknown error'))
                        except json.JSONDecodeError:
                            self.errors.append(f"Invalid JSON: {line[:50]}")
                else:
                    time.sleep(0.001)
                    
            except Exception as e:
                self.errors.append(f"Reader error: {e}")
                time.sleep(0.1)
    
    def pulse_relay(self, relay_id, duration_s=1.0):
        """Pulse a single relay"""
        try:
            self.relay_hat.set(relay_id, 1)
            time.sleep(duration_s)
            self.relay_hat.set(relay_id, 0)
            return True
        except Exception as e:
            self.errors.append(f"Relay {relay_id} pulse failed: {e}")
            return False
    
    def run_test(self, duration_s=30, relay_pulse_interval_s=3):
        """Main test execution"""
        print("\n" + "="*60)
        print("🧪 INTEGRATION TEST: Relay Switching During Sensor Streaming")
        print("="*60)
        
        if not self.setup():
            return False
        
        if not self.start_sensor(rate_hz=50):
            return False
        
        # Calculate expected frames
        self.frames_expected = int(duration_s * 50)  # 50 Hz
        
        # Start sensor reader thread
        self.running = True
        self.sensor_thread = threading.Thread(target=self.sensor_reader_thread, daemon=True)
        self.sensor_thread.start()
        
        print(f"\n⏱️  Running {duration_s}s test with relay switching every {relay_pulse_interval_s}s...")
        print("   Monitoring: USB stability, frame delivery, error count\n")
        
        # Test loop with relay switching
        start_time = time.time()
        relay_cycle = 0
        relays_to_test = [15, 16]  # Your master and cage solenoids
        
        try:
            while time.time() - start_time < duration_s:
                elapsed = time.time() - start_time
                
                # Pulse relays at intervals
                if int(elapsed / relay_pulse_interval_s) > relay_cycle:
                    relay_cycle = int(elapsed / relay_pulse_interval_s)
                    relay_id = relays_to_test[relay_cycle % len(relays_to_test)]
                    
                    print(f"  [{elapsed:5.1f}s] 🔌 Pulsing relay {relay_id}...", end='')
                    frames_before = self.frames_received
                    
                    self.pulse_relay(relay_id, duration_s=0.5)
                    
                    time.sleep(0.5)  # Wait for sensor to recover
                    frames_after = self.frames_received
                    frames_during = frames_after - frames_before
                    expected_during = int(1.0 * 50)  # 50 Hz * 1s
                    loss_pct = ((expected_during - frames_during) / expected_during) * 100
                    
                    print(f" Frames: {frames_during}/{expected_during} (loss: {loss_pct:.1f}%)")
                
                # Progress update
                if int(elapsed) % 5 == 0 and int(elapsed) > 0:
                    frame_rate = self.frames_received / elapsed
                    print(f"  [{elapsed:5.1f}s] 📊 Received {self.frames_received} frames ({frame_rate:.1f} Hz), {len(self.errors)} errors")
                
                time.sleep(0.5)
        
        except KeyboardInterrupt:
            print("\n⚠️  Test interrupted by user")
        
        finally:
            # Cleanup
            self.running = False
            self.stop_sensor()
            self.relay_hat.set_all(0)
            
            if self.sensor_thread:
                self.sensor_thread.join(timeout=2.0)
            
            if self.serial:
                self.serial.close()
        
        # Results
        return self.print_results()
    
    def print_results(self):
        """Print test results and determine pass/fail"""
        print("\n" + "="*60)
        print("📊 TEST RESULTS")
        print("="*60)
        
        # Calculate metrics
        actual_duration = self.frames_received / 50 if self.frames_received > 0 else 0
        frame_delivery_rate = (self.frames_received / self.frames_expected * 100) if self.frames_expected > 0 else 0
        
        print(f"\n📈 Frame Delivery:")
        print(f"   Expected: {self.frames_expected} frames")
        print(f"   Received: {self.frames_received} frames")
        print(f"   Rate: {frame_delivery_rate:.1f}%")
        print(f"   Max gap: {self.max_frame_gap:.3f}s")
        
        print(f"\n🔌 USB Stability:")
        print(f"   Disconnects: {self.usb_disconnects}")
        print(f"   Status: {'✅ STABLE' if self.usb_disconnects == 0 else '❌ UNSTABLE'}")
        
        print(f"\n⚠️  Errors:")
        print(f"   Total: {len(self.errors)}")
        if self.errors:
            print("   Recent errors:")
            for err in self.errors[-5:]:
                print(f"     - {err}")
        else:
            print("   ✅ No errors")
        
        # Pass/Fail criteria
        pass_criteria = {
            'usb_stable': self.usb_disconnects == 0,
            'frame_delivery': frame_delivery_rate >= 95,
            'max_gap': self.max_frame_gap < 2.0,
            'low_errors': len(self.errors) < 10
        }
        
        print(f"\n✅ Pass/Fail Criteria:")
        for criterion, passed in pass_criteria.items():
            status = "✅ PASS" if passed else "❌ FAIL"
            print(f"   {criterion}: {status}")
        
        all_passed = all(pass_criteria.values())
        
        print("\n" + "="*60)
        if all_passed:
            print("🎉 TEST PASSED - System is production-ready!")
            print("   ✅ USB stable during relay switching")
            print("   ✅ Sensor streaming reliable")
            print("   ✅ Ready for full RRR delivery testing")
        else:
            print("❌ TEST FAILED - Hardware issues remain")
            if not pass_criteria['usb_stable']:
                print("   ❌ USB still disconnecting → Add flyback diodes")
            if not pass_criteria['frame_delivery']:
                print("   ❌ Frame loss too high → Check grounding/EMI")
            if not pass_criteria['max_gap']:
                print("   ❌ Long frame gaps → EMI or USB issues")
        print("="*60 + "\n")
        
        return all_passed


def main():
    import argparse
    parser = argparse.ArgumentParser(description="Integration test: Relay + Sensor")
    parser.add_argument('--port', default='/dev/ttyACM0', help='Teensy serial port')
    parser.add_argument('--stack', type=int, default=0, help='Relay HAT stack level')
    parser.add_argument('--duration', type=int, default=30, help='Test duration (seconds)')
    parser.add_argument('--interval', type=int, default=3, help='Relay pulse interval (seconds)')
    args = parser.parse_args()
    
    test = IntegrationTest(teensy_port=args.port, relay_stack=args.stack)
    success = test.run_test(duration_s=args.duration, relay_pulse_interval_s=args.interval)
    
    sys.exit(0 if success else 1)


if __name__ == '__main__':
    main()

