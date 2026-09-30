# Valve Calibration Quick Start

Per-valve calibration corrects for manufacturing variance between solenoid valves. Each valve gets its own `mL/pulse` factor stored in the DB and applied automatically at runtime.

Since v1.16.0 a calibration also stores the **pulse timing profile** it was measured at — the pulse width and the valve-closed rest between pulses — and deliveries replay that same profile. Calibrate at the timing you intend to run; see [Pulse timing profile](#pulse-timing-profile) below.

Calibration runs in the in-app **Calibration Wizard**, one cage at a time. The standalone command-line tool that earlier versions of this guide described was removed in v1.21.0: it could not start.

---

## Calibrate a valve (~10 min per valve)

### Step 1: Prepare (2 min)
1. Place an empty pre-tared beaker under the target cage outlet.
2. Verify the cage's water supply: the reservoir full on a shared-manifold rig; on an independent rig, the cage's own syringe filled to its normal running level (the wizard's pre-flight checklist asks for the one your rig uses).
3. If the system was just started, let it warm up for ~30 min.
4. Open **Settings → Priming** and prime the lines if they contain air.

### Step 2: Run the Wizard
1. Open **Settings → Calibration**. The table has one row per cage in the device's cage map, with the names set in the Cages tab. Click **Calibrate** on the cage's row (**Recalibrate** if it already has one); the wizard opens for that cage.
2. Work through the **Pre-Flight Checklist**, then set the **Calibration Parameters**: the number of pulses, the **pulse width**, and the **inter-pulse interval**. The page shows the estimated run time and flags a hot duty cycle.
3. Click **Next**: the wizard fires the pulse train automatically. Progress updates live, and closing the wizard stops the run.

### Step 3: Measure & Save
1. Weigh the beaker and enter the **Measured Volume** in mL (1 g of water ≈ 1 mL).
2. The wizard shows the volume per pulse, the estimated CV and a quality rating. **Save & Finish** stores it; the cage's row in the table then shows **[OK]**, the mL/pulse and the date.

### Step 4: Verify
Run a small test schedule (e.g. 0.5 mL) and confirm the delivered volume is within ±5 %.

---

## Pulse timing profile

A calibration says "this valve delivers X mL per pulse" — but only at the cadence it was measured at. Firing the same valve harder heats its coil, which weakens the magnetic pull, which slows the valve opening. On short pulses that lost time is a large share of the shot, so the volume per pulse drifts **downward over a long run**. Bench runs at a 15 ms width and a 100 ms rest lost about 40 % of their output across nine consecutive 500-pulse runs.

Two controls set the profile, and both are stored with the calibration:

| Control | What it does | Default |
|---|---|---|
| **Pulse Width** | How long the valve is held open per pulse. Wider pulses spend proportionally less time in the slow opening transient, so they are less sensitive to coil heating — but they coarsen the dose granularity. | 20 ms |
| **Inter-Pulse Interval** | The valve-closed rest between pulses. A longer rest lowers the duty cycle, so the coil runs cooler and the output holds steady. | 500 ms |

**Calibrate at the profile you intend to run.** Deliveries replay the stored profile for that cage, so the duty cycle that produced the `mL/pulse` figure is the duty cycle the animal receives.

**Duty cycle advisory.** Above roughly 15 % duty (`width ÷ (width + interval)`) the wizard shows a warning. It never blocks — it flags that the valve is energised for a large share of the run and the output may drift. Lengthen the interval to bring it down.

**Trade-off: longer intervals make deliveries longer.** A delivery whose estimated duration would exceed `max_pulse_delivery_time_s` (default 120 s) is **refused before any water is dispensed**, with the reason logged. If you hit that, shorten the interval, reduce the per-delivery volume, or raise the limit.

**Existing calibrations are unaffected.** A calibration saved before v1.16.0 has no stored interval and keeps the previous 100 ms cadence exactly. It only changes when you re-calibrate that cage.

**Finding the right profile.** There is no universal answer — it depends on the valve, the head, and the dose. Calibrate the same valve at several intervals (for example 100, 500 and 1000 ms), repeat each several times, and pick the shortest interval whose output stays flat across runs. Record the winner for your lab.

---

## Dose rounding policy

Water leaves the valve in whole pulses, so a dose can only ever land within one pulse of its target — at 33 µL per pulse, a 0.3 mL dose is 9.1 pulses and the app must fire 9 or 10. The default rounds to the **nearest** pulse: the dose lands within half a pulse either side of its target, and which side depends on the arithmetic (9.1 → 9, under; 8.8 → 9, over).

**Settings → Delivery → Pulse Mode → "Round doses up to the next whole pulse"** flips that: any dose that is not an exact number of pulses gets the next whole pulse, so the plan never falls below its target and lands up to one pulse over. The rounding stays cumulative within a schedule window — a 0.6 mL window split into three chunks fires `ceil(0.6 ÷ mL/pulse)` pulses in total, not one extra per chunk.

**When to use it.** Turn it on when weighed doses come out consistently short of their target and you would rather err over than under. The bench case: with a flow-restricting needle on the reservoir, 0.3–0.7 mL doses weighed 3–8 % under target at nearest rounding. Rounding up plans one more pulse per dose. At 33 µL per pulse that puts the plan at +10 / +5 / +4 / +3.5 / +2 % for 0.3 / 0.5 / 0.6 / 0.7 / 1.0 mL — the ceiling, if the hardware delivers exactly what is planned — and with the ~16 µL per-dose shortfall measured on the needle rig the bowl lands around +4.5 / +2 / +1.5 / +1 / +0.5 %. Verify with ten weighed doses at the smallest target you use — the choice is a policy, not a calibration, and only weighing tells you which side of the target your rig should sit on. If the needle comes out later, turn the setting off again: on a cage without the shortfall it still adds one pulse to every dose that rounds down.

**What the log shows.** `volume_actual_ml` in the dispensing history, the window progress percentage and the completion "precision" line are the plan — `pulses_fired × mL/pulse` — not a weighing. With rounding up they read one pulse above the target even when the bowl, with a retention shortfall, lands near it. Only the scale tells you where the bowl is.

**What it does not change.** The volume per pulse, the timing profile, the per-window carry and the history columns are the same; only the rounding direction of the plan changes — including what counts as "done": nearest rounding closes a window within half a pulse of its target, rounding up closes it only at or above the target (a window cut short by a failed chunk is topped up after the window ends, as today). The setting is global (all cages), off by default, and read when a schedule starts — a schedule that is already running keeps the policy it started with.

---

## Expected Results

| Stage | Target (mL) | Actual Before (mL) | Actual After (mL) | Error |
|-------|-------------|-------------------|-------------------|-------|
| **Before Calibration** | 1.000 | 2.863 | - | **186 % (fail)** |
| **After Calibration** | 1.000 | - | 1.000 ± 0.050 | **5 % (pass)** |

---

## Calibrate All Valves

**Settings → Calibration → Calibrate All Uncalibrated** lists every cage in the device's cage map that has no calibration yet (15 cages on one HAT, 31 on two), then every cage whose stored volume per pulse or pulse width is missing, zero or invalid (**Invalid**), then every cage whose calibration was measured under the other valve topology (**Stale**), and opens the wizard for each in turn. Cancelling a wizard stops the batch; a summary then says how many were done and which were not.

---

## Quality Check

**Good Calibration:**
```
Volume per pulse:       0.075000 mL/pulse
Estimated CV:           0.27%
Quality: EXCELLENT
```

**Bad Calibration (needs redo):**
```
Volume per pulse:       0.082000 mL/pulse
Estimated CV:           8.5%
Quality: POOR
```

**Fix:** recalibrate the cage with **Number of Pulses** set to 300.

---

## Pro Tips

1. **Use Lab Scale:** ±0.001g precision minimum
2. **Warm Up System:** 30 minutes before calibration
3. **Supply Level:** Head pressure affects volume (the reservoir full on a shared manifold; each cage's syringe at its normal running level on an independent rig)
4. **Measure Water as-is:** 1g ≈ 1mL (at room temp)
5. **Recalibrate:** Every 3 months or after valve replacement
6. **After a topology switch** (**Settings → Delivery → Valve Topology**): recalibrate every animal cage. A calibration measured under the other valve topology shows **Stale** in the table (one saved before v1.21.0 counts as shared manifold), and in solenoid pulse mode (the default) Run refuses any schedule that waters a Stale cage until it is recalibrated. **Calibrate All Uncalibrated** includes the Stale cages.

---

## Troubleshooting

### "The valve does not click during calibration"
```bash
# Check the relay HAT is on the I²C bus
ls /dev/i2c-*          # should show /dev/i2c-1
sudo i2cdetect -y 1    # the HAT should appear at its address
```
Then run the relay bring-up test in [HARDWARE_SETUP.md §9](HARDWARE_SETUP.md#9-first-power-on-and-bring-up-test).

### "Calibration Failed: … did not open at pulse N" (or "did not close")
A relay did not switch partway through the run, so the water in the beaker no longer matches the pulse count. The wizard stops there. Do not save a measurement from that run: fix the relay HAT as above, then calibrate again. After "did not close", the valve may still be open, so check the rig before anything else.

### "Volume seems wrong"
```bash
# 1. Check scale is tared
# 2. Ensure no spills
# 3. Run calibration again (3x), average results
```

### "Still over-delivering after calibration"
1. In **Settings → Calibration**, the cage's row should show **[OK]** with the new mL/pulse and today's date.
2. Calibrations are read when a schedule starts. A schedule that was already running keeps the calibration it started with: stop it and start it again.
3. At schedule start the app prints the calibration every cage will use in its **Terminal** tab, one line per calibrated cage:
   ```
   [CAL SNAPSHOT] cage=15 width=30ms rest=1000ms vol=0.032936 mL/pulse topology=shared_manifold
   ```
   Every cage the schedule waters has a line: since v1.21.0, in solenoid pulse mode (the default), Run refuses a schedule that waters a cage with no usable calibration measured under this device's valve topology (see ["Valve calibration needed" when pressing Run](#valve-calibration-needed-when-pressing-run) below). These lines appear only in the Terminal tab: once the window is up, the app sends its output there rather than to the system journal.

### "Valve calibration needed" when pressing Run

With solenoid hardware and **Enable Pulse Mode** on (the default), Run checks every cage the schedule waters before anything starts (for an instant schedule, the cages of the deliveries still ahead). It refuses the schedule and lists the cages when a cage:

- has no calibration (**Not Calibrated** in Settings → Calibration),
- has one measured under the other valve topology (**Stale**; one saved before v1.21.0 counts as shared manifold), or
- has one whose volume per pulse or pulse width is missing, zero or invalid (**Invalid**).

Calibrate those cages in **Settings → Calibration** (the highlighted button on each cage's row, or **Calibrate All Uncalibrated**), then press Run again. A calibration only has to match the topology: its pulse width may differ from the one in Settings, because a delivery replays the cage's own.

A "**Not a cage on this device**" line (the dialog is titled **Cage not on this device** when that is the only problem) means the schedule waters a cage this device's cage map does not have. Edit the schedule so its animals are on cages listed in Settings → Calibration.

"**Can't check valve calibrations**" means RRR could not read the valve calibrations from its database. Press Run again; if it repeats, the Terminal tab shows the database error.

---

## Full Documentation

See [VALVE_CALIBRATION_GUIDE.md](VALVE_CALIBRATION_GUIDE.md) for:
- Complete technical explanation
- Root cause analysis
- Best practices
- API reference
- Advanced troubleshooting

---

**Next Steps:**

1. Calibrate every cage used in active experiments.
2. Run a small test schedule (e.g. 0.5 mL) and weigh the output to verify accuracy is within ±5 %.
3. Schedule quarterly recalibration on the lab calendar.

**Time investment:** approximately 10 min per valve × 15 valves = 2.5 hours for a full HAT.

**Benefit:** Sub-5 % delivery error vs. the uncalibrated baseline of ~186 % over-delivery.

