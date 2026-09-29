"""The bench tools behind the topology validation (v1.21.0).

tools/gravimetric_check.py pairs a dispensing_history row with a balance
reading and keeps the raw reading, the density used and a snapshot of the
delivery context in gravimetric_checks.csv; tools/topology_compare.py
grades those CSVs against the C2/C3/C4 beaker criteria and the
CLSI EP15-A3 equivalence check. Pinned here: the read-only database
access, the CSV contract between the two tools, the planner verdict,
the water-density table, the chi-square factor, and the grading.
"""

from __future__ import annotations

import csv
import hashlib
import importlib.util
import json
import sqlite3
from pathlib import Path

import pytest

from utils import paths

TOOLS = Path(__file__).resolve().parents[2] / "tools"
Q = 0.032936  # mL per pulse with the upstream 16 G needle (bench, 30 ms / 1000 ms)
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


def _log(handler, **overrides):
    data = {
        'schedule_id': 7,
        'animal_id': 1,
        'relay_unit_id': 3,
        'timestamp': '2026-09-28T10:00:00',
        'volume_delivered': 0.3,
        'status': 'completed',
        'volume_actual_ml': 9 * Q,
        'pulses_fired': 9,
        'volume_per_pulse_ml': Q,
        'topology': 'shared_manifold',
        'calibration_id': 42,
        'pulse_width_ms': 30,
        'inter_pulse_interval_ms': 1000,
        'duration_s': 9.7,
        'app_version': '1.21.0',
    }
    data.update(overrides)
    assert handler.log_delivery(data) is True
    with sqlite3.connect(handler.db_path) as conn:
        return conn.execute("SELECT MAX(history_id) FROM dispensing_history").fetchone()[0]


def _digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def _checks(csv_path):
    with open(csv_path, newline='') as handle:
        return list(csv.DictReader(handle))


# --- where the data lives --------------------------------------------------------


def test_bench_data_dir_precedence(tmp_path, monkeypatch):
    explicit = tmp_path / "explicit"
    env = tmp_path / "env"
    default = tmp_path / "default"
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


# --- the delivery side ------------------------------------------------------------


@pytest.mark.parametrize(
    "target,pulses,verdict",
    [
        (0.3, 9, 'nearest'),  # 0.3 / q = 9.11 -> nearest 9, up 10
        (0.3, 10, 'up'),
        (0.3, 8, 'mismatch'),
        (3 * Q, 3, 'both'),  # an exact multiple: both policies agree
        (None, 9, ''),
        (0.3, None, ''),
    ],
)
def test_planner_verdict(gravimetric, target, pulses, verdict):
    assert gravimetric.planner_verdict(target, pulses, Q) == verdict


def test_water_density_table_and_interpolation(gravimetric):
    assert gravimetric.water_density(20) == pytest.approx(0.99821)
    assert gravimetric.water_density(21.5) == pytest.approx((0.99799 + 0.99777) / 2)
    with pytest.raises(ValueError):
        gravimetric.water_density(40)


def test_list_shows_context_expected_volume_and_planner(gravimetric, database_handler, capsys):
    _log(database_handler)
    _log(
        database_handler,
        relay_unit_id=5,
        pulses_fired=10,
        topology='independent',
        calibration_id=43,
        app_version='1.21.0',
    )

    assert gravimetric.main(['list']) == 0
    out = capsys.readouterr().out
    lines = [
        line for line in out.splitlines() if 'shared_manifold' in line or 'independent' in line
    ]
    assert len(lines) == 2
    independent, shared = lines  # newest first
    assert 'nearest' in shared and f"{9 * Q:.4f}" in shared and '42' in shared
    assert 'up' in independent and f"{10 * Q:.4f}" in independent
    assert '2 delivered, 0 weighed' in out


