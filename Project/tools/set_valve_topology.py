"""Show or set a device's valve topology.

    RRR_DATA=~/rrr/shared/data python3 tools/set_valve_topology.py               # show
    RRR_DATA=~/rrr/shared/data python3 tools/set_valve_topology.py independent   # set
    RRR_DATA=~/rrr/shared/data python3 tools/set_valve_topology.py shared_manifold

Writes through SystemController.save_settings, so the value is stored with
the same typing and in the same table the app reads at start-up. Run it with
the app closed and restart the app afterwards; the topology is read when the
hardware is set up, not while a schedule is running.

`independent` means one syringe and one solenoid per animal and no master
valve: the app will never drive the master relay. On a rig that still has a
master valve, that means no water. `shared_manifold` is the production rig
(master valve on the relay named by global_master_relay_id, default 16).
"""

from __future__ import annotations

import argparse
import os
import sys


def _append_project_to_syspath() -> None:
    here = os.path.abspath(os.path.dirname(__file__))
    project_root = os.path.abspath(os.path.join(here, os.pardir))
    if project_root not in sys.path:
        sys.path.append(project_root)


_append_project_to_syspath()

from utils.topology import SETTING_KEY, TOPOLOGIES, topology_from  # noqa: E402


def _controller():
    from controllers.system_controller import SystemController  # noqa: PLC0415
    from models.database_handler import DatabaseHandler  # noqa: PLC0415

    return SystemController(DatabaseHandler())


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument(
        'topology',
        nargs='?',
        choices=TOPOLOGIES,
        help="topology to set; omit to show the current value",
    )
    args = parser.parse_args(argv)

    controller = _controller()
    current = topology_from(controller.settings)
    print(f"current {SETTING_KEY}: {current}")
    if args.topology is None:
        return 0
    if args.topology == current:
        print("no change")
        return 0

    controller.save_settings({SETTING_KEY: args.topology})
    stored = topology_from(_controller().settings)
    if stored != args.topology:
        print(f"ERROR: {SETTING_KEY} did not persist (read back {stored!r})", file=sys.stderr)
        return 1
    print(f"{SETTING_KEY} set to: {stored}")
    print("Restart the app for the change to take effect.")
    return 0


if __name__ == '__main__':
    sys.exit(main())
