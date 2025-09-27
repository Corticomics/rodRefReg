import smbus2
import time

I2C_BUS = 8
ADDRESS = 0x08
CMD_HIGH = 0x36
CMD_LOW  = 0x08

def send_start(bus):
    # Try block-data write first
    for attempt in range(5):
        try:
            bus.write_i2c_block_data(ADDRESS, CMD_HIGH, [CMD_LOW])
            return True
        except OSError:
            time.sleep(0.02)  # 20 ms retry delay
    # Fallback: send two separate writes (some SMBus implementations accept this)
    try:
        bus.write_byte_data(ADDRESS, CMD_HIGH, CMD_LOW)
        return True
    except OSError:
        return False

def main():
    bus = smbus2.SMBus(I2C_BUS)
    time.sleep(0.1)  # initial wait
    if not send_start(bus):
        print("Failed to send start command after retries.")
        return
    print("Measurement started.")
    try:
        while True:
            data = bus.read_i2c_block_data(ADDRESS, 0x00, 9)
            raw = (data[0] << 8) | data[1]
            if raw & 0x8000: raw -= 1<<16
            print(f"Flow: {raw/10:.2f} µL/min")
            time.sleep(1)
    except KeyboardInterrupt:
        print("Stopped.")

if __name__ == "__main__":
    main()
