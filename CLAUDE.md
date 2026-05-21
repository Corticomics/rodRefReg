# CLAUDE.md

Guidance for Claude Code in this repo. Full runbooks live in `docs/`.

## Project

Rodent Refreshment Regulator (RRR) — PyQt5 app on Raspberry Pi OS Bookworm that
delivers metered water to lab animals on a schedule. App code: `Project/`.
Device installer: modular bash in `scripts/install/`, entered via `install.sh`
and `bootstrap.sh`.

## Dev commands

- Tests: `pytest` (config in `pytest.ini`; dev deps in `requirements-dev.txt`).
- Local release dry-run: `bash scripts/release/build-bundle.sh` → inspect
  `dist/rrr-<version>.rrrupdate`.

## Hard rules (gotchas — read before acting)

- **Version source of truth is `Project/version.py`.** Nothing else stores it.
  The git tag MUST equal `v<__version__>` exactly (e.g. `v1.2.0`,
  `v1.2.0-beta` for pre-release). CI fails the build on mismatch.
- **Pull `main` before tagging.** `git tag` is silent about which commit it
  marks; if local `main` is stale, you'll tag the wrong commit and CI rejects
  it. Always `git checkout main && git pull --ff-only origin main` first.
- **`git push origin <tag>` is the point of no return** — it publishes a real
  GitHub Release. `git tag` alone is local and reversible.
- **Never ship updates via `git pull`.** Tagged GitHub Releases are the only
  supported channel; CI owns `dist/` and release assets — do not hand-edit or
  upload manually.
- **Never commit device data.** The SQLite DB and `settings/settings.json` are
  excluded from git and from release bundles; keep it that way.

Full release procedure (version bump → tag → CI workflow) and recovery for a
mis-tagged commit: see [docs/UPDATE_SYSTEM.md](docs/UPDATE_SYSTEM.md).
