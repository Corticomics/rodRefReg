# CLAUDE.md

Guidance for Claude Code in this repo. Full runbooks live in
[`Project/docs/`](Project/docs/); the central index is
[README.md](README.md).

## Project

Rodent Refreshment Regulator (RRR) — PyQt5 app on Raspberry Pi OS Bookworm that
delivers metered water to lab animals on a schedule. App code: `Project/`.
Device installer: modular bash in `scripts/install/`, entered via `install.sh`
and `bootstrap.sh`.

## Dev commands

- Tests: `pytest` (config in `pytest.ini`; dev deps in `requirements-dev.txt`).
- Local release dry-run: `bash scripts/release/build-bundle.sh` → inspect
  `dist/rrr-<version>.rrrupdate`.

## Process gate — before every commit

Run this checklist mentally on every change. If any answer is "no", stop.

1. Am I on a branch off `main` (not `main` itself)?
2. Does the branch name follow `<type>/<short-kebab-slug>`?
3. Did I run `pytest` and confirm green (or that my new test passes / skips
   as designed) before staging?
4. Are the staged files only the files this PR is about — no `.DS_Store`,
   no `secrets.json`, no `*.db`, no `settings/settings.json`?
5. If this change affects runtime behavior on a device, did I bump
   `Project/version.py` per the SemVer table in
   [MAINTENANCE.md §2](Project/docs/MAINTENANCE.md#2-picking-the-version-number--semver-for-rrr)?
6. Is the commit message Conventional Commits format
   (`<type>(<scope>): <one-liner>`)?
7. Am I leaving `Co-Authored-By: Claude` and "🤖 Generated with Claude Code"
   out of the commit message and PR body?

## Hard rules (gotchas — read before acting)

### Branching, committing, reviewing

- **Never commit directly to `main`.** Always branch off `main` with
  `<type>/<short-kebab-slug>` (`feat/`, `fix/`, `refactor/`, `test/`,
  `docs/`, `chore/`, `style/`, `perf/`, `ci/` — see
  [MAINTENANCE.md §7](Project/docs/MAINTENANCE.md#7-branch--commit-conventions)),
  push the branch, open a PR, merge through GitHub. Applies to **every**
  change — code, tests, docs, tooling, gitignore tweaks.
- **One concern per PR.** If the diff spans unrelated topics, split it.
- **Conventional Commits.** `<type>(<scope>): <one-line subject>`; body
  explains *why*, not *what*. For release-bound work, mention the target
  version in the subject (`feat(offline): … (Phase 3, v1.6.1)`).
- **No AI attribution in git.** Never add `Co-Authored-By: Claude` /
  `Co-Authored-By: Anthropic` trailers; never add "🤖 Generated with
  Claude Code" lines to commit messages or PR bodies.
- **Never amend a pushed commit and never force-push to `main`.** If a
  pre-commit hook rejects a commit, **fix the issue and create a NEW
  commit** — do not `--amend` (the original commit didn't happen, so
  amend modifies the previous commit and can destroy work).
- **Pull `main` before branching or tagging.** `git checkout main &&
  git pull --ff-only origin main` first. `git tag` is silent about which
  commit it marks; on a stale `main` you'll tag the wrong commit and CI
  will reject it (see [MAINTENANCE.md §6.2](Project/docs/MAINTENANCE.md#62-you-pushed-a-bad-tag-no-release-exists-yet-ci-rejected-it)).

### Versioning (`Project/version.py`) and releases

- **Version source of truth is `Project/version.py`.** Nothing else
  stores it. The git tag MUST equal `v<__version__>` exactly (`v1.2.0`,
  `v1.2.0-beta` for pre-release). CI fails the build on mismatch.
- **Bump `Project/version.py` for every release-bound change**, using the
  SemVer table in [MAINTENANCE.md §2](Project/docs/MAINTENANCE.md#2-picking-the-version-number--semver-for-rrr):
  - PATCH — bug fix, dep security pin, anything user-invisible
  - MINOR — new feature, new sub-tab, new driver opt-in
  - MAJOR — breaking change, schema migration, GPIO/hardware change
  - In doubt → bump the higher level.
  - **If the user explicitly lists "bump version" in their instructions
    for this PR, do it — do not skip citing §3c.** The explicit
    instruction overrides the test/doc-only exemption.
- **Test-only / doc-only PRs default to no version bump and no tag**
  per [MAINTENANCE.md §1](Project/docs/MAINTENANCE.md#1-when-to-release-and-when-not-to)
  / §3c — unless the user instructs otherwise (see above).
- **Pre-release tags use `-beta`** (`v1.7.0-beta`, `-beta.2`). CI flags
  them as pre-release; the in-app updater ignores them unless the
  device opts into the beta channel.
- **`git push origin <tag>` is the point of no return** — it publishes a
  real GitHub Release. `git tag` alone is local and reversible. Pause
  before that command.
- **Never ship updates via `git pull`.** Tagged GitHub Releases are the
  only supported channel; CI owns `dist/` and release assets — do not
  hand-edit `dist/` or upload assets manually (rule H5).
- **Never commit device data.** The SQLite DB, `settings/settings.json`,
  and `secrets.json` are excluded from git and from release bundles
  (`.gitignore` + `build-bundle.sh` enforce this); keep it that way.

### Editing code — test before you ship

- **Never edit code without testing it.** "Tested" means at minimum:
  - `pytest` runs green locally (or the new test you added does), AND
  - for UI/runtime changes touching anything beyond a doc, the change
    has been exercised — at least a headless smoke (`QT_QPA_PLATFORM=
    offscreen`) and ideally a real Pi for hardware-adjacent paths.
  Static checks don't validate feature correctness. If a UI change
  can't be exercised in your environment, **say so explicitly** in the
  PR description rather than claiming success.
- **Add a test alongside any non-trivial code change.** A regression
  that ships and breaks a device costs more than a 5-minute unit test.
- **Never disable, skip, or weaken an existing test to make a PR pass.**
  Either fix the production code, or write a focused replacement test
  and explain in the PR description why the old one was wrong.
- **Hooks are not optional.** Never use `--no-verify`, `--no-gpg-sign`,
  or `-c commit.gpgsign=false` unless explicitly asked. If a pre-commit
  hook fails, investigate the underlying issue; do not bypass.

### Files and paths to never touch casually

| Path | Why |
|---|---|
| `Project/settings/settings.json`, `*.db`, `secrets.json` | Operator data + Slack credentials; leak risk |
| `dist/` | CI owns it — never hand-edit or upload (rule H5) |
| Anything under `~/rrr/` on a device | Live deployment surface; touched only by the launcher and update applier |
| `.github/workflows/*.yml` | Changes here affect every release downstream |
| `Project/version.py` | Only edit as part of a deliberate version bump |

Full release procedure (version bump → tag → CI workflow), recovery for
a mis-tagged commit, and the SemVer decision tables: see
[Project/docs/MAINTENANCE.md](Project/docs/MAINTENANCE.md) (operator-friendly
recipe book) and [Project/docs/UPDATE_SYSTEM.md](Project/docs/UPDATE_SYSTEM.md)
(full design). Hardware bring-up for a new device:
[Project/docs/HARDWARE_SETUP.md](Project/docs/HARDWARE_SETUP.md).
