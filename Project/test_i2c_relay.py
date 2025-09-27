import smbus2
import time

I2C_BUS = 8
ADDRESS = 0x08
START_MEASUREMENT = [0x36, 0x08]  # per datasheet

bus = smbus2.SMBus(I2C_BUS)
time.sleep(0.1)  # sensor startup

# Send start measurement
bus.write_i2c_block_data(ADDRESS, START_MEASUREMENT[0], [START_MEASUREMENT[1]])

try:
    while True:
        # Read 9 bytes: Flow(2)+CRC(1), Temp(2)+CRC(1), Flags(2)+CRC(1)
        data = bus.read_i2c_block_data(ADDRESS, 0x00, 9)

        # Parse flow (first two bytes)
        flow_raw = (data[0] << 8) | data[1]
        if flow_raw & 0x8000:  # two’s complement
            flow_raw -= 1 << 16
        # Scale: flow_raw / 10 = µL/min
        flow_rate = flow_raw / 10.0

        print(f"Flow: {flow_rate:.2f} µL/min | Raw: {flow_raw} | Bytes: {data}")
        time.sleep(1)
except KeyboardInterrupt:
    print("Measurement stopped.")
