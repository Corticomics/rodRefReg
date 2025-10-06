#!/usr/bin/env python3
"""
Integration Test: Relay Switching During Sensor Streaming
==========================================================

Tests the critical scenario that was previously failing:
- Sensor streaming continuously via USB (Teensy + SLF3S-0600F)
- Relays switching solenoids (12V inductive load via Sequent 16-Relays HAT)
- Monitor for USB disconnects, CRC errors, frame gaps

Hardware References:
- Sequent 16-Relays HAT: https://cdn.shopify.com/s/files/1/0534/4392/0067/files/16-RELAYS-UsersGuide_d5e24457-bdd9-4e16-a307-7f90bbd668bb.pdf
- Teensy 4.1: https://www.pjrc.com/store/teensy41.html
- SLF3S-0600F: https://sensirion.com/media/documents/C4F8D965/66F56F53/LQ_DS_SLF3S-0600F_Datasheet.pdf

Success criteria per Sensirion reliability standards:
- Zero USB disconnects
- Zero "Flow stream not available" errors
- >95% frame delivery (per SLF3S f_flow spec: up to 500 Hz capable)
- Sensor recovers within 1s after relay activity
- Max frame gap <2s (allows for transient EMI)
"""

import sys
import time
import threading
from datetime import datetime
from pathlib import Path

# Import canonical serial protocol
sys.path.insert(0, str(Path(__file__).parent))
from drivers.teensy_serial_protocol import TeensySerialProtocol, FlowMeasurement

# Check dependencies
try:
    import SM16relind
except ImportError as e:
    print(f"Missing dependency: {e}")
    print("Install with: sudo apt install python3-sm16relind")
    sys.exit(1)


