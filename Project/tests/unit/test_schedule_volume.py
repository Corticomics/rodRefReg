"""The schedule wizard's volume limits, in one place.

utils.schedule_volume holds them: two decimals, 0.1 to 50.0 mL. Every volume
field of the wizard, Quick Apply's and each animal's in both modes, is built
from them (ui.schedule_wizard.volume_spin_box), and so is every volume field
of the Schedules hub's Edit dialog, which reuses the wizard's Step 3
(test_edit_schedule_dialog.py). Text that gives the operator an amount to
type there takes the same limits, so the two cannot drift. Giving the limits
one source changes none of them. The limits are Qt-free; the fields are
checked offscreen and skip without PyQt5.
"""

from __future__ import annotations

import os

import pytest

from utils.schedule_volume import (
    SCHEDULE_VOLUME_DECIMALS,
    SCHEDULE_VOLUME_MAX_ML,
    SCHEDULE_VOLUME_MIN_ML,
)

LIMITS = ("SCHEDULE_VOLUME_DECIMALS", "SCHEDULE_VOLUME_MIN_ML", "SCHEDULE_VOLUME_MAX_ML")


def test_the_limits_are_the_wizards_as_they_were():
    """Two decimals, 0.1 to 50.0 mL: what the wizard's fields took before."""
    assert SCHEDULE_VOLUME_DECIMALS == 2
    assert SCHEDULE_VOLUME_MIN_ML == 0.1
    assert SCHEDULE_VOLUME_MAX_ML == 50.0


@pytest.fixture(scope="module")
def qapp():
    pytest.importorskip("PyQt5")
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    from PyQt5.QtWidgets import QApplication  # noqa: PLC0415

    return QApplication.instance() or QApplication([])


def _step3(mode):
    """The wizard's Step 3 for two animals, as the wizard builds it."""
    from ui.schedule_wizard import Step3ConfigureParameters  # noqa: PLC0415

    step = Step3ConfigureParameters()
    step.set_animals(
        [{"id": 1, "lab_id": "M-11", "name": "A"}, {"id": 2, "lab_id": "M-12", "name": "B"}]
    )
    step.set_schedule_type(mode)
    return step


def _volume_fields(step):
    """Quick Apply's volume field, then each animal's."""
    return [step._global_volume] + [step._animal_widgets[a]["volume"] for a in (1, 2)]


@pytest.mark.parametrize("mode", ["staggered", "instant"])
def test_every_wizard_volume_field_keeps_its_range_decimals_and_default(qapp, mode):
    """Quick Apply's and each animal's, the only spin boxes of Step 3: 0.10 to
    50.00 mL at two decimals, starting at 1.00 mL, as before. Quick Apply's
    set no decimals before, so it had the spin box's own 2."""
    from PyQt5.QtWidgets import QDoubleSpinBox  # noqa: PLC0415

    step = _step3(mode)
    fields = _volume_fields(step)
    assert {id(f) for f in step.findChildren(QDoubleSpinBox)} == {id(f) for f in fields}
    for field in fields:
        assert (field.decimals(), field.minimum(), field.maximum()) == (2, 0.1, 50.0)
        assert (field.decimals(), field.minimum(), field.maximum()) == (
            SCHEDULE_VOLUME_DECIMALS,
            SCHEDULE_VOLUME_MIN_ML,
            SCHEDULE_VOLUME_MAX_ML,
        )
        assert (field.value(), field.suffix(), field.singleStep()) == (1.0, " mL", 1.0)


@pytest.mark.parametrize("mode", ["staggered", "instant"])
def test_every_wizard_volume_field_is_built_from_the_shared_limits(qapp, monkeypatch, mode):
    """The wizard's limits are utils.schedule_volume's own objects, and when
    the limits the wizard reads change, every volume field follows: none
    keeps a limit of its own."""
    import ui.schedule_wizard as wizard  # noqa: PLC0415
    from utils import schedule_volume  # noqa: PLC0415

    for name in LIMITS:
        assert getattr(wizard, name) is getattr(schedule_volume, name), name
    for name, value in zip(LIMITS, (3, 0.25, 40.0)):
        monkeypatch.setattr(wizard, name, value)
    for field in _volume_fields(_step3(mode)):
        assert (field.decimals(), field.minimum(), field.maximum()) == (3, 0.25, 40.0)
