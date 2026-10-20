"""A cage's pulse profile: the pulse width and the valve-closed rest it was
calibrated at.

valve_calibration holds one profile per cage: cage_id is UNIQUE, and the
calibration wizard replaces the cage's row on every save. There is no global
pulse width (v2.1.0 removed it from Settings > Delivery): a delivery to a cage
replays that cage's profile (strategies.solenoid_flow_strategy), Settings >
Calibration shows it, and the calibration wizard starts from a profile chosen
here.

Qt-free, so the rules can be tested on their own.
"""

from __future__ import annotations

from collections.abc import Mapping
from datetime import datetime
from typing import NamedTuple, Optional, Tuple

from utils.calibration_gate import calibration_is_usable

# The rest between pulses before v1.16.0 stored one with each calibration. A
# row saved before then (NULL) keeps exactly this cadence.
LEGACY_INTER_PULSE_INTERVAL_MS = 100

# The production valve's validated profile (Parker 003-0257-900: 30 ms open,
# then 1000 ms closed, which keeps the coil cool and the volume per pulse
# steady). The wizard starts from it on a device with no calibration at all.
PRODUCTION_PULSE_WIDTH_MS = 30
PRODUCTION_INTER_PULSE_INTERVAL_MS = 1000

# What the calibration wizard's spin boxes accept.
PULSE_WIDTH_RANGE_MS = (10, 500)
INTER_PULSE_INTERVAL_RANGE_MS = (100, 2000)

# Where a wizard's starting profile came from.
THIS_CAGE = 'this cage'
LATEST_ON_DEVICE = 'latest on device'
PRODUCTION = 'production'


def resolve_interval_ms(raw) -> int:
    """The rest a delivery uses for a stored interval, in ms: the interval
    itself, or the legacy 100 ms when none was stored (NULL) or the stored one
    is not a positive number."""
    try:
        if raw is None:
            return LEGACY_INTER_PULSE_INTERVAL_MS
        interval = int(raw)
    except (TypeError, ValueError, OverflowError):
        return LEGACY_INTER_PULSE_INTERVAL_MS
    return interval if interval > 0 else LEGACY_INTER_PULSE_INTERVAL_MS


def profile_of(row) -> Optional[Tuple[int, int]]:
    """``(pulse width, rest)`` in ms, as a delivery to the cage replays them,
    or None when there is no row or it cannot plan a delivery
    (calibration_gate.calibration_is_usable: Settings shows it as Invalid)."""
    if not isinstance(row, Mapping) or not calibration_is_usable(row):
        return None
    return int(row['pulse_width_ms']), resolve_interval_ms(row.get('inter_pulse_interval_ms'))


def profile_text(pulse_width_ms, interval_ms) -> str:
    """A profile as Settings > Calibration shows it: ``30 / 1000 ms``."""
    return f"{pulse_width_ms} / {interval_ms} ms"


class StartingProfile(NamedTuple):
    """The pulse width and rest the calibration wizard starts a cage from."""

    pulse_width_ms: int
    interval_ms: int
    source: str  # THIS_CAGE, LATEST_ON_DEVICE or PRODUCTION
    source_cage_id: Optional[int] = None

    def describe(self) -> str:
        """One sentence for the wizard: the values, and where they came from."""
        values = f"{self.pulse_width_ms} ms / {self.interval_ms} ms"
        if self.source == THIS_CAGE:
            return f"Starting from this cage's last calibration: {values}."
        if self.source == LATEST_ON_DEVICE:
            return (
                f"Starting from cage {self.source_cage_id}'s calibration, the most recent "
                f"on this device: {values}."
            )
        return (
            f"Starting from {values}, the production valve's validated profile: no cage "
            "on this device has a calibration to start from."
        )


def _as_cage_id(value) -> Optional[int]:
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _repeatable(profile) -> bool:
    """Whether the wizard can run this profile again (inside its ranges)."""
    if profile is None:
        return False
    width, interval = profile
    low_width, high_width = PULSE_WIDTH_RANGE_MS
    low_interval, high_interval = INTER_PULSE_INTERVAL_RANGE_MS
    return low_width <= width <= high_width and low_interval <= interval <= high_interval


def _saved_when(row) -> datetime:
    """When a row was saved: its calibration date, or the earliest possible
    moment when the date cannot be read."""
    try:
        return datetime.fromisoformat(str(row.get('calibration_date'))).replace(tzinfo=None)
    except (TypeError, ValueError):
        return datetime.min


def _calibration_id(row) -> int:
    try:
        return int(row.get('calibration_id') or 0)
    except (TypeError, ValueError):
        return 0


def wizard_starting_profile(cage_id, calibrations) -> StartingProfile:
    """The pulse width and rest the calibration wizard starts ``cage_id`` from.

    1. The cage's own calibration, when it has a usable one. A Stale one
       counts: the valve topology changes the volume per pulse, not the
       profile the operator chose.
    2. Otherwise the device's most recent usable calibration: the latest
       calibration date, a tie going to the later save (the higher
       calibration id; a save replaces a cage's row with a new id).
    3. Otherwise the production valve's validated 30 ms / 1000 ms.

    Usable means calibration_gate.calibration_is_usable (a positive, finite
    volume per pulse and pulse width: what Settings does not mark Invalid)
    with a profile inside the wizard's ranges. ``calibrations`` is
    ``get_all_valve_calibrations()``: cage id to row. Anything else counts
    as no calibrations.
    """
    rows = {}
    if isinstance(calibrations, Mapping):
        for key, row in calibrations.items():
            cage = _as_cage_id(key)
            if cage is not None and isinstance(row, Mapping):
                rows[cage] = row

    own = profile_of(rows.get(_as_cage_id(cage_id)))
    if _repeatable(own):
        return StartingProfile(own[0], own[1], THIS_CAGE, _as_cage_id(cage_id))

    candidates = [(cage, row) for cage, row in rows.items() if _repeatable(profile_of(row))]
    if candidates:
        cage, row = max(
            candidates,
            key=lambda item: (_saved_when(item[1]), _calibration_id(item[1]), item[0]),
        )
        width, interval = profile_of(row)
        return StartingProfile(width, interval, LATEST_ON_DEVICE, cage)

    return StartingProfile(
        PRODUCTION_PULSE_WIDTH_MS, PRODUCTION_INTER_PULSE_INTERVAL_MS, PRODUCTION
    )
