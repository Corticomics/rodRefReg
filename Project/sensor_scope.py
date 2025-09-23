#!/usr/bin/env python3
"""
Sensor Scope – SLF3S-0600F Live Reader (no GUI)
================================================

Purpose: Minimal, dependency-free tool to visualize SLF3S-0600F readings
from the Raspberry Pi over I²C. Prints a live table and ASCII bars.

Usage examples:
  python3 sensor_scope.py --bus 1 --rate 20
  python3 sensor_scope.py --bus 1 --rate 20 --seconds 60 --csv readings.csv

Notes:
  - Uses the project driver (drivers/flow_sensor.SLF3S0600FDriver)
  - Handles intermittent read errors and shows counters
  - No matplotlib; safe for headless use
"""

import argparse
import csv
import os
import sys
import time
from datetime import datetime

# Allow running directly from Project/ or repo root
if os.path.basename(os.getcwd()) == 'Project':
    sys.path.append('.')
else:
    sys.path.append('Project')

from drivers.flow_sensor import SLF3S0600FDriver  # noqa: E402


def _sparkline(value: float, vmin: float, vmax: float, width: int = 40) -> str:
    if vmax <= vmin:
        return ' ' * width
    clamped = max(vmin, min(value, vmax))
    frac = (clamped - vmin) / (vmax - vmin)
    bars = int(frac * width)
    return ('#' * bars) + ('-' * (width - bars))


def run_scope(bus: int, rate_hz: float, seconds: int | None, csv_path: str | None) -> int:
    sampling_period = 1.0 / max(1.0, rate_hz)
    sensor = SLF3S0600FDriver(i2c_bus=bus, sampling_hz=rate_hz)

    # Start sensor once
    try:
        sensor.start()
    except Exception as e:
        print(f"ERROR: Failed to start sensor on bus {bus}: {e}")
        return 2

    csv_file = None
    csv_writer = None
    if csv_path:
        try:
            csv_file = open(csv_path, 'w', newline='')
            csv_writer = csv.writer(csv_file)
            csv_writer.writerow(['timestamp_iso', 'flow_ml_min', 'temp_c'])
        except Exception as e:
            print(f"WARN: Could not open CSV '{csv_path}': {e}")
            csv_file = None
            csv_writer = None

    print("\nSLF3S-0600F Sensor Scope")
    print(f"Bus: {bus}   Rate: {rate_hz:.1f} Hz   CSV: {csv_path or '-'}")
    print("Press Ctrl+C to stop.\n")

    start = time.time()
    last_ok_ts = None
    null_count = 0
    ok_count = 0
    min_flow = +1e9
    max_flow = -1e9

    # Define a practical visualization range (adjust if needed)
    vis_min = -10.0  # ml/min (slight reverse or noise)
    vis_max = 60.0   # ml/min

    try:
        while True:
            if seconds is not None and (time.time() - start) > seconds:
                break

            reading = sensor.read_one()  # returns tuple or None
            now = datetime.now().isoformat(timespec='seconds')

            if reading is None:
                null_count += 1
                sys.stdout.write(f"{now}  flow: ----  temp: ----   ERR(null)={null_count}  OK={ok_count}\r")
                sys.stdout.flush()
                time.sleep(sampling_period)
                continue

            flow_ul_min, temp_c, _flags = reading
            flow_ml_min = flow_ul_min / 1000.0

            ok_count += 1
            last_ok_ts = time.time()
            min_flow = min(min_flow, flow_ml_min)
            max_flow = max(max_flow, flow_ml_min)

            bar = _sparkline(flow_ml_min, vis_min, vis_max)
            line = f"{now}  flow: {flow_ml_min:7.2f} ml/min  temp: {temp_c:6.2f} C  [{bar}]"
            sys.stdout.write(line + "\r")
            sys.stdout.flush()

            if csv_writer:
                try:
                    csv_writer.writerow([now, f"{flow_ml_min:.5f}", f"{temp_c:.3f}"])
                except Exception:
                    pass

            time.sleep(sampling_period)

    except KeyboardInterrupt:
        print("\nInterrupted by user.")
    finally:
        try:
            sensor.stop()
        except Exception:
            pass
        if csv_file:
            try:
                csv_file.close()
            except Exception:
                pass

    print("\n\nSummary:")
    print(f"  OK samples:   {ok_count}")
    print(f"  Null samples: {null_count}")
    if ok_count > 0:
        print(f"  Flow range (observed): {min_flow:.2f} .. {max_flow:.2f} ml/min")
    else:
        print("  No valid frames observed.")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Live SLF3S-0600F flow sensor visualizer")
    parser.add_argument('--bus', type=int, default=1, help='I2C bus (default: 1)')
    parser.add_argument('--rate', type=float, default=20.0, help='Sampling rate Hz (default: 20)')
    parser.add_argument('--seconds', type=int, default=None, help='Run duration in seconds (default: infinite)')
    parser.add_argument('--csv', type=str, default=None, help='Optional CSV output path')
    args = parser.parse_args()

    return run_scope(args.bus, args.rate, args.seconds, args.csv)


if __name__ == '__main__':
    sys.exit(main())


