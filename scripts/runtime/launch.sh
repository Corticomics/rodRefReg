#!/usr/bin/env bash
# RRR launcher — runs the application from the current release.
#
# Lives inside each release at scripts/runtime/launch.sh and is invoked by the
# stable shim at ~/.local/bin/rrr. It resolves the blue-green layout, runs the
# boot sentinel (auto-rollback of a release that fails to start), exports
# RRR_DATA, and execs the app. See docs/UPDATE_SYSTEM.md §13.2 / §14.7.
set -Eeuo pipefail

RRR_HOME="${RRR_HOME:-$HOME/rrr}"
CURRENT="$RRR_HOME/current"
PREVIOUS="$RRR_HOME/previous"
STATE="$RRR_HOME/state"
BOOT="$STATE/boot.json"
VENV="$RRR_HOME/shared/venv"

[[ -d "$CURRENT/Project" ]] || {
  echo "rrr: no current release at $CURRENT — run install.sh" >&2; exit 1; }

# ---- boot sentinel --------------------------------------------------------
# launch.sh increments a per-release failure counter; the app resets it to 0
# once it has started cleanly. If a release is launched twice without ever
# reaching that healthy mark, roll back to the previous release.
cur_ver=$(basename "$(readlink -f "$CURRENT")")
fail=0 ; rel=""
if [[ -f "$BOOT" ]]; then
  rel=$(python3 -c "import json;print(json.load(open('$BOOT')).get('release',''))" 2>/dev/null || true)
  fail=$(python3 -c "import json;print(int(json.load(open('$BOOT')).get('fail_count',0)))" 2>/dev/null || echo 0)
fi
[[ "$fail" =~ ^[0-9]+$ ]] || fail=0
[[ "$rel" == "$cur_ver" ]] || fail=0          # current changed -> clean slate

if (( fail >= 2 )) && [[ -L "$PREVIOUS" ]]; then
  prev_target=$(readlink -f "$PREVIOUS")
  if [[ -d "$prev_target/Project" && "$prev_target" != "$(readlink -f "$CURRENT")" ]]; then
    echo "rrr: release $cur_ver failed to start twice — rolling back" >&2
    ln -sfn "$prev_target" "$RRR_HOME/.current.tmp"
    mv -T "$RRR_HOME/.current.tmp" "$CURRENT"
    mkdir -p "$STATE"
    printf '{"release": "%s", "fail_count": 0}\n' "$(basename "$prev_target")" >"$BOOT"
    exec "$CURRENT/scripts/runtime/launch.sh" "$@"
  fi
fi

mkdir -p "$STATE"
printf '{"release": "%s", "fail_count": %d}\n' "$cur_ver" "$((fail + 1))" >"$BOOT"

# ---- launch ---------------------------------------------------------------
[[ -x "$VENV/bin/python3" ]] || {
  echo "rrr: venv missing at $VENV — run install.sh" >&2; exit 1; }

export RRR_HOME
export RRR_DATA="$RRR_HOME/shared/data"
mkdir -p "$RRR_DATA"

cd "$CURRENT/Project"
exec "$VENV/bin/python3" main.py "$@"
