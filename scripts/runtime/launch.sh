#!/usr/bin/env bash
# Launch the RRR application. Installed to ~/.local/bin/rrr.
set -Eeuo pipefail

# Resolve repo root: this file lives at <repo>/scripts/runtime/launch.sh
# When installed to ~/.local/bin/rrr, RRR_REPO env var or fallback path is used.
if [[ -n "${RRR_REPO:-}" && -d "$RRR_REPO" ]]; then
  REPO="$RRR_REPO"
elif [[ -d "$HOME/rodRefReg" ]]; then
  REPO="$HOME/rodRefReg"
elif [[ -d "$HOME/Documents/GitHub/rodRefReg" ]]; then
  REPO="$HOME/Documents/GitHub/rodRefReg"
else
  echo "rrr: cannot locate repo; set RRR_REPO=/path/to/rodRefReg" >&2
  exit 1
fi

VENV="$REPO/.venv"
[[ -x "$VENV/bin/python3" ]] || { echo "rrr: venv missing at $VENV; run install.sh" >&2; exit 1; }

cd "$REPO/Project"
exec "$VENV/bin/python3" main.py "$@"
