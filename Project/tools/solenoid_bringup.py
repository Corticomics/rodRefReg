from __future__ import annotations

import argparse
import os
import signal
import sys
import time
from typing import Dict


def _append_project_to_syspath() -> None:
    """Ensure the `Project` package is importable when running this script directly.

    This avoids requiring users to set PYTHONPATH. No effect if already importable.
    """
    here = os.path.abspath(os.path.dirname(__file__))
    project_root = os.path.abspath(os.path.join(here, os.pardir))
    if project_root not in sys.path:
        sys.path.append(project_root)


_append_project_to_syspath()


from drivers.solenoid_controller import SolenoidController  # noqa: E402
from gpio.gpio_handler import RelayHandler  # noqa: E402
from models.relay_unit_manager import RelayUnitManager  # noqa: E402


def parse_cage_map(expr: str) -> Dict[int, int]:
    """Parse cage map expression like "1:1,2:2,3:3" into a dict.

    Keys are cage IDs, values are relay IDs (1..16 per HAT).
    """
    if not expr:
        return {}
    mapping: Dict[int, int] = {}
    for part in expr.split(","):
        if not part.strip():
            continue
        try:
            cage_str, relay_str = part.split(":", 1)
            cage_id = int(cage_str.strip())
            relay_id = int(relay_str.strip())
        except Exception as exc:
            raise argparse.ArgumentTypeError(
                f"Invalid mapping entry '{part}'. Expected 'cage:relay'"
            ) from exc
        if cage_id in mapping:
            raise argparse.ArgumentTypeError(f"Duplicate cage_id {cage_id} in mapping")
        mapping[cage_id] = relay_id
    return mapping


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Hardware bring-up: exercise master + cage solenoid relays via Sequent Microsystems HAT.\n"
            "Requires a safe wiring setup and correct valve coil voltage supply."
        )
    )
    parser.add_argument(
        "--mode",
        choices=["health", "functionality", "sequence"],
        default="sequence",
        help=(
            "Test mode: 'health' = energize one relay only; 'functionality' = cycle "
            "cage relay N times; 'sequence' = master→cage→hold→off (default)."
        ),
    )
    parser.add_argument(
        "--num-hats",
        type=int,
        default=1,
        help="Number of Sequent relay HATs stacked (default: 1)",
    )
    parser.add_argument(
        "--master",
        type=int,
        default=16,
        help="Relay ID used as master shutoff (default: 16)",
    )
    parser.add_argument(
        "--no-master",
        action="store_true",
        help="Skip master relay operations (use when you have no master valve).",
    )
    parser.add_argument(
        "--cage-map",
        type=parse_cage_map,
        default=parse_cage_map("1:1,2:2,3:3,4:4,5:5,6:6,7:7,8:8"),
        help=("Cage to relay mapping like '1:1,2:2,...'. Only the selected cage is exercised."),
    )
    parser.add_argument(
        "--cage",
        type=int,
        default=1,
        help="Cage ID to exercise from cage-map (default: 1)",
    )
    parser.add_argument(
        "--relay",
        type=int,
        default=None,
        help=("Direct relay ID to energize (bypasses cage-map) for health/functionality tests."),
    )
    parser.add_argument(
        "--duration",
        type=float,
        default=1.0,
        help="Seconds to keep the cage valve open (default: 1.0)",
    )
    parser.add_argument(
        "--interval",
        type=float,
        default=0.25,
        help="Seconds between state transitions (default: 0.25)",
    )
    parser.add_argument(
        "--cycles",
        type=int,
        default=5,
        help="Number of on/off cycles for functionality mode (default: 5)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Do not command hardware; only log the intended actions",
    )
    parser.add_argument(
        "--yes",
        action="store_true",
        help=(
            "Confirm you have verified wiring, valve voltage, and power supplies."
            " Required to run without interactivity."
        ),
    )
    return parser


