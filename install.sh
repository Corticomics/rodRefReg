#!/usr/bin/env bash
#
# Rodent Refreshment Regulator — installer
#
# Target: Raspberry Pi OS Bookworm (64-bit).
# Usage:
#   sudo ./install.sh                 # full install (prompts for sudo if not root)
#   ./install.sh --dry-run            # print actions, change nothing
#   ./install.sh --only 30-python     # run a single module
#   ./install.sh --skip 50-services   # skip a module (repeatable)
#   ./install.sh --branch dev         # override git branch
#   ./install.sh -y                   # non-interactive (assume yes)
#
# Modules run in order from scripts/install/[0-9][0-9]-*.sh.
#
set -Eeuo pipefail

# Bash 4+ required (mapfile, ${var,,}, etc). Bookworm ships 5.2.
if (( BASH_VERSINFO[0] < 4 )); then
  echo "install.sh requires bash >= 4 (found $BASH_VERSION)" >&2
  exit 1
fi

# Resolve absolute paths (works when invoked via symlink or PATH).
SCRIPT_PATH=$(readlink -f -- "${BASH_SOURCE[0]}")
REPO_ROOT=$(dirname -- "$SCRIPT_PATH")
MODULE_DIR="$REPO_ROOT/scripts/install"

# shellcheck source=scripts/install/lib.sh
source "$MODULE_DIR/lib.sh"

# ---- Flags ---------------------------------------------------------------
DRY_RUN=0
YES=0
BRANCH=""
ONLY=""
SKIP=()

usage() {
  awk 'NR>1 && /^#/{ sub(/^# ?/,""); print; next } NR>1{ exit }' "$SCRIPT_PATH"
  exit "${1:-0}"
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --dry-run)    DRY_RUN=1 ;;
    -y|--yes)     YES=1 ;;
    --branch)     BRANCH=${2:?missing value}; shift ;;
    --only)       ONLY=${2:?missing value};  shift ;;
    --skip)       SKIP+=("${2:?missing value}"); shift ;;
    -h|--help)    usage 0 ;;
    *)            err "unknown flag: $1"; usage 1 ;;
  esac
  shift
done
export DRY_RUN YES BRANCH REPO_ROOT MODULE_DIR

# ---- Logging -------------------------------------------------------------
LOG_DIR="$HOME/.local/state/rrr"
mkdir -p "$LOG_DIR"
LOG_FILE="$LOG_DIR/install-$(date +%Y%m%d-%H%M%S).log"
export LOG_FILE

# Mirror stdout/stderr to the log. In rich mode the UI writes styled lines
# straight to /dev/tty, so the tee drops its terminal copy (-> /dev/null) to
# avoid double output and to keep the log free of ANSI escapes. In plain
# mode the tee is the only output path, so it keeps writing to the terminal.
if [[ "${_UI_MODE:-plain}" == "rich" ]]; then
  exec > >(tee -a "$LOG_FILE" >/dev/null) 2>&1
else
  exec > >(tee -a "$LOG_FILE") 2>&1
fi

ui_banner "Rodent Refreshment Regulator" "installer"
[[ "$DRY_RUN" == "1" ]] && ui_warn "DRY-RUN mode: no changes will be applied"

# Ensure the summary always prints — even on die() or signal.
_SUMMARY_SHOWN=0
_print_summary_once() { (( _SUMMARY_SHOWN )) && return 0; _SUMMARY_SHOWN=1; summary; }
trap '_print_summary_once; _lib_cleanup; _ui_cleanup' EXIT

# ---- Module discovery ---------------------------------------------------
mapfile -t MODULES < <(find "$MODULE_DIR" -maxdepth 1 -type f -name '[0-9][0-9]-*.sh' | sort)
[[ ${#MODULES[@]} -gt 0 ]] || die "no install modules found in $MODULE_DIR"

should_run() {
  local name=$1 s
  [[ -n "$ONLY" && "$name" != "$ONLY" ]] && return 1
  for s in "${SKIP[@]:-}"; do [[ "$name" == "$s" ]] && return 1; done
  return 0
}

# ---- Execute -------------------------------------------------------------
for m in "${MODULES[@]}"; do
  name=$(basename "$m" .sh)
  if ! should_run "$name"; then
    info "skip: $name"
    continue
  fi
  section "$name"
  # shellcheck disable=SC1090
  source "$m"
done

# Summary + post-install notes.
_print_summary_once

section "next steps"
info "log out and back in so group membership (i2c, dialout) takes effect"
info "launch: ~/.local/bin/rrr  (or run scripts/runtime/launch.sh)"

# Conditional reboot — only when a module flagged one as needed. Never
# auto-reboots under -y or a non-interactive run (would kill the session).
if (( ${_RRR_REBOOT_REQUIRED:-0} )); then
  _ui_emit "" ""
  for _r in "${_RRR_REBOOT_REASONS[@]:-}"; do
    [[ -n "$_r" ]] && info "reboot needed: $_r"
  done
  if [[ "$DRY_RUN" != "1" && "$YES" != "1" ]] && ui_confirm "reboot now?"; then
    info "rebooting…"
    sudo reboot
  else
    info "a reboot is recommended before use:  sudo reboot"
  fi
fi
