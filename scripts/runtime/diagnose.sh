#!/usr/bin/env bash
# RRR diagnostic snapshot. Safe to run any time.
set -Eeuo pipefail

REPO=${RRR_REPO:-$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/../.." && pwd)}
VENV="$REPO/.venv"

hr() { printf '\n--- %s ---\n' "$*"; }

hr "OS"
[[ -r /etc/os-release ]] && cat /etc/os-release || echo "no /etc/os-release"

hr "Pi model"
[[ -r /proc/device-tree/model ]] && tr -d '\0' </proc/device-tree/model && echo

hr "Python"
"$VENV/bin/python3" --version 2>/dev/null || echo "venv python missing at $VENV"

hr "Imports"
"$VENV/bin/python3" - <<'PY' 2>&1 || true
import importlib
for m in ("PyQt5.QtCore","pandas","numpy","RPi.GPIO","gpiozero",
         "serial","slack_sdk","smbus2","jsonschema","requests"):
    try:
        importlib.import_module(m); print(f"  ok   {m}")
    except Exception as e:
        print(f"  FAIL {m}: {e}")
PY

hr "I2C buses"
ls /dev/i2c-* 2>/dev/null || echo "none"

hr "i2cdetect"
for b in /dev/i2c-*; do
  [[ -e "$b" ]] || continue
  echo "bus ${b##*/i2c-}:"
  sudo i2cdetect -y "${b##*/i2c-}" 2>&1 || true
done

hr "Teensy"
ls -l /dev/teensy_flow 2>/dev/null || echo "no /dev/teensy_flow"

hr "Groups"
id

hr "Recent journal (user rrr.service)"
journalctl --user -u rrr.service -n 30 --no-pager 2>/dev/null || echo "no user unit logs"
