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
import os
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


def test_boot_announces_the_resolved_topology(database_handler, capsys):
    """
    Nothing is connected to system_status at boot (main.setup and the
    splash worker call ensure_solenoid_defaults with no receivers), so the
    announcement must also be printed - that is what reaches the journal an
    operator checks. Asserted on stdout with NO signal receiver connected.
    """
    from controllers.system_controller import SystemController  # noqa: PLC0415

    sc = SystemController(database_handler)
    sc.ensure_solenoid_defaults()
    out = capsys.readouterr().out
    assert "[TOPOLOGY] Valve topology: shared_manifold" in out

    sc.save_settings({SETTING_KEY: INDEPENDENT})
    sc.ensure_solenoid_defaults()
    out = capsys.readouterr().out
    assert "[TOPOLOGY] Valve topology: independent" in out and "no master valve" in out

    sc.save_settings({SETTING_KEY: "bogus"})
    sc.ensure_solenoid_defaults()
    out = capsys.readouterr().out
    assert "[TOPOLOGY] Unknown valve_topology 'bogus'" in out


# --- the cage map -----------------------------------------------------------


def test_cage_map_numbers_cages_over_every_relay_but_the_master():
    from utils.topology import cage_map_from  # noqa: PLC0415

    one_hat = cage_map_from({"num_hats": 1, "global_master_relay_id": 16})
    assert one_hat == {cage: cage for cage in range(1, 16)}

    two_hats = cage_map_from({"num_hats": 2, "global_master_relay_id": 16})
    assert len(two_hats) == 31
    assert two_hats[15] == 15 and two_hats[16] == 17 and two_hats[31] == 32

    master_first = cage_map_from({"num_hats": 1, "global_master_relay_id": 1})
    assert master_first[1] == 2 and master_first[15] == 16


def test_cage_map_prefers_the_stored_map_with_int_keys():
    from utils.topology import cage_map_from  # noqa: PLC0415

    assert cage_map_from({"cage_relays": {"1": 5, "2": 9}, "num_hats": 2}) == {1: 5, 2: 9}
    assert cage_map_from({}) == {cage: cage for cage in range(1, 16)}


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
    monkeypatch.setattr(module, "_app_running", lambda: (False, "inactive"))
    return module


class _FakeRun:
    """Stand-in for subprocess.run returning a fixed systemctl result."""

    def __init__(self, returncode, stdout="", stderr="", raise_=None):
        self.returncode, self.stdout, self.stderr, self.raise_ = returncode, stdout, stderr, raise_

    def __call__(self, *_args, **_kwargs):
        if self.raise_:
            raise self.raise_
        return self


@pytest.mark.parametrize(
    "run,expected",
    [
        (_FakeRun(0, stdout="active"), True),
        (_FakeRun(3, stdout="inactive"), False),
        (_FakeRun(4, stderr="Unit rrr.service could not be found."), False),
        (_FakeRun(1, stderr="Failed to connect to bus: no session bus"), None),
        (_FakeRun(0, raise_=FileNotFoundError("systemctl")), None),
    ],
)
def test_app_running_is_tri_state(monkeypatch, run, expected):
    """Without /proc to scan, systemd's answer is all there is."""
    module = _load_tool()
    monkeypatch.setattr(module.subprocess, "run", run)
    monkeypatch.setattr(module, "_app_processes", lambda: None)
    state, _detail = module._app_running()
    assert state is expected


def test_tool_refuses_when_it_cannot_tell_whether_the_app_runs(
    database_handler, monkeypatch, capsys
):
    """A shell without a session bus must not be read as 'app stopped'."""
    from controllers.system_controller import SystemController  # noqa: PLC0415

    module = _load_tool()
    monkeypatch.setattr(module.subprocess, "run", _FakeRun(1, stderr="Failed to connect to bus"))
    monkeypatch.setattr(module, "_app_processes", lambda: None)  # no /proc either

    assert module.main([INDEPENDENT, "--yes"]) == 2
    err = capsys.readouterr().err
    assert "could not determine" in err and "Failed to connect to bus" in err
    assert SystemController(database_handler).settings[SETTING_KEY] == SHARED_MANIFOLD

    assert module.main([]) == 0, "showing never needs the check"
    assert module.main([INDEPENDENT, "--yes", "--force"]) == 0


def test_tool_names_a_data_dir_that_is_not_a_directory(tool, tmp_path, capsys):
    not_a_dir = tmp_path / "file"
    not_a_dir.write_text("x")
    assert tool.main(["--data-dir", str(not_a_dir)]) == 2
    assert "is not a directory" in capsys.readouterr().err


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

    monkeypatch.setattr(tool, "_app_running", lambda: (True, "rrr.service is active"))
    assert tool.main([INDEPENDENT, "--yes"]) == 2
    err = capsys.readouterr().err
    assert "the app is running (rrr.service is active)" in err and "Close it first" in err
    assert SystemController(database_handler).settings[SETTING_KEY] == SHARED_MANIFOLD

    assert tool.main([]) == 0, "showing is always allowed"
    assert tool.main([INDEPENDENT, "--yes", "--force"]) == 0
    assert SystemController(database_handler).settings[SETTING_KEY] == INDEPENDENT


