# Valve Calibration Quick Start

Per-valve calibration corrects for manufacturing variance between solenoid valves. Each valve gets its own `mL/pulse` factor stored in the DB and applied automatically at runtime.

Since v1.16.0 a calibration also stores the **pulse timing profile** it was measured at — the pulse width and the valve-closed rest between pulses — and deliveries replay that same profile. Calibrate at the timing you intend to run; see [Pulse timing profile](#pulse-timing-profile) below.

The **recommended path is the in-app Calibration Wizard**. A CLI tool is available for headless use.

---

## Option A — In-App Wizard (recommended, ~10 min per valve)

### Step 1: Prepare (2 min)
1. Place an empty pre-tared beaker under the target cage outlet.
2. Verify the reservoir is full and pressurized.
3. If the system was just started, let it warm up for ~30 min.
4. Open **Settings → Priming** and prime the lines if they contain air.

### Step 2: Run the Wizard
1. Open **Settings → Calibration** and click **Run Calibration Wizard**.
2. Select the cage(s) to calibrate (cage names from the Cages tab are shown).
3. On the configuration page, set the number of pulses, the **pulse width**, and the **inter-pulse interval**. The page shows the estimated run time and flags a hot duty cycle.
4. Follow the on-screen prompts — the wizard executes the pulse train automatically. Progress updates live, and the run can be stopped by closing the wizard.

### Step 3: Measure & Save
1. When prompted, enter the measured volume (in mL) from your lab scale.
2. The wizard computes the new `mL/pulse` factor and saves it to the DB.

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

## Option B — CLI Tool (headless or advanced)

### Step 1: Prepare (same as Option A)

### Step 2: Run Calibration
```bash
cd ~/rodent-refreshment-regulator/Project
python tools/valve_calibration_tool.py --cage 15 --interactive
```

### Step 3: Measure & Save
```
# Tool executes 250 pulses (~8 min) then prompts:
Enter measured volume (mL): 18.750
# Tool calculates: 18.750 / 250 = 0.075 mL/pulse
Save this calibration to database? yes
```

### Step 4: Verify
Run a small test schedule (0.5 mL) and confirm output is within ±5 %.

---

## Expected Results

| Stage | Target (mL) | Actual Before (mL) | Actual After (mL) | Error |
|-------|-------------|-------------------|-------------------|-------|
| **Before Calibration** | 1.000 | 2.863 | - | **186 % (fail)** |
| **After Calibration** | 1.000 | - | 1.000 ± 0.050 | **5 % (pass)** |

---

## Calibrate All Valves

**In-app**: The Calibration Wizard supports multi-cage selection — pick all cages at once and the wizard sequences them with confirmation prompts.

**CLI**:
```bash
for cage in 1 2 3 4 5 6 7 8 9 10 11 12 13 14 15; do
  python tools/valve_calibration_tool.py --cage "$cage" --interactive
done
```

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

**Fix:** Increase pulses to 300:
```bash
python tools/valve_calibration_tool.py --cage 15 --num-pulses 300 --interactive
```

---

## Pro Tips

1. **Use Lab Scale:** ±0.001g precision minimum
2. **Warm Up System:** 30 minutes before calibration
3. **Full Reservoir:** Pressure affects volume
4. **Measure Water as-is:** 1g ≈ 1mL (at room temp)
5. **Recalibrate:** Every 3 months or after valve replacement

---

## Troubleshooting

### "Tool says cage not found"
```bash
# Check relay connections
ls /dev/i2c-*  # Should show /dev/i2c-1
```

### "Volume seems wrong"
```bash
# 1. Check scale is tared
# 2. Ensure no spills
# 3. Run calibration again (3x), average results
```

### "Still over-delivering after calibration"
```bash
# 1. Verify database has entry
sqlite3 rrr_database.db "SELECT * FROM valve_calibration WHERE cage_id=15;"

# 2. Restart application
# 3. Check logs for "Using per-valve calibration"
```

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

