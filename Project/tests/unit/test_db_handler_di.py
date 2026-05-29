"""Regression tests for the database-handler DI contract (R3).

After R3 (finish DI), the two classes that previously self-constructed
their own ``DatabaseHandler`` — ``ProjectsController`` and
``ScheduleDropArea`` — must instead accept the canonical handler as a
required constructor argument. These tests pin that contract so a future
edit can't silently re-introduce a second writer to the DB.

Background: see DATABASE_HANDLER_REFACTOR_DESIGN.md §10 ("DI feasibility")
— two redundant ``DatabaseHandler()`` instances each re-ran
``create_tables()`` on startup; the goal was one canonical handle.

``ProjectsController`` is Qt-free; ``ScheduleDropArea`` imports PyQt5 and
is skipped where PyQt5 is unavailable (same convention as test_gui_smoke).
"""

from __future__ import annotations

import pytest


def test_projects_controller_requires_database_handler(database_handler):
    """Injected handler must be stored verbatim — no self-construct."""
    from controllers.projects_controller import ProjectsController  # noqa: PLC0415

    controller = ProjectsController(database_handler)
    assert controller.db_handler is database_handler


def test_projects_controller_rejects_missing_handler():
    """Constructing without a handler must fail loudly, not silently work."""
    from controllers.projects_controller import ProjectsController  # noqa: PLC0415

    with pytest.raises(TypeError):
        ProjectsController()  # signature requires database_handler
    with pytest.raises(ValueError):
        ProjectsController(None)


def test_schedule_drop_area_requires_database_handler(database_handler):
    """ScheduleDropArea must accept the injected handler and store it."""
    pytest.importorskip("PyQt5")
    import os  # noqa: PLC0415

    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    from PyQt5.QtWidgets import QApplication  # noqa: PLC0415

    from ui.schedule_drop_area import ScheduleDropArea  # noqa: PLC0415

    app = QApplication.instance() or QApplication([])
    try:
        area = ScheduleDropArea(database_handler)
        assert area.database_handler is database_handler
    finally:
        if app is not None:
            app.processEvents()


def test_schedule_drop_area_rejects_missing_handler():
    """ScheduleDropArea must refuse a None/absent handler."""
    pytest.importorskip("PyQt5")
    import os  # noqa: PLC0415

    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    from PyQt5.QtWidgets import QApplication  # noqa: PLC0415

    from ui.schedule_drop_area import ScheduleDropArea  # noqa: PLC0415

    _ = QApplication.instance() or QApplication([])
    with pytest.raises(TypeError):
        ScheduleDropArea()  # signature requires database_handler
    with pytest.raises(ValueError):
        ScheduleDropArea(None)