class Bringup:
    def __init__(
        self,
        *,
        num_hats: int,
        master_relay_id: int,
        cage_to_relay: Dict[int, int],
        cage_id: int,
        mode: str,
        no_master: bool,
        relay_id: int | None,
        duration_s: float,
        interval_s: float,
        cycles: int,
        dry_run: bool,
    ) -> None:
        self.num_hats = num_hats
        self.master_relay_id = int(master_relay_id)
        self.cage_to_relay = {int(k): int(v) for k, v in cage_to_relay.items()}
        self.cage_id = int(cage_id)
        self.mode = str(mode)
        self.no_master = bool(no_master)
        self.relay_id = int(relay_id) if relay_id is not None else None
        self.duration_s = float(duration_s)
        self.interval_s = float(interval_s)
        self.cycles = int(cycles)
        self.dry_run = bool(dry_run)
        self._relay_handler: RelayHandler | None = None
        self._controller: SolenoidController | None = None

    def _init_controller(self) -> None:
        # Minimal settings; RelayUnitManager provides default pairs when missing.
        settings = {"num_hats": self.num_hats}
        manager = RelayUnitManager(settings)
        self._relay_handler = RelayHandler(manager, self.num_hats)
        self._controller = SolenoidController(
            self._relay_handler, self.master_relay_id, self.cage_to_relay
        )

    def _log(self, msg: str) -> None:
        print(f"[bringup] {msg}")

    def _set_state(self, action: str) -> bool:
        assert self._controller is not None
        if action == "open_master":
            self._log(f"open master relay {self.master_relay_id}")
            return True if self.dry_run else self._controller.open_master()
        if action == "close_master":
            self._log(f"close master relay {self.master_relay_id}")
            return True if self.dry_run else self._controller.close_master()
        if action == "open_cage":
            relay = self.cage_to_relay.get(self.cage_id)
            self._log(f"open cage {self.cage_id} (relay {relay})")
            return True if self.dry_run else self._controller.open_cage(self.cage_id)
        if action == "close_cage":
            relay = self.cage_to_relay.get(self.cage_id)
            self._log(f"close cage {self.cage_id} (relay {relay})")
            return True if self.dry_run else self._controller.close_cage(self.cage_id)
        raise ValueError(f"Unknown action {action}")

    def _cleanup(self) -> None:
        try:
            # Best-effort close in reverse order; tolerate missing master.
            self._close_cage_direct()
            time.sleep(self.interval_s)
            if not self.no_master:
                self._set_state("close_master")
        finally:
            self._log("Cleanup complete.")

    def _target_relay(self) -> int:
        if self.relay_id is not None:
            return self.relay_id
        relay = self.cage_to_relay.get(self.cage_id)
        if relay is None:
            raise ValueError(f"No relay mapping for cage {self.cage_id}")
        return relay

    def _open_cage_direct(self) -> bool:
        assert self._relay_handler is not None
        relay = self._target_relay()
        self._log(f"set relay {relay} ON")
        return True if self.dry_run else self._relay_handler.set_relays([relay], 1)

    def _close_cage_direct(self) -> bool:
        assert self._relay_handler is not None
        relay = self._target_relay()
        self._log(f"set relay {relay} OFF")
        return True if self.dry_run else self._relay_handler.set_relays([relay], 0)

    def run_health(self) -> int:
        """Health check: energize a single relay (no master)."""
        self._init_controller()
        self._log("Health check: energize a single relay only.")
        signal.signal(signal.SIGINT, lambda *_: self._cleanup())
        signal.signal(signal.SIGTERM, lambda *_: self._cleanup())
        try:
            if not self._open_cage_direct():
                self._log("Failed to energize relay")
                return 2
            time.sleep(self.duration_s)
            if not self._close_cage_direct():
                self._log("Failed to de-energize relay")
                return 3
            self._log("Health check finished successfully.")
            return 0
        finally:
            self._cleanup()

    def run_functionality(self) -> int:
        """Functionality test: cycle the relay N times; optional master open/close once."""
        self._init_controller()
        self._log(
            f"Functionality test: cycles={self.cycles}, on={self.duration_s}s, off={self.interval_s}s"
        )
        signal.signal(signal.SIGINT, lambda *_: self._cleanup())
        signal.signal(signal.SIGTERM, lambda *_: self._cleanup())
        try:
            if not self.no_master:
                if not self._set_state("open_master"):
                    self._log("Failed to open master relay")
                    return 2
                time.sleep(self.interval_s)
            for i in range(self.cycles):
                self._log(f"Cycle {i + 1}/{self.cycles}")
                if not self._open_cage_direct():
                    self._log("Failed to energize relay")
                    return 3
                time.sleep(self.duration_s)
                if not self._close_cage_direct():
                    self._log("Failed to de-energize relay")
                    return 4
                time.sleep(self.interval_s)
            if not self.no_master:
                if not self._set_state("close_master"):
                    self._log("Failed to close master relay")
                    return 5
            self._log("Functionality test finished successfully.")
            return 0
        finally:
            self._cleanup()

    def run_sequence(self) -> int:
        self._init_controller()
        self._log("Starting sequence: master→cage→hold→cage off→master off.")

        def _cleanup(_sig=None, _frame=None):
            try:
                self._set_state("close_cage")
                time.sleep(self.interval_s)
                self._set_state("close_master")
            finally:
                self._log("Cleanup complete.")

        signal.signal(signal.SIGINT, _cleanup)
        signal.signal(signal.SIGTERM, _cleanup)

        try:
            if not self.no_master and not self._set_state("open_master"):
                self._log("Failed to open master relay")
                return 2
            time.sleep(self.interval_s)

            if not self._set_state("open_cage"):
                self._log("Failed to open cage relay")
                return 3

            time.sleep(self.duration_s)

            if not self._set_state("close_cage"):
                self._log("Failed to close cage relay")
                return 4
            time.sleep(self.interval_s)

            if not self.no_master and not self._set_state("close_master"):
                self._log("Failed to close master relay")
                return 5

            self._log("Sequence finished successfully.")
            return 0
        finally:
            _cleanup()

    def run(self) -> int:
        if self.mode == "health":
            return self.run_health()
        if self.mode == "functionality":
            return self.run_functionality()
        return self.run_sequence()


def main(argv: list[str] | None = None) -> int:
    parser = build_arg_parser()
    args = parser.parse_args(argv)

    # Safety gate: require explicit confirmation
    if not args.yes:
        parser.error("You must pass --yes to confirm wiring and power were verified.")

    if args.relay is None and args.cage not in args.cage_map:
        parser.error(f"--cage {args.cage} not present in --cage-map {args.cage_map}")

    bringup = Bringup(
        num_hats=args.num_hats,
        master_relay_id=args.master,
        cage_to_relay=args.cage_map,
        cage_id=args.cage,
        mode=args.mode,
        no_master=args.no_master,
        relay_id=args.relay,
        duration_s=args.duration,
        interval_s=args.interval,
        cycles=args.cycles,
        dry_run=args.dry_run,
    )
    return bringup.run()


if __name__ == "__main__":
    raise SystemExit(main())