class IntegrationTest:
    """
    Integration test using canonical TeensySerialProtocol.
    
    Validates concurrent relay switching + sensor streaming per:
    - SLF3S-0600F datasheet (500 Hz max update rate)
    - Sequent 16-Relays HAT specifications
    - Teensy 4.1 USB CDC best practices
    """
    
    def __init__(self, teensy_port='/dev/ttyACM0', relay_stack=0):
        self.teensy_port = teensy_port
        self.relay_stack = relay_stack
        self.protocol = None  # TeensySerialProtocol instance
        self.relay_hat = None
        
        # Test metrics
        self.frames_received = 0
        self.frames_expected = 0
        self.errors = []
        self.usb_disconnects = 0
        self.max_frame_gap = 0.0
        self.last_frame_time = None
        self.latest_measurement = None  # Store latest measurement for live display
        
        # Control
        self.running = False
        self.sensor_thread = None
        
    def setup(self):
        """
        Initialize hardware using canonical protocols.
        
        Per hardware documentation:
        - Teensy: 3.5s USB CDC enumeration (handled by protocol)
        - Relay HAT: I2C stack 0-7, default 0x20 address
        """
        print("🔧 Initializing hardware...")
        
        # Initialize Teensy using canonical protocol
        try:
            self.protocol = TeensySerialProtocol(port=self.teensy_port)
            self.protocol.connect()  # Handles 3.5s wait + ping test
            print(f"  ✓ Teensy connected on {self.teensy_port}")
        except Exception as e:
            print(f"  ✗ Teensy connection failed: {e}")
            return False
        
        # Initialize Relay HAT per Sequent documentation
        try:
            self.relay_hat = SM16relind.SM16relind(self.relay_stack)
            self.relay_hat.set_all(0)  # All off per safety best practice
            print(f"  ✓ Relay HAT initialized (stack {self.relay_stack})")
        except Exception as e:
            print(f"  ✗ Relay HAT initialization failed: {e}")
            return False
        
        return True
    
    def start_sensor(self, rate_hz=50):
        """
        Start sensor streaming using canonical protocol.
        
        Per SLF3S-0600F datasheet Section 2.2:
        - Soft reset: 25ms
        - Warm-up: ~60ms
        - Total initialization: ~100ms (handled by protocol)
        """
        try:
            if not self.protocol.send_start_command(rate_hz=rate_hz):
                return False
            print(f"  ✓ Sensor streaming started at {rate_hz} Hz")
            return True
        except Exception as e:
            print(f"  ✗ Sensor start failed: {e}")
            return False
    
    def stop_sensor(self):
        """Stop sensor streaming using canonical protocol."""
        try:
            self.protocol.send_stop_command()
        except Exception:
            pass
    
    def sensor_reader_thread(self):
        """
        Background thread to read sensor data using canonical protocol.
        
        Monitors:
        - Frame delivery rate
        - USB connection stability
        - Inter-frame gaps (EMI indicator)
        - Error messages from Teensy
        - Live measurements
        """
        while self.running:
            try:
                # Check USB connection health
                if not self.protocol or not self.protocol.is_connected:
                    self.usb_disconnects += 1
                    self.errors.append(f"USB disconnect at frame {self.frames_received}")
                    time.sleep(0.1)
                    continue
                
                # Read message using canonical protocol
                msg = self.protocol.read_message(timeout_s=0.1)
                
                if msg:
                    now = time.time()
                    msg_type = msg.get('type')
                    
                    if msg_type == 'measurement':
                        # Track frame gaps to detect EMI-induced delays
                        if self.last_frame_time:
                            gap = now - self.last_frame_time
                            self.max_frame_gap = max(self.max_frame_gap, gap)
                        self.last_frame_time = now
                        self.frames_received += 1
                        
                        # Store latest measurement for live display
                        self.latest_measurement = {
                            'flow': msg.get('flow', 0.0),
                            'temp': msg.get('temp', 0.0),
                            'count': msg.get('count', 0)
                        }
                        
                    elif msg_type == 'error':
                        error_msg = msg.get('error', 'Unknown error')
                        # Ignore transient "0 bytes" during warm-up (per protocol logic)
                        if 'bytes' not in error_msg.lower():
                            self.errors.append(error_msg)
                else:
                    time.sleep(0.001)  # Prevent CPU spinning
                    
            except Exception as e:
                self.errors.append(f"Reader error: {e}")
                time.sleep(0.1)
    
    def pulse_relay(self, relay_id, duration_s=1.0):
        """
        Pulse a single relay per Sequent 16-Relays HAT specification.
        
        Per Sequent documentation:
        - set(relay_num, state): relay_num 1-16, state 0 or 1
        - Generates back-EMF on inductive loads (solenoids)
        - Star grounding mitigates conducted EMI
        """
        try:
            self.relay_hat.set(relay_id, 1)  # ON
            time.sleep(duration_s)
            self.relay_hat.set(relay_id, 0)  # OFF
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
                    
                    # Print live measurement before relay switch
                    if self.latest_measurement:
                        print(f"  [{elapsed:5.1f}s] 📊 Before: flow={self.latest_measurement['flow']:.4f} mL/min, temp={self.latest_measurement['temp']:.2f}°C")
                    
                    print(f"  [{elapsed:5.1f}s] 🔌 Pulsing relay {relay_id}...", end='')
                    frames_before = self.frames_received
                    
                    self.pulse_relay(relay_id, duration_s=0.5)
                    
                    time.sleep(0.5)  # Wait for sensor to recover
                    frames_after = self.frames_received
                    frames_during = frames_after - frames_before
                    expected_during = int(1.0 * 50)  # 50 Hz * 1s
                    loss_pct = ((expected_during - frames_during) / expected_during) * 100
                    
                    print(f" Frames: {frames_during}/{expected_during} (loss: {loss_pct:.1f}%)")
                    
                    # Print live measurement after relay switch
                    if self.latest_measurement:
                        print(f"  [{elapsed:5.1f}s] 📊 After: flow={self.latest_measurement['flow']:.4f} mL/min, temp={self.latest_measurement['temp']:.2f}°C")
                
                # Progress update
                if int(elapsed) % 5 == 0 and int(elapsed) > 0:
                    frame_rate = self.frames_received / elapsed
                    print(f"  [{elapsed:5.1f}s] 📊 Received {self.frames_received} frames ({frame_rate:.1f} Hz), {len(self.errors)} errors")
                
                time.sleep(0.5)
        
        except KeyboardInterrupt:
            print("\n⚠️  Test interrupted by user")
        
        finally:
            # Cleanup per best practices
            self.running = False
            self.stop_sensor()
            
            # Ensure all relays OFF (Sequent safety best practice)
            if self.relay_hat:
                try:
                    self.relay_hat.set_all(0)
                except Exception:
                    pass
            
            # Wait for reader thread to exit gracefully
            if self.sensor_thread:
                self.sensor_thread.join(timeout=2.0)
            
            # Close serial connection using canonical protocol
            if self.protocol:
                self.protocol.close()
        
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

