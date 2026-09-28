"""The valve_topology setting and the controller it selects (v1.20.0, step 1).

Two topologies share one codebase: the production shared manifold (master
valve on relay 16 + one valve per cage) and the independent setup (one
syringe and one valve per animal, no master). This PR lands the setting, the
no-master controller and the one place that chooses between them; nothing
in the delivery path consumes it yet, so the shared trace
(test_topology_trace.py) must be untouched.

Pinned here:
- the setting defaults to the shared manifold, persists as a string, survives
  the force-merge block on every boot, and a value nobody recognises falls
  back to the shared manifold (today's behaviour) with a status message;
- the independent controller never drives a relay it was not given as a
  cage: its master operations succeed with zero relay writes;
- the shared controller refuses a master id below 1, because the relay layer
  would route 0 / -1 to a real relay on the last HAT;
- build_solenoid_controller is the single decision point;
- the device tool writes the setting through SystemController.
"""

from __future__ import annotations

import importlib.util
import sqlite3
from pathlib import Path

import pytest

pytest.importorskip("PyQt5")

from drivers.solenoid_controller import (  # noqa: E402
    IndependentSolenoidController,
    SolenoidController,
)
from utils.topology import (  # noqa: E402
    INDEPENDENT,
    SETTING_KEY,
    SHARED_MANIFOLD,
    build_solenoid_controller,
    is_independent,
    normalize,
    topology_from,
)

CAGES = {1: 1, 2: 2, 3: 3}


# --- the setting ------------------------------------------------------------


@pytest.mark.parametrize(
    "stored,expected",
    [
        ('shared_manifold', SHARED_MANIFOLD),
        ('independent', INDEPENDENT),
        (' Independent ', INDEPENDENT),
        ('manifold', SHARED_MANIFOLD),
        ('', SHARED_MANIFOLD),
        (None, SHARED_MANIFOLD),
        (16, SHARED_MANIFOLD),
    ],
)
def test_normalize_falls_back_to_the_shared_manifold(stored, expected):
    assert normalize(stored) == expected
    assert topology_from({SETTING_KEY: stored}) == expected


def test_setting_defaults_to_shared_and_persists_as_a_string(database_handler):
    from controllers.system_controller import SystemController  # noqa: PLC0415

    sc1 = SystemController(database_handler)
    assert sc1.settings[SETTING_KEY] == SHARED_MANIFOLD
    assert SETTING_KEY in sc1._get_persisted_keys()
    assert is_independent(sc1.settings) is False

    sc1.save_settings({SETTING_KEY: INDEPENDENT})
    sc2 = SystemController(database_handler)
    assert sc2.settings[SETTING_KEY] == INDEPENDENT
    assert is_independent(sc2.settings) is True
    # The row is tagged as a string, which is what governs the read-back.
    with sqlite3.connect(database_handler.db_path) as conn:
        row = conn.execute(
            "SELECT setting_type FROM system_settings WHERE setting_key = ?", (SETTING_KEY,)
        ).fetchone()
    assert row == ('str',)

    # main.setup() runs this on every boot; its pulse_mode_settings block
    # force-merges values, so a key placed there would reset the choice.
    sc2.ensure_solenoid_defaults()
    assert sc2.settings[SETTING_KEY] == INDEPENDENT
    assert database_handler.get_system_settings()[SETTING_KEY] == INDEPENDENT


@pytest.mark.parametrize(
    "stored,expected",
    [(' Independent ', INDEPENDENT), ('bogus', SHARED_MANIFOLD)],
)
def test_unrecognised_stored_value_is_normalised_on_boot(database_handler, stored, expected):
    from controllers.system_controller import SystemController  # noqa: PLC0415

    SystemController(database_handler).save_settings({SETTING_KEY: stored})

    sc = SystemController(database_handler)
    messages = []
    sc.system_status.connect(messages.append)
    sc.ensure_solenoid_defaults()

    assert sc.settings[SETTING_KEY] == expected
    assert database_handler.get_system_settings()[SETTING_KEY] == expected
    assert any(SETTING_KEY in m and repr(stored) in m for m in messages), messages
    # A recognised-but-untidy value is reported as normalised, not unknown.
    verb = "Normalised" if expected == INDEPENDENT else "Unknown"
    assert any(m.startswith(verb) for m in messages), messages


