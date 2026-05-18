# shellcheck shell=bash
# Layout: build the blue-green release tree under ~/rrr and migrate data.
#
# Runs after 20-repo (needs the synced checkout) and before 30-python (which
# creates the venv inside shared/). See docs/UPDATE_SYSTEM.md §13.2 and §13.4.
#
# Idempotent: a re-run refreshes the release for the current version and
# leaves already-migrated data untouched.

VERSION=$(python3 -c "exec(open('$REPO_ROOT/Project/version.py').read()); print(__version__)") \
  || die "cannot read version from Project/version.py"
[[ -n "$VERSION" ]] || die "empty version in Project/version.py"
RELEASE_DIR="$RRR_RELEASES/$VERSION"

info "blue-green layout: home=$RRR_HOME version=$VERSION"

# ---- directory skeleton -------------------------------------------------
run install -d -o "$RRR_TARGET_USER" -g "$RRR_TARGET_USER" \
  "$RRR_HOME" "$RRR_RELEASES" "$RRR_SHARED" "$RRR_DATA_DIR" \
  "$RRR_LOGS_DIR" "$RRR_BACKUPS_DIR" "$RRR_STATE"

# ---- build the release bundle and stage it ------------------------------
# build-bundle.sh archives git HEAD, which 20-repo has already synced.
step "building release bundle $VERSION" -- \
  run bash "$REPO_ROOT/scripts/release/build-bundle.sh"

BUNDLE="$REPO_ROOT/dist/rrr-$VERSION.rrrupdate"
[[ -f "$BUNDLE" || "${DRY_RUN:-0}" == "1" ]] || die "release bundle not found: $BUNDLE"

# Extract into a staging dir, then swap into place — never extract over a
# live release directory (B4).
INCOMING="$RRR_RELEASES/.incoming-$VERSION"
run rm -rf "$INCOMING"
run install -d -o "$RRR_TARGET_USER" -g "$RRR_TARGET_USER" "$INCOMING"
step "extracting release $VERSION" -- run tar -xzf "$BUNDLE" -C "$INCOMING"
run rm -rf "$RELEASE_DIR"
run mv "$INCOMING" "$RELEASE_DIR"

# ---- point `current` at this release (atomic rename) -------------------
run ln -sfn "$RELEASE_DIR" "$RRR_HOME/.current.tmp"
run mv -T "$RRR_HOME/.current.tmp" "$RRR_CURRENT"
info "current -> $RELEASE_DIR"

# ---- migrate persistent data into shared/ ------------------------------
# Copy-not-move, idempotent. See docs/UPDATE_SYSTEM.md §13.4 / risks R1-R5.
_rrr_migrate_data() {
  local db_dst="$RRR_DATA_DIR/rrr_database.db"
  if [[ -e "$db_dst" ]]; then
    info "data already migrated ($db_dst) — skipping"
    return 0
  fi

  local legacy_db="$REPO_ROOT/Project/rrr_database.db"
  local legacy_settings="$REPO_ROOT/Project/settings/settings.json"
  [[ -f "$legacy_settings" ]] || legacy_settings="$REPO_ROOT/Project/settings.json"

  local backup
  backup="$RRR_BACKUPS_DIR/$(date +%Y%m%d-%H%M%S)"

  if [[ -f "$legacy_db" ]]; then
    install -d "$backup"
    # SQLite online-backup API: a consistent snapshot even if the DB is open.
    python3 - "$legacy_db" "$db_dst" "$backup/rrr_database.db" <<'PY'
import sqlite3, sys
src = sqlite3.connect(sys.argv[1])
for dest_path in sys.argv[2:]:
    dst = sqlite3.connect(dest_path)
    with dst:
        src.backup(dst)
    dst.close()
src.close()
PY
    info "migrated database -> $db_dst (backup in $backup)"
  else
    info "no legacy database — fresh install, nothing to migrate"
  fi

  if [[ -f "$legacy_settings" ]]; then
    install -d "$backup"
    install -m 0644 "$legacy_settings" "$RRR_DATA_DIR/settings.json"
    install -m 0644 "$legacy_settings" "$backup/settings.json"
    info "migrated settings -> $RRR_DATA_DIR/settings.json"
  fi
}

if [[ "${DRY_RUN:-0}" == "1" ]]; then
  info "[dry-run] would migrate database + settings into $RRR_DATA_DIR"
else
  _rrr_migrate_data
fi

# ---- ensure the whole tree is owned by the target user (B1 / R4) -------
run chown -R "$RRR_TARGET_USER:$RRR_TARGET_USER" "$RRR_HOME"
