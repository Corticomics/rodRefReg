"""Grade weighed bench deliveries against the topology validation criteria.

Input is one or more ``gravimetric_checks.csv`` files written by
tools/gravimetric_check.py (typically one per device; each row carries the
topology the delivery ran under). Completed deliveries of instant schedules
are grouped by topology, cage and the dose that was asked for, and graded
against the beaker criteria in docs/TOPOLOGY_VALIDATION.md:

    C2 precision   CV of the weighed volumes <= --cv-max (5 %, the lab's cap)
    C3 planner     every row fired the pulse count its recorded rounding
                   policy gives for the dose (and, with --policy, that policy
                   is the one required); a mismatch is a code regression,
                   not a hardware finding
    C4 trueness    |mean weighed - mean(pulses x mL/pulse)| <= q/2

C2 and C4 are graded for every topology except the reference (the manifold
rig by default), whose figures are printed as the baseline; C3 is graded
for every topology. Per dose, each other topology's precision is then
graded against the reference's:

    precision      SD_topology <= SD_reference x sqrt(chi2(0.95, n-1)/(n-1))
                   (CLSI EP15-A3 upper verification limit; 1.371 at n = 10)

The difference between the rigs' mean weighed volumes and between their
shortfalls is reported for information, not graded: each rig's trueness is
judged against its own pulses x mL/pulse (C4), because the two rigs' pulse
sizes and the manifold's needle differ by design.

    python3 tools/topology_compare.py manifold.csv independent.csv --policy nearest
    python3 tools/topology_compare.py c7.csv --since 2026-10-05 --until 2026-10-05

Exit status: 0 when every graded criterion passed, 1 when one failed or the
comparison is incomplete (a dose present for a topology but missing, or
short of --min-n rows, on the reference), 2 on a usage or input error.
Groups with fewer than --min-n rows are listed but not graded, and a report
with nothing graded is not a pass. Rows that did not complete, staggered
chunks, and rows without a recorded dose are counted and left out.
"""

from __future__ import annotations

import argparse
import csv
import json
import math
import os
import statistics
import sys
from collections import defaultdict
from datetime import date, datetime, timedelta

DEFAULT_REFERENCE = 'shared_manifold'
LEGACY_TOPOLOGY = 'not_recorded'
POLICIES = ('nearest', 'up')

# 95th percentile of chi-square by degrees of freedom (n - 1), the factor
# CLSI EP15-A3 uses for the upper verification limit of a claimed SD.
CHI2_95 = {
    1: 3.841,
    2: 5.991,
    3: 7.815,
    4: 9.488,
    5: 11.070,
    6: 12.592,
    7: 14.067,
    8: 15.507,
    9: 16.919,
    10: 18.307,
    11: 19.675,
    12: 21.026,
    13: 22.362,
    14: 23.685,
    15: 24.996,
    16: 26.296,
    17: 27.587,
    18: 28.869,
    19: 30.144,
    20: 31.410,
    21: 32.671,
    22: 33.924,
    23: 35.172,
    24: 36.415,
    25: 37.652,
    26: 38.885,
    27: 40.113,
    28: 41.337,
    29: 42.557,
    30: 43.773,
}


def chi2_95(df: int) -> float:
    """chi-square 95th percentile; Wilson-Hilferty beyond the table."""
    if df in CHI2_95:
        return CHI2_95[df]
    z = 1.6449
    return df * (1 - 2 / (9 * df) + z * math.sqrt(2 / (9 * df))) ** 3


def uvl_factor(n: int) -> float:
    """Multiply a reference SD by this to get the upper verification limit at n."""
    df = n - 1
    return math.sqrt(chi2_95(df) / df)


# --- reading -------------------------------------------------------------------


class InputError(ValueError):
    """An input file cannot be read as a readings file."""


def _float(value):
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def iso_bound(text: str) -> str:
    """A --since/--until value as the ISO text the CSV's delivered_at uses."""
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


def _in_range(delivered_at, since, until) -> bool:
    if not (since or until):
        return True
    if not delivered_at:
        return False
    if since and delivered_at < since:
        return False
    if until:
        if 'T' in until:
            return delivered_at <= until
        next_day = (date.fromisoformat(until) + timedelta(days=1)).isoformat()
        return delivered_at < next_day
    return True


