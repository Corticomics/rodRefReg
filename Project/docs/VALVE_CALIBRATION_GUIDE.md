# Valve Calibration Guide - RRR System
## Per-Valve Empirical Calibration for Precision Water Delivery

> **User-facing entry point:** `Settings → Calibration → Run Calibration Wizard` (`ui/CalibrationWizard.py`). For a step-by-step walkthrough use [CALIBRATION_QUICK_START.md](CALIBRATION_QUICK_START.md). This document is the technical reference behind the wizard.

---

## Table of Contents
1. [Problem Summary](#problem-summary)
2. [Root Cause Analysis](#root-cause-analysis)
3. [Solution Overview](#solution-overview)
4. [Calibration Workflow](#calibration-workflow)
5. [Technical Implementation](#technical-implementation)
6. [Best Practices](#best-practices)
7. [Troubleshooting](#troubleshooting)

---

## Problem Summary

**Symptoms:**
- Target: 1.0 mL delivery
- Actual: 2.863 mL measured (186% over-delivery)
- System reported: 1.000 mL delivered
- Sensor readings: ~0.004-0.005 mL per pulse (shown in logs)
- Calibration expected: 0.026 mL per pulse
- **Calculated actual:** ~0.075 mL per pulse (2.863 mL ÷ 38 pulses)

**Impact:**
- Animals receiving ~3x target water volume
- Experimental data compromised
- Potential health risks from over-hydration

---

## Root Cause Analysis

### Issue 1: Global Calibration ≠ Individual Valve Behavior

**Problem:**
The system used a single calibration value (0.026 mL/pulse from `pulse_calibration.py`) for ALL valves.

**Reality:**
Manufacturing tolerances in Parker Series 3 valves cause 10-30% variation between units.

**Your Valve's Behavior:**
- Hardcoded: 0.026 mL/pulse
- Actual: ~0.075 mL/pulse
- Error: **188% over-delivery**

### Issue 2: Sensor Integration Window Too Narrow

**Problem:**
The sensor measurement window **completely missed the bulk flow**:

**Original Flow (BROKEN):**
```
Time:     [----valve opens----|----valve closes----|----settling----|----measurement window----]
Flow:     [████████ BULK ████]  [██ tail ██]        [░ settling ░]   [measure: 0.005 mL]
Missed:   [~~~NOT MEASURED~~~]  [NOT MEASURED]      [NOT MEASURED]   [measured]
```

**The system was:**
1. Suspending sensor reads BEFORE opening valve
2. Opening valve (bulk flow happens here: ~0.070 mL)
3. Closing valve
4. Resuming sensor reads
5. Measuring only tail/settling (~0.005 mL)
6. Reporting: "Pulse volume deviation: 82% diff" ← **System detected the problem but kept using wrong value!**

**Fixed Flow (NEW):**
```
Time:     [----valve opens----|----valve closes----|----settling----]
Flow:     [████████ BULK ████]  [██ tail ██]        [░ settling ░]
Measure:  [<<<<< CONTINUOUS MEASUREMENT >>>>>>>>>>>>>>>]
```

Now captures:
- Valve opening transient
- Bulk flow
- Valve closing transient
- Settling period
- **Total: Full delivery profile**

---

## Solution Overview

### Three-Tier Hybrid System

**Tier 1: Per-Valve Empirical Calibration (Primary)**
- Run 200-300 pulses per valve
- Gravimetric measurement (lab scale ±0.001g)
- Calculate: mL_per_pulse = total_volume / num_pulses
- Store in database per cage

**Tier 2: Real-Time Sensor Feedback (Validation)**
- Integrate full flow curve (not just tail)
- Compare measured vs. calibrated values
- Adaptive weighting based on deviation

**Tier 3: Drift Detection & Alerts**
- Track sensor vs. calibration over time
- Alert if deviation >20% sustained
- Recommend recalibration

---

## Calibration Workflow

### Prerequisites
- Lab scale with ±0.001g precision
- Empty collection beaker
- System warm-up: 30 minutes
- Full fluid reservoir

### Step-by-Step Process

#### 1. Prepare Equipment
```bash
# 1. Verify system is in solenoid + pulse mode
# 2. Check fluid reservoir is FULL
# 3. Place beaker under cage output
# 4. Tare scale with empty beaker
```

#### 2. Run Calibration Tool
```bash
cd ~/rodRefReg/Project
python tools/valve_calibration_tool.py --cage 15 --interactive
```

**Interactive Mode Prompts:**
```
VALVE CALIBRATION - Cage 15 (Relay 15)
======================================
Pulse width: 20ms
Number of pulses: 250

PRE-FLIGHT CHECKLIST:
  1. Verify fluid reservoir is FULL
  2. Place empty beaker under cage 15 output
  3. Tare your lab scale with empty beaker
  4. Ensure system has been running >30min (stable temp)

Press ENTER when ready to begin calibration...

Executing 250 pulses...
(This will take ~8.3 minutes)
  Progress: 50/250 (20.0%) - Elapsed: 95.3s
  Progress: 100/250 (40.0%) - Elapsed: 190.1s
  Progress: 150/250 (60.0%) - Elapsed: 285.8s
  Progress: 200/250 (80.0%) - Elapsed: 380.2s
  Progress: 250/250 (100.0%) - Elapsed: 475.6s
Completed 250 pulses in 476.2s

MEASUREMENT:
  1. Remove beaker from under cage output
  2. Weigh beaker on lab scale
  3. For water: weight in grams ≈ volume in mL

Enter measured volume (mL): 18.750

======================================================================
CALIBRATION RESULTS
======================================================================
Total volume measured:  18.7500 mL
Number of pulses:       250
Volume per pulse:       0.075000 mL/pulse
Estimated CV:           0.27%

Quality: EXCELLENT

Save this calibration to database? (yes/no): yes
Calibration saved to database (ID: 1)
Calibration complete and saved.
  Cage 15: 0.075000 mL/pulse
```
*Note: Be sure to keep the reservoir water level constant, as pressure variation can result in a poor calibration. Add water gently and gradually to maintain a constant level. This is especially important for small reservoirs.*

#### 3. Verify Calibration
```bash
# Check database
sqlite3 rrr_database.db "SELECT * FROM valve_calibration WHERE cage_id=15;"
```

**Expected Output:**
```
calibration_id|cage_id|relay_id|pulse_width_ms|volume_per_pulse_ml|stddev_ml|coefficient_of_variation_pct|num_samples|calibration_date|calibrated_by|notes
1|15|15|20|0.075|0.000212|0.27|250|2025-11-04T14:30:15.123456|1|Empirical calibration: 250 pulses @ 20ms
```

#### 4. Test Delivery
Run a small test schedule (e.g., 0.5 mL) and verify with scale:
- Target: 0.5 mL
- Expected pulses: ~7 (0.5 / 0.075)
- Measured: 0.500 ± 0.010 mL (within tolerance)

*Note: Manually verifying calibration is especially important when flow sensors are not integrated into the system. Always run sample schedules to verify that the system dispenses the correct volume of liquid.*

## Technical Implementation

### Database Schema

**`valve_calibration` Table:**
```sql
CREATE TABLE valve_calibration (
    calibration_id INTEGER PRIMARY KEY AUTOINCREMENT,
    cage_id INTEGER NOT NULL UNIQUE,
    relay_id INTEGER NOT NULL,
    pulse_width_ms INTEGER NOT NULL,
    volume_per_pulse_ml REAL NOT NULL,      -- Main calibration value
    stddev_ml REAL,                          -- Standard deviation
    coefficient_of_variation_pct REAL,       -- CV% (should be <5%)
    num_samples INTEGER NOT NULL,            -- Number of pulses (200-300)
    calibration_date TEXT NOT NULL,
    calibrated_by INTEGER,                   -- Trainer ID
    notes TEXT
);
```

**`valve_calibration_history` Table:**
- Same schema as above
- Tracks ALL calibrations for drift analysis

### Code Flow

#### 1. Initialization (RelayWorker)
```python
# Pass database handler to strategy
self.strategy = StrategyFactory.create(
    'solenoid',
    solenoid_controller=solenoid,
    flow_sensor=flow_sensor,
    calibration_store=cal_store,
    settings=system_settings,
    database_handler=self.system_controller.database_handler,  # NEW
)
```

#### 2. Per-Pulse Delivery (SolenoidFlowStrategy)
```python
async def _execute_single_pulse(self, cage_id: int) -> float:
    # 1. Get per-valve calibration from database
    expected_vol_ml = await self._get_valve_calibration_value(cage_id)
    
    # 2. Clear sensor queue
    self._sensor.clear_queue()
    
    # 3. Execute pulse while collecting samples CONTINUOUSLY
    samples = []
    self._valves.open_cage(cage_id)
    while valve_open:
        sample = self._sensor.read_one()
        samples.append(sample)  # Capture DURING opening
        await asyncio.sleep(0.05)
    
    self._valves.close_cage(cage_id)
    while settling:
        sample = self._sensor.read_one()
        samples.append(sample)  # Capture DURING settling
        await asyncio.sleep(0.05)
    
    # 4. Integrate full flow curve
    delivered_ml = trapezoidal_integration(samples)
    
    # 5. Adaptive correction
    if sensor_reading_reasonable:
        weight = adaptive_weight(deviation_pct)
        final_volume = (sensor * weight) + (calibration * (1-weight))
    else:
        final_volume = expected_vol_ml  # Fallback to calibration
    
    return final_volume
```

#### 3. Database Lookup
```python
async def _get_valve_calibration_value(self, cage_id: int) -> float:
    # Try database first
    cal = self._db.get_valve_calibration(cage_id)
    if cal and cal['pulse_width_ms'] == self._pulse_width_ms:
        return cal['volume_per_pulse_ml']  # Per-valve value!
    
    # Fallback to global
    return self._empirical_pulse_volumes.get(self._pulse_width_ms, 0.026)
```

### Adaptive Correction Algorithm

**Goal:** Trust sensor when it's working, use calibration as fallback

```python
deviation_pct = abs(sensor_ml - calibration_ml) / calibration_ml * 100.0

if deviation_pct > 50.0:
    # Sensor clearly wrong (e.g., disconnected)
    use_value = calibration_ml
elif deviation_pct < 20.0:
    # Good agreement, trust sensor more
    weight_sensor = 0.7
    use_value = (sensor_ml * 0.7) + (calibration_ml * 0.3)
else:
    # Moderate disagreement, blend
    weight_sensor = 1.0 / (1.0 + deviation_pct / 100.0)
    use_value = (sensor_ml * weight_sensor) + (calibration_ml * (1 - weight_sensor))
```

---

## Best Practices

### When to Calibrate

**Must calibrate:**
- New valve installation
- Valve replacement
- Pressure change in system
- Fluid type change (e.g. water to saline)
- After maintenance on manifold

**Should calibrate:**
- Every 3 months (routine)
- If delivery accuracy exceeds 10 % error for 3 or more consecutive schedules
- After 10,000+ valve cycles (wear)

**Optional:**
- Seasonally (temperature affects valve timing)
- After firmware updates

### Calibration Quality Metrics

| Coefficient of Variation (CV%) | Quality | Action |
|-------------------------------|---------|--------|
| < 1 % | EXCELLENT | Production ready |
| 1–3 % | GOOD | Production ready |
| 3–5 % | ACCEPTABLE | Monitor closely |
| > 5 % | POOR | Re-calibrate with more pulses or check hardware |

### Sample Size Guidelines

| Valve Type | Recommended Pulses | Time @ 20ms pulse |
|-----------|-------------------|-------------------|
| Parker Series 3 | 250 | ~8 minutes |
| High-precision required | 300 | ~10 minutes |
| Quick check | 100 | ~3 minutes |

**Math:**
- Standard error = (scale_precision / √num_pulses)
- For ±0.001g scale and 250 pulses: SE = 0.001 / √250 = 0.000063 g ≈ 0.00006 mL
- CV% = (SE / mean) × 100%

### Per-Cage vs. Global Calibration

**Use Per-Cage Calibration (Recommended):**
- Different valves per cage
- High precision required (<5% error)
- Experimental research

**Use Global Calibration (Not Recommended):**
- All valves from same batch
- Moderate precision acceptable (10% error)
- Quick prototyping

---

## Troubleshooting

### Issue: CV > 5% (Poor Stability)

**Possible Causes:**
1. **Insufficient pulses** → Increase to 300
2. **Pressure instability** → Check reservoir level, pump operation
3. **Valve sticking** → Clean valve, check for debris
4. **Temperature drift** → Allow 30min warm-up
5. **Scale precision** → Use lab-grade scale (±0.001g minimum)

**Diagnostic Test:**
```bash
# Run calibration 3 times consecutively
python tools/valve_calibration_tool.py --cage 15 --num-pulses 100 --interactive
# Compare results - should be within 5%
```

### Issue: Sensor Measurement ≠ Calibration

**Symptoms:**
```
Adaptive correction: sensor=0.045mL, cal=0.075mL, using=0.060mL (dev=40%)
```

**Possible Causes:**
1. **Sensor partially blocked** → Check sensor for debris
2. **Air bubbles** → Prime system thoroughly
3. **EMI from valves** → Check grounding, shielding
4. **Sensor calibration drift** → Recalibrate sensor (see sensor manual)
5. **Pressure transient** → Adjust pulse settling time

**Action:**
- If deviation < 50%: System uses adaptive correction (OK)
- If deviation > 50%: System uses calibration (OK, but investigate)
- If sustained high deviation: Check sensor health

### Issue: System Still Using Old Global Calibration

**Check:**
```bash
# 1. Verify database entry exists
sqlite3 rrr_database.db "SELECT * FROM valve_calibration WHERE cage_id=15;"

# 2. Check logs for calibration lookup
grep "Using per-valve calibration" /path/to/logs/system.log

# 3. Restart application to reload database
```

### Issue: Calibration Tool Fails

**Error: "Solenoid controller not found"**
```bash
# Ensure relay hat is connected
ls /dev/i2c-*
# Should show /dev/i2c-1

# Test relay manually
python -c "import SM16relind; SM16relind.set(0, 1, 1)"
```

**Error: "Database locked"**
```bash
# Close any open connections
killall python3
# Retry calibration
```

---

## Migration Path (For Existing Systems)

### Scenario 1: Fresh System (No Calibration)

**Status:** Currently using hardcoded defaults (0.026 mL/pulse)

**Action:**
1. Calibrate all valves using tool
2. System automatically switches to per-valve calibration

### Scenario 2: Existing System with Global Calibration

**Status:** Using `pulse_calibration.json`

**Action:**
1. Calibrate critical valves (used in active experiments)
2. System uses per-valve where available, falls back to global
3. Gradually calibrate remaining valves

### Scenario 3: System with Incorrect Global Calibration

**Status:** Your situation - 0.026 mL hardcoded, actual ~0.075 mL

**Action:**
1. **IMMEDIATE:** Calibrate cage 15 (your test cage)
```bash
python tools/valve_calibration_tool.py --cage 15 --num-pulses 250 --interactive
```

2. **SHORT-TERM (this week):** Calibrate all active cages

3. **LONG-TERM:** Schedule quarterly recalibration

---

## API Reference

### Database Methods

```python
from models.database_handler import DatabaseHandler

db = DatabaseHandler('rrr_database.db')

# Save calibration
cal_id = db.save_valve_calibration(
    cage_id=15,
    relay_id=15,
    pulse_width_ms=20,
    volume_per_pulse_ml=0.075,
    stddev_ml=0.000212,
    cv_pct=0.27,
    num_samples=250,
    calibrated_by=1,  # trainer ID
    notes="Initial calibration"
)

# Load calibration
cal = db.get_valve_calibration(cage_id=15)
print(f"Calibrated volume: {cal['volume_per_pulse_ml']:.6f} mL/pulse")

# Get all calibrations
all_cals = db.get_all_valve_calibrations()
for cage_id, cal in all_cals.items():
    print(f"Cage {cage_id}: {cal['volume_per_pulse_ml']:.6f} mL/pulse")

# Get calibration history
history = db.get_valve_calibration_history(cage_id=15, limit=10)
for entry in history:
    print(f"{entry['calibration_date']}: {entry['volume_per_pulse_ml']:.6f} mL/pulse")
```

### Command-Line Tool

```bash
# Interactive mode (recommended)
python tools/valve_calibration_tool.py --cage 15 --interactive

# Automated mode (for scripting)
python tools/valve_calibration_tool.py \\
    --cage 15 \\
    --num-pulses 250 \\
    --pulse-width-ms 20 \\
    --measured-ml 18.750 \\
    --trainer-id 1

# Custom pulse count
python tools/valve_calibration_tool.py --cage 15 --num-pulses 300 --interactive

# Quick test (100 pulses)
python tools/valve_calibration_tool.py --cage 15 --num-pulses 100 --interactive
```

---

## Summary

**What Changed:**
1. Database schema for per-valve calibration storage
2. Calibration tool using a 200–300 pulse gravimetric method
3. Sensor integration fixed to capture the full flow curve (not just the tail)
4. Adaptive correction that blends sensor and calibration values
5. Per-valve lookup in the delivery strategy
6. Drift detection via calibration history

**What to Do Next:**
1. **Calibrate your valve (cage 15):**
   ```bash
   python tools/valve_calibration_tool.py --cage 15 --interactive
   ```
   
2. **Run test schedule** to verify accuracy

3. **Calibrate remaining valves** in active use

4. **Schedule quarterly recalibration**

**Expected Results:**
- **Before:** 1.0 mL target → 2.863 mL actual (186% error)
- **After:** 1.0 mL target → 1.000 ± 0.05 mL actual (<5% error)

---

## References

- [Sensirion SLF3S-0600F Datasheet](https://sensirion.com/media/documents/C4F8D965/66F56F53/LQ_DS_SLF3S-0600F_Datasheet.pdf)
- [Parker Series 3 Valve Manual](https://www.parker.com)
- [User Rules: Database Interaction Guidelines](../user_rules)
- [Pulse Mode Implementation Documentation](./PULSE_MODE_COMPLETE_SUMMARY.md)

---

**Created:** 2025-11-04  
**Last Updated:** 2025-11-04  
**Version:** 1.0  
**Author:** RRR Development Team

