"""Pair bench deliveries with balance readings.

The topology validation (docs/TOPOLOGY_VALIDATION.md) compares what the
valve put in the beaker with what the planner fired: ``pulses_fired`` times
the calibrated volume per pulse. The app records the pulse side in
``dispensing_history``; this tool records the balance side next to it.

    cd ~/rrr/current/Project
    ~/rrr/shared/venv/bin/python3 tools/gravimetric_check.py list
    ~/rrr/shared/venv/bin/python3 tools/gravimetric_check.py weigh 1234 --gross 12.7413 --tare 12.1435
    ~/rrr/shared/venv/bin/python3 tools/gravimetric_check.py weigh 1235 --net 0.5988 --temp-c 22

``list`` shows the latest completed deliveries with the context the app
recorded (topology, pulses, mL/pulse, calibration row, version) and the
volume those pulses should have produced. ``weigh`` stores a balance reading
against one delivery: the raw gross and tare (or a net) in grams, the water
temperature, the density used, and the resulting volume, together with a
snapshot of the delivery row, in ``gravimetric_checks.csv`` in the device
data directory. The CSV is self-contained: copy it off the device and feed
it to tools/topology_compare.py.

The database is opened read-only. Nothing here ever writes to it, so the
tool is safe to run while the app is running. Weigh promptly after the
delivery (the lab's water is drunk immediately; on the bench evaporation
is the operator's problem, not the tool's).

Requires the context columns added to dispensing_history in v1.21.0; rows
written by older releases list with blanks and can still be weighed.
"""

from __future__ import annotations

import argparse
import csv
import math
import os
import sqlite3
import sys
from datetime import datetime
from pathlib import Path


def _append_project_to_syspath() -> None:
    here = os.path.abspath(os.path.dirname(__file__))
    project_root = os.path.abspath(os.path.join(here, os.pardir))
    if project_root not in sys.path:
        sys.path.append(project_root)


_append_project_to_syspath()

from utils.paths import DEVICE_DATA_DIR, bench_data_dir  # noqa: E402

DB_NAME = 'rrr_database.db'
CSV_NAME = 'gravimetric_checks.csv'
DEFAULT_TEMP_C = 21.0

# Density of air-free water in g/mL by temperature (Kell 1975; the values
# ISO 8655-6 tabulates before the air-buoyancy correction). Bench balances
# in this lab read to 0.1 mg; the buoyancy term (~0.1 %) is below the
# tolerance the validation grades against (5 %), so it is not applied.
WATER_DENSITY_G_PER_ML = {
    15: 0.99910,
    16: 0.99895,
    17: 0.99878,
    18: 0.99860,
    19: 0.99841,
    20: 0.99821,
    21: 0.99799,
    22: 0.99777,
    23: 0.99754,
    24: 0.99730,
    25: 0.99705,
    26: 0.99679,
    27: 0.99652,
    28: 0.99624,
    29: 0.99595,
    30: 0.99565,
}

# Columns of gravimetric_checks.csv. The delivery snapshot makes the file
# self-contained so topology_compare.py needs no database.
CSV_COLUMNS = (
    'history_id',
    'weighed_at',
    'gross_g',
    'tare_g',
    'net_g',
    'temp_c',
    'density_g_per_ml',
    'measured_ml',
    'delivered_at',
    'cage_id',
    'schedule_id',
    'animal_id',
    'status',
    'topology',
    'target_ml',
    'pulses_fired',
    'volume_per_pulse_ml',
    'expected_ml',
    'planner',
    'calibration_id',
    'pulse_width_ms',
    'inter_pulse_interval_ms',
    'duration_s',
    'app_version',
    'note',
)

CONTEXT_COLUMNS = (
    'topology',
    'calibration_id',
    'pulse_width_ms',
    'inter_pulse_interval_ms',
    'duration_s',
    'app_version',
)


def _say(message: str) -> None:
    print(message, flush=True)


def _fail(message: str) -> int:
    print(f"ERROR: {message}", file=sys.stderr, flush=True)
    return 2


# --- the delivery side (read-only) ------------------------------------------


def water_density(temp_c: float) -> float:
    """Density of water at ``temp_c`` (linear between tabulated degrees)."""
    if not (15.0 <= temp_c <= 30.0):
        raise ValueError(f"water temperature {temp_c} C is outside the 15-30 C table")
    low = math.floor(temp_c)
    high = min(low + 1, 30)
    d_low, d_high = WATER_DENSITY_G_PER_ML[low], WATER_DENSITY_G_PER_ML[high]
    return d_low + (d_high - d_low) * (temp_c - low)


