"""Shared pytest fixtures for the RRR unit tests.

Every fixture isolates the test from real device state — no fixture touches
``~/rrr``, the user's settings, or the production database. ``RRR_DATA`` is
redirected to a per-test temp directory via ``monkeypatch``, so it is
guaranteed to be restored even on test failure.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Callable

import pytest


@pytest.fixture
def isolated_data_dir(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Return a tmp directory configured as ``RRR_DATA`` for the test.

    The environment variable is set via ``monkeypatch`` so it is automatically
    rolled back after the test, even on assertion failure.
    """
    data = tmp_path / "data"
    data.mkdir()
    monkeypatch.setenv("RRR_DATA", str(data))
    return data


@pytest.fixture
def database_handler(isolated_data_dir: Path):
    """A ``DatabaseHandler`` bound to the isolated ``RRR_DATA``.

    The handler creates a fresh SQLite database with the full RRR schema in
    the per-test temp directory; no production DB is touched.
    """
    from models.database_handler import DatabaseHandler  # noqa: PLC0415

    return DatabaseHandler()


@pytest.fixture
def system_controller(database_handler):
    """A ``SystemController`` whose backing store is the isolated DB.

    Instantiating it calls :meth:`load_settings`, which transparently runs
    the legacy-JSON migration (a no-op when no ``settings.json`` is present).
    """
    from controllers.system_controller import SystemController  # noqa: PLC0415

    return SystemController(database_handler)


@pytest.fixture
def write_legacy_settings(isolated_data_dir: Path) -> Callable[[dict], Path]:
    """Factory: write a fake legacy ``settings.json`` into the isolated dir.

    Returns the path of the written file so tests can assert against it
    later (e.g. "the migration must not modify this file").
    """

    def _write(payload: dict) -> Path:
        path = isolated_data_dir / "settings.json"
        path.write_text(json.dumps(payload))
        return path

    return _write
