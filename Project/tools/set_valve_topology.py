"""Show or set a device's valve topology.

On an installed device (the app runs as the user unit ``rrr.service``):

    systemctl --user stop rrr.service
    cd ~/rrr/current/Project
    ~/rrr/shared/venv/bin/python3 tools/set_valve_topology.py                    # show
    ~/rrr/shared/venv/bin/python3 tools/set_valve_topology.py independent --yes  # set
    ~/rrr/shared/venv/bin/python3 tools/set_valve_topology.py shared_manifold
    systemctl --user start rrr.service

The device database lives under ``RRR_DATA`` (the launcher exports
``~/rrr/shared/data``). This tool uses that directory when the variable is
set, falls back to ``~/rrr/shared/data`` when it exists, and otherwise
refuses to run — pass ``--data-dir`` to point it elsewhere. It never creates
a database: if there is none at the resolved path it stops and says so.

Writes go through SystemController.save_settings, so the value is stored
with the same typing and in the same table the app reads at start-up. Stop
the app first: a running app writes its whole in-memory settings back on
every auto-save and would overwrite the value. The topology is read when
the hardware is set up, so the app must be restarted afterwards.

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


def _app_running() -> bool:
    """Best effort: is the app's user service active on this device?"""
    try:
        result = subprocess.run(
            ['systemctl', '--user', 'is-active', SERVICE],
            capture_output=True,
            text=True,
            timeout=5,
        )
    except (OSError, subprocess.SubprocessError):
        return False
    return result.returncode == 0


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
    if args.topology is not None and not args.force and _app_running():
        return _fail(
            f"{SERVICE} is running and would overwrite the value on its next auto-save. "
            f"Stop it first (systemctl --user stop {SERVICE}) or pass --force."
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
    _say(f"Start the app for the change to take effect (systemctl --user start {SERVICE}).")
    return 0


if __name__ == '__main__':
    sys.exit(main())
