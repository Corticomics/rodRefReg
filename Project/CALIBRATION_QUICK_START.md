# Valve Calibration Quick Start

## 🚨 Emergency: Fix Your Over-Delivery NOW

**Problem:** Delivering 2.863 mL instead of 1.0 mL (186% error)  
**Root Cause:** Wrong calibration value (0.026 mL/pulse vs. actual ~0.075 mL/pulse)  
**Solution:** Run per-valve calibration

---

## ⚡ 5-Minute Setup

### Step 1: Prepare (2 min)
```bash
# 1. Place empty beaker under cage 15 output
# 2. Tare lab scale with empty beaker
# 3. Verify reservoir is FULL
# 4. Let system warm up (if just started, wait 30 min)
```

### Step 2: Run Calibration (8 min)
```bash
cd /Users/zes/.cursor/worktrees/rodRefReg/P9fOC/Project
python tools/valve_calibration_tool.py --cage 15 --interactive
```

### Step 3: Measure & Save (1 min)
```
# Tool will execute 250 pulses (~8 minutes)
# Then prompt for measurement:

Enter measured volume (mL): [weigh beaker on scale]

# Example: If scale shows 18.750g → enter 18.750
# Tool calculates: 18.750 / 250 = 0.075 mL/pulse

Save this calibration to database? yes
```

### Step 4: Verify (2 min)
```bash
# Run small test schedule (0.5 mL)
# Measure output with scale
# Expected: 0.500 ± 0.025 mL ✓
```

---

## 📊 Expected Results

| Stage | Target (mL) | Actual Before (mL) | Actual After (mL) | Error |
|-------|-------------|-------------------|-------------------|-------|
| **Before Calibration** | 1.000 | 2.863 | - | **186% ❌** |
| **After Calibration** | 1.000 | - | 1.000 ± 0.050 | **5% ✅** |

---

## 🔧 Calibrate All Valves

```bash
# Cage 1
python tools/valve_calibration_tool.py --cage 1 --interactive

# Cage 2  
python tools/valve_calibration_tool.py --cage 2 --interactive

# ... repeat for all active cages

# Cage 15
python tools/valve_calibration_tool.py --cage 15 --interactive
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

