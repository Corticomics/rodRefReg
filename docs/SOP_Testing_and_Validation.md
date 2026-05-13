# Rodent Refreshment Regulator (RRR)
# Standard Operating Procedure (SOP)
# System Validation, Testing, & Pilot Experiment

---

## 1. Purpose
Establish a rigorous, reproducible protocol for validating the **RRR** hardware & software stack and executing the 1-month pilot experiment comparing **Automated (RRR-watered)** versus **Manual (bottle-watered)** mice.

## 2. Scope
• Raspberry-Pi control software (PyQt5 UI, GPIO drivers, IR drinking module).  
• SM16-RELIND pump hats & tubing.  
• Eight C57BL/6J mice (4 ♂ / 4 ♀).  
• Rack "Nest" zone configured for two experimental rows.

## 3. Roles & Responsibilities
| Role | Name(s) | Responsibilities |
|------|---------|------------------|
| PI / Neuroscientist / Sr\. SW | Jackson & Steve | Approval, ethical oversight, senior software guidance |
| SW Engineer / Architect | Jose | Code development, architecture, CI |
| Behaviour / Animal Lead | Jamie | Progressive\-ratio task design, daily animal oversight |
| Hardware Techs | Jose & Jamie | Pump calibration, leak tests |
| Animal / OHRBETS Consultant | Adrianna | Cage setup, husbandry, surgery guidance |

## 4. Definitions
*PR* = Progressive Ratio behavioural task; *CV* = Coefficient of Variation.

---

## 5. Pre-Experiment Checklist
1. **Nest Planning**  
   a. Reserve two contiguous rack rows.  
   b. \*Final layout (2025-06-26 meeting)\*: **Top shelf** – Pi, SM16\-RELIND hats, power supplies, 2\-L water reservoir; **Middle shelf** – cages for RRR \(automated\) mice; **Lower shelf** – cages for manual bottle\-watered mice\.  
   c\. Detach water manifolds; install \*dummy\* cages for cable routing tests.
2. **Cleaning & Sterile Setup**  
   • Autoclave cages, sipper tubes, connectors.  
   • Wipe Pi case, pumps, sensors with 70 % EtOH.
3. **Hardware Installation**  
   • Mount Pi & SM16-RELIND HATs on rack side-panel.  
   • Choose delivery hardware:  
     – **Solenoid mode (default)**: pressurized reservoir → master solenoid on relay 16 → per-cage solenoid valves on relays 1–15; Teensy 4.1 + SLF3S-0600F flow sensor on the master line (see `Project/docs/FLOW_SENSOR_INTEGRATION_GUIDE.md`).  
     – **Peristaltic mode (legacy)**: 4–8 peristaltic pumps + tubing (ensure < 30 cm head drop).  
   • Position IR beam-break sensors per cage (see `Project/ir_module/`).
4. **Software Flash & Configuration**  
   • Flash Raspberry Pi OS 12-Lite.  
   • Run the one-line installer: `curl -fsSL https://raw.githubusercontent.com/Corticomics/rodRefReg/main/setup_rrr.sh | sudo bash` (handles I²C, dependencies, venv, DB, service).  
   • Confirm I²C bus auto-detected (the installer probes both bus 1 and bus 0).  
   • If migrating an older install, run `python Project/migrations/migrate_settings.py`.
5. **Cage Naming**: open the **Cages** tab and assign a custom name to each relay channel; names propagate to the Wizard and Calibration tables.
6. **Calibration & QA** (see § 8) — use **Settings → Calibration → Run Calibration Wizard**.
7. **Priming** — use **Settings → Priming** to flush lines before any data collection.
8. **IR Module Bench Test** (see § 10)
7. **Regulatory Approvals**  
   • IACUC / AWERB amendment approved & logged.

---

