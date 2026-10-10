"""Pair bench deliveries with balance readings.

The topology validation (docs/TOPOLOGY_VALIDATION.md) asks two questions of
every weighed delivery: did the planner fire the right number of pulses for
the dose that was asked for, and did those pulses put their calibrated
volume (pulses x mL/pulse) in the beaker? The app records the first half in
dispensing_history (v1.21.0: the dose asked for, the rounding policy, the
pulses fired, the calibration); this tool records the balance side next to
it.

    cd ~/rrr/current/Project
    ~/rrr/shared/venv/bin/python3 tools/gravimetric_check.py list
    ~/rrr/shared/venv/bin/python3 tools/gravimetric_check.py weigh 1234 --gross 12.7413 --tare 12.1435
    ~/rrr/shared/venv/bin/python3 tools/gravimetric_check.py weigh 1235 --net 0.5988 --temp-c 22
    ~/rrr/shared/venv/bin/python3 tools/gravimetric_check.py daily --since 2026-10-01

``list`` shows recent completed deliveries: the dose asked for, the rounding
policy, the pulses fired, the plan (pulses x mL/pulse), the planner verdict,
the calibration row, and the reading once weighed. ``weigh`` stores one
reading against one delivery in ``gravimetric_checks.csv`` beside the
database (``--csv`` names another file): the raw gross and tare (or a net) in
grams, the water temperature, the density used, the resulting volume, and a
snapshot of the delivery row, so the file is self-contained for
tools/topology_compare.py. ``daily`` totals the ledger per day and cage: the
deliveries by status and the volume the hardware reports it dispensed (the
daily-total and row-status criteria; no sqlite3 command needed).

Planner verdict, for a completed delivery of an instant schedule:
  ok        the pulse count is what the recorded rounding policy gives for
            the dose asked for
  mismatch  it is not: a code regression, never a hardware finding
Rows written before the policy was recorded show which policy the count is
consistent with instead (nearest, up, both, or mismatch). A staggered chunk
shows 'carry': its count depends on the window's running carry, so it is
not judged per row. A delivery that did not complete, or has no recorded
dose, shows nothing.

The database is opened read-only and never created, so the tool is safe to
run while the app is running. Weigh promptly after the delivery.
"""

from __future__ import annotations

import argparse
import csv
import math
import os
import sqlite3
import sys
from datetime import date, datetime, timedelta
from pathlib import Path


def _append_project_to_syspath() -> None:
    here = os.path.abspath(os.path.dirname(__file__))
    project_root = os.path.abspath(os.path.join(here, os.pardir))
    if project_root not in sys.path:
        sys.path.append(project_root)


_append_project_to_syspath()

from utils.dose_rounding import whole_pulses  # noqa: E402
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
#   target_ml   the dose asked for (dispensing_history.volume_requested_ml)
#   planned_ml  the planned volume the ledger records (volume_dispensed)
#   expected_ml pulses actually fired x mL/pulse
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
    'delivery_mode',
    'topology',
    'target_ml',
    'dose_rounding',
    'pulses_fired',
    'volume_per_pulse_ml',
    'expected_ml',
    'planned_ml',
    'planner',
    'calibration_id',
    'pulse_width_ms',
    'inter_pulse_interval_ms',
    'duration_s',
    'app_version',
    'note',
)

# dispensing_history columns this tool reads that older databases may lack.
OPTIONAL_COLUMNS = (
    'volume_actual_ml',
    'pulses_fired',
    'volume_per_pulse_ml',
    'topology',
    'calibration_id',
    'pulse_width_ms',
    'inter_pulse_interval_ms',
    'duration_s',
    'app_version',
    'volume_requested_ml',
    'dose_rounding',
)


def _say(message: str) -> None:
    print(message, flush=True)


def _fail(message: str) -> int:
    print(f"ERROR: {message}", file=sys.stderr, flush=True)
    return 2


# --- arithmetic -------------------------------------------------------------


def water_density(temp_c: float) -> float:
    """Density of water at ``temp_c`` (linear between tabulated degrees)."""
    if not (15.0 <= temp_c <= 30.0):
        raise ValueError(f"water temperature {temp_c} C is outside the 15-30 C table")
    low = math.floor(temp_c)
    high = min(low + 1, 30)
    d_low, d_high = WATER_DENSITY_G_PER_ML[low], WATER_DENSITY_G_PER_ML[high]
    return d_low + (d_high - d_low) * (temp_c - low)


