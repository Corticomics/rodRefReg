"""The volume a schedule can be given: the schedule wizard's limits, in one place.

Every volume field of the schedule wizard (ui/schedule_wizard.py, whose Step 3
the Schedules hub's Edit dialog reuses) takes SCHEDULE_VOLUME_MIN_ML to
SCHEDULE_VOLUME_MAX_ML at SCHEDULE_VOLUME_DECIMALS decimals. Text that tells
the operator an amount to type there takes the limits from here too, so the
two cannot drift: the amount to schedule for the rest of a run
(utils.last_run_text, utils.run_warnings) is given by schedule_amount() and
checked with can_be_scheduled(), so the figure on screen is one the field
takes as it is typed.

Qt-free, so the words that use it can be tested on their own.
"""

from __future__ import annotations

from decimal import ROUND_HALF_UP, Decimal

SCHEDULE_VOLUME_DECIMALS = 2
SCHEDULE_VOLUME_MIN_ML = 0.1
SCHEDULE_VOLUME_MAX_ML = 50.0

_STEP = Decimal(1).scaleb(-SCHEDULE_VOLUME_DECIMALS)  # 0.01


def schedule_amount(volume_ml) -> Decimal:
    """``volume_ml`` at the wizard's decimals, an exact half rounding up:
    0.369 to 0.37, 0.365 to 0.37.

    It rounds the figure as written, Decimal(str(volume_ml)), not its binary
    value: 0.365 is stored as 0.36499999999999999, which float formatting
    and Decimal(0.365) round down to 0.36. ``volume_ml`` may also be the
    figure as text, as a screen shows it ("0.365").
    """
    return Decimal(str(volume_ml)).quantize(_STEP, rounding=ROUND_HALF_UP)


# The smallest amount a schedule can be given, as the wizard shows it: 0.10.
SMALLEST_SCHEDULE = schedule_amount(SCHEDULE_VOLUME_MIN_ML)


def can_be_scheduled(amount: Decimal) -> bool:
    """Whether a schedule_amount() is one the wizard takes: at least
    SMALLEST_SCHEDULE. The rest of a run is never more than the run's
    scheduled amount, which the wizard kept within SCHEDULE_VOLUME_MAX_ML."""
    return amount >= SMALLEST_SCHEDULE