def planner_verdict(target_ml, pulses_fired, volume_per_pulse_ml) -> str:
    """How the fired pulse count relates to the requested volume.

    ``nearest`` and ``up`` are the two rounding policies the planner can
    run (Settings -> Delivery -> "Round doses up"); ``both`` when they agree;
    ``mismatch`` when the count is neither, which on a single-shot bench
    delivery means a code regression. Staggered chunks carry a running
    deficit, so their per-row verdicts are informative only. Blank when the
    row has no pulse data (older release, or a delivery that never fired).
    """
    try:
        target = float(target_ml)
        pulses = int(pulses_fired)
        q = float(volume_per_pulse_ml)
    except (TypeError, ValueError):
        return ''
    if q <= 0 or pulses < 0:
        return ''
    nearest = int(round(target / q))
    up = int(math.ceil(target / q - 1e-9))
    if pulses == nearest == up:
        return 'both'
    if pulses == nearest:
        return 'nearest'
    if pulses == up:
        return 'up'
    return 'mismatch'


def expected_ml(pulses_fired, volume_per_pulse_ml):
    """The volume the fired pulses should have produced, or None."""
    try:
        pulses = int(pulses_fired)
        q = float(volume_per_pulse_ml)
    except (TypeError, ValueError):
        return None
    if pulses < 0 or q <= 0:
        return None
    return pulses * q


def open_readonly(db_path: str) -> sqlite3.Connection:
    """Open the device database read-only; a missing file is an error, not a new DB."""
    if not os.path.isfile(db_path):
        raise FileNotFoundError(db_path)
    uri = Path(db_path).resolve().as_uri() + '?mode=ro'
    conn = sqlite3.connect(uri, uri=True)
    conn.row_factory = sqlite3.Row
    return conn


def _history_columns(conn: sqlite3.Connection) -> set:
    return {row[1] for row in conn.execute("PRAGMA table_info(dispensing_history)")}


def fetch_deliveries(
    conn, *, last=None, since=None, cage=None, history_id=None, all_statuses=False
):
    """Rows of dispensing_history as dicts, newest first, with the v1.21.0
    context columns present (None where the database predates them)."""
    present = _history_columns(conn)
    if 'history_id' not in present:
        raise sqlite3.OperationalError("no dispensing_history table in this database")
    select = [
        'history_id',
        'schedule_id',
        'animal_id',
        'relay_unit_id',
        'timestamp',
        'volume_dispensed',
        'status',
    ]
    optional = ('volume_actual_ml', 'pulses_fired', 'volume_per_pulse_ml') + CONTEXT_COLUMNS
    for column in optional:
        select.append(column if column in present else f"NULL AS {column}")
    where, params = [], []
    if history_id is not None:
        where.append("history_id = ?")
        params.append(int(history_id))
    if not all_statuses and history_id is None:
        where.append("status = 'completed'")
    if since:
        where.append("timestamp >= ?")
        params.append(since)
    if cage is not None:
        where.append("relay_unit_id = ?")
        params.append(int(cage))
    sql = f"SELECT {', '.join(select)} FROM dispensing_history"
    if where:
        sql += " WHERE " + " AND ".join(where)
    sql += " ORDER BY history_id DESC"
    if last:
        sql += " LIMIT ?"
        params.append(int(last))
    return [dict(row) for row in conn.execute(sql, params)]


# --- the balance side (CSV) ---------------------------------------------------


def read_checks(csv_path: str) -> list:
    if not os.path.isfile(csv_path):
        return []
    with open(csv_path, newline='', encoding='utf-8') as handle:
        return list(csv.DictReader(handle))


def write_checks(csv_path: str, rows: list) -> None:
    """Rewrite the CSV atomically (write beside, then rename over)."""
    tmp_path = csv_path + '.tmp'
    with open(tmp_path, 'w', newline='', encoding='utf-8') as handle:
        writer = csv.DictWriter(handle, fieldnames=CSV_COLUMNS, extrasaction='ignore')
        writer.writeheader()
        for row in rows:
            writer.writerow({column: _cell(row.get(column)) for column in CSV_COLUMNS})
    os.replace(tmp_path, csv_path)


def _cell(value):
    if value is None:
        return ''
    if isinstance(value, float):
        return repr(value)
    return value


