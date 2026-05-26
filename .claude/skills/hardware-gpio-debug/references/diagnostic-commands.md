# Shell-level hardware diagnostics

Operator-friendly commands. Run from any shell on the device; no Python needed.

## Bus and HAT presence

```bash
# Bus 1, addresses 0x03–0x77
i2cdetect -y 1

# Sequent Microsystems CLI: board info / relay state / individual relays
16relind 0 board                # stack 0 = first HAT
16relind 0 read 1               # 0 = off, 1 = on
16relind 0 write 1 1            # click on
16relind 0 write 1 0            # click off
```

`16relind` is the vendor's own tool and bypasses RRR's entire stack — useful
to isolate "is it the hardware?" from "is it our code?". If `16relind`
works and RRR doesn't, the fault is in `RelayHandler`/`RelayWorker`.

## Teensy flow sensor (UART)

```bash
ls -l /dev/teensy_flow          # stable udev symlink; installer creates it
ls -l /dev/serial/by-id/*Teensy*

# Tail the protocol bytes
stty -F /dev/teensy_flow 115200 raw
cat /dev/teensy_flow | head -c 200 | xxd
```

If `/dev/teensy_flow` is missing, the udev rule from
[scripts/install/40-hardware.sh](scripts/install/40-hardware.sh) didn't apply —
re-run with `./install.sh --only 40-hardware`.

## Mock-fallback detection

```bash
# Tail the app's debug log; "MockSM16relind" means we're not on real hardware
tail -F ~/rrr_app_debug.log | grep -i mock

# On an installed device data root:
tail -F "$HOME/rrr/shared/logs/rrr_app_debug.log" | grep -i mock
```

If you see `MockSM16relind` lines while running on a real Pi, the
`sm_16relind` import failed — usually means the venv was built without
`--system-site-packages` or the apt package isn't installed.

## I²C bus reset (last resort)

```bash
sudo modprobe -r i2c_dev i2c_bcm2835
sudo modprobe i2c_bcm2835 i2c_dev
```

This kicks a stuck I²C controller. Won't fix wiring; will sometimes recover
from a clock-stretching deadlock after a hot-swap.