## 6. Experimental Design
| Group | n (♂/♀) | Water Source | Handling/Weighting | PR Training |
|-------|---------|-------------|-------------------|-------------|
| **Automated** | 4 (2/2) | RRR pumps | daily weighting Maybe:(**No** daily handling/weight and weeknd's) | Every other day |
| **Manual** | 4 (2/2) | Bottles | Daily weight; handled whenever auto group cages touched | Every other day |

*Weekend Schedule*: identical for both groups (bottles on Sat/Sun).

---

## 7. System Verification — **Completed**
The entire software & hardware stack passed all the initial verification tests 

## 8. Software Verification Strategy
1. **Static Analysis**  
   • `flake8`, `black --check`, `mypy Project/`.  
   • Security audit: `bandit -r Project/`.
2. **Unit Tests**  
   Located in `Project/tests/`. Minimum coverage 80 %. Key areas:  
   • `gpio/gpio_handler.py` (mock bus).  
   • `controllers/pump_controller.py` dosing logic.  
   • `ir_module/utils/test_utilities.py` session detection.  
   • `models/database_handler.py` CRUD + migrations.
3. **Integration Tests**  
   a. **Pump Loop Test** (`test_relay_diagnostic.py`): 100 triggers/pump (sealed & unsealed). Log volume and time per trigger; assert CV < 5 %.  
   b. **Schedule Replay**: load fixture JSON → run `RelayWorker` in mock-GPIO; compare emitted `dispensing_history` rows with ground-truth.
4. **Hardware-in-the-Loop (HIL)**  
   CI job runs nightly on lab Pi via GitHub Actions self-hosted runner, executing HIL tests and pushing artefacts to Slack.
5. **Acceptance Tests**  
   Conducted by Jamie & Adrianna on staging rack before live animals.

## 8. In-Vivo Feedback & Adjustment Plan
1. **Data Streams Monitored**  
   • Dispensed volume vs target (`dispensing_history`).  
   • Animal body weight (manual & scale-connected).  
   • IR drink events (`ir_module/data`).  
   • PR task breakpoint & trial counts.  
   • Vet/OHRBETS health observations.  
   All records are timestamped and stored in the SQLite DB; nightly ETL pushes snapshots to the lab NAS.
2. **Automated Daily QC**  
   Cron job `scripts/daily_qc.py` executes at 23:59 to compute:  
   • Cumulative intake (mL) & deviation.  
   • Weight change %.  
   • Sensor fault rate.  
   Any metric outside predefined thresholds triggers a Slack alert tagged `#rrr-alerts`.
3. **Weekly Review Meeting**  
   Every Monday 09:00, Jamie screens dashboards (Grafana) and summarises anomalies; minutes logged via `DatabaseHandler.log_action`.
4. **Parameter Adjustment Workflow**  
   a. Create GitHub issue referencing anomaly ID.  
   b. Branch `hotfix/param_<YYYYMMDD>`, update JSON config or SettingsTab UI.  
   c. Peer review by Jose; PI sign-off for welfare-relevant changes.  
   d. Merge → CI pipeline redeploys to Pi; version tag `v1.x+rev`.
5. **Hardware Calibration Loop**  
   • If delivered/target deviation > 5 % on two consecutive days, run `scripts/pump_recalibrate.py` after lights-off.  
   • For IR sensors, threshold auto-tunes using 24-h rolling median noise floor.
6. **Validation of Adjustments**  
   • 24-h A/B comparison between updated and baseline parameters on two RRR mice.  
   • Metrics must show ≥ 95 % success rate & no adverse health signs before rollout to all animals.
7. **Ethical Oversight**  
   Any change impacting water volume or task difficulty requires PI (Jackson or Steve) approval and IACUC notification.

---

## 9. Delivery Hardware Testing Protocol

This section covers both delivery modes. Use the **Calibration Wizard** (Settings → Calibration → Run Calibration Wizard) to execute the per-cage runs; bench tests can be run from `tools/valve_calibration_tool.py` if Pi access is required without the UI.

1. **Prime First** — Always prime tubing via **Settings → Priming** before recording calibration data. Air slugs invalidate volumes.
2. **Solenoid Mode Metrics**  
   • Per-pulse volume from the inline SLF3S-0600F flow sensor (mL).  
   • Master-valve open duration and pulse count.  
   • Flow-sensor stream health (no NACK / packet-loss events).
3. **Peristaltic Mode Metrics**  
   • Delivered volume per trigger (mass/ρ).  
   • Flow rate (mL/s).  
   • Motor temperature < 40 °C.
4. **Shared Acceptance Criteria**  
   • Mean ± CV ≤ 5 % across 100 pulses per channel.  
   • No leaks or missed triggers.  
   • All channels produce non-zero, monotonic volumes.
5. **Database Logging**  
   Calibration results are stored in `dispensing_history` with `schedule_id = -1`; per-channel calibration factors are written to the calibration table and applied automatically at runtime.


---

## 12. Mouse Surgery & Recovery


---

## 10. IR Drinking Module Validation

1. **Enable the module** per `Project/ir_module/ENABLING.md` (sets the `ir_module.enabled` flag in `settings.json`).
2. **Bench test**: with the Pi powered, interrupt each beam manually for 1 s; verify an event appears in the Drinking Analysis tab and in `ir_module/data`.
3. **Cross-check**: after running a 24 h schedule, the cumulative drink-event count per cage should correlate with the corresponding `dispensing_history` totals (Spearman ρ ≥ 0.8).
4. **Sensor health**: confirm fault rate ≤ 1 % per 24 h via the daily QC script.

## 11. Progressive-Ratio (PR) Task Plan

## 13. Deployment & 4-Week Trial
1. **Day -2**: Move calibrated pumps & Pi to cleaned rack.  
2. **Day -1**: Load animals; start water restriction (refer to vet policy).  
3. **Day 0**: Begin RRR & manual bottle protocols.  
4. **Daily Routines**  
   • Manual group: weigh at 10:00; bottle refill 10 mL.  
   • Automated group: *no handling*.  
   • Both groups: PR training at 14:00 on alternate days (Mon/Wed/Fri).
5. **Weekend**  
   • Manual groups receive bottles (50 mL).  
6. **Data Capture**  
   • RRR auto-logs dispensing & IR events.  
   • Manual group volumes weighed & entered via UI `Animals Tab`.

---

