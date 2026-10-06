# MAINTENANCE.md

Release, versioning, and maintenance reference for RRR maintainers.
Companion to [DEVELOPMENT.md](DEVELOPMENT.md) (architecture and how to
develop) and [UPDATE_SYSTEM.md](UPDATE_SYSTEM.md) (design of
the update pipeline). Hard rules live in [CLAUDE.md](../../CLAUDE.md); this
file is the operator-friendly recipe book.

---

## Contents

1. [When to release (and when not to)](#1-when-to-release-and-when-not-to)
2. [Picking the version number — SemVer for RRR](#2-picking-the-version-number--semver-for-rrr)
3. [Release recipes](#3-release-recipes)
4. [Hard rules](#4-hard-rules)
5. [Verifying a release](#5-verifying-a-release)
6. [Recovery procedures](#6-recovery-procedures)
7. [Branch & commit conventions](#7-branch--commit-conventions)

---

## 1. When to release (and when not to)

A release publishes a `.rrrupdate` bundle that deployed devices can
install via the in-app **Updates** tab. Cutting one means **every device
on the network can pull this code**, so the decision is operational, not
cosmetic.

### Cut a release when…

| Change | Why |
|---|---|
| Bug fix in delivery, calibration, scheduling, sensor, or relay code | Live animals; ship the fix |
| Behavior change visible to operators (UI text, new tab, new flow) | Operators should pick it up |
| New feature wired into the runtime | What we're shipping |
| Security fix (token handling, file permissions, integrity check) | Always release security fixes |
| Hardware driver fix or new supported board | Production reliability |
| Dependency bump that fixes a real issue | Once vetted |

### Do **not** cut a release when…

| Change | Why not |
|---|---|
| Pure documentation (README, CLAUDE.md, this file, doc-string typos) | No runtime effect |
| Repo reorganisation, `.gitignore` tweaks, dev tooling | No runtime effect |
| Test-only changes that don't change production code | No runtime effect — *but* CI must still go green |
| Internal refactor whose new code path is not yet called | Land it, ship later when wired up |
| Anything not yet validated on a real Pi | Test first, then release |

**Test-only or doc-only PRs do NOT bump `Project/version.py` and do NOT
get tagged.** Merge to `main` and stop. Devices keep running their
current release; nothing pulls.

### Edge case — "should this be its own release or wait for the next one?"

If the next release is days away and the change isn't urgent, pile on.
If you're not sure, **bias toward a release** — `MINOR`/`PATCH` is cheap
and the in-app update path is well tested. Avoid sitting on fixes that
affect device behavior.

---

## 2. Picking the version number — SemVer for RRR

`Project/version.py` carries `__version__ = "MAJOR.MINOR.PATCH"`. The
git tag must be exactly `v<__version__>` at the tagged commit, or CI
rejects the build (see [`.github/workflows/release.yml`](../../.github/workflows/release.yml)).

### PATCH bump — `1.6.1 → 1.6.2`

A user-invisible-or-near-invisible **fix** to existing behavior. No new
features, no breaking changes.

| Example | PATCH |
|---|---|
| Off-by-one in cycle timing | yes |
| CSV export drops the last row | yes |
| Slack indicator shows wrong glyph on a specific error code | yes |
| Crash on launch when `settings.json` is missing a key | yes |
| Dependency security pin (e.g. `requests` to a patched version) | yes |
| New UI feature | no — that is MINOR |
| New DB column | no — that is MINOR or MAJOR depending on migration |

### MINOR bump — `1.6.1 → 1.7.0`

A **feature or behavior change** that is backwards-compatible. Devices
on the previous version can install this without operator intervention,
or with only a step the set-up guide already required (see "When in
doubt").

| Example | MINOR |
|---|---|
| New scheduling mode (e.g. "burst") | yes |
| New Settings sub-tab | yes |
| New sensor driver, opt-in via config | yes |
| `apply_update` switched to fail-closed digest verification | yes (Phase 2 / v1.6.0) |
| Slack notifier broadens what it catches; new `last_status` attribute | yes (Phase 2 / v1.6.0) |
| Run refuses a schedule until every cage it waters is calibrated — a step HARDWARE_SETUP already required | yes (v1.21.0; see "When in doubt") |
| Pure bug fix | no — that is PATCH |
| DB schema change requiring a one-way migration | no — that is MAJOR |

### MAJOR bump — `1.6.1 → 2.0.0`

A **breaking change** — devices may need explicit operator action, a
hardware change, or a non-trivial migration. Stop and ask whether the
change can be designed backwards-compatible *before* committing to a
MAJOR release.

| Example | MAJOR |
|---|---|
| DB schema change that cannot be auto-migrated | yes |
| Change of GPIO pin mapping or hardware protocol | yes |
| Drop support for an old Pi model or board revision | yes |
| Settings file format change that operators must hand-edit | yes (avoid this — provide a migration) |
| Renaming `Project/version.py` or any path the installer hard-codes | yes |

Practical signal: **if you're about to add a release-note line that
starts with "Operators must…", it's a MAJOR** — unless the line only
enforces something the set-up guide already required of every device
(see "When in doubt").

### When in doubt

- Fix → PATCH.
- New thing → MINOR.
- Forces the operator to do something new → MAJOR.
- Enforces a step a correctly set-up device has already done (v1.21.0
  refusing to water an uncalibrated cage, which the set-up guide already
  required) → MINOR, with a **Before you update** list in the CHANGELOG
  entry so an operator who skipped the step can do it first. Decided for
  v1.21.0 (2026-10-05).
- If two reasonable people would disagree, pick the *higher* of the two.
  An over-bump is cheap; an under-bump misleads operators about what's
  in a release.

### Pre-releases — `1.7.0-beta`

For risky changes you want to validate on a test Pi before fleet
rollout. Tag as `v1.7.0-beta` (or `-beta.2`, etc). CI publishes it as a
GitHub **pre-release**; the in-app check ignores pre-releases unless the
device is explicitly opted into the beta channel (see
[UPDATE_SYSTEM.md §5.4](UPDATE_SYSTEM.md)).

### Tag history as a sanity check

```
$ git tag --list 'v*' --sort=v:refname
v1.4.1
v1.4.2
v1.5.0   # MINOR — Phase 2.5a settings persistence
v1.5.1   # PATCH — Phase 2.5b secrets file
v1.5.2
v1.5.3   # PATCH — offline-resilience test harness (Phase 1)
v1.6.0   # MINOR — utils.net + fail-closed digest (Phase 2)
v1.6.1   # PATCH — Slack indicator + classified dialogs (Phase 3, arguably MINOR)
```

If a row makes you go "huh, that should have been MINOR not PATCH" —
note it for next time. Past tags are immutable.

---

## 3. Release recipes

### 3a. Standard release — code change shipping to devices

```bash
# 1. clean base
git checkout main
git pull --ff-only origin main

# 2. branch
git checkout -b <type>/<short-slug>          # e.g. fix/calibration-csv-export

# 3. make your code changes; commit incrementally if useful

# 4. bump the version — ALWAYS for a release-bound change
$EDITOR Project/version.py                   # SemVer per §2

# 4b. add the release to CHANGELOG.md (newest first), as "## <version> — …".
#     Start with a "Before you update" list if operators must do anything,
#     e.g. calibrate cages. Fold any version number that was set on main
#     but never tagged into this entry. The release workflow publishes this
#     entry as the GitHub Release notes, which the in-app Updates tab shows;
#     the test suite fails while version.py names a version with no entry.
$EDITOR CHANGELOG.md

# 5. tests and both lint gates must pass locally (CI runs all three)
pytest
ruff check .
ruff format --check .                        # `ruff format .` fixes layout

# 6. commit + push + PR
git add -A
git commit -m "<type>(<scope>): one-line summary

Optional body."
git push -u origin <type>/<short-slug>
# open the printed compare URL, create PR, merge on GitHub

# 7. tag and publish — ONLY after the PR is merged into main
git checkout main
git pull --ff-only origin main
git tag v<MAJOR.MINOR.PATCH>                 # MUST equal Project/version.py
git push origin v<MAJOR.MINOR.PATCH>         # point of no return
# CI now builds the bundle, computes SHA256, and creates the GitHub Release
# with this release's CHANGELOG.md entry as its notes (step 4b). Check the
# Release page once the workflow is green.
```

### 3b. Hotfix on top of an in-flight release

If you've already merged a release-bound PR but haven't tagged yet, and
you spot a bug — fix it on a new branch, merge to `main`, bump
`version.py` once more (PATCH again), and in `CHANGELOG.md` rename the
untagged heading to the new version, add the untagged version to the
entry's "also carries" line (step 4b folds it) and add a line for the
fix. The suite fails until `CHANGELOG.md` has a `## <new version>`
entry. Then tag the latest commit. The intermediate
"would-have-been-tagged" commit on `main` is just history.

If you've **already pushed the tag**, the bad release is published.
Don't try to undo it — cut a new PATCH on top. See §6.

### 3c. Doc / test-only change

Same as 3a but **skip steps 4, 4b and 7**. No version bump, no
CHANGELOG entry, no tag. The
change lands on `main` and stays there until the next code change cuts
the next release (which will pick this up automatically).

### 3d. Pre-release / beta

```bash
# in version.py
__version__ = "1.7.0-beta"

git tag v1.7.0-beta
git push origin v1.7.0-beta
```

CI flags it as a pre-release. Promote it to stable by tagging `v1.7.0`
on the same (or a newer) commit after validation. Don't forget to
re-bump `version.py` to `1.7.0` before tagging stable. The CHANGELOG
entry can be `## 1.7.0-beta` or just `## 1.7.0`: a pre-release uses its
own entry when there is one, else the stable one.

---

## 4. Hard rules

Restated from [CLAUDE.md](../../CLAUDE.md) — the ones that matter at release
time:

| # | Rule | What it stops |
|---|---|---|
| H1 | Always branch off `main` — never commit directly to `main` | Bypassed review; partial releases |
| H2 | `git pull --ff-only origin main` *before* tagging | Tagging a stale commit (we did this with v1.6.0 once — recovered in §6) |
| H3 | `Project/version.py` MUST equal the tag (`v` + value) at the tagged commit | CI rejects the build with an explicit error |
| H4 | `git push origin <tag>` publishes a GitHub Release — point of no return | Anything you push, customers can download |
| H5 | Never edit `dist/` or upload release assets by hand | CI is the only writer there |
| H6 | Never commit `settings/settings.json`, `*.db`, or `secrets.json` | Operator data + Slack credentials would leak |
| H7 | Pre-release tag suffix is `-beta` (e.g. `v1.7.0-beta`) | Mixing pre-release into stable; CI uses the suffix to flag |

`git tag` alone is local and reversible. `git push origin <tag>` is
not. Pause before that command.

---

## 5. Verifying a release

### Before the tag — smoke test on a test Pi (relay HAT, no water)

A Pi with a relay HAT and no plumbing exercises everything but the
water: the install and launch path, relay addressing, the relay-failure
reporting, the hardware lock, the emergency stop and the UI flows. Run
it on the candidate `main` before tagging, in order; dosing accuracy
still needs the bench validation in
[TOPOLOGY_VALIDATION.md](TOPOLOGY_VALIDATION.md). Leave the relay outputs
unconnected: the relays only click. With no valves, every ledger row
shows the planned volume, which is correct (the app cannot know that no
water moved).

Quit RRR first (close it, or `systemctl --user stop rrr` if it
autostarts): the installer does not stop a running copy, and the
single-instance guard is per version, so a new version would start
beside an old one. `git -C ~/rodRefReg status --short
--untracked-files=no` must print nothing: the installer leaves a
checkout with changes to tracked files as it is and installs its
current commit instead. (A plain `git status` also lists `?? vendor/`,
the relay driver the installer cloned there; that is expected.) Then
install the candidate. The installer
fetches `main` itself and builds the same bundle the tag will, so the
Pi ends up on `~/rrr/releases/<version>` exactly as a device would:

```bash
ssh -Y pi@<test-pi>
cd ~/rodRefReg && ./install.sh -y --branch main
```

A Pi without RRR gets it with the one-line `bootstrap.sh` install in the
[README](../../README.md#1-setting-up-your-system), which clones to
`~/rodRefReg`.

RRR is a PyQt5 window, so use the Pi's desktop, VNC, or `ssh -Y` (from a
Mac it needs XQuartz). Use `-Y`, not `-X`: `-X` is untrusted forwarding,
which refuses new windows 20 minutes after login, so the restarts in
steps 6 and 7 would fail to open RRR. Log in on the Profile tab (Create New
Profile on a fresh database): in guest mode the Settings tab (Priming,
Calibration, Delivery, Updates) is hidden, and Run and Change Relay Hats
are greyed out ("Please log in to use this control"). With the HAT
fitted and I²C enabled (`sudo i2cdetect -y 1` lists it):

1. **Start.** Launch with `~/.local/bin/rrr` from the ssh terminal and
   read that terminal: the start-up lines are printed before the Terminal
   tab exists. Expect `Initialized relay hat stack=0`, `[TOPOLOGY] Valve
   topology: shared_manifold`, and no `Failed to initialize hat stack=…`.
   Do not check this in `journalctl --user -u rrr`: under the service the
   output is buffered, and only the `[TOPOLOGY]` line reaches the journal
   before RRR quits.
2. **Priming.** Settings → Priming: Open Master (relay 16 clicks), Open
   Selected on a cage (its relay clicks), Close Master (both click off).
   Run is greyed out while the session is open and comes back after
   Close Master.
3. **Calibration.** Settings → Calibration: calibrate a cage with 10
   pulses and hear the relay; finish the wizard by entering any measured
   volume (there is no water; 0.3 mL gives 0.03 mL per pulse) so the cage
   counts as calibrated. Start a second run and press Esc while it
   pulses: the clicking stops within about a second, Run is available,
   and no `[VALVE CRITICAL]` line appears.
4. **Run and Stop.** A staggered schedule for one animal on that cage,
   with a window from now to at least two hours ahead: steps 5 to 7 run
   it again, across restarts, and Run refuses it once the window has
   ended (**Expired Schedule**). Drop it in the Schedule Queue and press
   Run; answer Yes to **Schedule Start Time Passed** (asked on every Run
   once the start time is past). The relays click in the pulse rhythm.
   Stop: `[STOP] HARDWARE SAFE: all relays off on every relay HAT`, and
   nothing clicks afterwards.
5. **Emergency stop.** Run the schedule again, then Settings → Priming →
   CLOSE ALL RELAYS: the dialog says the schedule was stopped, Run is
   available, and nothing clicks afterwards.
6. **A missing HAT.** Change Relay Hats to 2 with one HAT fitted: the
   second is now "missing". The Terminal tab shows `Failed to initialize
   hat stack=1: …`, `Relay HAT(s) missing: 1 of 2 initialised; …`,
   `[CLEANUP] CRITICAL: relays NOT confirmed off; …` (expected here) and
   `Relay hats updated to 2 hats.`
   - Run the step-4 schedule and press Stop: the Terminal tab shows
     `[STOP] CRITICAL: not every relay HAT confirmed OFF`, then **Relays
     Not Confirmed Off** and a **Warning** dialog appear. Run is
     available again.
   - A cage on the missing HAT (16 or above) cannot be watered. A
     schedule for an animal on cage 16 is refused at Run with **Valve
     calibration needed** ("Not calibrated: cage 16"). Calibrating cage
     16 with 10 pulses fails at the first pulse: **Calibration Failed**, "The cage 16
     valve did not open at pulse 1 of 10: its relay did not switch",
     with a `[VALVE CRITICAL] calibration of cage 16` line (relay 17
     cannot be switched off either); nothing is saved.
   - Run the step-4 schedule again and press Settings → Priming → CLOSE
     ALL RELAYS: the schedule is stopped first (**Relays Not Confirmed
     Off** and **Warning** again), then **Emergency Stop Failed**. Run
     and Change Relay Hats stay greyed out ("Unavailable while an
     unconfirmed emergency stop is in progress").
   - Restart RRR, log in again, then set the count back to 1 with Change
     Relay Hats (the restart cleared the lock-out).
7. **Topology.** Settings → Delivery → Valve Topology → Independent
   (answer Yes to **Change Valve Topology**): the step-3 calibration
   shows **Stale**, and Priming's Open buttons are greyed out until
   restart. After a restart the Priming panel has no master group.
   Calibrate the cage again (only its relay clicks; relay 16 stays
   silent), then Run the step-4 schedule: a delivery clicks only the cage
   relay. Switch back to Shared manifold, recalibrate, restart.
8. **Updates tab.** Shows Installed version: <version>, which must be
   the candidate's; press **Check for updates** and it says "You’re up to
   date (version <version>)" (the latest Release is still the previous
   version). The real update path is checked after the tag, below.

### After the tag

After `git push origin v<x.y.z>`:

1. **Open the Actions tab** on GitHub. The "Release" workflow should
   run within seconds. Wait for it to go green (~1–2 min).
2. **Open the Releases page**. The new tag should appear with three
   assets: `rrr-<x.y.z>.rrrupdate`, `rrr-<x.y.z>.rrrupdate.sha256`,
   `latest.json`. The newest stable release gets the **Latest** badge.
3. **Sanity-check `latest.json`** — open it in the browser:
   ```json
   {
     "version": "1.6.1",
     "url": "https://github.com/Corticomics/rodRefReg/releases/download/v1.6.1/rrr-1.6.1.rrrupdate",
     "sha256": "...",
     "min_upgradable_from": "0.0.0",
     "channel": "stable"
   }
   ```
   The `version` field must match the tag; the bundle URL must 200.
4. **On a test Pi**, open RRR → Settings → Updates → "Check for
   updates". The new version should appear within seconds. Click
   "Update now" and watch the apply → restart cycle complete.
   To rehearse the update the lab devices will get, put the test Pi on
   the previous release first, with data of its own, before the tag:
   quit RRR, move the smoke test's data aside (`mv ~/rrr/shared/data
   ~/rrr/shared/data.smoke`), then
   `git -C ~/rodRefReg checkout v<previous> && cd ~/rodRefReg && ./install.sh -y`
   (a checked-out tag stays pinned). Log in, calibrate a cage and run a
   schedule on it, so the update has a database to migrate.
5. **Watch the test Pi for ~5 minutes** under a real schedule before
   declaring victory. The launcher's boot sentinel
   ([scripts/runtime/launch.sh](../../scripts/runtime/launch.sh)) auto-rolls
   back a release that fails to start twice in a row, but you want to
   catch behavior issues *before* the fleet does.

If CI fails: the most common cause is a tag/version mismatch (rule H3).
See §6.4.

---

## 6. Recovery procedures

### 6.1 You tagged the wrong commit — tag not yet pushed

```bash
git tag -d v<x.y.z>
# re-tag on the right commit
git tag v<x.y.z> <correct-sha>
git push origin v<x.y.z>
```

### 6.2 You pushed a bad tag; no Release exists yet (CI rejected it)

This is the v1.6.0 situation we recovered from. CI rejected because the
tag pointed at a commit whose `version.py` was older than the tag name.
The same recovery applies when the Release job fails because
`CHANGELOG.md` has no entry for the version: nothing was published; add
the entry on a branch, merge it, then re-tag the new commit as below.

```bash
git tag -d v<x.y.z>                          # local
git push origin :refs/tags/v<x.y.z>          # remote (the `:` prefix = delete)
git tag v<x.y.z> <correct-sha>               # re-tag at the commit where version.py == x.y.z
git push origin v<x.y.z>                     # new CI run, this time should pass
```

### 6.3 A bad release IS published and devices may have it

You cannot recall a release; devices may already be running it.

1. **Cut a new PATCH release** with the fix as fast as you can. Bump
   `version.py`, branch, PR, merge, tag, push. Affected devices update
   on their next check (default cadence is silent on launch).
2. If the bug is severe (delivery affected, data loss risk), tell
   operators directly via Slack / email. The Updates tab also has a
   **Revert to previous version** button — operators can click it to
   roll back to the last known-good release.
3. Yank the bad release? `gh release delete v<x.y.z>` removes the
   GitHub Release; the tag stays. Devices that already pulled it keep
   running it until they update. Not a substitute for shipping a fix.

### 6.4 CI rejected the tag with "tag does not match Project/version.py"

The release workflow ([`.github/workflows/release.yml`](../../.github/workflows/release.yml))
checks `tag_name == "v" + Project/version.py` *at the tagged commit*.
The fix is §6.1 (tag not yet pushed) or §6.2 (tag pushed). Do not edit
`version.py` and force-push — that rewrites history and is worse.

### 6.5 The bundle won't download or verify on a device

The Phase 2 updater (`v1.6.0+`) **refuses to install** an unverifiable
bundle (`utils.net.require_digest` is fail-closed). The dialog says
*"Could not verify the update — the checksum file is unreachable"*.

- 99% of the time: GitHub asset propagation lag. Wait a minute and
  re-check.
- 1% of the time: real corruption. Re-cut the release; the bundle is
  rebuilt deterministically from `git archive HEAD`.

---

## 7. Branch & commit conventions

### Branch names

`<type>/<short-kebab-slug>` — examples:

- `feat/burst-scheduling-mode`
- `fix/calibration-csv-export`
- `refactor/extract-relay-handler`
- `test/coverage-for-secrets`
- `docs/add-maintenance-guide`
- `chore/bump-cryptography`

Phased work that ships across multiple PRs can use a longer prefix:

- `offline-resilience/phase-1-test-harness`
- `offline-resilience/phase-2-net-and-updater`

### Commit message format

Conventional commits, as in [DEVELOPMENT.md § Commit Messages](DEVELOPMENT.md#commit-messages):

```
<type>(<scope>): <one-line summary>

<optional body — wrap at ~72 cols, explain why, not what>

<optional footer>
```

`<type>` ∈ `feat`, `fix`, `refactor`, `test`, `docs`, `chore`,
`style`, `perf`, `ci`. `<scope>` is usually a directory or
component (`secrets`, `updater`, `installer`, `offline`).

For release-bound commits, mentioning the target version helps later
readers:

```
feat(offline): Slack failure indicator + clearer updater dialogs (Phase 3, v1.6.1)
```

### PR conventions

- One concern per PR. If the diff stat starts to look unrelated, split.
- The PR title matches the merge commit's subject (GitHub default).
- Squash-merge is fine for small PRs; merge-commit is fine for phased
  work where individual commits add value to `git log`.
- A release-bound PR's description should call out: what bumped
  `version.py`, what category of change (PATCH/MINOR/MAJOR), and any
  manual validation done on a test Pi.

---

## Cross-references

- [CLAUDE.md](../../CLAUDE.md) — the hard-rule one-pager (read before tagging)
- [DEVELOPMENT.md](DEVELOPMENT.md) — architecture, modules, hardware,
  dev environment setup
- [UPDATE_SYSTEM.md](UPDATE_SYSTEM.md) — full design of the
  update pipeline (bundle format, blue-green layout, apply engine,
  boot sentinel)
- [README.md](../../README.md) — user/operator-facing install and quickstart
- [.github/workflows/tests.yml](../../.github/workflows/tests.yml) — on every
  PR and push to `main`: ruff (format + lint) and pytest on the runner's
  Python, and pytest again in a Debian Bookworm container (Python 3.11, apt
  PyQt5/pandas, a `--system-site-packages` venv) that mirrors the devices
- [.github/workflows/release.yml](../../.github/workflows/release.yml) — the
  CI workflow that runs on every `v*` tag push (it does not re-run the tests)
- [scripts/release/build-bundle.sh](../../scripts/release/build-bundle.sh) —
  what `git archive`s into the bundle (worth reading once)
