# Rodent Refreshment Regulator (RRR) – Solenoid + Flow Sensor Strategy

**Version 3.1 — August 20, 2025**

*Prepared for engineering, procurement, and deployment teams*

This document defines the validated, industry-grade architecture and implementation plan for Solenoid + Flow Sensor delivery in the Rodent Refreshment Regulator (RRR). It covers both Option A (R&D configuration) and Option B (Production configuration) with complete hardware specifications, vendor analysis, cost modeling, and implementation roadmap.

Sources
- Sensirion SLF3S‑0600F: https://sensirion.com/products/sensors/liquid-flow-sensors/slf3s-0600f/
- Sensirion SLF3S‑0600F Datasheet (PDF): https://sensirion.com/media/documents/83E76F65/63394A1E/Sensirion_Liquid_Flow_SLF3S-0600F_Datasheet.pdf
- The Lee Company – LHD Solenoid Valves: https://www.theleeco.com/products/solenoid-valves/lhd-series/
- The Lee Company – Lohm's Law Calculator: https://www.theleeco.com/resources/lohms-law-calculator/
- Guide for the Care and Use of Laboratory Animals (NRC/ILAR, 8th ed.): https://nap.nationalacademies.org/catalog/12910/guide-for-the-care-and-use-of-laboratory-animals-8th-edition
- AALAS/Facility best practices for potable water delivery (summary guidance consistent with the ILAR Guide).

---

## 1. Scope & Guarantees

This document defines the validated, industry-grade architecture for Solenoid + Flow Sensor delivery in RRR, covering:

- **Option A**: R&D configuration — per-cage sensor and dual solenoids (high precision, low scaling)
- **Option B**: Production configuration — centralized sensor, master solenoid + manifold + per-cage valves (cost-effective, scalable)

**Core Guarantees:**
- Hardware modes: Pump (existing) and Solenoid (new). User selects in Settings.
- **Per-valve calibration**: each valve maintains its own `mL/pulse` factor (in the DB, applied at runtime). The single global calibration assumed in earlier revisions of this document is superseded by the per-valve approach — see [`Project/VALVE_CALIBRATION_GUIDE.md`](Project/VALVE_CALIBRATION_GUIDE.md) and the in-app `Settings → Calibration` wizard.
- Serial delivery: One cage at a time (matches Pump strategy).
- Time-window behavior: We always deliver full volume. The time window is scheduling guidance; if infeasible, we continue in "overtime" until the target is reached, with clear UI warnings.
- Safety: Double shutoff (Option A) or master + per-cage shutoff (Option B), leak detection, watchdogs, and fail-closed behavior on power loss.
- Cleaning: Water-only to animals. Sanitization (if required by SOP) is off-line to waste, followed by verified rinse before reconnecting to animals (per ILAR/AALAS guidance).

---

## 2. Architecture Overview

| **Option** | **Topology** | **Relays/Cage** | **Extra Relays** | **Flow Sensors** | **Solenoids/Cage** | **Manifolds** | **Distinction** |
|------------|--------------|-----------------|------------------|------------------|---------------------|---------------|----------------|
| A | SolA + FS + SolB per cage | 2 | 0 | 1/cage | 2 | None | Maximum accuracy, simple software |
| B | Master Sol + FS + Manifold + 1 Sol/cage | 1 | +1 master | 1 total | 1 + 1 master | 1/8–15 cages | Lowest cost per cage, higher software load |