def load_rows(paths, *, since=None, until=None):
    """(gradable rows, excluded counts). Accepts a byte-order mark."""
    rows, excluded = [], defaultdict(int)
    for path in paths:
        try:
            with open(path, newline='', encoding='utf-8-sig') as handle:
                reader = csv.DictReader(handle)
                raw_rows = list(reader)
                header = reader.fieldnames or []
        except (UnicodeDecodeError, csv.Error) as exc:
            raise InputError(
                f"{path} is not a UTF-8 CSV ({exc.__class__.__name__}); "
                "re-save it as 'CSV UTF-8' or use the copy gravimetric_check wrote"
            ) from None
        if raw_rows and 'measured_ml' not in header:
            raise InputError(f"{path} has no measured_ml column; it is not a readings file")
        for raw in raw_rows:
            measured = _float(raw.get('measured_ml'))
            if measured is None:
                excluded['no reading'] += 1
                continue
            if not _in_range(raw.get('delivered_at') or '', since, until):
                continue
            if (raw.get('status') or 'completed') != 'completed':
                excluded['did not complete'] += 1
                continue
            if raw.get('delivery_mode') == 'staggered':
                excluded['staggered chunk'] += 1
                continue
            target = _float(raw.get('target_ml'))
            if target is None or target <= 0:
                excluded['no recorded dose'] += 1
                continue
            rows.append(
                {
                    'source': os.path.basename(path),
                    'history_id': raw.get('history_id'),
                    'topology': raw.get('topology') or LEGACY_TOPOLOGY,
                    'cage_id': raw.get('cage_id') or '?',
                    'target_ml': target,
                    'measured_ml': measured,
                    'expected_ml': _float(raw.get('expected_ml')),
                    'q': _float(raw.get('volume_per_pulse_ml')),
                    'pulses': _float(raw.get('pulses_fired')),
                    'planner': raw.get('planner') or '',
                    'dose_rounding': raw.get('dose_rounding') or '',
                }
            )
    return rows, dict(excluded)


def dose_key(target_ml) -> str:
    return '?' if target_ml is None else f"{target_ml:.3f}"


# --- grading -------------------------------------------------------------------


def _stats(values):
    n = len(values)
    mean = statistics.fmean(values) if n else None
    sd = statistics.stdev(values) if n >= 2 else None
    cv = (sd / mean * 100.0) if sd is not None and mean else None
    return n, mean, sd, cv


def grade_group(rows, *, cv_max, min_n, policy, is_reference) -> dict:
    """Summary and C2/C3/C4 verdicts for one (topology, cage, dose) group."""
    measured = [r['measured_ml'] for r in rows]
    n, mean, sd, cv = _stats(measured)
    expected = [r['expected_ml'] for r in rows if r['expected_ml'] is not None]
    qs = [r['q'] for r in rows if r['q']]
    q = statistics.median(qs) if qs else None
    mean_expected = statistics.fmean(expected) if expected else None
    shortfall = (mean - mean_expected) if mean is not None and mean_expected is not None else None
    target = rows[0]['target_ml']
    bias_pct = ((mean - target) / target * 100.0) if mean is not None and target else None
    verdict_counts = defaultdict(int)
    for r in rows:
        verdict_counts[r['planner'] or 'none'] += 1
    policies = sorted({r['dose_rounding'] for r in rows if r['dose_rounding']})
    wrong_policy = sum(
        1 for r in rows if policy and r['dose_rounding'] and r['dose_rounding'] != policy
    )
    unjudged = verdict_counts.get('none', 0)

    graded = n >= min_n
    verdicts = {}
    if graded:
        verdicts['C3_planner'] = (
            verdict_counts.get('mismatch', 0) == 0 and wrong_policy == 0 and unjudged < n
        )
        if not is_reference:
            verdicts['C2_precision'] = cv is not None and cv <= cv_max
            if shortfall is not None and q:
                verdicts['C4_trueness'] = abs(shortfall) <= q / 2
    return {
        'topology': rows[0]['topology'],
        'cage_id': rows[0]['cage_id'],
        'dose_ml': target,
        'n': n,
        'graded': graded,
        'reference': is_reference,
        'mean_ml': mean,
        'sd_ml': sd,
        'cv_pct': cv,
        'q_ml': q,
        'mean_expected_ml': mean_expected,
        'shortfall_ml': shortfall,
        'bias_vs_dose_pct': bias_pct,
        'planner': dict(sorted(verdict_counts.items())),
        'policies': policies,
        'rows_with_other_policy': wrong_policy,
        'verdicts': verdicts,
    }


