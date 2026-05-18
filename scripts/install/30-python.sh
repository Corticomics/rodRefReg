# shellcheck shell=bash
# Python: venv with --system-site-packages, pip install -r requirements.txt.

# venv lives in the shared/ tree so it survives release swaps (layout.sh).
VENV_DIR="$RRR_VENV"
REQ_FILE="$REPO_ROOT/requirements.txt"

[[ -f "$REQ_FILE" ]] || die "requirements.txt missing at $REQ_FILE"

if [[ ! -d "$VENV_DIR" ]]; then
  step "creating venv at $VENV_DIR" -- \
    run python3 -m venv --system-site-packages "$VENV_DIR"
else
  info "venv exists at $VENV_DIR"
fi

# Use the venv's pip explicitly; never `source activate` in a script.
PIP="$VENV_DIR/bin/pip"

if [[ "${DRY_RUN:-0}" == "1" ]]; then
  info "[dry-run] would: $PIP install --upgrade pip"
  info "[dry-run] would: $PIP install -r $REQ_FILE"
  return 0
fi

step "upgrading pip" -- run "$PIP" install --upgrade --disable-pip-version-check -q pip
step "installing python requirements" -- \
  with_retry 3 5 -- run "$PIP" install --disable-pip-version-check -q -r "$REQ_FILE"

# Record full freeze to the log only (not the screen).
if [[ -n "${LOG_FILE:-}" ]]; then
  {
    printf '\n--- pip freeze ---\n'
    "$PIP" freeze
    printf '--- end pip freeze ---\n'
  } >>"$LOG_FILE" 2>/dev/null || true
fi