def planner_verdict(
    requested_ml,
    pulses_fired,
    volume_per_pulse_ml,
    *,
    policy=None,
    status='completed',
    delivery_mode=None,
) -> str:
    """How the fired pulse count relates to the dose that was asked for.

    Mirrors RelayWorker._quantize_to_pulses for a single-shot (instant)
    request, through the same utils.dose_rounding.whole_pulses: nearest
    rounds an exact half up, and up takes the next whole pulse. See the
    module docstring for the labels.
    """
    if status != 'completed':
        return ''
    try:
        dose = float(requested_ml)
        pulses = int(pulses_fired)
        q = float(volume_per_pulse_ml)
    except (TypeError, ValueError):
        return ''
    if dose <= 0 or q <= 0 or pulses < 0:
        return ''
    if delivery_mode == 'staggered':
        return 'carry'
    nearest = whole_pulses(dose, q)
    up = whole_pulses(dose, q, round_up=True)
    if policy == 'nearest':
        return 'ok' if pulses == nearest else 'mismatch'
    if policy == 'up':
        return 'ok' if pulses == up else 'mismatch'
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


def iso_bound(text: str) -> str:
    """Validate a --since/--until value and put it in the ledger's form.

    The ledger stores ``datetime.isoformat()`` strings ('2026-09-29T08:00:00')
    and the comparison is textual, so '2026-09-29 08:00' (a space sorts
    below 'T') or an unpadded hour would silently select the wrong rows.
    A date stays a date; a date-time is re-rendered with the 'T'.
    """
    text = text.strip()
    try:
        return date.fromisoformat(text).isoformat()
    except ValueError:
        pass
    try:
        return datetime.fromisoformat(text).isoformat()
    except ValueError:
        raise argparse.ArgumentTypeError(
            f"{text!r} is not an ISO date or date-time (e.g. 2026-10-02 or 2026-10-02T08:00)"
        ) from None


def _until_clause(bound: str):
    """(SQL, parameter) for an inclusive upper bound on timestamp."""
    if 'T' in bound:
        return "dh.timestamp <= ?", bound
    next_day = date.fromisoformat(bound) + timedelta(days=1)
    return "dh.timestamp < ?", next_day.isoformat()


# --- the delivery side (read-only) ------------------------------------------


def open_readonly(db_path: str) -> sqlite3.Connection:
    """Open the device database read-only; a missing file is an error, not a new DB."""
    if not os.path.isfile(db_path):
        raise FileNotFoundError(db_path)
    uri = Path(db_path).resolve().as_uri() + '?mode=ro'
    conn = sqlite3.connect(uri, uri=True)
    conn.row_factory = sqlite3.Row
    return conn


def _columns(conn: sqlite3.Connection, table: str) -> set:
    return {row[1] for row in conn.execute(f"PRAGMA table_info({table})")}


def fetch_deliveries(
    conn,
    *,
    last=None,
    since=None,
    until=None,
    cage=None,
    history_id=None,
    all_statuses=False,
):
    """Rows of dispensing_history as dicts, newest first.

    Every OPTIONAL_COLUMNS name is present (None where the database predates
    it), plus ``delivery_mode`` ('instant' / 'staggered'): the row's own,
    else its schedule's, else None.
    """
    present = _columns(conn, 'dispensing_history')
    if 'history_id' not in present:
        raise sqlite3.OperationalError("no dispensing_history table in this database")
    select = [
        f"dh.{column}"
        for column in (
            'history_id',
            'schedule_id',
            'animal_id',
            'relay_unit_id',
            'timestamp',
            'volume_dispensed',
            'status',
        )
    ]
    for column in OPTIONAL_COLUMNS:
        select.append(f"dh.{column}" if column in present else f"NULL AS {column}")
    # The row's own mode (v1.21.0) wins: a schedule can be deleted while its
    # rows stay, and a staggered chunk must never be judged like an instant
    # dose. Older rows fall back to the schedule's mode when it still exists.
    join = ""
    on_row = 'delivery_mode' in present
    on_schedule = 'delivery_mode' in _columns(conn, 'schedules')
    if on_schedule:
        join = " LEFT JOIN schedules s ON s.schedule_id = dh.schedule_id"
    if on_row and on_schedule:
        select.append("COALESCE(dh.delivery_mode, s.delivery_mode) AS delivery_mode")
    elif on_row:
        select.append("dh.delivery_mode AS delivery_mode")
    elif on_schedule:
        select.append("s.delivery_mode AS delivery_mode")
    else:
        select.append("NULL AS delivery_mode")
    where, params = [], []
    if history_id is not None:
        where.append("dh.history_id = ?")
        params.append(int(history_id))
    if not all_statuses and history_id is None:
        where.append("dh.status = 'completed'")
    if since:
        where.append("dh.timestamp >= ?")
        params.append(since)
    if until:
        clause, value = _until_clause(until)
        where.append(clause)
        params.append(value)
    if cage is not None:
        where.append("dh.relay_unit_id = ?")
        params.append(int(cage))
    sql = f"SELECT {', '.join(select)} FROM dispensing_history dh{join}"
    if where:
        sql += " WHERE " + " AND ".join(where)
    sql += " ORDER BY dh.history_id DESC"
    if last:
        sql += " LIMIT ?"
        params.append(int(last))
    return [dict(row) for row in conn.execute(sql, params)]


