# shellcheck shell=bash
# Python: venv with --system-site-packages, pip install -r requirements.txt.

VENV_DIR="$REPO_ROOT/.venv"
REQ_FILE="$REPO_ROOT/requirements.txt"

[[ -f "$REQ_FILE" ]] || die "requirements.txt missing at $REQ_FILE"

if [[ ! -d "$VENV_DIR" ]]; then
  info "creating venv at $VENV_DIR"
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

run "$PIP" install --upgrade --disable-pip-version-check pip
run "$PIP" install --disable-pip-version-check -r "$REQ_FILE"

info "pip freeze:"
"$PIP" freeze | sed 's/^/    /' >&2
