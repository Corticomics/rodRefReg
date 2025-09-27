import smbus2
import time

I2C_BUS = 8
ADDRESS = 0x08

START_MEASUREMENT = [0x36, 0x08]  # For water

bus = smbus2.SMBus(I2C_BUS)
# Step 1: Start continuous measurement
bus.write_i2c_block_data(ADDRESS, START_MEASUREMENT[0], [START_MEASUREMENT[1]])
time.sleep(0.06)  # Wait at least 60 ms for warm-up

try:
    while True:
        # Step 2: Read 9 bytes: 2 (flow) + 1 (crc) + 2 (temp) + 1 (crc) + 2 (flags) + 1 (crc)
        data = bus.read_i2c_block_data(ADDRESS, 0x00, 9)
        # Convert flow bytes, ignoring CRC for basic demo
        flow_raw = (data[0] << 8) | data[1]
        # Handle two's complement for signed value:
        if flow_raw >= 0x8000: flow_raw -= 0x10000
        flow_ul_min = flow_raw / 10.0
        print(f"Flow: {flow_ul_min:.2f} μL/min, Raw bytes: {data}")
        time.sleep(1)
except KeyboardInterrupt:
    print("Stopped.")
