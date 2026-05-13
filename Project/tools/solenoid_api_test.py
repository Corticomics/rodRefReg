from __future__ import annotations

import argparse
import os
import sys
import time


def _append_project_to_syspath() -> None:
    here = os.path.abspath(os.path.dirname(__file__))
    project_root = os.path.abspath(os.path.join(here, os.pardir))
    if project_root not in sys.path:
        sys.path.append(project_root)


_append_project_to_syspath()


from drivers.solenoid_controller import SolenoidController  # noqa: E402
from gpio.gpio_handler import RelayHandler  # noqa: E402
from models.relay_unit_manager import RelayUnitManager  # noqa: E402


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Simple solenoid API smoke test using SolenoidController."
    )
    parser.add_argument(
        "--relay",
        type=int,
        default=1,
        help="Relay ID to use (used as both master and cage 1). Default: 1",
    )
    parser.add_argument(
        "--duration",
        type=float,
        default=0.5,
        help="Seconds to hold valve open in tests. Default: 0.5",
    )
    parser.add_argument(
        "--num-hats",
        type=int,
        default=1,
        help="Number of stacked relay HATs. Default: 1",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Log actions only; do not command hardware",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()

    # Minimal setup for RelayHandler
    manager = RelayUnitManager({"num_hats": args.num_hats})
    relay_handler = RelayHandler(manager, args.num_hats)

    # Use the same relay as both master and cage 1 for a single-valve bench test
    controller = SolenoidController(
        relay_handler,
        master_relay_id=args.relay,
        cage_to_relay_id={1: args.relay},
    )

    def log(step: str, ok: bool) -> None:
        print(f"[api-test] {step}: {'OK' if ok else 'FAIL'}")

    try:
        if args.dry_run:
            print("[api-test] DRY RUN: no hardware commands will be sent")

        # 1) open/close master
        ok = True if args.dry_run else controller.open_master()
        log("open_master()", ok)
        time.sleep(args.duration)
        ok = True if args.dry_run else controller.close_master()
        log("close_master()", ok)

        # 2) open/close cage 1
        ok = True if args.dry_run else controller.open_cage(1)
        log("open_cage(1)", ok)
        time.sleep(args.duration)
        ok = True if args.dry_run else controller.close_cage(1)
        log("close_cage(1)", ok)

        # 3) sequence master + cage
        ok = True if args.dry_run else controller.open_master()
        log("open_master()", ok)
        time.sleep(0.1)
        ok = True if args.dry_run else controller.open_cage(1)
        log("open_cage(1)", ok)
        time.sleep(args.duration)
        ok = True if args.dry_run else controller.close_cage(1)
        log("close_cage(1)", ok)
        time.sleep(0.1)
        ok = True if args.dry_run else controller.close_master()
        log("close_master()", ok)

        # 4) close all cages and check state helper
        ok = True if args.dry_run else controller.close_all_cages()
        log("close_all_cages()", ok)
        log("all_closed()", controller.all_closed())

        print("[api-test] Completed.")
        return 0
    except Exception as exc:
        print(f"[api-test] ERROR: {exc}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())


