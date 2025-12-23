#!/usr/bin/env python3
"""
USB Stability Test for Teensy Flow Sensor
Test USB connection stability and auto-recovery features
"""

import time
import serial
import json
import threading
import os
import signal
import sys
from datetime import datetime

class USBStabilityTester:
    def __init__(self, port='/dev/ttyACM1', duration_minutes=5):
        self.port = port
        self.duration_minutes = duration_minutes
        self.running = False
        self.serial_conn = None
        self.stats = {
            'messages_sent': 0,
            'messages_received': 0,
            'errors': 0,
            'reconnections': 0,
            'max_error_streak': 0,
            'current_error_streak': 0
        }
        
    def signal_handler(self, signum, frame):
        """Handle Ctrl+C gracefully"""
        print(f"\nReceived signal {signum}, shutting down...")
        self.running = False
        
    def connect(self):
        """Establish serial connection"""
        try:
            if self.serial_conn and self.serial_conn.is_open:
                self.serial_conn.close()
            
            self.serial_conn = serial.Serial(self.port, 115200, timeout=1.0)
            time.sleep(1.0)  # Allow Teensy to initialize
            return True
        except Exception as e:
            print(f"Connection failed: {e}")
            return False
    
    def test_ping(self):
        """Test basic ping communication"""
        try:
            if not self.serial_conn or not self.serial_conn.is_open:
                return False
                
            # Send ping
            command = {"cmd": "ping"}
            cmd_str = json.dumps(command) + '\n'
            self.serial_conn.write(cmd_str.encode('utf-8'))
            self.serial_conn.flush()
            self.stats['messages_sent'] += 1
            
            # Wait for response
            start_time = time.time()
            while time.time() - start_time < 2.0:
                if self.serial_conn.in_waiting:
                    line = self.serial_conn.readline().decode('utf-8').strip()
                    if line:
                        try:
                            response = json.loads(line)
                            if response.get("type") == "pong":
                                self.stats['messages_received'] += 1
                                self.stats['current_error_streak'] = 0
                                return True
                        except json.JSONDecodeError:
                            pass
                time.sleep(0.01)
            
            # No response received
            return False
            
        except Exception as e:
            print(f"Ping test error: {e}")
            return False
    
    def attempt_reconnection(self):
        """Attempt to reconnect after failure"""
        print(f"[{datetime.now().strftime('%H:%M:%S')}] Attempting reconnection...")
        
        # Close existing connection
        try:
            if self.serial_conn:
                self.serial_conn.close()
        except:
            pass
        
        # Wait and retry
        time.sleep(2.0)
        
        if self.connect():
            print(f"[{datetime.now().strftime('%H:%M:%S')}] ✓ Reconnection successful")
            self.stats['reconnections'] += 1
            return True
        else:
            print(f"[{datetime.now().strftime('%H:%M:%S')}] ✗ Reconnection failed")
            return False
    
    def run_test(self):
        """Run the stability test"""
        print(f"Starting USB stability test on {self.port}")
        print(f"Duration: {self.duration_minutes} minutes")
        print(f"Press Ctrl+C to stop early\n")
        
        # Set up signal handler
        signal.signal(signal.SIGINT, self.signal_handler)
        
        # Initial connection
        if not self.connect():
            print("Failed to establish initial connection")
            return False
        
        print(f"[{datetime.now().strftime('%H:%M:%S')}] ✓ Initial connection established")
        
        self.running = True
        start_time = time.time()
        end_time = start_time + (self.duration_minutes * 60)
        
        while self.running and time.time() < end_time:
            # Test communication
            if self.test_ping():
                print(f"[{datetime.now().strftime('%H:%M:%S')}] ✓ Ping successful")
            else:
                self.stats['errors'] += 1
                self.stats['current_error_streak'] += 1
                self.stats['max_error_streak'] = max(
                    self.stats['max_error_streak'], 
                    self.stats['current_error_streak']
                )
                
                print(f"[{datetime.now().strftime('%H:%M:%S')}] ✗ Ping failed (streak: {self.stats['current_error_streak']})")
                
                # Attempt reconnection after 3 consecutive failures
                if self.stats['current_error_streak'] >= 3:
                    if not self.attempt_reconnection():
                        print("Multiple reconnection attempts failed, continuing...")
                        time.sleep(5.0)  # Wait longer before retry
            
            # Wait before next test
            time.sleep(1.0)
        
        # Cleanup
        try:
            if self.serial_conn:
                self.serial_conn.close()
        except:
            pass
        
        self.print_results()
        return True
    
    def print_results(self):
        """Print test results"""
        print(f"\n{'='*50}")
        print(f"USB Stability Test Results")
        print(f"{'='*50}")
        print(f"Duration: {self.duration_minutes} minutes")
        print(f"Port: {self.port}")
        print(f"Messages sent: {self.stats['messages_sent']}")
        print(f"Messages received: {self.stats['messages_received']}")
        print(f"Success rate: {self.stats['messages_received']/max(self.stats['messages_sent'], 1)*100:.1f}%")
        print(f"Total errors: {self.stats['errors']}")
        print(f"Reconnections: {self.stats['reconnections']}")
        print(f"Max error streak: {self.stats['max_error_streak']}")
        
        if self.stats['errors'] == 0:
            print(f"\n🎉 Perfect! No USB connection issues detected.")
        elif self.stats['errors'] < 5:
            print(f"\n✅ Good stability with minor occasional errors.")
        elif self.stats['reconnections'] > 0:
            print(f"\n⚠️ USB connection issues detected, but recovery worked.")
        else:
            print(f"\n❌ Significant USB stability issues detected.")
            print(f"   Consider:")
            print(f"   1. Different USB cable")
            print(f"   2. Different USB port")
            print(f"   3. USB hub with power supply")
            print(f"   4. Checking Pi power supply")

def main():
    """Main entry point"""
    import sys
    
    port = sys.argv[1] if len(sys.argv) > 1 else '/dev/ttyACM1'
    duration = int(sys.argv[2]) if len(sys.argv) > 2 else 3  # Default 3 minutes
    
    # Check if port exists
    if not os.path.exists(port):
        print(f"Error: Port {port} does not exist")
        print("Available ports:")
        for i in range(5):
            test_port = f'/dev/ttyACM{i}'
            if os.path.exists(test_port):
                print(f"  {test_port}")
        return 1
    
    tester = USBStabilityTester(port, duration)
    success = tester.run_test()
    
    return 0 if success else 1

if __name__ == "__main__":
    sys.exit(main())
