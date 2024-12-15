import RPi.GPIO as GPIO
import time

# Relay GPIO pins for Sequent Multi I/O HAT
RELAY1_PIN = 26  # RL1
RELAY2_PIN = 20  # RL2

def setup():
    # Use GPIO numbers rather than pin numbers
    GPIO.setmode(GPIO.BCM)
    
    # Setup relay pins as outputs
    GPIO.setup(RELAY1_PIN, GPIO.OUT)
    GPIO.setup(RELAY2_PIN, GPIO.OUT)
    
    # Initialize relays to OFF
    GPIO.output(RELAY1_PIN, GPIO.HIGH)  # Relays are typically active LOW
    GPIO.output(RELAY2_PIN, GPIO.HIGH)

def test_relay(relay_pin, relay_name, cycles=3):
    """Test a single relay by turning it on and off multiple times"""
    print(f"\nTesting {relay_name}...")
    
    for i in range(cycles):
        print(f"Cycle {i + 1}/{cycles}")
        
        # Turn relay ON (active LOW)
        print(f"{relay_name} ON")
        GPIO.output(relay_pin, GPIO.LOW)
        time.sleep(1)
        
        # Turn relay OFF
        print(f"{relay_name} OFF")
        GPIO.output(relay_pin, GPIO.HIGH)
        time.sleep(1)

def main():
    try:
        setup()
        
        # Test each relay
        test_relay(RELAY1_PIN, "Relay 1")
        test_relay(RELAY2_PIN, "Relay 2")
        
        # Test both relays together
        print("\nTesting both relays together...")
        for i in range(3):
            print(f"Cycle {i + 1}/3")
            
            # Both ON
            print("Both relays ON")
            GPIO.output(RELAY1_PIN, GPIO.LOW)
            GPIO.output(RELAY2_PIN, GPIO.LOW)
            time.sleep(1)
            
            # Both OFF
            print("Both relays OFF")
            GPIO.output(RELAY1_PIN, GPIO.HIGH)
            GPIO.output(RELAY2_PIN, GPIO.HIGH)
            time.sleep(1)
            
    except KeyboardInterrupt:
        print("\nTest interrupted by user")
    finally:
        # Clean up GPIO settings
        GPIO.cleanup()
        print("\nTest completed, GPIO cleaned up")

if __name__ == "__main__":
    main()