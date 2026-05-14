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
for m in PyQt5.QtCore pandas numpy RPi.GPIO gpiozero serial slack_sdk smbus2 jsonschema requests; do
  check_import "$m"
done

# I2C buses
BUSES=$(detect_i2c_buses)
if [[ -n "$BUSES" ]]; then
  info "i2c buses: $BUSES"
  for b in $BUSES; do
    if command -v i2cdetect >/dev/null; then
      run sudo i2cdetect -y "$b" || warn "i2cdetect -y $b failed"
    fi
  done
else
  warn "no i2c buses present (reboot may be required after first install)"
fi

# Teensy symlink (advisory)
if [[ -e /dev/teensy_flow ]]; then
  info "teensy: /dev/teensy_flow present"
else
  info "teensy: /dev/teensy_flow not present (appears on replug)"
fi