def verdict_for(delivery: dict) -> str:
    return planner_verdict(
        delivery.get('volume_requested_ml'),
        delivery.get('pulses_fired'),
        delivery.get('volume_per_pulse_ml'),
        policy=delivery.get('dose_rounding'),
        status=delivery.get('status'),
        delivery_mode=delivery.get('delivery_mode'),
    )


# --- the balance side (CSV) ---------------------------------------------------


class ReadingsFileError(ValueError):
    """The readings file cannot be used as it is."""


def read_checks(csv_path: str) -> list:
    """Existing readings. Accepts a byte-order mark (Excel's 'CSV UTF-8')."""
    if not os.path.isfile(csv_path):
        return []
    try:
        with open(csv_path, newline='', encoding='utf-8-sig') as handle:
            reader = csv.DictReader(handle)
            rows = list(reader)
            header = reader.fieldnames or []
    except (UnicodeDecodeError, csv.Error) as exc:
        raise ReadingsFileError(
            f"{csv_path} is not a UTF-8 CSV ({exc.__class__.__name__}); "
            "re-save it as 'CSV UTF-8' or restore the copy the tool wrote"
        ) from None
    if rows and 'history_id' not in header:
        raise ReadingsFileError(
            f"{csv_path} has no history_id column; it is not a readings file this tool wrote"
        )
    return rows


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
        'measured_ml': net_g / density,
        'delivered_at': delivery.get('timestamp'),
        'cage_id': delivery.get('relay_unit_id'),
        'schedule_id': delivery.get('schedule_id'),
        'animal_id': delivery.get('animal_id'),
        'status': delivery.get('status'),
        'delivery_mode': delivery.get('delivery_mode'),
        'topology': delivery.get('topology'),
        'target_ml': delivery.get('volume_requested_ml'),
        'dose_rounding': delivery.get('dose_rounding'),
        'pulses_fired': pulses,
        'volume_per_pulse_ml': q,
        'expected_ml': expected_ml(pulses, q),
        'planned_ml': delivery.get('volume_dispensed'),
        'planner': verdict_for(delivery),
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
    weighed = {str(row.get('history_id')): row for row in checks}
    rows = fetch_deliveries(
        conn,
        last=args.last,
        since=args.since,
        until=args.until,
        cage=args.cage,
        all_statuses=args.all,
    )
    if not rows:
        _say("no deliveries match")
        return 0
    _say(
        f"{'id':>6} {'delivered_at':19} {'cage':>4} {'topology':15} {'status':9} "
        f"{'dose':>6} {'rounding':8} {'pulses':>6} {'mL/pulse':>9} {'plan':>7} {'planner':8} "
        f"{'weighed':>8} {'short':>8} {'cal':>4}"
    )
    for row in rows:
        check = weighed.get(str(row['history_id']))
        measured = float(check['measured_ml']) if check and check.get('measured_ml') else None
        plan = expected_ml(row['pulses_fired'], row['volume_per_pulse_ml'])
        shortfall = measured - plan if measured is not None and plan is not None else None
        _say(
            f"{row['history_id']:>6} {str(row['timestamp'])[:19]:19} {row['relay_unit_id']:>4} "
            f"{(row['topology'] or '-'):15} {row['status']:9} "
            f"{_fmt(row['volume_requested_ml'], 3):>6} {(row['dose_rounding'] or '-'):8} "
            f"{_fmt(row['pulses_fired'], 0):>6} {_fmt(row['volume_per_pulse_ml'], 6):>9} "
            f"{_fmt(plan):>7} {(verdict_for(row) or '-'):8} "
            f"{_fmt(measured):>8} {_fmt(shortfall):>8} {_fmt(row['calibration_id'], 0):>4}"
        )
    weighed_count = sum(1 for r in rows if str(r['history_id']) in weighed)
    _say(f"{len(rows)} delivered, {weighed_count} weighed")
    return 0


