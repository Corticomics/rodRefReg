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


class RelayControlModel(QObject):
    """
    Model for relay state management.

    Responsibilities:
    - Track master and cage relay states
    - Provide thread-safe state access
    - Emit signals on state changes

    Best Practices:
    - Single Responsibility Principle
    - Observer pattern via Qt signals
    - Encapsulated state management
    """

    master_state_changed = pyqtSignal(bool)  # True = open, False = closed
    cage_state_changed = pyqtSignal(int, bool)  # cage_id, is_open

    def __init__(self):
        super().__init__()
        self._master_open: bool = False
        self._open_cages: Set[int] = set()

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
        self.set_master_open(False)
        self.close_all_cages()


class PrimingControlWidget(QWidget):
    """
    Standalone widget for manual relay control and tube priming.

    Features:
    - Master solenoid control
    - Individual cage relay control
    - Safety interlocks (master must be open before cages)
    - Visual state indicators
    - Emergency stop functionality
    - Activity logging

    Usage:
        settings = system_controller.settings
        priming_widget = PrimingControlWidget(settings, print_callback)
        layout.addWidget(priming_widget)
    """

    # Signals for parent widget integration
    status_message = pyqtSignal(str)  # For logging to parent terminal

    def __init__(self, settings: Dict, print_callback=None):
        """
        Initialize priming control widget.

        Args:
            settings: System settings dictionary from SystemController
            print_callback: Optional callback for status messages (e.g., print_to_terminal)
        """
        super().__init__()

        # Store settings and callback
        self.settings = settings
        self._print_callback = print_callback or (lambda x: None)

        # Initialize model
        self._model = RelayControlModel()

        # Hardware controllers (lazy initialization)
        self._relay_handler = None
        self._solenoid_controller = None

        # Setup UI
        self._init_ui()

        # Connect model signals to UI updates
        self._model.master_state_changed.connect(self._on_master_state_changed)
        self._model.cage_state_changed.connect(self._on_cage_state_changed)

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
        return group

    def _create_cage_control_group(self) -> QGroupBox:
        """Create cage relay control group."""
        group = QGroupBox("Cage Relay Control")
        layout = QVBoxLayout()

        # Info label
        info = QLabel("Select a cage relay to control. Master must be open first.")
        info.setObjectName("HelpText")
        layout.addWidget(info)

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

    def _get_relay_handler(self):
        """Lazy initialization of relay handler (Dependency Injection pattern)."""
        if self._relay_handler is None:
            try:
                from gpio.gpio_handler import RelayHandler
                from models.relay_unit_manager import RelayUnitManager

                manager = RelayUnitManager(self.settings)
                num_hats = self.settings.get('num_hats', 1)
                self._relay_handler = RelayHandler(manager, num_hats)

            except Exception as e:
                self._log_error(f"Failed to initialize relay handler: {e}")
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
                from drivers.solenoid_controller import SolenoidController

                relay_handler = self._get_relay_handler()
                if not relay_handler:
                    return None

                master_id = self.settings.get('global_master_relay_id', 16)
                cage_map = self._build_cage_map()

                self._solenoid_controller = SolenoidController(relay_handler, master_id, cage_map)

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

    # ==================== Event Handlers ====================

    def _on_open_master_clicked(self):
        """Handle master open button click."""
        try:
            controller = self._get_solenoid_controller()
            if not controller:
                return

            if controller.open_master():
                self._model.set_master_open(True)
                self._log_success("Master solenoid OPENED")
            else:
                QMessageBox.warning(
                    self,
                    "Hardware Error",
                    "Failed to open master solenoid. Check hardware connections.",
                )

        except Exception as e:
            self._log_error(f"Error opening master: {e}")
            QMessageBox.critical(self, "Error", f"Failed to open master:\n{str(e)}")

    def _on_close_master_clicked(self):
        """Handle master close button click."""
        try:
            controller = self._get_solenoid_controller()
            if not controller:
                return

            # Close all cages first (safety)
            if self._model.get_open_cages():
                controller.close_all_cages()
                self._model.close_all_cages()

            if controller.close_master():
                self._model.set_master_open(False)
                self._log_success("Master solenoid CLOSED, all cages closed")
            else:
                QMessageBox.warning(self, "Hardware Error", "Failed to close master solenoid.")

        except Exception as e:
            self._log_error(f"Error closing master: {e}")
            QMessageBox.critical(self, "Error", f"Failed to close master:\n{str(e)}")

    def _on_open_cage_clicked(self):
        """Handle cage open button click."""
        try:
            if not self._model.is_master_open:
                QMessageBox.warning(
                    self,
                    "Safety Interlock",
                    "Master solenoid must be open before opening cage relays.",
                )
                return

            controller = self._get_solenoid_controller()
            if not controller:
                return

            cage_id = self._get_selected_cage_id()
            if cage_id is None:
                return

            if controller.open_cage(cage_id):
                self._model.set_cage_open(cage_id, True)
                cage_text = self.cage_selector.currentText()
                self._log_success(f"OPENED: {cage_text}")
            else:
                QMessageBox.warning(
                    self, "Hardware Error", f"Failed to open {self.cage_selector.currentText()}."
                )

        except Exception as e:
            self._log_error(f"Error opening cage: {e}")
            QMessageBox.critical(self, "Error", f"Failed to open cage:\n{str(e)}")

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
            else:
                QMessageBox.warning(
                    self, "Hardware Error", f"Failed to close {self.cage_selector.currentText()}."
                )

        except Exception as e:
            self._log_error(f"Error closing cage: {e}")
            QMessageBox.critical(self, "Error", f"Failed to close cage:\n{str(e)}")

    def _on_emergency_stop_clicked(self):
        """Handle emergency stop button click."""
        try:
            relay_handler = self._get_relay_handler()
            if not relay_handler:
                return

            # Direct hardware call for fastest response
            relay_handler.set_all_relays(0)

            # Reset model state
            self._model.reset()

            self._log_warning("⛔ EMERGENCY STOP - All relays closed")
            QMessageBox.information(self, "Emergency Stop", "All relays have been closed.")

        except Exception as e:
            self._log_error(f"Emergency stop error: {e}")
            QMessageBox.critical(
                self,
                "Critical Error",
                f"Emergency stop failed:\n{str(e)}\n\n" "Manually disconnect power if necessary!",
            )

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
            self.master_open_btn.setEnabled(True)
            self.master_close_btn.setEnabled(False)

        self._update_cage_button_states()

    def _on_cage_state_changed(self, cage_id: int, is_open: bool):
        """Handle cage state changes from model."""
        self._update_cage_button_states()

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
        """Update cage control button states based on current state."""
        has_selection = self.cage_selector.count() > 0
        master_is_open = self._model.is_master_open

        self.cage_open_btn.setEnabled(master_is_open and has_selection)
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
                self._relay_handler.set_all_relays(0)

            self._model.reset()
            self._print_callback("Priming control widget cleaned up")

        except Exception as e:
            self._print_callback(f"Cleanup error: {e}")