def build_check(delivery: dict, *, gross_g, tare_g, net_g, temp_c, density, note, now) -> dict:
    """One CSV row: the reading, the volume it means, and the delivery snapshot."""
    measured_ml = net_g / density
    target = delivery.get('volume_dispensed')
    pulses = delivery.get('pulses_fired')
    q = delivery.get('volume_per_pulse_ml')
    row = {
        'history_id': delivery['history_id'],
        'weighed_at': now.isoformat(timespec='seconds'),
        'gross_g': gross_g,
        'tare_g': tare_g,
        'net_g': net_g,
        'temp_c': temp_c,
        'density_g_per_ml': density,
        'measured_ml': measured_ml,
        'delivered_at': delivery.get('timestamp'),
        'cage_id': delivery.get('relay_unit_id'),
        'schedule_id': delivery.get('schedule_id'),
        'animal_id': delivery.get('animal_id'),
        'status': delivery.get('status'),
        'topology': delivery.get('topology'),
        'target_ml': target,
        'pulses_fired': pulses,
        'volume_per_pulse_ml': q,
        'expected_ml': expected_ml(pulses, q),
        'planner': planner_verdict(target, pulses, q),
        'note': note or '',
    }
    for column in (
        'calibration_id',
        'pulse_width_ms',
        'inter_pulse_interval_ms',
        'duration_s',
        'app_version',
    ):
        row[column] = delivery.get(column)
    return row


# --- commands -----------------------------------------------------------------


def _fmt(value, digits=4):
    if value is None or value == '':
        return '-'
    try:
        return f"{float(value):.{digits}f}"
    except (TypeError, ValueError):
        return str(value)


def _list(conn, checks, args) -> int:
    weighed = {str(row['history_id']): row for row in checks}
    rows = fetch_deliveries(
        conn, last=args.last, since=args.since, cage=args.cage, all_statuses=args.all
    )
    if not rows:
        _say("no deliveries match")
        return 0
    header = (
        f"{'id':>6} {'delivered_at':19} {'cage':>4} {'topology':15} {'status':9} "
        f"{'target':>7} {'pulses':>6} {'mL/pulse':>9} {'expected':>8} {'planner':8} "
        f"{'weighed':>8} {'short':>8} {'cal':>4} {'version':8}"
    )
    _say(header)
    for row in rows:
        check = weighed.get(str(row['history_id']))
        measured = float(check['measured_ml']) if check and check.get('measured_ml') else None
        expected = expected_ml(row['pulses_fired'], row['volume_per_pulse_ml'])
        shortfall = None
        if measured is not None and expected is not None:
            shortfall = measured - expected
        _say(
            f"{row['history_id']:>6} {str(row['timestamp'])[:19]:19} {row['relay_unit_id']:>4} "
            f"{(row['topology'] or '-'):15} {row['status']:9} "
            f"{_fmt(row['volume_dispensed'], 3):>7} {_fmt(row['pulses_fired'], 0):>6} "
            f"{_fmt(row['volume_per_pulse_ml'], 6):>9} {_fmt(expected):>8} "
            f"{(planner_verdict(row['volume_dispensed'], row['pulses_fired'], row['volume_per_pulse_ml']) or '-'):8} "
            f"{_fmt(measured):>8} {_fmt(shortfall):>8} {_fmt(row['calibration_id'], 0):>4} "
            f"{(row['app_version'] or '-'):8}"
        )
    _say(
        f"{len(rows)} delivered, {sum(1 for r in rows if str(r['history_id']) in weighed)} weighed"
    )
    return 0


