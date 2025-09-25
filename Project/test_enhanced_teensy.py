#!/usr/bin/env python3
"""
Enhanced Teensy Flow Sensor Diagnostic (Benchmark/Debug Suite)
==============================================================

Captures timing, error, and stability metrics for Teensy 4.1 + SLF3x UART bridge.
Implements datasheet timing checks per Sensirion SLF3x (reset 25ms, warm-up ~50–60ms) [SLF3x Datasheet].

Reference: Sensirion SLF3S-1300F Datasheet (§2.2 Timing Specifications, Start/Stop/Reset) [1].

[1] https://sensirion.com/media/documents/6971528D/63625D22/Sensirion_Datasheet_SLF3S-1300F.pdf
"""

import argparse
import csv
import json
import os
import time
import sys
from datetime import datetime
from pathlib import Path

try:
    import serial
except Exception as e:
    print(f"pyserial missing: {e}")
    sys.exit(1)


def _now_ms():
    return int(time.time() * 1000)


def _write_jsonl(fp, obj):
    fp.write(json.dumps(obj, ensure_ascii=False) + "\n")
    fp.flush()


def open_serial(port: str, baud: int, timeout: float) -> serial.Serial:
    ser = serial.Serial(port, baud, timeout=timeout)
    time.sleep(2.5)  # Teensy CDC re-enumeration guard
    return ser


def flush_input(ser: serial.Serial):
    try:
        ser.reset_input_buffer()
    except Exception:
        pass


def send_cmd(ser: serial.Serial, cmd: dict, logf=None, tag: str = "cmd"):
    try:
        payload = json.dumps(cmd) + "\n"
        # Flush to avoid stale data before request/response
        flush_input(ser)
        t0 = _now_ms()
        ser.write(payload.encode("utf-8"))
        ser.flush()
        if logf:
            _write_jsonl(logf, {"t": t0, tag: cmd})
        return t0
    except Exception as e:
        if logf:
            _write_jsonl(logf, {"t": _now_ms(), "error": f"send_cmd failed: {e}", "cmd": cmd})
        raise


def readline_split(ser: serial.Serial):
    """Read one line and split if multiple JSONs concatenated."""
    raw = ser.readline().decode("utf-8", errors="ignore").strip()
    if not raw:
        return []
    # Split on CRLF boundaries if multiple frames arrived at once
    parts = [p for p in raw.split("\r\n") if p]
    return parts if parts else [raw]


def collect_stream(ser: serial.Serial, duration_s: float, logf, stats, expected_rate_hz: float):
    start = time.time()
    last_meas_ts = None
    while time.time() - start < duration_s:
        if ser.in_waiting:
            lines = readline_split(ser)
            for line in lines:
                ts = _now_ms()
                try:
                    obj = json.loads(line)
                    t = obj.get("type")
                    _write_jsonl(logf, {"t": ts, "rx": obj})
                    stats["total"] += 1
                    if t == "measurement":
                        stats["meas"] += 1
                        if last_meas_ts is not None:
                            dt = (ts - last_meas_ts) / 1000.0
                            stats["periods"].append(dt)
                        last_meas_ts = ts
                        stats["flows"].append(float(obj.get("flow", 0.0)))
                        stats["temps"].append(float(obj.get("temp", 0.0)))
                    elif t == "error":
                        stats["errors"] += 1
                        stats["error_msgs"].append(obj.get("error", ""))
                    elif t == "status":
                        stats["status"] += 1
                    else:
                        stats["unknown"] += 1
                except json.JSONDecodeError:
                    stats["raw"] += 1
                    _write_jsonl(logf, {"t": ts, "raw": line})
        else:
            time.sleep(0.005)


def summarize(stats):
    out = {}
    out["frames_total"] = stats["total"]
    out["frames_meas"] = stats["meas"]
    out["frames_errors"] = stats["errors"]
    out["frames_status"] = stats["status"]
    out["frames_unknown"] = stats["unknown"]
    out["frames_raw"] = stats["raw"]
    if stats["periods"]:
        avg_period = sum(stats["periods"]) / len(stats["periods"])
        out["avg_period_s"] = avg_period
        out["effective_rate_hz"] = 1.0 / avg_period if avg_period > 0 else 0.0
    if stats["temps"]:
        out["temp_avg_c"] = sum(stats["temps"]) / len(stats["temps"])
        out["temp_min_c"] = min(stats["temps"]) 
        out["temp_max_c"] = max(stats["temps"])
    if stats["flows"]:
        out["flow_avg_ml_min"] = sum(stats["flows"]) / len(stats["flows"])
        out["flow_min_ml_min"] = min(stats["flows"]) 
        out["flow_max_ml_min"] = max(stats["flows"])
    out["distinct_error_msgs"] = sorted(set(stats["error_msgs"]))
    return out


