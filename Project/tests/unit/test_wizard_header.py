"""Tests for the wizard header refactor (QA item #5).

Covers:
- create_step_header() produces a single, uniform header (48px icon, the
  StepIcon/StepTitle/StepDescription objectNames) — replacing the four
  divergent per-step _create_header methods (36 vs 48px icons, inline fonts on
  the Review step) that read as inconsistent headers.
- WizardContainer exposes a persistent "Start Over" control that emits
  restart_requested (it used to live in a separate header band above the tab).

Skips when PyQt5 is unavailable; CI installs python3-pyqt5 so it runs there.
"""

from __future__ import annotations

import os

import pytest

pytest.importorskip("PyQt5")

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")


@pytest.fixture(scope="module")
def qapp():
    from PyQt5.QtWidgets import QApplication  # noqa: PLC0415

    return QApplication.instance() or QApplication([])


def test_create_step_header_is_uniform(qapp):
    from PyQt5.QtWidgets import QLabel  # noqa: PLC0415
    from ui.schedule_wizard import create_step_header  # noqa: PLC0415

    header = create_step_header("⚙", "Configure", "set things")
    labels = header.findChildren(QLabel)

    icons = [w for w in labels if w.objectName() == "StepIcon"]
    titles = [w for w in labels if w.objectName() == "StepTitle"]
    descs = [w for w in labels if w.objectName() == "StepDescription"]

    assert len(icons) == 1
    # The canonical icon size (the old compact steps used 36px).
    assert icons[0].width() == 48 and icons[0].height() == 48
    assert titles and titles[0].text() == "Configure"
    assert descs and descs[0].text() == "set things"


def test_steps_no_longer_define_local_header_factory(qapp):
    """Every step uses the shared helper, not its own _create_header."""
    import ui.schedule_wizard as sw  # noqa: PLC0415

    for cls_name in (
        "Step1SelectType",
        "Step2SelectAnimals",
        "Step3ConfigureParameters",
        "Step4Review",
    ):
        cls = getattr(sw, cls_name)
        assert not hasattr(cls, "_create_header"), f"{cls_name} still has _create_header"


def test_wizard_container_start_over_emits_restart(qapp):
    from ui.components.wizard import WizardContainer, WizardStep  # noqa: PLC0415

    container = WizardContainer([WizardStep("a", "A", "d"), WizardStep("b", "B", "d")])
    assert hasattr(container, "_start_over_button")

    fired = []
    container.restart_requested.connect(lambda: fired.append(True))
    container._start_over_button.click()
    assert fired == [True]
