"""Show or set a device's valve topology.

On an installed device, with the app closed (its window, or
``systemctl --user stop rrr.service`` where it runs as the user service):

    cd ~/rrr/current/Project
    ~/rrr/shared/venv/bin/python3 tools/set_valve_topology.py                    # show
    ~/rrr/shared/venv/bin/python3 tools/set_valve_topology.py independent --yes  # set
    ~/rrr/shared/venv/bin/python3 tools/set_valve_topology.py shared_manifold

then start the app again (its desktop icon, or ``systemctl --user start
rrr.service``).

The device database lives under ``RRR_DATA`` (the launcher exports
``~/rrr/shared/data``). This tool uses that directory when the variable is
set, falls back to ``~/rrr/shared/data`` when it exists, and otherwise
refuses to run — pass ``--data-dir`` to point it elsewhere. It never creates
a database: if there is none at the resolved path it stops and says so.

Writes go through SystemController.save_settings, so the value is stored
with the same typing and in the same table the app reads at start-up. Close
the app first: a running app writes its whole in-memory settings back on
every auto-save and would overwrite the value. The tool refuses to write
while it can see the app: the rrr.service user unit active, or an RRR
``main.py`` process found through /proc (the desktop icon starts the app
outside the service, so asking systemd alone is not enough). The topology
is read when the hardware is set up, so the app must be restarted
afterwards.

``independent`` means one syringe and one solenoid per animal and no master
valve: the app will never drive the master relay. On a rig that still has a
master valve that means NO WATER while every delivery is logged as a full
dose — which is why setting it needs ``--yes``. ``shared_manifold`` is the
production rig (master valve on the relay named by global_master_relay_id,
default 16).
"""

from __future__ import annotations

import argparse
import os
import subprocess
import sys


def _append_project_to_syspath() -> None:
    here = os.path.abspath(os.path.dirname(__file__))
    project_root = os.path.abspath(os.path.join(here, os.pardir))
    if project_root not in sys.path:
        sys.path.append(project_root)


_append_project_to_syspath()

from utils.topology import (  # noqa: E402
    INDEPENDENT,
    SETTING_KEY,
    TOPOLOGIES,
    describe,
    topology_from,
)

DEFAULT_DATA_DIR = os.path.expanduser('~/rrr/shared/data')
SERVICE = 'rrr.service'


def _say(message: str) -> None:
    print(message, flush=True)


def _fail(message: str) -> int:
    print(f"ERROR: {message}", file=sys.stderr, flush=True)
    return 2


def _resolve_data_dir(explicit: str | None) -> str | None:
    """The data directory to act on, or None when it cannot be determined safely."""
    if explicit:
        os.environ['RRR_DATA'] = os.path.abspath(os.path.expanduser(explicit))
    elif not os.environ.get('RRR_DATA') and os.path.isdir(DEFAULT_DATA_DIR):
        os.environ['RRR_DATA'] = DEFAULT_DATA_DIR
    root = os.environ.get('RRR_DATA')
    if not root or not os.path.isdir(root):
        return None
    return root


def _is_rrr_project(directory: str) -> bool:
    """Whether ``directory`` is an RRR ``Project`` tree (a release or a clone)."""
    return os.path.isfile(os.path.join(directory, 'version.py')) and os.path.isfile(
        os.path.join(directory, 'gpio', 'relay_worker.py')
    )


# How /proc/<pid>/cwd reads when the directory was removed under the process.
_DELETED_SUFFIX = ' (deleted)'


def _app_processes(proc_root: str = '/proc') -> list[int] | None:
    """
    PIDs of running RRR app processes, or None when there is no /proc.

    The launcher (scripts/runtime/launch.sh) changes into the release's
    Project directory and runs ``python3 main.py``, whether the desktop
    icon or the systemd unit started it, so the app is a Python process with
    a ``main.py`` argument that resolves into an RRR Project tree (an editor
    or pager open on main.py is not). Processes that cannot be read
    (another user's, or gone mid-scan) are skipped.

    When the release directory was replaced under a running app (an
    installer re-run at the same version), the kernel shows its working
    directory as '<path> (deleted)'. The original path is checked instead,
    and if it no longer holds a Project tree but still names one, the
    process is counted anyway: reading a running app as stopped is the
    dangerous mistake.
    """
    if not os.path.isdir(proc_root):
        return None
    found = []
    me = str(os.getpid())
    for entry in os.listdir(proc_root):
        if not entry.isdigit() or entry == me:
            continue
        base = os.path.join(proc_root, entry)
        try:
            with open(os.path.join(base, 'cmdline'), 'rb') as handle:
                argv = [arg.decode(errors='replace') for arg in handle.read().split(b'\0') if arg]
            cwd = os.readlink(os.path.join(base, 'cwd'))
        except OSError:
            continue
        if not argv or not os.path.basename(argv[0]).lower().startswith('python'):
            continue
        deleted = cwd.endswith(_DELETED_SUFFIX)
        if deleted:
            cwd = cwd[: -len(_DELETED_SUFFIX)]
        for arg in argv[1:]:
            if os.path.basename(arg) != 'main.py':
                continue
            project = os.path.dirname(os.path.join(cwd, arg))
            if _is_rrr_project(project) or (deleted and os.path.basename(project) == 'Project'):
                found.append(int(entry))
                break
    return sorted(found)