def run_benchmark(args):
    ts_str = datetime.now().strftime("%Y%m%d_%H%M%S")
    outdir = Path(args.outdir)
    outdir.mkdir(parents=True, exist_ok=True)
    jsonl_path = outdir / f"teensy_diag_{ts_str}.jsonl"
    csv_path = outdir / f"teensy_diag_{ts_str}.csv"

    with open(jsonl_path, "w", encoding="utf-8") as logf:
        print("🔬 Enhanced Teensy Flow Sensor Diagnostic")
        print("=" * 50)
        print(f"Port: {args.port}")
        print(f"Duration: {args.duration}s, Rate: {args.rate} Hz")
        print(f"Logs: {jsonl_path}")

        ser = open_serial(args.port, 115200, timeout=1.0)
        try:
            # Phase 0: optional reset (datasheet: 25ms)
            if args.reset_first:
                send_cmd(ser, {"cmd": "reset"}, logf, tag="reset")
                time.sleep(0.03)

            # Phase 1: ping (latency)
            t0 = send_cmd(ser, {"cmd": "ping"}, logf)
            ping_line = ser.readline().decode("utf-8", errors="ignore").strip()
            t1 = _now_ms()
            ok_pong = False
            if ping_line:
                try:
                    pong = json.loads(ping_line)
                    ok_pong = pong.get("type") == "pong"
                    _write_jsonl(logf, {"t": t1, "rx": pong, "latency_ms": t1 - t0})
                except json.JSONDecodeError:
                    _write_jsonl(logf, {"t": t1, "raw": ping_line, "latency_ms": t1 - t0})
            print(f"📡 Ping: {'OK' if ok_pong else 'Unexpected'} (latency ~{t1 - t0} ms)")

            # Phase 2: start streaming at requested rate
            send_cmd(ser, {"cmd": "start", "rate": args.rate}, logf)
            # Datasheet warm-up guidance (~50–60ms to within spec). We measure until 3 frames.
            warm_start = _now_ms()
            meas_seen = 0
            first_ts = None
            while (meas_seen < 3) and ( (_now_ms() - warm_start) < 2000 ):
                if ser.in_waiting:
                    for line in readline_split(ser):
                        ts = _now_ms()
                        try:
                            obj = json.loads(line)
                            _write_jsonl(logf, {"t": ts, "rx": obj})
                            if obj.get("type") == "measurement":
                                meas_seen += 1
                                if first_ts is None:
                                    first_ts = ts
                        except json.JSONDecodeError:
                            _write_jsonl(logf, {"t": ts, "raw": line})
                else:
                    time.sleep(0.005)
            if meas_seen >= 1:
                print(f"⏱ First measurement after ~{(first_ts - warm_start) if first_ts else '?'} ms")
            else:
                print("⏱ No measurement within 2s warm-up window")

            # Phase 3: continuous collection
            stats = {"total": 0, "meas": 0, "errors": 0, "status": 0, "unknown": 0, "raw": 0,
                     "periods": [], "flows": [], "temps": [], "error_msgs": []}
            print("\n🌊 Collecting stream…")
            collect_stream(ser, args.duration, logf, stats, args.rate)
            summary = summarize(stats)

            # Phase 4: optional reconnect simulation (close/reopen)
            if args.reconnect:
                print("\n🔁 Simulating reconnect (close/reopen)")
                try:
                    ser.close()
                except Exception:
                    pass
                ser = open_serial(args.port, 115200, timeout=1.0)
                send_cmd(ser, {"cmd": "start", "rate": args.rate}, logf)
                collect_stream(ser, 3.0, logf, stats, args.rate)
                summary = summarize(stats)

            # Phase 5: stop
            send_cmd(ser, {"cmd": "stop"}, logf)
            time.sleep(0.2)

            # Print summary
            print("\n📊 Summary")
            for k, v in summary.items():
                print(f"- {k}: {v}")

            # Also output CSV snapshot of summary
            with open(csv_path, "w", newline="", encoding="utf-8") as cf:
                w = csv.writer(cf)
                w.writerow(["metric", "value"])
                for k, v in summary.items():
                    w.writerow([k, v])

            print(f"\n🗂️  Saved logs to: {jsonl_path} and {csv_path}")
            return summary.get("frames_meas", 0) > 0
        finally:
            try:
                ser.close()
            except Exception:
                pass


def main():
    p = argparse.ArgumentParser(description="Enhanced Teensy Flow Sensor Diagnostic")
    p.add_argument("--port", default="/dev/ttyACM0")
    p.add_argument("--duration", type=float, default=10.0)
    p.add_argument("--rate", type=float, default=1.0, help="Requested streaming rate (Hz)")
    p.add_argument("--outdir", default="diagnostics")
    p.add_argument("--reset-first", action="store_true", help="Send reset before starting stream (datasheet: 25ms)")
    p.add_argument("--reconnect", action="store_true", help="Simulate close/reopen and verify recovery")
    args = p.parse_args()

    ok = run_benchmark(args)
    print(f"\n{'='*50}")
    if ok:
        print("🎉 Enhanced test PASSED - streaming OK")
        print("   Next: run RRR schedule and verify deliveries.")
    else:
        print("❌ Enhanced test FAILED - no measurements received")
        print("   Check Teensy firmware, wiring, and I2C reset/start sequence.")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