### 2.1 Option A Architecture (8 cages shown)
```mermaid
flowchart TB
  classDef blk fill:#0e1e2b,stroke:#183142,color:#eaf1f7;
  classDef bus fill:#0f2f3a,stroke:#205360,color:#dfeff5;
  classDef mod fill:#0e2230,stroke:#2a4a5a,color:#e8f3f8;

  end

  %% Cage module template
  subgraph C1["Cage 1 module"]
    class C1 mod
    A1["Solenoid A (12 V)"] --> FS1["SLF3S‑0600F"] --> B1["Solenoid B (12 V)"] --> DP1["Drinking point"]
  end
  subgraph C2["Cage 2 module"]  ; class C2 mod
    A2["Solenoid A"] --> FS2["SLF3S‑0600F"] --> B2["Solenoid B"] --> DP2["Drinking point"]
  end
  subgraph C3["Cage 3 module"]  ; class C3 mod
    A3["Solenoid A"] --> FS3["SLF3S‑0600F"] --> B3["Solenoid B"] --> DP3["Drinking point"]
  end
  subgraph C4["Cage 4 module"]  ; class C4 mod
    A4["Solenoid A"] --> FS4["SLF3S‑0600F"] --> B4["Solenoid B"] --> DP4["Drinking point"]
  end
  subgraph C5["Cage 5 module"]  ; class C5 mod
    A5["Solenoid A"] --> FS5["SLF3S‑0600F"] --> B5["Solenoid B"] --> DP5["Drinking point"]
  end
  subgraph C6["Cage 6 module"]  ; class C6 mod
    A6["Solenoid A"] --> FS6["SLF3S‑0600F"] --> B6["Solenoid B"] --> DP6["Drinking point"]
  end
  subgraph C7["Cage 7 module"]  ; class C7 mod
    A7["Solenoid A"] --> FS7["SLF3S‑0600F"] --> B7["Solenoid B"] --> DP7["Drinking point"]
  end
  subgraph C8["Cage 8 module"]  ; class C8 mod
    A8["Solenoid A"] --> FS8["SLF3S‑0600F"] --> B8["Solenoid B"] --> DP8["Drinking point"]
  end

  %% Bus connections (collapsed to avoid clutter)
  RES --- A1 & A2 & A3 & A4 & A5 & A6 & A7 & A8
  PSU --- A1 & B1 & A2 & B2 & A3 & B3 & A4 & B4 & A5 & B5 & A6 & B6 & A7 & B7 & A8 & B8
  HAT --- A1 & B1 & A2 & B2 & A3 & B3 & A4 & B4 & A5 & B5 & A6 & B6 & A7 & B7 & A8 & B8
  RPi --- FS1 & FS2 & FS3 & FS4 & FS5 & FS6 & FS7 & FS8
```

### 2.2 Per-cage detail (one module)
```mermaid
flowchart LR
  classDef mod fill:#0e2230,stroke:#2a4a5a,color:#e8f3f8;
  classDef bus fill:#0f2f3a,stroke:#205360,color:#dfeff5;

  subgraph MOD["Cage module (detail)"]
    class MOD mod
    A["Solenoid A (12 V)"] --> FS["SLF3S‑0600F"]
    FS --> B["Solenoid B (12 V)"]
    B --> DP["Drinking point"]
  end

  subgraph BUSES["Buses"]
    class BUSES bus
    RES["Reservoir"] --- A
    "GPIO via Relay HAT" --- A & B
    "I2C (3.3 V)" --- FS
    "12 V rail" --- A & B
  end
```

### 2.2 Option B Architecture (Master + Manifold)


---

## 3. Hardware Specification

### 3.1 Common Stack Components

