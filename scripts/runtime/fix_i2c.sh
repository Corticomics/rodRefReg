#!/usr/bin/env bash
# Re-apply I2C configuration. Idempotent; safe to re-run.
set -Eeuo pipefail

BOOT_DIR=/boot/firmware
[[ -d "$BOOT_DIR" ]] || BOOT_DIR=/boot
CONFIG="$BOOT_DIR/config.txt"

if [[ -f "$CONFIG" ]] && ! grep -qx 'dtparam=i2c_arm=on' "$CONFIG"; then
  echo "enabling i2c in $CONFIG"
  echo 'dtparam=i2c_arm=on' | sudo tee -a "$CONFIG" >/dev/null
  echo "reboot required for change to take effect"
fi

sudo modprobe i2c-dev || true
if ! grep -qx 'i2c-dev' /etc/modules; then
  echo 'i2c-dev' | sudo tee -a /etc/modules >/dev/null
fi

getent group i2c >/dev/null || sudo groupadd i2c
id -nG "$USER" | tr ' ' '\n' | grep -qx i2c || sudo usermod -aG i2c "$USER"

echo
echo "i2c buses:"
ls /dev/i2c-* 2>/dev/null || echo "  none (reboot may be needed)"
for b in /dev/i2c-*; do
  [[ -e "$b" ]] || continue
  echo "scanning ${b##*/i2c-}:"
  sudo i2cdetect -y "${b##*/i2c-}" || true
done
