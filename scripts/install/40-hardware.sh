# shellcheck shell=bash
# Hardware: I2C enable, Sequent Microsystems 16-relay HAT driver, udev rules.

BOOT_DIR=$(boot_firmware_dir)            # /boot/firmware on Bookworm
CONFIG_TXT="$BOOT_DIR/config.txt"
CMDLINE_TXT="$BOOT_DIR/cmdline.txt"
TARGET_USER=${SUDO_USER:-$USER}

# ---- I2C enable --------------------------------------------------------
# Prefer raspi-config: it is the canonical, Pi-aware tool. It edits
# /boot/firmware/config.txt, unblacklists i2c-bcm2708, appends i2c-dev to
# /etc/modules, AND — crucially on Pi 5 — applies `dtparam i2c_arm=on` live
# so /dev/i2c-* appears without a reboot. Manual fallbacks tend to miss the
# last step and require the user to re-run `sudo raspi-config` by hand.
if command -v raspi-config >/dev/null; then
  step "enabling I2C via raspi-config" -- run sudo raspi-config nonint do_i2c 0
else
  warn "raspi-config not present; falling back to manual config (reboot likely required)"
  if [[ -f "$CONFIG_TXT" ]]; then
    append_line_if_missing "$CONFIG_TXT" "dtparam=i2c_arm=on"
  fi
  append_line_if_missing /etc/modules "i2c-dev"
  run sudo modprobe i2c-dev || warn "modprobe i2c-dev failed"
  # Try to apply the device-tree param live; the dtparam tool ships with
  # raspberrypi-sys-mods on Pi OS. Failures here just mean a reboot is needed.
  command -v dtparam >/dev/null && run sudo dtparam i2c_arm=on || true
  request_reboot "I2C enabled via manual config — reboot to bring up /dev/i2c-*"
fi

# ---- Groups ------------------------------------------------------------
ensure_user_in_group "$TARGET_USER" i2c
ensure_user_in_group "$TARGET_USER" gpio
ensure_user_in_group "$TARGET_USER" dialout

# ---- 16-relay HAT driver (Sequent Microsystems) -----------------------
# Use a tracked clone under REPO_ROOT/vendor so re-runs are fast and clean.
VENDOR_DIR="$REPO_ROOT/vendor/16relind-rpi"
REPO_URL="https://github.com/SequentMicrosystems/16relind-rpi.git"
mkdir -p "$REPO_ROOT/vendor"

_update_vendor() {
  run git -C "$VENDOR_DIR" fetch --depth 1 origin
  run git -C "$VENDOR_DIR" reset --hard origin/HEAD
}
if [[ -d "$VENDOR_DIR/.git" ]]; then
  step "updating 16relind-rpi vendor checkout" -- _update_vendor
else
  step "cloning 16relind-rpi (Sequent Microsystems)" -- \
    with_retry 3 3 -- run git clone --depth 1 "$REPO_URL" "$VENDOR_DIR"
fi

if [[ -f "$VENDOR_DIR/Makefile" ]]; then
  step "building & installing 16relind driver" -- run sudo make -C "$VENDOR_DIR" install
fi

if command -v 16relind >/dev/null; then
  info "16relind CLI: $(command -v 16relind)"
else
  warn "16relind not on PATH after install"
fi

# Install the SM16relind Python wrapper into the project venv.
# Upstream ships it under python/ with a setup.py (modern build).
SM_PY_DIR="$VENDOR_DIR/python"
VENV_PIP="$RRR_VENV/bin/pip"
if [[ -d "$SM_PY_DIR" && -x "$VENV_PIP" ]]; then
  if [[ -f "$SM_PY_DIR/pyproject.toml" || -f "$SM_PY_DIR/setup.py" ]]; then
    step "installing SM16relind python wrapper into venv" -- \
      run "$VENV_PIP" install --disable-pip-version-check -q "$SM_PY_DIR"
  else
    warn "SM16relind python source dir present but no setup.py/pyproject.toml"
  fi
elif [[ ! -d "$SM_PY_DIR" ]]; then
  warn "upstream python/ dir missing at $SM_PY_DIR — SM16relind module not installed"
fi

# ---- Teensy udev rule (stable /dev/teensy_flow symlink) ----------------
UDEV_RULE=/etc/udev/rules.d/99-rrr-teensy.rules
write_file_atomic "$UDEV_RULE" 0644 root:root <<'EOF'
# RRR — Teensy 4.x (Teensyduino Serial) stable symlink
SUBSYSTEM=="tty", ATTRS{idVendor}=="16c0", ATTRS{idProduct}=="0483", \
  SYMLINK+="teensy_flow", MODE="0660", GROUP="dialout"
EOF

step "reloading udev rules" -- run sudo udevadm control --reload-rules
step "triggering udev (tty subsystem)" -- run sudo udevadm trigger --subsystem-match=tty

# ---- Console / display blanking (lab use, optional) -------------------
# Append once; users can revert by editing cmdline.txt.
if [[ -f "$CMDLINE_TXT" ]] && ! grep -qw 'consoleblank=0' "$CMDLINE_TXT"; then
  run sudo cp -n "$CMDLINE_TXT" "${CMDLINE_TXT}.rrr-bak"
  run_sh "sudo sed -i 's/\$/ consoleblank=0/' $(printf %q "$CMDLINE_TXT")"
  info "added consoleblank=0 to $CMDLINE_TXT (backup: ${CMDLINE_TXT}.rrr-bak)"
  request_reboot "kernel cmdline changed (consoleblank=0) — reboot to apply"
fi
