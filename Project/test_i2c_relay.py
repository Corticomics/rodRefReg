import smbus2
import time

I2C_BUS = 8
ADDRESS = 0x08
START_MEASUREMENT = [0x36, 0x08]

bus = smbus2.SMBus(I2C_BUS)
print("Waiting for sensor startup...")
time.sleep(0.1)  # 100 ms delay for sensor startup

try:
    bus.write_i2c_block_data(ADDRESS, START_MEASUREMENT[0], [START_MEASUREMENT[1]])
    print("Start command sent OK!")
except Exception as e:
    print(f"Write error: {e}")
