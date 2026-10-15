"""A stopped run's record matches the delivery log and the Animals cell.

The headless test across the v2.0.0 train (docs/STOP_AND_PARTIAL_DELIVERY.md
§12, PR 12). From main.run_program on, the run is the app's own code over
stand-in hardware: Run starts a real RelayWorker in a QThread; the worker
drives the real SolenoidFlowStrategy and SolenoidController over a fake relay
HAT, calibration-only (no flow sensor), as the production rig runs; Stop runs
the real stop sequence through RunStopSection.stop_program and
main.stop_program; main._record_run_end closes the run in a real database;
and a real AnimalsTab shows it to the logged-in trainer. Not covered: Run's
queued schedule checks, which are skipped (see _press_run), and the Execution
Monitor: main's window here holds only the Run/Stop section and that tab.

A Stop in the middle of a delivery must record what the delivery log says the
animal got, and the Animals tab must show it red. An instant run that ends on
its own must record completed, with delivered equal to planned.

The cage's calibration stores a 1 ms rest between pulses instead of the rig's
1000 ms, and the strategy replays the rest stored per cage, so a run takes
seconds. The shared manifold's 200 ms prime and 0.3 s master hold, and the
100 ms settling after each pulse, stay as on the rig.
"""

from __future__ import annotations

import os
import sqlite3
import sys
import time
from datetime import datetime, timedelta
from types import SimpleNamespace

import pytest
from models.animal import Animal
from utils.dose_rounding import whole_pulses
from utils.last_run_text import NO_RUN_TEXT
from version import __version__

pytest.importorskip("PyQt5")

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

Q = 0.034164  # Parker valve without the needle, as calibrated on the Pi
CAGE = 1  # relay 1 on the one-HAT map; relay 16 drives the master valve
TRAINER, PASSWORD = "alice", "pw"
# Generous: a run here takes seconds, and a CI runner can be several times
# slower than a desktop. The waits end as soon as their condition holds.
TIMEOUT_S = 30

# The QApplication this module uses, kept for the rest of the session. When a
# QApplication is destroyed, PyQt5 deletes every QObject without a parent,
# main.control_signals and any SystemController a later test holds included.
_QAPP = []


@pytest.fixture(scope="module", autouse=True)
def qapp():
    from PyQt5.QtWidgets import QApplication  # noqa: PLC0415

    if not _QAPP:
        _QAPP.append(QApplication.instance() or QApplication([]))
    return _QAPP[0]


@pytest.fixture
def lock(qapp):
    import utils.operation_lock as ol  # noqa: PLC0415

    ol._singleton = None
    yield ol.get_operation_lock()
    ol._singleton = None


@pytest.fixture
def dialogs(monkeypatch):
    """Every message box, recorded as (kind, title, text) instead of shown."""
    from PyQt5.QtWidgets import QMessageBox  # noqa: PLC0415

    shown = []
    for kind in ("information", "warning", "critical"):
        monkeypatch.setattr(
            QMessageBox,
            kind,
            staticmethod(lambda *a, _kind=kind, **k: shown.append((_kind, a[1], a[2]))),
        )
    return shown


