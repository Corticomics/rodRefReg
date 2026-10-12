"""What Run says before a start that will not go as scheduled.

An instant schedule some of whose delivery times have passed: Run skips those
deliveries (the worker never gives a delivery whose time has passed), while
the run's record plans the whole schedule. So the run delivers less than it
records as scheduled, and the Animals tab shows it in red as incomplete for
the animals that lose a delivery (docs/STOP_AND_PARTIAL_DELIVERY.md §9).

A schedule that ran before and gave some water: Run does not resume a
schedule, it starts it over, so every animal gets its full amount again on
top of what it got. When that last run ended early (stopped, ended short, or
RRR closed during it), Run lists what each animal got and what is missing;
when it completed, Run lists what each animal got.

RunStopSection asks before it starts, at most one question per Run; this
module only words the questions. Qt-free, so the wording can be tested on its
own, as utils.calibration_gate.
"""

from __future__ import annotations

from datetime import datetime

from utils.last_run_text import delivery_log_command, remaining_ml

PASSED_TITLE = "Some Deliveries Passed"
LAST_RUN_TITLE = "Last Run Ended Early"
COMPLETED_RUN_TITLE = "Last Run Completed"
START_RUN = "Start Run"
START_OVER = "Start Over"

# The outcomes (schedule_run_animals.outcome) of an animal whose run ended
# before it got its full amount. A run still 'running' when Run is pressed is
# one whose end was never recorded: no run can be in progress while Run holds
# the operation lock, and start-up marks a run that RRR's closing cut off
# 'interrupted'.
ENDED_EARLY = frozenset({'stopped', 'incomplete', 'interrupted', 'running'})

MAX_TIMES = 4  # delivery times listed for one animal
MAX_ANIMALS = 10  # animals listed in one dialog

# A smaller remainder shows as 0.000 mL, so it is not offered for a new
# schedule (the Animals tab's red cell does the same).
_SMALLEST_REMAINDER_ML = 0.0005


def _times(moments, now):
    """Times of day when all are today; otherwise each one with its date."""
    fmt = '%H:%M' if all(m.date() == now.date() for m in moments) else '%Y-%m-%d %H:%M'
    return ', '.join(m.strftime(fmt) for m in moments)


def _time(stored, now, dated=False):
    """A time the run history stored, as _times shows it, or always with its
    date when ``dated``; None when it was not recorded or cannot be read."""
    try:
        moment = datetime.fromisoformat(stored)
    except (TypeError, ValueError):
        return None
    return moment.strftime('%Y-%m-%d %H:%M') if dated else _times([moment], now)


def _label(lab_id, cage):
    """'M-12, cage 3'; the cage alone when the animal has no lab ID."""
    name = str(lab_id).strip() if lab_id is not None else ''
    if name and cage is not None:
        return f"{name}, cage {cage}"
    return name or f"cage {cage}"


def _passed_times(moments, now):
    """The first MAX_TIMES passed times of one animal, then 'and N more'."""
    moments = sorted(moments)
    shown = _times(moments[:MAX_TIMES], now)
    more = len(moments) - MAX_TIMES
    return f"{shown} and {more} more" if more > 0 else shown


def _bulleted(lines):
    """One bullet per animal, at most MAX_ANIMALS, then '...and N more animals'."""
    shown = [f"• {line}" for line in lines[:MAX_ANIMALS]]
    more = len(lines) - MAX_ANIMALS
    if more > 0:
        shown.append(f"...and {more} more {'animal' if more == 1 else 'animals'}")
    return '\n'.join(shown)


def _animal_line(label, animal, now):
    """What one animal loses. RRR creates one instant delivery per animal, so
    an animal whose time has passed gets nothing from this run. Only a
    schedule with several deliveries for one animal, which RRR cannot create
    today, can still have some of them ahead."""
    times = _passed_times(animal['passed'], now)
    scheduled = animal['scheduled']
    if not animal['ahead']:
        return f"{label}: {times} passed, nothing from this run ({scheduled:.3f} mL scheduled)"
    ahead = sum(animal['ahead'])
    return f"{label}: {times} passed; {ahead:.3f} of {scheduled:.3f} mL still to deliver"


