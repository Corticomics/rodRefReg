"""Grade weighed bench deliveries against the topology validation criteria.

Input is one or more ``gravimetric_checks.csv`` files written by
tools/gravimetric_check.py (one per device; each row carries the topology
the delivery ran under). Rows are grouped by topology, cage and dose, and
each group is graded against the beaker criteria in
docs/TOPOLOGY_VALIDATION.md:

    C2 precision   CV of the weighed volumes <= --cv-max (5 %, the lab's cap)
    C3 planner     every row's pulse count is what the planner should have
                   fired for its dose (nearest or rounded up); a 'mismatch'
                   is a code regression, not a hardware finding
    C4 trueness    |mean weighed - mean(pulses x mL/pulse)| <= q/2

and, per dose, the independent topology against the reference one:

    equivalence    SD_topology <= SD_reference x sqrt(chi2(0.95, n-1)/(n-1))
                   (CLSI EP15-A3 upper verification limit; 1.371 at n = 10)
                   and |mean_topology - mean_reference| <= --equivalence-pct
                   of the dose (2.5 %)

Always compared against pulses x mL/pulse, never against the nominal dose:
rounding to whole pulses is the planner's job and is graded separately.

    python3 tools/topology_compare.py manifold/gravimetric_checks.csv independent/gravimetric_checks.csv
    python3 tools/topology_compare.py *.csv --json report.json

Exit status 0 when every graded criterion passes, 1 when any fails, 2 on a
usage error. Groups with fewer than --min-n rows are listed but not graded.
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

DEFAULT_REFERENCE = 'shared_manifold'
LEGACY_TOPOLOGY = 'not_recorded'

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


def _float(value):
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def load_rows(paths) -> list:
    """Rows of every CSV, with the numeric fields parsed; unparseable rows dropped."""
    rows = []
    for path in paths:
        with open(path, newline='', encoding='utf-8') as handle:
            for raw in csv.DictReader(handle):
                measured = _float(raw.get('measured_ml'))
                if measured is None:
                    continue
                rows.append(
                    {
                        'source': os.path.basename(path),
                        'history_id': raw.get('history_id'),
                        'topology': raw.get('topology') or LEGACY_TOPOLOGY,
                        'cage_id': raw.get('cage_id') or '?',
                        'target_ml': _float(raw.get('target_ml')),
                        'measured_ml': measured,
                        'expected_ml': _float(raw.get('expected_ml')),
                        'q': _float(raw.get('volume_per_pulse_ml')),
                        'pulses': _float(raw.get('pulses_fired')),
                        'planner': raw.get('planner') or '',
                        'status': raw.get('status') or '',
                    }
                )
    return rows


def dose_key(target_ml) -> str:
    return '?' if target_ml is None else f"{target_ml:.3f}"


# --- grading -------------------------------------------------------------------


def _stats(values):
    n = len(values)
    mean = statistics.fmean(values) if n else None
    sd = statistics.stdev(values) if n >= 2 else None
    cv = (sd / mean * 100.0) if sd is not None and mean else None
    return n, mean, sd, cv


def grade_group(rows, *, cv_max, min_n) -> dict:
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
    planner = {'both': 0, 'nearest': 0, 'up': 0, 'mismatch': 0, '': 0}
    for r in rows:
        planner[r['planner'] if r['planner'] in planner else ''] += 1

    graded = n >= min_n
    verdicts = {}
    if graded:
        verdicts['C2_precision'] = cv is not None and cv <= cv_max
        verdicts['C3_planner'] = planner['mismatch'] == 0 and (n - planner['']) > 0
        if shortfall is not None and q:
            verdicts['C4_trueness'] = abs(shortfall) <= q / 2
    return {
        'topology': rows[0]['topology'],
        'cage_id': rows[0]['cage_id'],
        'dose_ml': target,
        'n': n,
        'graded': graded,
        'mean_ml': mean,
        'sd_ml': sd,
        'cv_pct': cv,
        'q_ml': q,
        'mean_expected_ml': mean_expected,
        'shortfall_ml': shortfall,
        'bias_vs_target_pct': bias_pct,
        'planner': {k: v for k, v in planner.items() if v},
        'verdicts': verdicts,
    }


def grade_equivalence(pooled, *, reference, equivalence_pct, min_n) -> list:
    """Per dose: each non-reference topology against the reference."""
    results = []
    by_dose = defaultdict(dict)
    for group in pooled:
        by_dose[dose_key(group['dose_ml'])][group['topology']] = group
    for dose, per_topology in sorted(by_dose.items()):
        ref = per_topology.get(reference)
        for topology, group in sorted(per_topology.items()):
            if topology == reference:
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
                and group['n'] >= min_n
                and ref['sd_ml'] is not None
                and group['sd_ml'] is not None
                and group['dose_ml']
            ):
                factor = uvl_factor(group['n'])
                uvl = ref['sd_ml'] * factor
                mean_diff = group['mean_ml'] - ref['mean_ml']
                allowed = group['dose_ml'] * equivalence_pct / 100.0
                entry.update(
                    {
                        'graded': True,
                        'sd_ml': group['sd_ml'],
                        'sd_reference_ml': ref['sd_ml'],
                        'uvl_factor': factor,
                        'uvl_ml': uvl,
                        'mean_diff_ml': mean_diff,
                        'mean_diff_allowed_ml': allowed,
                        'verdicts': {
                            'precision_vs_reference': group['sd_ml'] <= uvl,
                            'mean_vs_reference': abs(mean_diff) <= allowed,
                        },
                    }
                )
            results.append(entry)
    return results


def compare(rows, *, reference, cv_max, equivalence_pct, min_n) -> dict:
    groups = defaultdict(list)
    pooled = defaultdict(list)
    for r in rows:
        groups[(r['topology'], str(r['cage_id']), dose_key(r['target_ml']))].append(r)
        pooled[(r['topology'], dose_key(r['target_ml']))].append(r)
    detail = [grade_group(groups[k], cv_max=cv_max, min_n=min_n) for k in sorted(groups)]
    summary = []
    for key in sorted(pooled):
        group = grade_group(pooled[key], cv_max=cv_max, min_n=min_n)
        group['cage_id'] = 'all'
        summary.append(group)
    equivalence = grade_equivalence(
        summary, reference=reference, equivalence_pct=equivalence_pct, min_n=min_n
    )
    failed, graded = [], 0
    for group in detail + summary:
        for name, ok in group['verdicts'].items():
            graded += 1
            if not ok:
                failed.append(
                    f"{group['topology']} cage {group['cage_id']} "
                    f"{dose_key(group['dose_ml'])} mL: {name}"
                )
    for entry in equivalence:
        for name, ok in entry.get('verdicts', {}).items():
            graded += 1
            if not ok:
                failed.append(
                    f"{entry['topology']} vs {reference} at "
                    f"{dose_key(entry['dose_ml'])} mL: {name}"
                )
    return {
        'rows': len(rows),
        'reference': reference,
        'cv_max_pct': cv_max,
        'equivalence_pct': equivalence_pct,
        'min_n': min_n,
        'by_cage': detail,
        'pooled': summary,
        'equivalence': equivalence,
        'graded': graded,
        'failed': failed,
        # "Passed" needs something to have been graded: a file of three
        # readings must not come back as a clean bill of health.
        'passed': graded > 0 and not failed,
    }


# --- printing ------------------------------------------------------------------


def _fmt(value, digits=4):
    if value is None:
        return '-'
    return f"{value:.{digits}f}"


def _mark(verdicts, name):
    if name not in verdicts:
        return '  '
    return 'ok' if verdicts[name] else 'FAIL'


def say(line: str) -> None:
    print(line, flush=True)


def print_report(report) -> None:
    say(
        f"{report['rows']} weighed deliveries; reference topology {report['reference']}; "
        f"CV cap {report['cv_max_pct']:g} %; equivalence {report['equivalence_pct']:g} % of dose; "
        f"groups graded from n = {report['min_n']}"
    )
    for title, groups in (
        ("Per cage", report['by_cage']),
        ("Pooled per topology", report['pooled']),
    ):
        say("")
        say(title)
        say(
            f"{'topology':16} {'cage':>4} {'dose':>6} {'n':>3} {'mean':>7} {'sd':>7} {'cv%':>5} "
            f"{'q':>8} {'expect':>7} {'short':>8} {'bias%':>6} {'planner':22} {'C2':4} {'C3':4} {'C4':4}"
        )
        for g in groups:
            planner = ' '.join(f"{k or 'none'}={v}" for k, v in sorted(g['planner'].items()))
            v = g['verdicts']
            say(
                f"{g['topology']:16} {str(g['cage_id']):>4} {dose_key(g['dose_ml']):>6} {g['n']:>3} "
                f"{_fmt(g['mean_ml']):>7} {_fmt(g['sd_ml']):>7} {_fmt(g['cv_pct'], 1):>5} "
                f"{_fmt(g['q_ml'], 6):>8} {_fmt(g['mean_expected_ml']):>7} "
                f"{_fmt(g['shortfall_ml']):>8} {_fmt(g['bias_vs_target_pct'], 1):>6} "
                f"{planner:22} {_mark(v, 'C2_precision'):4} {_mark(v, 'C3_planner'):4} "
                f"{_mark(v, 'C4_trueness'):4}"
                + ("" if g['graded'] else "  (not graded: n too small)")
            )
    say("")
    say("Equivalence to the reference, per dose")
    if not report['equivalence']:
        say("  no other topology to compare, or no reference rows")
    for e in report['equivalence']:
        if not e['graded']:
            say(
                f"  {e['topology']} at {dose_key(e['dose_ml'])} mL: not graded "
                f"(n = {e['n']}, reference n = {e['n_reference']}, need {report['min_n']} each)"
            )
            continue
        v = e['verdicts']
        say(
            f"  {e['topology']} at {dose_key(e['dose_ml'])} mL: "
            f"SD {_fmt(e['sd_ml'])} vs UVL {_fmt(e['uvl_ml'])} "
            f"(= {_fmt(e['sd_reference_ml'])} x {e['uvl_factor']:.3f}) "
            f"{_mark(v, 'precision_vs_reference')}; "
            f"mean diff {e['mean_diff_ml']:+.4f} mL vs +/-{_fmt(e['mean_diff_allowed_ml'])} "
            f"{_mark(v, 'mean_vs_reference')}"
        )
    say("")
    if report['passed']:
        say(f"RESULT: every graded criterion passed ({report['graded']} graded)")
    elif not report['graded']:
        say(f"RESULT: nothing graded; every group needs at least {report['min_n']} readings")
    else:
        say("RESULT: FAILED")
        for line in report['failed']:
            say(f"  - {line}")


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument('csv', nargs='+', help="gravimetric_checks.csv file(s)")
    parser.add_argument(
        '--reference',
        default=DEFAULT_REFERENCE,
        help=f"topology the others are compared to (default {DEFAULT_REFERENCE})",
    )
    parser.add_argument('--cv-max', type=float, default=5.0, help="C2 cap in %% (default 5)")
    parser.add_argument(
        '--equivalence-pct',
        type=float,
        default=2.5,
        help="allowed mean difference vs the reference, %% of dose (default 2.5)",
    )
    parser.add_argument(
        '--min-n',
        type=int,
        default=10,
        help="rows a group needs to be graded (default 10, per ISO 8655-6)",
    )
    parser.add_argument('--json', help="also write the full report to this file")
    args = parser.parse_args(argv)
    if args.min_n < 2:
        print("ERROR: --min-n must be at least 2 (an SD needs two rows)", file=sys.stderr)
        return 2
    try:
        rows = load_rows(args.csv)
    except OSError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2
    if not rows:
        print("ERROR: no weighed deliveries in the given file(s)", file=sys.stderr)
        return 2
    report = compare(
        rows,
        reference=args.reference,
        cv_max=args.cv_max,
        equivalence_pct=args.equivalence_pct,
        min_n=args.min_n,
    )
    print_report(report)
    if args.json:
        with open(args.json, 'w', encoding='utf-8') as handle:
            json.dump(report, handle, indent=2)
        print(f"report written to {args.json}", flush=True)
    return 0 if report['passed'] else 1


if __name__ == '__main__':
    sys.exit(main())
