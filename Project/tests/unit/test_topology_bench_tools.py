"""The bench tools behind the topology validation (v1.21.0).

tools/gravimetric_check.py pairs a dispensing_history row with a balance
reading and keeps the raw reading, the density used and a snapshot of the
delivery (the dose asked for, the rounding policy, the pulses, the plan) in
gravimetric_checks.csv; tools/topology_compare.py grades those CSVs against
the C2/C3/C4 beaker criteria and the CLSI EP15-A3 precision comparison.

The rows seeded here are shaped the way the worker really writes them:
volume_dispensed is the PLAN (whole pulses x mL/pulse) and the dose asked
for is volume_requested_ml. The first version of these tests seeded the
nominal dose into volume_dispensed, a row the worker never writes, and
missed that the tools graded the plan. The end-to-end test at the bottom
drives the real worker, strategy and database for two rigs before grading.
"""

from __future__ import annotations

import asyncio
import csv
import hashlib
import importlib.util
import json
import sqlite3
from datetime import datetime
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from utils import paths

TOOLS = Path(__file__).resolve().parents[2] / "tools"
NEEDLE_Q = 0.032936  # mL per pulse, manifold rig with the upstream 16 G needle
FREE_Q = 0.034164  # mL per pulse, the same valve without the needle
OFFSETS = [-0.004, 0.003, -0.002, 0.005, 0.001, -0.003, 0.002, -0.005, 0.004, -0.001]


