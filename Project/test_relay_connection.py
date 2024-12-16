#!/usr/bin/env python3

import sys
import time
try:
    import SM16relind
except ImportError:
    print("Error: SM16relind module not found. Please install using:")
    print("cd 16relind-rpi/ && sudo make install")
    sys.exit(1)

def test_connection():
    try:
        # Initialize the relay hat
        print("Initializing relay hat...")
        relay_hat = SM16relind.SM16relind(0)
        
        # Test single relay
        print("Testing relay 1...")
        relay_hat.set(1, 1)  # Turn on relay 1
        time.sleep(1)
        relay_hat.set(1, 0)  # Turn off relay 1
        
        # Test all relays
        print("Testing all relays...")
        relay_hat.set_all(1)  # Turn all on
        time.sleep(1)
        relay_hat.set_all(0)  # Turn all off
        
        print("Test completed successfully!")
        return True
    except Exception as e:
        print(f"Error during test: {str(e)}")
        return False

if __name__ == "__main__":
    test_connection() 