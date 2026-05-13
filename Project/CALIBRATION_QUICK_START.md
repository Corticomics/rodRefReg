# Valve Calibration Quick Start

Per-valve calibration corrects for manufacturing variance between solenoid valves. Each valve gets its own `mL/pulse` factor stored in the DB and applied automatically at runtime.

The **recommended path is the in-app Calibration Wizard**. A CLI tool is available for headless use.

---

## ⚡ Option A — In-App Wizard (Recommended, ~10 min per valve)

### Step 1: Prepare (2 min)
1. Place an empty pre-tared beaker under the target cage outlet.
2. Verify the reservoir is full and pressurized.
3. If the system was just started, let it warm up for ~30 min.
4. Open **Settings → Priming** and prime the lines if they contain air.

### Step 2: Run the Wizard
1. Open **Settings → Calibration** and click **Run Calibration Wizard**.
2. Select the cage(s) to calibrate (cage names from the Cages tab are shown).
3. Follow the on-screen prompts — the wizard executes the pulse train automatically.

### Step 3: Measure & Save
1. When prompted, enter the measured volume (in mL) from your lab scale.
2. The wizard computes the new `mL/pulse` factor and saves it to the DB.

### Step 4: Verify
Run a small test schedule (e.g. 0.5 mL) and confirm the delivered volume is within ±5 %.

---

## ⚡ Option B — CLI Tool (Headless / advanced)

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

## 📊 Expected Results

| Stage | Target (mL) | Actual Before (mL) | Actual After (mL) | Error |
|-------|-------------|-------------------|-------------------|-------|
| **Before Calibration** | 1.000 | 2.863 | - | **186% ❌** |
| **After Calibration** | 1.000 | - | 1.000 ± 0.050 | **5% ✅** |

---

## 🔧 Calibrate All Valves

**In-app**: The Calibration Wizard supports multi-cage selection — pick all cages at once and the wizard sequences them with confirmation prompts.

**CLI**:
```bash
for cage in 1 2 3 4 5 6 7 8 9 10 11 12 13 14 15; do
  python tools/valve_calibration_tool.py --cage "$cage" --interactive
done
```

---

## 🎯 Quality Check

**Good Calibration:**
```
Volume per pulse:       0.075000 mL/pulse
Estimated CV:           0.27%
Quality: EXCELLENT ✅
```

**Bad Calibration (needs redo):**
```
Volume per pulse:       0.082000 mL/pulse
Estimated CV:           8.5%
Quality: POOR ❌
```

**Fix:** Increase pulses to 300:
```bash
python tools/valve_calibration_tool.py --cage 15 --num-pulses 300 --interactive
```

---

## 💡 Pro Tips

1. **Use Lab Scale:** ±0.001g precision minimum
2. **Warm Up System:** 30 minutes before calibration
3. **Full Reservoir:** Pressure affects volume
4. **Measure Water as-is:** 1g ≈ 1mL (at room temp)
5. **Recalibrate:** Every 3 months or after valve replacement

---

## 🆘 Troubleshooting

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

## 📚 Full Documentation

See `VALVE_CALIBRATION_GUIDE.md` for:
- Complete technical explanation
- Root cause analysis
- Best practices
- API reference
- Advanced troubleshooting

---

**Next Steps:**
1. ✅ Calibrate cage 15 NOW (your active test cage)
2. ✅ Run test schedule to verify accuracy
3. ✅ Calibrate all cages used in experiments
4. ⏰ Schedule quarterly recalibration (add to calendar)

**Time Investment:** ~10 min per valve × 15 valves = **2.5 hours for complete system**

**Benefit:** **99% accuracy** vs. current 186% error = **Worth it!**

