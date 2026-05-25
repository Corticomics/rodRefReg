# Flow Sensor Integration Guide
## Teensy 4.1 + SLF3S-0600F UART Bridge for RRR

**Version:** 1.0  
**Date:** October 6, 2025  
**Status:** Production — integrated into `strategies/solenoid_flow_strategy.py` and `drivers/uart_flow_sensor.py`.

---

## Table of Contents
1. [Hardware Setup](#hardware-setup)
2. [Software Architecture](#software-architecture)
3. [GUI Configuration](#gui-configuration)
4. [Coding Standards](#coding-standards)
5. [Testing Strategy](#testing-strategy)
6. [Troubleshooting](#troubleshooting)

---

## Hardware Setup

### Components
- **Teensy 4.1** ([PJRC](https://www.pjrc.com/store/teensy41.html))
  - ARM Cortex-M7 @ 600 MHz
  - USB 2.0 High Speed (480 Mbit/s)
  - I²C (Wire library, pins 18/19)
  
- **SLF3S-0600F Flow Sensor** ([Sensirion Datasheet](https://sensirion.com/media/documents/C4F8D965/66F56F53/LQ_DS_SLF3S-0600F_Datasheet.pdf))
  - Flow range: ±2000 µL/min (±3.25 mL/min max)
  - Accuracy: ±5% of measured value or ±10 µL/min
  - I²C address: 0x08
  - Update rate: up to 500 Hz
  - Warm-up time: ~60ms typical

- **Sequent Microsystems 16-Relays HAT** ([Documentation](https://cdn.shopify.com/s/files/1/0534/4392/0067/files/16-RELAYS-UsersGuide_d5e24457-bdd9-4e16-a307-7f90bbd668bb.pdf))
  - 16x SPDT relays
  - I²C address: 0x20 (stack 0)
  - Switching 12V solenoid valves (inductive load)

### Wiring Diagram

```
STAR GROUNDING TOPOLOGY (Critical for EMI mitigation)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

                    AC Plug Head
                    (Earth Ground)
                          │
                    Terminal Block
                    (Star Point)
                          │
          ┌───────────────┼───────────────┬───────────────┐
          │               │               │               │
          │               │               │               │
     12V PSU GND     Pi Pin 6 GND   Teensy GND     Solenoid (-)
     (14 AWG)        (22 AWG)       (22 AWG)       (both, terminal)


TEENSY 4.1 CONNECTIONS:
━━━━━━━━━━━━━━━━━━━━━
  Pin 18 (SDA) ──→ SLF3S-0600F SDA ──┐
  Pin 19 (SCL) ──→ SLF3S-0600F SCL ──┤  2kΩ pullup resistors
  3V3          ──→ SLF3S-0600F VDD ──┤  to 3V3 for both lines
  GND          ──→ Terminal Block Star Point (breadboard row, not direct)
  USB          ──→ Raspberry Pi USB port


FLOW SENSOR CONNECTIONS (SLF3S-0600F):
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  VDD (Red)       ──→ Teensy 3V3
  GND (Black)     ──→ Breadboard (same row as Teensy GND → terminal)
  SDA (White)     ──→ Teensy Pin 18  ┐
  SCL (Yellow)    ──→ Teensy Pin 19  ├─ 2kΩ pullups to 3V3
                                     ┘

RELAY HAT + SOLENOIDS:
━━━━━━━━━━━━━━━━━━━━━
  Relay HAT logic GND: Connected via Pi GPIO header (Pin 6 → terminal)
  Solenoid (+):        12V PSU positive rail
  Solenoid (-):        Terminal block star point (same position as PSU GND)
```

### Critical Grounding Rules

1. **ALL grounds must connect to star point** (terminal block on AC earth)
2. **Breadboard ground is ISOLATED** (only connects to star via dedicated wires)
3. **Teensy GND**: Breadboard → terminal block (NOT direct to terminal)
4. **Flow sensor GND**: Breadboard → terminal block (shares row with Teensy)
5. **Solenoid (-) wires**: BOTH connect to terminal block at PSU GND position
6. **NO ground loops** - single path from each component to star point

### I²C Pullup Resistors

**Required** per [SLF3S-0600F datasheet](https://sensirion.com/media/documents/C4F8D965/66F56F53/LQ_DS_SLF3S-0600F_Datasheet.pdf):
- **Value:** 2kΩ (not 5.3kΩ, not 10kΩ)
- **SDA:** Teensy Pin 18 ← 2kΩ → Teensy 3V3
- **SCL:** Teensy Pin 19 ← 2kΩ → Teensy 3V3
- **Location:** On breadboard near Teensy
- **Purpose:** I²C bus requires pullups; Teensy 4.1 has no internal pullups on I²C pins

---

## Software Architecture

### Canonical Serial Protocol

All serial communication must use `drivers/teensy_serial_protocol.py`:

```python
from drivers.teensy_serial_protocol import TeensySerialProtocol

# Connect to Teensy
protocol = TeensySerialProtocol(port='/dev/ttyACM0')
protocol.connect()  # Handles 3.5s USB CDC wait + ping test

# Start sensor
protocol.send_start_command(rate_hz=50.0)

# Read measurements
measurement = protocol.read_measurement(timeout_s=1.0)
if measurement:
    print(f"Flow: {measurement.flow_ml_min} mL/min")
    print(f"Temp: {measurement.temp_c} °C")

# Stop and close
protocol.send_stop_command()
protocol.close()
```

### Key Timing Constants

Per [SLF3S-0600F datasheet Section 2.2](https://sensirion.com/media/documents/C4F8D965/66F56F53/LQ_DS_SLF3S-0600F_Datasheet.pdf):

| Parameter | Symbol | Min | Typical | Max | Unit | Source |
|-----------|--------|-----|---------|-----|------|--------|
| Power-up time | t_PU | - | - | 25 | ms | SLF3S datasheet Table 4 |
| Soft reset time | t_SR | - | - | 25 | ms | SLF3S datasheet Table 4 |
| Warm-up time | t_w | - | 60 | - | ms | SLF3S datasheet Table 4 |
| Update rate | f_flow | 180 | 400 | 500 | Hz | SLF3S datasheet Table 4 |
| I²C SCL frequency | f_SCL | - | 400 | 1000 | kHz | SLF3S datasheet Table 4 |
| **Teensy CDC enum** | - | - | 3.5 | - | s | **Empirical (Pi-specific)** |

**Implementation:**
```python
class TeensySerialProtocol:
    SENSOR_POWER_UP_MS = 25       # t_PU max
    SENSOR_SOFT_RESET_MS = 25     # t_SR max
    SENSOR_WARMUP_MS = 60         # t_w typical
    TEENSY_CDC_ENUMERATION_S = 3.5  # Pi needs longer than Mac
```

### Message Protocol

All messages are JSON lines (newline-terminated):

**Commands (Pi → Teensy):**
```json
{"cmd": "start", "rate": 50.0}
{"cmd": "stop"}
{"cmd": "status"}
{"cmd": "ping"}
{"cmd": "reset"}
```

**Responses (Teensy → Pi):**
```json
{"type": "measurement", "flow": 0.123, "temp": 25.4, "time": 12345, "count": 0}
{"type": "error", "error": "Sensor read failed, received 0 bytes", "time": 12345}
{"type": "status", "message": "Sensor started at 50.00 Hz (reset: 0)", "running": true, "rate": 50, "errors": 0}
{"type": "pong"}
{"type": "sensor_status", "running": true, "rate": 50, "samples": 1234, "errors": 0, "uptime": 56789}
```

### Error Handling

Per Sensirion best practices:

1. **"0 bytes" errors are NORMAL during warm-up**
   - Sensor may not respond during soft reset (25ms)
   - Ignore these errors in first 100ms after start
   - Implementation: `teensy_serial_protocol.py` filters these automatically

2. **I²C NACK errors require reset**
   - Send `{"cmd": "reset"}` to perform soft reset
   - Wait 30ms for reset completion
   - Re-send start command
   - Implementation: `uart_flow_sensor.py::_recover_i2c_error()`

3. **USB disconnects require reconnection**
   - Close serial port
   - Wait 2s for device to settle
   - Reopen port
   - Wait 3.5s for CDC enumeration
   - Send ping to verify
   - Implementation: `uart_flow_sensor.py::_attempt_reconnection()`

---

## GUI Configuration

### Step-by-Step Setup for Users

The RRR GUI provides a **Hardware** settings tab for configuring pump vs. solenoid delivery modes.

#### 1. Open Settings Tab
1. Launch RRR application: `cd ~/rodent-refreshment-regulator/Project && python3 main.py`
2. **Log in** (Settings are only accessible to logged-in users)
3. Navigate to **Profile** → **Settings** tab

#### 2. Configure Hardware Mode
In the **Hardware** sub-tab:

**Delivery Hardware Mode:**
- Select **`solenoid`** (default, recommended) or **`pump`**
- **Solenoid**: Flow sensor-based volumetric control (accurate, real-time feedback)
- **Pump**: Time-based peristaltic pump control (legacy mode)

**Flow Sensor Configuration (solenoid mode only):**
- **Teensy Port**: 
  - Click **Auto-Detect** to find Teensy automatically
  - Or manually enter port (e.g., `/dev/ttyACM0`, `/dev/teensy_flow`)
  - Click **Test Connection** to verify communication

- **Sampling Rate**: 50.0 Hz (default, matches test results)
  - Range: 1.0 – 100.0 Hz
  - Higher = more responsive, lower = less CPU load

- **Max Valve Open Time**: 20.0 s (safety cutoff)
  - Maximum time solenoid can remain open
  - Prevents runaway deliveries

- **No-Flow Timeout**: 3.5 s (default per integration tests)
  - Abort delivery if no flow detected for this duration
  - Detects occlusions, sensor failures, empty reservoir

- **Predictive Close Lag**: 10.0 ms (default)
  - Compensates for solenoid valve close delay
  - Reduces overshoot (tune based on valve characteristics)

#### 3. Save Settings
Click **Save All Settings** at the bottom of the Settings tab.

#### 4. Verify Configuration
**Test Sensor Connection:**
1. Ensure Teensy is plugged in via USB
2. In Hardware tab, click **Test Connection**
3. You should see: ✓ Teensy responded successfully!

**Troubleshooting:**
- ✗ Port not found → Run auto-detect or check USB cable
- ✗ Permission denied → Add user to `dialout` group: `sudo usermod -a -G dialout $USER` (then log out/in)
- ✗ No response → Verify firmware is uploaded to Teensy

#### 5. Create and Run Schedule
1. **Animals Tab**: Add animals (if not already present)
2. **Schedules Tab**: 
   - Create new schedule
   - Assign animals to cages
   - Set target volumes
   - Select **Instant** or **Staggered** delivery mode
3. **Run**: Click **Run** button
   - RRR will automatically use hardware mode from settings
   - Solenoid mode: Real-time flow monitoring in terminal
   - Pump mode: Time-based delivery

### GUI Testing Workflow

**Pre-Delivery Checklist:**
- [ ] Hardware mode configured (Settings → Hardware tab)
- [ ] Teensy connection tested (green checkmark)
- [ ] Animals assigned to cages
- [ ] Schedule created with target volumes
- [ ] Relay HAT initialized (visible in terminal on startup)

**During Delivery:**
- Monitor **System Messages** terminal for:
  - `✓ Flow sensor started (uart on /dev/ttyACM0)`
  - `Starting delivery for cage X: Y.YYY mL`
  - `cage=X flow=Z.ZZZ mL/min delivered=A.AAA mL` (1 Hz updates)
  - `Target reached for cage X`

**Post-Delivery:**
- Check delivered volumes in **Progress UI**
- Review logs for any errors or warnings

---

## Coding Standards

### Rule 1: Use Canonical Protocol

**✅ CORRECT:**
```python
from drivers.teensy_serial_protocol import TeensySerialProtocol

protocol = TeensySerialProtocol('/dev/ttyACM0')
protocol.connect()
protocol.send_start_command(rate_hz=50.0)
msg = protocol.read_message()
```

**❌ INCORRECT:**
```python
# DON'T duplicate serial communication logic!
import serial
ser = serial.Serial('/dev/ttyACM0', 115200)
time.sleep(2.5)  # Wrong timing!
ser.write(b'{"cmd":"start"}\n')
```

### Rule 2: Document Hardware References

All hardware-related code must reference official documentation:

```python
def pulse_relay(self, relay_id, duration_s=1.0):
    """
    Pulse a single relay per Sequent 16-Relays HAT specification.
    
    Per Sequent documentation:
    - set(relay_num, state): relay_num 1-16, state 0 or 1
    - Generates back-EMF on inductive loads (solenoids)
    - Star grounding mitigates conducted EMI
    
    Reference: https://cdn.shopify.com/s/files/1/0534/4392/0067/files/16-RELAYS-UsersGuide_d5e24457-bdd9-4e16-a307-7f90bbd668bb.pdf
    """
```

### Rule 3: Validate Data Ranges

Per [SLF3S-0600F datasheet Table 1](https://sensirion.com/media/documents/C4F8D965/66F56F53/LQ_DS_SLF3S-0600F_Datasheet.pdf):

```python
def _is_measurement_valid(self, flow_ul_min: float, temp_c: float) -> bool:
    """
    Validate sensor measurements against Sensirion SLF3S-0600F specifications.
    
    Per datasheet Table 1:
    - Flow range: ±2000 µL/min nominal, ±3250 µL/min saturation
    - Temp range: -10 to +70°C operating range
    """
    # Flow range: ±40 mL/min = ±40000 µL/min (safety margin)
    if not (-40000 <= flow_ul_min <= 40000):
        return False
    
    # Temperature range: -10 to +70°C
    if not (-10 <= temp_c <= 70):
        return False
    
    return True
```

### Rule 4: Handle Timing Correctly

**✅ CORRECT (using protocol constants):**
```python
# Start sensor
protocol.send_start_command(rate_hz=50.0)
# Protocol internally handles:
# - Soft reset: 25ms
# - Warm-up: 60ms
# - Status verification

# Wait for first valid measurement
measurement = protocol.read_measurement(timeout_s=0.5)
```

**❌ INCORRECT (magic numbers):**
```python
send_start()
time.sleep(0.1)  # Why 0.1? Should be 100ms per datasheet!
```

---

## Testing Strategy

### Phase 1: Sensor-Only Test (✅ PASSED - 99% frame delivery)

```bash
cd ~/rodent-refreshment-regulator/Project
python3 test_sensor_wiring.py --rate 10 --duration 20
```

**Success Criteria:**
- ✅ 95%+ frame delivery
- ✅ Stable USB connection
- ✅ Valid temperature readings

**Result:** 198/200 frames (99%) ✅

### Phase 2: Integration Test (⏳ PENDING)

```bash
python3 test_relay_sensor_integration.py --duration 60 --interval 3
```

**Success Criteria:**
- ✅ >95% frame delivery during relay switching
- ✅ Zero USB disconnects
- ✅ Max frame gap <2s
- ✅ <10 total errors

**Purpose:** Validate star grounding mitigates EMI from relay switching

### Phase 3: RRR Application Test (⏳ PENDING)

```bash
python3 main.py
# In GUI:
# 1. Verify Settings Tab shows hardware_mode="solenoid", uart_port="/dev/ttyACM0"
# 2. Create instant delivery: 0.5 mL, 1 minute from now
# 3. Run and observe: flow sensor streaming, valves open/close, volume integrated
```

**Success Criteria:**
- ✅ Flow sensor auto-detected
- ✅ Solenoid delivery completes
- ✅ Volume accuracy ±10%
- ✅ No USB disconnects

### Phase 4: Multi-Animal Stress Test (⏳ PENDING)

**Configuration:**
- 4 animals, staggered deliveries
- 2-hour window, 15-minute intervals
- Varying volumes: 1.0-2.5 mL

**Success Criteria:**
- ✅ All deliveries complete
- ✅ Zero USB disconnects over 2 hours
- ✅ Volume accuracy ±10% for all animals

---

## Troubleshooting

### Issue: Integration Test Fails (USB Disconnects)

**Symptoms:**
- `test_relay_sensor_integration.py` shows USB disconnects
- Frame loss >5%
- "Flow stream not available" errors

**Root Cause:** Back-EMF from solenoids coupling to USB despite star grounding

**Solution:** Add flyback diodes across solenoid coils

```
Solenoid Coil (+) ──┬──→ Relay NO
                    │
                   [Diode]  ← 1N4007 or equivalent
                    │       Cathode (band) to (+)
Solenoid Coil (-) ──┴──→ Terminal GND
```

**Re-test:** Run Phase 2 integration test after adding diodes

---

### Issue: "I²C error: 4" (NACK on address)

**Symptoms:**
- Teensy reports "Failed to start sensor, I2C error: 4"
- Sensor not detected

**Causes:**
1. Missing pullup resistors (most common!)
2. Wrong pullup value (should be 2kΩ, not 5.3kΩ or 10kΩ)
3. SDA/SCL pins swapped
4. Sensor not powered (check 3.3V)

**Debug:**
```bash
# With Teensy powered on:
# Measure voltage on Teensy Pin 18 to GND → should read ~3.3V
# Measure voltage on Teensy Pin 19 to GND → should read ~3.3V
# If <2.5V: missing or wrong pullups

# With Teensy powered OFF:
# Measure resistance Pin 18 to 3V3 → should read ~2kΩ
# Measure resistance Pin 19 to 3V3 → should read ~2kΩ
```

---

### Issue: "Sensor read failed, received 0 bytes"

**Symptoms:**
- Persistent "0 bytes" errors during streaming (not just startup)

**Causes:**
1. Sensor ground not connected properly
2. I²C clock too fast (should be 50kHz for breadboard)
3. Sensor damaged

**Debug:**
1. Verify sensor GND wired to breadboard row, then to terminal block
2. Check Teensy firmware uses `Wire.setClock(50000)`
3. Try different sensor if available

---

### Issue: RRR GUI doesn't auto-detect flow sensor

**Symptoms:**
- Settings Tab shows `hardware_mode="pump"` instead of `"solenoid"`
- `uart_port` not set

**Causes:**
1. Teensy not plugged in
2. Wrong USB cable (power-only, not data-capable)
3. Auto-detection logic not running

**Debug:**
```bash
# Check Teensy detected
ls -l /dev/ttyACM*
# Should show /dev/ttyACM0 or /dev/ttyACM1

# Test Teensy connection
python3 test_sensor_simple.py
# Should show measurements

# Check RRR settings
cat Project/settings.json | grep -A 5 "hardware_mode"
```

**Manual Override:**
1. Open RRR GUI → Settings Tab
2. Set `hardware_mode` = `"solenoid"`
3. Set `flow_sensor_type` = `"uart"`
4. Set `uart_port` = `"/dev/ttyACM0"`
5. Set `cage_relays` = `{"1": 15, "2": 16}`
6. Click "Save Settings"

---

## References

### Hardware Documentation
- [Teensy 4.1](https://www.pjrc.com/store/teensy41.html)
- [SLF3S-0600F Datasheet](https://sensirion.com/media/documents/C4F8D965/66F56F53/LQ_DS_SLF3S-0600F_Datasheet.pdf)
- [Sequent 16-Relays HAT User Guide](https://cdn.shopify.com/s/files/1/0534/4392/0067/files/16-RELAYS-UsersGuide_d5e24457-bdd9-4e16-a307-7f90bbd668bb.pdf)

### Software Components
- `drivers/teensy_serial_protocol.py` - Canonical serial communication
- `drivers/uart_flow_sensor.py` - Production flow sensor driver (uses protocol)
- `strategies/solenoid_flow_strategy.py` - Volume-based delivery logic
- `test_sensor_wiring.py` - Sensor-only diagnostic (99% validated)
- `test_relay_sensor_integration.py` - Integration test (relay + sensor)
- `test_sensor_simple.py` - Minimal test for debugging

---

## Change Log

| Date | Version | Changes |
|------|---------|---------|
| 2025-10-06 | 1.0 | Initial release - star grounding validated, canonical protocol implemented |

---

## License

MIT License -

