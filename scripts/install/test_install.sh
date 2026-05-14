#!/usr/bin/env bash
#
# Smoke-test the installer without mutating the system.
#
#   - bash -n on every installer script
#   - shellcheck (if available) at warning level
#   - install.sh --help renders
#   - install.sh --dry-run executes end-to-end with no errors
#   - sanity checks on the log file
#
# Safe to run on a fresh Pi. Exits non-zero on any failure.
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
DRY_LOG=$(mktemp)
if ./install.sh --dry-run -y >"$DRY_LOG" 2>&1; then
  ok "dry-run exit 0"
else
  bad "dry-run exit $?"
  tail -50 "$DRY_LOG"
fi

# Log sanity
if grep -q 'rrr installer finished' "$DRY_LOG"; then ok "dry-run reached end"; else bad "dry-run did not finish"; fi
if grep -qE '^[^[:space:]]*(ERROR|FATAL)' "$DRY_LOG"; then
  bad "errors in dry-run log"
  grep -nE '^[^[:space:]]*(ERROR|FATAL)' "$DRY_LOG" | head -20
else
  ok "no errors in dry-run log"
fi

# Confirm dry-run did NOT mutate the system
hdr "no-mutation invariants"
if [[ ! -d "$REPO_ROOT/.venv" ]]; then ok ".venv NOT created"; else bad ".venv was created during dry-run"; fi
if [[ ! -d "$REPO_ROOT/vendor/16relind-rpi" ]]; then ok "vendor/ NOT created"; else bad "vendor/ was created during dry-run"; fi
if [[ ! -e /etc/udev/rules.d/99-rrr-teensy.rules ]]; then ok "udev rule NOT installed"; else bad "udev rule was installed"; fi

rm -f "$DRY_LOG"

hdr "summary"
printf '  passed: %d\n  failed: %d\n' "$PASS" "$FAIL"
exit $(( FAIL > 0 ? 1 : 0 ))
