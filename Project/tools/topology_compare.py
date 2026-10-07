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
compared with the reference's:

    precision      s2_topology / s2_reference <= F(1 - alpha/k; df_topology, df_reference)

where s2 is the pooled within-cage variance of each row's deviation from
its own plan (weighed - pulses x mL/pulse), so neither cages with different
mL/pulse nor a cage recalibrated between rows inflate it, and the bound is a
one-sided F test at a family-wise alpha (--alpha, 5 %) over the k doses
compared (Bonferroni). C2's SD is taken the same way. A group whose rows lack
a plan falls back to the spread of the weighed volumes.
A rig exactly as precise as the reference passes it 95 % of the time. At
ten rows a side and one dose the bound is 1.78 x the reference SD; at four
doses, about 2.2 x. C2's absolute 5 % cap still applies on top.

The difference between the rigs' mean weighed volumes and between their
shortfalls is reported for information, not graded: each rig's trueness is
judged against its own pulses x mL/pulse (C4), because the two rigs' pulse
sizes and the manifold's needle differ by design.

    python3 tools/topology_compare.py manifold.csv independent.csv --policy nearest
    python3 tools/topology_compare.py c7.csv --reference none --since 2026-10-05 --until 2026-10-05

Exit status: 0 when every graded criterion passed, 1 when one failed or the
comparison is INCOMPLETE, 2 on a usage or input error. The comparison is
incomplete when the reference has no gradable rows (pass --reference none
to grade one rig alone), when no other topology has any (nothing was
compared with the reference), or when a dose either rig ran has no cage with
--min-n rows on the other side. Groups with fewer than --min-n rows are
listed but not graded, and a report with nothing graded is not a pass.
Rows that did not complete, staggered chunks, and rows without a recorded
dose are counted and left out.
"""

from __future__ import annotations

import argparse
import csv
import functools
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
DEFAULT_ALPHA = 0.05


# --- the F distribution (stdlib only) --------------------------------------------


def _betacf(a: float, b: float, x: float) -> float:
    """Continued fraction for the incomplete beta function (modified Lentz)."""
    tiny, eps = 1e-300, 3e-15
    qab, qap, qam = a + b, a + 1.0, a - 1.0
    c, d = 1.0, 1.0 - qab * x / qap
    d = 1.0 / (d if abs(d) > tiny else tiny)
    h = d
    for m in range(1, 400):
        m2 = 2 * m
        aa = m * (b - m) * x / ((qam + m2) * (a + m2))
        d = 1.0 + aa * d
        d = 1.0 / (d if abs(d) > tiny else tiny)
        c = 1.0 + aa / c
        c = c if abs(c) > tiny else tiny
        h *= d * c
        aa = -(a + m) * (qab + m) * x / ((a + m2) * (qap + m2))
        d = 1.0 + aa * d
        d = 1.0 / (d if abs(d) > tiny else tiny)
        c = 1.0 + aa / c
        c = c if abs(c) > tiny else tiny
        delta = d * c
        h *= delta
        if abs(delta - 1.0) < eps:
            break
    return h


def _betai(a: float, b: float, x: float) -> float:
    """Regularized incomplete beta function I_x(a, b)."""
    if x <= 0.0:
        return 0.0
    if x >= 1.0:
        return 1.0
    log_front = (
        math.lgamma(a + b) - math.lgamma(a) - math.lgamma(b) + a * math.log(x) + b * math.log1p(-x)
    )
    front = math.exp(log_front)
    if x < (a + 1.0) / (a + b + 2.0):
        return front * _betacf(a, b, x) / a
    return 1.0 - front * _betacf(b, a, 1.0 - x) / b


def f_cdf(f: float, d1: float, d2: float) -> float:
    """P(F <= f) for the F distribution with (d1, d2) degrees of freedom."""
    if f <= 0.0:
        return 0.0
    return _betai(d1 / 2.0, d2 / 2.0, d1 * f / (d1 * f + d2))


@functools.lru_cache(maxsize=None)
def f_quantile(p: float, d1: float, d2: float) -> float:
    """The p-quantile of F(d1, d2), by bisection on f_cdf."""
    if not 0.0 < p < 1.0:
        raise ValueError("p must be strictly between 0 and 1")
    lo, hi = 0.0, 1.0
    while f_cdf(hi, d1, d2) < p:
        hi *= 2.0
    for _ in range(200):
        mid = (lo + hi) / 2.0
        if f_cdf(mid, d1, d2) < p:
            lo = mid
        else:
            hi = mid
    return (lo + hi) / 2.0


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
    """Summary and C2/C3/C4 verdicts for one (topology, cage, dose) group.

    The SD is repeatability: the spread of each row's deviation from its own
    plan (pulses x mL/pulse). With one plan in the group that is exactly
    the spread of the weighed volumes; when the cage was recalibrated
    between rows, or a retry fired fewer pulses, the step between plans is
    not counted as noise. Rows without a plan fall back to the weighed
    spread.
    """
    measured = [r['measured_ml'] for r in rows]
    n, mean, sd, cv = _stats(measured)
    expected = [r['expected_ml'] for r in rows if r['expected_ml'] is not None]
    sd_basis = 'weighed'
    if n >= 2 and len(expected) == n:
        sd = statistics.stdev(m - e for m, e in zip(measured, expected))
        cv = (sd / mean * 100.0) if mean else None
        sd_basis = 'plan'
    plans = len({round(e, 6) for e in expected})
    qs = [r['q'] for r in rows if r['q']]
    q = statistics.median(qs) if qs else None
    mean_expected = statistics.fmean(expected) if expected else None
    shortfall = (mean - mean_expected) if mean is not None and mean_expected is not None else None
    target = rows[0]['target_ml']
    bias_pct = ((mean - target) / target * 100.0) if mean is not None and target else None
    verdict_counts = defaultdict(int)
    for r in rows:
        verdict_counts[r['planner'] or 'none'] += 1
    policy_counts = defaultdict(int)
    for r in rows:
        policy_counts[r['dose_rounding'] or 'not recorded'] += 1
    wrong_policy = sum(
        1 for r in rows if policy and r['dose_rounding'] and r['dose_rounding'] != policy
    )
    unjudged = verdict_counts.get('none', 0)
    mismatches = verdict_counts.get('mismatch', 0)

    graded = n >= min_n
    verdicts, why = {}, {}
    if graded:
        verdicts['C3_planner'] = mismatches == 0 and wrong_policy == 0 and unjudged < n
        if not verdicts['C3_planner']:
            reasons = []
            if mismatches:
                reasons.append(f"{mismatches} row(s) fired the wrong pulse count for the dose")
            if wrong_policy:
                used = ', '.join(p for p in sorted(policy_counts) if p != policy)
                reasons.append(f"{wrong_policy} row(s) rounded '{used}', '{policy}' required")
            if unjudged >= n:
                reasons.append("no row could be judged")
            why['C3_planner'] = '; '.join(reasons)
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
        'sd_basis': sd_basis,
        'plans': plans,
        'cv_pct': cv,
        'q_ml': q,
        'mean_expected_ml': mean_expected,
        'shortfall_ml': shortfall,
        'bias_vs_dose_pct': bias_pct,
        'planner': dict(sorted(verdict_counts.items())),
        'policies': dict(sorted(policy_counts.items())),
        'rows_with_other_policy': wrong_policy,
        'verdicts': verdicts,
        'why': why,
    }


def pooled_within_cage(groups):
    """(pooled variance, degrees of freedom, mean, mean shortfall) over cage groups.

    The pooled within-cage variance, sum((n_i - 1) s_i^2) / sum(n_i - 1),
    measures repeatability without the spread between cages whose plans
    differ (each cage has its own mL/pulse); each s_i is already taken
    about the rows' own plans (see grade_group).
    """
    df = sum(g['n'] - 1 for g in groups)
    variance = sum((g['n'] - 1) * g['sd_ml'] ** 2 for g in groups) / df
    total = sum(g['n'] for g in groups)
    mean = sum(g['n'] * g['mean_ml'] for g in groups) / total
    shortfalls = [(g['n'], g['shortfall_ml']) for g in groups if g['shortfall_ml'] is not None]
    shortfall = (
        sum(n * s for n, s in shortfalls) / sum(n for n, _ in shortfalls) if shortfalls else None
    )
    return variance, df, mean, shortfall


def grade_precision(detail, *, reference, min_n, alpha) -> list:
    """Each other topology's pooled within-cage precision against the reference's.

    Every dose either side ran is compared; a dose with no cage of min_n
    rows on either side is an INCOMPLETE entry, never a skip.
    """
    usable = defaultdict(list)  # (topology, dose) -> cage groups with n >= min_n
    doses = defaultdict(set)  # topology -> doses it ran at all
    for group in detail:
        key = dose_key(group['dose_ml'])
        doses[group['topology']].add(key)
        if group['n'] >= min_n and group['sd_ml'] is not None:
            usable[(group['topology'], key)].append(group)
    results = []
    for topology in sorted(t for t in doses if t != reference):
        compared = sorted(doses[topology] | doses.get(reference, set()))
        k = len(compared)
        for key in compared:
            ours, theirs = usable.get((topology, key)), usable.get((reference, key))
            entry = {
                'dose_ml': float(key) if key != '?' else None,
                'topology': topology,
                'reference': reference,
                'graded': False,
                'doses_compared': k,
            }
            if not ours or not theirs:
                short = []
                if not ours:
                    short.append(f"{topology} has no cage with {min_n} rows")
                if not theirs:
                    short.append(f"{reference} has no cage with {min_n} rows")
                entry['incomplete'] = '; '.join(short)
                results.append(entry)
                continue
            var_t, df_t, mean_t, short_t = pooled_within_cage(ours)
            var_r, df_r, mean_r, short_r = pooled_within_cage(theirs)
            f_crit = f_quantile(1.0 - alpha / k, df_t, df_r)
            entry.update(
                {
                    'graded': True,
                    'sd_ml': math.sqrt(var_t),
                    'sd_reference_ml': math.sqrt(var_r),
                    'df': df_t,
                    'df_reference': df_r,
                    'alpha_per_dose': alpha / k,
                    'bound_factor': math.sqrt(f_crit),
                    'ratio': math.sqrt(var_t / var_r) if var_r > 0 else math.inf,
                    'mean_diff_ml': mean_t - mean_r,
                    'shortfall_diff_ml': (
                        short_t - short_r if short_t is not None and short_r is not None else None
                    ),
                    'verdicts': {'precision_vs_reference': var_t <= var_r * f_crit},
                }
            )
            results.append(entry)
    return results


def compare(rows, *, reference, cv_max, min_n, policy=None, alpha=DEFAULT_ALPHA, excluded=None):
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
            is_reference=(reference is not None and topology == reference),
        )

    detail = [grade(groups[k]) for k in sorted(groups)]
    summary = []
    for key in sorted(pooled):
        group = grade(pooled[key])
        group['cage_id'] = 'all'
        summary.append(group)

    topologies = {g['topology'] for g in detail}
    others = sorted(t for t in topologies if t != reference)
    reference_present = reference is not None and reference in topologies
    precision = []
    incomplete = []
    if reference is not None:
        if not others:
            # Only the baseline rig's rows: C3 alone would read as a pass
            # although no rig was compared with it.
            incomplete.append(
                f"no gradable rows from any topology other than the reference {reference}; "
                "nothing was compared with it (grade one rig alone with --reference none)"
            )
        elif not reference_present:
            incomplete.append(
                f"no gradable rows from the reference topology {reference}; the comparison "
                "between rigs cannot be made (grade one rig alone with --reference none)"
            )
        else:
            precision = grade_precision(detail, reference=reference, min_n=min_n, alpha=alpha)

    failed, graded = [], 0
    for group in detail + summary:
        for name, ok in group['verdicts'].items():
            graded += 1
            if not ok:
                line = (
                    f"{group['topology']} cage {group['cage_id']} "
                    f"{dose_key(group['dose_ml'])} mL: {name}"
                )
                if group['why'].get(name):
                    line += f" ({group['why'][name]})"
                failed.append(line)
    for entry in precision:
        if not entry['graded']:
            incomplete.append(
                f"{entry['topology']} at {dose_key(entry['dose_ml'])} mL: no precision "
                f"comparison ({entry['incomplete']})"
            )
            continue
        for name, ok in entry['verdicts'].items():
            graded += 1
            if not ok:
                failed.append(
                    f"{entry['topology']} vs {reference} at {dose_key(entry['dose_ml'])} mL: "
                    f"{name} (SD ratio {entry['ratio']:.2f} > bound {entry['bound_factor']:.2f})"
                )
    return {
        'rows': len(rows),
        'excluded': excluded or {},
        'reference': reference,
        'reference_present': reference_present,
        'policy': policy,
        'alpha': alpha,
        'cv_max_pct': cv_max,
        'min_n': min_n,
        'by_cage': detail,
        'pooled': summary,
        'precision': precision,
        'graded': graded,
        'failed': failed,
        'incomplete': incomplete,
        # "Passed" needs something graded and nothing missing: a file of three
        # readings, a dose one rig never ran, or a reference with no gradable
        # rows is not a clean bill.
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


def _planner_text(group) -> str:
    verdicts = ' '.join(f"{k}={v}" for k, v in group['planner'].items())
    policies = '/'.join(p for p in group['policies'] if p != 'not recorded')
    return f"{verdicts} [{policies}]" if policies else verdicts


def print_report(report) -> None:
    reference = report['reference'] or 'none (one rig at a time)'
    say(
        f"{report['rows']} weighed deliveries graded; reference topology {reference}; "
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
            f"{'q':>8} {'plan':>7} {'short':>8} {'bias%':>6} {'planner':26} {'C2':4} {'C3':4} {'C4':4}"
        )
        for g in groups:
            say(
                f"{g['topology']:16} {str(g['cage_id']):>4} {dose_key(g['dose_ml']):>6} {g['n']:>3} "
                f"{_fmt(g['mean_ml']):>7} {_fmt(g['sd_ml']):>7} {_fmt(g['cv_pct'], 1):>5} "
                f"{_fmt(g['q_ml'], 6):>8} {_fmt(g['mean_expected_ml']):>7} "
                f"{_fmt(g['shortfall_ml']):>8} {_fmt(g['bias_vs_dose_pct'], 1):>6} "
                f"{_planner_text(g):26} {_mark(g, 'C2_precision'):4} {_mark(g, 'C3_planner'):4} "
                f"{_mark(g, 'C4_trueness'):4}"
                + ("" if g['graded'] else "  (not graded: n too small)")
                + (f"  ({g['plans']} plans: sd about each row's own)" if g['plans'] > 1 else "")
            )
    say("")
    if report['reference'] is None:
        say("Precision between rigs: not graded (--reference none grades each rig on its own)")
    else:
        say(
            f"Precision against the reference ({report['reference']}), pooled within cages; "
            f"one-sided F test, family-wise alpha {report['alpha']:g}"
        )
    for e in report['precision']:
        if not e['graded']:
            say(
                f"  {e['topology']} at {dose_key(e['dose_ml'])} mL: INCOMPLETE ({e['incomplete']})"
            )
            continue
        ok = e['verdicts']['precision_vs_reference']
        diff = "-" if e['shortfall_diff_ml'] is None else f"{e['shortfall_diff_ml']:+.4f} mL"
        say(
            f"  {e['topology']} at {dose_key(e['dose_ml'])} mL: SD {_fmt(e['sd_ml'])} "
            f"vs {_fmt(e['sd_reference_ml'])} (ratio {e['ratio']:.2f}, bound "
            f"{e['bound_factor']:.2f} at df {e['df']}/{e['df_reference']}) "
            f"{'ok' if ok else 'FAIL'}; for information: mean diff {e['mean_diff_ml']:+.4f} mL, "
            f"shortfall diff {diff}"
        )
    say("")
    if report['passed']:
        say(f"RESULT: every graded criterion passed ({report['graded']} graded)")
    elif not report['graded'] and not report['incomplete']:
        say(f"RESULT: nothing graded; every group needs at least {report['min_n']} readings")
    else:
        say("RESULT: FAILED" if report['failed'] else "RESULT: INCOMPLETE")
        for line in report['failed'] + report['incomplete']:
            say(f"  - {line}")


def _reference_arg(text: str):
    return None if text.strip().lower() == 'none' else text.strip()


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument('csv', nargs='+', help="gravimetric_checks.csv file(s)")
    parser.add_argument(
        '--reference',
        type=_reference_arg,
        default=DEFAULT_REFERENCE,
        help=f"topology the others are compared to (default {DEFAULT_REFERENCE}); "
        "'none' grades each rig on its own (C7, C8)",
    )
    parser.add_argument(
        '--policy',
        choices=POLICIES,
        help="require every graded row to have been rounded with this policy (C3)",
    )
    parser.add_argument('--cv-max', type=float, default=5.0, help="C2 cap in %% (default 5)")
    parser.add_argument(
        '--alpha',
        type=float,
        default=DEFAULT_ALPHA,
        help="family-wise alpha of the precision comparison (default 0.05)",
    )
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
    if not 0.0 < args.alpha < 1.0:
        print("ERROR: --alpha must be between 0 and 1", file=sys.stderr)
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
        alpha=args.alpha,
        excluded=excluded,
    )
    print_report(report)
    if args.json:
        with open(args.json, 'w', encoding='utf-8') as handle:
            json.dump(report, handle, indent=2, default=str)
        print(f"report written to {args.json}", flush=True)
    return 0 if report['passed'] else 1


if __name__ == '__main__':
    sys.exit(main())
