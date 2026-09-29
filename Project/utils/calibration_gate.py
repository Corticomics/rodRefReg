"""Whether a schedule may start: every cage it waters needs a usable calibration.

In solenoid pulse mode a dose is planned in whole pulses of the cage's
calibrated volume per pulse. A cage with no calibration falls back to an
empirical guess (about 0.026 mL per pulse against the production valve's
0.034, so roughly 30 % too much water). A calibration measured under the
other valve topology is off by the difference between the two rigs. The Run
path refuses such a start (RunStopSection._passes_calibration_gate), on the
GUI thread and before any worker exists. The delivery strategy keeps its
fallbacks only as a defence in depth.

Qt-free, so the rule can be tested on its own.
"""

from __future__ import annotations

import math
from typing import Iterable, List, NamedTuple

from utils.topology import calibration_is_stale, calibration_label, topology_from

UNCALIBRATED = 'uncalibrated'
STALE = 'stale'
UNUSABLE = 'unusable'


class CageProblem(NamedTuple):
    cage_id: object
    reason: str
    detail: str = ''


def gate_applies(settings) -> bool:
    """Only solenoid pulse delivery plans from valve calibrations.

    Pump mode times its triggers, and the legacy continuous mode times the
    valve from an expected flow rate; neither reads a calibration. The mode
    is normalised as RelayWorker._resolve_hardware_mode does.
    """
    settings = settings or {}
    mode = str(settings.get('hardware_mode') or 'solenoid').strip().lower()
    return mode == 'solenoid' and bool(settings.get('use_pulse_delivery', True))


def run_cage_ids(mode, relay_unit_assignments, future_instant_deliveries) -> set:
    """The cages a run will water.

    Staggered: every assignment. Instant: the cages of the deliveries still
    ahead, each taken from the delivery itself, since the worker skips the
    past ones and does not use the assignment map.
    """
    if str(mode).strip().lower() == 'instant':
        return {d.get('relay_unit_id') for d in (future_instant_deliveries or [])}
    return set((relay_unit_assignments or {}).values())


def _as_cage_id(value):
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _positive(value, cast) -> bool:
    try:
        number = cast(value)
    except (TypeError, ValueError, OverflowError):
        return False
    return math.isfinite(number) and number > 0


def _order(cage):
    number = _as_cage_id(cage)
    return (0, number, '') if number is not None else (1, 0, str(cage))


def calibration_problems(cage_ids: Iterable, calibrations, settings) -> List[CageProblem]:
    """Every cage in ``cage_ids`` without a calibration this run can use.

    ``calibrations`` is ``get_all_valve_calibrations()``: cage id to row.
    A cage passes when its row exists, has a positive, finite volume per
    pulse and pulse width, and was measured under the device's topology
    (an untagged, pre-v1.21.0 row counts as the shared manifold). The
    pulse width need not match the settings: a delivery replays the
    cage's own. An id that is not a number fails as uncalibrated.
    """
    if not gate_applies(settings):
        return []
    problems = []
    for raw in sorted(cage_ids, key=_order):
        cage = _as_cage_id(raw)
        row = calibrations.get(cage) if cage is not None else None
        if row is None:
            problems.append(CageProblem(raw, UNCALIBRATED))
        elif not (
            _positive(row.get('volume_per_pulse_ml'), float)
            and _positive(row.get('pulse_width_ms'), int)
        ):
            problems.append(CageProblem(cage, UNUSABLE))
        elif calibration_is_stale(row, settings):
            problems.append(CageProblem(cage, STALE, calibration_label(row)))
    return problems


def format_problems(problems, settings) -> str:
    """The refusal dialog's text: one line for each kind of problem found."""
    by_reason = {UNCALIBRATED: [], STALE: [], UNUSABLE: []}
    for problem in problems:
        by_reason[problem.reason].append(problem)
    lines = [
        f"This schedule was not started. {len(problems)} cage(s) it waters do not have "
        "a valve calibration RRR can use:",
        "",
    ]
    if by_reason[UNCALIBRATED]:
        cages = ', '.join(f"cage {p.cage_id}" for p in by_reason[UNCALIBRATED])
        lines.append(f"Not calibrated: {cages}")
    if by_reason[STALE]:
        cages = ', '.join(f"cage {p.cage_id} (measured on {p.detail})" for p in by_reason[STALE])
        lines.append(
            "Calibrated under the other valve topology (this device uses "
            f"{topology_from(settings)}): {cages}"
        )
    if by_reason[UNUSABLE]:
        cages = ', '.join(f"cage {p.cage_id}" for p in by_reason[UNUSABLE])
        lines.append(
            f"Calibration unusable (volume per pulse or pulse width missing or zero): {cages}"
        )
    lines += [
        "",
        "Without a calibration it can use, RRR would have to guess how much water each "
        "pulse gives, and these animals could get much more or less water than scheduled.",
        "",
        "Calibrate each cage listed in Settings > Calibration, then press Run again.",
    ]
    return '\n'.join(lines)
