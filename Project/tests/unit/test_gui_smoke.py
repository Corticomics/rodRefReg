"""Headless smoke tests for the PyQt5 UI tree.

Phase 0 of the stale-code cleanup. Constructs the widgets that the
forthcoming Tier-0/Tier-1 removals touch, so any regression that drops a
still-referenced symbol breaks CI immediately. Runs offscreen via
``QT_QPA_PLATFORM=offscreen``; no display server required.

Coverage:

* every module under ``Project/ui/`` imports cleanly (catches broken
  intra-package imports and dangling references to removed files),
* ``ui.__init__`` re-exports every name in its ``__all__``,
* ``ProjectsSection`` constructs and exposes the four live tabs —
  ``SchedulesHub``, ``AnimalsTab``, ``WizardTab``, ``CagesVisualizationTab`` —
  via the attribute names that callers (``main.py``, ``SettingsTab``) use.

The test skips when PyQt5 is not importable so the suite still passes on a
developer machine without the system Qt bindings. CI installs
``python3-pyqt5`` from apt, so the test always runs there.
"""

from __future__ import annotations

import importlib
import os
import pkgutil
from pathlib import Path

import pytest

# Skip the whole module when PyQt5 is unavailable (e.g. a dev laptop without
# the system bindings). The conftest fixtures import models lazily, so this
# guard does not affect any other test in the suite.
pytest.importorskip("PyQt5")

# Headless Qt: must be set before QApplication is constructed.
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")


@pytest.fixture(scope="module")
def qapp():
    """Module-scoped QApplication so widgets can construct.

    Qt requires exactly one ``QApplication`` per process. Reusing one across
    tests is faster and matches how the real app runs.
    """
    from PyQt5.QtWidgets import QApplication  # noqa: PLC0415

    app = QApplication.instance() or QApplication([])
    yield app
    # No teardown: tearing the QApplication down mid-suite breaks any later
    # widget test in the same process.


def _ui_module_names() -> list[str]:
    """Return every importable module name under ``ui`` (top-level only)."""
    ui_dir = Path(__file__).resolve().parents[2] / "ui"
    names: list[str] = []
    for entry in pkgutil.iter_modules([str(ui_dir)]):
        # Skip subpackages (components/, widgets/, style/) — they are
        # imported transitively by the modules that depend on them, so
        # walking only the top-level catches the same regressions without
        # importing unrelated nested packages.
        if entry.ispkg:
            continue
        names.append(f"ui.{entry.name}")
    return names


def test_ui_package_imports_cleanly(qapp):
    """``import ui`` runs every re-export in ``ui/__init__.py``."""
    ui = importlib.import_module("ui")
    # Every name listed in ``__all__`` must resolve. Catches the case where
    # ``__init__.py`` re-exports a class that has been deleted.
    for name in getattr(ui, "__all__", []):
        assert hasattr(ui, name), f"ui.__all__ lists {name!r} but it is missing"


@pytest.mark.parametrize("modname", _ui_module_names())
def test_ui_module_imports(qapp, modname):
    """Every top-level ``ui.*`` module imports without error."""
    importlib.import_module(modname)


def test_projects_section_constructs(qapp, database_handler, system_controller):
    """``ProjectsSection`` builds and exposes the four live tabs.

    Pins the contract main.py and SettingsTab rely on: ``schedules_tab``
    is a ``SchedulesHub``, ``animals_tab`` an ``AnimalsTab``,
    ``wizard_tab`` a ``WizardTab``, ``cages_tab`` a
    ``CagesVisualizationTab``.

    Also asserts ``cages_tab._system_controller`` is the same instance
    that was passed in — guards against the Phase 3.4 regression where
    ``gui.py`` forgot to forward ``system_controller`` to
    ``ProjectsSection``, leaving ``CagesVisualizationTab.refresh()`` a
    silent no-op that fell back to ``num_hats=1``.
    """
    from models.login_system import LoginSystem  # noqa: PLC0415
    from ui.animals_tab import AnimalsTab  # noqa: PLC0415
    from ui.cages_visualization_tab import CagesVisualizationTab  # noqa: PLC0415
    from ui.projects_section import ProjectsSection  # noqa: PLC0415
    from ui.schedules_hub import SchedulesHub  # noqa: PLC0415
    from ui.wizard_tab import WizardTab  # noqa: PLC0415

    login_system = LoginSystem(database_handler)
    section = ProjectsSection(
        settings={},
        print_to_terminal=lambda _msg: None,
        database_handler=database_handler,
        login_system=login_system,
        system_controller=system_controller,
    )

    assert isinstance(section.schedules_tab, SchedulesHub)
    assert isinstance(section.animals_tab, AnimalsTab)
    assert isinstance(section.wizard_tab, WizardTab)
    assert isinstance(section.cages_tab, CagesVisualizationTab)

    # Phase 3.4a contract: system_controller propagates to cages_tab.
    # Without this, refresh() falls back silently to num_hats=1.
    assert section.cages_tab._system_controller is system_controller


def test_cages_tab_renders_one_tab_per_hat(qapp, database_handler, system_controller):
    """Phase 3.4c: ``CagesVisualizationTab`` paginates by HAT.

    1 hat -> 1 HAT-tab. 2 hats -> 2 HAT-tabs. ``refresh()`` after a
    ``num_hats`` change rebuilds the tabs. The tab strip is the
    operator's entry point into multi-HAT setups; if the count drifts,
    HAT 1+ cages are silently inaccessible.
    """
    from ui.cages_visualization_tab import CagesVisualizationTab  # noqa: PLC0415

    system_controller.settings['num_hats'] = 1
    tab = CagesVisualizationTab(
        database_handler=database_handler,
        system_controller=system_controller,
    )
    assert tab._hat_tab_widget.count() == 1

    system_controller.settings['num_hats'] = 2
    tab.refresh()
    assert tab._hat_tab_widget.count() == 2

    system_controller.settings['num_hats'] = 1
    tab.refresh()
    assert tab._hat_tab_widget.count() == 1