def _load(name):
    spec = importlib.util.spec_from_file_location(name, TOOLS / f"{name}.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture
def gravimetric():
    return _load("gravimetric_check")


@pytest.fixture
def compare_tool():
    return _load("topology_compare")


def _schedule(db_path, schedule_id=7, mode='instant'):
    with sqlite3.connect(db_path) as conn:
        conn.execute(
            "INSERT OR REPLACE INTO schedules (schedule_id, name, water_volume, start_time, "
            "end_time, created_by, delivery_mode) VALUES (?, 'bench', 0.6, "
            "'2026-09-29T00:00:00', '2026-09-29T23:59:00', 1, ?)",
            (schedule_id, mode),
        )


def _log(handler, dose=0.6, q=NEEDLE_Q, pulses=None, **overrides):
    """A dispensing_history row as the worker writes it."""
    if pulses is None:
        pulses = int(dose / q + 0.5)
    data = {
        'schedule_id': 7,
        'animal_id': 1,
        'relay_unit_id': 3,
        'timestamp': '2026-09-29T10:00:00',
        'volume_delivered': pulses * q,  # the PLAN, not the dose
        'status': 'completed',
        'volume_actual_ml': pulses * q,
        'pulses_fired': pulses,
        'volume_per_pulse_ml': q,
        'topology': 'shared_manifold',
        'calibration_id': 42,
        'pulse_width_ms': 30,
        'inter_pulse_interval_ms': 1000,
        'duration_s': 18.7,
        'app_version': '1.21.0',
        'volume_requested_ml': dose,
        'dose_rounding': 'nearest',
    }
    data.update(overrides)
    assert handler.log_delivery(data) is True
    with sqlite3.connect(handler.db_path) as conn:
        return conn.execute("SELECT MAX(history_id) FROM dispensing_history").fetchone()[0]


def _digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def _checks(csv_path):
    with open(csv_path, newline='', encoding='utf-8-sig') as handle:
        return list(csv.DictReader(handle))


def _rows_of(out):
    return [line for line in out.splitlines() if line[:6].strip().isdigit()]


# --- where the data lives --------------------------------------------------------


def test_bench_data_dir_precedence(tmp_path, monkeypatch):
    explicit, env, default = tmp_path / "explicit", tmp_path / "env", tmp_path / "default"
    for d in (explicit, env, default):
        d.mkdir()
    monkeypatch.setattr(paths, "DEVICE_DATA_DIR", str(default))

    monkeypatch.delenv("RRR_DATA", raising=False)
    assert paths.bench_data_dir(None) == str(default)
    monkeypatch.setenv("RRR_DATA", str(env))
    assert paths.bench_data_dir(None) == str(env)
    assert paths.bench_data_dir(str(explicit)) == str(explicit)
    # A named location that does not exist is not skipped in favour of the next.
    assert paths.bench_data_dir(str(tmp_path / "missing")) is None
    monkeypatch.setenv("RRR_DATA", str(tmp_path / "missing"))
    assert paths.bench_data_dir(None) is None
    monkeypatch.delenv("RRR_DATA")
    monkeypatch.setattr(paths, "DEVICE_DATA_DIR", str(tmp_path / "missing"))
    assert paths.bench_data_dir(None) is None
    assert not (tmp_path / "missing").exists(), "never creates anything"


def test_gravimetric_refuses_without_a_database_and_creates_nothing(
    gravimetric, tmp_path, monkeypatch, capsys
):
    monkeypatch.delenv("RRR_DATA", raising=False)
    monkeypatch.setattr(gravimetric, "DEVICE_DATA_DIR", str(tmp_path / "nowhere"))
    monkeypatch.setattr(paths, "DEVICE_DATA_DIR", str(tmp_path / "nowhere"))
    assert gravimetric.main(['list']) == 2
    assert "cannot find the device data directory" in capsys.readouterr().err

    empty = tmp_path / "empty"
    empty.mkdir()
    assert gravimetric.main(['--data-dir', str(empty), 'list']) == 2
    assert "never creates one" in capsys.readouterr().err
    assert list(empty.iterdir()) == []


# --- the planner verdict ------------------------------------------------------------


@pytest.mark.parametrize(
    "dose,pulses,policy,status,mode,verdict",
    [
        # 0.6 mL at the needle q is 18.22 pulses: 18 at nearest, 19 rounded up.
        (0.6, 18, 'nearest', 'completed', 'instant', 'ok'),
        (0.6, 19, 'up', 'completed', 'instant', 'ok'),
        (0.6, 19, 'nearest', 'completed', 'instant', 'mismatch'),
        (0.6, 18, 'up', 'completed', 'instant', 'mismatch'),
        (0.6, 21, 'nearest', 'completed', 'instant', 'mismatch'),  # a planner regression
        # The planner rounds half UP (int(x + 0.5)); Python's round() would say 18.
        (18.5 * NEEDLE_Q, 19, 'nearest', 'completed', 'instant', 'ok'),
        # Rows written before the policy was recorded: which policy fits.
        (0.6, 18, None, 'completed', 'instant', 'nearest'),
        (0.6, 19, None, 'completed', 'instant', 'up'),
        (3 * NEEDLE_Q, 3, None, 'completed', 'instant', 'both'),
        (0.6, 17, None, 'completed', 'instant', 'mismatch'),
        # Not planner events: stopped part-way, a staggered chunk, no recorded dose.
        (0.6, 4, 'nearest', 'partial', 'instant', ''),
        (0.0, 4, None, 'partial', None, ''),
        (0.6, 18, 'nearest', 'completed', 'staggered', 'carry'),
        (None, 18, 'nearest', 'completed', 'instant', ''),
        (0.6, 18, 'nearest', 'completed', None, 'ok'),  # schedule unknown: judged
    ],
)
def test_planner_verdict(gravimetric, dose, pulses, policy, status, mode, verdict):
    assert (
        gravimetric.planner_verdict(
            dose, pulses, NEEDLE_Q, policy=policy, status=status, delivery_mode=mode
        )
        == verdict
    )


def test_water_density_table_and_interpolation(gravimetric):
    assert gravimetric.water_density(20) == pytest.approx(0.99821)
    assert gravimetric.water_density(21.5) == pytest.approx((0.99799 + 0.99777) / 2)
    with pytest.raises(ValueError):
        gravimetric.water_density(40)


@pytest.mark.parametrize(
    "text,expected",
    [
        ("2026-09-29", "2026-09-29"),
        ("2026-09-29 10:00", "2026-09-29T10:00:00"),  # a space sorts below 'T'
        ("2026-09-29T08:00", "2026-09-29T08:00:00"),
    ],
)
def test_time_bounds_use_the_ledgers_form(gravimetric, compare_tool, text, expected):
    assert gravimetric.iso_bound(text) == expected
    assert compare_tool.iso_bound(text) == expected


def test_a_malformed_time_bound_is_a_usage_error(gravimetric, database_handler, capsys):
    with pytest.raises(SystemExit) as excinfo:
        gravimetric.main(['list', '--since', '2026-09-29T8:00'])
    assert excinfo.value.code == 2
    assert "not an ISO date" in capsys.readouterr().err


# --- list and daily ------------------------------------------------------------------


def test_list_shows_the_dose_the_policy_and_the_plan(gravimetric, database_handler, capsys):
    _schedule(database_handler.db_path)
    _log(database_handler)  # 0.6 mL, 18 pulses, nearest
    _log(database_handler, relay_unit_id=5, pulses=19, dose_rounding='up', topology='independent')

    assert gravimetric.main(['list']) == 0
    out = capsys.readouterr().out
    independent, shared = _rows_of(out)  # newest first
    for line in (independent, shared):
        assert '0.600' in line and ' ok ' in f" {line} "
    assert 'nearest' in shared and f"{18 * NEEDLE_Q:.4f}" in shared
    assert ' up ' in independent and f"{19 * NEEDLE_Q:.4f}" in independent
    assert '2 delivered, 0 weighed' in out


def test_list_flags_a_wrong_pulse_count_and_ignores_non_planner_rows(
    gravimetric, database_handler, capsys
):
    _schedule(database_handler.db_path, 7, 'instant')
    _schedule(database_handler.db_path, 8, 'staggered')
    _log(database_handler, pulses=21)  # instant 0.6 mL fired 21: regression
    _log(database_handler, status='partial', volume_delivered=0, pulses=4)
    _log(database_handler, schedule_id=8, dose=0.2, pulses=6)

    assert gravimetric.main(['list', '--all']) == 0
    staggered, partial, regression = _rows_of(capsys.readouterr().out)
    assert 'mismatch' in regression
    assert 'mismatch' not in partial and 'partial' in partial
    assert 'carry' in staggered


def test_list_filters(gravimetric, database_handler, capsys):
    _log(database_handler, status='failed', volume_delivered=0, pulses=0)
    _log(database_handler, relay_unit_id=5, timestamp='2026-09-29T08:00:00')
    _log(database_handler, relay_unit_id=5, timestamp='2026-09-29T12:00:00')

    assert gravimetric.main(['list']) == 0
    assert '2 delivered' in capsys.readouterr().out
    assert gravimetric.main(['list', '--all']) == 0
    assert '3 delivered' in capsys.readouterr().out
    assert gravimetric.main(['list', '--cage', '4']) == 0
    assert 'no deliveries match' in capsys.readouterr().out
    # The time bound is honoured even when typed with a space.
    assert gravimetric.main(['list', '--since', '2026-09-29 10:00']) == 0
    (row,) = _rows_of(capsys.readouterr().out)
    assert '12:00:00' in row
    assert gravimetric.main(['list', '--until', '2026-09-29T09:00']) == 0
    (row,) = _rows_of(capsys.readouterr().out)
    assert '08:00:00' in row


def test_daily_totals_the_ledger_per_day_and_cage(gravimetric, database_handler, capsys):
    for hour in (8, 12, 16):
        _log(database_handler, dose=0.2, timestamp=f'2026-09-29T{hour:02d}:00:00')
    _log(database_handler, dose=0.2, status='partial', volume_delivered=0, pulses=3,
         volume_actual_ml=3 * NEEDLE_Q, timestamp='2026-09-29T20:00:00')
    _log(database_handler, dose=0.2, relay_unit_id=5, topology='independent',
         timestamp='2026-09-30T08:00:00')
    _log(database_handler, status='sensor_failure', volume_delivered=0, pulses=None,
         volume_actual_ml=None, timestamp='2026-09-30T09:00:00')

    assert gravimetric.main(['daily']) == 0
    lines = [line for line in capsys.readouterr().out.splitlines() if line.startswith('2026-')]
    first = next(line for line in lines if line.startswith('2026-09-29'))
    assert first.split()[1:7] == ['3', 'shared_manifold', '3', '1', '0', '0']
    per_pulse = int(0.2 / NEEDLE_Q + 0.5)
    assert first.split()[-1] == f"{(3 * per_pulse + 3) * NEEDLE_Q:.4f}"
    assert any(line.split()[1:3] == ['5', 'independent'] for line in lines)
    other = next(line for line in lines if line.startswith('2026-09-30') and ' 3 ' in line)
    assert other.split()[6] == '1'  # the sensor_failure row

    assert gravimetric.main(['daily', '--since', '2026-09-30', '--cage', '5']) == 0
    lines = [ln for ln in capsys.readouterr().out.splitlines() if ln.startswith('2026-')]
    assert len(lines) == 1 and lines[0].startswith('2026-09-30')


# --- weigh ---------------------------------------------------------------------------


def test_weigh_keeps_the_raw_reading_and_the_delivery_snapshot(
    gravimetric, database_handler, isolated_data_dir, capsys
):
    _schedule(database_handler.db_path)
    history_id = _log(database_handler)
    before = _digest(database_handler.db_path)

    argv = ['weigh', str(history_id), '--gross', '12.7413', '--tare', '12.1435', '--note', 'A']
    assert gravimetric.main(argv) == 0
    out = capsys.readouterr().out
    assert _digest(database_handler.db_path) == before, "the database is never written"

    rows = _checks(isolated_data_dir / gravimetric.CSV_NAME)
    assert len(rows) == 1 and list(rows[0]) == list(gravimetric.CSV_COLUMNS)
    row = rows[0]
    assert (row['gross_g'], row['tare_g']) == ('12.7413', '12.1435')
    assert float(row['net_g']) == pytest.approx(0.5978)
    assert float(row['density_g_per_ml']) == 0.99799 and float(row['temp_c']) == 21.0
    assert float(row['measured_ml']) == pytest.approx(0.5978 / 0.99799)
    assert float(row['target_ml']) == pytest.approx(0.6), "the dose asked for, not the plan"
    assert float(row['planned_ml']) == pytest.approx(18 * NEEDLE_Q)
    assert float(row['expected_ml']) == pytest.approx(18 * NEEDLE_Q)
    assert (row['dose_rounding'], row['delivery_mode'], row['planner']) == (
        'nearest', 'instant', 'ok')
    assert (row['calibration_id'], row['pulse_width_ms'], row['inter_pulse_interval_ms']) == (
        '42', '30', '1000')
    assert row['topology'] == 'shared_manifold' and row['note'] == 'A'
    assert f"{0.5978 / 0.99799 - 18 * NEEDLE_Q:+.4f}" in out

    assert gravimetric.main(['list']) == 0
    listed = capsys.readouterr().out
    assert '1 delivered, 1 weighed' in listed and f"{0.5978 / 0.99799:.4f}" in listed


def test_weighing_a_wrong_pulse_count_warns(gravimetric, database_handler, capsys):
    _schedule(database_handler.db_path)
    history_id = _log(database_handler, pulses=21)
    assert gravimetric.main(['weigh', str(history_id), '--net', '0.69']) == 0
    assert "WARNING: 21 pulses is not what the planner should fire" in capsys.readouterr().out


def test_weigh_refuses_a_second_reading_unless_replaced(
    gravimetric, database_handler, isolated_data_dir, capsys
):
    history_id = _log(database_handler)
    assert gravimetric.main(['weigh', str(history_id), '--net', '0.5951']) == 0
    assert gravimetric.main(['weigh', str(history_id), '--net', '0.5960']) == 2
    assert "already has a reading" in capsys.readouterr().err
    rows = _checks(isolated_data_dir / gravimetric.CSV_NAME)
    assert [float(r['net_g']) for r in rows] == [0.5951]

    assert gravimetric.main(['weigh', str(history_id), '--net', '0.5960', '--replace']) == 0
    rows = _checks(isolated_data_dir / gravimetric.CSV_NAME)
    assert [float(r['net_g']) for r in rows] == [0.5960]


def test_weigh_validates_its_inputs(gravimetric, database_handler, capsys):
    history_id = _log(database_handler)
    cases = [
        (['weigh', '999', '--net', '0.3'], "no dispensing_history row"),
        (['weigh', str(history_id)], "--gross G --tare T"),
        (['weigh', str(history_id), '--net', '0.3', '--gross', '1'], "not both"),
        (['weigh', str(history_id), '--gross', '1.0', '--tare', '1.5'], "negative"),
        (['weigh', str(history_id), '--net', '0.3', '--temp-c', '45'], "outside the 15-30 C"),
        (['weigh', str(history_id), '--net', '0.3', '--density', '0'], "positive"),
    ]
    for argv, message in cases:
        assert gravimetric.main(argv) == 2, argv
        assert message in capsys.readouterr().err, argv


def test_a_partial_row_is_recorded_but_not_judged(
    gravimetric, database_handler, isolated_data_dir, capsys
):
    history_id = _log(database_handler, status='partial', volume_delivered=0, pulses=4)
    assert gravimetric.main(['weigh', str(history_id), '--net', '0.1300', '--density', '1.0']) == 0
    out = capsys.readouterr().out
    assert "status 'partial'" in out and "left out of the grading" in out and "1 g/mL" in out
    row = _checks(isolated_data_dir / gravimetric.CSV_NAME)[0]
    assert row['status'] == 'partial' and row['planner'] == '' and row['temp_c'] == ''


def test_tools_work_on_a_database_from_before_the_context_columns(
    gravimetric, tmp_path, capsys
):
    """Rows written by v1.17-v1.20 have no dose, policy or topology: blanks, not errors."""
    data = tmp_path / "old"
    data.mkdir()
    with sqlite3.connect(data / gravimetric.DB_NAME) as conn:
        conn.execute(
            "CREATE TABLE dispensing_history (history_id INTEGER PRIMARY KEY AUTOINCREMENT, "
            "schedule_id INTEGER NOT NULL, animal_id INTEGER NOT NULL, "
            "relay_unit_id INTEGER NOT NULL, timestamp TEXT NOT NULL, "
            "volume_dispensed REAL NOT NULL, status TEXT NOT NULL)"
        )
        conn.execute(
            "INSERT INTO dispensing_history (schedule_id, animal_id, relay_unit_id, timestamp, "
            "volume_dispensed, status) VALUES (1, 1, 2, '2026-09-01T00:00:00', 0.3, 'completed')"
        )
    argv = ['--data-dir', str(data)]
    assert gravimetric.main(argv + ['list']) == 0
    assert '1 delivered, 0 weighed' in capsys.readouterr().out
    assert gravimetric.main(argv + ['daily']) == 0
    assert '2026-09-01' in capsys.readouterr().out
    assert gravimetric.main(argv + ['weigh', '1', '--net', '0.29']) == 0
    assert 'topology not recorded' in capsys.readouterr().out
    row = _checks(data / gravimetric.CSV_NAME)[0]
    assert (row['topology'], row['target_ml'], row['planner'], row['expected_ml']) == ('', '', '', '')


def test_readings_saved_back_from_a_spreadsheet(
    gravimetric, database_handler, isolated_data_dir, capsys
):
    first = _log(database_handler)
    second = _log(database_handler, relay_unit_id=5)
    assert gravimetric.main(['weigh', str(first), '--net', '0.59']) == 0
    csv_path = isolated_data_dir / gravimetric.CSV_NAME

    # Excel's "CSV UTF-8" adds a byte-order mark.
    csv_path.write_bytes(b'\xef\xbb\xbf' + csv_path.read_bytes())
    assert gravimetric.main(['list']) == 0
    assert '2 delivered, 1 weighed' in capsys.readouterr().out
    assert gravimetric.main(['weigh', str(second), '--net', '0.60']) == 0
    assert len(_checks(csv_path)) == 2

    # A Windows "CSV (Comma delimited)" save of a note with a degree sign.
    csv_path.write_bytes(csv_path.read_bytes().replace(b'\xef\xbb\xbf', b'') + b'x\xb0C\n')
    assert gravimetric.main(['list']) == 2
    assert "not a UTF-8 CSV" in capsys.readouterr().err

    csv_path.write_text("cage,grams\n3,0.6\n")
    assert gravimetric.main(['list']) == 2
    assert "no history_id column" in capsys.readouterr().err


# --- the comparison --------------------------------------------------------------------


@pytest.mark.parametrize(
    "n,factor",
    [(2, 1.960), (10, 1.371), (31, 1.208), (41, 1.181)],  # 41: beyond the table, Wilson-Hilferty
)
def test_uvl_factor_matches_ep15(compare_tool, n, factor):
    assert compare_tool.uvl_factor(n) == pytest.approx(factor, abs=0.002)


def _write_checks(gravimetric, path, topology, cage, dose, q, shortfall, offsets, **kw):
    """Readings for `len(offsets)` deliveries of `dose` at `q`, as weigh writes them."""
    pulses = kw.pop('pulses', int(dose / q + 0.5))
    policy = kw.pop('policy', 'nearest')
    rows = []
    for i, offset in enumerate(offsets):
        plan = pulses * q
        rows.append(
            {
                'history_id': f"{cage}{i:03d}",
                'weighed_at': '2026-10-01T10:00:00',
                'net_g': (plan + shortfall + offset) * 0.99799,
                'temp_c': 21.0,
                'density_g_per_ml': 0.99799,
                'measured_ml': plan + shortfall + offset,
                'delivered_at': kw.get('delivered_at', '2026-10-01T09:00:00'),
                'cage_id': cage,
                'status': kw.get('status', 'completed'),
                'delivery_mode': kw.get('mode', 'instant'),
                'topology': topology,
                'target_ml': dose,
                'dose_rounding': policy,
                'pulses_fired': pulses,
                'volume_per_pulse_ml': q,
                'expected_ml': plan,
                'planned_ml': plan,
                'planner': kw.get('planner') or gravimetric.planner_verdict(
                    dose, pulses, q, policy=policy
                ),
            }
        )
    existing = _checks(path) if Path(path).exists() else []
    gravimetric.write_checks(str(path), existing + rows)


def test_two_rigs_with_different_pulse_sizes_are_compared_at_the_same_dose(
    gravimetric, compare_tool, tmp_path, capsys
):
    """0.6 mL is 18 pulses on both rigs, but 0.593 mL of plan on one and 0.615 on
    the other. Grading by the dose asked for puts them in one comparison."""
    manifold, independent = tmp_path / "manifold.csv", tmp_path / "independent.csv"
    _write_checks(gravimetric, manifold, 'shared_manifold', 3, 0.6, NEEDLE_Q, -0.016, OFFSETS)
    _write_checks(gravimetric, independent, 'independent', 7, 0.6, FREE_Q, 0.0, OFFSETS)

    report_path = tmp_path / 'report.json'
    assert compare_tool.main([str(manifold), str(independent), '--policy', 'nearest',
                              '--json', str(report_path)]) == 0
    out = capsys.readouterr().out
    assert 'every graded criterion passed' in out and 'INCOMPLETE' not in out

    report = json.loads(report_path.read_text())
    (equivalence,) = report['equivalence']
    assert equivalence['graded'] is True and equivalence['dose_ml'] == pytest.approx(0.6)
    assert equivalence['uvl_factor'] == pytest.approx(1.371, abs=0.002)
    assert equivalence['verdicts'] == {'precision_vs_reference': True}
    # Reported, not graded: the pulse sizes alone put the plans 0.022 mL apart.
    assert equivalence['mean_diff_ml'] == pytest.approx(18 * (FREE_Q - NEEDLE_Q) + 0.016)
    assert equivalence['shortfall_diff_ml'] == pytest.approx(0.016)
    pooled = {g['topology']: g for g in report['pooled']}
    assert pooled['independent']['verdicts'] == {
        'C2_precision': True, 'C3_planner': True, 'C4_trueness': True}
    assert pooled['shared_manifold']['verdicts'] == {'C3_planner': True}, "reference: baseline"


def test_the_reference_is_a_baseline_not_a_candidate(gravimetric, compare_tool, tmp_path, capsys):
    """A manifold rig exactly as its baseline documents (dose CV above 5 %, a
    shortfall over half a pulse) must not fail the independent rig's run."""
    manifold, independent = tmp_path / "manifold.csv", tmp_path / "independent.csv"
    wide = [o * 8 for o in OFFSETS]  # CV about 5.5 %
    _write_checks(gravimetric, manifold, 'shared_manifold', 3, 0.6, NEEDLE_Q, -0.019, wide)
    _write_checks(gravimetric, independent, 'independent', 7, 0.6, FREE_Q, 0.0, OFFSETS)

    assert compare_tool.main([str(manifold), str(independent)]) == 0
    out = capsys.readouterr().out
    manifold_line = next(ln for ln in out.splitlines() if ln.startswith('shared_manifold') and ' all ' in ln)
    assert manifold_line.split()[-3:] == ['ref', 'ok', 'ref']


def test_failures_are_named(gravimetric, compare_tool, tmp_path, capsys):
    manifold, independent = tmp_path / "manifold.csv", tmp_path / "independent.csv"
    _write_checks(gravimetric, manifold, 'shared_manifold', 3, 0.6, NEEDLE_Q, -0.016, OFFSETS)
    wide = [o * 12 for o in OFFSETS]  # SD about 0.041 mL: CV about 7 %, over 1.371 x the manifold's
    _write_checks(gravimetric, independent, 'independent', 7, 0.6, FREE_Q, 0.030, wide)
    rows = _checks(independent)
    rows[4]['planner'] = 'mismatch'
    gravimetric.write_checks(str(independent), rows)

    assert compare_tool.main([str(manifold), str(independent)]) == 1
    out = capsys.readouterr().out
    failures = [ln for ln in out.splitlines() if ln.startswith('  - ')]
    assert 'RESULT: FAILED' in out
    for name in ('C2_precision', 'C3_planner', 'C4_trueness'):
        assert f"  - independent cage 7 0.600 mL: {name}" in failures
    assert "  - independent vs shared_manifold at 0.600 mL: precision_vs_reference" in failures
    assert not any(ln.startswith('  - shared_manifold') for ln in failures)


def test_a_required_policy_is_enforced(gravimetric, compare_tool, tmp_path, capsys):
    # 0.6 mL at the needle q is 18.22 pulses: 18 at nearest, 19 rounded up.
    independent = tmp_path / "independent.csv"
    _write_checks(
        gravimetric, independent, 'independent', 7, 0.6, NEEDLE_Q, 0.0, OFFSETS, policy='up', pulses=19
    )
    assert compare_tool.main([str(independent)]) == 0  # consistent with its own policy
    capsys.readouterr()
    assert compare_tool.main([str(independent), '--policy', 'nearest']) == 1
    assert 'independent cage 7 0.600 mL: C3_planner' in capsys.readouterr().out


def test_a_dose_the_reference_never_ran_is_incomplete(gravimetric, compare_tool, tmp_path, capsys):
    manifold, independent = tmp_path / "manifold.csv", tmp_path / "independent.csv"
    _write_checks(gravimetric, manifold, 'shared_manifold', 3, 0.3, NEEDLE_Q, -0.016, OFFSETS)
    _write_checks(gravimetric, independent, 'independent', 7, 0.6, FREE_Q, 0.0, OFFSETS)

    assert compare_tool.main([str(manifold), str(independent)]) == 1
    out = capsys.readouterr().out
    assert 'RESULT: INCOMPLETE' in out
    assert 'independent at 0.600 mL: no precision comparison (reference n = 0, need 10)' in out


def test_one_rig_alone_is_graded_and_says_nothing_was_compared(
    gravimetric, compare_tool, tmp_path, capsys
):
    independent = tmp_path / "independent.csv"
    _write_checks(gravimetric, independent, 'independent', 7, 0.6, FREE_Q, 0.0, OFFSETS)
    assert compare_tool.main([str(independent)]) == 0
    assert 'not graded: no rows from the reference topology shared_manifold' in capsys.readouterr().out


def test_rows_that_are_not_single_shot_doses_are_left_out(
    gravimetric, compare_tool, tmp_path, capsys
):
    path = tmp_path / "mixed.csv"
    _write_checks(gravimetric, path, 'independent', 7, 0.6, FREE_Q, 0.0, OFFSETS)
    _write_checks(gravimetric, path, 'independent', 8, 0.6, FREE_Q, -0.3, OFFSETS[:2],
                  status='partial')
    _write_checks(gravimetric, path, 'independent', 9, 0.2, FREE_Q, 0.0, OFFSETS[:3],
                  mode='staggered')
    _write_checks(gravimetric, path, 'independent', 6, 0.6, FREE_Q, 0.0, OFFSETS[:1])
    rows = _checks(path)
    rows[-1]['target_ml'] = ''  # cage 6: a row with no recorded dose
    gravimetric.write_checks(str(path), rows)

    assert compare_tool.main([str(path)]) == 0
    out = capsys.readouterr().out
    assert 'left out: 2 did not complete, 1 no recorded dose, 3 staggered chunk' in out
    assert ' 8 ' not in ' '.join(ln for ln in out.splitlines() if ln.startswith('independent'))


def test_one_day_can_be_graded_out_of_a_cumulative_file(gravimetric, compare_tool, tmp_path, capsys):
    """C7: day 3 dropped 5 %; pooled with day 1 it would read -2.5 % and pass."""
    path = tmp_path / "c7.csv"
    _write_checks(gravimetric, path, 'independent', 7, 0.6, FREE_Q, 0.0, OFFSETS,
                  delivered_at='2026-10-01T09:00:00')
    rows = _checks(path)
    for row in rows:
        row['history_id'] = 'd1' + row['history_id']
    gravimetric.write_checks(str(path), rows)
    _write_checks(gravimetric, path, 'independent', 7, 0.6, FREE_Q, -0.031, OFFSETS,
                  delivered_at='2026-10-03T09:00:00')

    report_path = tmp_path / 'day3.json'
    compare_tool.main([str(path), '--since', '2026-10-03', '--until', '2026-10-03',
                       '--json', str(report_path)])
    (cell,) = [g for g in json.loads(report_path.read_text())['by_cage']]
    assert cell['n'] == 10
    assert cell['mean_ml'] == pytest.approx(18 * FREE_Q - 0.031)


def test_nothing_graded_is_not_a_pass(gravimetric, compare_tool, tmp_path, capsys):
    few = tmp_path / "few.csv"
    _write_checks(gravimetric, few, 'independent', 7, 0.6, FREE_Q, 0.0, OFFSETS[:3])
    assert compare_tool.main([str(few)]) == 1
    out = capsys.readouterr().out
    assert 'not graded: n too small' in out and 'nothing graded' in out
    assert compare_tool.main([str(few), '--min-n', '3']) == 0


def test_compare_rejects_unusable_input(gravimetric, compare_tool, tmp_path, capsys):
    empty = tmp_path / "empty.csv"
    empty.write_text("history_id,measured_ml\n")
    assert compare_tool.main([str(empty)]) == 2
    assert 'no gradable weighed deliveries' in capsys.readouterr().err
    assert compare_tool.main([str(empty), '--min-n', '1']) == 2

    bom = tmp_path / "bom.csv"
    _write_checks(gravimetric, bom, 'independent', 7, 0.6, FREE_Q, 0.0, OFFSETS)
    bom.write_bytes(b'\xef\xbb\xbf' + bom.read_bytes())
    assert compare_tool.main([str(bom)]) == 0
    capsys.readouterr()

    cp1252 = tmp_path / "cp1252.csv"
    cp1252.write_bytes(bom.read_bytes()[3:] + b'x\xb0C\n')
    assert compare_tool.main([str(cp1252)]) == 2
    assert 'not a UTF-8 CSV' in capsys.readouterr().err

    alien = tmp_path / "alien.csv"
    alien.write_text("cage,grams\n3,0.6\n")
    assert compare_tool.main([str(alien)]) == 2
    assert 'no measured_ml column' in capsys.readouterr().err


# --- end to end: the real worker, strategy and database, then the tools -------------------


def _rig(tmp_path, name, topology, q, fake_relay_handler, monkeypatch):
    """A device data directory whose ledger holds ten real instant 0.6 mL deliveries."""
    pytest.importorskip("PyQt5")
    from drivers.solenoid_controller import (  # noqa: PLC0415
        IndependentSolenoidController,
        SolenoidController,
    )
    from gpio.relay_worker import RelayWorker  # noqa: PLC0415
    from models.database_handler import DatabaseHandler  # noqa: PLC0415
    from PyQt5.QtCore import QMutex, QObject  # noqa: PLC0415
    from strategies.solenoid_flow_strategy import SolenoidFlowStrategy  # noqa: PLC0415

    data = tmp_path / name
    data.mkdir()
    db = DatabaseHandler(db_path=str(data / 'rrr_database.db'))
    assert db.save_valve_calibration(
        cage_id=3, relay_id=3, pulse_width_ms=30, volume_per_pulse_ml=q, stddev_ml=0.0003,
        cv_pct=1.0, num_samples=250, inter_pulse_interval_ms=1000,
    )
    _schedule(db.db_path)
    if topology == 'shared_manifold':
        valves = SolenoidController(fake_relay_handler, 16, {3: 3})
    else:
        valves = IndependentSolenoidController(fake_relay_handler, {3: 3})
    strategy = SolenoidFlowStrategy(
        solenoid_controller=valves,
        flow_sensor=None,
        calibration_store=None,
        settings={
            'use_pulse_delivery': True,
            'pulse_width_ms': 30,
            'pulse_settling_ms': 100,
            'max_pulses_per_delivery': 100,
            'max_pulse_delivery_time_s': 120.0,
        },
        database_handler=db,
    )

    async def _no_rest(_interval_ms):
        return False

    monkeypatch.setattr(strategy, '_rest_between_pulses', _no_rest)

    worker = RelayWorker.__new__(RelayWorker)
    QObject.__init__(worker)
    worker.mutex = QMutex()
    worker.settings = {'valve_topology': topology, 'round_doses_up': False}
    worker.delivered_volumes, worker.failed_deliveries, worker.issued_targets = {}, {}, {}
    worker.schedule_id = 7
    worker.hardware_mode = 'solenoid'
    worker.database_handler = db
    worker.strategy = strategy
    worker.progress.connect(lambda _m: None)
    worker.volume_updated.connect(lambda *_a: None)

    class _Event:
        def is_set(self):
            return False

    worker._cancel_requested = _Event()
    monkeypatch.setattr(type(worker), "schedule_retry", lambda self, data: None, raising=False)
    for i in range(10):
        worker._handle_delivery({
            'animal_id': 1, 'relay_unit_id': 3, 'water_volume': 0.6, 'schedule_id': 7,
            'instant_time': datetime(2026, 10, 1, 9, i, 0),
        })
    return data


def test_end_to_end_two_rigs_are_graded_against_the_dose(
    gravimetric, compare_tool, fake_relay_handler, tmp_path, monkeypatch, capsys
):
    async def _no_sleep(_seconds):
        return None

    monkeypatch.setattr(asyncio, 'sleep', _no_sleep)
    rigs = {
        'shared_manifold': (_rig(tmp_path, 'manifold', 'shared_manifold', NEEDLE_Q,
                                 fake_relay_handler, monkeypatch), NEEDLE_Q, -0.016),
        'independent': (_rig(tmp_path, 'independent', 'independent', FREE_Q,
                             fake_relay_handler, monkeypatch), FREE_Q, 0.0),
    }
    csvs = []
    for data, q, shortfall in rigs.values():
        assert gravimetric.main(['--data-dir', str(data), 'list']) == 0
        listed = _rows_of(capsys.readouterr().out)
        assert len(listed) == 10 and all(' ok ' in f" {ln} " for ln in listed)
        for i, line in enumerate(sorted(listed)):
            history_id = line.split()[0]
            net = (18 * q + shortfall + OFFSETS[i]) * 0.99799
            assert gravimetric.main(['--data-dir', str(data), 'weigh', history_id,
                                     '--net', f"{net:.4f}"]) == 0
        capsys.readouterr()
        csvs.append(str(data / gravimetric.CSV_NAME))

    assert compare_tool.main(csvs + ['--policy', 'nearest']) == 0
    out = capsys.readouterr().out
    assert 'independent at 0.600 mL: SD' in out and 'RESULT: every graded criterion passed' in out
