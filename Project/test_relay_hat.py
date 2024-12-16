#!/usr/bin/env python3

import RPi.GPIO as GPIO
import sm_16relind
import time

def test_relay_hat():
    try:
        # Initialize the relay hat (using index 0 for the first hat)
        print("Initializing relay hat...")
        relay_hat = sm_16relind.SM16relind(0)
        
        # Test 1: Individual relay test
        print("\nTest 1: Testing each relay individually...")
        for relay in range(1, 17):
            print(f"Activating relay {relay}")
            relay_hat.set(relay, 1)  # Turn on
            time.sleep(1)
            relay_hat.set(relay, 0)  # Turn off
            time.sleep(0.5)
        
        # Test 2: All relays on/off
        print("\nTest 2: Testing all relays together...")
        print("Turning all relays ON")
        relay_hat.set_all(1)
        time.sleep(2)
        print("Turning all relays OFF")
        relay_hat.set_all(0)
        time.sleep(1)
        
        # Test 3: Sequential pattern
        print("\nTest 3: Running sequential pattern...")
        for _ in range(2):  # Run pattern twice
            # Turn on relays in sequence
            for relay in range(1, 17):
                relay_hat.set(relay, 1)
                time.sleep(0.2)
            # Turn off relays in sequence
            for relay in range(1, 17):
                relay_hat.set(relay, 0)
                time.sleep(0.2)
        
        print("\nRelay hat testing completed successfully!")
        
    except Exception as e:
        print(f"An error occurred: {str(e)}")
    finally:
        # Ensure all relays are turned off
        try:
            relay_hat.set_all(0)
        except:
            pass
        GPIO.cleanup()

if __name__ == "__main__":
    print("Starting relay hat test sequence...")
    test_relay_hat() 