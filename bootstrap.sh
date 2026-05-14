#!/usr/bin/env bash
#
# Rodent Refreshment Regulator — bootstrap installer
#
# One-line install on a fresh Raspberry Pi OS Bookworm:
#
#   curl -fsSL https://raw.githubusercontent.com/Corticomics/rodRefReg/main/bootstrap.sh | bash
#
# Environment overrides:
#   RRR_REPO_URL   git URL to clone from (default: Corticomics/rodRefReg)
#   RRR_DIR        target directory      (default: ~/rodRefReg)
#   RRR_BRANCH     branch to install     (default: main)
#
# All extra args are forwarded to install.sh, e.g.:
#   curl -fsSL .../bootstrap.sh | bash -s -- --dry-run
#
set -Eeuo pipefail

REPO_URL=${RRR_REPO_URL:-https://github.com/Corticomics/rodRefReg.git}
REPO_DIR=${RRR_DIR:-$HOME/rodRefReg}
BRANCH=${RRR_BRANCH:-main}

# ---- guards --------------------------------------------------------------
if [[ $(id -u) -eq 0 && -z ${SUDO_USER:-} ]]; then
  echo "bootstrap.sh: run as your normal user, not root — it will sudo when needed." >&2
  exit 1
fi

# ---- git -----------------------------------------------------------------
if ! command -v git >/dev/null; then
  echo "bootstrap: installing git..."
  sudo apt-get update -qq
  sudo apt-get install -y --no-install-recommends git
fi

# ---- clone or update ----------------------------------------------------
if [[ -d "$REPO_DIR/.git" ]]; then
  echo "bootstrap: updating $REPO_DIR ($BRANCH)"
  git -C "$REPO_DIR" fetch --prune origin
  git -C "$REPO_DIR" checkout "$BRANCH"
  git -C "$REPO_DIR" pull --ff-only origin "$BRANCH"
else
  echo "bootstrap: cloning $REPO_URL into $REPO_DIR ($BRANCH)"
  git clone --branch "$BRANCH" "$REPO_URL" "$REPO_DIR"
fi

# ---- hand off to install.sh ---------------------------------------------
# When piped from curl, stdin is not a TTY — default to non-interactive (-y)
# if the user did not pass any flags of their own.
ARGS=("$@")
if [[ ${#ARGS[@]} -eq 0 && ! -t 0 ]]; then
  ARGS=(-y)
fi

exec "$REPO_DIR/install.sh" "${ARGS[@]}"
