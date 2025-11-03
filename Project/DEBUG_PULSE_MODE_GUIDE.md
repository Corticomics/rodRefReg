# Debug Guide: Pulse Mode Firmware Hang Investigation

## Current Status: PERIODIC RESTART NOT EXECUTING

### Evidence from Logs

The periodic restart logic **is not triggering** during the first delivery. Expected output:

```
[PERIODIC CHECK] pulse_count=4, pulses_since_restart=4, max=5
[PULSE 5] Executing...
[PULSE 5] Complete: vol=0.0080mL, total=0.040mL, pulses_since_restart=5
[PERIODIC CHECK] pulse_count=5, pulses_since_restart=5, max=5
🔄 PERIODIC RESTART: After 5 pulses...
✅ Sensor restarted successfully, resuming delivery
[PULSE 6] Executing...
```

**Actual output:** NONE of these messages appear!

### Hypothesis

One of the following is true:

1. **Code not on Pi:** Latest changes not pulled/applied
2. **Logic error:** The restart condition is evaluated BEFORE pulse execution, but `pulses_since_restart` starts at 0
3. **Silent failure:** Something is crashing before the print statements

### Added Debug Instrumentation

**File:** `Project/strategies/solenoid_flow_strategy.py`

**Lines 518-533:** Added print statements to trace execution:
```python
print(f"[PERIODIC CHECK] pulse_count={pulse_count}, pulses_since_restart={pulses_since_restart}, max={max_pulses_before_restart}")
if pulses_since_restart >= max_pulses_before_restart:
    print(f"🔄 PERIODIC RESTART: After {pulses_since_restart} pulses...")
    # ... restart logic
    print(f"✅ Sensor restarted successfully, resuming delivery")
```

**Lines 537-546:** Added pulse execution tracking:
```python
print(f"[PULSE {pulse_count+1}] Executing... (pulses_since_restart will be {pulses_since_restart+1} after)")
# ... execute pulse
print(f"[PULSE {pulse_count}] Complete: vol={pulse_volume:.4f}mL, total={delivered_ml:.4f}mL, pulses_since_restart={pulses_since_restart}")
```

## Next Steps

### Step 1: Verify Code is on Pi

```bash
cd ~/rodent-refreshment-regulator/Project
git pull
git log --oneline -5
```

**Expected:** You should see a recent commit with "Periodic restart" or "pulse mode fix"

**If NOT:** The code isn't on the Pi! You need to:
1. Commit changes from your Mac
2. Push to `ze-dev` branch
3. Pull on Pi

### Step 2: Run Test Schedule

Create a test schedule:
- 1 animal
- 0.2 mL target
- 5-minute window

**Watch for these messages:**
```
[PERIODIC CHECK] pulse_count=0, pulses_since_restart=0, max=5
[PULSE 1] Executing...
[PULSE 1] Complete: vol=0.0080mL, total=0.008mL, pulses_since_restart=1
[PERIODIC CHECK] pulse_count=1, pulses_since_restart=1, max=5
...
[PERIODIC CHECK] pulse_count=4, pulses_since_restart=5, max=5
🔄 PERIODIC RESTART: After 5 pulses...
```

### Step 3: Analyze Output

**Scenario A: No `[PERIODIC CHECK]` messages**
- **Problem:** Code not running at all
- **Solution:** Verify git pull worked, restart app

**Scenario B: `[PERIODIC CHECK]` appears but never reaches 5**
- **Problem:** Firmware hangs before pulse 5
- **Solution:** Reduce restart frequency to every 3 pulses

**Scenario C: `pulses_since_restart` stays at 0**
- **Problem:** Variable not incrementing
- **Solution:** Check line 545 is executing

**Scenario D: Restart triggers but fails**
- **Problem:** Sensor restart failing
- **Solution:** Check restart error messages

## Key Differences: RRR vs Test File

### Test File (`test_valve_characterization.py`)

**Pulse Execution Pattern:**
```python
for pulse_width in [10, 20, 50, 100, 200, 500]:
    for trial in range(1, 4):
        if trial > 1:
            restart_sensor()  # ← RESTART BETWEEN TRIALS
        
        # Execute SINGLE pulse
        controller.open_cage()
        time.sleep(pulse_width / 1000.0)
        controller.close_cage()
        
        # Integrate flow
        volume = integrate_samples()
```

