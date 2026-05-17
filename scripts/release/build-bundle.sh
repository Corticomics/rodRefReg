#!/usr/bin/env bash
# Build a release bundle from the current checkout.
#
# Produces, under dist/:
#   rrr-<version>.rrrupdate         the bundle (tar.gz of app code + manifest)
#   rrr-<version>.rrrupdate.sha256  integrity checksum
#   latest.json                     release manifest the app polls for updates
#
# Used by .github/workflows/release.yml; also runnable locally to inspect a
# bundle before tagging. See docs/UPDATE_SYSTEM.md §5.
set -Eeuo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$REPO_ROOT"

# Portable SHA-256 (sha256sum on Linux/CI, shasum on macOS).
sha256() {
  if command -v sha256sum >/dev/null 2>&1; then
    sha256sum "$1" | cut -d' ' -f1
  else
    shasum -a 256 "$1" | cut -d' ' -f1
  fi
}

VERSION="$(python3 -c 'exec(open("Project/version.py").read()); print(__version__)')"
DIST="$REPO_ROOT/dist"
STAGE="$DIST/stage"
BUNDLE="$DIST/rrr-${VERSION}.rrrupdate"

rm -rf "$DIST"
mkdir -p "$STAGE"

# --- application payload -----------------------------------------------------
# Built from git-tracked files at HEAD only — never the working tree — so the
# release reflects committed state and excludes untracked local cruft (e.g.
# Project/venv/). Then prune committed artifacts that must not ship:
#   - rodrefreg/, build/, dist/  committed virtualenv / PyInstaller output
#   - settings/settings.json     operator data; a release must never overwrite it
#   - .DS_Store                  macOS editor cruft
# See docs/UPDATE_SYSTEM.md §7.
git archive --format=tar HEAD Project scripts requirements.txt | tar -x -C "$STAGE"
rm -rf "$STAGE/Project/rodrefreg" "$STAGE/Project/build" "$STAGE/Project/dist"
rm -f  "$STAGE/Project/settings/settings.json"
find "$STAGE" -name '.DS_Store' -delete

REQ_HASH="$(sha256 requirements.txt)"

# --- manifest (travels inside the bundle) -----------------------------------
cat > "$STAGE/manifest.json" <<EOF
{
  "version": "${VERSION}",
  "min_upgradable_from": "0.0.0",
  "requirements_hash": "${REQ_HASH}",
  "channel": "stable"
}
EOF

# --- pack --------------------------------------------------------------------
tar -czf "$BUNDLE" -C "$STAGE" .
BUNDLE_SHA="$(sha256 "$BUNDLE")"
echo "${BUNDLE_SHA}  rrr-${VERSION}.rrrupdate" > "${BUNDLE}.sha256"

# --- release manifest (separate asset; the small file the app polls) --------
# "signature" is null until minisign signing lands in Phase 3.
cat > "$DIST/latest.json" <<EOF
{
  "version": "${VERSION}",
  "url": "https://github.com/Corticomics/rodRefReg/releases/download/v${VERSION}/rrr-${VERSION}.rrrupdate",
  "sha256": "${BUNDLE_SHA}",
  "signature": null,
  "min_upgradable_from": "0.0.0",
  "channel": "stable",
  "changelog": ""
}
EOF

rm -rf "$STAGE"
echo "built:  $BUNDLE"
echo "sha256: $BUNDLE_SHA"
