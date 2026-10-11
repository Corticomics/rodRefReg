"""What RRR says about an animal's last schedule run.

Animal.last_run is the animal's latest schedule run that started delivering
(models/schedule_runs_repo.py), or None. last_run_cell() turns it into the
Animals tab's "Last schedule delivered amount" cell: its text, its tooltip
and whether it is red. outcome_word(), remaining_ml() and
delivery_log_command() serve anything else that describes a run, such as the
animal export, so every screen gives the same word, the same remainder and
the same command.

Red follows the outcome the run recorded, never a comparison of delivered
with scheduled: whole-pulse rounding makes a completed run differ from its
schedule (docs/STOP_AND_PARTIAL_DELIVERY.md §5 and §8). An amount that was
not recorded shows as "?", never as 0 or as the planned amount.

Qt-free, so the words can be tested on their own.
"""

from __future__ import annotations

# The cell of an animal that has no recorded schedule run.
NO_RUN_TEXT = "—"

# Run never resumes a schedule. A staggered schedule starts over and gives
# every animal its full amount again; an instant one skips every delivery time
# that has passed (RelayWorker.run_instant_cycle).
STARTS_OVER_STAGGERED = (
    "Running this schedule again starts it over and delivers the full amount again."
)
SKIPS_PASSED_INSTANT = (
    "Running this schedule again skips every delivery time that has passed; it does not "
    "give those deliveries again."
)

# A smaller remainder shows as 0.000 mL, so no new schedule is offered for it.
_SMALLEST_REMAINDER_ML = 0.0005


def _ml(volume):
    """A volume to three decimals, or "?" when it was not recorded."""
    return "?" if volume is None else f"{volume:.3f}"


def outcome_word(outcome):
    """How the run stands for the animal, in one word: Running, Completed,
    Stopped, Incomplete or Interrupted. The cell starts with it, except a
    completed one, which shows only the amount. An outcome that a newer
    release wrote, read after a revert, shows by name; "" when there is no
    run."""
    return str(outcome).capitalize() if outcome else ""


def remaining_ml(last_run):
    """What the run did not deliver: scheduled minus delivered, never below 0.

    None when the delivered amount was not recorded. It starts from the
    scheduled amount, the figure the operator typed, not the planned one: a
    new schedule for the rest is rounded again at the cage's calibration,
    which gives back the pulses that did not fire.
    """
    requested = last_run.get('requested_ml')
    delivered = last_run.get('delivered_ml')
    if requested is None or delivered is None:
        return None
    return max(0.0, requested - delivered)


def delivery_log_command(started_at, relay_unit_id):
    """The command, typed in a terminal on the Pi, that totals what a cage
    received per day from the run's day on (tools/gravimetric_check.py daily).
    Without a cage it lists every cage."""
    command = (
        "cd ~/rrr/current/Project && ~/rrr/shared/venv/bin/python3 "
        "tools/gravimetric_check.py daily"
    )
    day = (started_at or "")[:10]
    if day:
        command += f" --since {day}"
    if relay_unit_id is not None:
        command += f" --cage {relay_unit_id}"
    return command


def _delivery_log_lines(last_run):
    """Where to read what the cage got, when the run did not record it."""
    cage = last_run.get('relay_unit_id')
    where = "each cage" if cage is None else f"cage {cage}"
    return [
        f"To see what {where} received, run this in a terminal on the Pi:",
        delivery_log_command(last_run.get('started_at'), cage),
    ]


def _next_steps(last_run):
    """How to give the rest of a run that ended short, for its delivery mode."""
    remaining = remaining_ml(last_run)
    owed = remaining is not None and remaining >= _SMALLEST_REMAINDER_ML
    if last_run.get('delivery_mode') == 'instant':
        # A run started late counts the deliveries whose times had passed as
        # not delivered, even when an earlier run gave them: the delivery log
        # tells, before a new schedule gives them twice.
        lines = [SKIPS_PASSED_INSTANT]
        if owed:
            lines += [
                f"{remaining:.3f} mL was not delivered in this run. If it started after some "
                "delivery times had passed, an earlier run may already have given them. "
                "Check the delivery log first, then create a new schedule for what is "
                "missing:",
                delivery_log_command(last_run.get('started_at'), last_run.get('relay_unit_id')),
            ]
        return lines
    lines = [STARTS_OVER_STAGGERED]
    if owed:
        lines.append(
            f"To deliver only the remaining {remaining:.3f} mL, create a new schedule for "
            "that amount."
        )
    return lines


def last_run_cell(last_run, when):
    """The "Last schedule delivered amount" cell: ``(text, tooltip, red)``.

    ``last_run`` is Animal.last_run, or None. ``when`` turns a stored time
    into words, as AnimalsTab._when does: "2 hours ago (2026-10-09 07:00)".
    """
    if not last_run:
        return NO_RUN_TEXT, "No schedule run has been recorded for this animal yet.", False
    outcome = last_run.get('outcome')
    name = last_run.get('schedule_name')
    requested = _ml(last_run.get('requested_ml'))
    planned = _ml(last_run.get('planned_ml'))
    delivered = last_run.get('delivered_ml')
    planned_line = f"Planned: {planned} mL"
    if planned != requested:
        planned_line += " (rounded to whole valve pulses at this cage's calibration)"
    amounts = [f"Scheduled: {requested} mL", planned_line]

    if outcome == 'running':
        lines = [f'Schedule "{name}" is running. It started {when(last_run.get("started_at"))}.']
        lines += amounts + ["The delivered amount appears here when the schedule ends."]
        return f"{outcome_word(outcome)} · {planned} mL planned", "\n".join(lines), False

    red = outcome != 'completed'
    if not red:
        text = f"{_ml(delivered)} mL"
        lines = [f'Schedule "{name}" completed {when(last_run.get("ended_at"))}.']
    else:
        # Stopped, incomplete, interrupted, or an outcome that a newer release
        # wrote before a revert: red, which errs towards a check.
        text = f"{outcome_word(outcome)} · {_ml(delivered)} / {planned} mL"
        if outcome == 'interrupted':
            # Dated by its start: its end is when the next start found it open.
            lines = [
                f'RRR closed unexpectedly or lost power while schedule "{name}" was running.',
                f'It started {when(last_run.get("started_at"))}.',
            ]
        elif outcome == 'stopped':
            lines = [
                f'Schedule "{name}" was stopped {when(last_run.get("ended_at"))}, before this '
                "animal received its full amount."
            ]
        else:
            lines = [
                f'Schedule "{name}" ended {when(last_run.get("ended_at"))} without this '
                "animal's full amount."
            ]
            if outcome == 'incomplete':
                lines.append(
                    "Some deliveries failed, or their times had already passed when it was "
                    "started."
                )
    lines += amounts
    if delivered is None:
        lines.append("Delivered: not recorded.")
        lines += _delivery_log_lines(last_run)
    else:
        lines.append(f"Delivered: {_ml(delivered)} mL")
        if red:
            lines += _next_steps(last_run)
    return text, "\n".join(lines), red
