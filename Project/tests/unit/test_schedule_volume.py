"""The schedule wizard's volume limits, in one place.

utils.schedule_volume holds them: two decimals, 0.1 to 50.0 mL. Every volume
field of the wizard, Quick Apply's and each animal's in both modes, is built
from them (ui.schedule_wizard.volume_spin_box), and so is every volume field
of the Schedules hub's Edit dialog, which reuses the wizard's Step 3
(test_edit_schedule_dialog.py). Text that gives the operator an amount to
type there takes the same limits, so the two cannot drift. Giving the limits
one source changes none of them.

The amount to schedule for the rest of a run is rounded to them, half up
(utils.last_run_text.amount_to_schedule). Lab run 37 (2026-10-19) offered
"the remaining 0.369 mL", which the field cannot take: the operator typed
0.36. The limits and the rounding are Qt-free; the fields are checked
offscreen and skip without PyQt5.
"""

from __future__ import annotations

import os
from decimal import ROUND_HALF_UP, Decimal

import pytest

from utils.last_run_text import BELOW_SMALLEST_SCHEDULE, amount_to_schedule
from utils.schedule_volume import (
    SCHEDULE_VOLUME_DECIMALS,
    SCHEDULE_VOLUME_MAX_ML,
    SCHEDULE_VOLUME_MIN_ML,
    SMALLEST_SCHEDULE,
    can_be_scheduled,
    schedule_amount,
)

LIMITS = ("SCHEDULE_VOLUME_DECIMALS", "SCHEDULE_VOLUME_MIN_ML", "SCHEDULE_VOLUME_MAX_ML")


def test_the_limits_are_the_wizards_as_they_were():
    """Two decimals, 0.1 to 50.0 mL: what the wizard's fields took before."""
    assert SCHEDULE_VOLUME_DECIMALS == 2
    assert SCHEDULE_VOLUME_MIN_ML == 0.1
    assert SCHEDULE_VOLUME_MAX_ML == 50.0


def test_the_smallest_schedule_is_the_wizards_minimum_as_it_shows_it():
    assert str(SMALLEST_SCHEDULE) == "0.10"
    assert BELOW_SMALLEST_SCHEDULE == "below the smallest schedule (0.10 mL)"
    assert can_be_scheduled(schedule_amount(0.1))
    assert can_be_scheduled(schedule_amount("0.095")), "rounds up to 0.10"
    assert not can_be_scheduled(schedule_amount("0.094"))
    assert not can_be_scheduled(schedule_amount(0.0))


@pytest.mark.parametrize(
    ("volume", "amount"),
    [
        (0.369456, "0.37"),  # lab run 37's remainder
        ("0.369", "0.37"),  # the same, as the tooltip shows it
        (0.365, "0.37"),  # stored as 0.36499999999999999
        ("0.365", "0.37"),
        (0.375, "0.38"),
        (0.125, "0.13"),  # exact in binary: float formatting rounds it to even
        (0.364, "0.36"),
        (0.1, "0.10"),
        (50.0, "50.00"),
    ],
)
def test_an_amount_is_rounded_half_up_on_the_figure_as_written(volume, amount):
    assert str(schedule_amount(volume)) == amount


def test_0_365_is_stored_below_the_half_and_still_rounds_up():
    """0.365 is stored as 0.36499999999999999: float formatting, and Decimal
    of the float, round that binary value down to 0.36. schedule_amount()
    rounds the figure as written, so 0.365 is 0.37, as it reads."""
    assert f"{0.365:.17f}" == "0.36499999999999999"
    assert f"{0.365:.2f}" == "0.36"
    assert Decimal(0.365).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP) == Decimal("0.36")
    assert schedule_amount(0.365) == Decimal("0.37")
    assert f"{0.125:.2f}" == "0.12", "an exact binary half goes to even"
    assert schedule_amount(0.125) == Decimal("0.13")


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


def test_the_amount_given_for_run_37_is_typed_as_shown(qapp):
    """Lab run 37: typed into a wizard volume field, the "0.369" the tooltip
    gave loses its third decimal and the field holds 0.36, the amount the
    operator scheduled. The amount the tooltip and Run give now, 0.37, is
    held as typed."""
    from PyQt5.QtCore import QLocale  # noqa: PLC0415
    from PyQt5.QtTest import QTest  # noqa: PLC0415

    run_37 = amount_to_schedule(0.6 - 12 * 0.019212)
    assert run_37 == "0.37"
    field = _volume_fields(_step3("staggered"))[1]
    field.setLocale(QLocale.c())  # typed with a "." decimal point, whatever the host's locale
    for typed, held in (("0.369", "0.36"), (run_37, "0.37")):
        field.lineEdit().selectAll()
        QTest.keyClicks(field, typed)
        field.interpretText()
        assert field.cleanText() == held, typed
