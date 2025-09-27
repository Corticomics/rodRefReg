import smbus2
import time

I2C_BUS = 8
ADDRESS = 0x08
CMD_BYTES = [0x36, 0x08]

def send_start(bus):
    # Prepare the raw write message (no register byte)
    msg = smbus2.i2c_msg.write(ADDRESS, CMD_BYTES)
    try:
        bus.i2c_rdwr(msg)
        return True
    except OSError as e:
        print(f"Raw write error: {e}")
        return False

def main():
    bus = smbus2.SMBus(I2C_BUS)
    print("Powering sensor and waiting 500 ms for warm-up...")
    time.sleep(0.5)

    if not send_start(bus):
        print("Failed to send start command via raw I²C write.")
        return
    print("Measurement started successfully!")

    try:
        while True:
            data = bus.read_i2c_block_data(ADDRESS, 0x00, 9)
            raw = (data[0] << 8) | data[1]
            if raw & 0x8000: raw -= 1 << 16
            print(f"Flow: {raw/10:.2f} µL/min")
            time.sleep(1)
    except KeyboardInterrupt:
        print("Stopped.")

if __name__ == "__main__":
    main()
