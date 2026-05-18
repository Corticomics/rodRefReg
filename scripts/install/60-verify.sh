# shellcheck shell=bash
# Verify: smoke-test imports and hardware presence. Non-fatal warnings only.

VENV_PY="$RRR_VENV/bin/python3"
[[ -x "$VENV_PY" ]] || { warn "venv python not found; skipping verify"; return 0; }

_check_import() {
  "$VENV_PY" -c "import importlib,sys; importlib.import_module('$1')" 2>/dev/null
}

# Python deps
for m in PyQt5.QtCore pandas numpy RPi.GPIO gpiozero serial slack_sdk smbus2 jsonschema requests SM16relind; do
  verify_soft "python import: $m" -- _check_import "$m"
done

# 16relind CLI tool (separate from the Python module)
verify_soft "cli: 16relind on PATH" -- command -v 16relind

# I2C buses
BUSES=$(detect_i2c_buses)
if [[ -z "$BUSES" ]]; then
  err "no /dev/i2c-* present — I2C did not come up. Try: sudo raspi-config nonint do_i2c 0 && sudo reboot"
  request_reboot "I2C bus not live yet — reboot to bring up /dev/i2c-*"
else
  info "i2c buses: $BUSES"
  if [[ -e /dev/i2c-1 ]]; then
    verify "i2c-1 present (relay HAT bus)" -- true
    if command -v i2cdetect >/dev/null; then
      # Non-fatal: this module only reports, never aborts the install.
      step "scanning i2c-1 (i2cdetect)" -- run sudo i2cdetect -y 1 \
        || warn "i2cdetect -y 1 failed"
    fi
  else
    warn "/dev/i2c-1 NOT present — HAT bus is not live. Reboot, then re-run scripts/runtime/fix_i2c.sh"
    request_reboot "relay HAT bus (/dev/i2c-1) not live — reboot to bring it up"
  fi
fi

# Teensy symlink (advisory)
if [[ -e /dev/teensy_flow ]]; then
  verify "teensy: /dev/teensy_flow present" -- true
else
  info "teensy: /dev/teensy_flow not present (appears on replug)"
fi
