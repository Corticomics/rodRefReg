"""
Priming Control Widget for RRR
================================

Modular, reusable widget for manual relay control and tube priming.

Architecture:
- Follows MVC pattern (Model-View-Controller)
- Encapsulates all priming logic in a standalone widget
- Can be imported and used in any parent widget
- Thread-safe relay operations
- Comprehensive error handling and user feedback

Author: RRR Development Team
Date: 2025-10-16
"""

from datetime import datetime
from typing import Dict, Optional, Set

from PyQt5.QtCore import QObject, pyqtSignal
from PyQt5.QtWidgets import (
    QComboBox,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
    QWidget,
)
from utils.operation_lock import (
    CALIBRATION,
    EMERGENCY,
    PRIMING,
    SCHEDULE,
    get_operation_lock,
)
from utils.topology import INDEPENDENT, SETTING_KEY, SHARED_MANIFOLD, is_independent


class RelayControlModel(QObject):
    """
    Model for relay state management.

    Responsibilities:
    - Track master and cage relay states
    - Provide thread-safe state access
    - Emit signals on state changes

    On a topology without a master valve (one syringe and valve per animal)
    the "master" is permanently open as far as the interlocks are concerned:
    there is nothing upstream of a cage valve to open first.

    Best Practices:
    - Single Responsibility Principle
    - Observer pattern via Qt signals
    - Encapsulated state management
    """

    master_state_changed = pyqtSignal(bool)  # True = open, False = closed
    cage_state_changed = pyqtSignal(int, bool)  # cage_id, is_open

    def __init__(self, has_master: bool = True):
        super().__init__()
        self._has_master = has_master
        self._master_open: bool = not has_master
        self._open_cages: Set[int] = set()

    @property
    def has_master(self) -> bool:
        return self._has_master

    def master_closed(self) -> None:
        """The master is closed — or, without one, stays virtually open."""
        self.set_master_open(not self._has_master)

    @property
    def is_master_open(self) -> bool:
        """Thread-safe master state getter."""
        return self._master_open

    def set_master_open(self, is_open: bool) -> None:
        """Update master state and emit signal."""
        if self._master_open != is_open:
            self._master_open = is_open
            self.master_state_changed.emit(is_open)

    def set_cage_open(self, cage_id: int, is_open: bool) -> None:
        """Update cage state and emit signal."""
        if is_open:
            self._open_cages.add(cage_id)
        else:
            self._open_cages.discard(cage_id)
        self.cage_state_changed.emit(cage_id, is_open)

    def is_cage_open(self, cage_id: int) -> bool:
        """Check if specific cage is open."""
        return cage_id in self._open_cages

    def close_all_cages(self) -> None:
        """Close all cages and emit signals."""
        for cage_id in list(self._open_cages):
            self.set_cage_open(cage_id, False)

    def get_open_cages(self) -> Set[int]:
        """Get set of currently open cage IDs."""
        return self._open_cages.copy()

    def reset(self) -> None:
        """Reset all states to closed."""
        self.master_closed()
        self.close_all_cages()


