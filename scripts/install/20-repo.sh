# shellcheck shell=bash
# Repo: ensure REPO_ROOT is a clean checkout on the requested branch.
#
# Behavior:
#   - If REPO_ROOT is already a git repo: refuse to mutate a dirty tree.
#   - If --branch was passed, switch to it (only when tree is clean).
#   - Never auto-stash, never force-checkout. User decides.

if [[ ! -d "$REPO_ROOT/.git" ]]; then
  warn "$REPO_ROOT is not a git checkout; skipping repo sync"
  return 0
fi

cd "$REPO_ROOT" || die "cannot cd to $REPO_ROOT"

# Refuse to touch a dirty tree.
if ! git diff --quiet || ! git diff --cached --quiet; then
  warn "working tree is dirty; leaving repo state untouched"
  warn "commit/stash your changes and re-run if you need a branch switch or pull"
  return 0
fi

CURRENT_BRANCH=$(git rev-parse --abbrev-ref HEAD)
TARGET_BRANCH=${BRANCH:-$CURRENT_BRANCH}
info "current branch: $CURRENT_BRANCH; target: $TARGET_BRANCH"

step "fetching from origin" -- with_retry 3 3 -- run git fetch --prune origin

if [[ "$TARGET_BRANCH" != "$CURRENT_BRANCH" ]]; then
  step "switching to branch $TARGET_BRANCH" -- run git checkout "$TARGET_BRANCH"
fi

# Fast-forward only; never rewrite history.
step "pulling $TARGET_BRANCH (fast-forward only)" -- \
  run git pull --ff-only origin "$TARGET_BRANCH"