**Key Points:**
- **1 pulse per trial**
- **Restart between trials** (lines 601-609)
- **Master valve reopened** for each trial
- **2-second delay** between trials (line 670)

**Why It Works:**
- Never accumulates more than ~15 errors per trial
- Restart clears error counter before next trial
- Total errors per test: MAX 15 (single pulse)

### RRR Application

**Pulse Execution Pattern:**
```python
# Open master once
valves.open_master()

while delivered < target:
    if pulses_since_restart >= 5:  # ← PERIODIC RESTART
        restart_sensor()
    
    # Execute pulse
    valves.open_cage()
    await asyncio.sleep(pulse_width / 1000.0)
    valves.close_cage()
    
    # Integrate flow
    pulse_volume = integrate_samples()
    
    pulses_since_restart += 1
    
    await asyncio.sleep(0.1)  # Small delay
```

**Key Points:**
- **19 consecutive pulses** for 0.2 mL
- **Master stays open** (maintains manifold pressure)
- **0.1s delay** between pulses (vs. 2s in test)
- **Periodic restart** every 5 pulses

**Why It Should Work:**
- Restart every 5 pulses = max 75 errors (5 × 15)
- Well below 200-error firmware limit
- But **ONLY IF restart logic executes!**

## Critical Findings from Your Logs

### Firmware Hangs at Pulse ~15

```
Pulse 1: 0.0080mL  ← Working
Pulse 5: 0.0077mL  ← Working
Pulse 10: 0.0063mL ← Working but degrading
Pulse 15: 0.0064mL ← Last valid measurement
Pulse 16-19: "No flow measurements" ← FIRMWARE STOPPED
```

**Analysis:**
- 15 pulses × ~13 errors/pulse = **~195 errors**
- Just under the 200-error firmware limit
- Matches prediction perfectly!

**Conclusion:**
The periodic restart **WOULD work** if it executed, but it's **NOT executing**.

### Sensor Never Recovers

After first delivery, all subsequent deliveries fail:
```
[UART] ✗ Ping test failed on /dev/teensy_flow, attempt 1/3
[UART] ✗ Ping test failed on /dev/teensy_flow, attempt 2/3
[UART] ✗ Ping test failed on /dev/teensy_flow, attempt 3/3
Sensor restart failed: Teensy not responding
```

**Why:**
- Firmware completely hung after 195+ errors
- Won't respond to serial commands
- Requires physical Teensy reset (replug or reboot)

## Debugging Checklist

### ✅ Things We Know Work

- [x] Sensor initializes successfully
- [x] First 15 pulses execute
- [x] Pulse volume measurement works
- [x] Valve control works
- [x] Initial sensor restart (before delivery) works

### ❌ Things That DON'T Work

- [ ] Periodic restart during delivery
- [ ] Firmware recovery after hang
- [ ] Sensor responds after 195+ errors

### 🔍 Things to Investigate

1. **Is periodic restart code executing?**
   - Look for `[PERIODIC CHECK]` messages
   - Check `pulses_since_restart` increments

2. **Why doesn't firmware recover?**
   - Check if watchdog is active
   - Verify LED blinks during hang
   - Test manual `stop()` → `start()` after hang

3. **Can we reduce restart frequency?**
   - Try every 3 pulses (max 45 errors)
   - Try every 2 pulses (max 30 errors, very safe)

## Expected Output with Fix

### Successful Delivery with Periodic Restarts