class PrimingControlWidget(QWidget):
    """
    Standalone widget for manual relay control and tube priming.

    Features:
    - Master solenoid control (shared-manifold topology only)
    - Individual cage relay control
    - Safety interlocks (master must be open before cages, where a master exists)
    - Visual state indicators
    - Emergency stop functionality
    - Activity logging

    Valve topology: on the independent topology (one syringe and valve per
    animal, ``valve_topology = independent``) the master group is hidden, a
    cage valve is primed directly, and the PRIMING operation lock is held
    from the first cage valve opened until the last one is closed.

    Usage:
        settings = system_controller.settings
        priming_widget = PrimingControlWidget(settings, print_callback)
        layout.addWidget(priming_widget)
    """

    # Signals for parent widget integration
    status_message = pyqtSignal(str)  # For logging to parent terminal

    def __init__(self, settings: Dict, print_callback=None, stop_schedule=None):
        """
        Initialize priming control widget.

        Args:
            settings: System settings dictionary from SystemController
            print_callback: Optional callback for status messages (e.g., print_to_terminal)
            stop_schedule: Optional callable that stops a running schedule the
                way the Stop button does and returns True if one was running.
                CLOSE ALL RELAYS calls it: a schedule left running opens its
                valves again at its next pulse.
        """
        super().__init__()

        # Store settings and callback
        self.settings = settings
        self._print_callback = print_callback or (lambda x: None)
        self._stop_schedule = stop_schedule

        # Valve topology: on the independent topology there is no master
        # valve, so the master controls are hidden, a cage valve is primed
        # directly, and the priming lock follows the cage valves instead.
        self._independent = is_independent(settings)

        # Initialize model
        self._model = RelayControlModel(has_master=not self._independent)

        # Hardware controllers (lazy initialization)
        self._relay_handler = None
        self._solenoid_controller = None

        # Setup UI
        self._init_ui()

        # Connect model signals to UI updates
        self._model.master_state_changed.connect(self._on_master_state_changed)
        self._model.cage_state_changed.connect(self._on_cage_state_changed)

        # Grey out the Open controls when another hardware operation (schedule
        # or calibration) holds the lock; refresh on every lock state change.
        get_operation_lock().state_changed.connect(self._refresh_lock_state)
        self._refresh_lock_state()

    def _init_ui(self):
        """Initialize user interface following Material Design principles."""
        layout = QVBoxLayout(self)
        layout.setSpacing(16)

        # Warning banner
        layout.addWidget(self._create_warning_banner())

        # Master control section
        layout.addWidget(self._create_master_control_group())

        # Cage control section
        layout.addWidget(self._create_cage_control_group())

        # Emergency controls
        layout.addWidget(self._create_emergency_group())

        # Note: Activity log removed - all messages now go to main Terminal tab
        # via the print_callback and status_message signal

        # Push everything to top
        layout.addStretch()

    def _create_warning_banner(self) -> QWidget:
        """Create safety warning banner."""
        warning_label = QLabel(
            "⚠️ <b>Manual Control Mode</b><br>"
            "Use this panel to prime tubes and test hardware.<br>"
            "Ensure water reservoir is connected before opening valves."
        )
        warning_label.setProperty("variant", "warning")
        warning_label.setWordWrap(True)
        return warning_label

    def _create_master_control_group(self) -> QGroupBox:
        """Create master solenoid control group."""
        group = QGroupBox("Master Solenoid Control")
        layout = QVBoxLayout()

        # Status indicator
        self.master_status_label = QLabel("Status: CLOSED")
        self.master_status_label.setObjectName("StatusLabel")
        self.master_status_label.setProperty("status", "closed")
        layout.addWidget(self.master_status_label)

        # Control buttons
        btn_layout = QHBoxLayout()

        self.master_open_btn = QPushButton("Open Master")
        self.master_open_btn.setProperty("variant", "primary")
        self.master_open_btn.clicked.connect(self._on_open_master_clicked)
        btn_layout.addWidget(self.master_open_btn)

        self.master_close_btn = QPushButton("Close Master")
        self.master_close_btn.setProperty("variant", "danger")
        self.master_close_btn.clicked.connect(self._on_close_master_clicked)
        self.master_close_btn.setEnabled(False)
        btn_layout.addWidget(self.master_close_btn)

        layout.addLayout(btn_layout)
        group.setLayout(layout)
        # No master valve on the independent topology: the group stays built
        # (its handlers and labels are wired throughout) but is never shown.
        self.master_group = group
        if self._independent:
            group.hide()
        return group

    def _create_cage_control_group(self) -> QGroupBox:
        """Create cage relay control group."""
        group = QGroupBox("Cage Relay Control")
        layout = QVBoxLayout()

        # Info label
        if self._independent:
            info_text = (
                "Select a cage valve to control. This device has no master valve: "
                "opening a cage valve primes that animal's line directly."
            )
        else:
            info_text = "Select a cage relay to control. Master must be open first."
        info = QLabel(info_text)
        info.setObjectName("HelpText")
        info.setWordWrap(True)
        layout.addWidget(info)
        self.cage_info_label = info

        if self._independent:
            advisory = QLabel(
                "Check every syringe line daily. A primed line holds for about three "
                "days, so a line left idle over a long weekend must be primed again "
                "before its animal depends on it."
            )
            advisory.setProperty("variant", "warning")
            advisory.setWordWrap(True)
            layout.addWidget(advisory)
            self.daily_check_label = advisory

        # Selector and controls
        control_layout = QHBoxLayout()

        self.cage_selector = QComboBox()
        self.cage_selector.setMinimumWidth(200)
        self.cage_selector.currentIndexChanged.connect(self._update_cage_button_states)
        control_layout.addWidget(QLabel("Cage:"))
        control_layout.addWidget(self.cage_selector)

        self.cage_open_btn = QPushButton("Open Selected")
        self.cage_open_btn.setProperty("variant", "primary")
        self.cage_open_btn.clicked.connect(self._on_open_cage_clicked)
        self.cage_open_btn.setEnabled(False)
        control_layout.addWidget(self.cage_open_btn)

        self.cage_close_btn = QPushButton("Close Selected")
        self.cage_close_btn.clicked.connect(self._on_close_cage_clicked)
        self.cage_close_btn.setEnabled(False)
        control_layout.addWidget(self.cage_close_btn)

        layout.addLayout(control_layout)

        # Populate cage selector
        self._populate_cage_selector()

        group.setLayout(layout)
        return group

    def _create_emergency_group(self) -> QGroupBox:
        """Create emergency controls group."""
        group = QGroupBox("Emergency Controls")
        layout = QHBoxLayout()

        self.emergency_btn = QPushButton("⛔ CLOSE ALL RELAYS")
        self.emergency_btn.setProperty("variant", "danger")
        self.emergency_btn.clicked.connect(self._on_emergency_stop_clicked)
        layout.addWidget(self.emergency_btn)
        layout.addStretch()

        group.setLayout(layout)
        return group

    # ==================== Hardware Control Methods ====================

    def _get_relay_handler(self, quiet=False):
        """Lazy initialization of relay handler (Dependency Injection pattern).

        ``quiet`` skips the error dialog: the emergency stop must not wait
        behind one before it stops the schedule.
        """
        if self._relay_handler is None:
            try:
                from gpio.gpio_handler import RelayHandler
                from models.relay_unit_manager import RelayUnitManager

                manager = RelayUnitManager(self.settings)
                num_hats = self.settings.get('num_hats', 1)
                self._relay_handler = RelayHandler(manager, num_hats)

            except Exception as e:
                self._log_error(f"Failed to initialize relay handler: {e}")
                if quiet:
                    return None
                QMessageBox.critical(
                    self,
                    "Hardware Error",
                    f"Failed to initialize relay hardware:\n{str(e)}\n\n"
                    "Ensure relay HAT is properly connected.",
                )
                return None

        return self._relay_handler

    def _get_solenoid_controller(self):
        """Lazy initialization of solenoid controller."""
        if self._solenoid_controller is None:
            try:
                from utils.topology import build_solenoid_controller

                relay_handler = self._get_relay_handler()
                if not relay_handler:
                    return None

                cage_map = self._build_cage_map()

                # The device's valve topology decides whether a master valve
                # exists. On the independent topology the master group is
                # hidden, the controller's master operations are no-ops and
                # the cage buttons drive the valves directly. The topology is
                # the one this panel was built for, not the live setting: a
                # Close after a change in Settings must not build (and keep)
                # a controller for the other topology, which Open would use
                # once the change is undone.
                built_for = INDEPENDENT if self._independent else SHARED_MANIFOLD
                self._solenoid_controller = build_solenoid_controller(
                    relay_handler, {**self.settings, SETTING_KEY: built_for}, cage_map
                )

            except Exception as e:
                self._log_error(f"Failed to initialize solenoid controller: {e}")
                QMessageBox.critical(
                    self,
                    "Controller Error",
                    f"Failed to initialize solenoid controller:\n{str(e)}",
                )
                return None

        return self._solenoid_controller

    def _build_cage_map(self) -> Dict[int, int]:
        """Build cage-to-relay mapping from settings."""
        cage_map = self.settings.get('cage_relays', {})

        if not cage_map:
            # Build default sequential map
            num_hats = self.settings.get('num_hats', 1)
            master_id = self.settings.get('global_master_relay_id', 16)
            total_relays = 16 * num_hats

            cage_map = {}
            cage_id = 1
            for relay_id in range(1, total_relays + 1):
                if relay_id != master_id:
                    cage_map[cage_id] = relay_id
                    cage_id += 1

        # Ensure keys are integers
        return {int(k): int(v) for k, v in cage_map.items()}

    # ==================== Topology changed in Settings ====================

    _RESTART_TOOLTIP = "Restart RRR to prime with the new valve topology"

    def _topology_changed_since_start(self) -> bool:
        """Whether the valve topology in Settings differs from the one this
        panel was built for. The layout, the valve-state model and the lock
        rules all follow the topology at construction, so opening a valve
        under the other one waits for a restart. Closing never does."""
        return is_independent(self.settings) != self._independent

    def refresh_topology_state(self) -> None:
        """Re-apply the Open states after Settings changes the topology."""
        self._refresh_lock_state()

    def _refused_until_restart(self) -> bool:
        if not self._topology_changed_since_start():
            return False
        QMessageBox.information(
            self,
            "Restart required",
            "The valve topology was changed in Settings. Close and reopen RRR "
            "to prime with it.\n\nClosing valves and the emergency stop still work.",
        )
        return True

    # ==================== Event Handlers ====================

    def _on_open_master_clicked(self):
        """Handle master open button click."""
        if self._refused_until_restart():
            return
        # Hardware mutual-exclusion: priming holds the lock for the whole
        # session (master open → all closed), since the master valve is shared
        # with schedules and calibration. Acquire before opening anything.
        lock = get_operation_lock()
        if not lock.try_acquire(PRIMING):
            QMessageBox.warning(
                self,
                "Hardware busy",
                f"Cannot prime while {lock.active_label()} is in progress.",
            )
            return
        # On a failure the lock is released only if nothing is open: after a
        # Close Master that left a cage valve unconfirmed, the session (and
        # the lock) must go on until that valve is closed.
        try:
            controller = self._get_solenoid_controller()
            if not controller:
                self._release_if_idle()
                return

            if controller.open_master():
                self._model.set_master_open(True)
                self._log_success("Master solenoid OPENED")
            else:
                self._release_if_idle()
                QMessageBox.warning(
                    self,
                    "Hardware Error",
                    "Failed to open master solenoid. Check hardware connections.",
                )

        except Exception as e:
            self._release_if_idle()
            self._log_error(f"Error opening master: {e}")
            QMessageBox.critical(self, "Error", f"Failed to open master:\n{str(e)}")

    def _on_close_master_clicked(self):
        """Handle master close button click."""
        try:
            controller = self._get_solenoid_controller()
            if not controller:
                return

            # Close the cages this panel opened first (safety). One by one,
            # so a missing second HAT does not fail the close of a cage on
            # the first, and a cage that did not close is named.
            unclosed = []
            for cage in sorted(self._model.get_open_cages()):
                if controller.close_cage(cage):
                    self._model.set_cage_open(cage, False)
                else:
                    unclosed.append(cage)

            # The master closes even if a cage did not: on the shared
            # manifold it is what cuts the supply to a cage valve left open.
            master_closed = controller.close_master()
            if master_closed:
                self._model.master_closed()
            if unclosed:
                # A valve may still be open: the priming session (and the
                # hardware lock) goes on until CLOSE ALL RELAYS.
                cages = ", ".join(str(cage) for cage in unclosed)
                supply = (
                    "The master was closed to cut their supply."
                    if master_closed
                    else "The master did not close either."
                )
                self._log_error(f"Cage valve(s) {cages} did not confirm closed")
                QMessageBox.warning(
                    self,
                    "Hardware Error",
                    f"Cage valve(s) {cages} did not confirm closed (a relay did not "
                    f"switch). {supply}\n\nUse CLOSE ALL RELAYS, and cut the valve power "
                    "if water still flows.",
                )
                return
            if master_closed:
                # All valves closed — end the priming session, release the lock.
                get_operation_lock().release(PRIMING)
                self._log_success("Master solenoid CLOSED, all cages closed")
            else:
                QMessageBox.warning(self, "Hardware Error", "Failed to close master solenoid.")

        except Exception as e:
            self._log_error(f"Error closing master: {e}")
            QMessageBox.critical(self, "Error", f"Failed to close master:\n{str(e)}")

    def _on_open_cage_clicked(self):
        """Handle cage open button click."""
        if self._refused_until_restart():
            return
        try:
            if not self._model.is_master_open:
                QMessageBox.warning(
                    self,
                    "Safety Interlock",
                    "Master solenoid must be open before opening cage relays.",
                )
                return

            cage_id = self._get_selected_cage_id()
            if cage_id is None:
                return

            # Without a master valve the priming session starts with the
            # first cage valve opened, so the hardware lock is taken here
            # (the shared topology takes it on Open Master).
            lock = get_operation_lock()
            if self._independent and not lock.held_by(PRIMING):
                if not lock.try_acquire(PRIMING):
                    QMessageBox.warning(
                        self,
                        "Hardware busy",
                        f"Cannot prime while {lock.active_label()} is in progress.",
                    )
                    return

            controller = self._get_solenoid_controller()
            if not controller:
                self._release_if_idle()
                return

            if controller.open_cage(cage_id):
                self._model.set_cage_open(cage_id, True)
                cage_text = self.cage_selector.currentText()
                self._log_success(f"OPENED: {cage_text}")
            else:
                self._release_if_idle()
                QMessageBox.warning(
                    self, "Hardware Error", f"Failed to open {self.cage_selector.currentText()}."
                )

        except Exception as e:
            self._release_if_idle()
            self._log_error(f"Error opening cage: {e}")
            QMessageBox.critical(self, "Error", f"Failed to open cage:\n{str(e)}")

    def _release_if_idle(self) -> None:
        """The session ends when no cage valve is open and, where there is a
        master, it is closed. On the shared manifold that is normally Close
        Master's job; this covers a cage that did not confirm closed then
        and is closed afterwards."""
        if self._model.get_open_cages():
            return
        if self._independent or not self._model.is_master_open:
            get_operation_lock().release(PRIMING)

    def _on_close_cage_clicked(self):
        """Handle cage close button click."""
        try:
            controller = self._get_solenoid_controller()
            if not controller:
                return

            cage_id = self._get_selected_cage_id()
            if cage_id is None:
                return

            if controller.close_cage(cage_id):
                self._model.set_cage_open(cage_id, False)
                cage_text = self.cage_selector.currentText()
                self._log_success(f"CLOSED: {cage_text}")
                self._release_if_idle()
            else:
                QMessageBox.warning(
                    self, "Hardware Error", f"Failed to close {self.cage_selector.currentText()}."
                )

        except Exception as e:
            self._log_error(f"Error closing cage: {e}")
            QMessageBox.critical(self, "Error", f"Failed to close cage:\n{str(e)}")

    def _on_emergency_stop_clicked(self):
        """Handle emergency stop button click.

        Switches every relay off, stops a running schedule (left running, it
        would open its valves again at its next pulse), then switches the
        relays off once more. The operation lock is cleared only when every
        relay is confirmed off and nothing that can open a valve is still
        running. Otherwise whoever holds it keeps it, and when nobody does
        the panel takes it (EMERGENCY): nothing can start onto a valve that
        may be open until a later press is confirmed or RRR is restarted.
        """
        try:
            # Built without a dialog: a panel that cannot reach the relays
            # must still stop the schedule, which has a handler of its own.
            relay_handler = self._get_relay_handler(quiet=True)

            # Direct hardware call for fastest response
            all_off = self._all_relays_off(relay_handler)

            schedule_stopped = self._stop_running_schedule()
            if schedule_stopped:
                # The schedule may have pulsed once more before it stopped.
                all_off = self._all_relays_off(relay_handler)
            still_running = self._delivery_may_be_running()
            lock = get_operation_lock()

            if not all_off:
                # A HAT missing or not answering: its relays are in an
                # unknown state, which only cutting the power settles. The
                # panel keeps showing what may be open, and the hardware
                # stays locked.
                self._hold_until_safe(lock)
                self._log_error("⛔ EMERGENCY STOP - relays NOT confirmed off")
                if schedule_stopped and still_running:
                    schedule_note = (
                        "\n\nThe schedule was told to stop, but its delivery worker has not "
                        "finished."
                    )
                elif schedule_stopped:
                    schedule_note = "\n\nThe running schedule was stopped."
                else:
                    schedule_note = ""
                if lock.held_by(PRIMING):
                    locked_note = (
                        "The priming session stays open, so Run and calibration stay unavailable."
                    )
                else:
                    locked_note = (
                        "Run, priming and calibration stay unavailable until every relay is "
                        "confirmed off."
                    )
                QMessageBox.critical(
                    self,
                    "Emergency Stop Failed",
                    "Not every relay HAT confirmed the command, so a valve may still be "
                    "OPEN.\n\nDisconnect the valve power supply now, then check the relay "
                    f"HAT and its I²C connection.{schedule_note}\n\n{locked_note} Once the "
                    "relay HAT answers, press CLOSE ALL RELAYS again; or close and reopen RRR.",
                )
                return

            # Every relay is confirmed off.
            self._model.reset()

            if still_running:
                self._hold_until_safe(lock)
                if schedule_stopped:
                    # The Stop path released the schedule's hold although its
                    # worker thread did not exit (it abandons one that will
                    # not die). That worker can fire one more pulse.
                    self._log_error(
                        "⛔ EMERGENCY STOP - All relays closed; the delivery worker has not stopped"
                    )
                    QMessageBox.critical(
                        self,
                        "Emergency Stop",
                        "All relays have been closed, but the schedule's delivery worker has "
                        "not stopped and may pulse a valve once more.\n\nWait a few seconds "
                        "and press CLOSE ALL RELAYS again. If this message comes back, "
                        "disconnect the valve power supply and restart the Raspberry Pi.",
                    )
                else:
                    # Nothing here could stop it: its hold on the hardware stays.
                    self._log_warning(
                        "⛔ EMERGENCY STOP - All relays closed; a schedule is still running"
                    )
                    QMessageBox.warning(
                        self,
                        "Emergency Stop",
                        "All relays have been closed, but a schedule is still running and will "
                        "open its valves again.\n\nPress Stop to end it.",
                    )
                return

            if lock.held_by(CALIBRATION):
                # Not known to be stale. The wizard is modal, so this button
                # should be out of reach while a calibration pulses; a hold
                # seen here means that guarantee failed, and freeing it would
                # let a schedule start beside a run that may still be live.
                self._log_warning(
                    "⛔ EMERGENCY STOP - All relays closed; a calibration holds the hardware"
                )
                QMessageBox.warning(
                    self,
                    "Emergency Stop",
                    "All relays have been closed, but a calibration holds the hardware and "
                    "may still be pulsing.\n\nClose the calibration window. If none is open, "
                    "close and reopen RRR.",
                )
                return

            # The failsafe for a hold nothing is using: the priming session
            # is over, a running schedule has just been stopped and its
            # worker is gone, and an earlier unconfirmed stop is now confirmed.
            lock.force_release()
            self._log_warning(
                "⛔ EMERGENCY STOP - All relays closed"
                + ("; the running schedule was stopped" if schedule_stopped else "")
            )
            QMessageBox.information(
                self,
                "Emergency Stop",
                "All relays have been closed."
                + (
                    " The running schedule was stopped.\n\nAnimals it had not yet watered "
                    "get no water until Run is pressed again."
                    if schedule_stopped
                    else ""
                ),
            )

        except Exception as e:
            self._log_error(f"Emergency stop error: {e}")
            QMessageBox.critical(
                self,
                "Critical Error",
                f"Emergency stop failed:\n{str(e)}\n\n" "Manually disconnect power if necessary!",
            )

    def _all_relays_off(self, relay_handler) -> bool:
        """Switch every relay off. False unless every relay HAT confirmed it:
        no handler, a HAT that did not answer and a command that raised all
        leave a valve possibly open. Never raises."""
        if relay_handler is None:
            return False
        try:
            return relay_handler.set_all_relays(0) is not False
        except Exception as exc:
            self._log_error(f"Emergency stop: the all-relays-off command failed: {exc}")
            return False

    @staticmethod
    def _hold_until_safe(lock) -> None:
        """Keep the hardware locked. Whoever holds the lock keeps it; a free
        lock is taken for the emergency stop itself."""
        if not lock.is_busy():
            lock.try_acquire(EMERGENCY)

    def _stop_running_schedule(self) -> bool:
        """Stop a running schedule through the callback Settings provides.

        True if one was running. Never raises: the relays are already off,
        and the rest of the emergency stop must still run.
        """
        if self._stop_schedule is None:
            return False
        try:
            return bool(self._stop_schedule())
        except Exception as exc:
            self._log_error(f"Emergency stop could not stop the schedule: {exc}")
            return False

    def _delivery_may_be_running(self) -> bool:
        """Whether a schedule's delivery worker may still open a valve.

        The worker thread itself decides, whoever holds the lock: the Stop
        path releases the schedule's hold even when its worker did not exit.
        A panel with no way to stop a schedule assumes one that holds the
        lock is live.
        """
        if self._stop_schedule is None:
            return get_operation_lock().held_by(SCHEDULE)
        from utils import updater  # noqa: PLC0415

        return updater.is_busy()

    # ==================== Model Event Handlers ====================

    def _on_master_state_changed(self, is_open: bool):
        """Handle master state changes from model."""
        if is_open:
            self.master_status_label.setText("Status: OPEN [OK]")
            self.master_status_label.setProperty("status", "open")
            self.master_status_label.style().unpolish(self.master_status_label)
            self.master_status_label.style().polish(self.master_status_label)
            self.master_open_btn.setEnabled(False)
            self.master_close_btn.setEnabled(True)
        else:
            self.master_status_label.setText("Status: CLOSED")
            self.master_status_label.setProperty("status", "closed")
            self.master_status_label.style().unpolish(self.master_status_label)
            self.master_status_label.style().polish(self.master_status_label)
            self.master_open_btn.setEnabled(not self._topology_changed_since_start())
            self.master_close_btn.setEnabled(False)

        self._update_cage_button_states()

    def _on_cage_state_changed(self, cage_id: int, is_open: bool):
        """Handle cage state changes from model."""
        self._update_cage_button_states()

    def _refresh_lock_state(self):
        """Grey out the Open controls while another hardware operation (a
        schedule run or calibration) holds the operation lock; restore the
        normal valve/selection-driven state otherwise.

        Close + Emergency are intentionally left to their normal logic so the
        operator can always shut valves. The Phase-1 guard still refuses on
        click regardless — this is purely the visual layer.

        A topology change in Settings greys Open out until restart, whatever
        the lock does, so it is checked first.
        """
        if self._topology_changed_since_start():
            for button in (self.master_open_btn, self.cage_open_btn):
                button.setEnabled(False)
                button.setToolTip(self._RESTART_TOOLTIP)
            return
        lock = get_operation_lock()
        if lock.is_busy() and not lock.held_by(PRIMING):
            tip = f"Unavailable while {lock.active_label()} is in progress"
            self.master_open_btn.setEnabled(False)
            self.master_open_btn.setToolTip(tip)
            self.cage_open_btn.setEnabled(False)
            self.cage_open_btn.setToolTip(tip)
        else:
            # Restore enable state from the current valve/selection state.
            self._on_master_state_changed(self._model.is_master_open)
            self.master_open_btn.setToolTip("")
            self.cage_open_btn.setToolTip("")

    # ==================== UI Helper Methods ====================

    def _populate_cage_selector(self):
        """Populate cage selector with available cages."""
        try:
            self.cage_selector.clear()
            cage_map = self._build_cage_map()

            for cage_id, relay_id in sorted(cage_map.items()):
                self.cage_selector.addItem(f"Cage {cage_id} (Relay {relay_id})", cage_id)

        except Exception as e:
            self._log_error(f"Error populating cage selector: {e}")

    def _get_selected_cage_id(self) -> Optional[int]:
        """Get currently selected cage ID."""
        return self.cage_selector.currentData()

    def _update_cage_button_states(self):
        """Update cage control button states based on current state.

        Open also stays greyed while another hardware operation holds the
        lock. On the independent topology the (virtual) master is open from
        construction, so without this a cage-selector change during a
        schedule run would re-enable Open under an "Unavailable" tooltip.
        The shared path is unchanged: there an open master already means
        PRIMING holds the lock. A topology change in Settings keeps Open
        greyed until restart.
        """
        has_selection = self.cage_selector.count() > 0
        master_is_open = self._model.is_master_open
        lock = get_operation_lock()
        blocked = lock.is_busy() and not lock.held_by(PRIMING)
        blocked = blocked or self._topology_changed_since_start()

        self.cage_open_btn.setEnabled(master_is_open and has_selection and not blocked)
        self.cage_close_btn.setEnabled(has_selection)

    # ==================== Logging Methods ====================

    def _log_message(self, message: str, level: str = "INFO"):
        """Log message to main terminal via callback and signal."""
        timestamp = datetime.now().strftime("%H:%M:%S")
        log_entry = f"[Priming {timestamp}] {message}"

        # Emit signal for parent widget (e.g., main GUI terminal)
        self.status_message.emit(log_entry)

        # Call print callback if provided (logs to Terminal tab)
        self._print_callback(log_entry)

    def _log_success(self, message: str):
        """Log success message."""
        self._log_message(f"[OK] {message}", "SUCCESS")

    def _log_error(self, message: str):
        """Log error message."""
        self._log_message(f"[X] {message}", "ERROR")

    def _log_warning(self, message: str):
        """Log warning message."""
        self._log_message(f"⚠ {message}", "WARNING")

    # ==================== Public API ====================

    def cleanup(self):
        """Cleanup method to be called when widget is destroyed."""
        try:
            # Close all relays on cleanup for safety
            if self._relay_handler:
                if self._relay_handler.set_all_relays(0) is False:
                    self._print_callback(
                        "[X] Priming cleanup: relays NOT confirmed off; a valve may still be open"
                    )

            self._model.reset()
            self._print_callback("Priming control widget cleaned up")

        except Exception as e:
            self._print_callback(f"Cleanup error: {e}")