- **Raspberry Pi 4/5** (existing)
- **Sequent 16-Relay HAT** (24 V / 2 A contact rating) - [Product Link](https://sequentmicrosystems.com/products/16-relays-stackable-card-for-raspberry-pi)
- **12 V DC PSU** (sized per strategy, see §3.3)

### 3.2 Per-Cage Bill of Materials

| **Component** | **Qty A** | **Qty B** |
|---------------|-----------|-----------|
| Solenoid valve (LHDA1233115H) | 2 | 1 (+1 master) |
| Flow sensor (SLF3S-0600F) | 1 | 0 (1 master) |
| Relay channels | 2 | 1 (+1 master) |
| Manifold (8-port) | — | Shared |

### 3.3 Power Budget (Per Active Cage)

| **Option** | **Energized Components** | **Current @ 12 V** | **PSU Recommendation** |
|------------|--------------------------|-------------------|------------------------|
| A | 2 solenoids | 0.60 A | 12 V / 3 A |
| B | 1 solenoid + master + manifold valve | 0.90–1.05 A | 12 V / 4–5 A |

*Note: Assumes 0.30 A per coil based on typical LHD series specifications. Actual current should be bench-measured.*

---

## 4. Scaling Example (100 Cages)

**Component Prices (Aug 2025):**
- **LHDA Solenoid** ≈ $80 USD — [Lee LHD Series](https://www.theleeco.com/products/solenoid-valves/lhd-series/)
- **SLF3S-0600F Flow Sensor** ≈ $55 USD — [Sensirion Product Page](https://sensirion.com/products/sensors/liquid-flow-sensors/slf3s-0600f/)
- **16-Relay HAT** ≈ $60 USD
- **Manifold and respective solenoids:**
  - SMC VQ1000 ≈ $400 + ~$40/valve — [SMC USA](https://www.smcusa.com)
  - Festo MH2 ≈ $450 + ~$65/valve — [Festo US](https://www.festo.com/us/en/)
  - Humphrey HEM ≈ $350 + ~$50/valve — [Humphrey Products](https://www.humphrey-products.com)

| **Option** | **HATs** | **Solenoids** | **Flow Sensors** | **Manifolds** | **Total Approx. Cost (USD)** |
|------------|----------|---------------|------------------|---------------|-------------------------------|
| A | 13 | 200 | 100 | 0 | $22,300 |
| B | 7 | 101 + 7 manifold solenoids | 1 | 7 | $11,355 (w/ SMC) |

> **Note:** Manifold vendors require use of their proprietary or compatible solenoids. Valve cost per port is included above for each vendor.

---

## 5. Feasibility & Flow Safety Margins

**Sensor Range:** 0–600 mL/min (design target: 60 mL/min)

**Feasibility Calculation:**
```
T_min_total = ∑ (V_i / 60 mL/min) × 1.2 (safety margin)
```

**Rules:**
- If T_window < T_min_total → Block with rationale
- If window expires → Continue as "Overtime" with telemetry

**Physics Basis:**
- Sensor measurable band: 30–400 mL/min (conservative, well below saturation)
- Valve hydraulic limit using Lee Lohm's Law: Q [gpm] = sqrt(ΔP / L)
  - Example: L=1500, ΔP=0.43 psi → Q ≈ 64 mL/min
  - [Lohm's Law Reference](https://www.theleeco.com/resources/lohms-law-calculator/)

---

## 6. Manifold Selection (Option B)

> **Important:** Each manifold system requires use of its compatible proprietary solenoid valves. Total price and power calculations must include these. Solenoids are specified below.

### 6.1 Evaluated Solutions

| **Vendor** | **Model** | **Ports** | **Power** | **Control** | **Solenoid Valve Link** | **Manifold Link** | **Cost / 8-port (w/ valves)** | **Notes** |
|------------|-----------|-----------|-----------|-------------|-------------------------|-------------------|-------------------------------|----------|
| SMC | VQ1000 | 2–24 | 12/24V | Parallel/Serial | [SMC Product Search](https://www.smcusa.com) | [SMC USA](https://www.smcusa.com) | ~$400 + $320 = $720 | Preferred, modular |
| Festo | MH2 Series | 2–12 | 12/24V | IO-Link/CAN | Contact Festo Sales | [Festo US](https://www.festo.com/us/en/) | ~$450 + $520 = $970 | Compact, advanced control |
| Humphrey | HEM Series | 2–16 | 12/24V | Discrete | Contact Humphrey Sales | [Humphrey Products](https://www.humphrey-products.com) | ~$350 + $400 = $750 | low profile |

### 6.2 Recommendation

- Use **SMC VQ1000** for most cases (price/performance, global availability)
- Choose **Festo MH2** for tight installations or advanced IO integration
- Prefer **Humphrey HEM** for budget-sensitive US installations

---

## 7. Installation & Maintenance

| **Option** | **Install Effort** | **Maintenance** | **Notes** |
|------------|-------------------|-----------------|----------|
| A | High | Sensor per cage | Simple software, tubing-intensive |
| B | Medium | Manifold ports (annual) | Centralized plumbing, purge logic required |

---

## 8. Control Algorithm (SolenoidFlowStrategy)

### 8.1 State Machine (per delivery)
- **Prime** (optional): brief fill to remove bubbles; close both; short settle
- **Deliver:**
  - Open A, then (20–40 ms later) open B
  - Start high-rate sensor reads; integrate volume V_delivered
  - Predictive cutoff: when V_delivered ≥ V_target − V_lag, close A then B
    - V_lag = q_avg_last_100ms × τ_close (use τ_close ≈ 8–15 ms)
- **Settle:** read residual flow; if > threshold, bleed to zero
- **Log:** volume, duration, temperature, warnings

### 8.2 Safety & Faults
- **Leak detection:** if both valves closed AND flow > threshold → critical alert
- **Sensor fault:** CRC/I²C errors → pause, retry, fail if persistent
- **Power loss:** valves fail-closed; resume at next safe point

---

## 9. Software Architecture

### 9.1 New Modules
- `drivers/flow_sensor.py`: SLF3S‑0600F I²C driver with CRC‑8, filtering
- `drivers/solenoid_controller.py`: Relay HAT wrapper with state management
- `strategies/solenoid_flow_strategy.py`: Implements DeliveryStrategy interface
- `utils/calibration.py`: Zero-flow and span calibration with JSON storage

### 9.2 Updated Modules
- `gpio/relay_worker.py`: Strategy factory, feasibility check, overtime telemetry
- `ui/SettingsTab.py`: Hardware mode selector with solenoid sub-forms
- `ui/run_stop_section.py`: Live flow/volume/ETA, overtime banner
- `installer/requirements.txt`: Add sensirion-i2c-slf3x

### 9.3 Key Interfaces
```python
class DeliveryStrategy(Protocol):
    async def deliver(self, cage_id: int, target_ml: float) -> bool: ...
    async def clean(self, cage_id: int, to_waste: bool = True) -> None: ...

class FlowSensor(Protocol):
    def zero_calibrate(self) -> None: ...
    async def read(self) -> AsyncIterator[FlowSample]: ...
```

---

## 10. UI/UX Details

### 10.1 Pre-run Interface
- **Feasibility card:** Shows computed T_min_total, user window, pass/fail with physics reasoning
- **Hardware selector:** Pump vs Solenoid mode with dynamic sub-forms

### 10.2 Runtime Interface
- **Per-cage panels:** Live flow (mL/min), delivered (mL), remaining (mL), ETA
- **Overtime banner:** When window elapsed, shows cumulative overtime clock
- **Fault toasts:** "Leak suspected on Cage X" with isolation status

### 10.3 Cleaning Interface
- **Water-only to animals:** Post-run flush routines
- **Sanitization to waste:** Optional disinfectant routing with mandatory rinse

---

## 11. Calibration

- **Zero-flow:** Auto on startup with valves closed (store offset per sensor)
- **Span check:** Optional 1-point verification (dispense 1.00 mL to scale)
- **Storage:** Per-sensor factors in `settings/calibration.json` keyed by I²C address

---

## 12. Safety & Compliance

### 12.1 Animal Welfare (ILAR/AALAS Aligned)
- **Water quality:** Potable water only; no disinfectants to animals
- **Cleaning protocol:** Water flush to animals; sanitization to waste with validated rinse
- **Volume guarantee:** Always deliver full target volume, even in overtime

### 12.2 System Safety
- **Fail-safe design:** Valves default closed on power loss
- **Leak detection:** Flow monitoring when valves commanded closed
- **Fault isolation:** Per-cage isolation in Option A; master shutoff in Option B

---

## 13. Testing & Validation

### 13.1 Bench Tests
- **Flow calibration:** 60s flow test per cage → update feasibility constants
- **Accuracy test:** 10× 1.00 mL deliveries → verify ±0.05 mL precision
- **Leak simulation:** Command valves closed → verify alert triggers

### 13.2 System Tests
- **Nominal schedule:** 8 cages × 3 mL, feasible window → on-time completion
- **Overtime test:** Undersized window → block, then override → complete with overtime telemetry

---

## 14. Deployment Checklist

### 14.1 Software Dependencies
- Add to `installer/requirements.txt`:
  - `sensirion-i2c-slf3x` (or `sensirion-i2c-driver` + SLF3x)
  - `numpy` for filtering
  - Optional `scipy` for IIR design

### 14.2 Hardware Setup
- Enable I²C on Raspberry Pi
- Confirm sensor I²C addresses
- Run calibration wizard
- Perform dry-run to waste

### 14.3 Validation
- Test all cage accessibility
- Verify flow sensor readings
- Confirm leak detection
- Document baseline performance

---

## 15. References

1. **Sensirion SLF3S‑0600F:** [Product Page](https://sensirion.com/products/sensors/liquid-flow-sensors/slf3s-0600f/) | [Datasheet (PDF)](https://sensirion.com/media/documents/83E76F65/63394A1E/Sensirion_Liquid_Flow_SLF3S-0600F_Datasheet.pdf)
2. **Lee Solenoid Valves (LHD family):** [Family Overview](https://www.theleeco.com/products/solenoid-valves/lhd-series/)
3. **Lee Lohm's Law:** [Calculator & Overview](https://www.theleeco.com/resources/lohms-law-calculator/)
4. **ILAR Guide:** [Guide for Care and Use of Laboratory Animals](https://nap.nationalacademies.org/catalog/12910/guide-for-the-care-and-use-of-laboratory-animals-8th-edition)
5. **Sequent 16-Relay HAT:** [Product Page](https://sequentmicrosystems.com/products/16-relays-stackable-card-for-raspberry-pi)
6. **SMC USA:** [Main Site](https://www.smcusa.com) (Search for VQ1000 series)
7. **Festo US:** [Main Site](https://www.festo.com/us/en/) (Contact sales for MH2 series)
8. **Humphrey Products:** [Main Site](https://www.humphrey-products.com) (Contact sales for HEM manifolds)

---

*Updated 2025-08-20 to incorporate vendor-specific solenoids, pricing implications, and engineering requirements.*