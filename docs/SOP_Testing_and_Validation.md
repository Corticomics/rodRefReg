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
   • Mount Pi & SM16-RELIND hats on rack side-panel.  
   • Route 4 × peristaltic pumps + tubing (ensure <30 cm head drop).  
   • Position IR beam-break sensors (see `Project/ir_module/hardware/ir_sensor.py`).
4. **Software Flash & Configuration**  
   • Flash Raspberry Pi OS 12-Lite, enable I²C (`enable_i2c.sh`).  
   • Clone repo, create venv: `python -m venv venv && source venv/bin/activate`.  
   • `pip install -r installer/requirements.txt`.  
   • Run **Installer UI** (`installer/main.py`) → generate `settings.json`.  
   • Verify DB migration runs (`python Project/migrations/migrate_settings.py`).
5. **Pump Calibration & QA** (see § 8)  
6. **IR Module Bench Test** (see § 9)
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

## 9. Pump Testing Protocol
1. **Environment Stress Test**  
 explain why we need to prime the pumps and let the use decide
2. **Metrics Recorded**  
   • Delivered volume per trigger (mass/ρ).  
   • Flow rate (mL/s).  
   • Leak incidence.  
   • Temperature & Humidity.
3. **Acceptance Criteria**  
   • Mean ± CV ≤ 5 %.  
   • No leaks or missed triggers.  
   • Motor temperature < 40 °C.
4. **Database Logging**  
   Results stored in `dispensing_history` with `schedule_id = -1` (calibration).


---

## 12. Mouse Surgery & Recovery


---

## 10. IR Drinking Module Validation & 11. Progressive-Ratio (PR) Task Plan d

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