def grade_equivalence(pooled, *, reference, min_n) -> list:
    """Per dose: each non-reference topology's precision against the reference."""
    results = []
    by_dose = defaultdict(dict)
    for group in pooled:
        by_dose[dose_key(group['dose_ml'])][group['topology']] = group
    for _dose, per_topology in sorted(by_dose.items()):
        ref = per_topology.get(reference)
        for topology, group in sorted(per_topology.items()):
            if topology == reference or group['n'] < min_n:
                continue
            entry = {
                'dose_ml': group['dose_ml'],
                'topology': topology,
                'reference': reference,
                'n': group['n'],
                'n_reference': ref['n'] if ref else 0,
                'graded': False,
            }
            if (
                ref
                and ref['n'] >= min_n
                and ref['sd_ml'] is not None
                and group['sd_ml'] is not None
            ):
                factor = uvl_factor(group['n'])
                uvl = ref['sd_ml'] * factor
                entry.update(
                    {
                        'graded': True,
                        'sd_ml': group['sd_ml'],
                        'sd_reference_ml': ref['sd_ml'],
                        'uvl_factor': factor,
                        'uvl_ml': uvl,
                        'mean_diff_ml': group['mean_ml'] - ref['mean_ml'],
                        'shortfall_diff_ml': (
                            group['shortfall_ml'] - ref['shortfall_ml']
                            if group['shortfall_ml'] is not None
                            and ref['shortfall_ml'] is not None
                            else None
                        ),
                        'verdicts': {'precision_vs_reference': group['sd_ml'] <= uvl},
                    }
                )
            results.append(entry)
    return results


def compare(rows, *, reference, cv_max, min_n, policy=None, excluded=None) -> dict:
    groups = defaultdict(list)
    pooled = defaultdict(list)
    for r in rows:
        groups[(r['topology'], str(r['cage_id']), dose_key(r['target_ml']))].append(r)
        pooled[(r['topology'], dose_key(r['target_ml']))].append(r)

    def grade(key_rows):
        topology = key_rows[0]['topology']
        return grade_group(
            key_rows,
            cv_max=cv_max,
            min_n=min_n,
            policy=policy,
            is_reference=(topology == reference),
        )

    detail = [grade(groups[k]) for k in sorted(groups)]
    summary = []
    for key in sorted(pooled):
        group = grade(pooled[key])
        group['cage_id'] = 'all'
        summary.append(group)
    reference_present = any(g['topology'] == reference for g in summary)
    equivalence = grade_equivalence(summary, reference=reference, min_n=min_n)

    failed, incomplete, graded = [], [], 0
    for group in detail + summary:
        for name, ok in group['verdicts'].items():
            graded += 1
            if not ok:
                failed.append(
                    f"{group['topology']} cage {group['cage_id']} "
                    f"{dose_key(group['dose_ml'])} mL: {name}"
                )
    for entry in equivalence:
        if not entry['graded']:
            if reference_present:
                incomplete.append(
                    f"{entry['topology']} at {dose_key(entry['dose_ml'])} mL: no precision "
                    f"comparison (reference n = {entry['n_reference']}, need {min_n})"
                )
            continue
        for name, ok in entry['verdicts'].items():
            graded += 1
            if not ok:
                failed.append(
                    f"{entry['topology']} vs {reference} at {dose_key(entry['dose_ml'])} mL: {name}"
                )
    return {
        'rows': len(rows),
        'excluded': excluded or {},
        'reference': reference,
        'reference_present': reference_present,
        'policy': policy,
        'cv_max_pct': cv_max,
        'min_n': min_n,
        'by_cage': detail,
        'pooled': summary,
        'equivalence': equivalence,
        'graded': graded,
        'failed': failed,
        'incomplete': incomplete,
        # "Passed" needs something graded and nothing missing: a file of three
        # readings, or a dose the reference never ran, is not a clean bill.
        'passed': graded > 0 and not failed and not incomplete,
    }


# --- printing ------------------------------------------------------------------


def say(line: str) -> None:
    print(line, flush=True)


def _fmt(value, digits=4):
    if value is None:
        return '-'
    return f"{value:.{digits}f}"


def _mark(group, name):
    if group.get('reference') and name in ('C2_precision', 'C4_trueness'):
        return 'ref'
    verdicts = group['verdicts']
    if name not in verdicts:
        return '  '
    return 'ok' if verdicts[name] else 'FAIL'


