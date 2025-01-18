#!/usr/bin/python3
import RPi.GPIO as GPIO
import time

class RelayDiscovery:
    def __init__(self):
        # List of all possible GPIO pins on Raspberry Pi
        # Excluding special pins like I2C, SPI, etc.
        self.possible_pins = [
            2, 3, 4, 17, 27, 22, 10, 9, 11, 5, 6, 13, 19, 26, 
            14, 15, 18, 23, 24, 25, 8, 7, 12, 16, 20, 21
        ]
        self.discovered_relays = []
        self.setup_gpio()

    def setup_gpio(self):
        GPIO.setmode(GPIO.BCM)
        GPIO.setwarnings(False)

    def test_pin(self, pin):
        """Test if a pin controls a relay"""
        try:
            print(f"\nTesting GPIO {pin}")
            GPIO.setup(pin, GPIO.OUT)
            
            # Turn the pin ON (relay might be active LOW or HIGH)
            print("Testing active LOW...")
            GPIO.output(pin, GPIO.LOW)
            response = input(f"Did you hear/see relay click? (y/n): ").lower()
            if response == 'y':
                return True, "LOW"
            
            print("Testing active HIGH...")
            GPIO.output(pin, GPIO.HIGH)
            response = input(f"Did you hear/see relay click? (y/n): ").lower()
            if response == 'y':
                return True, "HIGH"
            
            # Reset pin to input to avoid leaving it active
            GPIO.setup(pin, GPIO.IN)
            return False, None
            
        except Exception as e:
            print(f"Error testing pin {pin}: {e}")
            return False, None

    def discover_relays(self):
        """Run discovery process for all possible pins"""
        print("Starting relay discovery process...")
        print("Listen for relay clicks and watch for relay LED indicators.")
        print("Press Ctrl+C at any time to stop the discovery process.")
        
        try:
            for pin in self.possible_pins:
                is_relay, active_state = self.test_pin(pin)
                if is_relay:
                    self.discovered_relays.append((pin, active_state))
                    print(f"\nRelay found! GPIO {pin} (Active {active_state})")
                    
                    # Ask if user wants to continue
                    if input("\nContinue searching? (y/n): ").lower() != 'y':
                        break

        except KeyboardInterrupt:
            print("\nDiscovery process interrupted by user")

        finally:
            self.cleanup()
            self.print_results()

    def verify_discovered_relays(self):
        """Verify all discovered relays by testing them in sequence"""
        if not self.discovered_relays:
            print("No relays to verify!")
            return

        print("\nVerifying discovered relays...")
        try:
            for pin, active_state in self.discovered_relays:
                GPIO.setup(pin, GPIO.OUT)
                
                # Activate relay
                state = GPIO.LOW if active_state == "LOW" else GPIO.HIGH
                print(f"\nTesting GPIO {pin} (Active {active_state})")
                GPIO.output(pin, state)
                time.sleep(1)
                GPIO.output(pin, not state)
                time.sleep(0.5)
                
                if input("Did the relay work correctly? (y/n): ").lower() != 'y':
                    print(f"Marking GPIO {pin} as potentially incorrect")
        
        finally:
            self.cleanup()

    def cleanup(self):
        """Clean up GPIO settings"""
        GPIO.cleanup()

    def print_results(self):
        """Print the discovery results"""
        print("\n=== Relay Discovery Results ===")
        if self.discovered_relays:
            print("Discovered relays:")
            for pin, active_state in self.discovered_relays:
                print(f"GPIO {pin} (Active {active_state})")
            
            print("\nTo use these in the relay test script, set relay_pins to:")
            pins = [pin for pin, _ in self.discovered_relays]
            print(f"relay_pins = {pins}")
        else:
            print("No relays were discovered")

def main():
    discoverer = RelayDiscovery()
    print("This script will help discover which GPIO pins control your relays.")
    print("You'll need to confirm when you hear or see a relay activate.")
    
    if input("\nReady to begin? (y/n): ").lower() == 'y':
        discoverer.discover_relays()
        
        if discoverer.discovered_relays:
            if input("\nWould you like to verify all discovered relays? (y/n): ").lower() == 'y':
                discoverer.verify_discovered_relays()

if __name__ == "__main__":
    main()