# Installer module cheatsheet

One-line summary of each numbered module. Source-of-truth lives in
[`scripts/install/`](scripts/install/) — read the file when the cheatsheet
disagrees.

## 00-preflight.sh

[`scripts/install/00-preflight.sh`](scripts/install/00-preflight.sh) —
sanity checks before any mutation.

- OS = Raspberry Pi OS **Bookworm** (reads `/etc/os-release`).
- Arch = `aarch64` (warn-only otherwise).
- Free disk space.
- Internet reachable (used by apt + git later).

Failures here are fatal — the rest of the installer assumes Bookworm
semantics (PEP 668, `/boot/firmware/config.txt`, etc.).

## 10-apt.sh

[`scripts/install/10-apt.sh`](scripts/install/10-apt.sh) — single source
of truth for OS-level dependencies.

- `apt install` the `APT_PACKAGES` list: git, curl, build-essential,
  PyQt5, pandas, numpy, RPi.GPIO, gpiozero, i2c-tools, dialog, etc.
- Uses `--no-install-recommends` to keep the install small.
- Why apt and not pip: PEP 668 on Bookworm forbids global pip; we expose
  apt-installed packages to the venv via `--system-site-packages` in
  `30-python.sh`. Matches the comment in
  [`requirements.txt`](requirements.txt#L3-L5).

## 20-repo.sh

[`scripts/install/20-repo.sh`](scripts/install/20-repo.sh) — sync the
git checkout.

- Refuses to touch a dirty tree (no auto-stash).
- `--branch` flag switches branch *only* if the tree is clean.
- No-op if the checkout is already on the requested branch and clean.

## 25-layout.sh

[`scripts/install/25-layout.sh`](scripts/install/25-layout.sh) — build
the blue-green `~/rrr/` tree.

- Creates `~/rrr/releases/v<__version__>/` and rsync's the working
  checkout into it.
- Atomically repoints `~/rrr/current` to the new release (and `previous`
  to the prior `current`).
- Migrates data: copies `Project/rrr_database.db` → `~/rrr/shared/data/`
  on first install only.

Idempotent — re-running for the same version is a refresh.

## 30-python.sh

[`scripts/install/30-python.sh`](scripts/install/30-python.sh) —
the Python venv.

- Creates `~/rrr/shared/venv` with `--system-site-packages` so PyQt5,
  pandas, numpy, RPi.GPIO from apt are visible.
- `pip install -r requirements.txt` for everything else (cryptography,
  jsonschema, slack_sdk, smbus2, …).
- venv lives under `shared/` so it survives release swaps (not
  rebuilt per release).

## 40-hardware.sh

[`scripts/install/40-hardware.sh`](scripts/install/40-hardware.sh) —
hardware enablement.

- Enables I²C via `raspi-config nonint do_i2c 0` (canonical path).
- Edits `/boot/firmware/config.txt` for `dtparam=i2c_arm=on`,
  `consoleblank=0`.
- Clones + makes the Sequent Microsystems 16-relay HAT driver (the
  `16relind` CLI), Pi-4 and Pi-5 compatible.
- Installs the udev rule that creates `/dev/teensy_flow` (stable symlink
  for the Teensy flow-sensor bridge).
- Adds the user to the `i2c` and `dialout` groups.
- May flag `_RRR_REBOOT_REQUIRED=1` if `consoleblank=0` changed.

## 50-services.sh

[`scripts/install/50-services.sh`](scripts/install/50-services.sh) —
launcher, menu entry, optional autostart.

- Installs `~/.local/bin/rrr` shim (it execs
  [`scripts/runtime/rrr-shim.sh`](scripts/runtime/rrr-shim.sh) →
  [`scripts/runtime/launch.sh`](scripts/runtime/launch.sh)).
- Drops a `.desktop` entry under `~/.local/share/applications/` so the
  app appears in the Raspberry Pi OS menu.
- Optionally installs a systemd `--user` unit for autostart on login.

No system-level service — RRR is a GUI app, so it runs under the user
session, not as root.

## 60-verify.sh

[`scripts/install/60-verify.sh`](scripts/install/60-verify.sh) —
post-install smoke.

- `python3 -c "import PyQt5"`, `import pandas`, `import RPi.GPIO`, etc.
- Calls `16relind 0 board` and warns if the HAT isn't visible (could be
  legitimately absent on a dev install).
- Non-fatal — warnings only. The summary line tells the operator what
  worked.

## Helper files (not numbered, sourced)

- [`scripts/install/lib.sh`](scripts/install/lib.sh) — `die`, `warn`,
  `info`, `section`, `ui_banner`, `ui_confirm`, `boot_firmware_dir`, etc.
- [`scripts/install/layout.sh`](scripts/install/layout.sh) — blue-green
  path helpers used by `25-layout.sh` and `50-services.sh`.
- [`scripts/install/ui.sh`](scripts/install/ui.sh) /
  [`ui.theme.sh`](scripts/install/ui.theme.sh) — rich-mode TUI rendering.
- [`scripts/install/test_install.sh`](scripts/install/test_install.sh) —
  unit-test scaffold for the lib functions.