def print_report(report) -> None:
    say(
        f"{report['rows']} weighed deliveries graded; reference topology {report['reference']}; "
        f"CV cap {report['cv_max_pct']:g} %; rounding policy required: "
        f"{report['policy'] or 'the one each row recorded'}; groups graded from n = {report['min_n']}"
    )
    if report['excluded']:
        parts = ', '.join(f"{count} {why}" for why, count in sorted(report['excluded'].items()))
        say(f"left out: {parts}")
    for title, groups in (
        ("Per cage", report['by_cage']),
        ("Pooled per topology", report['pooled']),
    ):
        say("")
        say(title)
        say(
            f"{'topology':16} {'cage':>4} {'dose':>6} {'n':>3} {'mean':>7} {'sd':>7} {'cv%':>5} "
            f"{'q':>8} {'plan':>7} {'short':>8} {'bias%':>6} {'planner':22} {'C2':4} {'C3':4} {'C4':4}"
        )
        for g in groups:
            planner = ' '.join(f"{k}={v}" for k, v in g['planner'].items())
            say(
                f"{g['topology']:16} {str(g['cage_id']):>4} {dose_key(g['dose_ml']):>6} {g['n']:>3} "
                f"{_fmt(g['mean_ml']):>7} {_fmt(g['sd_ml']):>7} {_fmt(g['cv_pct'], 1):>5} "
                f"{_fmt(g['q_ml'], 6):>8} {_fmt(g['mean_expected_ml']):>7} "
                f"{_fmt(g['shortfall_ml']):>8} {_fmt(g['bias_vs_dose_pct'], 1):>6} "
                f"{planner:22} {_mark(g, 'C2_precision'):4} {_mark(g, 'C3_planner'):4} "
                f"{_mark(g, 'C4_trueness'):4}"
                + ("" if g['graded'] else "  (not graded: n too small)")
            )
    say("")
    say(f"Precision against the reference ({report['reference']}), per dose")
    if not report['reference_present']:
        say(
            f"  not graded: no rows from the reference topology {report['reference']} in the input"
        )
    elif not report['equivalence']:
        say("  no other topology with enough rows to compare")
    for e in report['equivalence'] if report['reference_present'] else []:
        if not e['graded']:
            say(
                f"  {e['topology']} at {dose_key(e['dose_ml'])} mL: INCOMPLETE "
                f"(reference n = {e['n_reference']}, need {report['min_n']})"
            )
            continue
        ok = e['verdicts']['precision_vs_reference']
        say(
            f"  {e['topology']} at {dose_key(e['dose_ml'])} mL: SD {_fmt(e['sd_ml'])} vs UVL "
            f"{_fmt(e['uvl_ml'])} (= {_fmt(e['sd_reference_ml'])} x {e['uvl_factor']:.3f}) "
            f"{'ok' if ok else 'FAIL'}; for information: mean diff {e['mean_diff_ml']:+.4f} mL, "
            f"shortfall diff "
            + ("-" if e['shortfall_diff_ml'] is None else f"{e['shortfall_diff_ml']:+.4f} mL")
        )
    say("")
    if report['passed']:
        say(f"RESULT: every graded criterion passed ({report['graded']} graded)")
    elif not report['graded']:
        say(f"RESULT: nothing graded; every group needs at least {report['min_n']} readings")
    else:
        say("RESULT: FAILED" if report['failed'] else "RESULT: INCOMPLETE")
        for line in report['failed'] + report['incomplete']:
            say(f"  - {line}")


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument('csv', nargs='+', help="gravimetric_checks.csv file(s)")
    parser.add_argument(
        '--reference',
        default=DEFAULT_REFERENCE,
        help=f"topology the others are compared to (default {DEFAULT_REFERENCE})",
    )
    parser.add_argument(
        '--policy',
        choices=POLICIES,
        help="require every graded row to have been rounded with this policy (C3)",
    )
    parser.add_argument('--cv-max', type=float, default=5.0, help="C2 cap in %% (default 5)")
    parser.add_argument(
        '--min-n',
        type=int,
        default=10,
        help="rows a group needs to be graded (default 10, per ISO 8655-6)",
    )
    parser.add_argument(
        '--since', type=iso_bound, help="only deliveries at or after this ISO date/date-time"
    )
    parser.add_argument(
        '--until', type=iso_bound, help="only deliveries up to this ISO date/date-time"
    )
    parser.add_argument('--json', help="also write the full report to this file")
    args = parser.parse_args(argv)
    if args.min_n < 2:
        print("ERROR: --min-n must be at least 2 (an SD needs two rows)", file=sys.stderr)
        return 2
    try:
        rows, excluded = load_rows(args.csv, since=args.since, until=args.until)
    except (OSError, InputError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2
    if not rows:
        print("ERROR: no gradable weighed deliveries in the given file(s)", file=sys.stderr)
        if excluded:
            print(f"left out: {excluded}", file=sys.stderr)
        return 2
    report = compare(
        rows,
        reference=args.reference,
        cv_max=args.cv_max,
        min_n=args.min_n,
        policy=args.policy,
        excluded=excluded,
    )
    print_report(report)
    if args.json:
        with open(args.json, 'w', encoding='utf-8') as handle:
            json.dump(report, handle, indent=2)
        print(f"report written to {args.json}", flush=True)
    return 0 if report['passed'] else 1


if __name__ == '__main__':
    sys.exit(main())
