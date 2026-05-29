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
- **No AI attribution in git.** No `Co-Authored-By` / `Co-authored-by`
  trailers for any AI tool — Claude, Cursor (`cursoragent@cursor.com`),
  GitHub Copilot, Anthropic, or any other agent identifier. No "🤖 Generated
  with …" lines in commit messages or PR bodies. If a tool injects such a
  trailer automatically (Cursor's "agent co-author" setting, Claude Code's
  default trailer, etc.), disable it in the tool's settings — do not strip
  it manually per commit.
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

## Deferred refactors — watch for triggers

Some refactors are intentionally deferred because the *present* benefit
doesn't justify the diff. Don't propose, schedule, or quietly start them.
Instead, watch for the trigger conditions below and surface them when they
appear — that's when the cost/benefit flips.

### R2 — Database domain split behind a facade

**What it is.** Split [Project/models/database_handler.py](Project/models/database_handler.py)
(~2245 LOC) into per-domain repository modules (e.g. `animals_repo.py`,
`schedules_repo.py`, `calibration_repo.py`, `projects_repo.py`,
`deliveries_repo.py`, `users_repo.py`, `cages_repo.py`) behind a thin
`DatabaseHandler` facade so call sites don't change. Roughly 6–8 small PRs,
one domain at a time. Full design in
[DATABASE_HANDLER_REFACTOR_DESIGN.md §4, §9](Project/docs/DATABASE_HANDLER_REFACTOR_DESIGN.md).

**Why deferred (decided 2026-05).** No production fleet, schema is static,
the file works and is tested. A big-bang split now is a large diff for a
navigability gain only — and the correct domain cut lines are best
*discovered* when a real driver appears, not guessed up front. R3 (finish
DI) was done instead because it was a small, concrete win.

**Trigger conditions — open R2 (one domain at a time) when ANY are true:**

1. A planned change is about to touch **>~200 LOC inside a single logical
   domain** of `database_handler.py` (animals, schedules, calibration,
   projects, sessions, deliveries, users, cages). Extract *that* domain
   behind the facade first; the substantive change then lands in the new
   focused repo.
2. Two unrelated PRs in a row need to edit the same domain block and keep
   merge-conflicting against each other (signal: the file has become a
   contention point).
3. A schema change is greenlit that touches one domain heavily — pair the
   R2 extraction with R1 (migration runner) for that domain.
4. Test coverage for one domain is being expanded substantially and the
   tests would be materially cleaner against a focused repo than against
   the monolithic handler.

**When a trigger fires.** Do NOT extract every domain at once. One domain,
one PR: signatures preserved, call sites unchanged via the facade, land it,
verify on Pi, stop. Re-check the watch list before extracting the next.

**If none of the above is true, leave `database_handler.py` alone.**

### Flow sensor — extension point (a future sensor plugs in here)

A new flow sensor is a *possible future* feature using **different hardware,
components, and code** than anything shipped today. The room for it already
exists — do not build speculative abstraction ahead of it, and do not
resurrect the retired driver.

- **The seam is the factory.** [Project/drivers/flow_sensor_factory.py](Project/drivers/flow_sensor_factory.py)
  `create_flow_sensor(settings)` dispatches on `settings['flow_sensor_type']`.
  Today only `'uart'` ships (Teensy bridge,
  [Project/drivers/uart_flow_sensor.py](Project/drivers/uart_flow_sensor.py)).
- **To add one:** write a new `drivers/<name>_flow_sensor.py`, add a new
  `flow_sensor_type` branch in `create_flow_sensor`, and add it to
  `get_available_sensor_types()`. No call site changes — the strategy
  consumes whatever the factory returns.
- **The contract is duck-typed**, defined by what
  [Project/strategies/solenoid_flow_strategy.py](Project/strategies/solenoid_flow_strategy.py)
  calls on the sensor (e.g. `start`/`stop`/`read_one`/`wait_for_frames`). A
  new driver must satisfy that. Only formalize it into a `Protocol` once the
  real sensor exists and the true contract is known — not before.
- **The legacy direct-I²C Sensirion driver (`flow_sensor.py`,
  `SLF3S0600FDriver`) was deleted in v1.9.0** — it was dead and has no reuse
  value for a different sensor. Do not bring it back.

---

Full release procedure (version bump → tag → CI workflow), recovery for
a mis-tagged commit, and the SemVer decision tables: see
[Project/docs/MAINTENANCE.md](Project/docs/MAINTENANCE.md) (operator-friendly
recipe book) and [Project/docs/UPDATE_SYSTEM.md](Project/docs/UPDATE_SYSTEM.md)
(full design). Hardware bring-up for a new device:
[Project/docs/HARDWARE_SETUP.md](Project/docs/HARDWARE_SETUP.md).
