import smbus2
import time

I2C_BUS = 8
ADDRESS = 0x08
START_FLOW_CMD = [0x36, 0x08]  # Per SLF3S-0600F documentation, start continuous measurement

def main():
    bus = smbus2.SMBus(I2C_BUS)
    print(f"Starting measurement on I2C bus {I2C_BUS} at address 0x{ADDRESS:02X}")

    # Send the "start continuous measurement" command
    bus.write_i2c_block_data(ADDRESS, START_FLOW_CMD[0], [START_FLOW_CMD[1]])

    try:
        while True:
            # Read 6 bytes: flow, temperature, status (see Sensirion docs)
            data = bus.read_i2c_block_data(ADDRESS, 0x00, 6)
            # Flow is first two bytes (big endian)
            flow_raw = (data[0] << 8) | data[1]
            print(f"Raw flow: {flow_raw}, All bytes: {data}")
            time.sleep(1)
    except KeyboardInterrupt:
        print("Stopped.")

if __name__ == "__main__":
    main()
