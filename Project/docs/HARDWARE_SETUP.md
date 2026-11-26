# Hardware Setup Guide

End-to-end procedure for building an RRR device from parts: Raspberry Pi, relay
HAT, solenoid valves, 12 V DC power, common-ground bus, tubing, and a wall
mount. Written for lab technicians and undergraduate research assistants
without prior electronics experience.

> **Before you start.** Read this document fully once, then execute it
> top-to-bottom on a single bench session. Skipping ahead is the most common
> failure mode. If something does not match what you see in front of you,
> stop and check with a maintainer before applying power.

---

## Contents

1. [Safety](#1-safety)
2. [Bill of Materials](#2-bill-of-materials)
3. [Plan the Installation Before Cutting Wire](#3-plan-the-installation-before-cutting-wire)
4. [Raspberry Pi and Operating System](#4-raspberry-pi-and-operating-system)
   - [4.4 A Pi 5 on NVMe](#44-a-pi-5-on-nvme)
   - [4.5 A frozen rig: what to do](#45-a-frozen-rig-what-to-do), the page
     to print and tape to every rig that waters animals
5. [16-Relays HAT — Stacking and Jumpers](#5-16-relays-hat--stacking-and-jumpers)
6. [Electrical System — Power and Common Ground](#6-electrical-system--power-and-common-ground)
7. [Valve Wiring](#7-valve-wiring)
8. [Tubing and Reservoir](#8-tubing-and-reservoir)
9. [First Power-On and Bring-Up Test](#9-first-power-on-and-bring-up-test)
10. [Software Install and Verification](#10-software-install-and-verification)
11. [Troubleshooting](#11-troubleshooting)
12. [References](#12-references)

---

## 1. Safety

Solenoid valves, 120 V AC mains, and DC power supplies in close proximity to
water create three risks that you must respect: electric shock, short circuits
through spilled water, and the device latching valves open if it fails wrong.
The procedure below is designed to mitigate each one. Do not deviate.

- **Never apply mains power until every step in
  [§9 First Power-On](#9-first-power-on-and-bring-up-test) is complete.**
- **Keep the 12 V (or 24 V) DC bench supply unplugged from the wall while you
  wire anything.** A multimeter on continuity mode is your friend; an
  energized rail is not.
- **Water and electronics must be separated by a physical barrier.** Mount the
  Pi and HAT above any reservoir or drip path so a leak cannot land on a
  powered board.
- **The DC power supply must be sized for your load.** See
  [§6.2](#62-power-budget). Undersized supplies sag under load and cause valves
  to chatter or fail to open.
- **If you smell burning insulation, see smoke, or a relay LED flickers
  rapidly during quiescent state, disconnect mains immediately.** Diagnose
  cold.
- **Two-person rule for first power-on.** One person at the wall plug, one
  watching the boards. See [§9.1](#91-pre-flight-checklist).
- **If RRR or the desktop freezes, or a command shows `Input/output error`,
  switch the valve power supply off first**, then follow
  [§4.5](#45-a-frozen-rig-what-to-do). The relay HAT keeps its relays as they
  were, so a valve that was open stays open.

---

## 2. Bill of Materials

Quantities are for a single 15-cage device: 1 HAT × 16 relays gives 15 animal
channels plus relay 16, which is the master valve on the shared-manifold rig
and is left unwired on the independent rig (one syringe and one valve per
animal; see [§7.2](#72-why-the-master-valve-is-on-channel-16)). Scale up for
stacked HATs; each further HAT adds 16 animal channels.

### 2.1 Compute and control

| Item | Qty | Notes |
|---|---|---|
| Raspberry Pi 5 (4 GB or 8 GB) | 1 | Pi 4 also works; this guide targets Pi 5. |
| Raspberry Pi 5 official 27 W USB-C PSU | 1 | Required for Pi 5; under-powered PSUs cause USB resets. |
| microSD card, 32 GB or larger, A2/Class 10 | 1 | Imaged with Raspberry Pi OS Bookworm 64-bit. See [§4](#4-raspberry-pi-and-operating-system). |
| USB adapter for an M.2 NVMe drive (it must say NVMe: an M.2 SATA-only adapter cannot read one) | 1 per lab, if any rig boots from NVMe | On a Pi that boots from an NVMe drive, the boot partition, with `cmdline.txt` and its backups, is on that same drive. If an edit stops the Pi booting, this adapter lets another computer copy the backup back. See [§4.4.7](#447-the-reboot-after-an-edit-and-a-pi-that-does-not-boot). |
| HDMI cable (micro-HDMI to HDMI), USB keyboard, USB mouse, monitor | 1 each | For initial OS setup only. After install you can run headless. |
| Sequent Microsystems *Sixteen Relays 2 A / 24 V 8-Layer Stackable HAT* | 1 (up to 8 stackable) | See bundled [16-RELAYS-UsersGuide](16-RELAYS-UsersGuide_d5e24457-bdd9-4e16-a307-7f90bbd668bb.pdf). |

### 2.2 Solenoid valves

The system is valve-agnostic as long as the valve can be switched by a
single-pole relay rated 2 A at 24 V (the HAT's relay rating). Historical
RRR builds used Parker Series 3 valves; cheaper third-party valves are
currently under evaluation.

| Item | Qty | Notes |
|---|---|---|
| 12 V DC (or 24 V DC) normally-closed solenoid valve, ≤ 2 A holding current, with female 2.1 × 5.5 mm DC barrel-jack pigtail or equivalent leads | Shared manifold: 16 per HAT (1 master + 15 animal). Independent: 15 on the first HAT, 16 on each further HAT (no master) | **TBD — exact model pending lab confirmation.** Confirm voltage matches your PSU. Normally-closed (NC) is required so a power loss closes the valve. |

> **Why 16, not 15? (shared-manifold rig)** The master valve is wired in
> series upstream of the animal valves and provides a single shutoff point.
> Relay channel **16** is the master and channels 1–15 are the animal
> channels — that is the application's default (`global_master_relay_id = 16`
> in [`Project/controllers/system_controller.py`](../controllers/system_controller.py),
> stored per device in the `system_settings` table). Wire to match the
> setting, never the other way round. On an independent rig (one syringe and
> one valve per animal) there is no master: buy 15 valves for the first HAT
> and leave relay 16 unwired (see [§7.2](#72-why-the-master-valve-is-on-channel-16)).

### 2.3 DC power and distribution

| Item | Qty | Notes |
|---|---|---|
| 12 V DC regulated power supply, ≥ 10 A continuous (or 24 V DC if your valves require it) | 1 | **TBD — confirmed amperage pending valve selection.** See [§6.2 Power Budget](#62-power-budget) for the calculation. |
| 1-input × 8-output DC power splitter, 2.1 × 5.5 mm barrel jacks (e.g., Amazon B01H4VEB6G or equivalent) | 2 | One splits PSU → 8 valves; with 16 valves you need two splitters in parallel from the PSU. Verify the splitter's wire gauge supports your total current. |
| Male 2.1 × 5.5 mm DC barrel-jack connectors with screw terminals (e.g., DAYKIT B01J1WZENK or equivalent) | 16 (15 on an independent rig) | One per valve. The valve's two leads land in these connectors. |
| 22 AWG hookup wire, stranded, two colors (red for +12 V, black for ground) | ~5 m each | **Measure your run lengths in [§3](#3-plan-the-installation-before-cutting-wire) before cutting.** |
| Wago lever-nut connectors or equivalent (optional) | as needed | Cleaner than wire nuts for branching the splitter output. |

### 2.4 Common-ground bus

This is the most error-prone subsystem. Read [§6.3](#63-common-ground-bus) in
full before buying parts.

| Item | Qty | Notes |
|---|---|---|
| **Preferred:** DIN-rail grounding terminal block (e.g., Phoenix Contact UT 4 PE or equivalent), or copper bus bar with insulated standoffs | 1 | Purpose-built, safe, and labelable. |
| **Alternative (what we currently use):** 6-outlet surge-protected power strip + 2 × male NEMA 5-15P plug bodies (replaceable plug ends from a hardware store) | 1 strip, 2 plug bodies | See the safety caveats in [§6.3.2](#632-alternative--energized-power-strip-as-ground-bus-current-practice-not-recommended-long-term) — this approach works but ties your DC return to building earth, which has tradeoffs. |
| Solder, heat-shrink tubing, electrical tape | as needed | All wire-to-plug joints must be soldered and insulated. |

### 2.5 Mechanical / mounting

| Item | Qty | Notes |
|---|---|---|
| Wall-mount enclosure or backboard | 1 | **TBD — STL file pending; mount must support the Pi + HAT stack above water level.** |
| 3D-printed reservoir mounts, intra-cage water collectors, pump holders | as needed | STL files in [`Project/docs/STL Files/`](STL%20Files/). |
| Cable ties, adhesive cable mounts, label maker | as needed | Label every wire at both ends before installing. |

### 2.6 Tubing and fluid path

| Item | Qty | Notes |
|---|---|---|
| Food-grade silicone or Tygon tubing | enough for 16 runs | **TBD — confirm inner diameter, outer diameter, material, and length per cage.** Match the tubing ID to your valve's barb fitting. |
| Water reservoir (10 mL per cage mount provided as STL): one shared reservoir on the shared-manifold rig; one syringe per animal on the independent rig | Shared: 1+. Independent: 1 per animal | See [10ml_Water_Reservoir_Mount_x4.stl](STL%20Files/10ml_Water_Reservoir_Mount_x4.stl). |
| Inline barbed fittings, tubing cutter, tube clamps | as needed | |

---

## 3. Plan the Installation Before Cutting Wire

**Do not cut, strip, or solder anything until this step is complete.** A
twenty-minute layout exercise saves hours of rework and a spool of wasted wire.

1. **Locate the wall area where the device will live for the duration of the
   experiment.** This is the mounting surface referenced by the STL backplate
   (TBD — file pending).
2. **Mark the rack/cage positions.** For each animal cage, mark the planned
   location of:
   - The valve body
   - The reservoir
   - The water-delivery spout inside the cage
3. **Measure the longest required run** from the relay HAT to the farthest
   valve, and from that valve to the farthest cage spout. Add 15 % slack for
   service loops at each termination.
4. **Sum the wire runs.** Wire is cheap; running out mid-build is not. Buy
   25 % more than your measured total of each color.
5. **Sketch the layout** (paper is fine). The sketch should show: PSU
   location, splitter location, ground-bus location, every wire run, and every
   tubing run. Photograph the sketch — you will reference it during wiring.
6. **Shared-manifold rig: decide your master-valve location.** The master sits
   between the reservoir and the manifold feeding the animal valves. Wire it to
   relay channel 16 (the application default — see [§7.2](#72-why-the-master-valve-is-on-channel-16)).
   **Independent rig:** there is no master valve and no manifold. Mark each
   animal's syringe location instead, and plan relay 16 as unwired.

---

## 4. Raspberry Pi and Operating System

### 4.1 Flash the OS

1. On any computer, install **Raspberry Pi Imager** from
   <https://www.raspberrypi.com/software/>.
2. Insert the microSD card into your computer.
3. In Imager, choose:
   - **Device:** Raspberry Pi 5
   - **Operating System:** Raspberry Pi OS (64-bit) — *Bookworm*. Do **not**
     choose Lite; the RRR application is a PyQt5 GUI and requires a desktop
     session.
   - **Storage:** the microSD card
4. Click the gear icon (or *Edit Settings*) to pre-configure:
   - Hostname (e.g., `rrr-lab1`)
   - Username and password (avoid the legacy `pi`/`raspberry` default)
   - Wi-Fi SSID and password, or skip if using Ethernet
   - Locale and timezone
   - **Enable SSH** (password authentication is fine on a lab network)
5. Click **Write** and wait for the imager to verify.

### 4.2 First boot

1. Insert the SD card into the Pi 5.
2. Connect HDMI, keyboard, and mouse.
3. Connect the Pi 5's official 27 W PSU **last**.
4. The Pi will boot to a desktop. Open a terminal (top-bar icon).
5. Run a full system update:

   ```bash
   sudo apt update
   sudo apt full-upgrade -y
   sudo reboot
   ```

6. After reboot, verify the OS version:

   ```bash
   cat /etc/os-release | grep VERSION_CODENAME
   # Expected: VERSION_CODENAME=bookworm
   ```

### 4.3 Enable I²C

The relay HAT communicates over I²C. The RRR installer enables this
automatically, but if you want to verify or do it manually:

```bash
sudo raspi-config nonint do_i2c 0
ls /dev/i2c-*           # /dev/i2c-1 must appear
```

### 4.4 A Pi 5 on NVMe

This guide installs Raspberry Pi OS on a microSD card
([§4.1](#41-flash-the-os)). Some lab rigs boot from an NVMe drive instead: an
M.2 SSD on the Pi 5's PCIe connector. To check which one a Pi uses:

```bash
findmnt -n -o SOURCE /   # /dev/nvme0n1p2: an NVMe drive; /dev/mmcblk0p2: the SD card
```

When the drive drops out, the root file system goes with it. RRR and the
desktop freeze, or commands print `Input/output error`. The relay HAT keeps
every relay as it was, so **a valve that was open stays open**. What to do
then is [§4.5](#45-a-frozen-rig-what-to-do), the page to print for every rig.

#### 4.4.1 Power and the PCIe link

- Use the official Raspberry Pi 27 W USB-C supply
  ([§2.1](#21-compute-and-control)). To check it:

  ```bash
  vcgencmd get_throttled           # must print throttled=0x0
  vcgencmd pmic_read_adc EXT5V_V   # the supply's voltage: about 5.1 V
  ```

  Anything other than `throttled=0x0` means the Pi has been short of power,
  or slowed down by heat, since it booted. Fix that first.
- Leave the PCIe link at the Pi 5's default, Gen 2 (5 GT/s). Do not add
  `dtparam=pciex1_gen=3` to `/boot/firmware/config.txt`. To check the link:

  ```bash
  sudo lspci -vv -s 0001:01:00.0 | grep -E 'LnkSta:|LnkCtl:'
  ```

  `LnkSta` reads `Speed 5GT/s` (lspci adds "downgraded": the drive could run
  faster). `LnkCtl` shows whether the link's own power saving (ASPM) is on:
  `ASPM L1 Enabled`, or `ASPM Disabled`.

#### 4.4.2 The drive: model, firmware and temperature

These read the kernel's own files, so they need no extra package:

```bash
cat /sys/class/nvme/nvme0/model /sys/class/nvme/nvme0/firmware_rev
cat /sys/class/nvme/nvme0/hwmon*/temp1_input   # in thousandths of a °C: 58850 is 58.85 °C
cat /sys/class/nvme/nvme0/hwmon*/temp1_max     # the drive's own warning limit
```

`temp1` is the drive's overall (Composite) temperature. Any other
`temp*_input` is one of the drive's own sensors, named in the matching
`temp*_label`: on the Kingston KC3000, `temp3` is its Sensor 2.

#### 4.4.3 Drive drops on the home test Pi

The home test Pi is the maintainer's bench Pi 5, with a relay HAT and no
water connected. It boots from a Kingston KC3000 512 GB, firmware EIFK51.2,
on a PCIe link at 5 GT/s x1 (Gen 2). Its drive has dropped out four times,
each time while the Pi sat idle:

| # | When | What was recorded |
|---|---|---|
| 1 | 2026-10-29, about 12:40 MDT | About 20 min after a dry run went idle. The journal was kept in memory only, so the Pi kept no record. |
| 2 | 2026-10-29, between 21:17 and 22:17 MDT | Dated by the Pi's hourly clock save (fake-hwclock). No record either. |
| 3 | 2026-11-01, 15:10:35 MST | 1 h 28 min after boot. Clean power: `throttled=0x0`, EXT5V 5.10 V. The drive warmed from 47 to 64 °C at idle in 70 min. Captured on another computer ([§4.4.4](#444-the-journal-and-a-capture-that-survives-a-drop)). |
| 4 | 2026-11-02, 18:02:46 MST | 22 min after a cold boot, **with APST off**: the parameter read 0 ([§4.4.5](#445-nvme-power-states-apst)). The last sample, at 18:01:48, read Composite 58.85 °C, Sensor 2 75.85 °C, `throttled=0x0`. ASPM L1 was still enabled on the link. Captured on another computer. |

Both captures show these kernel lines, in this order:

```text
nvme nvme0: controller is down; will reset: CSTS=0xffffffff, PCI_STATUS=0x10
nvme nvme0: Does your device have a faulty power saving mode enabled?
nvme nvme0: Try "nvme_core.default_ps_max_latency_us=0 pcie_aspm=off pcie_port_pm=off" and report a bug
nvme nvme0: Disabling device after reset failure: -19
```

then I/O errors, `Aborting journal on device nvme0n1p2-8`, and the root file
system remounted read-only.

Also on 2026-11-02, the soft reboot right after the APST edit gave a boot that
never became usable. Ping answered and port 22 was open, but SSH reset at the
key exchange for 30 min, and that boot left nothing on disk. A power cycle
brought the Pi back, with the parameter at 0.

What is known, as of 2026-11-03:

- **The cause is not known.** The kernel's hint names the drive's own power
  saving (APST) and the PCIe link's (ASPM, and the port's power management).
- **Turning APST off did not stop the drops** (drop 4). The PCIe link's power
  saving, heat, the PCIe adapter or its ribbon cable, and the drive itself are
  all still possible causes. No step in this section is a known fix.
- **The lab test Pi** (a relay rig that waters no animals) has the same drive
  model, with firmware EIFK31.7. It has run more than 25 h with APST off and
  no drive error, at about 37 °C. It had no recorded drop before either, but
  its unclean boots on 2026-10-15, 10-16 and 10-21 have no known cause: with
  the journal in memory, a drop leaves no trace on the Pi.
- **A third Pi** has the home test Pi's drive and firmware (EIFK51.2), and no
  recorded drop. Its journal, too, is kept in memory only.

#### 4.4.4 The journal, and a capture that survives a drop

On these Pis, Raspberry Pi OS keeps the system journal in memory only (its
default). After a power cycle the previous boot's messages are gone:
`journalctl -b -1` finds nothing. A persistent journal
(`Storage=persistent` in a journald drop-in) keeps them across boots. It is
an option, and which rigs get one is the owner's call. Even a persistent
journal cannot record the drive's own disappearance, because it is written
to that drive.

The record that survives a drop is a capture on another computer. `dmesg`
reads the kernel's buffer in memory, so its stream goes on while the drive is
gone:

```bash
ssh <user>@<pi> 'sudo dmesg -w --time-format iso' | tee -a nvme-capture.log
```

For a long test, add a `SAMPLE` line each minute with the time the Pi booted
(`up=`) and the drive's temperature. These lines stop when the Pi can no
longer run programs from its drive:

```bash
ssh <user>@<pi> '(while sleep 60; do echo "SAMPLE $(date -Is) up=$(uptime -s) temp=$(cat /sys/class/nvme/nvme0/hwmon*/temp1_input)"; done) & sudo dmesg -w --time-format iso' | tee -a nvme-capture.log
```

Keep the other computer awake (on a Mac, put `caffeinate -i` in front of
`ssh`). If the connection drops, run the command again: it replays the
kernel's buffer, and the timestamps tell repeated lines apart.

To read RRR's own output when it runs as `rrr.service`, use
`journalctl --user-unit=rrr`. With the journal in memory,
`journalctl --user -u rrr` finds nothing.

#### 4.4.5 NVMe power states (APST)

APST lets the drive drop into low-power states when it is idle. The kernel's
default leaves it on; `0` turns it off. To check:

```bash
cat /sys/module/nvme_core/parameters/default_ps_max_latency_us   # 100000: on (the default); 0: off
```

The installer does not change this today. APST is off, set by hand, on the
home test Pi and the lab test Pi. On any other rig, turn it off only with the
owner's OK. It is the first step the kernel's hint names, not a known fix
([§4.4.3](#443-drive-drops-on-the-home-test-pi)).

The setting goes in `/boot/firmware/cmdline.txt`, a single line the Pi reads
at boot. A broken line can stop the Pi booting, so back the file up first and
check the edit:

1. **Between schedules only:** no run active, none due within an hour, no
   priming valve open. Quit RRR (close its window, or
   `systemctl --user stop rrr` where it runs as the service).
   `pgrep -af 'python3 main.py'` prints nothing, and `16relind 0 read` prints
   `0`. Switch the valve supply off.
2. **Back up** to a file of its own, note its name, and count the lines:

   ```bash
   sudo cp /boot/firmware/cmdline.txt /boot/firmware/cmdline.txt.rrr-nvme-bak-$(date +%Y%m%d-%H%M%S)
   ls /boot/firmware/cmdline.txt*
   wc -l < /boot/firmware/cmdline.txt
   ```

   The backup is not `cmdline.txt.rrr-bak`: the installer's first run made
   that file, and it holds an older line. `wc -l` prints `0` on these Pis,
   because the file has no newline at its end.
3. **Edit with one command.** If the line has no
   `nvme_core.default_ps_max_latency_us` yet:

   ```bash
   sudo sed -i '1 s/$/ nvme_core.default_ps_max_latency_us=0/' /boot/firmware/cmdline.txt
   ```

   If it has one, set it to 0:

   ```bash
   sudo sed -i '1 s/nvme_core[.]default_ps_max_latency_us=[0-9]*/nvme_core.default_ps_max_latency_us=0/' /boot/firmware/cmdline.txt
   ```

4. **Check before any reboot**, with your backup's name in place of `BACKUP`:

   ```bash
   wc -l < /boot/firmware/cmdline.txt
   diff <(tr ' ' '\n' < BACKUP; echo) <(tr ' ' '\n' < /boot/firmware/cmdline.txt; echo)
   ```

   `wc -l` prints the same number as in step 2. `diff` shows the new token
   added (or, after the second command, changed from its old value), and
   nothing else. With the home test Pi's line it shows:

   ```text
   11a12
   > nvme_core.default_ps_max_latency_us=0
   ```

   Without the two `echo`s, the line's last token reads as changed, because
   it has no newline. Anything else:
   `sudo cp BACKUP /boot/firmware/cmdline.txt`, and stop.
5. **Reboot** as in
   [§4.4.7](#447-the-reboot-after-an-edit-and-a-pi-that-does-not-boot). Then
   the `cat` above prints `0`. Start RRR the rig's usual way, and switch the
   valve supply on only once `16relind 0 read` prints `0`.

**To undo the edit:** `sudo cp BACKUP /boot/firmware/cmdline.txt`, then reboot
as in [§4.4.7](#447-the-reboot-after-an-edit-and-a-pi-that-does-not-boot).

#### 4.4.6 If a drive keeps dropping

Each step is the owner's choice, Pi by Pi:

- **(a) The hint's other two parameters,** `pcie_aspm=off pcie_port_pm=off`,
  with all five steps of [§4.4.5](#445-nvme-power-states-apst): between
  schedules with the valve supply off, the backup, a one-command edit, the
  check and the reboot. If the line has neither yet, step 3's command is:

  ```bash
  sudo sed -i '1 s/$/ pcie_aspm=off pcie_port_pm=off/' /boot/firmware/cmdline.txt
  ```

  The `diff` then shows those two tokens added, and nothing else. After the
  reboot, `LnkCtl` ([§4.4.1](#441-power-and-the-pcie-link)) should read
  `ASPM Disabled`; if it does not, tell the maintainer. Then leave the Pi
  idle for 72 h with the `SAMPLE` capture of
  [§4.4.4](#444-the-journal-and-a-capture-that-survives-a-drop) running. It
  passes if the `SAMPLE` lines cover 72 h of one boot (the same `up=` time
  throughout) and no `controller is down` line appears. If the drive's
  temperature reaches its `temp1_max`
  ([§4.4.2](#442-the-drive-model-firmware-and-temperature)), stop and tell
  the owner.
- **(b) Reseat the PCIe ribbon cable, and fit a heatsink on the drive.**
- **(c) Boot from an SD card or a USB SSD** instead of the NVMe drive.

#### 4.4.7 The reboot after an edit, and a Pi that does not boot

After any edit of `cmdline.txt`, someone stays at the rig for the reboot, with
the valve supply off.

1. `sudo reboot`. The desktop and SSH should be back within about 2 minutes.
2. If they are not (for example, ping answers but SSH resets at the key
   exchange), **power-cycle the Pi**: unplug its USB-C power, wait 10 s, plug
   it back in. On 2026-11-02 a cold boot brought the home test Pi back after
   such a reboot ([§4.4.3](#443-drive-drops-on-the-home-test-pi)).
3. Only if it still does not boot, copy the backup back from another
   computer. Power the Pi off, take the NVMe drive out and put it in the USB
   NVMe adapter ([§2.1](#21-compute-and-control)). On the other computer,
   open the drive's small boot partition (`bootfs`), copy the
   `cmdline.txt.rrr-nvme-bak-…` file over `cmdline.txt`, eject the drive, put
   it back in the Pi and boot. Or, only if the Pi's boot order tries the SD
   card before NVMe, boot it from a prepared Raspberry Pi OS SD card and make
   the same copy on the NVMe drive's boot partition (`/dev/nvme0n1p1`).
   `rpi-eeprom-config` shows the order as `BOOT_ORDER`: read its digits from
   the right, where `1` is the SD card and `6` is NVMe. Read it before the
   reboot of step 1, while the Pi still runs.

#### 4.4.8 Shutting down, and unattended runs

- **Never log out, reboot or shut down a rig while a schedule runs or a
  priming valve is open.** Press **Stop** first, or **CLOSE ALL RELAYS** in
  **Settings → Priming** while priming. RRR does not switch its relays off
  when the desktop session ends or the Pi shuts down, and what the relays do
  through a reboot or a shutdown has not been measured yet.
- **Start RRR from its desktop icon, or as `rrr.service`.** An RRR started
  with `~/.local/bin/rrr` in a terminal ends when that terminal closes, and
  leaves its relays as they were.
- **Unattended runs.** No software can be relied on to close an open valve
  once the Pi or its drive has gone. Fit a switch, or a plug the operator can
  pull, on the valve supply, within reach of where the operator stands. A
  hardware fail-safe in the valve supply (for example a watchdog relay in
  series with it) is the only thing that would close a valve with nobody
  there; no rig has one yet.

### 4.5 A frozen rig: what to do

**Print this section on one page and tape it to every rig that waters
animals.** Use it when RRR or the desktop stops answering, or anything shows
`Input/output error`. The relay HAT keeps every relay as it was: **an open
valve stays open**.

1. **Switch the valve power supply off**, or pull its plug. Always first.
   Note the time.
2. **Stop RRR.** If the desktop answers and nothing shows
   `Input/output error`, run `pkill -9 -f 'python3 main.py'` in a terminal.
   Otherwise **power-cycle the Pi**: unplug its power for 10 s.
3. **Let one RRR start.** Wait 10 s (after a power cycle, 10 s after the
   desktop is back), then run `pgrep -af 'python3 main.py'`. A line means
   RRR is starting by itself: do not start another. No line: start RRR from
   its desktop icon, not a terminal. RRR switches every relay off as it
   starts. Do not stop it until its main window has been open 10 s: two
   failed starts in a row roll RRR back to its previous version. If it will
   not start, keep the valve power off and call the maintainer.
4. **Check the database** before the next Run. Type these four lines in a
   terminal:

   ```bash
   ~/rrr/shared/venv/bin/python3 -c "import os, sqlite3; \
   p = os.path.expanduser('~/rrr/shared/data/rrr_database.db'); \
   db = sqlite3.connect('file:' + p + '?mode=ro', uri=True); \
   print(db.execute('PRAGMA integrity_check').fetchone())"
   ```

   It must print `('ok',)`. If it ends with
   `attempt to write a readonly database`, RRR has not opened the database
   since the crash: go back to step 3, then check again. Anything else: run
   no schedule; the maintainer restores the database from its last backup.
5. **After a power cycle**, on a rig with a persistent journal, keep the
   output of `journalctl -b -1 -k | tail -50` for the maintainer.
6. **Check what each animal received.** Log in and look for red cells in the
   Animals tab. After a disk fault the delivery log can miss deliveries:
   check each animal before giving more. Give any remainder only as a new
   schedule; never resume the stopped one.
7. **Reconnect the valve power last**, once every relay is off: all relay
   LEDs on the HAT dark, or `16relind 0 read` prints `0` (`16relind 1 read`
   for a second HAT). If a relay is on, or `pgrep -af 'python3 main.py'`
   prints nothing, power-cycle the Pi (every relay drops) and go back to
   step 3.

---

## 5. 16-Relays HAT — Stacking and Jumpers

The full vendor manual is bundled at
[16-RELAYS-UsersGuide_d5e24457-bdd9-4e16-a307-7f90bbd668bb.pdf](16-RELAYS-UsersGuide_d5e24457-bdd9-4e16-a307-7f90bbd668bb.pdf).
Read it once; the summary below covers only the RRR-specific choices.

### 5.1 Stack-level jumpers (J2)

For a single-HAT build, set **stack level 0** (all three stack-level jumpers
OFF). The HAT responds at I²C address `0x27`. If you stack a second HAT, set
the second board to stack level 1 (jumper 0 ON, jumpers 1 and 2 OFF), address
`0x26`. See pages 6–7 of the vendor manual for the full table.

### 5.2 Other jumpers

- **LED-SEL (rightmost on J2):** Leave at default; switches the on-board LED
  bank between relays 1–8 and 9–16 for visual diagnostics.
- **RS-485 ENB and TERM:** Leave OFF. RRR does not use RS-485 and leaving the
  jumper on holds the Pi's UART, which can interfere with serial debug.

### 5.3 Physical install

1. Pi is powered OFF and unplugged.
2. Install the four M2.5 × 19 mm standoffs in the Pi's mounting holes (nuts
   on the underside).
3. Seat the HAT firmly onto the Pi's 40-pin GPIO header. The header pins
   should disappear fully into the HAT's socket — a partial seat is the most
   common reason for "HAT not detected".
4. Secure with the four M2.5 × 5 mm screws into the standoffs.
5. **Do not connect the HAT's auxiliary +5 V terminal block yet.** The Pi
   powers the HAT logic over the GPIO header for bring-up; the auxiliary
   power is only needed if you want to power the Pi *from* the HAT's terminal
   (we do not).

---

## 6. Electrical System — Power and Common Ground

This section is the part most likely to go wrong. Wire it slowly, label
everything, and use a multimeter to verify continuity before applying power.

### 6.1 Topology overview

```
                              ┌──────────────────────┐
                              │   12 V DC PSU        │  (wall plug)
                              │   ≥ 10 A regulated   │
                              └─────────┬────────────┘
                                        │  (DC barrel out)
                                        ▼
                              ┌──────────────────────┐
                              │  1×8 DC splitter ×2  │  (8 outputs each = 16 total)
                              └─────────┬────────────┘
                                        │  (one barrel-jack per valve)
                                        ▼
                              ┌──────────────────────┐
   Relay HAT COM (per relay)──┤      Each valve      │
                              │   (+12 V from        │
                              │   splitter, switched │
                              │   by relay)          │
                              └─────────┬────────────┘
                                        │  (valve return)
                                        ▼
                              ┌──────────────────────┐
                              │  Common Ground Bus   │ ◄── Relay HAT GND
                              │  (§6.3)              │ ◄── PSU return
                              └──────────────────────┘
```

### 6.2 Power budget

Compute total current before choosing a PSU:

```
I_total = N_valves × I_per_valve_holding_current
        + I_Pi_5         (≈ 5 A peak on its own 5 V rail — separate supply)
        + I_HAT_logic    (≈ 10 mA, negligible)
```

For 16 valves at, say, 250 mA holding current each: `I_total = 16 × 0.25 = 4 A`.
A 10 A 12 V supply gives 2.5× headroom, which is the minimum for inductive
loads (valves) where inrush can briefly hit 2–3× holding current.

> **TBD.** Confirm the per-valve holding current from the valve datasheet
> before ordering the PSU.

### 6.3 Common-ground bus

Every DC return in the system — the relay HAT's GND pin, the PSU's negative
output, and every valve's return lead — must meet at a single physical point.
This is the **common ground**. Without it, relays either do not switch or
chatter, and the Pi can latch up.

#### 6.3.1 Preferred — DIN-rail terminal block or copper bus bar

1. Mount a single ground terminal block (e.g., Phoenix Contact UT 4 PE) on a
   short section of DIN rail attached to your backboard.
2. Run a single 18 AWG wire from the PSU's negative terminal to one slot.
3. Run a single 22 AWG wire from the relay HAT's GND header pin (any GND
   pin on the Pi 5 GPIO header, since the HAT shares it) to another slot.
4. Run every valve-return wire to its own slot (one per slot): 16 on the
   shared-manifold rig, 15 on the independent rig.
5. Label every slot. Take a photo.

This is electrically clean, mechanically tidy, and the obvious first thing a
future maintainer will understand.

#### 6.3.2 Alternative — energized power strip as ground bus (current practice, not recommended long-term)

This is the technique currently in use on existing RRR builds. It works, but
it has caveats that make the [§6.3.1](#631-preferred--din-rail-terminal-block-or-copper-bus-bar)
approach strictly better for new installs.

**What it does:** All DC return wires are soldered to the **ground (earth)
pin** of a male NEMA 5-15P plug body. The plug is inserted into a standard
6-outlet power strip whose ground bar internally joins every outlet's ground
pin and ties them to building earth via the wall outlet's third prong.

**Why it works:** Building earth is, by code, a low-impedance reference that
all DC returns can share. The power strip simply rents you a copper bar that
happens to already be wired to earth.

**Why it is risky:**

1. **You are tying your DC return to building earth at one specific point.**
   If anything else in your fluid path (a metal reservoir, a grounded sensor,
   a USB connection to a grounded laptop) is *also* tied to earth elsewhere,
   you have a ground loop. Ground loops cause noise on sensor reads and, in
   pathological cases, current flow through unintended paths.
2. **The hot and neutral pins of the plug body MUST be left unconnected and
   physically insulated.** A loose strand of solder bridging the ground pin
   to neutral energizes your entire DC return at 120 V AC. This will destroy
   the Pi, the HAT, and every valve, and present a shock hazard.
3. **The power strip must be plugged into a properly wired three-prong
   outlet** with a verified ground. Cheap outlet testers from any hardware
   store will confirm this.
4. **A soldered breadboard ground rail is NOT a substitute.** We tried it;
   the rail current capacity was insufficient for the combined valve return
   currents and produced intermittent valve behavior.

**Procedure if you must use this approach:**

1. Buy two male NEMA 5-15P replacement plug ends from any hardware store
   (Home Depot, Walmart, etc.). They unscrew to expose three terminals
   labeled HOT, NEUTRAL, and GROUND.
2. **Plug 1 (PSU side):** Solder together the PSU negative lead, the relay
   HAT GND lead, and any other "power-supply-side" returns. Heat-shrink the
   joint. Strip ~10 mm of one end and secure it under the GROUND screw of
   the plug body. Verify HOT and NEUTRAL terminals are empty and the screws
   are tight against the empty terminal so they cannot work loose. Reassemble
   the plug body.
3. **Plug 2 (valve side):** Same procedure with every valve return lead (16 on
   the shared-manifold rig, 15 on the independent rig) joined to a single lead
   going to the GROUND pin.
4. Plug both into the same power strip. The power strip's ground bar joins
   the two plug-side return bundles.
5. Plug the power strip into a verified-grounded wall outlet.
6. **Before applying DC power**, use a multimeter on continuity mode to
   verify:
   - Continuity between plug 1's GROUND pin and plug 2's GROUND pin (should
     beep through the power strip).
   - **No continuity** between either plug's GROUND pin and either plug's
     HOT or NEUTRAL pin. If you hear a beep, stop and rebuild — you have a
     short.

**Migration plan.** If your current build uses the power-strip technique, it
is safe to keep running, but the next time you have the device on the bench
for any other reason, swap to a DIN-rail terminal block per
[§6.3.1](#631-preferred--din-rail-terminal-block-or-copper-bus-bar). It is a
30-minute job and removes all of the caveats above.

---

## 7. Valve Wiring

Wire one valve end-to-end and bring it up before wiring the rest. Catching
a wiring error on valve 1 is a five-minute fix; catching it after wiring all
16 is two hours.

### 7.1 Per-valve wiring

For each valve, in order from relay channel 1 through channel 15 (animal
channels) and then, on the shared-manifold rig only, channel 16 (master). On
the independent rig leave channel 16 unwired:

1. **Identify the relay channel's NO and COM terminals** on the HAT's
   pluggable terminal block. NO is "normally open" (the side the valve sees
   only when the relay activates). COM is "common" (always connected to the
   downstream side of the relay). Pairs of two relays share a COM pin — see
   the board-layout diagram on page 6 of the vendor manual.
2. **Run a wire from one output of the DC splitter to the COM terminal of
   this relay channel.** This carries +12 V from the PSU through the splitter
   to the relay's input side. Use red wire.
3. **Run a wire from the relay's NO terminal to one lead of the valve.** Use
   red wire. Terminate it in the male barrel-jack connector that mates with
   the valve's pigtail.
4. **Run a wire from the valve's other lead to the common ground bus** (per
   [§6.3](#63-common-ground-bus)). Use black wire.
5. **Label both ends of every wire** with the channel number (e.g., `R03+`
   and `R03-` for relay 3).

### 7.2 Why the master valve is on channel 16

On the shared-manifold topology (the default) the master is software-treated
as a global shutoff: the application opens it before any animal valve and
closes it after the last one in every delivery and calibration run, and in
the Priming tab a cage valve opens only while the master is open. On the
independent topology (below) RRR never drives it. Channel 16 is the default
master: `global_master_relay_id = 16` in
[`Project/controllers/system_controller.py`](../controllers/system_controller.py),
stored per device in the `system_settings` table. The cage map skips that one
relay, so a single HAT gives 15 animal channels (1–15); a second HAT adds 16
more (relays 17–32 are all animal channels — the master is global, not per
HAT). Remap only if you have a hardware reason to, and change the setting
before you rewire: `SolenoidController` takes the id from the setting and has
no default of its own.

> **Independent setup (one syringe and one valve per animal, no manifold, no
> master).** From v1.21.0 the valve topology is chosen in RRR: log in, open
> **Settings → Delivery → Valve Topology** (in *Solenoid Mode Settings*, shown
> while Hardware Mode is *Solenoid*), click **Independent (one syringe and one
> valve per animal)** and confirm. The choice is greyed out, and refused with
> *Cannot Change Topology*, while a schedule, a priming session or a
> calibration is running. Confirming the change (**Restart RRR**; **Cancel**
> keeps the old one) restarts RRR, so priming, calibration and schedules all
> use the new topology; log in again afterwards. If RRR cannot restart itself
> it says so: close and reopen RRR before priming. RRR records who made the
> change, and when, in its database (the `logs` table, action
> `valve_topology`), and prints a `[TOPOLOGY] Valve topology changed in
> Settings: …` line with the user's name just before it restarts (under
> `rrr.service` the line is in the journal).
>
> With the app closed (its window, or `systemctl --user stop rrr.service`
> where it runs as the user service), the command-line tool does the same,
> without the `logs` record:
>
> ```bash
> cd ~/rrr/current/Project
> ~/rrr/shared/venv/bin/python3 tools/set_valve_topology.py independent --yes
> ~/rrr/shared/venv/bin/python3 tools/set_valve_topology.py   # prints: current valve_topology: independent
> ```
>
> and then start the app again. The tool prints the database it is acting
> on, never creates one, and refuses to write while it can see the app
> running (a running app would save its old value back over the new one).
> On the independent topology the Priming tab shows no master-valve controls.
> Deliveries pulse the cage valve only, with no manifold prime, and relay
> 16 is never driven. It is, however, still **reserved** in this release —
> an independent rig gets 15 animal channels on the first HAT (and 16 on
> each additional HAT, since only relay 16 is reserved), and channel 16
> should stay unwired until a later release lifts the reservation.
>
> On a release before v1.21.0, or before the setting is applied, the
> shared-manifold code energises relay 16 for the **whole** of every
> delivery (a 200 ms prime, then held open across every pulse — seconds to
> tens of seconds depending on the interval), for the whole of a calibration
> run, and in the priming tab from Open Master until Close Master. So on a
> rig without a master valve, leave channel 16 unwired. Every other step in
> this guide applies, following its notes for the independent rig: one relay
> per animal valve, one syringe per animal.
>
> Never set `independent` on a rig that has a master valve: the master would
> never open and every delivery would be logged as a full dose while the
> animal received nothing.
>
> After switching, calibrate every animal channel in **Settings →
> Calibration**. A calibration measured under the other valve topology shows
> **Stale** there (one saved before v1.21.0 counts as shared manifold). In
> solenoid mode (the default) **Run** refuses a schedule that waters a
> cage with no usable calibration measured under this device's valve
> topology (*Valve calibration needed*), so a Stale cage cannot be watered
> until it is recalibrated. **Calibrate All Uncalibrated** takes the Stale
> and Invalid cages as well as the uncalibrated ones.

### 7.3 Verify before powering

With the DC supply **still unplugged from the wall**:

- Every valve return lands on the common ground bus (visual inspection).
- Every relay COM has +12 V wired in (from a splitter output).
- No exposed conductors anywhere. Heat-shrink or insulating cap on every
  joint.
- The HAT is fully seated on the Pi's GPIO header.

---

## 8. Tubing and Reservoir

> **TBD — exact tubing specifications pending lab confirmation.** Update this
> section with the chosen inner diameter, outer diameter, material, and the
> per-cage length once the lab settles on a part.

General guidance:

1. **Shared-manifold rig:** mount the reservoir(s) above the highest valve.
   Gravity feed simplifies priming and prevents the master valve from running
   dry. **Independent rig:** mount each animal's syringe above its valve and
   note its fill level (whether the level changes the dose is still being
   measured; see [TOPOLOGY_VALIDATION.md](TOPOLOGY_VALIDATION.md) C8).
2. Cut tubing per fluid path, using the layout sketch from
   [§3](#3-plan-the-installation-before-cutting-wire). **Shared manifold:**
   reservoir → master valve → manifold → each animal valve → each cage spout.
   **Independent:** each syringe → its animal valve → its cage spout.
3. Use barbed fittings sized for your tubing's inner diameter. Push the
   tubing fully onto the barb; secure with a small zip tie or clamp if your
   delivery pressure exceeds gravity-fed.
4. Prime the lines before first delivery via **Settings → Priming** in the
   RRR application. See [PRIMING_FEATURE_DOCUMENTATION.md](PRIMING_FEATURE_DOCUMENTATION.md).
5. Inspect every joint for leaks after priming. A drip on a powered HAT will
   end your day.
6. **Independent rig:** check every syringe line daily; a primed line holds
   about three days, so prime again any line left idle over a long weekend
   before its animal depends on it.

---

## 9. First Power-On and Bring-Up Test

### 9.1 Pre-flight checklist

Verify each item; do not power on until all are checked.

- [ ] [§3](#3-plan-the-installation-before-cutting-wire) layout sketch
      matches what is on the wall.
- [ ] [§4](#4-raspberry-pi-and-operating-system) Pi boots to desktop and
      `/dev/i2c-1` exists.
- [ ] [§5](#5-16-relays-hat--stacking-and-jumpers) HAT seated, stack-level
      jumpers set, RS-485 jumpers OFF.
- [ ] [§6.3](#63-common-ground-bus) common ground bus continuity verified
      with multimeter; no short between ground and 12 V.
- [ ] [§7](#7-valve-wiring) every valve wired, labelled, insulated: 16 per HAT
      on the shared-manifold rig (15 animal + master on relay 16); on the
      independent rig 15 on the first HAT with relay 16 left unwired.
- [ ] [§8](#8-tubing-and-reservoir) tubing routed, reservoir (or every
      syringe) mounted, but **empty** for first bring-up.
- [ ] Two people present: one at the wall plug, one watching the boards.

### 9.2 Power-on sequence

Apply power in this order. Pause between each step and watch for smoke,
unexpected LEDs, or anything getting warm.

1. Plug in the Pi 5's USB-C PSU. Pi boots to desktop.
2. Plug in the 12 V DC supply (still no water). Relay HAT's power LED
   illuminates. **No relay LEDs should be on** in this quiescent state. If
   any are, the wiring has a short — disconnect immediately and recheck.
3. Open a terminal on the Pi and verify the HAT:

   ```bash
   sudo i2cdetect -y 1
   # Expected: device responds at 0x27 (stack level 0)
   ```

4. Click each relay individually using the vendor CLI (the RRR installer
   sets this up; for a pre-install dry run, follow the vendor manual's
   software setup section). With no water in the system, a successful click
   should:
   - Light the relay's status LED
   - Produce an audible click from the valve
   - Light extinguishes and valve clicks back when relay is released

5. If every wired relay clicks its valve cleanly (on the independent rig
   relay 16 has no valve: its LED lights and nothing else happens), fill the
   reservoir (or the syringes) and proceed to
   [§10](#10-software-install-and-verification).

---

## 10. Software Install and Verification

Once the hardware passes [§9](#9-first-power-on-and-bring-up-test), install
the RRR application:

```bash
curl -fsSL https://raw.githubusercontent.com/Corticomics/rodRefReg/main/bootstrap.sh | bash
```

The installer enables I²C, installs the relay HAT driver, sets up a systemd
user service, and verifies every dependency. Full install details, flags,
and headless operation are in the [project README](../../README.md).

After install:

1. **Launch the application** from the desktop icon or `~/.local/bin/rrr`.
2. **Set the valve topology** to match the plumbing: log in, open
   **Settings → Delivery → Valve Topology** and choose **Shared manifold
   (master valve)** (the default) or **Independent (one syringe and one valve
   per animal)**. Do this before priming and calibrating: each calibration
   records the topology it was measured under, and one measured under the
   other valve topology shows **Stale**. Confirming a change restarts RRR.
3. **Open Settings → Priming** and prime every line. See
   [PRIMING_FEATURE_DOCUMENTATION.md](PRIMING_FEATURE_DOCUMENTATION.md).
4. **Calibrate every valve.** See [CALIBRATION_QUICK_START.md](CALIBRATION_QUICK_START.md).
   This step is mandatory: in solenoid mode (the default) **Run**
   refuses a schedule that waters a cage with no usable calibration measured
   under this device's valve topology (*Valve calibration needed*), because
   RRR cannot know how much water a pulse gives without one.
5. **Run a 0.5 mL test schedule** on a single cage and weigh the output to
   confirm calibration accuracy is within ±5 %. The Animals tab's **Last
   schedule delivered amount** shows the volume RRR credited (whole pulses
   × the cage's calibration): compare the weighed volume with it.

---

## 11. Troubleshooting

| Symptom | First thing to check |
|---|---|
| HAT not detected (`i2cdetect` shows nothing at 0x27) | HAT fully seated on GPIO header; stack-level jumpers correct; `/dev/i2c-1` present; user in `i2c` group (`groups $USER`). |
| Relay clicks but valve does not open | +12 V present at COM terminal under load (measure with multimeter while relay is active); valve return reaches common-ground bus; PSU not sagging. |
| Multiple valves open when only one is requested | Common-ground continuity is bad; a relay's NO and another relay's COM are shorted; rewire and re-verify [§7.3](#73-verify-before-powering). |
| Relay LEDs flicker rapidly at idle | Wiring short between +12 V and ground somewhere; disconnect mains immediately and trace with a multimeter on continuity. |
| Pi reboots when valves activate | PSU undersized or the Pi is sharing power with the valve rail. Pi 5 must be on its own 27 W USB-C PSU; valves on their own 12 V supply. |
| Sensor noise / erratic flow readings | Likely ground loop. Check [§6.3.2 caveat 1](#632-alternative--energized-power-strip-as-ground-bus-current-practice-not-recommended-long-term). |
| **Run** shows *Valve calibration needed* or *Cage not on this device* and the schedule does not start | A cage the schedule waters has no calibration, one marked **Invalid** (volume per pulse or pulse width missing, zero or invalid), or one marked **Stale** (measured under the other valve topology; one saved before v1.21.0 counts as shared manifold); or the schedule names a cage this device does not have. Calibrate the listed cages in **Settings → Calibration** (or edit the schedule), then press **Run** again. See [CALIBRATION_QUICK_START.md](CALIBRATION_QUICK_START.md). |
| Delivered volume is well off target | The cage's calibration no longer matches its valve or line (a valve, tubing, needle or supply change, or air in the line): prime the line, recalibrate that cage per [CALIBRATION_QUICK_START.md](CALIBRATION_QUICK_START.md), and weigh a test dose. Each cage delivers at the pulse width and interval it was calibrated at (the **Profile** column in **Settings → Calibration**). |
| Terminal tab shows `[VALVE ERROR] cage N: … did not reach its relay; delivery stopped`, and the ledger shows `failed` / `partial` rows | A relay write did not reach its HAT: a HAT that was not found at start-up, a relay on a HAT that is missing, or an I²C error. From v1.21.0 the delivery stops there instead of counting the pulse. Only pulses whose valve opened are credited (a pulse whose close got through only on a retry is credited with the time its valve stayed open), and the retry 30 s later asks for the rest. A pulse that fails for any other reason also ends the delivery (`[VALVE ERROR] cage N: pulse K failed: …`). Check `i2cdetect -y 1` and run the bring-up test in [§9](#9-first-power-on-and-bring-up-test). RRR sets the HATs up only when it starts, so after fixing a HAT that was missing, **close and reopen RRR**; until then every delivery to it keeps failing. If deliveries keep failing, the schedule stops ("Deliveries kept failing: check the relay HAT … and the flow sensor"). |
| `[VALVE CRITICAL] … OPEN` (for pump relays, `… ON`), **Emergency Stop Failed**, **Relays Not Confirmed Off** or **Delivery Worker Did Not Stop** | A close, or the all-relays-off command, did not reach a HAT, or a valve's relay has not answered since the run started, so that valve may still be open; or the schedule's delivery did not stop and may open a valve again. **Disconnect the valve power supply first**, then check the relay HAT and its I²C connection as above. During a schedule press **Stop**: CLOSE ALL RELAYS is greyed out while a schedule runs. When no schedule runs, **Settings → Priming → CLOSE ALL RELAYS** switches every relay off again. A stopped schedule does not resume: Run starts it over, after asking (staggered: every animal's whole dose again; instant: delivery times that have passed are skipped), so check what each animal has received (the Animals tab's **Last schedule delivered amount**, or `tools/gravimetric_check.py daily`) before running it again; to give only the rest, create a schedule for the amount the red cell's tooltip gives, at the schedule wizard's two decimals (for an instant schedule, check the delivery log first). When a later close gets through, the Terminal tab shows `[VALVE OK] The cage N valve closed after all; …`. |
| Run, priming and calibration greyed out with *Unavailable while an unconfirmed emergency stop is in progress* | A Stop or a CLOSE ALL RELAYS could not confirm every relay off, or the schedule's delivery did not stop. **Disconnect the valve power supply first**, then check the relay HAT and its I²C connection, then press **Settings → Priming → CLOSE ALL RELAYS**: once every relay is confirmed off and the delivery has stopped, Run, priming and calibration come back (if it says the delivery worker has not stopped, wait a few seconds and press it again). Or close and reopen RRR (if it will not quit, restart the Raspberry Pi). With a relay HAT missing since RRR started, every Stop does this: restart RRR, then fix the HAT and restart again, or set the number of HATs the rig has with **Change Relay Hats**. |
| The Animals tab shows **Interrupted · ? / … mL** in red | RRR closed or lost power during that schedule, so the amount delivered was not recorded. Run the command in the cell's tooltip in a terminal on the Pi (`tools/gravimetric_check.py daily --since <day> --cage <cage>`): it totals what that cage received each day from that day on. |
| Water leaking onto HAT | Power off immediately. Dry fully (24 h, no heat). Inspect for corrosion on terminals before re-powering. |
| RRR or the desktop is frozen, or a window or command shows `Input/output error` | **Disconnect the valve power supply first**: the HAT keeps its relays as they were, so a valve may be held open. Then follow [§4.5](#45-a-frozen-rig-what-to-do). On a Pi that boots from NVMe, the drive may have dropped out: see [§4.4](#44-a-pi-5-on-nvme). |

---

## 12. References

- [16-RELAYS Vendor User's Guide](16-RELAYS-UsersGuide_d5e24457-bdd9-4e16-a307-7f90bbd668bb.pdf)
  — Sequent Microsystems, version 1.0
- [Raspberry Pi 5 documentation](https://www.raspberrypi.com/documentation/computers/raspberry-pi-5.html)
- [Raspberry Pi OS Bookworm release notes](https://www.raspberrypi.com/news/bookworm-the-new-version-of-raspberry-pi-os/)
- [CALIBRATION_QUICK_START.md](CALIBRATION_QUICK_START.md) — per-valve
  calibration procedure (run after hardware build).
- [VALVE_CALIBRATION_GUIDE.md](VALVE_CALIBRATION_GUIDE.md) — technical
  reference behind the calibration wizard.
- [PRIMING_FEATURE_DOCUMENTATION.md](PRIMING_FEATURE_DOCUMENTATION.md) —
  priming sequence and safety interlocks.
- [DEVELOPMENT.md](DEVELOPMENT.md) — software architecture (for developers
  extending the system).
- [MAINTENANCE.md](MAINTENANCE.md) — release and update procedures.

---

## Items pending lab confirmation (TBD)

The following are flagged in-line above. Update this list as decisions are
made:

- [ ] Solenoid valve make and model (currently evaluating cheaper alternatives
      to Parker Series 3).
- [ ] Per-valve holding current, used in [§6.2 Power Budget](#62-power-budget).
- [ ] 12 V vs. 24 V DC PSU (depends on chosen valve).
- [ ] Exact PSU make and model with confirmed continuous current rating.
- [ ] Wall-mount backplate STL file (referenced in
      [§2.5](#25-mechanical--mounting) and [§3](#3-plan-the-installation-before-cutting-wire)).
- [ ] Tubing inner diameter, outer diameter, material, per-cage length
      (referenced in [§2.6](#26-tubing-and-fluid-path) and [§8](#8-tubing-and-reservoir)).
