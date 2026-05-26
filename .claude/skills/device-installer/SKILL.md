---
name: device-installer
description: Install or repair RRR on a Raspberry Pi OS Bookworm device — the modular bash installer in scripts/install/[0-9][0-9]-*.sh, the bootstrap.sh one-liner entry, blue-green layout under ~/rrr, and the systemd --user launcher. Use when the user reports "install failed", asks how to add or modify an install step, debugs an apt/udev/I²C-enable problem, or needs to re-run one stage. Covers `--dry-run`, `--only`, `--skip`, and the reboot-handling logic.
---

# Device installer

The installer is **modular bash**, not a Python script. Entry points:

- [`bootstrap.sh`](bootstrap.sh) — one-line curl install (clones the repo,
  then execs `install.sh`).
- [`install.sh`](install.sh) — runs every `scripts/install/[0-9][0-9]-*.sh`
  module in order.

```bash
curl -fsSL https://raw.githubusercontent.com/Corticomics/rodRefReg/main/bootstrap.sh | bash
```

## The eight modules (in order)

| # | File | Owns |
|---|---|---|
| 00 | [`00-preflight.sh`](scripts/install/00-preflight.sh) | OS = Bookworm check, arch, disk space, network |
| 10 | [`10-apt.sh`](scripts/install/10-apt.sh) | `apt install` PyQt5, pandas, numpy, RPi.GPIO, etc. |
| 20 | [`20-repo.sh`](scripts/install/20-repo.sh) | Sync the checkout to the requested branch (never auto-stashes) |
| 25 | [`25-layout.sh`](scripts/install/25-layout.sh) | Build the blue-green tree under `~/rrr/` |
| 30 | [`30-python.sh`](scripts/install/30-python.sh) | `venv --system-site-packages` + `pip install -r requirements.txt` |
| 40 | [`40-hardware.sh`](scripts/install/40-hardware.sh) | Enable I²C, install SM16relind driver, install udev rule for `/dev/teensy_flow` |
| 50 | [`50-services.sh`](scripts/install/50-services.sh) | Launcher at `~/.local/bin/rrr`, desktop entry, optional systemd `--user` unit |
| 60 | [`60-verify.sh`](scripts/install/60-verify.sh) | Smoke-test imports + `16relind 0 board`; warnings only, never fatal |

One-liner per module: [`references/module-cheatsheet.md`](references/module-cheatsheet.md).

## Flags every operator should know

```bash
./install.sh --dry-run              # print every action, change nothing
./install.sh -y / --yes             # non-interactive (no prompts)
./install.sh --only 40-hardware     # run a single module
./install.sh --skip 50-services     # skip a stage; repeatable
./install.sh --branch dev           # install from a non-main branch
```

Module discovery is in `install.sh`:
```bash
mapfile -t MODULES < <(find "$MODULE_DIR" -maxdepth 1 -type f -name '[0-9][0-9]-*.sh' | sort)
```

Names not matching `[0-9][0-9]-*.sh` are silently ignored — useful for
helper libs (`lib.sh`, `ui.sh`, `ui.theme.sh`, `layout.sh`) that get
sourced but aren't standalone stages.

## Blue-green layout

After 25-layout, the device has:

```
~/rrr/
├── current   → releases/v1.6.4       (symlink)
├── previous  → releases/v1.6.3       (symlink)
├── releases/
│   ├── v1.6.4/   (Project/ + scripts/)
│   └── v1.6.3/
├── shared/
│   ├── venv/     (one venv across all releases)
│   ├── data/     (DB + settings.json + secrets.json + logs)
│   └── logs/
└── state/
    └── boot.json   (release name + fail_count)
```

[`scripts/runtime/launch.sh`](scripts/runtime/launch.sh) reads `boot.json`,
increments `fail_count` on each launch, and rolls `current` back to
`previous` when `fail_count >= 2`. The app resets the counter to 0 once
it starts cleanly.

Details: [`references/blue-green-layout.md`](references/blue-green-layout.md).

## Reboot policy

Modules can flag a reboot as needed by setting `_RRR_REBOOT_REQUIRED=1`
and pushing a reason into `_RRR_REBOOT_REASONS`. The installer summary
prints the reasons and (in interactive mode) asks whether to reboot
immediately. Under `-y` or in a piped-from-curl session, it never
auto-reboots — it just prints the recommendation.

Typical reasons: changing `consoleblank=0`, enabling I²C via
`raspi-config` (the device node `/dev/i2c-1` is available without reboot
in most cases, but group membership in `i2c` only takes effect after the
user logs out and back in).

## Logs

Every run writes to `~/.local/state/rrr/install-<timestamp>.log`. Find
the latest:

```bash
ls -t ~/.local/state/rrr/install-*.log | head -1
```

The installer mirrors stdout+stderr through `tee`; in "rich" UI mode
(`_UI_MODE=rich`) the terminal output is styled and the log file is
stripped of ANSI escapes.

## When something fails

- A non-zero exit kills `install.sh` (set `-Eeuo pipefail` at top).
- An `EXIT` trap prints the per-module summary so you always know where
  it died.
- Re-run with `--only <module>` to retry just the failed stage; modules
  are idempotent by design (apt is `--no-install-recommends`, layout.sh
  doesn't clobber existing data, etc.).

## Don't do this

- Don't shell out to `sudo apt install` from a Python module at runtime.
  All apt installs live in `10-apt.sh`. The Pi installs system packages;
  the venv uses `--system-site-packages` to expose them. See the
  comment in [`requirements.txt`](requirements.txt#L3-L5).
- Don't add `set +e` to a module unless you've also added explicit
  error handling. The strict-mode flags from `install.sh` are
  load-bearing.
- Don't add a numbered module that's not in the `[0-9][0-9]-*.sh`
  pattern. The discovery glob skips it silently and your stage will
  never run.
- Don't write data into the release directory (`~/rrr/current/...`).
  That tree gets swapped on every update. Persistent data lives under
  `~/rrr/shared/data/` and is referenced via `RRR_DATA`
  ([`Project/utils/paths.py`](Project/utils/paths.py)).