def passed_deliveries_message(
    schedule_name, deliveries, labels, now, last_run=(), completed_run=()
):
    """The question Run asks when some of an instant schedule's times have passed.

    ``deliveries`` is Schedule.instant_deliveries: every delivery, passed ones
    included, as {'animal_id', 'datetime', 'volume', 'relay_unit_id'}.
    ``labels`` maps animal_id to its lab ID. A delivery has passed when its
    time is before ``now``, as Run judges it. Volumes are the scheduled ones.
    ``last_run`` holds last_run_lines() when the last run of this schedule
    ended early, ``completed_run`` completed_run_lines() when it completed:
    that run's paragraph goes before the question, and says that this run
    does not give the passed deliveries again.
    """
    animals = {}
    for d in deliveries:
        animal = animals.setdefault(
            d['animal_id'],
            {'cage': d.get('relay_unit_id'), 'passed': [], 'ahead': [], 'scheduled': 0.0},
        )
        volume = float(d['volume'])
        animal['scheduled'] += volume
        if d['datetime'] < now:
            animal['passed'].append(d['datetime'])
        else:
            animal['ahead'].append(volume)
    passed = sum(len(a['passed']) for a in animals.values())
    ahead = len(deliveries) - passed
    lines = [
        _animal_line(_label(labels.get(animal_id), a['cage']), a, now)
        for animal_id, a in animals.items()
        if a['passed']
    ]
    scheduled = sum(a['scheduled'] for a in animals.values())
    still = sum(sum(a['ahead']) for a in animals.values())
    paragraphs = [
        f'{passed} of {len(deliveries)} deliveries of "{schedule_name}" '
        f"{'has' if passed == 1 else 'have'} already passed. This run skips "
        f"{'it' if passed == 1 else 'them'}:\n" + _bulleted(lines),
        f"This run delivers {still:.3f} of the {scheduled:.3f} mL scheduled. For the "
        "animals above, the Animals tab will show this run in red as incomplete.",
    ]
    if last_run or completed_run:
        paragraphs += [
            _ended_early(schedule_name, last_run)
            if last_run
            else _completed(schedule_name, completed_run),
            "Passed deliveries are skipped, never repeated.",
        ]
    paragraphs.append(
        f"Start the {ahead} {'delivery' if ahead == 1 else 'deliveries'} still ahead?"
    )
    return '\n\n'.join(paragraphs)


# --- the last run of this schedule ---------------------------------------------------------------


def _outcome(run):
    """How the run ended for the animal: 'completed', or one of ENDED_EARLY.
    An outcome this release does not know (a newer release wrote it, read
    after a revert) counts as 'incomplete', as the Animals tab shows it red."""
    outcome = run.get('outcome')
    return outcome if outcome == 'completed' or outcome in ENDED_EARLY else 'incomplete'


def _runs(latest, animal_ids):
    """The latest runs of the schedule's animals, in the schedule's order.
    Ids are matched as numbers; one that is not a number is skipped, and an
    animal listed twice gets one line."""
    by_id = {}
    for key, run in (latest or {}).items():
        try:
            by_id[int(key)] = run
        except (TypeError, ValueError):
            continue
    runs = []
    for animal_id in animal_ids:
        try:
            run = by_id.pop(int(animal_id), None)
        except (TypeError, ValueError):
            continue
        if run:
            runs.append(run)
    return runs


def _line(run, now, dated, timed):
    """What one animal got in its latest run of this schedule, and how that run
    ended for it.

    ``dated`` gives each time on the line its date: the run is older than the
    schedule's last one. ``timed`` says when a completed run ended; a line in
    a run that ended early does not, as that end is when the run was stopped,
    not when this animal completed. None-safe: an amount or a time that was
    not recorded is said to be so, so one odd row does not lose the warning.
    """
    label = _label(run.get('lab_animal_id'), run.get('relay_unit_id'))
    planned = run.get('planned_ml')
    delivered = run.get('delivered_ml')
    of_plan = f" of the planned {planned:.3f} mL" if planned is not None else ""
    command = delivery_log_command(run.get('started_at'), run.get('relay_unit_id'))
    in_the_log = f"how much{of_plan} it delivered is in the delivery log: {command}"
    outcome = _outcome(run)
    if outcome in ('interrupted', 'running'):
        what = (
            "RRR closed during that run"
            if outcome == 'interrupted'
            else "the end of that run was not recorded"
        )
        started = _time(run.get('started_at'), now, dated)
        if started:
            what += f" (started {started})"
        return f"{label}: {what}; {in_the_log}"
    got = None
    if delivered is not None:
        got = f"{delivered:.3f}{of_plan}" if of_plan else f"{delivered:.3f} mL"
    ended = _time(run.get('ended_at'), now, dated)
    if outcome == 'completed':
        how = f"completed at {ended}" if timed and ended else "complete"
        return f"{label}: {got}, {how}" if got else f"{label}: {how} (amount not recorded)"
    how = "stopped" if outcome == 'stopped' else "ended short"
    if ended:
        how += f" at {ended}"
    if got is None:
        return f"{label}: {how}; {in_the_log}"
    line = f"{label}: {got}, {how}"
    remaining = remaining_ml(run)
    # Re-running an instant schedule skips its passed times, so its lines
    # give no remainder; the Animals tab sends the operator to the delivery
    # log first.
    if (
        run.get('delivery_mode') != 'instant'
        and remaining is not None
        and remaining >= _SMALLEST_REMAINDER_ML
    ):
        line += f"; remaining {remaining:.3f} of the {run['requested_ml']:.3f} mL scheduled"
    return line


