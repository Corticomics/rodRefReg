# Contributing to RRR

Developer-facing guide for working on the Rodent Refreshment Regulator.
For the one-page hard rules see [CLAUDE.md](CLAUDE.md); for release
mechanics see [Project/docs/MAINTENANCE.md](Project/docs/MAINTENANCE.md);
for architecture see [Project/docs/DEVELOPMENT.md](Project/docs/DEVELOPMENT.md).

---

## 1. Local development environment

RRR targets **Raspberry Pi OS Bookworm (64-bit)** and runs on PyQt5. The
production install path uses **apt** for the heavy native packages and a
venv with `--system-site-packages` for everything else (see
[scripts/install/30-python.sh](scripts/install/30-python.sh)). Mirror that
split locally — do **not** add the apt-managed packages to
`requirements.txt`.

### Heavy native deps come from the OS package manager

| Package | Pi / Debian | macOS (dev) |
|---|---|---|
| PyQt5 | `sudo apt install python3-pyqt5` | `pip install PyQt5` |
| pandas (+ numpy) | `sudo apt install python3-pandas` | `pip install pandas` |
| RPi.GPIO, gpiozero, sm_16relind | apt (Pi only) | not needed off-device |

These are **intentionally absent** from `requirements.txt` (see the
comment at the top of that file) so pip never clobbers the apt builds on
a device. CI installs them via apt to mirror the Pi
([.github/workflows/tests.yml](.github/workflows/tests.yml)).

### Pinned pip deps

```bash
python3 -m pip install -r requirements.txt        # runtime deps (pinned)
python3 -m pip install -r requirements-dev.txt     # pytest, vulture
```

---

## 2. Running the tests

```bash
pytest                      # from the repo root; config in pytest.ini
```

`pytest.ini` collects only `Project/tests/unit/`. The scripts directly
under `Project/tests/` are hardware-diagnostic CLIs (run manually on a
device) and are **not** collected.

### "Some tests are skipped" is expected without PyQt5

Tests that reach `SystemController`, the GUI, or `RelayWorker` import
PyQt5 at module load. On a machine without PyQt5 they **skip cleanly**
via `pytest.importorskip("PyQt5")` rather than erroring — you'll see
`N skipped`, not failures. To run the **full** suite locally, install
PyQt5 (table above). CI always runs everything (it apt-installs PyQt5 +
pandas), so a green CI run is the source of truth.

Prefer **Qt-free, dependency-injected** tests where possible — e.g.
`test_stop_sequence.py` and `test_strategy_cancellation.py` test
safety-critical logic with plain mocks and run on any machine. That
pattern is the goal for new tests.

`filterwarnings = error` in `pytest.ini` means a new `DeprecationWarning`
(other than the explicitly-ignored ones) will fail the suite — fix the
warning, don't suppress it.

---

## 3. Branch, commit, PR workflow

Full conventions: [MAINTENANCE.md §7](Project/docs/MAINTENANCE.md#7-branch--commit-conventions).
The essentials:

1. **Never commit to `main`.** Branch off `main` as
   `<type>/<short-kebab-slug>` — `feat/`, `fix/`, `refactor/`, `test/`,
   `docs/`, `chore/`, `style/`, `perf/`, `ci/`.
2. **One concern per PR.** Split unrelated changes.
3. **Conventional Commits**: `<type>(<scope>): <one-line subject>`; body
   explains *why*. For release-bound work, name the target version.
4. **Add a test** alongside any non-trivial change. Never weaken or skip
   an existing test to make a PR pass.
5. **Run `pytest` green** (or confirm your new test passes / skips as
   designed) before staging.
6. Push the branch, open a PR, merge through GitHub.

### No AI-tool attribution in git

Do not add `Co-Authored-By` trailers for any AI tool (Claude, Cursor's
`cursoragent@cursor.com`, Copilot, etc.) or "🤖 Generated with …" lines
to commits or PR bodies. If a tool injects one automatically, disable it
in the tool's settings — don't strip it per-commit. See
[CLAUDE.md](CLAUDE.md).

---

## 4. Versioning and releases

`Project/version.py` is the single source of truth; the git tag must
equal `v<__version__>` exactly or CI rejects the build.

- **Code change shipping to devices** → bump `Project/version.py` per the
  SemVer table in [MAINTENANCE.md §2](Project/docs/MAINTENANCE.md#2-picking-the-version-number--semver-for-rrr)
  (PATCH = fix, MINOR = feature, MAJOR = breaking).
- **Doc-only / test-only / tooling-only** PRs do **not** bump the version
  and do **not** get tagged ([MAINTENANCE.md §1 / §3c](Project/docs/MAINTENANCE.md#1-when-to-release-and-when-not-to)).
- Tagging (`git push origin v<x.y.z>`) is the point of no return — it
  publishes a GitHub Release that devices can pull. Pause before it.

Releases are built by CI from `git archive HEAD` of `Project/ scripts/
requirements.txt` — top-level files (this doc, `CLAUDE.md`, installers)
are **not** shipped to devices.

---

## 5. Things to never touch casually

| Path | Why |
|---|---|
| `Project/settings/settings.json`, `*.db`, `secrets.json` | Operator data + Slack credentials; leak risk (gitignored) |
| `dist/` | CI owns it |
| `Project/version.py` | Only as a deliberate version bump |
| `.github/workflows/*.yml` | Affects every release downstream |
| Anything under `~/rrr/` on a device | Live deployment surface |

---

## 6. Hardware-adjacent changes

Code that touches relays, valves, sensors, or the delivery worker can't
be fully validated off-device. At minimum: `pytest` green + a headless
Qt smoke (`QT_QPA_PLATFORM=offscreen`). For real confidence, exercise it
on a Pi and watch `~/rrr/shared/logs/rrr_app_debug.log`. If a change
can't be device-tested in your environment, **say so in the PR
description** rather than claiming it works. The relay/stop/delivery
paths are animal-safety-critical — treat them accordingly.
