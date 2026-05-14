# shellcheck shell=bash
# apt: system packages. Single source of truth for OS-level deps.
#
# We install Python GUI/scientific libs from apt (not pip) and expose them
# to the venv via --system-site-packages. This matches PEP 668 on Bookworm
# and avoids the long compile times pip would incur on a Pi.

APT_PACKAGES=(
  # Build / VCS / utility
  git curl ca-certificates build-essential
  # Python runtime & venv
  python3 python3-pip python3-venv python3-dev
  # Hardware / I2C / GPIO
  i2c-tools python3-smbus python3-rpi.gpio python3-gpiozero python3-lgpio
  # Scientific / GUI (apt builds; venv inherits via --system-site-packages)
  python3-pyqt5 python3-pandas python3-numpy
  # Serial (Teensy)
  python3-serial
  # Systemd user lingering (for headless autostart)
  systemd
)

export DEBIAN_FRONTEND=noninteractive
run sudo apt-get update -y
run sudo apt-get install -y --no-install-recommends "${APT_PACKAGES[@]}"