# --- finding the app however it was started --------------------------------------
#
# The desktop icon starts the app outside rrr.service, so asking systemd
# alone said "stopped" while the app ran, and the tool wrote a value the
# app then saved its old one back over. The launcher runs `python3 main.py`
# from the release's Project directory either way; the tool finds that
# process through /proc.


def _fake_project(tmp_path, name="releases/1.21.0/Project"):
    project = tmp_path / name
    (project / "gpio").mkdir(parents=True)
    (project / "version.py").write_text('__version__ = "1.21.0"\n')
    (project / "gpio" / "relay_worker.py").write_text("")
    return project


def _fake_proc(tmp_path, entries):
    """entries: {pid: (argv or None, cwd or None)} -> a /proc-shaped tree."""
    proc = tmp_path / "proc"
    proc.mkdir()
    (proc / "self").mkdir()  # non-numeric entries are ignored
    for pid, (argv, cwd) in entries.items():
        entry = proc / str(pid)
        entry.mkdir()
        if argv is not None:
            (entry / "cmdline").write_bytes(b"\0".join(a.encode() for a in argv) + b"\0")
        if cwd is not None:
            (entry / "cwd").symlink_to(cwd)
    return proc


def test_the_process_scan_finds_the_app_and_nothing_else(tmp_path):
    module = _load_tool()
    project = _fake_project(tmp_path)
    elsewhere = tmp_path / "elsewhere"
    elsewhere.mkdir()
    venv_python = "/home/pi/rrr/shared/venv/bin/python3"
    proc = _fake_proc(
        tmp_path,
        {
            101: ([venv_python, "main.py"], project),  # the launcher's way
            102: ([venv_python, "main.py"], elsewhere),  # some other main.py
            103: (["python3", str(project / "main.py")], elsewhere),  # absolute path
            104: (None, project),  # gone mid-scan / unreadable
            105: (["python3", "-m", "pytest"], project),  # not the app
            os.getpid(): ([venv_python, "main.py"], project),  # never ourselves
        },
    )
    assert module._app_processes(str(proc)) == [101, 103]
    assert module._app_processes(str(tmp_path / "no-proc")) is None


@pytest.mark.parametrize(
    "unit,pids,expected",
    [
        (True, [], True),
        (False, [4242], True),  # started from the desktop icon, not the service
        (None, [], False),  # the scan answers what systemd could not
        (False, [], False),
        (False, None, False),  # no /proc: systemd's answer stands
        (None, None, None),  # neither can tell: never read as "stopped"
    ],
)
def test_app_running_combines_the_service_and_the_process_scan(monkeypatch, unit, pids, expected):
    module = _load_tool()
    monkeypatch.setattr(module, "_unit_state", lambda: (unit, "systemctl says so"))
    monkeypatch.setattr(module, "_app_processes", lambda: pids)
    state, detail = module._app_running()
    assert state is expected
    if pids:
        assert f"pid {pids[0]}" in detail


def test_tool_refuses_while_a_desktop_launched_app_runs(database_handler, monkeypatch, capsys):
    from controllers.system_controller import SystemController  # noqa: PLC0415

    module = _load_tool()
    monkeypatch.setattr(module.subprocess, "run", _FakeRun(3, stdout="inactive"))
    monkeypatch.setattr(module, "_app_processes", lambda: [4242])

    assert module.main([INDEPENDENT, "--yes"]) == 2
    err = capsys.readouterr().err
    assert "RRR app process running (pid 4242)" in err and "Close it first" in err
    assert SystemController(database_handler).settings[SETTING_KEY] == SHARED_MANIFOLD


@pytest.mark.skipif(not os.path.isdir("/proc"), reason="needs a real /proc (Linux, as on the Pi)")
def test_the_process_scan_finds_a_real_app_process(tmp_path):
    """Against the real /proc: a `python3 main.py` child run from a Project tree."""
    import subprocess  # noqa: PLC0415
    import sys  # noqa: PLC0415
    import time  # noqa: PLC0415

    module = _load_tool()
    project = _fake_project(tmp_path)
    (project / "main.py").write_text("import time\ntime.sleep(30)\n")
    child = subprocess.Popen([sys.executable, "main.py"], cwd=str(project))
    try:
        deadline = time.monotonic() + 10
        found = []
        while time.monotonic() < deadline and child.pid not in found:
            found = module._app_processes() or []
            time.sleep(0.05)
        assert child.pid in found
    finally:
        child.kill()
        child.wait()
    assert child.pid not in (module._app_processes() or [])