@pytest.fixture
def rig(monkeypatch, qapp, lock, dialogs, database_handler, system_controller, fake_relay_handler):
    """main's run and stop as setup() wires them, over a fake relay HAT and
    the test's database: the Run/Stop section and the Animals tab of a
    logged-in trainer who has one animal."""
    from drivers.uart_flow_sensor import TeensyUnavailableError  # noqa: PLC0415
    from models.login_system import LoginSystem  # noqa: PLC0415
    from ui.animals_tab import AnimalsTab  # noqa: PLC0415
    from ui.run_stop_section import RunStopSection  # noqa: PLC0415

    monkeypatch.setattr(sys, "excepthook", sys.excepthook)  # main installs its own on import
    import main  # noqa: PLC0415

    def _no_teensy(_settings):
        raise TeensyUnavailableError("no Teensy on this bench")

    # Calibration-only, as the production rig runs, and at once: a missing
    # serial port would otherwise cost the worker seconds of retries.
    monkeypatch.setattr("drivers.flow_sensor_factory.create_flow_sensor", _no_teensy)

    assert database_handler.add_trainer(TRAINER, PASSWORD)
    login = LoginSystem(database_handler)
    trainer = login.authenticate(TRAINER, PASSWORD)
    animal_id = database_handler.add_animal(
        Animal(lab_animal_id="M-001", name="Basil", sex="female"), trainer['trainer_id']
    )

    stops = []
    threads = []  # each run's QThread, held until it has finished (see _join)

    def _stop():
        """main.stop_program, as the Stop button calls it; its result kept."""
        stops.append(main.stop_program())
        return stops[-1]

    section = RunStopSection(
        main.run_program,
        _stop,
        lambda: None,
        system_controller=system_controller,
        database_handler=database_handler,
        login_system=login,
    )
    tab = AnimalsTab(
        settings={},
        print_to_terminal=lambda *_: None,
        database_handler=database_handler,
        login_system=login,
    )
    monkeypatch.setattr(main, "system_controller", system_controller, raising=False)
    monkeypatch.setattr(main, "database_handler", database_handler, raising=False)
    monkeypatch.setattr(main, "relay_handler", fake_relay_handler, raising=False)
    monkeypatch.setattr(main, "login_system", login, raising=False)
    monkeypatch.setattr(main, "controller", SimpleNamespace(pump_controller=None), raising=False)
    monkeypatch.setattr(main, "notification_handler", None, raising=False)
    gui = SimpleNamespace(
        run_stop_section=section, projects_section=SimpleNamespace(animals_tab=tab)
    )
    monkeypatch.setattr(main, "gui", gui, raising=False)
    monkeypatch.setattr(main, "thread", None)
    monkeypatch.setattr(main, "worker", None)
    # A fresh one: main's module-level instance does not outlive another test
    # module's QApplication.
    monkeypatch.setattr(main, "control_signals", main.ControlSignals())
    monkeypatch.setattr(main, "_dbg", lambda _message: None)  # not the real debug log

    yield SimpleNamespace(
        main=main,
        db=database_handler,
        relays=fake_relay_handler,
        lock=lock,
        dialogs=dialogs,
        section=section,
        tab=tab,
        stops=stops,
        threads=threads,
        trainer_id=trainer['trainer_id'],
        animal_id=animal_id,
    )

    # A failed assertion must not leave a delivery thread running into the
    # next test: stop it as the Stop button would.
    if main.worker is not None or _thread_running(main.thread):
        main.stop_program()
    _join(threads)
    _settle(qapp)


def _thread_running(thread):
    from PyQt5 import sip  # noqa: PLC0415

    return thread is not None and not sip.isdeleted(thread) and thread.isRunning()


def _join(threads):
    """Let go of each run's QThread only once it has finished.

    main.cleanup drops its reference as soon as isRunning() is False, which
    Qt 5 reports while the thread is still finishing. Were that the last
    reference, ~QThread would wait for the thread with the GIL held, while the
    finishing thread waits for the GIL to delete the worker's slot proxies: a
    deadlock. That race is main.cleanup's, not what this test checks, so the
    test holds a reference until wait(), which releases the GIL, returns.
    """
    from PyQt5 import sip  # noqa: PLC0415

    while threads:
        thread = threads.pop()
        if not sip.isdeleted(thread):
            assert thread.wait(TIMEOUT_S * 1000), "the run's thread finished"


def _wait_for(condition, timeout_s=TIMEOUT_S):
    """Process the GUI thread's events until ``condition()`` holds; False if it
    has not within ``timeout_s``. The worker's signals to the GUI thread are
    queued, so the run's record and cleanup happen only while this waits."""
    from PyQt5.QtTest import QTest  # noqa: PLC0415

    deadline = time.monotonic() + timeout_s
    while not condition():
        if time.monotonic() > deadline:
            return False
        QTest.qWait(10)
    return True


def _settle(qapp):
    """Run what is still queued to the GUI thread, then let deleteLater finish
    (worker, thread, slot proxies) before the next test."""
    from PyQt5.QtCore import QEvent  # noqa: PLC0415

    for _ in range(5):
        qapp.processEvents()
    qapp.sendPostedEvents(None, QEvent.DeferredDelete)


def _calibrate(db, q):
    """The cage's calibration as the wizard saves it, at the production pulse
    width and topology, but with a 1 ms rest between pulses."""
    assert db.save_valve_calibration(
        cage_id=CAGE,
        relay_id=CAGE,
        pulse_width_ms=30,
        volume_per_pulse_ml=q,
        stddev_ml=0.0,
        cv_pct=0.0,
        num_samples=30,
        inter_pulse_interval_ms=1,
        topology='shared_manifold',
    )