def _weigh(conn, csv_path, checks, args) -> int:
    rows = fetch_deliveries(conn, history_id=args.history_id)
    if not rows:
        return _fail(f"no dispensing_history row with history_id {args.history_id}")
    delivery = rows[0]
    if delivery['status'] != 'completed':
        _say(
            f"note: delivery {args.history_id} has status {delivery['status']!r}, "
            "it is recorded as such"
        )

    if args.net is not None:
        if args.gross is not None or args.tare is not None:
            return _fail("give either --net or --gross with --tare, not both")
        gross_g, tare_g, net_g = None, None, args.net
    else:
        if args.gross is None or args.tare is None:
            return _fail("a reading is --gross G --tare T (the raw balance readings) or --net N")
        gross_g, tare_g = args.gross, args.tare
        net_g = gross_g - tare_g
    if net_g < 0:
        return _fail(f"net mass {net_g:.4f} g is negative; check gross and tare")

    if args.density is not None:
        density = args.density
        temp_c = args.temp_c
    else:
        temp_c = DEFAULT_TEMP_C if args.temp_c is None else args.temp_c
        try:
            density = water_density(temp_c)
        except ValueError as exc:
            return _fail(str(exc))
    if density <= 0:
        return _fail("density must be positive")

    existing = [row for row in checks if str(row['history_id']) == str(args.history_id)]
    if existing and not args.replace:
        return _fail(
            f"delivery {args.history_id} already has a reading "
            f"({existing[0]['net_g']} g on {existing[0]['weighed_at']}); "
            "pass --replace to overwrite it"
        )

    check = build_check(
        delivery,
        gross_g=gross_g,
        tare_g=tare_g,
        net_g=net_g,
        temp_c=temp_c,
        density=density,
        note=args.note,
        now=datetime.now(),
    )
    kept = [row for row in checks if str(row['history_id']) != str(args.history_id)]
    kept.append(check)
    kept.sort(key=lambda row: int(row['history_id']))
    write_checks(csv_path, kept)

    expected = check['expected_ml']
    conditions = f"at {temp_c:g} C" if temp_c is not None else f"at {density:g} g/mL"
    line = (
        f"delivery {check['history_id']} cage {check['cage_id']} "
        f"({check['topology'] or 'topology not recorded'}): "
        f"net {net_g:.4f} g {conditions} = {check['measured_ml']:.4f} mL"
    )
    if expected is not None:
        line += (
            f"; pulses x mL/pulse = {expected:.4f} mL, "
            f"shortfall {check['measured_ml'] - expected:+.4f} mL"
        )
    _say(line)
    _say(f"recorded in {csv_path}")
    return 0


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument(
        '--data-dir',
        help=f"device data directory holding {DB_NAME} (default: $RRR_DATA, else {DEVICE_DATA_DIR})",
    )
    parser.add_argument('--csv', help=f"readings file (default: {CSV_NAME} in the data directory)")
    commands = parser.add_subparsers(dest='command', required=True)

    listing = commands.add_parser('list', help="show recent deliveries and their readings")
    listing.add_argument('--last', type=int, default=30, help="how many rows (default 30)")
    listing.add_argument('--since', help="ISO timestamp; only deliveries at or after it")
    listing.add_argument('--cage', type=int, help="only this cage")
    listing.add_argument('--all', action='store_true', help="include partial/failed rows")

    weigh = commands.add_parser('weigh', help="record a balance reading for one delivery")
    weigh.add_argument('history_id', type=int, help="the dispensing_history row (see list)")
    weigh.add_argument('--gross', type=float, help="balance reading with the water, g")
    weigh.add_argument('--tare', type=float, help="balance reading of the empty vessel, g")
    weigh.add_argument('--net', type=float, help="net mass, g, when the balance was tared")
    weigh.add_argument(
        '--temp-c', type=float, help=f"water temperature (default {DEFAULT_TEMP_C:g} C)"
    )
    weigh.add_argument('--density', type=float, help="override the density, g/mL")
    weigh.add_argument('--note', help="free text kept with the reading")
    weigh.add_argument('--replace', action='store_true', help="overwrite an existing reading")
    args = parser.parse_args(argv)

    root = bench_data_dir(args.data_dir)
    if root is None:
        named = args.data_dir or os.environ.get('RRR_DATA')
        if named:
            return _fail(
                f"the data directory {named!r} (from --data-dir or RRR_DATA) is not a directory."
            )
        return _fail(
            "cannot find the device data directory: RRR_DATA is not set and "
            f"{DEVICE_DATA_DIR} does not exist. Pass --data-dir PATH."
        )
    db_path = os.path.join(root, DB_NAME)
    csv_path = os.path.abspath(args.csv) if args.csv else os.path.join(root, CSV_NAME)
    try:
        conn = open_readonly(db_path)
    except FileNotFoundError:
        return _fail(f"no database at {db_path}; this tool never creates one.")
    try:
        checks = read_checks(csv_path)
        if args.command == 'list':
            return _list(conn, checks, args)
        return _weigh(conn, csv_path, checks, args)
    except sqlite3.Error as exc:
        return _fail(f"database error: {exc}")
    finally:
        conn.close()


if __name__ == '__main__':
    sys.exit(main())