def _lines(runs, now, timed):
    """One line per animal that got water: delivered above 0, or not recorded.
    One that got nothing is left out, since its full amount is what it needs.
    A line from a run older than the schedule's last one (an animal that was
    not in that run) carries its date."""
    newest = max((run['run_id'] for run in runs if run.get('run_id') is not None), default=None)
    lines = []
    for run in runs:
        delivered = run.get('delivered_ml')
        if delivered is not None and delivered <= 0:
            continue
        older = newest is not None and run.get('run_id') is not None and run['run_id'] < newest
        lines.append(_line(run, now, dated=older, timed=timed or older))
    return lines


def last_run_lines(latest, animal_ids, now):
    """One line per animal the last run of this schedule watered, if it ended early.

    ``latest`` maps animal_id to that animal's latest run of this schedule
    (DatabaseHandler.get_latest_runs_of_schedule): a later run of another
    schedule does not hide it. [] unless one of ``animal_ids`` ended early
    (ENDED_EARLY) and some water went out. Every animal that got water is
    listed, completed ones too: starting over gives each its full amount
    again.
    """
    runs = _runs(latest, animal_ids)
    if not any(_outcome(run) in ENDED_EARLY for run in runs):
        return []
    return _lines(runs, now, timed=False)


def completed_run_lines(latest, animal_ids, now):
    """One line per animal the last run of this schedule watered, if every one
    completed, saying when that run ended.

    The other half of last_run_lines, the owner's choice (design record §14,
    item 7): starting the schedule over gives each animal its full amount
    again, on top of what it got. [] when an animal ended early, or when
    there was no run or no water went out.
    """
    runs = _runs(latest, animal_ids)
    if any(_outcome(run) in ENDED_EARLY for run in runs):
        return []
    return _lines(runs, now, timed=True)


def _ended_early(schedule_name, lines):
    return (
        f'The last run of "{schedule_name}" ended early. These animals already got water '
        "in it:\n" + _bulleted(list(lines))
    )


def _completed(schedule_name, lines):
    return (
        f'The last run of "{schedule_name}" completed. These animals already got their '
        "full amount in it:\n" + _bulleted(list(lines))
    )


def window_note(scheduled_start, scheduled_end, now):
    """A staggered schedule whose start has passed: what is left of its window."""
    minutes = round((scheduled_end - now).total_seconds() / 60)
    return (
        f"The scheduled start time ({scheduled_start.strftime('%Y-%m-%d %H:%M')}) has "
        f"already passed: the full amount goes out in the {minutes} "
        f"{'minute' if minutes == 1 else 'minutes'} left until "
        f"{scheduled_end.strftime('%H:%M')}."
    )


def last_run_message(schedule_name, lines, window=None):
    """The question Run asks before it starts over a schedule whose last run
    ended early. ``window`` is window_note() when the start has passed."""
    paragraphs = [
        _ended_early(schedule_name, lines),
        "Run does not resume a schedule: it starts this one over, so the animals above get "
        "their full amount again, on top of what they already got. If the missing water has "
        "not been given since, press Cancel and create a new schedule for the remaining "
        "amount.",
    ]
    if window:
        paragraphs.append(window)
    paragraphs.append(f'Start "{schedule_name}" over?')
    return '\n\n'.join(paragraphs)


def completed_run_message(schedule_name, lines, window=None):
    """The question Run asks before it starts over a schedule whose last run
    completed. ``window`` is window_note() when the start has passed."""
    paragraphs = [
        _completed(schedule_name, lines),
        "Run starts this schedule over, so the animals above get their full amount again, "
        "on top of what they already got.",
    ]
    if window:
        paragraphs.append(window)
    paragraphs.append(f'Start "{schedule_name}" over?')
    return '\n\n'.join(paragraphs)


def start_over_question(schedule_name, last_run=(), completed_run=(), window=None):
    """``(title, text)`` of the question Run asks before it starts a schedule
    over: Last Run Ended Early for ``last_run`` (last_run_lines()), else Last
    Run Completed for ``completed_run`` (completed_run_lines())."""
    if last_run:
        return LAST_RUN_TITLE, last_run_message(schedule_name, last_run, window)
    return COMPLETED_RUN_TITLE, completed_run_message(schedule_name, completed_run, window)
