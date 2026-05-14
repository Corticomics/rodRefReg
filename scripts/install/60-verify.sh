# shellcheck shell=bash
# Verify: smoke-test imports and hardware presence. Non-fatal warnings only.

VENV_PY="$REPO_ROOT/.venv/bin/python3"
[[ -x "$VENV_PY" ]] || { warn "venv python not found; skipping verify"; return 0; }

check_import() {
  local mod=$1
  if "$VENV_PY" -c "import importlib,sys; importlib.import_module('$mod')" 2>/dev/null; then
    info "import ok: $mod"
  else
    warn "import FAILED: $mod"
  fi
}

# Python deps
for m in PyQt5.QtCore pandas numpy RPi.GPIO gpiozero serial slack_sdk smbus2 jsonschema requests SM16relind; do
  check_import "$m"
done

# 16relind CLI tool (separate from the Python module)
if command -v 16relind >/dev/null; then
  info "cli ok: 16relind ($(command -v 16relind))"
else
  warn "cli MISSING: 16relind"
fi

# I2C buses
BUSES=$(detect_i2c_buses)
if [[ -z "$BUSES" ]]; then
  err "no /dev/i2c-* present — I2C did not come up. Try: sudo raspi-config nonint do_i2c 0 && sudo reboot"
else
  info "i2c buses: $BUSES"
  # Identify the user-GPIO bus (the one HATs sit on). On Pi 4 it's bus 1;
  # on Pi 5 it's bus 1 once dtparam=i2c_arm=on is live. We treat the
  # presence of /dev/i2c-1 as the canary for "I2C is truly enabled."
  if [[ -e /dev/i2c-1 ]]; then
    info "i2c-1 present (relay HAT bus)"
    if command -v i2cdetect >/dev/null; then
      run sudo i2cdetect -y 1 || warn "i2cdetect -y 1 failed"
    fi
  else
    warn "/dev/i2c-1 NOT present — HAT bus is not live. Reboot, then re-run scripts/runtime/fix_i2c.sh"
  fi
fi

# Teensy symlink (advisory)
if [[ -e /dev/teensy_flow ]]; then
  info "teensy: /dev/teensy_flow present"
else
  info "teensy: /dev/teensy_flow not present (appears on replug)"
fi
