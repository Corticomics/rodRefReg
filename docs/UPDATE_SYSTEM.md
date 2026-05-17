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

## 12. Open questions

1. **Migration timing** — relocate data on the *next installer run* (operator-initiated, simple)
   or on the *app's first launch* under the new layout (automatic, but the app must handle the
   pre-migration state)? Recommend installer-run.
2. **Release cadence & who signs** — who holds the minisign private key, and what is the
   expected release frequency? Affects key-custody and channel policy.
3. **Fleet visibility** — is there any future need to know which version each device runs
   (a check-in ping)? Out of scope here, but the design leaves room for it.