def test_list_filters_and_hides_failures_unless_asked(gravimetric, database_handler, capsys):
    _log(database_handler, status='failed', volume_delivered=0)
    _log(database_handler, relay_unit_id=5, timestamp='2026-09-29T08:00:00')

    assert gravimetric.main(['list']) == 0
    assert '1 delivered' in capsys.readouterr().out
    assert gravimetric.main(['list', '--all']) == 0
    assert '2 delivered' in capsys.readouterr().out
    assert gravimetric.main(['list', '--cage', '3']) == 0
    assert 'no deliveries match' in capsys.readouterr().out
    assert gravimetric.main(['list', '--since', '2026-09-29']) == 0
    assert '1 delivered' in capsys.readouterr().out


# --- the balance side -------------------------------------------------------------


def test_weigh_keeps_the_raw_reading_and_the_delivery_snapshot(
    gravimetric, database_handler, isolated_data_dir, capsys
):
    history_id = _log(database_handler, volume_delivered=0.6, pulses_fired=18)
    before = _digest(database_handler.db_path)

    assert (
        gravimetric.main(
            [
                'weigh',
                str(history_id),
                '--gross',
                '12.7413',
                '--tare',
                '12.1435',
                '--note',
                'beaker A',
            ]
        )
        == 0
    )
    out = capsys.readouterr().out
    assert _digest(database_handler.db_path) == before, "the database is never written"

    csv_path = isolated_data_dir / gravimetric.CSV_NAME
    rows = _checks(csv_path)
    assert len(rows) == 1 and list(rows[0]) == list(gravimetric.CSV_COLUMNS)
    row = rows[0]
    assert (row['gross_g'], row['tare_g']) == ('12.7413', '12.1435')
    assert float(row['net_g']) == pytest.approx(0.5978)
    assert float(row['temp_c']) == 21.0 and float(row['density_g_per_ml']) == 0.99799
    assert float(row['measured_ml']) == pytest.approx(0.5978 / 0.99799)
    assert row['topology'] == 'shared_manifold' and row['cage_id'] == '3'
    assert row['pulses_fired'] == '18' and float(row['volume_per_pulse_ml']) == Q
    assert float(row['expected_ml']) == pytest.approx(18 * Q)
    assert row['planner'] == 'nearest'
    assert (row['calibration_id'], row['pulse_width_ms'], row['inter_pulse_interval_ms']) == (
        '42',
        '30',
        '1000',
    )
    assert row['app_version'] == '1.21.0' and row['note'] == 'beaker A'
    assert "shortfall" in out and f"{0.5978 / 0.99799 - 18 * Q:+.4f}" in out

    assert gravimetric.main(['list']) == 0
    listed = capsys.readouterr().out
    assert '1 delivered, 1 weighed' in listed
    assert f"{0.5978 / 0.99799:.4f}" in listed


def test_weigh_refuses_a_second_reading_unless_replaced(
    gravimetric, database_handler, isolated_data_dir, capsys
):
    history_id = _log(database_handler)
    assert gravimetric.main(['weigh', str(history_id), '--net', '0.2951']) == 0
    assert gravimetric.main(['weigh', str(history_id), '--net', '0.2960']) == 2
    assert "already has a reading" in capsys.readouterr().err
    rows = _checks(isolated_data_dir / gravimetric.CSV_NAME)
    assert [float(r['net_g']) for r in rows] == [0.2951]

    assert gravimetric.main(['weigh', str(history_id), '--net', '0.2960', '--replace']) == 0
    rows = _checks(isolated_data_dir / gravimetric.CSV_NAME)
    assert [float(r['net_g']) for r in rows] == [0.2960]


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


