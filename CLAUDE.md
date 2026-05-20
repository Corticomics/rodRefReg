# CLAUDE.md

Guidance for Claude Code when working in this repository.

## Project

Rodent Refreshment Regulator (RRR) — a PyQt5 application that runs on Raspberry
Pi OS Bookworm and delivers metered water to laboratory animals on a schedule.
Application code lives in `Project/`; the device installer is the modular bash
under `scripts/install/`, driven by `install.sh` and `bootstrap.sh`.

## Releasing an update

The update system is specified in `docs/UPDATE_SYSTEM.md` — read it before
changing anything in this section. To cut a new release, follow these steps
exactly:

1. **Decide the version.** Semantic Versioning, `MAJOR.MINOR.PATCH`:
   - **PATCH** — bug fixes only.
   - **MINOR** — backward-compatible features.
   - **MAJOR** — a breaking DB migration or hardware-protocol change.
2. **Bump `Project/version.py`.** `__version__` is the single source of truth;
   nothing else stores the version.
3. **Land it on `main`.** Commit the bump (with release notes) and merge via PR.
   Releases are cut from `main` only — never from a feature branch or an
   arbitrary commit.
4. **Sanity-check the bundle locally** (recommended): run
   `bash scripts/release/build-bundle.sh` and inspect
   `dist/rrr-<version>.rrrupdate` — confirm it contains no virtualenv, build
   artifacts, or device data.
5. **Tag and push — but pull `main` first.** The tag MUST be `v<__version__>`
   exactly (version `1.2.0` → tag `v1.2.0`); a pre-release uses a `-beta`
   suffix (`v1.2.0-beta`). **Always fast-forward `main` before tagging** —
   otherwise `git tag` will silently mark a stale commit (whatever local `main`
   was pointing at) and CI will reject the tag/version mismatch:
   ```
   git checkout main
   git pull --ff-only origin main   # <- the step that bites if skipped
   git tag v1.2.0
   git push origin v1.2.0
   ```
   If you do tag the wrong commit, the recovery is:
   ```
   git tag -d v1.2.0
   git push origin :refs/tags/v1.2.0
   # then pull and re-tag as above
   ```
6. **CI does the rest.** `.github/workflows/release.yml` fires on the tag,
   verifies the tag matches `Project/version.py` (and fails the build if not),
   builds the release bundle, and publishes a GitHub Release with the
   `.rrrupdate` bundle, its `.sha256`, and `latest.json` attached.

### Rules

- **Never** ship updates by telling users to `git pull`. Tagged GitHub Releases
  are the only supported channel.
- The git tag and `Project/version.py` must always agree — CI enforces this.
- Do not hand-edit `dist/` or upload release assets manually; the workflow owns
  them.
- `git tag` is local and reversible; `git push origin <tag>` publishes a real,
  public release — treat the push as the point of no return and confirm intent
  before running it.

## Repository hygiene

- Build output (`build/`, `dist/`), virtualenvs (`venv/`, `.venv/`,
  `Project/rodrefreg/`), `__pycache__/`, and `.DS_Store` are git-ignored — do
  not re-add them.
- Persistent device data — the SQLite database and `settings/settings.json` —
  must never be committed and is excluded from release bundles.
