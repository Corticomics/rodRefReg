# Topology Validation — proving the independent rig against the manifold rig

RRR runs two valve topologies from one codebase ([HARDWARE_SETUP.md §7.2](HARDWARE_SETUP.md#72-why-the-master-valve-is-on-channel-16)):

| `valve_topology` | Fluid path | Per delivery |
|---|---|---|
| `shared_manifold` (default; the production rig) | one syringe → master valve (relay 16) → manifold → one valve per cage | master primed and held open across the pulse train |
| `independent` | one syringe → one valve → one spout, per animal | cage valve pulsed only; relay 16 never driven |

Before an animal goes on an independent rig, this document is how the lab shows it delivers water **as precisely as the manifold rig**. It pre-declares the criteria (nothing is decided after seeing the numbers), gives the bench recipe, and names the tools that grade the result. Criteria C1–C8 are beaker tests; only C9 involves an animal.

**Both rigs run the same tagged release** (v1.21.0 or later, which records the context of every delivery). The only difference between them is one setting, set with `tools/set_valve_topology.py`. Never put a `-beta` tag on a device for this: the updater ignores pre-releases and the device is stranded.

---

## 1. Principles

1. **Compare to what was fired, not to the nominal dose.** Water leaves a valve in whole pulses. The figure to hold a rig to is `pulses_fired × mL/pulse` (the app records both per delivery); the distance between that and the nominal dose is the planner's rounding, graded separately (C3). A rig that fires the planned pulses and delivers their calibrated volume has done its job.
2. **Freeze the calibration before the doses.** Calibrate a cage (C1), then run its dose sets against that calibration. Recalibrating between sets makes the sets incomparable; the app now records which calibration row each delivery used, so a mixed set is visible in the ledger.
3. **Characterise the hardware under nearest rounding, validate the production policy.** Run C1–C4 with **Settings → Delivery → Pulse Mode → "Round doses up"** *off*, so the shortfall you measure is physics, not policy. Run C5–C9 with the setting the animals will actually get (on the manifold rig with the needle, that is *on*; see [CALIBRATION_QUICK_START.md → Dose rounding policy](CALIBRATION_QUICK_START.md#dose-rounding-policy)).
4. **Weigh promptly.** The lab's animals drink immediately, so evaporation is not modelled; on the bench, weigh within a minute of the delivery. Record the raw balance readings, never a mental subtraction.
5. **n = 10 per cell**, three or more doses, as ISO 8655-6 does for pipettes. Below ten the tools list a cell but refuse to grade it.

### The manifold baseline (Parker 003-0257-900, 30 ms pulse / 1000 ms interval)

These are the bench figures the criteria are graded against. They come from the manifold rig's own beaker runs (see the calibration sheets); refresh them if the rig or the profile changes.

| Quantity | Value |
|---|---|
| mL per pulse, `q` | 34.164 µL without the upstream needle; **32.936 µL with the 16 G needle the lab keeps** |
| Pulse calibration CV (three 250-pulse runs) | 1.0 % |
| Dose CV, 0.3–1.0 mL, n = 10 | 3.1–5.5 % |
| Per-dose shortfall vs pulses × q (needle rig) | 13–19 µL, i.e. about half a pulse, independent of dose |
| Lab tolerance | **5 % maximum** on any dose (the mice take 0.6, 0.7 and 1.0 mL per day) |

---

## 2. Acceptance criteria

`q` is the cage's own mL/pulse from C1; `q/2` is half a pulse (≈ 16 µL on the needle rig).

| # | Criterion | Test | Pass (independent rig) | Graded by |
|---|---|---|---|---|
| **C1** | Pulse calibration | Every cage that will carry an animal: 250 pulses × 3 runs at 30 ms / 1000 ms through the wizard | CV of the three run means ≤ 1.5 % (manifold 1.0 %); first→last run drift ≤ 3 %; q ≤ 40 µL | Wizard figures, recorded by hand (§3.2) |
| **C2** | Precision | 0.3 / 0.6 / 0.7 / 1.0 mL, n = 10 each, via a real instant schedule, each weighed | CV ≤ 5.0 % **and** SD ≤ SD_manifold × 1.371 at the same dose (CLSI EP15-A3 upper verification limit for n = 10) | `topology_compare.py` |
| **C3** | Planner parity | Every weighed delivery, from the ledger | `pulses_fired` equals the count the planner should have fired for the dose: nearest, or rounded up under the setting. A `mismatch` is a code regression, never a hardware finding | `topology_compare.py` (`gravimetric_check.py list` shows it per row) |
| **C4** | Trueness / shortfall | Per dose, under nearest rounding | \|mean weighed − pulses × q\| ≤ q/2. Report the independent rig's shortfall next to the manifold's: with neither needle nor manifold, ≈ 0 is the expected and informative result | `topology_compare.py` |
| **C5** | Daily total | Simulated 0.6 mL and 1.0 mL mouse-days in the staggered chunks the schedule uses, ≥ 3 consecutive days, production rounding policy | Each day's weighed total within ± 5 % of the prescribed day | Ledger sums (§3.5) + weighings |
| **C6** | Start-up after idle | First dose after ≥ 12 h idle and after a 48 h weekend | Within C2/C4; \|first dose − mean of the next nine\| ≤ q/2 (a primed syringe line is reported to hold ~3 days; this measures it) | `gravimetric_check.py` rows, compared by hand |
| **C7** | Drift over days | 0.6 mL × 10 on days 1, 3 and 7, same calibration | Each day's mean within ± 3 % of day 1 | `topology_compare.py` on one CSV per day |
| **C8** | Syringe fill level (independent-specific) | 0.6 mL × 10 with the syringe full, half full, and ≤ 2 mL | Mean shift between fill levels ≤ q/2. A larger shift means a fill-level term is needed before animals go on (none exists in the delivery path today) | `topology_compare.py` on one CSV per fill level, `--min-n 10` |
| **C9** | Operational (the only animal criterion) | Every cage that will carry an animal passes C1 and the 0.6 mL × 10 set; the full dose grid and C6–C8 on ≥ 3 representative cages; then one animal per cage on ≥ 3 cages for ≥ 14 days | Daily weights and per-animal delivered totals within ± 5 % of the prescribed day; partial / failed / `sensor_failure` row rate no higher than the manifold rig's | Animal records + ledger |

**Equivalence.** "As precise as the manifold rig" means, at each dose: SD_independent ≤ SD_manifold × 1.371 (n = 10) **and** \|mean_independent − mean_manifold\| ≤ 2.5 % of the dose. `topology_compare.py` grades both once it has ten weighed rows per dose from each rig.

**Exit.** Every criterion passes on every animal-carrying channel across the three-day window, and the 14-day observation shows no weight excursions. After that both rigs simply keep running the same releases; the topology setting is a permanent configuration, not a flag to remove.

---

## 3. Bench recipe

### 3.1 Set up the independent rig

1. Build and wire per [HARDWARE_SETUP.md](HARDWARE_SETUP.md): one relay per valve, relay 16 **unwired** (it stays reserved on this release).
2. Install the same release as the manifold rig. The version is in the main window's title bar (and in `~/rrr/current/Project/version.py`).
3. Set the topology with the app stopped, then start it and confirm the log line:
   ```bash
   systemctl --user stop rrr.service
   cd ~/rrr/current/Project
   ~/rrr/shared/venv/bin/python3 tools/set_valve_topology.py independent --yes
   systemctl --user start rrr.service
   journalctl --user -u rrr.service -n 50 | grep TOPOLOGY     # [TOPOLOGY] Valve topology: independent (...)
   ```
4. Prime each line from **Settings → Priming** (on the independent rig there is no master step: select the cage, **Open Selected**, **Close Selected**). Check the lines every day; a primed syringe line has been seen to hold about three days.
5. Fill each syringe to a known level and note it (C8 uses the level).

### 3.2 C1 — calibrate and freeze

For every cage that will carry an animal, in **Settings → Calibration → Run Calibration Wizard**: 250 pulses, **30 ms pulse width, 1000 ms interval**, weigh, save. Repeat three times and write down the three mL/pulse figures per cage:

| cage | run 1 | run 2 | run 3 | CV of the three (%) | drift run 1→3 (%) | q saved (µL) |
|---|---|---|---|---|---|---|

CV ≤ 1.5 %, drift ≤ 3 %, q ≤ 40 µL. The **last** saved run is the calibration in force; do not recalibrate that cage again until its dose sets are done.

### 3.3 C2–C4 — weighed doses

With **"Round doses up" off**:

1. Put a tared beaker under the cage.
2. Create an **instant** schedule (schedule wizard, step 1: *Instant*) with one animal on that cage and the dose (0.3, 0.6, 0.7 or 1.0 mL), run it, weigh promptly. Ten times per dose per cage. The app writes one `dispensing_history` row per delivery.
3. On the device, list the deliveries and record each weighing against its row id (the database is opened read-only, so this is safe while the app runs):
   ```bash
   cd ~/rrr/current/Project
   ~/rrr/shared/venv/bin/python3 tools/gravimetric_check.py list --last 20
   ~/rrr/shared/venv/bin/python3 tools/gravimetric_check.py weigh 1234 --gross 12.7413 --tare 12.1435 --temp-c 22
   ~/rrr/shared/venv/bin/python3 tools/gravimetric_check.py weigh 1235 --net 0.5988            # balance tared
   ```
   `list` shows, per row, the topology, pulses fired, mL/pulse, the calibration row, the volume those pulses should have produced, the planner verdict (`nearest` / `up` / `both` / `mismatch`) and, once weighed, the measured volume and the shortfall. `weigh` keeps the raw gross and tare, the water temperature and the density it used, and a snapshot of the delivery row in `~/rrr/shared/data/gravimetric_checks.csv`. A second reading for the same row is refused unless you pass `--replace`.
4. Do the same doses on the manifold rig (same day where possible). Its rows carry `shared_manifold` and are the baseline side.

### 3.4 Grade

Copy both CSVs to a laptop and run the comparison (Python 3, no dependencies):

```bash
scp pi-manifold:~/rrr/shared/data/gravimetric_checks.csv manifold.csv
scp pi-independent:~/rrr/shared/data/gravimetric_checks.csv independent.csv
python3 Project/tools/topology_compare.py manifold.csv independent.csv --json report.json
```

The report lists every topology / cage / dose cell (n, mean, SD, CV, q, expected, shortfall, bias vs nominal, planner verdict counts) with C2 / C3 / C4 marks, the pooled per-topology cells, and the equivalence lines per dose (SD against the upper verification limit, mean difference against 2.5 % of the dose). Exit status 0 means every graded criterion passed; 1 names what failed; a report with nothing graded (fewer than ten rows per cell) is not a pass. Keep `report.json` with the run.

### 3.5 C5–C8 — days, idle, drift, fill level

Switch **"Round doses up"** to the production setting first.

- **C5** — schedule a normal staggered day (the same chunking the animals get) at 0.6 mL and at 1.0 mL, three consecutive days, weighing the day's total per cage. The ledger side is the day's sum of `volume_actual_ml`:
  ```bash
  sqlite3 ~/rrr/shared/data/rrr_database.db "SELECT relay_unit_id AS cage, substr(timestamp,1,10) AS day, \
    COUNT(*) AS rows, ROUND(SUM(volume_actual_ml),4) AS planned_ml, topology \
    FROM dispensing_history WHERE status='completed' GROUP BY cage, day, topology ORDER BY day, cage;"
  ```
- **C6** — leave the rig idle ≥ 12 h, then a 48 h weekend; the first delivery after each idle is weighed with the next nine. Use `gravimetric_check.py list --since <date>` to find the rows.
- **C7** — the 0.6 mL × 10 set again on days 3 and 7 without recalibrating; grade each day's CSV copy with `topology_compare.py` and compare the means to day 1 by hand (± 3 %).
- **C8** — the 0.6 mL × 10 set with the syringe full, half full and near empty; grade each fill level's CSV separately and compare the means (≤ q/2).

### 3.6 C9 — animals

Only after C1–C8 pass on the cages concerned, and per the lab's welfare protocol: one animal per cage, daily weights, per-animal delivered totals from the ledger, and the row-status rate:

```bash
sqlite3 ~/rrr/shared/data/rrr_database.db "SELECT status, COUNT(*) FROM dispensing_history \
  WHERE timestamp >= '2026-10-01' GROUP BY status;"
```

---

## 4. Reading the results

| Observation | Meaning | Next step |
|---|---|---|
| `mismatch` in the planner column | The pulse count is neither the nearest nor the rounded-up count for the dose | Code regression: stop, record the row id, report it. Not a hardware finding |
| C4 shortfall ≈ 0 on the independent rig, ≈ q/2 on the manifold rig | Expected: the needle and manifold retain water, a syringe-to-spout line does not | Report both; it is the reason the manifold rig runs with "Round doses up" and the independent rig may not need to |
| C2 CV over 5 % on one cage only | That valve or line | Re-prime, re-run C1 for that cage, repeat; replace the valve if it persists |
| C2 CV over 5 % on every cage | Systematic: balance, weighing technique, timing profile | Check the balance with a reference mass; confirm 30 ms / 1000 ms in the calibration table |
| C8 mean shift > q/2 between fill levels | Head pressure from the syringe column matters | A fill-level term must be built before animals go on; until then keep the syringe in the band that passed |
| `calibration_id` blank in the CSV | The cage was uncalibrated: the delivery ran on the empirical default | Calibrate (C1) and discard the rows |
| `topology` blank | Rows written by a release before v1.21.0 | Update both rigs; the tools still list and weigh such rows |

---

## 5. Records to keep

For every validation run: the release version, the topology and `q` per cage, the rounding policy, the `gravimetric_checks.csv` of each rig, the `report.json` files, the C1 table, the C5 daily totals, and the animal records for C9. `DATABASE.md` documents the columns the ledger carries per delivery.

---

## 6. Rollback

- To take a rig off the independent topology: `tools/set_valve_topology.py shared_manifold` with the app stopped, then restart.
- Before rolling a rig **back to a release older than v1.20.0**, set the topology back to `shared_manifold` first: the older release ignores the setting and would drive relay 16 on every delivery.
- The validation data is in the device's data directory (`~/rrr/shared/data`), which releases and rollbacks never touch.
