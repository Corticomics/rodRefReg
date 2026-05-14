# shellcheck shell=bash
# Preflight: OS, arch, disk, network. Bookworm-only target.

# OS check ---------------------------------------------------------------
if [[ ! -r /etc/os-release ]]; then
  die "/etc/os-release missing; unsupported OS"
fi
# shellcheck disable=SC1091
. /etc/os-release
if [[ "${ID:-}" != "debian" && "${ID:-}" != "raspbian" ]]; then
  die "unsupported distro: ${ID:-unknown} (need Debian/Raspbian Bookworm)"
fi
if [[ "${VERSION_CODENAME:-}" != "bookworm" ]]; then
  die "unsupported release: ${VERSION_CODENAME:-unknown} (need bookworm)"
fi
info "os: ${PRETTY_NAME:-debian bookworm}"

# Arch -------------------------------------------------------------------
ARCH=$(uname -m)
case "$ARCH" in
  aarch64|arm64) info "arch: $ARCH" ;;
  armv7l)        warn "arch: $ARCH (32-bit; 64-bit recommended)" ;;
  *)             warn "arch: $ARCH (not a Raspberry Pi; hardware features will be unavailable)" ;;
esac

# Pi hardware (advisory only) -------------------------------------------
if [[ -r /proc/device-tree/model ]]; then
  PI_MODEL=$(tr -d '\0' </proc/device-tree/model)
  info "model: $PI_MODEL"
elif grep -qi 'raspberry pi' /proc/cpuinfo 2>/dev/null; then
  info "model: Raspberry Pi (cpuinfo)"
else
  warn "not a Raspberry Pi: GPIO/I2C features will not function"
fi

# Disk space (need ~1.5 GB) ---------------------------------------------
AVAIL_KB=$(df -P "$HOME" | awk 'NR==2 {print $4}')
AVAIL_MB=$((AVAIL_KB / 1024))
if (( AVAIL_MB < 1500 )); then
  die "insufficient disk: need ≥1500 MB free in \$HOME, have ${AVAIL_MB} MB"
fi
info "disk: ${AVAIL_MB} MB free"

# Network ----------------------------------------------------------------
if ! curl --silent --fail --head --max-time 5 https://github.com >/dev/null; then
  die "cannot reach https://github.com (check network/proxy)"
fi
info "network: github.com reachable"

# Sudo -------------------------------------------------------------------
if [[ "$(id -u)" -eq 0 ]]; then
  warn "running as root; user-scoped files will be created for \$SUDO_USER if set"
else
  if ! sudo -n true 2>/dev/null; then
    info "sudo password may be required during install"
    run sudo -v
  fi
fi
