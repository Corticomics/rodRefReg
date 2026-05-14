# shellcheck shell=bash
# Shared helpers for install modules. Sourced; never executed directly.
#
# Exported by install.sh: DRY_RUN, LOG_FILE, REPO_ROOT, MODULE_DIR.

set -Eeuo pipefail

if [[ -z "${_RRR_LIB_LOADED:-}" ]]; then
_RRR_LIB_LOADED=1

# ---- ANSI ----------------------------------------------------------------
if [[ -t 2 ]]; then
  _C_RED=$'\e[31m'; _C_YEL=$'\e[33m'; _C_GRN=$'\e[32m'; _C_DIM=$'\e[2m'; _C_RST=$'\e[0m'
else
  _C_RED=; _C_YEL=; _C_GRN=; _C_DIM=; _C_RST=
fi

# ---- Logging -------------------------------------------------------------
_ts() { date +'%Y-%m-%dT%H:%M:%S%z'; }
log()  { printf '%s %s\n'        "$(_ts)" "$*" >&2; }
info() { printf '%s %sINFO%s  %s\n' "$(_ts)" "$_C_GRN" "$_C_RST" "$*" >&2; }
warn() { printf '%s %sWARN%s  %s\n' "$(_ts)" "$_C_YEL" "$_C_RST" "$*" >&2; }
err()  { printf '%s %sERROR%s %s\n' "$(_ts)" "$_C_RED" "$_C_RST" "$*" >&2; }
die()  { err "$*"; exit 1; }

# Section banner; modules call once at entry.
section() { printf '\n%s== %s ==%s\n' "$_C_DIM" "$*" "$_C_RST" >&2; }

# ---- Dry-run aware command runner ---------------------------------------
# Usage: run cmd args...
# Honors DRY_RUN=1 by printing instead of executing.
run() {
  if [[ "${DRY_RUN:-0}" == "1" ]]; then
    printf '%s[dry-run]%s %s\n' "$_C_DIM" "$_C_RST" "$(_quote "$@")" >&2
    return 0
  fi
  "$@"
}

# run_sh "shell snippet"  — for pipelines/redirection. Dry-run aware.
run_sh() {
  if [[ "${DRY_RUN:-0}" == "1" ]]; then
    printf '%s[dry-run]%s sh -c %q\n' "$_C_DIM" "$_C_RST" "$1" >&2
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
    printf '%s[dry-run]%s would write %s (mode=%s owner=%s)\n' \
      "$_C_DIM" "$_C_RST" "$dest" "$mode" "$owner" >&2
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
}

# Require a command on PATH.
require_cmd() { command -v "$1" >/dev/null || die "required command not found: $1"; }

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
trap _lib_cleanup EXIT

fi # _RRR_LIB_LOADED
