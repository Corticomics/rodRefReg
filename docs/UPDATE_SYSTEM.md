# RRR Update System — Design

**Status:** Proposed · **Date:** 2026-05-17 · **Owner:** TBD

Design for shipping updates to deployed Rodent Refreshment Regulator (RRR) devices —
automatically, safely, and without requiring operators to touch a terminal.

---

## 1. Goals & Constraints

| Goal | Decision |
|------|----------|
| Trigger model | **In-app prompt + explicit approve.** App detects updates, operator clicks to apply. No surprise changes on a device delivering water to live animals. |
| Release source | **Tagged GitHub Releases only.** No shipping `main` HEAD. Every release is QA-gated. |
| Connectivity | **Online and offline both supported.** Same artifact applies either way. |
| Operators | **Non-technical researchers.** Update flow is 100% GUI. No git, no shell. |
| Platform | Raspberry Pi OS Bookworm (64-bit), per `README.md`. |

**Non-goals:** OS/firmware updates, multi-device fleet orchestration (future), delta updates.

---

## 2. Why the current model must change

Updates today run `git pull --ff-only` ([scripts/install/20-repo.sh:34](../scripts/install/20-repo.sh#L34),
[bootstrap.sh:41](../bootstrap.sh#L41)). For a non-technical operator on a lab device this fails on
four counts:

1. **Not atomic** — an interrupted pull leaves a half-updated checkout. The device is bricked
   with no clean state to boot from.
2. **No rollback** — a bad release cannot be reverted without a terminal.
3. **No offline path** — `git pull` needs network; air-gapped labs cannot update at all.
4. **Dirty-tree failure** — the SQLite DB and `settings.json` are written *inside the git
   checkout* (see §7). `--ff-only` aborts the moment they diverge, which is immediately.

The fix: stop updating code in place, and stop using git as the delivery mechanism on devices.

---

## 3. Architecture Overview

```
  DEVELOPER                      GITHUB                         DEVICE (Raspberry Pi)
  ─────────                      ──────                         ─────────────────────
  git tag v1.1.0  ──push──▶  Actions: build bundle        ┌──────────────────────────┐
                             ├─ rrr-1.1.0.rrrupdate       │  App (Updates panel)     │
                             ├─ minisign signature        │   ├─ online: latest.json │
                             ├─ SHA256                    │   └─ offline: USB file   │
                             └─ latest.json  ──────────▶  │             │            │
                                  (Release assets)        │             ▼            │
                                                          │     verify → apply       │
                                                          │     engine (§6)          │
                                                          └──────────────────────────┘
```

A release is **one signed bundle file**. Online, the device downloads it. Offline, the operator
copies it from a USB stick. From that point the apply path is identical.

---

## 4. Versioning

Single source of truth — new file `Project/version.py`:

```python
__version__ = "1.0.0"   # SemVer: MAJOR.MINOR.PATCH
```

- The app displays it (About / Updates panel) and uses it for comparison.
- A release is an **annotated git tag** `vX.Y.Z` matching `__version__`.
- CI rejects a tag whose name ≠ `version.py` (prevents drift).
- SemVer rule of thumb for this project: **MAJOR** = breaking DB migration or hardware-protocol
  change, **MINOR** = features, **PATCH** = fixes.

First action: set `1.0.0`, cut tag `v1.0.0` from the current `main`.

---

## 5. Release artifact & layout

### 5.1 Blue-green release directories

Replace "git clone run in place" with versioned, immutable release directories and an atomic
`current` symlink — the standard appliance-update pattern (RAUC/Mender), simplified:

```
~/rrr/
├── releases/
│   ├── 1.0.0/            ← extracted bundle, treated as read-only
│   └── 1.1.0/
├── current -> releases/1.1.0      ← atomic symlink; apply = swap, rollback = swap back
└── shared/                        ← PERSISTS across every update
    ├── venv/
    ├── rrr_database.db
    ├── settings/settings.json
    └── logs/
```

[scripts/runtime/launch.sh](../scripts/runtime/launch.sh) changes to follow `~/rrr/current`
instead of `~/rodRefReg`. The git clone remains, but **only as a developer workflow** — devices
no longer run from it.

### 5.2 The bundle — `rrr-X.Y.Z.rrrupdate`

A `tar.gz` containing:

- `Project/` and `scripts/` (application code for this version)
- `requirements.txt`
- `wheels/` — pip wheels vendored for offline install. Small: PyQt5/pandas/numpy come from
  apt `--system-site-packages`, so only `requests`, `slack_sdk`, `smbus2`, `pyserial` ship here.
- `migrations/` — forward-only DB migration scripts (see §7).
- `manifest.json` — `version`, `min_upgradable_from`, `changelog`, `requirements_hash`.

### 5.3 Release manifest — `latest.json` (separate Release asset)

```json
{
  "version": "1.1.0",
  "url": "https://github.com/Corticomics/rodRefReg/releases/download/v1.1.0/rrr-1.1.0.rrrupdate",
  "sha256": "…",
  "signature": "…",            // minisign detached sig
  "min_upgradable_from": "1.0.0",
  "channel": "stable",
  "changelog": "…"
}
```

The app fetches this one small file to decide whether an update exists.

### 5.4 Channels

`stable` (default) and `beta` (GitHub *pre-releases*). Operators stay on `stable`; a developer
can opt a test device into `beta`. One field in `settings.json`.

---

## 6. The apply engine — `Project/utils/updater.py`

Online and offline both converge here. Steps, in order, **fail-safe** (any failure before
step 7 aborts with the old version fully intact):

1. **Safety gate.** Refuse to apply if a delivery schedule is actively running. Live animals
   depend on the running process — this is a hard block, not a dismissible prompt.
2. **Verify integrity.** Check SHA256 **and** the minisign signature against the public key
   committed in the repo. Critical for the offline path — a USB stick is the realistic tamper
   and corruption vector. Reject on mismatch.
3. **Check compatibility.** Refuse if `current version < manifest.min_upgradable_from`
   (forces stepwise upgrades when a migration chain requires it).
4. **Extract** to `releases/<new>/`.
5. **Provision venv.** If `requirements_hash` differs from the installed one, `pip install`
   from `wheels/` (offline-capable). Otherwise reuse `shared/venv` untouched.
6. **Migrate data** — run pending forward-only migrations against `shared/rrr_database.db`
   inside a transaction; **back up the DB first** to `shared/backups/`.
7. **Health check.** Launch the new release in a subprocess with a `--selftest` flag: import
   modules, open the DB, init (mock) hardware. Must exit 0 within a timeout.
8. **Commit.** Atomically swap the `current` symlink → `restart` the systemd user service
   (`systemctl --user restart rrr`). If the app was launched manually, prompt the operator to
   restart instead.

### Rollback

- Keep the last **3** releases on disk; prune older.
- **Manual:** an Updates-panel button — "Revert to previous version" — swaps the symlink back.
- **Automatic:** a boot sentinel. The launcher writes a "boot attempt" marker; the app clears
  it once it reaches a healthy idle state. If the marker shows **2 consecutive failed boots**,
  the launcher reverts `current` to the prior release and restarts. A bad release can never
  permanently brick a device.

---

## 7. Data migration (audit findings)

The blue-green model only works if persistent data lives **outside** the release directory.
Today it does not. Audit of the current code:

| Data | Today | Code | Move to |
|------|-------|------|---------|
| SQLite DB `rrr_database.db` | **Inside repo** (`Project/`, CWD-relative) | [models/database_handler.py:12](../Project/models/database_handler.py#L12) | `~/rrr/shared/rrr_database.db` |
| `settings.json` | **Inside repo** (`Project/settings/`) | [settings/config.py:5](../Project/settings/config.py#L5) | `~/rrr/shared/settings/settings.json` |
| Slack credentials | **Inside repo**, CWD-relative `settings.json` — buggy | [ui/SlackCredentialsTab.py:41](../Project/ui/SlackCredentialsTab.py#L41) | same as above; **fix the CWD-relative path** |
| Runtime log `~/rrr_app_debug.log` | Outside repo (`$HOME`) | [main.py:28](../Project/main.py#L28) | `~/rrr/shared/logs/` |
| User exports / backups | Outside (operator-chosen) | [ui/SettingsTab.py:1425](../Project/ui/SettingsTab.py#L1425) | no change |

**Required work:**

1. Introduce a `paths` module — a single function resolving the data root
   (`$RRR_DATA` → `~/rrr/shared` → legacy in-repo fallback). All of the call sites above route
   through it. This kills the CWD-relative bugs.
2. **One-time install migration:** on first run under the new layout, if `shared/` is empty but
   a legacy in-repo DB/settings exist, copy them into `shared/`.
3. Forward-only DB migrations: a `schema_version` table + ordered scripts in the bundle's
   `migrations/`. Never auto-downgrade — that is what rollback's DB backup (step 6) covers.

This is the largest piece of work and the main risk in the plan. It is contained entirely in
Phase 2.

---

## 8. User experience

For non-technical researchers, the entire flow is two screens:

- **Banner** — when an update is found, a non-modal bar appears in the main window
  ([ui/gui.py:161](../Project/ui/gui.py#L161) area): *"RRR 1.1.0 is available."* → `[View]`.
- **Updates panel** — a new sub-tab in Settings (alongside Delivery/Calibration/Priming/General,
  [ui/SettingsTab.py:63](../Project/ui/SettingsTab.py#L63)). Shows current version, available
  version, changelog, and one primary button **[Update Now]** plus **[Later]**. Also hosts
  **[Check for updates]**, **[Install from file…]** (offline/USB), and **[Revert to previous
  version]**.
- During apply: a progress dialog with the §6 steps. On failure: a plain-language message
  ("Update could not be installed. Your system is unchanged.") and a log path for support.

The update check runs in a background `QThread` on launch — if there is no network it is a
silent no-op, never a blocking error.

---

## 9. Security

- **Signing:** every bundle is signed with **minisign** (small, single-binary, no GPG keyring
  pain). The public key is committed to the repo; the private key lives only in GitHub Actions
  secrets. The device verifies the signature before extracting (§6 step 2).
- **Transport:** downloads over HTTPS from `github.com` only.
- **Offline trust:** the signature — not TLS — is what protects the USB path. A bundle from an
  untrusted stick is rejected exactly like a tampered download.
- **No elevation:** updates apply entirely within the user's `~/rrr` and the user systemd
  service. No `sudo`, no system-wide writes.

---

## 10. CI/CD — release pipeline

GitHub Actions workflow, triggered on `push` of a tag matching `v*`:

1. Assert tag name == `Project/version.py`.
2. Build `rrr-X.Y.Z.rrrupdate` (code + vendored wheels + migrations + `manifest.json`).
3. Compute SHA256; sign with minisign.
4. Generate `latest.json`.
5. Create the GitHub Release (pre-release if the tag is `-beta`), attach all assets.

Result: cutting a release is `git tag v1.1.0 && git push --tags`. Nothing manual.

---

## 11. Rollout plan — phased, each phase independently shippable

| Phase | Scope | Outcome | Risk |
|-------|-------|---------|------|
| **0 — Versioning** | `version.py`; tag `v1.0.0`; GitHub Actions release workflow producing a bundle + SHA256 | Releases exist and are reproducible | None |
| **1 — Notify** | In-app update check + banner + Updates panel (read-only — tells the operator a version is available) | Operators *know* when they are out of date | Low — no apply logic yet |
| **2 — Apply** | Blue-green layout, `paths` module + data migration (§7), apply engine, rollback | One-click updates with rollback | **Medium** — the data migration |
| **3 — Harden** | Offline USB import, minisign signing/verification, `beta` channel, auto-rollback boot sentinel | Offline support + supply-chain integrity | Low |

Phases 0–1 ship value with near-zero risk and can go out immediately. Phase 2 is the real
engineering effort and should be tested on a non-production Pi before fleet rollout.

---

## 12. Resolved decisions (evidence-backed)

The three pre-Phase-2 questions, resolved against the actual codebase rather than assumption.

### 12.1 Migration timing → **installer-run**

Relocate data in the installer, not at app launch.

- The DB is created safely on demand — `create_tables()` runs in `__init__` with
  `CREATE TABLE IF NOT EXISTS` for every table
  ([database_handler.py:57-247](../Project/models/database_handler.py#L57)); a missing DB never
  crashes the app.
- **But `DatabaseHandler()` is instantiated in three uncoordinated places** —
  [main.py:115](../Project/main.py#L115), [splash_screen.py:53](../Project/ui/splash_screen.py#L53),
  [schedule_drop_area.py:22](../Project/ui/schedule_drop_area.py#L22) — each with the default
  CWD-relative `rrr_database.db`. An in-app migration would race: whichever site runs first
  creates a fresh empty DB in the wrong location.
- The installer is the opposite — one serialized step that already runs Python
  ([30-python.sh:11](../scripts/install/30-python.sh#L11)) and already does protected file copies
  ([40-hardware.sh:91](../scripts/install/40-hardware.sh#L91), `cp -n`).

→ Add a relocation step to the installer. The in-app `paths` module (§7) still ships, but only
to *read* the relocated locations, never to perform the move.

### 12.2 Signing key custody → **single maintainer**

- `git shortlog -sn`: `zepaulojr1` = 1273 commits; next contributor = 104. All recent commits
  are `zepaulojr1`.
- No `.github/` existed before this work — no prior CI, no CODEOWNERS.
- README's only contact is `zepaulojr2@gmail.com` ([README.md:246](../README.md#L246)); no lab
  or institution named.

→ No key-custody policy required. The minisign private key is held by the sole maintainer as a
single GitHub Actions secret. Releases are manual tag pushes at the maintainer's cadence.

### 12.3 Fleet visibility → **deferred; cheap interim win**

- The Slack integration sends only free-text relay/error strings
  ([notifications.py:17-22](../Project/notifications/notifications.py#L17),
  [main.py:367](../Project/main.py#L367)) — no device ID, no version.
- No telemetry, analytics, `device_id`, or `machine-id` code exists anywhere in the app.
- No version string is shown in the UI — the window title is the plain
  `"Rodent Refreshment Regulator"` ([gui.py:58](../Project/ui/gui.py#L58)).

→ A real check-in service is out of scope. Interim win once `version.py` ships: append
`__version__` to the existing Slack startup/error message — basic "which version is this
device on" with zero new infrastructure.

---

## 13. Phase 2 — detailed implementation plan

Phases 0 and 1 only *added* files. Phase 2 changes **where the app runs from** and **where
its data lives** — so it is split into three independently shippable sub-phases, each its own
PR and release.

Phase 2 status of the prerequisites: Phase 0 (versioning + release pipeline) and Phase 1
(in-app update check, shipped as v1.1.0) are done and validated on a Raspberry Pi 5.

### 13.0 Target on-device layout

Guiding principle: **code is disposable and versioned; data is sacred and shared.**

```
~/rrr/                         RRR_HOME
├── releases/
│   └── 1.3.0/                 one extracted release bundle (Project/, scripts/,
│                              requirements.txt, manifest.json, migrations/)
├── current -> releases/1.3.0  atomic symlink — the running version
├── shared/                    survives every update
│   ├── venv/                  the virtualenv
│   ├── data/                  rrr_database.db, settings.json   (RRR_DATA)
│   ├── logs/
│   └── backups/               timestamped DB snapshots taken before each migration
└── state/
    └── boot.json              boot sentinel for auto-rollback
```

The git clone at `~/rodRefReg` **stays**, but only as the installer / build workspace — it is
no longer what the device runs. The runtime is `~/rrr/current`.

### 13.1 Sub-phase 2a — `paths` module  (no behaviour change)  → v1.2.0

The foundation. Centralises every data-file location behind one resolver, with a fallback
that reproduces today's exact paths — so until 2b sets the env var, behaviour is *identical*.

**New file `Project/utils/paths.py`** — resolves locations from the `RRR_DATA` environment
variable, set by the launcher in 2b:

| function | with `RRR_DATA` set | fallback (unset — dev clone / pre-migration) |
|---|---|---|
| `data_dir()` | `$RRR_DATA` | `Project/` (the code dir) |
| `database_path()` | `$RRR_DATA/rrr_database.db` | `Project/rrr_database.db` |
| `settings_path()` | `$RRR_DATA/settings.json` | `Project/settings/settings.json` |
| `debug_log_path()` | `$RRR_DATA/../logs/rrr_app_debug.log` | `~/rrr_app_debug.log` |
| `backups_dir()` | `$RRR_DATA/../backups` | `Project/` |

**Reroute these call sites through `paths`:**

- [models/database_handler.py](../Project/models/database_handler.py) — default `db_path`
  argument → `paths.database_path()`. The three instantiation sites
  ([main.py:115](../Project/main.py#L115), [splash_screen.py:53](../Project/ui/splash_screen.py#L53),
  [schedule_drop_area.py:22](../Project/ui/schedule_drop_area.py#L22)) pass no path, so they
  all inherit the new default — this is what kills the 3-site race from §12.1.
- [settings/config.py](../Project/settings/config.py) — `settings.json` path → `paths.settings_path()`.
- [ui/SlackCredentialsTab.py](../Project/ui/SlackCredentialsTab.py) — fix the CWD-relative
  `settings.json` write → `paths.settings_path()`.
- [main.py](../Project/main.py) — `_DEBUG_LOG_PATH` → `paths.debug_log_path()`.

**Risk:** none — with `RRR_DATA` unset every path equals today's. **Test:** the offscreen
`main.setup()` harness already used in Phase 1 validation, plus a unit assertion that the
resolved paths match the legacy paths when the env var is absent.

### 13.2 Sub-phase 2b — blue-green layout + data migration  → v1.3.0

1. **Thin launcher shim.** `~/.local/bin/rrr` becomes a 3-line *stable* shim:
   `exec ~/rrr/current/scripts/runtime/launch.sh "$@"`. It never changes again — so the
   real launch logic, living inside the release, is itself updatable.
2. **New `scripts/runtime/launch.sh`.** Resolves `~/rrr/current`; exports
   `RRR_HOME=~/rrr` and `RRR_DATA=~/rrr/shared/data`; runs `current/Project/main.py` with
   `~/rrr/shared/venv`.
3. **New installer module `scripts/install/55-layout.sh`** — idempotent:
   - create `~/rrr/{releases,shared/{data,logs,backups},state}`;
   - run `build-bundle.sh`, extract the bundle into `releases/<version>/`;
   - create `shared/venv` fresh (`python -m venv --system-site-packages` + pip install) —
     **venvs are not relocatable**, so it is recreated, never moved;
   - run the data migration (§13.4);
   - point `current` → `releases/<version>`; install the thin shim.
4. **systemd unit** `rrr.service` — `ExecStart` already targets `~/.local/bin/rrr` (the
   shim), so no unit change is needed.

Shipping an installer change means each device re-runs the installer once; that single
re-run performs the migration. Existing `~/rodRefReg` installs are detected and migrated.

### 13.3 Sub-phase 2c — apply engine + rollback + UI  → v1.4.0

**`updater.py` additions:**
- `apply_bundle(path)` — gate (refuse if a delivery schedule is running) → verify SHA256 →
  extract to `releases/<new>/` → provision venv only if `requirements_hash` changed → run DB
  migrations (back up first) → health-check → swap `current` → restart.
- `revert()` — swap `current` to the previous release.
- prune — keep the newest 3 under `releases/`.

**`main.py`** — a `--selftest` flag: import core modules, open the DB, exit 0/1. Used as the
health-check before the symlink swap.

**Auto-rollback.** The launcher increments a counter in `state/boot.json`; the app clears it
on reaching a healthy idle state; the launcher reverts `current` after 2 consecutive failed
boots.

**Restart.** If `rrr.service` is active → `systemctl --user restart rrr`; otherwise prompt the
operator to relaunch.

**UI** ([UpdatesTab.py](../Project/ui/UpdatesTab.py)) — an "Update Now" button driving
`apply_bundle` with a progress dialog, and a "Revert to previous version" button.

Online download only. Offline USB import and minisign signing/verification remain **Phase 3**.

### 13.4 The data migration (the critical step)

Run by `55-layout.sh`, idempotent, **copy-not-move**:

```
if ~/rrr/shared/data/rrr_database.db exists:        skip — already migrated
else:
    locate the legacy DB: ~/rodRefReg/Project/rrr_database.db
    if found:  copy -> shared/data/rrr_database.db
               copy -> shared/backups/<timestamp>/rrr_database.db
    repeat for settings.json (Project/settings/settings.json)
    the legacy copies are LEFT IN PLACE as a fallback — never deleted
```

Forward-only schema migrations: a `schema_version` table plus ordered scripts under
`releases/<v>/migrations/`; the app applies pending ones at startup after backing up the DB.
Downgrades are never automatic — rollback relies on the pre-migration backup.

### 13.5 Validating 2b on the test Pi

The Pi 5 already carries an old-style `~/rodRefReg` install. Validating 2b = re-running the
installer on it and confirming: data lands in `~/rrr/shared/data`, the app runs from
`~/rrr/current`, the legacy DB is preserved, and a second installer run changes nothing
(idempotency).

### 13.6 Decisions already made (flag on review if you disagree)

- Virtualenv is **recreated** in `shared/venv`, not moved (venvs hard-code absolute paths).
- `~/.local/bin/rrr` is a **thin immutable shim**; the real launch logic ships in the release.
- The git clone **stays** as the installer/build workspace; it is not the runtime.
- The installer migration step is **copy-not-move with timestamped backups** — the biggest
  risk in Phase 2 is data loss, and this makes the migration non-destructive and reversible.

### 13.7 Rollout

| Sub-phase | Release | Risk | How users get it |
|---|---|---|---|
| 2a — `paths` module | v1.2.0 | none | normal release |
| 2b — blue-green + migration | v1.3.0 | medium | one installer re-run per device |
| 2c — apply engine + rollback + UI | v1.4.0 | medium | first version with one-click in-app updates |

### 13.8 Deferred — Phase 2.5: settings consolidation

`settings.json` today conflates three things that want different homes: secrets
(`slack_token`), preferences (`interval`, `num_hats`, …), and domain records (`schedules`,
`animals` — already duplicated in the SQLite tables). Phase 2a only does the *interim* fix:
unify the two write paths into one `settings.json` and stop tracking it in git.

The proper end state — best practice for this project — is **zero general-settings files**:

- preferences + domain data → the SQLite DB (the `system_settings` table already exists), so
  the update system has a *single* artifact to back up, migrate, and roll back;
- the Slack secret → a separate mode-600, gitignored `secrets.json` (or an OS keyring);
- retire `settings.json` and the dead `migrate_settings.py`.

This is a refactor that needs an audit of how `schedules`/`animals` actually flow (JSON blob
vs DB tables). It is scheduled as **Phase 2.5**, its own change after Phase 2 — deliberately
not entangled with the layout work.

---

## 14. Phase 2 risk register

Compiled from a code survey *before* implementation. Every risk below has a mitigation that
is now part of the plan.

### 14.1 Findings that correct the Phase 2 plan

- **F1 — `pump_log.json` is a third CWD-relative data file.** `notifications.py` writes
  `LOG_FILE = "pump_log.json"` relative to the working directory (`Project/`). Under
  blue-green the working directory becomes `~/rrr/current/Project`, so this file would land
  *inside the release directory and be lost on every update*. → 2a must also route
  `pump_log.json` through `paths`.
- **F2 — `settings.json` is already split across two files.** `config.py` writes
  `Project/settings/settings.json`; `SlackCredentialsTab.save_credentials` writes
  CWD-relative `Project/settings.json` — a *different file*. → 2a must fix
  `SlackCredentialsTab` to use `paths.settings_path()` **before** any migration, or
  migration copies an incomplete settings file.
- **F3 — 2b is an installer refactor, not just a new module.** `30-python.sh` hard-codes the
  venv at `$REPO_ROOT/.venv` and `50-services.sh` installs `launch.sh` verbatim as the
  launcher. Both must change (venv → `shared/venv`; launcher → thin shim). A standalone
  layout module is not sufficient.
- **F4 — no schema-version mechanism exists.** `create_tables()` does ad-hoc
  `PRAGMA table_info` + `ALTER TABLE` inline. A formal framework would be a *second*
  migration system. Decision: keep `create_tables()` as-is; Phase 2's "migration" support is
  only a `PRAGMA user_version` gate plus the pre-update DB backup — we do **not** rebuild the
  existing ad-hoc migrations.
- **F5 — `Project/migrations/migrate_settings.py` is dead code** (no import site anywhere).
  Flag for removal so it is not confused with the new mechanism.

### 14.2 Data-migration risks (highest severity)

- **R1 — split-brain DB:** app reads the old DB path while migration populated the new one.
  *Mitigation:* `paths` is the single resolver; the launcher always exports `RRR_DATA`;
  migration and runtime resolve identically.
- **R2 — SQLite copied while open → corruption** (live DB has `-wal`/`-shm` sidecars).
  *Mitigation:* migrate with `sqlite3 "$src" ".backup '$dst'"`, not `cp`; only when the app
  is not running.
- **R3 — wrong source DB selected.** *Mitigation:* one deterministic legacy path; if the
  target already exists, skip (idempotent); never guess.
- **R4 — root-owned files in `shared/`** (installer `sudo` steps). *Mitigation:* `shared/` and
  its contents are `chown`ed to the target user; writability asserted post-migration.
- **R5 — destructive migration.** *Mitigation:* copy-not-move; legacy files left intact; a
  timestamped copy also written to `shared/backups/`.

### 14.3 Blue-green / runtime risks

- **R6 — non-atomic symlink swap.** *Mitigation:* create the new link under a temp name then
  `mv -T` (atomic rename); never `rm` then `ln`.
- **R7 — dangling `current`.** *Mitigation:* prune never touches `current`'s target or the
  previous release.
- **R8 — a broken `launch.sh` shipped inside a release** breaks every launch. *Mitigation:*
  keep `launch.sh` minimal and stable; boot-sentinel auto-rollback is the backstop.
- **R9 — the venv is shared, not versioned:** rolling back code does not roll back dependency
  versions. *Mitigation:* deps are pinned and pure-python; re-pip only on a forward update,
  never on rollback; documented limitation.

### 14.4 Apply-engine risks

- **R10 — update applied mid-experiment.** *Mitigation:* hard gate — refuse to apply while a
  delivery worker is running (not a dismissible prompt).
- **R11 — interrupted apply.** *Mitigation:* extract to a temp directory; swap `current` only
  as the final step after the health-check; clean stale temp dirs on the next run.
- **R12 — shallow health-check** (`--selftest` only imports modules). *Mitigation:* accepted;
  the boot sentinel catches runtime failures.
- **R13 — boot sentinel cannot distinguish a crash from a clean quit** (the app exits 0 on a
  normal quit — confirmed in Phase 1 testing). *Mitigation:* the sentinel counts boots that
  *never reached the healthy mark*; the app writes that mark a few seconds after the GUI is
  up, so a clean quit afterwards does not count as a failure.
- **R14 — restart-path ambiguity** (systemd unit vs desktop-icon launch). *Mitigation:*
  `systemctl --user is-active rrr` decides — restart the unit, or instruct the operator.
- **R15 — disk exhaustion** from accumulating releases. *Mitigation:* check free space before
  extracting; prune to 3 releases.

### 14.5 Technical debt accepted

- **D1 — permanent dual path logic** in `paths` (device layout vs dev-clone fallback).
  Necessary; the fallback is kept dead-simple.
- **D2 — two "homes" on a device** (`~/rodRefReg` clone + `~/rrr`). The clone is build-only;
  documented so support is not misled.
- **D3 — installer module ordering** becomes layout-coupled (python → layout → services).
  Documented in each module header.
- **D4 — `requirements_hash` state** must live in `shared/` to decide whether to re-pip.
  A single small state file is the one source of truth.

### 14.6 Phase 2b — implementation risk log

Found while designing the installer refactor; each is mitigated in the 2b code.

- **B1 — root vs user home.** `install.sh` may run under `sudo`; assuming `$HOME` would build
  the tree in `/root`. *Mitigation:* a shared `scripts/install/layout.sh` resolves the target
  user/home via `SUDO_USER` (the pattern `50-services.sh` already uses); the tree is
  `chown`ed to the target user.
- **B2 — venv-path drift.** The venv path is referenced by `30-python`, `40-hardware`,
  `60-verify`, and `launch.sh`. *Mitigation:* `layout.sh` defines `RRR_VENV` once; every
  module consumes it — no path is hard-coded in more than one place.
- **B3 — `--only` / `--skip` runs.** Modules now depend on layout variables. *Mitigation:*
  `layout.sh` is sourced by `lib.sh`, so the variables exist for every module regardless of
  which subset runs.
- **B4 — a re-run corrupts the running release.** *Mitigation:* the bundle is extracted to
  `.incoming-<v>` then atomically `mv`'d into place; the `current` symlink is swapped with
  `mv -T` (atomic rename), never `rm`+`ln`.
- **B5 — migration corruption / live DB.** *Mitigation:* the DB is copied with SQLite's
  online-backup API (`Connection.backup()` via the stdlib — no `sqlite3` CLI dependency),
  consistent even if the DB is open. Copy-not-move; a timestamped copy also goes to
  `shared/backups/`.
- **B6 — re-migration / split data.** *Mitigation:* migration is skipped entirely when
  `shared/data/rrr_database.db` already exists.
- **B7 — `20-repo` refuses a dirty tree.** A device whose clone has local edits will silently
  not update through the installer. *Mitigation:* documented; a device clone is hard-reset to
  the target branch before an installer run. OTA updates (2c) bypass this path entirely.
- **B8 — orphaned pre-2b venv.** The old `~/rodRefReg/.venv` is left behind, unused.
  *Mitigation:* harmless; documented as build-only cruft (relates to D2).

### 14.7 Phase 2c — apply engine design & risk log

**Apply sequence** (`updater.apply_update`, run on a background thread):
gate → download → verify SHA256 → extract to `releases/<new>/` (staged, then atomic
`mv`) → re-pip into `shared/venv` *iff* `manifest.requirements_hash` changed →
`--selftest` the new release in a subprocess → record `state/previous` → atomic
`current` swap → restart. Any failure before the swap aborts with the old release live.

**Boot sentinel** (the subtle part). `state/boot.json` =
`{"release": "<version>", "fail_count": N}`.
- `launch.sh`, before exec'ing the app: if `boot.json.release` ≠ the version `current`
  points at, reset `fail_count` to 0 (a new release — or a revert — gets a clean slate).
  If `fail_count` ≥ 2 and a `previous` release exists → **revert** `current` → `previous`,
  reset, and re-exec. Otherwise write `fail_count + 1` and launch.
- The app, ~8 s after the GUI is up and the event loop is healthy, writes `fail_count: 0`.
- Net effect: a release that never reaches "healthy" twice running is auto-rolled-back on
  the third launch. A healthy release keeps `fail_count` at 0–1.

**Risks**

- **C1 — interrupted apply.** Extract to a staged dir; the `current` swap is the last
  step → a kill at any earlier point leaves the running release untouched. Stale staged
  dirs are cleared on the next apply.
- **C2 — corrupt/partial download.** SHA256 verified before extraction; mismatch aborts.
- **C3 — re-pip into a live venv.** The running app keeps its already-imported modules;
  new deps take effect on the next launch. Re-pip runs only when `requirements_hash`
  changed (rare). Documented limitation.
- **C4 — sentinel false rollback** (a clean quit before the 8 s healthy mark).
  *Mitigation:* the healthy mark fires quickly; two quick quits in a row are needed to
  trigger a revert — rare. Documented.
- **C5 — `launch.sh` now carries sentinel logic** (tension with "minimal launcher").
  *Mitigation:* the *shim* stays the immutable anchor; sentinel reads are all guarded so
  a malformed `boot.json` can never block launch.
- **C6 — apply during an experiment.** Hard gate: a module-level busy-check (registered
  by `main.py`) refuses to apply while a delivery worker runs.
- **C7 — shallow `--selftest`** (imports + DB open only). Accepted; the sentinel is the
  deeper net.
- **C8 — restart path.** `systemctl --user is-active rrr` decides: restart the unit, or
  tell the operator to relaunch.
- **C9 — disk.** Free space checked before download/extract; releases pruned to 3.
- **C11 — double-apply.** The "Update Now" button is disabled while an apply runs.
- **C14 — no previous release.** "Revert" is disabled when `previous` is absent.

**Technical debt**

- **D5 — `launch.sh` grows** to carry the sentinel; kept compact and fully guarded.
- **D7 — extract+swap exists twice** — in `25-layout.sh` (bash, install path) and
  `updater.py` (Python, OTA path). The shared contract is the release-dir layout, not the
  code. Accepted; both kept small.