def test_weigh_with_a_density_override_and_a_partial_row(
    gravimetric, database_handler, isolated_data_dir, capsys
):
    history_id = _log(database_handler, status='partial', volume_delivered=0, pulses_fired=4)
    assert gravimetric.main(['weigh', str(history_id), '--net', '0.1300', '--density', '1.0']) == 0
    out = capsys.readouterr().out
    assert "status 'partial'" in out and "1 g/mL" in out
    row = _checks(isolated_data_dir / gravimetric.CSV_NAME)[0]
    assert row['status'] == 'partial' and row['temp_c'] == '' and row['density_g_per_ml'] == '1.0'
    assert float(row['measured_ml']) == pytest.approx(0.13)


def test_tools_work_on_a_database_from_before_the_context_columns(gravimetric, tmp_path, capsys):
    """Rows written by v1.17-v1.20 have no topology/profile: blanks, not errors."""
    data = tmp_path / "old"
    data.mkdir()
    with sqlite3.connect(data / gravimetric.DB_NAME) as conn:
        conn.execute(
            "CREATE TABLE dispensing_history (history_id INTEGER PRIMARY KEY AUTOINCREMENT, "
            "schedule_id INTEGER NOT NULL, animal_id INTEGER NOT NULL, relay_unit_id INTEGER NOT NULL, "
            "timestamp TEXT NOT NULL, volume_dispensed REAL NOT NULL, status TEXT NOT NULL)"
        )
        conn.execute(
            "INSERT INTO dispensing_history (schedule_id, animal_id, relay_unit_id, timestamp, "
            "volume_dispensed, status) VALUES (1, 1, 2, '2026-09-01T00:00:00', 0.3, 'completed')"
        )
    argv = ['--data-dir', str(data)]
    assert gravimetric.main(argv + ['list']) == 0
    assert '1 delivered, 0 weighed' in capsys.readouterr().out
    assert gravimetric.main(argv + ['weigh', '1', '--net', '0.29']) == 0
    assert 'topology not recorded' in capsys.readouterr().out
    row = _checks(data / gravimetric.CSV_NAME)[0]
    assert row['topology'] == '' and row['expected_ml'] == '' and row['planner'] == ''


# --- the comparison ---------------------------------------------------------------


@pytest.mark.parametrize(
    "n,factor",
    [(2, 1.960), (10, 1.371), (31, 1.208), (41, 1.181)],  # 41: beyond the table, Wilson-Hilferty
)
def test_uvl_factor_matches_ep15(compare_tool, n, factor):
    assert compare_tool.uvl_factor(n) == pytest.approx(factor, abs=0.002)


def _write_checks(
    gravimetric,
    path,
    topology,
    cage,
    dose,
    pulses,
    shortfall,
    offsets,
    planner='nearest',
    mismatch_at=None,
):
    rows = []
    for i, offset in enumerate(offsets):
        expected = pulses * Q
        rows.append(
            {
                'history_id': f"{cage}{i:02d}",
                'weighed_at': '2026-09-28T10:00:00',
                'net_g': (expected + shortfall + offset) * 0.99799,
                'temp_c': 21.0,
                'density_g_per_ml': 0.99799,
                'measured_ml': expected + shortfall + offset,
                'delivered_at': '2026-09-28T09:00:00',
                'cage_id': cage,
                'status': 'completed',
                'topology': topology,
                'target_ml': dose,
                'pulses_fired': pulses,
                'volume_per_pulse_ml': Q,
                'expected_ml': expected,
                'planner': 'mismatch' if i == mismatch_at else planner,
            }
        )
    gravimetric.write_checks(str(path), rows)