def test_boot_announces_the_resolved_topology(database_handler):
    from controllers.system_controller import SystemController  # noqa: PLC0415

    sc = SystemController(database_handler)
    messages = []
    sc.system_status.connect(messages.append)
    sc.ensure_solenoid_defaults()
    assert any(m.startswith("Valve topology: shared_manifold") for m in messages), messages

    sc.save_settings({SETTING_KEY: INDEPENDENT})
    messages.clear()
    sc.ensure_solenoid_defaults()
    assert any(
        m.startswith("Valve topology: independent") and "no master valve" in m for m in messages
    ), messages


# --- the controllers --------------------------------------------------------


def test_independent_controller_never_drives_a_master_relay(fake_relay_handler):
    valves = IndependentSolenoidController(fake_relay_handler, CAGES)
    assert valves.has_master is False

    assert valves.open_master() is True
    assert valves.close_master() is True
    assert fake_relay_handler.trace == [], "master operations must not touch any relay"

    assert valves.open_cage(2) is True
    assert valves.close_cage(2) is True
    assert valves.close_all_cages() is True
    assert fake_relay_handler.trace == [((2,), 1), ((2,), 0), ((1, 2, 3), 0)]
    assert fake_relay_handler.energized() == set()

    with pytest.raises(ValueError):
        valves.open_cage(99)


def test_independent_controller_accepts_string_cage_keys(fake_relay_handler):
    valves = IndependentSolenoidController(fake_relay_handler, {'1': 1, '2': 2})
    valves.open_cage(1)
    assert fake_relay_handler.trace == [((1,), 1)]


def test_independent_controller_rejects_a_missing_handler_or_map():
    with pytest.raises(ValueError):
        IndependentSolenoidController(None, CAGES)
    with pytest.raises(ValueError):
        IndependentSolenoidController(object(), {})


@pytest.mark.parametrize("bad_master", [0, -1])
def test_shared_controller_rejects_a_master_id_that_would_hit_the_last_hat(
    fake_relay_handler, bad_master
):
    """gpio_handler routes divmod(id - 1, 16) with no lower bound: 0 -> relay 16
    of the last HAT, -1 -> relay 15. A sentinel must never reach the hardware."""
    with pytest.raises(ValueError):
        SolenoidController(fake_relay_handler, bad_master, CAGES)


@pytest.mark.parametrize("bad_relay", [0, -1])
@pytest.mark.parametrize("build", ["shared", "independent"])
def test_controllers_reject_a_cage_relay_id_that_would_hit_the_last_hat(
    fake_relay_handler, build, bad_relay
):
    """A cage mapped to relay 0 or -1 would be misrouted exactly like a bad master id."""
    with pytest.raises(ValueError, match="cage relay ids"):
        if build == "shared":
            SolenoidController(fake_relay_handler, 16, {1: bad_relay})
        else:
            IndependentSolenoidController(fake_relay_handler, {1: bad_relay})


def test_shared_controller_still_drives_the_master(fake_relay_handler):
    valves = SolenoidController(fake_relay_handler, 16, CAGES)
    assert valves.has_master is True
    valves.open_master()
    valves.close_master()
    assert fake_relay_handler.trace == [((16,), 1), ((16,), 0)]


# --- the single decision point ---------------------------------------------


def test_builder_picks_the_shared_controller_by_default(fake_relay_handler):
    valves = build_solenoid_controller(fake_relay_handler, {}, CAGES)
    assert type(valves) is SolenoidController
    assert valves.has_master is True
    valves.open_master()
    assert fake_relay_handler.trace == [((16,), 1)]


def test_builder_honours_a_custom_master_relay(fake_relay_handler):
    settings = {SETTING_KEY: SHARED_MANIFOLD, 'global_master_relay_id': 32}
    valves = build_solenoid_controller(fake_relay_handler, settings, CAGES)
    valves.open_master()
    assert fake_relay_handler.trace == [((32,), 1)]