```
[PULSE MODE] ✓ ENTERED _deliver_pulse_mode: cage=15, target=0.200mL
✓ Sensor restarted successfully
✓ Sensor health verified

[PERIODIC CHECK] pulse_count=0, pulses_since_restart=0, max=5
[PULSE 1] Executing... (pulses_since_restart will be 1 after)
Pulse volume deviation: measured=0.0185mL, expected=0.0260mL (28.8% diff)
[PULSE 1] Complete: vol=0.0185mL, total=0.019mL, pulses_since_restart=1

[PERIODIC CHECK] pulse_count=1, pulses_since_restart=1, max=5
[PULSE 2] Executing... (pulses_since_restart will be 2 after)
[PULSE 2] Complete: vol=0.0180mL, total=0.037mL, pulses_since_restart=2

[PERIODIC CHECK] pulse_count=2, pulses_since_restart=2, max=5
[PULSE 3] Executing...
[PULSE 3] Complete: vol=0.0182mL, total=0.055mL, pulses_since_restart=3

[PERIODIC CHECK] pulse_count=3, pulses_since_restart=3, max=5
[PULSE 4] Executing...
[PULSE 4] Complete: vol=0.0178mL, total=0.073mL, pulses_since_restart=4

[PERIODIC CHECK] pulse_count=4, pulses_since_restart=4, max=5
[PULSE 5] Executing...
[PULSE 5] Complete: vol=0.0185mL, total=0.092mL, pulses_since_restart=5

[PERIODIC CHECK] pulse_count=5, pulses_since_restart=5, max=5
🔄 PERIODIC RESTART: After 5 pulses...
✓ Sensor restarted successfully
✓ Sensor health verified
✅ Sensor restarted successfully, resuming delivery

[PERIODIC CHECK] pulse_count=5, pulses_since_restart=0, max=5
[PULSE 6] Executing... (pulses_since_restart will be 1 after)
[PULSE 6] Complete: vol=0.0183mL, total=0.110mL, pulses_since_restart=1

... (continues with consistent volumes) ...

[PULSE 19] Complete: vol=0.0184mL, total=0.200mL, pulses_since_restart=4
✓ Pulse delivery complete: delivered=0.200mL, target=0.200mL
```

### Key Indicators

✅ **`[PERIODIC CHECK]`** appears before every pulse
✅ **`pulses_since_restart`** increments: 0→1→2→3→4→5→0 (after restart)
✅ **Periodic restart** triggers at pulse 5, 10, 15
✅ **Consistent pulse volumes** throughout (no degradation)
✅ **All 19 pulses complete** without firmware hang

## Manual Testing Commands

### Test 1: Verify Periodic Restart Logic

```bash
cd ~/rodent-refreshment-regulator/Project
python3 << 'EOF'
# Simulate the restart logic
pulse_count = 0
pulses_since_restart = 0
max_pulses_before_restart = 5

for i in range(20):
    print(f"[PERIODIC CHECK] pulse_count={pulse_count}, pulses_since_restart={pulses_since_restart}, max={max_pulses_before_restart}")
    
    if pulses_since_restart >= max_pulses_before_restart:
        print(f"🔄 PERIODIC RESTART: After {pulses_since_restart} pulses...")
        pulses_since_restart = 0
        print(f"✅ Sensor restarted, resuming delivery")
    
    print(f"[PULSE {pulse_count+1}] Executing...")
    pulse_count += 1
    pulses_since_restart += 1
    print(f"[PULSE {pulse_count}] Complete, pulses_since_restart={pulses_since_restart}\n")
EOF
```

**Expected:** Restart triggers at pulse 5, 10, 15

### Test 2: Check if Sensor Can Restart After Hang

```bash
cd ~/rodent-refreshment-regulator/Project
python3 << 'EOF'
from drivers.uart_flow_sensor import UARTFlowSensor
import time

sensor = UARTFlowSensor(port='/dev/teensy_flow', sampling_hz=20.0)

print("Starting sensor...")
sensor.start()
time.sleep(2)

print("Stopping sensor...")
sensor.stop()
time.sleep(1)

print("Restarting sensor...")
sensor.start()
time.sleep(2)

print("✓ Restart successful!")
sensor.stop()
EOF
```

**Expected:** All steps succeed without errors

## Contact Information

If you see unexpected behavior:

1. **Copy ALL terminal output** (including `[PERIODIC CHECK]` messages)
2. **Note Teensy LED behavior** (blinking/solid/off)
3. **Check git commit hash:** `git log --oneline -1`
4. **Provide `/dev/teensy_flow` status:** `ls -l /dev/teensy_flow`

---

**Status**: 🟡 **WAITING FOR TEST RESULTS**

**Next Action**: User should git pull and run test schedule to verify periodic restart executes