def test_compare_grades_both_topologies_and_their_equivalence(
    gravimetric, compare_tool, tmp_path, capsys
):
    manifold = tmp_path / "manifold.csv"
    independent = tmp_path / "independent.csv"
    # The manifold rig loses ~12 uL per dose to the needle; the syringe rig loses nothing.
    _write_checks(gravimetric, manifold, 'shared_manifold', 3, 0.6, 18, -0.012, OFFSETS)
    _write_checks(gravimetric, independent, 'independent', 7, 0.6, 18, 0.0, OFFSETS)

    assert (
        compare_tool.main(
            [str(manifold), str(independent), '--json', str(tmp_path / 'report.json')]
        )
        == 0
    )
    out = capsys.readouterr().out
    assert 'every graded criterion passed' in out

    report = json.loads((tmp_path / 'report.json').read_text())
    pooled = {g['topology']: g for g in report['pooled']}
    assert pooled['shared_manifold']['n'] == 10
    assert pooled['shared_manifold']['shortfall_ml'] == pytest.approx(-0.012, abs=1e-9)
    assert pooled['independent']['shortfall_ml'] == pytest.approx(0.0, abs=1e-9)
    assert pooled['independent']['verdicts'] == {
        'C2_precision': True,
        'C3_planner': True,
        'C4_trueness': True,
    }
    assert pooled['shared_manifold']['cv_pct'] < 1.0
    assert pooled['independent']['planner'] == {'nearest': 10}

    (equivalence,) = report['equivalence']
    assert (
        equivalence['topology'] == 'independent' and equivalence['reference'] == 'shared_manifold'
    )
    assert equivalence['uvl_factor'] == pytest.approx(1.371, abs=0.002)
    assert equivalence['mean_diff_ml'] == pytest.approx(0.012, abs=1e-9)
    assert equivalence['mean_diff_allowed_ml'] == pytest.approx(0.015)
    assert equivalence['verdicts'] == {'precision_vs_reference': True, 'mean_vs_reference': True}
    assert report['graded'] == 14 and report['passed'] is True  # 6 per-cage + 6 pooled + 2


def test_compare_fails_on_a_planner_mismatch_a_wide_spread_and_a_shifted_mean(
    gravimetric, compare_tool, tmp_path, capsys
):
    manifold = tmp_path / "manifold.csv"
    independent = tmp_path / "independent.csv"
    _write_checks(gravimetric, manifold, 'shared_manifold', 3, 0.6, 18, -0.012, OFFSETS)
    wide = [o * 12 for o in OFFSETS]  # SD ~ 0.041 mL -> CV ~ 7 %
    _write_checks(gravimetric, independent, 'independent', 7, 0.6, 18, 0.030, wide, mismatch_at=4)

    assert compare_tool.main([str(manifold), str(independent)]) == 1
    out = capsys.readouterr().out
    assert 'RESULT: FAILED' in out
    assert 'independent cage 7 0.600 mL: C2_precision' in out
    assert 'independent cage 7 0.600 mL: C3_planner' in out
    assert 'independent cage 7 0.600 mL: C4_trueness' in out
    assert 'independent vs shared_manifold at 0.600 mL: precision_vs_reference' in out
    assert 'independent vs shared_manifold at 0.600 mL: mean_vs_reference' in out
    assert 'shared_manifold cage 3' not in '\n'.join(
        line for line in out.splitlines() if line.startswith('  - ')
    )


def test_compare_does_not_pass_what_it_could_not_grade(
    gravimetric, compare_tool, tmp_path, capsys
):
    few = tmp_path / "few.csv"
    _write_checks(gravimetric, few, 'independent', 7, 0.6, 18, 0.0, OFFSETS[:3])
    assert compare_tool.main([str(few)]) == 1
    out = capsys.readouterr().out
    assert 'not graded: n too small' in out and 'nothing graded' in out
    assert 'reference n = 0' in out, "no manifold rows: equivalence cannot be graded"

    assert compare_tool.main([str(few), '--min-n', '3']) == 0
    assert 'every graded criterion passed' in capsys.readouterr().out


def test_compare_rejects_empty_input(compare_tool, tmp_path, capsys):
    empty = tmp_path / "empty.csv"
    empty.write_text("history_id,measured_ml\n")
    assert compare_tool.main([str(empty)]) == 2
    assert 'no weighed deliveries' in capsys.readouterr().err
    assert compare_tool.main([str(empty), '--min-n', '1']) == 2