def test_builder_picks_the_independent_controller(fake_relay_handler):
    settings = {SETTING_KEY: INDEPENDENT, 'global_master_relay_id': 16}
    valves = build_solenoid_controller(fake_relay_handler, settings, {'1': 1})
    assert isinstance(valves, IndependentSolenoidController)
    valves.open_master()
    valves.open_cage(1)
    assert fake_relay_handler.trace == [((1,), 1)], "relay 16 is never written"


def test_builder_treats_garbage_as_shared(fake_relay_handler):
    valves = build_solenoid_controller(fake_relay_handler, {SETTING_KEY: 'nope'}, CAGES)
    assert type(valves) is SolenoidController


# --- the device tool ---------------------------------------------------------


def _load_tool():
    path = Path(__file__).resolve().parents[2] / "tools" / "set_valve_topology.py"
    spec = importlib.util.spec_from_file_location("set_valve_topology", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture
def tool(monkeypatch):
    module = _load_tool()
    monkeypatch.setattr(module, "_app_running", lambda: False)
    return module


def test_tool_shows_sets_and_reads_back_through_system_controller(
    database_handler, tool, capsys
):
    from controllers.system_controller import SystemController  # noqa: PLC0415

    assert tool.main([]) == 0
    out = capsys.readouterr().out
    assert f"database: {database_handler.db_path}" in out
    assert f"current {SETTING_KEY}: {SHARED_MANIFOLD}" in out

    assert tool.main([INDEPENDENT, "--yes"]) == 0
    out = capsys.readouterr().out
    assert f"{SETTING_KEY} set to: {INDEPENDENT}" in out
    assert SystemController(database_handler).settings[SETTING_KEY] == INDEPENDENT

    assert tool.main([INDEPENDENT, "--yes"]) == 0
    assert "no change" in capsys.readouterr().out

    assert tool.main([SHARED_MANIFOLD]) == 0
    assert SystemController(database_handler).settings[SETTING_KEY] == SHARED_MANIFOLD


def test_tool_requires_confirmation_to_set_independent(database_handler, tool, capsys):
    from controllers.system_controller import SystemController  # noqa: PLC0415

    assert tool.main([INDEPENDENT]) == 2
    assert "NO WATER" in capsys.readouterr().err
    assert SystemController(database_handler).settings[SETTING_KEY] == SHARED_MANIFOLD


def test_tool_refuses_without_a_data_directory_and_creates_nothing(tool, tmp_path, monkeypatch):
    monkeypatch.delenv("RRR_DATA", raising=False)
    missing_default = tmp_path / "no-such-rrr-data"
    monkeypatch.setattr(tool, "DEFAULT_DATA_DIR", str(missing_default))

    assert tool.main([INDEPENDENT, "--yes"]) == 2
    assert not missing_default.exists()
    assert not list(tmp_path.rglob("rrr_database.db"))


def test_tool_never_creates_a_database(tool, tmp_path):
    empty = tmp_path / "data"
    empty.mkdir()
    assert tool.main([INDEPENDENT, "--yes", "--data-dir", str(empty)]) == 2
    assert not (empty / "rrr_database.db").exists()
    assert not (empty / "secrets.json").exists()


def test_tool_refuses_while_the_app_is_running_unless_forced(
    database_handler, tool, monkeypatch, capsys
):
    from controllers.system_controller import SystemController  # noqa: PLC0415

    monkeypatch.setattr(tool, "_app_running", lambda: True)
    assert tool.main([INDEPENDENT, "--yes"]) == 2
    assert "rrr.service is running" in capsys.readouterr().err
    assert SystemController(database_handler).settings[SETTING_KEY] == SHARED_MANIFOLD

    assert tool.main([]) == 0, "showing is always allowed"
    assert tool.main([INDEPENDENT, "--yes", "--force"]) == 0
    assert SystemController(database_handler).settings[SETTING_KEY] == INDEPENDENT