def _press_run(rig, monkeypatch, schedule, mode, window_start, window_end):
    """Press Run: the job flag, the hardware lock and the start it queues,
    which here goes straight on to main.run_program through the section (the
    schedule checks it skips are test_run_warnings.py's and
    test_calibration_gate.py's). Returns the worker main.run_program started."""
    monkeypatch.setattr(
        rig.section,
        "_prepare_and_execute_schedule",
        lambda _token=None: rig.section._execute_program(
            schedule, mode, window_start.timestamp(), window_end.timestamp()
        ),
    )
    rig.section.schedule_drop_area.current_schedule = schedule
    rig.section.run_program()
    assert _wait_for(lambda: rig.section.run_button.text() != "Starting...")
    assert rig.section.run_button.text() == "Running", rig.dialogs
    rig.threads.append(rig.main.thread)
    return rig.main.worker


def _rows(db, sql, args=()):
    with db.connect() as conn:
        return conn.execute(sql, args).fetchall()


def _last_history_id(db):
    """The newest delivery-log row's history_id; 0 when the log is empty."""
    [(history_id,)] = _rows(db, "SELECT COALESCE(MAX(history_id), 0) FROM dispensing_history")
    return history_id


def _ledger(db, after_id, up_to_id):
    """The delivery-log rows written in between: (status, volume_actual_ml, pulses_fired)."""
    return _rows(
        db,
        "SELECT status, volume_actual_ml, pulses_fired FROM dispensing_history "
        "WHERE history_id > ? AND history_id <= ? ORDER BY history_id",
        (after_id, up_to_id),
    )


def _the_run(db):
    """The one run on record: its schedule_runs row and its animal's
    schedule_run_animals row, as dicts."""
    with db.connect() as conn:
        conn.row_factory = sqlite3.Row
        [run] = conn.execute("SELECT * FROM schedule_runs").fetchall()
        [animal] = conn.execute("SELECT * FROM schedule_run_animals").fetchall()
    return dict(run), dict(animal)


def _stop_rows(db):
    """The Stop's audit rows in the logs table: (super_user_id, details)."""
    return _rows(db, "SELECT super_user_id, details FROM logs WHERE action = 'schedule_stopped'")


def _cell(tab):
    """The animal's "Last schedule delivered amount" cell: (text, red)."""
    from ui.animals_tab import LAST_RUN_ALERT_ROLE  # noqa: PLC0415

    item = tab.animals_table.item(0, tab.LAST_RUN_COLUMN)
    return item.text(), bool(item.data(LAST_RUN_ALERT_ROLE))


def _cage_openings(relays):
    """How often the cage's valve has opened: one per pulse."""
    return relays.trace.count(((CAGE,), 1))


def _opened_after_stop(relays, pressed):
    """The relays switched on after the Stop's first all-off. ``pressed`` is
    the trace's length when Stop was pressed; until the run ends, only the
    stop sequence switches every relay off."""
    writes = relays.trace[pressed:]
    first_off = writes.index((("all",), 0))
    return [write for write in writes[first_off + 1 :] if write[1] == 1]


