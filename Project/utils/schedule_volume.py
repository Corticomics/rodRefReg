"""The volume a schedule can be given: the schedule wizard's limits, in one place.

Every volume field of the schedule wizard (ui/schedule_wizard.py, whose Step 3
the Schedules hub's Edit dialog reuses) takes SCHEDULE_VOLUME_MIN_ML to
SCHEDULE_VOLUME_MAX_ML at SCHEDULE_VOLUME_DECIMALS decimals. Text that tells
the operator an amount to type there takes the limits from here too, so the
two cannot drift.

Qt-free, so the words that use it can be tested on their own.
"""

from __future__ import annotations

SCHEDULE_VOLUME_DECIMALS = 2
SCHEDULE_VOLUME_MIN_ML = 0.1
SCHEDULE_VOLUME_MAX_ML = 50.0
