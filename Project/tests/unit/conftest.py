"""Shared pytest fixtures for the RRR unit tests.

Every fixture isolates the test from real device state — no fixture touches
``~/rrr``, the user's settings, or the production database. ``RRR_DATA`` is
redirected to a per-test temp directory via ``monkeypatch``, so it is
guaranteed to be restored even on test failure.
"""

from __future__ import annotations

import json
import threading
from pathlib import Path
from typing import Callable

import pytest


class FakeRelayHandler:
    """Stateful stand-in for ``gpio.gpio_handler.RelayHandler``.

    Keeps the state of every relay it has been asked to drive and an ordered
    log of every write, so a test can assert on the exact relay sequence a
    delivery produced (the "golden trace") and on the final state of the
    hardware, rather than on which methods were called.

    Faults are modelled the way the real HAT path fails: ``fail_on`` makes
    the matching write silently not happen while ``set_relays`` still
    returns True, which is what ``RelayHandler`` does when the vendor
    library raises (errors are printed and swallowed there).
    """

    def __init__(self, *_args, **_kwargs):
        self.states: dict[int, int] = {}
        self.writes: list[tuple[tuple[int, ...], int, int]] = []  # (ids, state, thread)
        self.dropped: list[tuple[tuple[int, ...], int]] = []
        self._fail_nth: int | None = None
        self._fail_relay: int | None = None

    def fail_on(self, nth: int | None = None, relay: int | None = None) -> None:
        """Drop the ``nth`` write (1-based) and/or every write touching ``relay``."""
        self._fail_nth = nth
        self._fail_relay = relay

    def set_relays(self, relay_ids, state) -> bool:
        ids = tuple(int(r) for r in relay_ids)
        state = int(state)
        attempt = len(self.writes) + len(self.dropped) + 1
        if attempt == self._fail_nth or (
            self._fail_relay is not None and self._fail_relay in ids
        ):
            self.dropped.append((ids, state))
            return True
        self.writes.append((ids, state, threading.get_ident()))
        for relay in ids:
            self.states[relay] = state
        return True

    def set_all_relays(self, state) -> None:
        state = int(state)
        self.writes.append((("all",), state, threading.get_ident()))
        for relay in list(self.states):
            self.states[relay] = state

    @property
    def trace(self) -> list[tuple[tuple[int, ...], int]]:
        """The write sequence without thread idents: ``[((16,), 1), ...]``."""
        return [(ids, state) for ids, state, _ in self.writes]

    def energized(self) -> set[int]:
        return {relay for relay, state in self.states.items() if state}


@pytest.fixture
def fake_relay_handler() -> FakeRelayHandler:
    """A fresh :class:`FakeRelayHandler`; pass it where a RelayHandler is expected."""
    return FakeRelayHandler()


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


@pytest.fixture
def offline(monkeypatch: pytest.MonkeyPatch) -> None:
    """Simulate a device with no network: DNS resolution fails for every host.

    Patches ``socket.getaddrinfo`` so any library that opens a connection
    (``requests``, ``urllib``, ``slack_sdk``) fails exactly as it would on a
    Pi that has lost its network — without the test ever touching a real
    socket. The patch is rolled back automatically after the test.

    Part of the Phase 1 offline-resilience test harness.
    """
    import socket

    def _no_dns(*_args, **_kwargs):
        raise socket.gaierror(socket.EAI_NONAME, "Name or service not known")

    monkeypatch.setattr(socket, "getaddrinfo", _no_dns)
