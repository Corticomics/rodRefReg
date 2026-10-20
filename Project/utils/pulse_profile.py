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
# steady). The wizard starts from it on a device with no calibration at all,
# and takes its interval for a calibration that has none stored.
PRODUCTION_PULSE_WIDTH_MS = 30
PRODUCTION_INTER_PULSE_INTERVAL_MS = 1000

# What the calibration wizard's spin boxes accept.
PULSE_WIDTH_RANGE_MS = (10, 500)
INTER_PULSE_INTERVAL_RANGE_MS = (100, 2000)

# Where a wizard's starting profile came from.
THIS_CAGE = 'this cage'
LATEST_ON_DEVICE = 'latest on device'
PRODUCTION = 'production'


def stored_interval_ms(raw) -> Optional[int]:
    """A calibration's stored interval in ms, when it has one a delivery can
    use as it is: a positive whole number of ms. None for NULL (saved before
    v1.16.0 stored one) and for anything else: zero, negative, unreadable or
    infinite, which only a hand edit can store."""
    if raw is None:
        return None
    try:
        interval = int(raw)
    except (TypeError, ValueError, OverflowError):
        return None
    return interval if interval > 0 else None


def resolve_interval_ms(raw) -> int:
    """The rest a delivery uses for a stored interval, in ms: the stored
    interval (stored_interval_ms), else the legacy 100 ms."""
    interval = stored_interval_ms(raw)
    return LEGACY_INTER_PULSE_INTERVAL_MS if interval is None else interval


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
    """The pulse width and interval the calibration wizard starts a cage from."""

    pulse_width_ms: int
    interval_ms: int
    source: str  # THIS_CAGE, LATEST_ON_DEVICE or PRODUCTION
    source_cage_id: Optional[int] = None
    # False when the calibration it starts from has no stored interval (saved
    # before v1.16.0): the width is that calibration's, the interval the
    # production one.
    interval_stored: bool = True

    def describe(self) -> str:
        """What the wizard says: the values, and where they came from."""
        if self.source == PRODUCTION:
            return (
                f"Starting from {self.pulse_width_ms} ms / {self.interval_ms} ms, RRR's "
                "recommended profile for the Parker valve: no cage on this device has a "
                "usable calibration yet."
            )
        if self.source == THIS_CAGE:
            start = "Starting from this cage's last calibration"
        else:
            start = (
                f"Starting from cage {self.source_cage_id}'s calibration, the most recent "
                "usable one on this device"
            )
        if self.interval_stored:
            return f"{start}: {self.pulse_width_ms} ms / {self.interval_ms} ms."
        return (
            f"{start}: {self.pulse_width_ms} ms. It has no stored interval, so the interval "
            f"starts at the recommended {self.interval_ms} ms."
        )


def _as_cage_id(value) -> Optional[int]:
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _wizard_start(row) -> Optional[Tuple[int, int, bool]]:
    """``(pulse width, interval, whether the interval is the row's own)`` the
    wizard can start from ``row``, or None when the row cannot plan a delivery
    (profile_of) or its profile is outside the wizard's ranges.

    A row with no stored interval (saved before v1.16.0) starts at its width
    and the production interval, not at the legacy 100 ms its deliveries use:
    nobody chose that 100 ms, and its duty cycle heats the coil, which is what
    the wizard's duty-cycle warning is about."""
    profile = profile_of(row)
    if profile is None:
        return None
    width = profile[0]
    interval = stored_interval_ms(row.get('inter_pulse_interval_ms'))
    own_interval = interval is not None
    if not own_interval:
        interval = PRODUCTION_INTER_PULSE_INTERVAL_MS
    low_width, high_width = PULSE_WIDTH_RANGE_MS
    low_interval, high_interval = INTER_PULSE_INTERVAL_RANGE_MS
    if not (low_width <= width <= high_width and low_interval <= interval <= high_interval):
        return None
    return width, interval, own_interval


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
    """The pulse width and interval the calibration wizard starts ``cage_id``
    from.

    1. The cage's own calibration, when it has a usable one. A Stale one
       counts: the valve topology changes the volume per pulse, not the
       profile the operator chose.
    2. Otherwise the device's most recent usable calibration: the latest
       calibration date, a tie going to the later save (the higher
       calibration id; a save replaces a cage's row with a new id).
    3. Otherwise the production valve's validated 30 ms / 1000 ms.

    Usable means calibration_gate.calibration_is_usable (a positive, finite
    volume per pulse and pulse width: what Settings does not mark Invalid)
    with a profile inside the wizard's ranges. A calibration with no stored
    interval gives its width and the production interval (_wizard_start).
    ``calibrations`` is ``get_all_valve_calibrations()``: cage id to row.
    Anything else counts as no calibrations.
    """
    rows = {}
    if isinstance(calibrations, Mapping):
        for key, row in calibrations.items():
            cage = _as_cage_id(key)
            if cage is not None and isinstance(row, Mapping):
                rows[cage] = row

    own = _wizard_start(rows.get(_as_cage_id(cage_id)))
    if own is not None:
        width, interval, interval_stored = own
        return StartingProfile(width, interval, THIS_CAGE, _as_cage_id(cage_id), interval_stored)

    candidates = [(cage, row) for cage, row in rows.items() if _wizard_start(row) is not None]
    if candidates:
        cage, row = max(
            candidates,
            key=lambda item: (_saved_when(item[1]), _calibration_id(item[1]), item[0]),
        )
        width, interval, interval_stored = _wizard_start(row)
        return StartingProfile(width, interval, LATEST_ON_DEVICE, cage, interval_stored)

    return StartingProfile(
        PRODUCTION_PULSE_WIDTH_MS, PRODUCTION_INTER_PULSE_INTERVAL_MS, PRODUCTION
    )
