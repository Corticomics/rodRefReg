# shellcheck shell=bash
# Shared helpers for install modules. Sourced; never executed directly.
#
# Exported by install.sh: DRY_RUN, LOG_FILE, REPO_ROOT, MODULE_DIR.

set -Eeuo pipefail

if [[ -z "${_RRR_LIB_LOADED:-}" ]]; then
_RRR_LIB_LOADED=1

# Load the UI renderer (sources ui.theme.sh in turn). All user-visible
# output is routed through ui.sh so modules never touch ANSI directly.
# shellcheck source=ui.sh
source "${BASH_SOURCE[0]%/*}/ui.sh"

# ---- Logging shims -------------------------------------------------------
# Back-compat helpers. Existing modules call info/warn/err/die/section; we
# keep those names but route through the UI renderer.
_ts() { date +'%Y-%m-%dT%H:%M:%S%z'; }
log()  { ui_info "$*"; }
info() { ui_info "$*"; }
warn() { ui_warn "$*"; }
err()  { ui_err  "$*"; }
die()  { ui_err  "$*"; exit 1; }

# section() is provided by ui.sh.

# ---- Dry-run aware command runner ---------------------------------------
# Usage: run cmd args...
# Honors DRY_RUN=1 by printing instead of executing.
run() {
  if [[ "${DRY_RUN:-0}" == "1" ]]; then
    printf '[dry-run] %s\n' "$(_quote "$@")" >&2
    return 0
  fi
  "$@"
}

# run_sh "shell snippet"  — for pipelines/redirection. Dry-run aware.
run_sh() {
  if [[ "${DRY_RUN:-0}" == "1" ]]; then
    printf '[dry-run] sh -c %q\n' "$1" >&2
    return 0
  fi
  bash -c "$1"
}

_quote() { local s; for s in "$@"; do printf '%q ' "$s"; done; }

# ---- Idempotent helpers --------------------------------------------------

# append_line_if_missing <file> <line>   (needs sudo for system files; caller decides)
append_line_if_missing() {
  local file=$1 line=$2
  if [[ -f "$file" ]] && grep -qxF -- "$line" "$file"; then
    return 0
  fi
  run_sh "printf '%s\n' $(printf %q "$line") | sudo tee -a $(printf %q "$file") >/dev/null"
}

# write_file_atomic <dest> <mode> <owner:group|-> <<<'content'
# Reads stdin; only writes if content differs (idempotent).
write_file_atomic() {
  local dest=$1 mode=$2 owner=$3 tmp
  tmp=$(mktemp)
  cat >"$tmp"
  if [[ -f "$dest" ]] && cmp -s "$tmp" "$dest"; then
    rm -f "$tmp"
    info "unchanged: $dest"
    return 0
  fi
  if [[ "${DRY_RUN:-0}" == "1" ]]; then
    info "[dry-run] would write $dest (mode=$mode owner=$owner)"
    rm -f "$tmp"
    return 0
  fi
  local sudo_cmd=""
  [[ -w "$(dirname "$dest")" ]] || sudo_cmd="sudo"
  $sudo_cmd install -m "$mode" "$tmp" "$dest"
  [[ "$owner" != "-" ]] && $sudo_cmd chown "$owner" "$dest"
  rm -f "$tmp"
  info "wrote: $dest"
}

# Add user to group if not already a member.
ensure_user_in_group() {
  local user=$1 group=$2
  if id -nG "$user" | tr ' ' '\n' | grep -qxF -- "$group"; then
    return 0
  fi
  getent group "$group" >/dev/null || run sudo groupadd "$group"
  run sudo usermod -aG "$group" "$user"
  info "added $user to group $group (re-login required to take effect)"
  request_reboot "group membership changed — re-login or reboot to apply"
}

# Require a command on PATH.
require_cmd() { command -v "$1" >/dev/null || die "required command not found: $1"; }

# ---- Reboot coordination -------------------------------------------------
# Modules call request_reboot when a change only takes effect after a
# reboot (or re-login). install.sh acts on the flag after the summary.
_RRR_REBOOT_REQUIRED=0
_RRR_REBOOT_REASONS=()
request_reboot() {
  local reason=$1 r
  _RRR_REBOOT_REQUIRED=1
  for r in "${_RRR_REBOOT_REASONS[@]:-}"; do
    [[ "$r" == "$reason" ]] && return 0      # dedup identical reasons
  done
  _RRR_REBOOT_REASONS+=("$reason")
}

# Confirm prompt; auto-yes if YES=1.
confirm() {
  local prompt=${1:-"Continue?"}
  [[ "${YES:-0}" == "1" ]] && return 0
  read -r -p "$prompt [y/N] " ans
  [[ "$ans" =~ ^[Yy]$ ]]
}

# Detect available I2C buses (prints numeric bus IDs, space-separated).
detect_i2c_buses() {
  local b out=""
  for b in /dev/i2c-*; do
    [[ -e "$b" ]] || continue
    out+="${b##*/i2c-} "
  done
  printf '%s\n' "${out% }"
}

# Resolve Bookworm firmware path (Bookworm-only target, but be defensive).
boot_firmware_dir() {
  if [[ -d /boot/firmware ]]; then echo /boot/firmware
  elif [[ -d /boot ]];          then echo /boot
  else die "no /boot directory found"
  fi
}

# Cleanup hook for tmp dirs created with mktemp_d.
_RRR_TMPDIRS=()
mktemp_d() { local d; d=$(mktemp -d); _RRR_TMPDIRS+=("$d"); echo "$d"; }
_lib_cleanup() {
  local d
  for d in "${_RRR_TMPDIRS[@]:-}"; do
    [[ -n "$d" && -d "$d" ]] && rm -rf "$d"
  done
  return 0
}
# Chain alongside the UI EXIT trap (ui.sh installs _ui_cleanup on EXIT).
trap '_lib_cleanup; _ui_cleanup' EXIT

fi # _RRR_LIB_LOADED