def test_a_stop_mid_dose_is_recorded_as_the_delivery_log_has_it_and_shows_red(rig, monkeypatch):
    """Staggered 0.6 mL at 0.03 mL per pulse over a 3 s window: about 0.2 mL a
    cycle, each delivery primed and held on the shared manifold, the next
    cycle due before a delivery ends. Stop is pressed once a delivery has been
    credited and the next one has opened the cage valve, so it cuts that one
    short: the record counts its pulses as the delivery log does."""
    from PyQt5.QtTest import QSignalSpy  # noqa: PLC0415

    _calibrate(rig.db, 0.03)
    assert _cell(rig.tab) == (NO_RUN_TEXT, False)
    before = _last_history_id(rig.db)
    animal = str(rig.animal_id)
    schedule = SimpleNamespace(
        name="AM water",
        schedule_id=12,
        water_volume=0.6,
        relay_unit_assignments={animal: CAGE},
        desired_water_outputs={animal: 0.6},
    )
    start = datetime.now()
    end = start + timedelta(seconds=3)
    worker = _press_run(rig, monkeypatch, schedule, "Staggered", start, end)
    credited = QSignalSpy(worker.volume_updated)

    assert credited.wait(TIMEOUT_S * 1000), "a delivery was credited"
    opened = _cage_openings(rig.relays)
    assert _wait_for(lambda: _cage_openings(rig.relays) > opened), "the next delivery pulses"
    pressed = len(rig.relays.trace)
    rig.section.stop_program()
    assert _wait_for(lambda: rig.main.thread is None), "the worker's cleanup ran"
    assert _wait_for(lambda: _cell(rig.tab)[0] != NO_RUN_TEXT), "the Animals tab reloaded"

    [result] = rig.stops
    assert result.safe, result
    assert rig.dialogs == [], "a clean Stop shows no dialog"
    assert rig.lock.is_busy() is False
    # S6: once Stop has switched every relay off, at most one valve opens
    # before the worker sees the cancel. A worker that never sees it pulses on.
    reopened = _opened_after_stop(rig.relays, pressed)
    assert len(reopened) <= 1, f"opened after Stop switched every relay off: {reopened}"

    run, ran = _the_run(rig.db)
    assert run['end_reason'] == 'stopped'
    assert (run['relays_confirmed_off'], run['worker_exited']) == (1, 1)
    assert run['app_version'] == __version__
    assert (run['started_by'], run['stopped_by']) == (rig.trainer_id, rig.trainer_id)

    ledger = _ledger(rig.db, before, _last_history_id(rig.db))
    assert len(ledger) >= 2, "the credited delivery and the one the Stop cut short"
    status, _volume, pulses = ledger[-1]
    assert (status, pulses > 0) == ('partial', True), ledger  # Stop ended it before its target
    delivered = ran['delivered_ml']
    assert delivered == pytest.approx(sum(volume for _, volume, _ in ledger), abs=1e-6)
    assert ran['outcome'] == 'stopped'
    # 0.6 mL is exactly 20 pulses of 0.03, so this is no rounding check (the
    # instant test's 9 pulses for 0.3 mL is).
    assert ran['planned_ml'] == pytest.approx(whole_pulses(0.6, 0.03) * 0.03)
    assert 0 < delivered < ran['planned_ml']
    # The last volume_updated figure (what the Execution Monitor shows), the
    # record and the log agree.
    assert credited[-1] == [animal, pytest.approx(delivered, abs=1e-6)]

    assert _stop_rows(rig.db) == [
        (
            rig.trainer_id,
            f"AM water (schedule 12, run {run['run_id']}) stopped by {TRAINER}: animal "
            f"{rig.animal_id} {delivered:.3f} of 0.600 mL planned. Relays confirmed off: yes; "
            "worker exited: yes",
        )
    ]
    assert _cell(rig.tab) == (f"Stopped · {delivered:.3f} / 0.600 mL", True)
    assert rig.relays.energized() == set(), "every relay is off"
    assert rig.relays.dropped == []


def test_an_instant_run_that_ends_on_its_own_delivers_its_plan_1_to_1(rig, monkeypatch):
    """0.3 mL at the production calibration, due in about a second: the plan
    is 9 whole pulses, 0.307 mL. The valve fires 9, and the record says
    completed with delivered equal to planned; the cell is not red."""
    from PyQt5.QtTest import QSignalSpy  # noqa: PLC0415

    _calibrate(rig.db, Q)
    before = _last_history_id(rig.db)
    due = datetime.now() + timedelta(seconds=1)
    schedule = SimpleNamespace(
        name="PM water",
        schedule_id=13,
        instant_deliveries=[
            {'relay_unit_id': CAGE, 'animal_id': rig.animal_id, 'datetime': due, 'volume': 0.3}
        ],
    )
    worker = _press_run(rig, monkeypatch, schedule, "Instant", due, due)
    finished = QSignalSpy(worker.finished)

    assert finished.wait(TIMEOUT_S * 1000), "the run ended on its own"
    assert _wait_for(lambda: rig.main.thread is None), "the worker's cleanup ran"
    assert _wait_for(lambda: _cell(rig.tab)[0] != NO_RUN_TEXT), "the Animals tab reloaded"

    run, ran = _the_run(rig.db)
    assert (run['delivery_mode'], run['end_reason']) == ('instant', 'completed')
    assert run['started_by'] == rig.trainer_id
    stop_fields = ('stopped_by', 'relays_confirmed_off', 'worker_exited')
    assert [run[field] for field in stop_fields] == [None, None, None], "no Stop"
    assert ran['outcome'] == 'completed'
    assert whole_pulses(0.3, Q) == 9
    assert ran['planned_ml'] == pytest.approx(9 * Q)
    assert ran['delivered_ml'] == ran['planned_ml'], "1:1"
    assert _ledger(rig.db, before, _last_history_id(rig.db)) == [
        ('completed', pytest.approx(9 * Q), 9)
    ]
    assert _cage_openings(rig.relays) == 9

    assert _stop_rows(rig.db) == []
    assert _cell(rig.tab) == ("0.307 mL", False)
    assert rig.relays.energized() == set(), "every relay is off"
    assert rig.stops == [] and rig.dialogs == []
    assert rig.lock.is_busy() is False
