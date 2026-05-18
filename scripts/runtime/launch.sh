#!/usr/bin/env bash
# RRR launcher — runs the application from the current release.
#
# Lives inside each release at scripts/runtime/launch.sh and is invoked by the
# stable shim at ~/.local/bin/rrr. It resolves the blue-green layout, exports
# RRR_DATA so the app stores data outside the swappable code, and execs the app.
# See docs/UPDATE_SYSTEM.md §13.2.
set -Eeuo pipefail

RRR_HOME="${RRR_HOME:-$HOME/rrr}"
CURRENT="$RRR_HOME/current"
VENV="$RRR_HOME/shared/venv"

[[ -d "$CURRENT/Project" ]] || {
  echo "rrr: no current release at $CURRENT — run install.sh" >&2; exit 1; }
[[ -x "$VENV/bin/python3" ]] || {
  echo "rrr: venv missing at $VENV — run install.sh" >&2; exit 1; }

export RRR_HOME
export RRR_DATA="$RRR_HOME/shared/data"
mkdir -p "$RRR_DATA"

cd "$CURRENT/Project"
exec "$VENV/bin/python3" main.py "$@"
