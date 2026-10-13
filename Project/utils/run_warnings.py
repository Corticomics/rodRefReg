"""What Run says before a start that will not go as scheduled.

An instant schedule some of whose delivery times have passed: Run skips those
deliveries (the worker never gives a delivery whose time has passed), while
the run's record plans the whole schedule. So the run delivers less than it
records as scheduled, and the Animals tab shows it in red as incomplete for
the animals that lose a delivery (docs/STOP_AND_PARTIAL_DELIVERY.md §9).
RunStopSection asks before it starts; this module only words the question.

Qt-free, so the wording can be tested on its own, as utils.calibration_gate.
"""

from __future__ import annotations

PASSED_TITLE = "Some Deliveries Passed"
START_RUN = "Start Run"

MAX_TIMES = 4  # delivery times listed for one animal
MAX_ANIMALS = 10  # animals listed in one dialog


def _times(moments, now):
    """Times of day when all are today; otherwise each one with its date."""
    fmt = '%H:%M' if all(m.date() == now.date() for m in moments) else '%Y-%m-%d %H:%M'
    return ', '.join(m.strftime(fmt) for m in moments)


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


def passed_deliveries_message(schedule_name, deliveries, labels, now):
    """The question Run asks when some of an instant schedule's times have passed.

    ``deliveries`` is Schedule.instant_deliveries: every delivery, passed ones
    included, as {'animal_id', 'datetime', 'volume', 'relay_unit_id'}.
    ``labels`` maps animal_id to its lab ID. A delivery has passed when its
    time is before ``now``, as Run judges it. Volumes are the scheduled ones.
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
    return '\n\n'.join(
        [
            f'{passed} of {len(deliveries)} deliveries of "{schedule_name}" '
            f"{'has' if passed == 1 else 'have'} already passed. This run skips "
            f"{'it' if passed == 1 else 'them'}:\n" + _bulleted(lines),
            f"This run delivers {still:.3f} of the {scheduled:.3f} mL scheduled. For the "
            "animals above, the Animals tab will show this run in red as incomplete.",
            f"Start the {ahead} {'delivery' if ahead == 1 else 'deliveries'} still ahead?",
        ]
    )
