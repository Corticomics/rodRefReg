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

---

## 7. Colours and themes

Every colour of the UI is a role in one table,
[`Project/ui/style/tokens.py`](Project/ui/style/tokens.py):
`"bg.surface": ("#FFFFFF", "#30373F")` is (light, dark). Four things read it:

| Reader | Colours |
|---|---|
| [`app.qss.tmpl`](Project/ui/style/app.qss.tmpl) → `app-light.qss`, `app-dark.qss` | every stylesheet rule, through `${bg.surface}`-style placeholders |
| [`qt_palette.py`](Project/ui/style/qt_palette.py) (`tokens.QPALETTE`) | the QPalette `StyleManager.apply` sets before the stylesheet: the window, plain containers, input text and placeholders, alternate rows, selection, links |
| [`help_content_manager.py`](Project/utils/help_content_manager.py) (`tokens.HELP_HTML`) | the Help tab's HTML |
| UI code that paints itself ([`theme.py`](Project/ui/style/theme.py) `theme_colour(role)`, `tone_weekend`) | a painter, a drag pixmap, a table cell's text, a colour in rich text, a calendar's weekend dates |

The light and dark stylesheets, `Project/ui/style/app-light.qss` and
`app-dark.qss`, are **generated**: never edit them by hand. Their source:

| File | Holds |
|---|---|
| [`Project/ui/style/tokens.py`](Project/ui/style/tokens.py) | every colour, by role |
| [`Project/ui/style/app.qss.tmpl`](Project/ui/style/app.qss.tmpl) | every rule, once, with `${bg.surface}`-style placeholders; `@light` / `@dark` … `@end`, each at the start of a line, mark lines one theme lacks (today only comments) |

To change a colour or a rule:

1. Edit `tokens.py` (a colour) or `app.qss.tmpl` (a rule).
2. From the repo root, run `python3 Project/ui/style/build_qss.py`. It
   rewrites whichever stylesheet is out of date (it prints `wrote …` or
   `up to date`), or stops on an unknown role, a `$role` without braces,
   an indented directive or an unclosed block, and names the template line.
3. Commit all three together: what you edited and both `.qss` files.

`test_qss_generated.py` fails while a committed stylesheet differs from the
render (`build_qss.py --check` says the same without writing), and when the
two themes differ in anything but token values and comments (a declaration
only one theme has must be listed in the test's `DARK_ONLY`; there are none
today).
`test_qss_parses.py` fails when Qt cannot parse a stylesheet. Name a colour
by what it is for, not how it looks: reuse a role that fits, or add one.
Do not write colours into Python under `Project/ui`: give the widget an
`objectName` or a dynamic property and style it in the template. Code that
paints itself (a `QPainter`, a drag pixmap, a table cell's text, a colour in
rich text) asks for a role when it paints, with `theme_colour(role)` from
[`theme.py`](Project/ui/style/theme.py), never at import: the theme can change
while the app runs. What stays on screen paints again when
`style_manager().theme_changed` fires, as the Calibration table does.
`test_no_new_raw_colours.py` counts the raw colours that UI files still hold
(today only four modules nothing uses, which are to be deleted): it fails when
a file gains one, and when a file loses one until you lower that file's count
in the test's `BASELINE`. The
Help tab's HTML takes its colours from `tokens.HELP_HTML`: a colour it needs
is a role there, never a literal in the HTML. The ratchet keeps counting
`help_content_manager.py`, so none comes back.

**Contrast is tested, in both themes.** `test_theme_contrast.py` checks every
pair of roles the UI draws together with the unrounded WCAG 2.x ratio
(Project/ui/style/contrast.py): 4.5:1 for text, 7:1 for body and secondary
text on the main surfaces, 3:1 for control boundaries and state marks, the
card-on-page step palette B was chosen for, and floors under the HDMI
clip/wash models. When you change a colour, run it; a pair that fails is
fixed by changing the colour, never its threshold. When you put two roles
together in a new way, add the pair: every role a `color:` declaration of
the template names needs one. The status-word colours (`success.text`,
`warning.text`, `danger.text`) also stay at least 25 apart in CIEDE2000
(`contrast.delta_e_2000`), so two of them never look alike in one column. `test_theme_structure.py` guards the
rules the palette depends on:

- no universal `QWidget` background or colour;
- no `color` on a rule that matches an input. Qt then draws the input's
  placeholder in that colour: at half alpha from Qt 5.15.12, under 4.5:1, and
  on the Pi's 5.15.8 at full strength, like typed text;
- no `[placeholderText]` or `QTextEdit:read-only` rule;
- scroll areas and stacked pages transparent.

`test_theme_palette.py` checks the palette on screen, offscreen.
