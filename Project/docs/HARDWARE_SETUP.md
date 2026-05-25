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

---

## 2. Bill of Materials

Quantities are for a single 15-cage device (1 HAT × 16 relays = 1 master + 15
animal channels). Scale up for stacked HATs.

### 2.1 Compute and control

| Item | Qty | Notes |
|---|---|---|
| Raspberry Pi 5 (4 GB or 8 GB) | 1 | Pi 4 also works; this guide targets Pi 5. |
| Raspberry Pi 5 official 27 W USB-C PSU | 1 | Required for Pi 5; under-powered PSUs cause USB resets. |
| microSD card, 32 GB or larger, A2/Class 10 | 1 | Imaged with Raspberry Pi OS Bookworm 64-bit. See [§4](#4-raspberry-pi-and-operating-system). |
| HDMI cable (micro-HDMI to HDMI), USB keyboard, USB mouse, monitor | 1 each | For initial OS setup only. After install you can run headless. |
| Sequent Microsystems *Sixteen Relays 2 A / 24 V 8-Layer Stackable HAT* | 1 (up to 8 stackable) | See bundled [16-RELAYS-UsersGuide](16-RELAYS-UsersGuide_d5e24457-bdd9-4e16-a307-7f90bbd668bb.pdf). |

### 2.2 Solenoid valves

The system is valve-agnostic as long as the valve can be switched by a
single-pole relay rated 2 A at 24 V (the HAT's relay rating). Historical
RRR builds used Parker Series 3 valves; cheaper third-party valves are
currently under evaluation.

| Item | Qty | Notes |
|---|---|---|
| 12 V DC (or 24 V DC) normally-closed solenoid valve, ≤ 2 A holding current, with female 2.1 × 5.5 mm DC barrel-jack pigtail or equivalent leads | 16 per HAT (1 master + 15 animal) | **TBD — exact model pending lab confirmation.** Confirm voltage matches your PSU. Normally-closed (NC) is required so a power loss closes the valve. |

> **Why 16, not 15?** The master valve is wired in series upstream of the
> animal valves and provides a single shutoff point. Reserve relay channel 1
> for the master and relays 2–16 for animal channels.

### 2.3 DC power and distribution

| Item | Qty | Notes |
|---|---|---|
| 12 V DC regulated power supply, ≥ 10 A continuous (or 24 V DC if your valves require it) | 1 | **TBD — confirmed amperage pending valve selection.** See [§6.2 Power Budget](#62-power-budget) for the calculation. |
| 1-input × 8-output DC power splitter, 2.1 × 5.5 mm barrel jacks (e.g., Amazon B01H4VEB6G or equivalent) | 2 | One splits PSU → 8 valves; with 16 valves you need two splitters in parallel from the PSU. Verify the splitter's wire gauge supports your total current. |
| Male 2.1 × 5.5 mm DC barrel-jack connectors with screw terminals (e.g., DAYKIT B01J1WZENK or equivalent) | 16 | One per valve. The valve's two leads land in these connectors. |
| 22 AWG hookup wire, stranded, two colors (red for +12 V, black for ground) | ~5 m each | **Measure your run lengths in [§3](#3-plan-the-installation-before-cutting-wire) before cutting.** |
| Wago lever-nut connectors or equivalent (optional) | as needed | Cleaner than wire nuts for branching the splitter output. |

### 2.4 Common-ground bus

This is the most error-prone subsystem. Read [§6.3](#63-common-ground-bus) in
full before buying parts.

| Item | Qty | Notes |
|---|---|---|
| **Preferred:** DIN-rail grounding terminal block (e.g., Phoenix Contact UT 4 PE or equivalent), or copper bus bar with insulated standoffs | 1 | Purpose-built, safe, and labelable. |
| **Alternative (what we currently use):** 6-outlet surge-protected power strip + 2 × male NEMA 5-15P plug bodies (replaceable plug ends from a hardware store) | 1 strip, 2 plug bodies | See the safety caveats in [§6.3.2](#632-alternative-energized-power-strip-as-ground-bus-current-practice-not-recommended-long-term) — this approach works but ties your DC return to building earth, which has tradeoffs. |
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
| Water reservoir (10 mL per cage mount provided as STL) | 1+ | See [10ml_Water_Reservoir_Mount_x4.stl](STL%20Files/10ml_Water_Reservoir_Mount_x4.stl). |
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
6. **Decide your master-valve location.** The master sits between the
   reservoir and the splitter feeding the animal valves. Wire it to relay
   channel 1.

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
4. Run all 16 valve-return wires to their own slots (one per slot).
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
3. **Plug 2 (valve side):** Same procedure with all 16 valve return leads
   joined to a single lead going to the GROUND pin.
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

For each valve, in order from relay channel 1 (master) through channel 16:

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

### 7.2 Why master valve on channel 1

The master is software-treated as a global shutoff. The application opens it
before any animal valve and closes it after the last one in any delivery
cycle. Channel 1 is the default master in
[`Project/drivers/solenoid_controller.py`](../drivers/solenoid_controller.py)
— remap only if you have a hardware reason to.

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

1. Mount the reservoir(s) above the highest valve. Gravity feed simplifies
   priming and prevents the master valve from running dry.
2. Cut tubing in two stages: reservoir → master valve → splitter manifold →
   each animal valve → each cage spout. Use the layout sketch from
   [§3](#3-plan-the-installation-before-cutting-wire).
3. Use barbed fittings sized for your tubing's inner diameter. Push the
   tubing fully onto the barb; secure with a small zip tie or clamp if your
   delivery pressure exceeds gravity-fed.
4. Prime the lines before first delivery via **Settings → Priming** in the
   RRR application. See [PRIMING_FEATURE_DOCUMENTATION.md](PRIMING_FEATURE_DOCUMENTATION.md).
5. Inspect every joint for leaks after priming. A drip on a powered HAT will
   end your day.

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
- [ ] [§7](#7-valve-wiring) all 16 valves wired, labelled, insulated.
- [ ] [§8](#8-tubing-and-reservoir) tubing routed, reservoir mounted, but
      reservoir **empty** for first bring-up.
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

5. If all 16 relays click cleanly, fill the reservoir and proceed to
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
2. **Open Settings → Priming** and run the priming sequence to fill the
   tubing. See [PRIMING_FEATURE_DOCUMENTATION.md](PRIMING_FEATURE_DOCUMENTATION.md).
3. **Calibrate every valve.** See [CALIBRATION_QUICK_START.md](CALIBRATION_QUICK_START.md).
   This step is mandatory: uncalibrated valves can deliver multiples of the
   target volume.
4. **Run a 0.5 mL test schedule** on a single cage and weigh the output to
   confirm calibration accuracy is within ±5 %.

---

## 11. Troubleshooting

| Symptom | First thing to check |
|---|---|
| HAT not detected (`i2cdetect` shows nothing at 0x27) | HAT fully seated on GPIO header; stack-level jumpers correct; `/dev/i2c-1` present; user in `i2c` group (`groups $USER`). |
| Relay clicks but valve does not open | +12 V present at COM terminal under load (measure with multimeter while relay is active); valve return reaches common-ground bus; PSU not sagging. |
| Multiple valves open when only one is requested | Common-ground continuity is bad; a relay's NO and another relay's COM are shorted; rewire and re-verify [§7.3](#73-verify-before-powering). |
| Relay LEDs flicker rapidly at idle | Wiring short between +12 V and ground somewhere; disconnect mains immediately and trace with a multimeter on continuity. |
| Pi reboots when valves activate | PSU undersized or the Pi is sharing power with the valve rail. Pi 5 must be on its own 27 W USB-C PSU; valves on their own 12 V supply. |
| Sensor noise / erratic flow readings | Likely ground loop. Check [§6.3.2 caveat 1](#632-alternative-energized-power-strip-as-ground-bus-current-practice-not-recommended-long-term). |
| Delivered volume is 2–3× target | Valves need per-valve calibration. Run [CALIBRATION_QUICK_START.md](CALIBRATION_QUICK_START.md). |
| Water leaking onto HAT | Power off immediately. Dry fully (24 h, no heat). Inspect for corrosion on terminals before re-powering. |

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
