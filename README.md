# Rodent Refreshment Regulator (RRR)

**A Simple Water Delivery System for Laboratory Animal Care**

![RRR System](https://github.com/user-attachments/assets/d616c02f-4deb-492b-9152-173165b6e278)

## What is the Rodent Refreshment Regulator?

The Rodent Refreshment Regulator (RRR) helps you automatically deliver precise amounts of water to laboratory animals on a schedule. It takes the guesswork out of water delivery and ensures your research animals receive consistent care.

**No programming knowledge needed!** The system has a simple, user-friendly interface designed for laboratory staff with any level of technical experience.

## Why Use the RRR System?

- ✅ **Consistent Care**: Delivers precise water amounts every time
- ✅ **Time-Saving**: Automates routine water delivery tasks
- ✅ **Animal Welfare**: Ensures animals receive proper hydration
- ✅ **Research Quality**: Improves consistency in experimental conditions
- ✅ **Remote Monitoring**: Sends alerts about system status

## Getting Started: Step-by-Step Guide

### 1. Setting Up Your System

If the system is already installed in your lab, skip to [Using the Application](#2-using-the-application). If you need to set up a new system, contact your IT support team for assistance with hardware installation.

**Requirements**: Raspberry Pi running **Raspberry Pi OS Bookworm (64-bit)** with internet access.

#### One-line install (recommended)

Open a terminal on your Raspberry Pi and run:

```bash
curl -fsSL https://raw.githubusercontent.com/Corticomics/rodRefReg/main/bootstrap.sh | bash
```

That command downloads a small bootstrap script, which installs `git`, clones the repository into `~/rodRefReg`, and then runs the full installer non-interactively. The whole process takes ~5–10 minutes on a fresh Pi (sudo password prompted once for apt).

To preview without changing anything:

```bash
curl -fsSL https://raw.githubusercontent.com/Corticomics/rodRefReg/main/bootstrap.sh | bash -s -- --dry-run
```

#### Manual install

If you'd rather audit the code before running it, or you already have the repo cloned:

```bash
git clone https://github.com/Corticomics/rodRefReg.git ~/rodRefReg
cd ~/rodRefReg
./install.sh
``` 
It will:

- Install all system and Python dependencies
- Enable I²C (via `raspi-config`) without requiring a reboot
- Compile and install the Sequent Microsystems 16-relay HAT driver
- Set up a stable `/dev/teensy_flow` symlink for the Teensy flow sensor (via udev)
- Create a desktop icon, an application-menu entry, and a systemd `--user` service for autostart
- Verify every Python import and the relay HAT CLI before exiting

**Useful installer flags** (work after `./install.sh` or after `bash -s --` in the curl form):

| Flag | Purpose |
|---|---|
| `--dry-run` | Print every action without changing anything (safe to try first) |
| `-y` / `--yes` | Non-interactive mode |
| `--only <module>` | Run a single stage, e.g. `--only 40-hardware` |
| `--skip <module>` | Skip a stage, repeatable |
| `--branch <name>` | Install from a non-`main` branch |
| `--help` | Full usage |

**After install**: log out and back in once (so the new `i2c`, `gpio`, `dialout` group memberships apply), then launch via the desktop icon or `~/.local/bin/rrr`. Reboot only if you want the `consoleblank=0` boot setting to take effect.

Logs from every install run live under `~/.local/state/rrr/install-<timestamp>.log`.

### 2. Using the Application

#### First-Time Login

1. Start the RRR application by clicking the desktop icon or running `~/.local/bin/rrr`
2. You'll see a login screen - if you don't have an account, click "Create Account" to continue
3. The main screen will appear with several tabs

#### Adding Your Animals

1. Go to the **Animals** tab
2. Click **Add Animal**
3. Enter the animal's information as requested
4. Click **Save**
5. Repeat for each animal

#### Naming Cages

1. Go to the **Cages** tab to see a visual layout of the relay board
2. Click any cage tile to assign a custom name (e.g., "Rack A — Cage 3")
3. Names sync automatically to the Wizard, Schedules, and Calibration views

#### Creating a Water Delivery Schedule

The **Schedule Wizard** walks you through schedule creation in 4 steps:

1. Go to the **Wizard** tab (or click **+ New Schedule** in the Schedules hub)
2. **Step 1 — Type**: Choose between:
   - **Instant Delivery**: All animals receive their volume at the same time; conflicting times are auto-queued
   - **Staggered Delivery**: The total volume is divided uniformly across the selected time window
3. **Step 2 — Animals**: Multi-select the animals/cages to include (limited by your hardware — typically 15 cages per HAT)
4. **Step 3 — Parameters**: Set per-animal volume, time window, and schedule name
5. **Step 4 — Review**: Confirm the configuration and click **Save Schedule**

The new schedule appears as a card in the **Schedules** hub.

#### Managing Schedules

- The **Schedules** tab is a hub that shows every schedule as a card with a search bar and multi-select for bulk delete
- Click **Edit** on any card to reopen the wizard-style editor
- Click **Info** for full schedule details

#### Starting Water Delivery

1. In the **Schedules** hub, drag a schedule card onto the **Run/Stop** drop area on the right
2. Click **Run Program**
3. The **Execution Monitor** tab appears next to the Terminal and shows live per-cage progress
4. Monitor the terminal output or the Execution Monitor cards for real-time updates


#### Stopping the Program

1. Click **Stop Program** to halt water delivery
2. The system will stop immediately

#### Unattended Operation

The RRR system is designed to run continuously even when you disconnect your display, keyboard, or mouse. For long-term experiments:

1. **Autostart on graphical login** — enable the user-level systemd service (do **not** run this as root):
   ```bash
   systemctl --user daemon-reload
   systemctl --user enable --now rrr.service
   ```

2. **Headless / no graphical login** — also enable user lingering so the service starts at boot:
   ```bash
   sudo loginctl enable-linger "$USER"
   ```

3. **Power management**: the installer adds `consoleblank=0` to `/boot/firmware/cmdline.txt` so the console will not blank during experiments. A reboot applies this.

4. **Status & logs**:
   ```bash
   systemctl --user status rrr.service
   journalctl --user -u rrr.service -f
   ```

5. **Stop / disable**:
   ```bash
   systemctl --user disable --now rrr.service
   ```

## Daily Use Guide

### Routine

1. **Check System Status**: Open the RRR application and verify it's running/Ran correctly
2. **Update Animal Weights**: Record new animal weights in the Animals tab
3. **Inspect Water Lines**: Check for any leaks or blockages
4. **Water Reservoir**: Ensure the water reservoir has sufficient clean water


5. **Check Delivery Log**: Review the delivery history in the terminal
6. **Verify Schedules**: Confirm schedules for the next day
7. **Backup Data** (optional): Export/Import animal data if needed

## Common Questions

### What if the system isn't delivering water?

1. Check that the **Run Program** button has been clicked
2. Verify that your time window settings are correct (is a future time if start time has passed but end time not, the system will NOT start)
3. Inspect the water tubes for air bubbles or blockages (make sure to prime the tubes and pumpos prior to first use)
4. Check that the water reservoir has enough water

### How do I know how much water each animal received?

The system keeps a log of all water deliveries. You can view this in the terminal window or export the data for your records from the database table called "logs".

### What if I need to change a schedule mid-experiment?

You can create a new schedule at any time. Stop the current program, create your new schedule, and start the program again with the new settings.

### How do I calibrate the system for accurate water delivery?

Go to **Settings → Calibration** and click **Run Calibration Wizard**. The wizard guides you through:

1. Selecting which cages to calibrate (uses the same custom names you set in the Cages tab)
2. Priming the tubing via the **Priming** sub-tab if you haven't already
3. Dispensing a measured pulse per cage and recording the actual volume
4. Saving per-cage calibration factors automatically

Calibrate before starting a new experiment and periodically to maintain accuracy. The **Priming** sub-tab in Settings can be used independently any time you swap tubing or refill the reservoir.

### How do I resolve "i2c-1 not found" or other I²C errors?

The installer enables I²C automatically via `raspi-config nonint do_i2c 0`, which makes `/dev/i2c-1` (the GPIO HAT bus) appear without a reboot on every Pi 4 and Pi 5. If the relay HAT does not respond:

1. Confirm the bus is up:
   ```bash
   ls /dev/i2c-*           # /dev/i2c-1 must be in the list
   sudo i2cdetect -y 1     # the HAT should appear at its I²C address
   ```

2. If `/dev/i2c-1` is missing, re-run the hardware module of the installer (idempotent, ~5 s):
   ```bash
   cd ~/rodRefReg
   ./install.sh -y --only 40-hardware
   ```

3. If it is still missing, run the standalone helper and reboot:
   ```bash
   ~/rodRefReg/scripts/runtime/fix_i2c.sh
   sudo reboot
   ```

4. As a last resort, enable I²C interactively:
   ```bash
   sudo raspi-config       # → Interface Options → I2C → Enable
   ```

Different Raspberry Pi models expose different *internal* I²C bus numbers (Pi 5 also shows `/dev/i2c-13` and `/dev/i2c-14`), but the relay HAT always sits on bus 1.

### How can I run a Python script against the RRR install?

The application uses a virtual environment at `~/rodRefReg/.venv`. Always call its Python directly — do **not** rely on the system `python3`, which (on Bookworm) is intentionally locked down by PEP 668:

```bash
~/rodRefReg/.venv/bin/python3 Project/tests/test_relay_hat.py
```

## Getting Help

If you need assistance with the RRR system:

1. Click the **Help** tab in the application for detailed guides
2. Use the search bar to find specific help topics
3. Contact your laboratory manager or IT support
4. For urgent issues, contact [zepaulojr2@gmail.com](mailto:support@example.com)

## Important Safety Notes

- Always monitor the system during the first few days of a new setup
- Check animals regularly to ensure they are receiving adequate hydration and to check if the hardware setup was made correctly do not leave the subjects by themselves for the first few uses to ensure correct software and hardware setup and safety 
- Keep water lines and pumps clean to prevent contamination
- Never modify the hardware without consulting technical staff

---

**Remember**: The RRR system is designed to assist with animal care, not replace regular monitoring. Always follow your institution's animal welfare guidelines and protocols.
