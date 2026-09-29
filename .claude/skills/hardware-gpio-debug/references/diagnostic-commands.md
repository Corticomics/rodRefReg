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

## No-hardware fallback detection

The relay library and the HATs are set up while the app boots, before it
redirects its output to the Terminal tab, so the evidence is in the journal
(the systemd unit sends stdout there), not in `rrr_app_debug.log`:

```bash
journalctl --user -u rrr.service -b | grep -E "SM16relind module not found|Failed to initialize"
```

- `WARNING: SM16relind module not found` — the relay library did not
  import: usually the venv was built without `--system-site-packages` or
  the apt package is missing.
- `Failed to initialize any relay hats` (after `Failed to initialize hat
  stack=N: …`) — the library loaded but no HAT answered.

In either case `RelayHandler` has no hats and every relay write is a silent
no-op that still reports success, so schedules run and log deliveries with
no valve moving. Fix the cause and restart the app before trusting a run.

## I²C bus reset (last resort)

```bash
sudo modprobe -r i2c_dev i2c_bcm2835
sudo modprobe i2c_bcm2835 i2c_dev
```

This kicks a stuck I²C controller. Won't fix wiring; will sometimes recover
from a clock-stretching deadlock after a hot-swap.
