import time
import sys

def test_connection():
    print("Testing relay connection...")
    
    # Try different I2C addresses
    addresses = [0, 1, 2, 3]  # Will try addresses 0x20, 0x21, 0x22, 0x23
    
    for addr in addresses:
        try:
            print(f"\nTrying sm_16relind with address {addr}...")
            import sm_16relind
            rel = sm_16relind.SM16relind(addr)
            print(f"Successfully connected using sm_16relind at address {addr}!")
            return rel, 'sm_16relind', addr
        except Exception as e:
            print(f"sm_16relind failed at address {addr}: {str(e)}")
            
            try:
                print(f"\nTrying SM16relind with address {addr}...")
                import SM16relind
                rel = SM16relind.SM16relind(addr)
                print(f"Successfully connected using SM16relind at address {addr}!")
                return rel, 'SM16relind', addr
            except Exception as e:
                print(f"SM16relind failed at address {addr}: {str(e)}")
    
    return None, None, None

if __name__ == "__main__":
    print("I2C Device Detection Results:")
    os.system("i2cdetect -y 1")
    
    rel, package_name, address = test_connection()
    if rel:
        print(f"\nSuccessfully connected using {package_name} at address {address}")
        print("\nTesting basic relay operations...")
        try:
            # Test single relay
            print("Testing relay 1...")
            rel.set(1, 1)
            time.sleep(1)
            rel.set(1, 0)
            print("Basic test completed!")
        except Exception as e:
            print(f"Error during basic test: {str(e)}")
        finally:
            rel.set_all(0)
    else:
        print("\nFailed to connect to relay hat at any address") 