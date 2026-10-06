#!/usr/bin/env bash
#
# Smoke-test the installer without mutating the system.
#
#   - bash -n on every installer script
#   - shellcheck (if available) at warning level
#   - install.sh --help renders
#   - install.sh --dry-run executes end-to-end with no errors
#   - sanity checks on the log file
#   - the dry run leaves what a real install writes as it found it
#
# Safe to run on a fresh Pi or on one where RRR is installed. Exits non-zero
# on any failure.
#
set -Eeuo pipefail

REPO_ROOT=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/../.." && pwd)
cd "$REPO_ROOT"

PASS=0; FAIL=0
ok()   { printf '  \e[32mPASS\e[0m  %s\n' "$*"; PASS=$((PASS+1)); }
bad()  { printf '  \e[31mFAIL\e[0m  %s\n' "$*"; FAIL=$((FAIL+1)); }
hdr()  { printf '\n== %s ==\n' "$*"; }

SCRIPTS=( install.sh scripts/install/*.sh scripts/runtime/*.sh )

hdr "bash -n syntax"
for f in "${SCRIPTS[@]}"; do
  if bash -n "$f" 2>/dev/null; then ok "$f"; else bad "$f"; fi
done

hdr "shellcheck"
if command -v shellcheck >/dev/null; then
  if shellcheck -S warning -x "${SCRIPTS[@]}"; then
    ok "shellcheck -S warning"
  else
    bad "shellcheck -S warning (see above)"
  fi
else
  printf '  \e[33mSKIP\e[0m  shellcheck not installed\n'
fi

hdr "install.sh --help"
if ./install.sh --help >/dev/null 2>&1; then ok "help renders"; else bad "help failed"; fi

hdr "install.sh --dry-run"
# What a real install writes (the release tree and the venv come from
# layout.sh). On a Pi that was installed before, these exist already, so the
# dry run is held to leaving each one as it found it.
# shellcheck source=scripts/install/layout.sh
source scripts/install/layout.sh || true
WATCHED=( "$RRR_RELEASES" "$RRR_CURRENT" "$RRR_VENV" "$REPO_ROOT/vendor" "$REPO_ROOT/dist"
          /etc/udev/rules.d/99-rrr-teensy.rules )
# A path's state: absent, a link's target, a file's checksum, or the list of
# a directory's entries. Python caches are left out: the import checks may
# write them into the venv.
state_of() {
  if [[ -L "$1" ]]; then readlink -- "$1"
  elif [[ -f "$1" ]]; then cksum <"$1" 2>/dev/null || echo unreadable
  elif [[ -d "$1" ]]; then
    { find "$1" -not -path '*/__pycache__*' 2>/dev/null || true; } | LC_ALL=C sort | cksum
  else echo absent
  fi
}
BEFORE=()
for p in "${WATCHED[@]}"; do BEFORE+=("$(state_of "$p")"); done
# A file or link rewritten in place inside a watched directory keeps the
# listing the same, but is newer than this mark.
MARK=$(mktemp)
DRY_LOG=$(mktemp)
if ./install.sh --dry-run -y >"$DRY_LOG" 2>&1; then
  ok "dry-run exit 0"
else
  bad "dry-run exit $?"
  tail -50 "$DRY_LOG"
fi

# Log sanity. The exit trap prints the summary even when the installer
# aborts; only the "next steps" section, printed after every module has run,
# shows that the dry run reached its end.
if grep -qF -e '-- next steps --' "$DRY_LOG"; then ok "dry-run reached end"; else bad "dry-run did not finish"; fi
if grep -qE '^[^[:space:]]*(ERROR|FATAL)' "$DRY_LOG"; then
  bad "errors in dry-run log"
  grep -nE '^[^[:space:]]*(ERROR|FATAL)' "$DRY_LOG" | head -20
else
  ok "no errors in dry-run log"
fi

# Confirm dry-run did NOT mutate the system
hdr "no-mutation invariants"
for i in "${!WATCHED[@]}"; do
  p=${WATCHED[$i]}
  if [[ "${BEFORE[$i]}" == absent ]]; then
    if [[ -e "$p" || -L "$p" ]]; then bad "$p was created during dry-run"; else ok "$p NOT created"; fi
  elif [[ "$(state_of "$p")" != "${BEFORE[$i]}" ]] ||
       [[ -d "$p" && ! -L "$p" &&
          -n "$(find "$p" \( -type f -o -type l \) -newer "$MARK" -not -path '*/__pycache__*' \
                 -print -quit 2>/dev/null)" ]]; then
    bad "$p was changed during dry-run"
  else
    ok "$p unchanged (it was there before)"
  fi
done

rm -f "$DRY_LOG" "$MARK"

hdr "summary"
printf '  passed: %d\n  failed: %d\n' "$PASS" "$FAIL"
exit $(( FAIL > 0 ? 1 : 0 ))
