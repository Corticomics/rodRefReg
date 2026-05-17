# shellcheck shell=bash
# Preflight: OS, arch, disk, network. Bookworm-only target.

# OS check ---------------------------------------------------------------
if [[ ! -r /etc/os-release ]]; then
  die "/etc/os-release missing; unsupported OS"
fi
# shellcheck disable=SC1091
. /etc/os-release

_check_os() {
  [[ "${ID:-}" == "debian" || "${ID:-}" == "raspbian" ]] || return 1
  [[ "${VERSION_CODENAME:-}" == "bookworm" ]] || return 1
}
verify "OS is Debian/Raspbian bookworm (${PRETTY_NAME:-unknown})" -- _check_os

# Arch -------------------------------------------------------------------
ARCH=$(uname -m)
case "$ARCH" in
  aarch64|arm64) verify "arch supported: $ARCH" -- true ;;
  armv7l)        verify_soft "arch: $ARCH (32-bit; 64-bit recommended)" -- false ;;
  *)             verify_soft "arch: $ARCH (not a Pi; hardware features unavailable)" -- false ;;
esac

# Pi hardware (advisory only) -------------------------------------------
if [[ -r /proc/device-tree/model ]]; then
  PI_MODEL=$(tr -d '\0' </proc/device-tree/model)
  verify "model: $PI_MODEL" -- true
elif grep -qi 'raspberry pi' /proc/cpuinfo 2>/dev/null; then
  verify "model: Raspberry Pi (cpuinfo)" -- true
else
  verify_soft "not a Raspberry Pi: GPIO/I2C features will not function" -- false
fi

# Disk space (need ~1.5 GB) ---------------------------------------------
AVAIL_KB=$(df -P "$HOME" | awk 'NR==2 {print $4}')
AVAIL_MB=$((AVAIL_KB / 1024))
if (( AVAIL_MB < 1500 )); then
  die "insufficient disk: need ≥1500 MB free in \$HOME, have ${AVAIL_MB} MB"
fi
verify "disk: ${AVAIL_MB} MB free in \$HOME" -- true

# Network ----------------------------------------------------------------
step "checking network reachability (github.com)" -- \
  curl --silent --fail --head --max-time 5 https://github.com \
  || die "cannot reach https://github.com (check network/proxy)"

# Sudo -------------------------------------------------------------------
if [[ "$(id -u)" -eq 0 ]]; then
  warn "running as root; user-scoped files will be created for \$SUDO_USER if set"
else
  if ! sudo -n true 2>/dev/null; then
    info "sudo password may be required during install"
    run sudo -v
  fi
fi