def _unit_state() -> tuple[bool | None, str]:
    """
    Is the app's user service active? Returns (state, detail).

    ``state`` is True when it is running, False when systemd says it is
    not, and None when that could not be determined — no systemctl, a
    shell without a session bus ("Failed to connect to bus"), a timeout.
    """
    try:
        result = subprocess.run(
            ['systemctl', '--user', 'is-active', SERVICE],
            capture_output=True,
            text=True,
            timeout=5,
        )
    except (OSError, subprocess.SubprocessError) as exc:
        return None, f"systemctl unavailable ({exc.__class__.__name__}: {exc})"
    detail = (result.stdout + result.stderr).strip()
    if result.returncode == 0:
        return True, detail
    # systemctl is-active: 3 = inactive/failed, 4 = no such unit (newer systemd).
    if result.returncode in (3, 4):
        return False, detail
    return None, detail or f"systemctl exited {result.returncode}"


def _app_running() -> tuple[bool | None, str]:
    """
    Is the app running, however it was started? Returns (state, detail).

    True when the user unit is active or an RRR app process is found;
    False when /proc was scanned and holds none (systemd's answer, which
    only covers the service, cannot turn that into "running"); None only
    when there is no /proc and systemd could not answer. An unknown state
    must not be read as "stopped": a running app writes its whole settings
    back on its next auto-save.
    """
    unit, unit_detail = _unit_state()
    if unit:
        return True, f"{SERVICE} is active"
    pids = _app_processes()
    if pids:
        return True, "RRR app process running (pid " + ", ".join(map(str, pids)) + ")"
    if pids is None:
        return unit, unit_detail
    return False, unit_detail or "no RRR app process"


def _controller():
    from controllers.system_controller import SystemController  # noqa: PLC0415
    from models.database_handler import DatabaseHandler  # noqa: PLC0415

    controller = SystemController(DatabaseHandler())
    controller.system_status.connect(lambda m: print(f"  [app] {m}", file=sys.stderr, flush=True))
    return controller


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument(
        'topology',
        nargs='?',
        choices=TOPOLOGIES,
        help="topology to set; omit to show the current value",
    )
    parser.add_argument(
        '--data-dir',
        help="device data directory holding rrr_database.db (default: $RRR_DATA, "
        "else ~/rrr/shared/data)",
    )
    parser.add_argument(
        '--yes',
        action='store_true',
        help="confirm setting 'independent' (no master valve will ever be driven)",
    )
    parser.add_argument(
        '--force',
        action='store_true',
        help="write even if the app service appears to be running",
    )
    args = parser.parse_args(argv)

    root = _resolve_data_dir(args.data_dir)
    if root is None:
        configured = os.environ.get('RRR_DATA')
        if configured:
            return _fail(
                f"the data directory {configured!r} (from --data-dir or RRR_DATA) is not a "
                "directory."
            )
        return _fail(
            "cannot find the device data directory: RRR_DATA is not set and "
            f"{DEFAULT_DATA_DIR} does not exist. Pass --data-dir PATH."
        )
    db_path = os.path.join(root, 'rrr_database.db')
    if not os.path.isfile(db_path):
        return _fail(f"no database at {db_path}; this tool never creates one.")
    _say(f"database: {db_path}")

    if args.topology == INDEPENDENT and not args.yes:
        return _fail(
            "setting 'independent' means the app will never drive the master relay. "
            "On a rig that still has a master valve that is NO WATER, logged as full "
            "doses. Re-run with --yes to confirm."
        )
    if args.topology is not None and not args.force:
        running, detail = _app_running()
        if running:
            return _fail(
                f"the app is running ({detail}) and would overwrite the value when it next "
                "saves its settings. Close it first (its window, or "
                f"systemctl --user stop {SERVICE} if it runs as the service), or pass --force."
            )
        if running is None:
            return _fail(
                f"could not determine whether the app is running ({detail}). "
                "Run this on the device itself, or pass --force if you are sure the app "
                "is closed."
            )

    controller = _controller()
    current = topology_from(controller.settings)
    _say(f"current {SETTING_KEY}: {current} — {describe(current)}")
    if args.topology is None:
        return 0
    if args.topology == current:
        _say("no change")
        return 0

    controller.save_settings({SETTING_KEY: args.topology})
    stored = topology_from(_controller().settings)
    if stored != args.topology:
        return _fail(f"{SETTING_KEY} did not persist (read back {stored!r}).")
    _say(f"{SETTING_KEY} set to: {stored} — {describe(stored)}")
    _say(
        "Start the app for the change to take effect (its desktop icon, or "
        f"systemctl --user start {SERVICE})."
    )
    return 0


if __name__ == '__main__':
    sys.exit(main())