def _daily(conn, args) -> int:
    rows = fetch_deliveries(
        conn, since=args.since, until=args.until, cage=args.cage, all_statuses=True
    )
    if not rows:
        _say("no deliveries match")
        return 0
    days = {}
    for row in rows:
        key = (str(row['timestamp'])[:10], row['relay_unit_id'], row['topology'] or '-')
        day = days.setdefault(
            key,
            {'completed': 0, 'partial': 0, 'failed': 0, 'other': 0, 'dispensed': None},
        )
        status = row['status'] if row['status'] in ('completed', 'partial', 'failed') else 'other'
        day[status] += 1
        if row['volume_actual_ml'] is not None:
            day['dispensed'] = (day['dispensed'] or 0.0) + float(row['volume_actual_ml'])
    _say(
        f"{'day':10} {'cage':>4} {'topology':15} {'completed':>9} {'partial':>7} "
        f"{'failed':>6} {'other':>5} {'dispensed_mL':>12}"
    )
    for (day, cage, topology), d in sorted(days.items()):
        _say(
            f"{day:10} {cage:>4} {topology:15} {d['completed']:>9} {d['partial']:>7} "
            f"{d['failed']:>6} {d['other']:>5} {_fmt(d['dispensed']):>12}"
        )
    _say(
        "dispensed_mL is the sum of volume_actual_ml, what the hardware reports it "
        "dispensed (pulses x mL/pulse), partial deliveries included; 'other' counts "
        "rows such as sensor_failure. Compare it with the prescribed day and the "
        "weighed day."
    )
    return 0


def _weigh(conn, csv_path, checks, args) -> int:
    rows = fetch_deliveries(conn, history_id=args.history_id)
    if not rows:
        return _fail(f"no dispensing_history row with history_id {args.history_id}")
    delivery = rows[0]
    if delivery['status'] != 'completed':
        _say(
            f"note: delivery {args.history_id} has status {delivery['status']!r}; it is "
            "recorded as such and left out of the grading"
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

    existing = [row for row in checks if str(row.get('history_id')) == str(args.history_id)]
    if existing and not args.replace:
        return _fail(
            f"delivery {args.history_id} already has a reading "
            f"({existing[0].get('net_g')} g on {existing[0].get('weighed_at')}); "
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
    kept = [row for row in checks if str(row.get('history_id')) != str(args.history_id)]
    kept.append(check)
    kept.sort(key=lambda row: int(row['history_id']))
    write_checks(csv_path, kept)

    plan = check['expected_ml']
    conditions = f"at {temp_c:g} C" if temp_c is not None else f"at {density:g} g/mL"
    line = (
        f"delivery {check['history_id']} cage {check['cage_id']} "
        f"({check['topology'] or 'topology not recorded'}): "
        f"net {net_g:.4f} g {conditions} = {check['measured_ml']:.4f} mL"
    )
    if plan is not None:
        line += (
            f"; pulses x mL/pulse = {plan:.4f} mL, "
            f"shortfall {check['measured_ml'] - plan:+.4f} mL"
        )
    _say(line)
    if check['planner'] == 'mismatch':
        _say(
            f"WARNING: {check['pulses_fired']} pulses is not what the planner should fire for "
            f"{_fmt(check['target_ml'], 3)} mL; see TOPOLOGY_VALIDATION.md, Reading the results"
        )
    _say(f"recorded in {csv_path}")
    return 0


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument(
        '--data-dir',
        help=f"device data directory holding {DB_NAME} (default: $RRR_DATA, else {DEVICE_DATA_DIR})",
    )
    parser.add_argument(
        '--csv',
        help=f"readings file (default: {CSV_NAME} in the data directory); give it before "
        "the command, e.g. --csv c8_full.csv weigh 1234 --net 0.6",
    )
    commands = parser.add_subparsers(dest='command', required=True)

    listing = commands.add_parser('list', help="show recent deliveries and their readings")
    listing.add_argument('--last', type=int, default=30, help="how many rows (default 30)")
    listing.add_argument(
        '--since', type=iso_bound, help="only deliveries at or after this ISO date/date-time"
    )
    listing.add_argument(
        '--until', type=iso_bound, help="only deliveries up to this ISO date/date-time"
    )
    listing.add_argument('--cage', type=int, help="only this cage")
    listing.add_argument('--all', action='store_true', help="include partial/failed rows")

    daily = commands.add_parser('daily', help="per-day, per-cage totals from the ledger")
    daily.add_argument('--since', type=iso_bound, help="first day (ISO date)")
    daily.add_argument('--until', type=iso_bound, help="last day (ISO date), inclusive")
    daily.add_argument('--cage', type=int, help="only this cage")

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
        if args.command == 'daily':
            return _daily(conn, args)
        checks = read_checks(csv_path)
        if args.command == 'list':
            return _list(conn, checks, args)
        return _weigh(conn, csv_path, checks, args)
    except ReadingsFileError as exc:
        return _fail(str(exc))
    except sqlite3.Error as exc:
        return _fail(f"database error: {exc}")
    finally:
        conn.close()


if __name__ == '__main__':
    sys.exit(main())
