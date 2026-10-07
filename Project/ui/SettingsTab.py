import csv
import json
from datetime import datetime

import pandas as pd
from models.animal import Animal
from PyQt5.QtCore import Qt, QTimer, pyqtSignal
from PyQt5.QtWidgets import (
    QApplication,
    QButtonGroup,
    QCheckBox,
    QComboBox,
    QDialog,
    QFileDialog,
    QFormLayout,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QRadioButton,
    QTableWidgetItem,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)
from utils import updater
from utils.calibration_gate import calibration_is_usable, gate_applies
from utils.operation_lock import CALIBRATION, get_operation_lock
from utils.topology import (
    DEFAULT_MASTER_RELAY_ID,
    INDEPENDENT,
    SETTING_KEY,
    SHARED_MANIFOLD,
    calibration_is_stale,
    calibration_label,
    calibration_topology,
    describe,
    is_known,
    normalize,
    topology_from,
)

from ui.PrimingControlWidget import PrimingControlWidget
from ui.UpdatesTab import UpdatesTab
from ui.widgets.safe_spinbox import SafeDoubleSpinBox, SafeSpinBox


def _as_number(value):
    """A stored number as a float, or None when it is missing or not a number."""
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _format_number(value, template):
    """Format a stored number for the calibration table and report; "—" if missing."""
    number = _as_number(value)
    return "—" if number is None else template.format(number)


class SettingsTab(QWidget):
    settings_updated = pyqtSignal(dict)

    def __init__(
        self,
        system_controller,
        suggest_callback=None,
        push_callback=None,
        save_slack_callback=None,
        run_stop_section=None,
        login_system=None,
        print_to_terminal=None,
        database_handler=None,
        notification_handler=None,
    ):
        super().__init__()

        if not system_controller:
            raise ValueError("system_controller is required")

        self.system_controller = system_controller
        self.settings = system_controller.settings
        self.suggest_callback = suggest_callback
        self.push_callback = push_callback
        self.save_slack_callback = save_slack_callback
        self.run_stop_section = run_stop_section
        self.login_system = login_system
        self.print_to_terminal = print_to_terminal or (lambda x: None)
        # Drives the Slack Integration indicator (Phase 3 offline-resilience).
        self.notification_handler = notification_handler

        # Get database handler from system controller if not provided
        self.database_handler = database_handler or system_controller.database_handler

        if not self.database_handler:
            raise ValueError(
                "database_handler must be provided either directly or through system_controller"
            )

        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)

        # Create tab widget for settings
        self.tab_widget = QTabWidget()

        # Create and add settings sub-tabs
        self.hardware_pump_settings = self._create_hardware_pump_settings()  # MERGED
        self.calibration_tab = self._create_calibration_tab()  # NEW
        self.priming_control = self._create_priming_control()
        self.general_tab = self._create_general_tab()
        self.updates_tab = UpdatesTab()

        # Add sub-tabs to settings
        # Note: Cage management moved to Projects Section (CagesVisualizationTab)
        self.tab_widget.addTab(self.hardware_pump_settings, "Delivery")
        self.tab_widget.addTab(self.calibration_tab, "Calibration")
        self.tab_widget.addTab(self.priming_control, "Priming")
        self.tab_widget.addTab(self.general_tab, "General")
        self.tab_widget.addTab(self.updates_tab, "Updates")

        layout.addWidget(self.tab_widget)

        # Update mode state when General tab is selected
        self.tab_widget.currentChanged.connect(self._on_subtab_changed)

        # Connect all settings widgets to auto-save (Best Practice: immediate persistence)
        self._connect_auto_save_handlers()

    def showEvent(self, event):
        """Update mode button state when Settings tab becomes visible."""
        super().showEvent(event)
        # Refresh mode state in case login status changed
        if hasattr(self, '_update_mode_button_state'):
            self._update_mode_button_state()
        self._apply_hardware_settings_lock_state()

    def _on_subtab_changed(self, index: int):
        """Handle settings sub-tab changes."""
        # If General tab is selected (index 3), refresh mode state
        if index == 3 and hasattr(self, '_update_mode_button_state'):
            self._update_mode_button_state()
        if self.tab_widget.widget(index) is self.hardware_pump_settings:
            self._apply_hardware_settings_lock_state()

    def refresh_calibration_table(self) -> None:
        """
        Public method to refresh the calibration table.

        Called when cage names change in the Cages tab and when the hat
        count changes (main.change_relay_hats), so the rows follow the
        device's cage map without a restart.
        """
        if hasattr(self, 'calibration_table'):
            self._populate_calibration_table()
            self.print_to_terminal("Calibration table refreshed")

    def _cage_map(self) -> dict:
        """
        The device's cage map for the calibration views.

        A stored map that cannot be read (only reachable by hand-editing
        the database) must not take the Settings tab, and with it the whole
        main window, down at boot: fall back to the sequential layout for
        the hat count and say so, as the neighbouring database reads do.
        """
        from utils.topology import cage_map_from

        try:
            return cage_map_from(self.settings)
        except (TypeError, ValueError) as exc:
            self.print_to_terminal(
                f"Stored cage map is unreadable ({exc}); showing the default layout"
            )
            layout = {
                key: self.settings[key]
                for key in ('num_hats', 'global_master_relay_id')
                if self.settings.get(key) is not None
            }
            return cage_map_from(layout)

    def _connect_auto_save_handlers(self):
        """
        Connect all settings widgets to auto-save on change.

        Best Practices:
        - Immediate persistence (no manual "Save" button needed)
        - Debounced saves to prevent excessive I/O
        - User expectations: changes persist immediately like modern apps
        """
        # Hardware mode (already has handler, but we'll enhance it)
        # Theme (already has handler)
        # Log level (already has handler, but we'll enhance it)

        # Solenoid settings
        self.teensy_port_edit.editingFinished.connect(self._auto_save_settings)
        self.flow_sensor_optional.stateChanged.connect(self._auto_save_settings)
        self.flow_sampling_hz.valueChanged.connect(self._auto_save_settings)
        self.max_valve_open_s.valueChanged.connect(self._auto_save_settings)
        self.no_flow_timeout_s.valueChanged.connect(self._auto_save_settings)
        self.predictive_close_ms.valueChanged.connect(self._auto_save_settings)
        self.use_pulse_delivery.stateChanged.connect(self._auto_save_settings)
        self.pulse_width_ms.valueChanged.connect(self._auto_save_settings)
        self.round_doses_up.stateChanged.connect(self._auto_save_settings)

        # Pump settings
        self.pump_volume.valueChanged.connect(self._auto_save_settings)
        self.calibration_factor.valueChanged.connect(self._auto_save_settings)
        self.min_triggers.valueChanged.connect(self._auto_save_settings)

        # Slack settings (when they exist)
        if hasattr(self, 'slack_token'):
            self.slack_token.editingFinished.connect(self._auto_save_settings)
        if hasattr(self, 'slack_channel'):
            self.slack_channel.editingFinished.connect(self._auto_save_settings)

    def _auto_save_settings(self):
        """
        Auto-save all settings to disk when any widget changes.

        This provides immediate persistence without requiring a "Save" button.
        Settings are validated and persisted via SystemController.
        """
        if not self.login_system or not self.login_system.is_logged_in():
            # Silently skip auto-save if not logged in
            return

        try:
            # Build updated settings dictionary from UI widgets
            updated_settings = {
                # Hardware mode
                'hardware_mode': self.hardware_mode_combo.currentData() or 'solenoid',
                # Theme (if exists)
                'theme': self.theme_combo.currentText()
                if hasattr(self, 'theme_combo')
                else self.settings.get('theme', 'light'),
                # Solenoid settings
                'uart_port': self.teensy_port_edit.text(),
                'flow_sensor_optional': self.flow_sensor_optional.isChecked(),
                'flow_sampling_hz': self.flow_sampling_hz.value(),
                'max_valve_open_s': self.max_valve_open_s.value(),
                'no_flow_timeout_s': self.no_flow_timeout_s.value(),
                'predictive_close_ms': self.predictive_close_ms.value(),
                'use_pulse_delivery': self.use_pulse_delivery.isChecked(),
                'pulse_width_ms': self.pulse_width_ms.value(),
                'round_doses_up': self.round_doses_up.isChecked(),
                # Pump settings
                'pump_volume_ul': self.pump_volume.value(),
                'calibration_factor': self.calibration_factor.value(),
                'min_triggers': self.min_triggers.value(),
                # System
                'log_level': self.log_level.value() if hasattr(self, 'log_level') else 2,
            }
            # Slack credentials, stored as entered: SystemController keeps
            # them in the mode-0600 secrets.json. Only when their fields
            # exist, so a save can never blank credentials it did not show.
            if hasattr(self, 'slack_token'):
                updated_settings['slack_token'] = self.slack_token.text()
            if hasattr(self, 'slack_channel'):
                updated_settings['channel_id'] = self.slack_channel.text()

            credentials = ('slack_token', 'channel_id')
            before = tuple(self.settings.get(key) for key in credentials)

            # Update settings via system controller (ensures persistence)
            self.settings.update(updated_settings)
            self.system_controller.save_settings(self.settings)

            # The running NotificationHandler was built with the credentials
            # at start-up; point it at the new ones so Slack uses them now.
            after = tuple(self.settings.get(key) for key in credentials)
            handler = self.notification_handler
            if after != before and hasattr(handler, 'update_credentials'):
                handler.update_credentials(*after)
                self._refresh_slack_status()
                self.print_to_terminal("Slack credentials updated; the next message uses them")

            # Emit signal for other components
            self.settings_updated.emit(self.settings)

            # Optional: provide subtle feedback (no annoying popups)
            self.print_to_terminal(f"Settings auto-saved")

        except Exception as e:
            self.print_to_terminal(f"Auto-save failed: {e}")
            # Don't show error dialog - auto-save failures should be silent

    def _create_hardware_pump_settings(self):
        """
        MERGED: Hardware + Pump settings in one tab

        Best Practices:
        - Single Responsibility: One place for all delivery hardware config
        - Progressive Disclosure: Show only relevant settings per mode
        - Safety: Prevent mode switching during active schedule
        """
        widget = QWidget()
        layout = QVBoxLayout()
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(12)

        # ==================== MODE SELECTION ====================
        # Two-column card: a compact selector on the left, the explanatory
        # bullets filling the space to its right (top-aligned), so the wide
        # card reads as one balanced row instead of a half-width control with
        # a large blank gap beside/below it.
        mode_group = QGroupBox("Delivery Hardware Mode")
        mode_layout = QGridLayout()
        mode_layout.setContentsMargins(16, 12, 16, 12)
        mode_layout.setHorizontalSpacing(16)
        mode_layout.setVerticalSpacing(8)

        self.hardware_mode_combo = QComboBox()
        # Display capitalized labels; store the canonical lowercase value as
        # userData so the saved setting (consumed by the strategy factory /
        # relay worker) stays 'solenoid' / 'pump'.
        self.hardware_mode_combo.addItem("Solenoid", "solenoid")
        self.hardware_mode_combo.addItem("Pump", "pump")
        self.hardware_mode_combo.setMinimumWidth(150)
        self.hardware_mode_combo.setMaximumWidth(200)
        current_mode = self.settings.get('hardware_mode', 'solenoid')
        mode_idx = self.hardware_mode_combo.findData(current_mode)
        self.hardware_mode_combo.setCurrentIndex(mode_idx if mode_idx >= 0 else 0)
        self.hardware_mode_combo.currentTextChanged.connect(self._on_hardware_mode_changed)

        mode_layout.addWidget(QLabel("Hardware Mode:"), 0, 0, Qt.AlignLeft | Qt.AlignVCenter)
        mode_layout.addWidget(self.hardware_mode_combo, 0, 1, Qt.AlignLeft | Qt.AlignVCenter)

        mode_help = QLabel(
            "• <b>Solenoid</b> (default): flow-sensor volumetric control with "
            "real-time feedback<br>"
            "• <b>Pump</b>: time-based peristaltic pump control (legacy mode)"
        )
        mode_help.setWordWrap(True)
        mode_help.setObjectName("HelpText")
        mode_layout.addWidget(mode_help, 0, 2, Qt.AlignTop | Qt.AlignLeft)

        # Keep the label/control columns compact; the help column absorbs the
        # remaining width so the bullets sit top-right rather than leaving a gap.
        mode_layout.setColumnStretch(0, 0)
        mode_layout.setColumnStretch(1, 0)
        mode_layout.setColumnStretch(2, 1)

        mode_group.setLayout(mode_layout)
        layout.addWidget(mode_group)

        # ==================== SOLENOID MODE SETTINGS ====================
        self.solenoid_group = QGroupBox("Solenoid Mode Settings")
        solenoid_layout = QVBoxLayout()
        solenoid_layout.setContentsMargins(12, 12, 12, 12)
        solenoid_layout.setSpacing(12)

        solenoid_layout.addWidget(self._create_valve_topology_group())

        # Flow Sensor Configuration
        sensor_group = QGroupBox("Flow Sensor (Teensy Bridge)")
        sensor_layout = QFormLayout()
        sensor_layout.setContentsMargins(12, 12, 12, 12)
        sensor_layout.setSpacing(8)
        sensor_layout.setFieldGrowthPolicy(QFormLayout.ExpandingFieldsGrow)
        sensor_layout.setLabelAlignment(Qt.AlignLeft | Qt.AlignVCenter)

        # Teensy port selection
        port_row = QHBoxLayout()
        self.teensy_port_edit = QLineEdit()
        self.teensy_port_edit.setText(self.settings.get('uart_port', '/dev/teensy_flow'))
        self.teensy_port_edit.setPlaceholderText("/dev/teensy_flow (symlink) or /dev/ttyACM0")
        port_row.addWidget(self.teensy_port_edit)

        detect_button = QPushButton("Auto-Detect")
        detect_button.setToolTip("Automatically find Teensy USB port")
        detect_button.clicked.connect(self._auto_detect_teensy)
        port_row.addWidget(detect_button)

        test_button = QPushButton("Test")
        test_button.setToolTip("Test connection to Teensy (sends ping)")
        test_button.clicked.connect(self._test_teensy_connection)
        port_row.addWidget(test_button)

        sensor_layout.addRow("Teensy Port:", port_row)

        # Flow sensor optional toggle (NEW: enables calibration-only mode)
        self.flow_sensor_optional = QCheckBox("Allow schedules without flow sensor")
        self.flow_sensor_optional.setChecked(self.settings.get('flow_sensor_optional', True))
        self.flow_sensor_optional.setToolTip(
            "If enabled, schedules can run using calibration values when flow sensor is unavailable.\n"
            "The sensor acts as a 'guardrail' - comparing expected vs actual delivery when connected.\n"
            "If disabled, schedules will fail if the flow sensor is not connected."
        )
        sensor_layout.addRow("", self.flow_sensor_optional)

        sensor_optional_help = QLabel(
            "<i>When sensor unavailable, deliveries use per-valve calibration (pulse count × volume/pulse)</i>"
        )
        sensor_optional_help.setObjectName("HelpText")
        sensor_optional_help.setWordWrap(True)
        sensor_layout.addRow("", sensor_optional_help)

        # Sampling rate (SafeDoubleSpinBox prevents accidental scroll changes)
        self.flow_sampling_hz = SafeDoubleSpinBox()
        self.flow_sampling_hz.setRange(1.0, 100.0)
        self.flow_sampling_hz.setValue(self.settings.get('flow_sampling_hz', 50.0))
        self.flow_sampling_hz.setSuffix(" Hz")
        self.flow_sampling_hz.setToolTip(
            "Sensor measurement frequency (default: 50 Hz, max: 100 Hz)"
        )
        sensor_layout.addRow("Sampling Rate:", self.flow_sampling_hz)

        sensor_group.setLayout(sensor_layout)
        solenoid_layout.addWidget(sensor_group)

        # Valve Safety Settings
        safety_group = QGroupBox("Safety Settings")
        safety_layout = QFormLayout()
        safety_layout.setContentsMargins(12, 12, 12, 12)
        safety_layout.setSpacing(8)
        safety_layout.setFieldGrowthPolicy(QFormLayout.ExpandingFieldsGrow)
        safety_layout.setLabelAlignment(Qt.AlignLeft | Qt.AlignVCenter)

        self.max_valve_open_s = SafeDoubleSpinBox()
        self.max_valve_open_s.setRange(1.0, 60.0)
        self.max_valve_open_s.setValue(self.settings.get('max_valve_open_s', 20.0))
        self.max_valve_open_s.setSuffix(" s")
        self.max_valve_open_s.setToolTip("Maximum time valve can remain open (emergency cutoff)")
        safety_layout.addRow("Max Valve Open Time:", self.max_valve_open_s)

        self.no_flow_timeout_s = SafeDoubleSpinBox()
        self.no_flow_timeout_s.setRange(0.5, 10.0)
        self.no_flow_timeout_s.setValue(self.settings.get('no_flow_timeout_s', 3.5))
        self.no_flow_timeout_s.setSuffix(" s")
        self.no_flow_timeout_s.setToolTip("Abort delivery if no flow detected for this duration")
        safety_layout.addRow("No-Flow Timeout:", self.no_flow_timeout_s)

        self.predictive_close_ms = SafeDoubleSpinBox()
        self.predictive_close_ms.setRange(0.0, 100.0)
        self.predictive_close_ms.setValue(self.settings.get('predictive_close_ms', 10.0))
        self.predictive_close_ms.setSuffix(" ms")
        self.predictive_close_ms.setToolTip("Valve close lag compensation (reduces overshoot)")
        safety_layout.addRow("Predictive Close Lag:", self.predictive_close_ms)

        safety_group.setLayout(safety_layout)
        solenoid_layout.addWidget(safety_group)

        # Pulse Mode Settings
        pulse_group = QGroupBox("Pulse Mode (Parker Series 3 Valves)")
        pulse_layout = QFormLayout()
        pulse_layout.setContentsMargins(12, 12, 12, 12)
        pulse_layout.setSpacing(8)
        pulse_layout.setFieldGrowthPolicy(QFormLayout.ExpandingFieldsGrow)
        pulse_layout.setLabelAlignment(Qt.AlignLeft | Qt.AlignVCenter)

        self.use_pulse_delivery = QCheckBox("Enable Pulse Mode")
        self.use_pulse_delivery.setChecked(self.settings.get('use_pulse_delivery', True))
        self.use_pulse_delivery.setToolTip("Use micro-pulse delivery for precision (recommended)")
        pulse_layout.addRow("", self.use_pulse_delivery)

        self.pulse_width_ms = SafeSpinBox()
        self.pulse_width_ms.setRange(10, 500)
        self.pulse_width_ms.setValue(self.settings.get('pulse_width_ms', 20))
        self.pulse_width_ms.setSuffix(" ms")
        self.pulse_width_ms.setToolTip("Pulse duration (default: 20ms for Parker Series 3)")
        pulse_layout.addRow("Pulse Width:", self.pulse_width_ms)

        # Dose rounding policy. Water leaves the valve in whole pulses, so a
        # dose can only land within one pulse of its target; this picks
        # which side of the target that pulse falls on.
        self.round_doses_up = QCheckBox("Round doses up to the next whole pulse")
        self.round_doses_up.setChecked(bool(self.settings.get('round_doses_up', False)))
        self.round_doses_up.setToolTip(
            "Doses are delivered in whole pulses.\n"
            "Off (default): each dose is rounded to the nearest pulse, so it can land "
            "up to half a pulse under or over its target.\n"
            "On: rounding always goes up, so a dose never plans below its target "
            "and lands up to one pulse over.\n"
            "Turn this on when weighed doses come out short — for example with a "
            "flow-restricting needle on the reservoir.\n"
            "Applies to schedules started after the change; a running schedule keeps "
            "the policy it started with."
        )
        pulse_layout.addRow("", self.round_doses_up)

        pulse_group.setLayout(pulse_layout)
        solenoid_layout.addWidget(pulse_group)

        self.solenoid_group.setLayout(solenoid_layout)
        layout.addWidget(self.solenoid_group)

        # ==================== PUMP MODE SETTINGS ====================
        self.pump_group = QGroupBox("Pump Mode Settings")
        pump_layout = QFormLayout()
        pump_layout.setContentsMargins(12, 12, 12, 12)
        pump_layout.setSpacing(8)
        pump_layout.setFieldGrowthPolicy(QFormLayout.ExpandingFieldsGrow)
        pump_layout.setLabelAlignment(Qt.AlignLeft | Qt.AlignVCenter)

        self.pump_volume = SafeDoubleSpinBox()
        self.pump_volume.setRange(0, 1000)
        self.pump_volume.setValue(self.settings.get('pump_volume_ul', 50))
        self.pump_volume.setSuffix(" µL")
        self.pump_volume.setToolTip("Volume delivered per pump trigger")
        pump_layout.addRow("Pump Output Volume:", self.pump_volume)

        self.calibration_factor = SafeDoubleSpinBox()
        self.calibration_factor.setRange(0.1, 10.0)
        self.calibration_factor.setValue(self.settings.get('calibration_factor', 1.0))
        self.calibration_factor.setSingleStep(0.1)
        self.calibration_factor.setDecimals(2)
        self.calibration_factor.setToolTip("Calibration multiplier to adjust for pump variance")
        pump_layout.addRow("Calibration Factor:", self.calibration_factor)

        self.min_triggers = SafeSpinBox()
        self.min_triggers.setRange(1, 100)
        self.min_triggers.setValue(self.settings.get('min_triggers', 1))
        self.min_triggers.setToolTip("Minimum number of pump triggers per delivery")
        pump_layout.addRow("Min Triggers:", self.min_triggers)

        self.pump_group.setLayout(pump_layout)
        layout.addWidget(self.pump_group)

        # Update visibility based on current mode
        self._update_hardware_ui_visibility()

        # Add stretch to push everything to top
        layout.addStretch()

        widget.setLayout(layout)

        # Wrap in scroll area for proper overflow handling
        from PyQt5.QtWidgets import QFrame, QScrollArea

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setWidget(widget)
        scroll.setFrameShape(QFrame.NoFrame)

        return scroll

    def _on_hardware_mode_changed(self, mode):
        """
        Handle hardware mode change with safety check.

        Refused, and the combo put back, while a schedule, a priming session
        or a calibration is running: the same check as the valve topology.
        (It used to look for a ``run_stop_section.worker`` that does not
        exist, so it never refused anything.)
        """
        reason = self._hardware_change_blocked_reason()
        if reason:
            QMessageBox.warning(
                self,
                "Cannot Change Mode",
                f"The hardware mode cannot change while {reason}.\n\n"
                "Wait for it to finish, then try again.",
            )
            # Revert to previous mode
            old_mode = self.settings.get('hardware_mode', 'solenoid')
            old_idx = self.hardware_mode_combo.findData(old_mode)
            self.hardware_mode_combo.blockSignals(True)
            self.hardware_mode_combo.setCurrentIndex(old_idx if old_idx >= 0 else 0)
            self.hardware_mode_combo.blockSignals(False)
            return

        self._update_hardware_ui_visibility()
        self.print_to_terminal(f"Hardware mode changed to: {mode}")
        # Auto-save the mode change
        self._auto_save_settings()

    def _update_hardware_ui_visibility(self):
        """
        Show/hide settings groups based on hardware mode.

        Progressive Disclosure: Only show relevant settings
        """
        is_solenoid = self.hardware_mode_combo.currentData() == 'solenoid'
        self.solenoid_group.setVisible(is_solenoid)
        self.pump_group.setVisible(not is_solenoid)

    # ==================== VALVE TOPOLOGY ====================

    def _create_valve_topology_group(self):
        """
        The valve topology this device drives (see utils.topology).

        Deliberately not on the auto-save path: a change is refused while
        any hardware operation or schedule is active, confirmed by the
        operator, saved on its own and read back from the database before
        it is reported as done.
        """
        group = QGroupBox("Valve Topology")
        group_layout = QVBoxLayout()
        group_layout.setContentsMargins(12, 12, 12, 12)
        group_layout.setSpacing(8)

        self.valve_topology_buttons = QButtonGroup(group)
        self.valve_topology_radios = {}
        for value, label in (
            (SHARED_MANIFOLD, "Shared manifold (master valve)"),
            (INDEPENDENT, "Independent (one syringe and one valve per animal)"),
        ):
            radio = QRadioButton(label)
            self.valve_topology_buttons.addButton(radio)
            self.valve_topology_radios[value] = radio
            group_layout.addWidget(radio)
        self._show_valve_topology(topology_from(self.settings))

        note = QLabel(
            "Must match how this rig is plumbed. Changing it restarts RRR, so priming, "
            "calibration and schedules all use the new topology. After a change, "
            "calibrations measured under the other topology show as Stale, and in solenoid "
            "pulse mode (the default) a schedule watering a Stale cage will not start until "
            "that cage is recalibrated."
        )
        note.setObjectName("HelpText")
        note.setWordWrap(True)
        group_layout.addWidget(note)
        group.setLayout(group_layout)

        # buttonClicked fires for the operator's clicks (mouse or keyboard)
        # only, never for the setChecked that puts a refused change back.
        self.valve_topology_buttons.buttonClicked.connect(self._on_valve_topology_clicked)
        get_operation_lock().state_changed.connect(self._apply_hardware_settings_lock_state)
        self._apply_hardware_settings_lock_state()
        return group

    def _show_valve_topology(self, topology):
        """Check the radio for ``topology`` without running the change handler."""
        radio = self.valve_topology_radios.get(topology)
        if radio is not None:
            radio.setChecked(True)

    def _hardware_change_blocked_reason(self):
        """
        Why the valve hardware settings cannot change right now, or None.

        Any holder of the operation lock counts (a schedule run, a priming
        session or a calibration), and so does a delivery worker that is
        still running or a job the Run/Stop section has not finished.
        """
        lock = get_operation_lock()
        if lock.is_busy():
            return f"{lock.active_label()} is in progress"
        if updater.is_busy() or getattr(self.run_stop_section, 'job_in_progress', False):
            return "a schedule is running"
        return None

    def _apply_hardware_settings_lock_state(self):
        """Grey out the hardware mode and the topology choice while a change
        would be refused.

        Purely visual: the handlers check again. The lock announces its own
        changes; a running worker is re-checked whenever Settings or its
        Delivery sub-tab is shown.
        """
        reason = self._hardware_change_blocked_reason()
        tip = f"Unavailable while {reason}" if reason else ""
        combo = getattr(self, 'hardware_mode_combo', None)
        if combo is not None:
            combo.setEnabled(reason is None)
            combo.setToolTip(tip)
        for value, radio in getattr(self, 'valve_topology_radios', {}).items():
            radio.setEnabled(reason is None)
            radio.setToolTip(tip or describe(value))

    def _on_valve_topology_clicked(self, button):
        for value, radio in self.valve_topology_radios.items():
            if radio is button:
                self._on_valve_topology_chosen(value)
                return

    def _on_valve_topology_chosen(self, new):
        """
        Switch the device to the ``new`` topology if nothing is running and
        the operator confirms. Returns True once the change is saved.

        A saved change restarts RRR (utils.updater.restart_app): Priming
        builds its panel for the topology RRR started with, so only a
        restart brings every part onto the new one. Where RRR cannot
        restart itself (no launcher, as in a development checkout), the
        change still holds: schedules and calibrations read the topology
        when they start, and Priming stays locked until RRR is reopened.
        """
        old = topology_from(self.settings)
        if new == old:
            return False
        if not self.login_system or not self.login_system.is_logged_in():
            self._show_valve_topology(old)
            QMessageBox.warning(
                self, "Access Denied", "You must be logged in to change the valve topology."
            )
            return False
        if self._refuse_valve_topology_change(old):
            return False
        if not self._confirm_valve_topology(old, new):
            self._show_valve_topology(old)
            return False
        # The confirmation is modal, but the event loop keeps running under
        # it: a schedule, priming session or calibration may have started.
        if self._refuse_valve_topology_change(old):
            return False
        outcome = self._save_valve_topology(old, new)
        if outcome != 'saved':
            self._show_valve_topology(old)
            if outcome == 'unchanged':
                self._announce_valve_topology(
                    f"Valve topology NOT changed: {new} could not be saved; still {old}"
                )
                QMessageBox.critical(
                    self,
                    "Topology Not Saved",
                    f"The valve topology could not be saved, so this device stays on "
                    f"{old}.\n\nThe Terminal tab shows the database error.",
                )
            else:
                self._announce_valve_topology(
                    f"Valve topology NOT confirmed: the database could not be read back "
                    f"after saving {new}; running on {old} until restart"
                )
                QMessageBox.critical(
                    self,
                    "Topology Not Confirmed",
                    f"The database could not confirm the valve topology. RRR keeps running "
                    f"on {old}, but the next start may load {new}.\n\n"
                    "The Terminal tab shows the database error. Restart RRR and check "
                    "Settings > Delivery > Valve Topology before running a schedule.",
                )
            return False

        trainer = self.login_system.get_current_trainer() or {}
        who = trainer.get('username') or 'unknown user'
        # The Terminal tab goes with the restart, so the database keeps who
        # changed the topology and when (the logs table, as calibrations do).
        self.database_handler.log_action(
            trainer.get('trainer_id') or 0, 'valve_topology', f"{old} -> {new} (by {who})"
        )
        if hasattr(self, 'calibration_table'):
            self._populate_calibration_table()  # the Stale badges follow the topology
        priming = getattr(self, 'priming_widget', None)
        if priming is not None:
            priming.refresh_topology_state()  # locked until the restart takes over
        # Announced before the restart: under rrr.service, systemctl stops this
        # process as soon as it can, and the journal must still get the line.
        self._announce_valve_topology(
            f"Valve topology changed in Settings: {old} -> {new} (by {who}). "
            "Restarting RRR to apply it."
        )
        restarted, detail = self._restart_for_valve_topology()
        if not restarted:
            self._announce_valve_topology(
                f"RRR could not restart itself ({detail.rstrip('.')}): schedules and "
                f"calibrations started from now on use {new}; Priming waits until RRR "
                "is reopened."
            )
            self._notify_valve_topology_changed(new, detail)
        return True

    def _restart_for_valve_topology(self):
        """
        Restart RRR so every part runs the new topology: ``(restarted,
        detail)`` from utils.updater.restart_app, which the in-app update
        uses too. Nothing is running at this point: the change is refused
        while any hardware operation holds the lock or a job is unfinished.
        """
        try:
            return updater.restart_app()
        except Exception as exc:  # the saved change holds; say why there was no restart
            return False, str(exc)

    def _refuse_valve_topology_change(self, old):
        reason = self._hardware_change_blocked_reason()
        if reason is None:
            return False
        self._show_valve_topology(old)
        QMessageBox.warning(
            self,
            "Cannot Change Topology",
            f"The valve topology cannot change while {reason}.\n\n"
            "Wait for it to finish, then try again.",
        )
        return True

    def _confirm_valve_topology(self, old, new):
        """Ask the operator; what can go wrong depends on the direction."""
        master = self.settings.get('global_master_relay_id', DEFAULT_MASTER_RELAY_ID)
        if new == INDEPENDENT:
            effect = (
                f"RRR will stop driving the master valve (relay {master}): every delivery, "
                "calibration and priming session opens only the animal's own valve.\n\n"
                "If this rig still has a master valve, NO WATER will reach any animal."
            )
        else:
            effect = (
                f"RRR will open the master valve (relay {master}) and hold it open around "
                "every delivery, calibration and priming session.\n\n"
                "Choose this only if a master valve feeds a shared manifold on this rig."
            )
        box = QMessageBox(self)
        box.setIcon(QMessageBox.Question)
        box.setWindowTitle("Change Valve Topology")
        box.setText(
            f"Change the valve topology from {old} to {new}?\n\n{effect}\n\n"
            "RRR restarts to apply the change, so priming, calibration and schedules all "
            "use the new topology. Log in again after the restart.\n\n"
            "Calibrations measured under the other topology will show as Stale, and in "
            "solenoid pulse mode (the default) Run refuses a schedule that waters a Stale "
            "cage until that cage is recalibrated."
        )
        restart = box.addButton("Restart RRR", QMessageBox.AcceptRole)
        cancel = box.addButton("Cancel", QMessageBox.RejectRole)
        box.setDefaultButton(cancel)
        box.setEscapeButton(cancel)
        box.exec_()
        confirmed = box.clickedButton() is restart
        box.deleteLater()
        return confirmed

    def _save_valve_topology(self, old, new):
        """
        Persist the topology alone and read it back: 'saved', 'unchanged'
        (the database confirms the old topology) or 'unknown'.

        save_settings reports failures on a signal instead of raising, and a
        failed row write still changes the in-memory value, so the database
        is the judge. On a mismatch the old topology is put back in memory
        and, as far as the database allows, on disk; 'unknown' means the
        database confirmed neither, so the next start cannot be predicted.
        """
        self.system_controller.save_settings({SETTING_KEY: new})
        if self._stored_valve_topology() == new:
            return 'saved'
        self.system_controller.save_settings({SETTING_KEY: old})
        self.settings[SETTING_KEY] = old
        return 'unchanged' if self._stored_valve_topology() == old else 'unknown'

    def _stored_valve_topology(self):
        """
        The topology stored in the database, or None when it cannot be
        confirmed. get_system_settings() answers {} when the database cannot
        be read, so a missing row is not taken for the default topology.
        """
        try:
            stored = self.database_handler.get_system_settings().get(SETTING_KEY)
        except Exception as exc:
            self.print_to_terminal(f"Could not read the valve topology back: {exc}")
            return None
        return normalize(stored) if is_known(stored) else None

    def _announce_valve_topology(self, message):
        """
        To the Terminal tab and to the process's own stdout (the journal
        under rrr.service), beside the [TOPOLOGY] line printed at start-up.
        Once the GUI is up, sys.stdout feeds the Terminal tab only.
        """
        import sys

        line = f"[TOPOLOGY] {message}"
        self.print_to_terminal(line)
        if sys.__stdout__ is not None:
            try:
                print(line, file=sys.__stdout__, flush=True)
            except (OSError, ValueError):
                pass

    def _notify_valve_topology_changed(self, new, detail):
        """Only when RRR could not restart itself after a saved change."""
        QMessageBox.information(
            self,
            "Valve Topology Changed",
            f"This device now runs the {new} topology, but RRR could not restart "
            f"itself: {detail}\n\n"
            "Close and reopen RRR: until then Priming cannot open a valve. Schedules and "
            "calibrations started from now on use the new topology, and valves calibrated "
            "under the other one are marked Stale in the Calibration tab.",
        )

    def _auto_detect_teensy(self):
        """Auto-detect Teensy port using system controller"""
        try:
            port = self.system_controller.detect_teensy_port()
            if port:
                self.teensy_port_edit.setText(port)
                self.print_to_terminal(f"[OK] Teensy detected on {port}")
                QMessageBox.information(self, "Auto-Detect", f"Teensy found on {port}")
            else:
                self.print_to_terminal("[X] Teensy not detected. Check USB connection.")
                QMessageBox.warning(
                    self,
                    "Auto-Detect",
                    "Teensy not found. Ensure:\n"
                    "• Teensy is connected via USB\n"
                    "• Firmware is uploaded\n"
                    "• You are in 'dialout' group",
                )
        except Exception as e:
            self.print_to_terminal(f"Auto-detect error: {e}")
            QMessageBox.critical(self, "Error", f"Auto-detect failed: {str(e)}")

    def _test_teensy_connection(self):
        """Test Teensy connection using basic ping with proper resource management"""
        import json
        import time

        import serial

        port = self.teensy_port_edit.text()
        if not port:
            QMessageBox.warning(self, "Test Error", "Please specify a Teensy port first.")
            return

        ser = None  # Initialize for finally block
        try:
            self.print_to_terminal(f"Testing connection to {port}...")
            ser = serial.Serial(port, 115200, timeout=2.0)
            time.sleep(3.5)  # Teensy CDC enumeration delay

            # Send ping
            ser.write(b'{"cmd":"ping"}\n')
            ser.flush()

            # Wait for pong
            pong_received = False
            for _ in range(10):
                if ser.in_waiting:
                    line = ser.readline().decode('utf-8').strip()
                    if line:
                        try:
                            msg = json.loads(line)
                            if msg.get("type") == "pong":
                                pong_received = True
                                self.print_to_terminal(f"[OK] Teensy connection OK on {port}")
                                QMessageBox.information(
                                    self,
                                    "Connection Test",
                                    f"Teensy responded successfully!\nPort: {port}",
                                )
                                break  # Exit loop, port closed in finally
                        except json.JSONDecodeError:
                            pass
                time.sleep(0.1)

            if not pong_received:
                self.print_to_terminal(f"Teensy did not respond on {port}")
                QMessageBox.warning(
                    self,
                    "Connection Test",
                    f"Teensy did not respond.\n\n"
                    f"Troubleshooting:\n"
                    f"- Verify firmware is uploaded\n"
                    f"- Check serial port permissions\n"
                    f"- Try replugging USB cable",
                )

        except serial.SerialException as e:
            self.print_to_terminal(f"Serial error: {e}")
            QMessageBox.critical(
                self,
                "Connection Test",
                f"Failed to open port:\n{str(e)}\n\n"
                f"Check that no other program is using {port}",
            )
        except Exception as e:
            self.print_to_terminal(f"Test error: {e}")
            QMessageBox.critical(self, "Connection Test", f"Test failed: {str(e)}")
        finally:
            # CRITICAL: Always close serial port and release file lock
            if ser and ser.is_open:
                try:
                    ser.close()
                    time.sleep(0.5)  # Give OS time to fully release port lock
                    self.print_to_terminal(f"Serial port {port} closed and lock released")
                except Exception as cleanup_error:
                    self.print_to_terminal(f"Warning: Error during port cleanup: {cleanup_error}")

    def _create_calibration_tab(self):
        """
        Integrated Calibration UI (Option A)

        Best Practices:
        - Table shows all cages at a glance
        - Click row to launch wizard
        - Real-time status updates
        - All users can calibrate (logged to database)
        - Visual indicators for calibration quality
        """
        from PyQt5.QtCore import Qt
        from PyQt5.QtWidgets import (
            QAbstractItemView,
            QFrame,
            QHeaderView,
            QPushButton,
            QScrollArea,
            QTableWidget,
        )

        widget = QWidget()
        layout = QVBoxLayout()

        # Header with info
        header = QLabel(
            "<b>Calibration</b><br>"
            "<span style='color: #666;'>Per-valve empirical calibration for precision water delivery</span>"
        )
        header.setWordWrap(True)
        layout.addWidget(header)

        # Calibration table
        self.calibration_table = QTableWidget()
        self.calibration_table.setColumnCount(6)
        self.calibration_table.setHorizontalHeaderLabels(
            ["Cage", "Status", "mL/Pulse", "CV%", "Date", "Action"]
        )

        # Table styling - Match app's Material Design theme
        self.calibration_table.setAlternatingRowColors(True)
        self.calibration_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.calibration_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.calibration_table.setShowGrid(True)
        self.calibration_table.verticalHeader().setVisible(False)
        self.calibration_table.verticalHeader().setDefaultSectionSize(40)  # Accommodate buttons
        self.calibration_table.setMinimumHeight(300)
        # Don't set maxHeight - let the parent scroll area handle overflow
        # This ensures the table displays naturally and the tab scrolls when needed
        self.calibration_table.setVerticalScrollBarPolicy(
            Qt.ScrollBarAlwaysOff
        )  # Tab scrolls instead
        self.calibration_table.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.calibration_table.setVerticalScrollMode(QAbstractItemView.ScrollPerPixel)
        # The global `QTableWidget::item` padding has a 12px top inset, which
        # pushes setCellWidget action buttons down so they dip into the next
        # row. Trim the item padding for this table so the Calibrate buttons sit
        # centred. Padding-only override keeps the theme's row border.
        self.calibration_table.setStyleSheet("QTableWidget::item { padding: 4px 16px; }")
        # Rely on global QSS styling

        # Column resize modes - all fixed widths for consistent layout
        header = self.calibration_table.horizontalHeader()
        header.setStretchLastSection(False)
        header.setMinimumSectionSize(40)

        # Column 0: Cage - stretch to absorb slack (names vary in length)
        header.setSectionResizeMode(0, QHeaderView.Stretch)

        # Column 1: Status - compact fixed width (badge only)
        header.setSectionResizeMode(1, QHeaderView.Fixed)
        self.calibration_table.setColumnWidth(1, 120)

        # Column 2: mL/Pulse - fixed width (fits "0.001234")
        header.setSectionResizeMode(2, QHeaderView.Fixed)
        self.calibration_table.setColumnWidth(2, 95)

        # Column 3: CV% - fixed width
        header.setSectionResizeMode(3, QHeaderView.Fixed)
        self.calibration_table.setColumnWidth(3, 70)

        # Column 4: Date - fixed width (fits "2026-05-12")
        header.setSectionResizeMode(4, QHeaderView.Fixed)
        self.calibration_table.setColumnWidth(4, 100)

        # Column 5: Action - fixed width for button with padding
        header.setSectionResizeMode(5, QHeaderView.Fixed)
        self.calibration_table.setColumnWidth(5, 124)

        # Populate table with 15 cages
        self._populate_calibration_table()

        layout.addWidget(self.calibration_table)

        # Add significant spacing before action buttons to prevent invasion
        layout.addSpacing(16)

        # Action buttons - wrap in container to enforce spacing from table
        actions_container = QWidget()
        actions_container.setObjectName("TableActionBar")
        actions_container.setContentsMargins(0, 12, 0, 0)
        button_row = QHBoxLayout(actions_container)
        button_row.setSpacing(8)
        button_row.setContentsMargins(0, 0, 0, 0)

        refresh_btn = QPushButton("Refresh")
        refresh_btn.setObjectName("CompactButton")
        refresh_btn.setFixedHeight(28)
        refresh_btn.setToolTip("Reload calibration data from database")
        refresh_btn.clicked.connect(self._populate_calibration_table)
        button_row.addWidget(refresh_btn)

        button_row.addStretch()

        calibrate_all_btn = QPushButton("Calibrate All Uncalibrated")
        calibrate_all_btn.setObjectName("CompactButton")
        calibrate_all_btn.setFixedHeight(28)
        calibrate_all_btn.setToolTip(
            "Run the calibration wizard for every valve with no calibration, or with one "
            "measured under the other valve topology (Stale) (all users)"
        )
        calibrate_all_btn.clicked.connect(self._calibrate_all_uncalibrated)
        button_row.addWidget(calibrate_all_btn)
        self._calibrate_all_btn = calibrate_all_btn
        # Grey out calibration launch buttons while another hardware operation
        # (schedule run / priming) holds the lock; the launcher also refuses.
        get_operation_lock().state_changed.connect(self._apply_calibration_lock_state)

        export_btn = QPushButton("Export Report")
        export_btn.setObjectName("CompactButton")
        export_btn.setFixedHeight(28)
        export_btn.setToolTip("Export calibration data to CSV")
        export_btn.clicked.connect(self._export_calibration_report)
        button_row.addWidget(export_btn)

        layout.addWidget(actions_container)

        # Help text
        help_text = QLabel(
            "<b>Tips:</b> Click 'Calibrate' to run 250-pulse characterization. "
            "Requires lab scale (±0.001g). CV% <5% = production ready. "
            "<b>Stale</b> = measured under the other valve topology; a schedule "
            "watering that cage will not start until it is recalibrated."
        )
        help_text.setWordWrap(True)
        help_text.setObjectName("HelpText")
        layout.addWidget(help_text)

        widget.setLayout(layout)

        # Wrap in scroll area so content can overflow properly
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setWidget(widget)
        scroll.setFrameShape(QFrame.NoFrame)  # Remove border for cleaner look
        return scroll

    def _populate_calibration_table(self):
        """Load calibration data from database and populate table"""
        from datetime import datetime

        from PyQt5.QtCore import Qt
        from PyQt5.QtGui import QColor
        from PyQt5.QtWidgets import QPushButton

        # One row per cage in the device's real cage map: 15 on one HAT, 31
        # on two (relay 16 is reserved, the master on the shared manifold and
        # unused on the independent topology, and has no row).
        cage_map = self._cage_map()
        self.calibration_table.setRowCount(len(cage_map))

        # Per-row launch buttons are recreated here; track them fresh so the
        # operation-lock gating can grey them out (see _apply_calibration_lock_state).
        self._calibrate_buttons = []

        # Get all calibrations from database
        calibrations = {}
        try:
            calibrations = self.database_handler.get_all_valve_calibrations()
        except Exception as e:
            self.print_to_terminal(f"Error loading calibrations: {e}")

        # Get all cage names from database (Best Practice: batch query instead of N+1)
        cage_names = {}
        try:
            cage_names = self.database_handler.get_all_cage_names()
        except Exception as e:
            self.print_to_terminal(f"Error loading cage names: {e}")

        for row, (cage_id, relay_id) in enumerate(sorted(cage_map.items())):
            cal = calibrations.get(cage_id)

            # Cage name - use custom name if set, otherwise "Cage N"
            cage_info = cage_names.get(cage_id, {})
            custom_name = cage_info.get('name', '')
            if custom_name and custom_name != f"Cage {cage_id}":
                display_name = f"{cage_id}: {custom_name}"
            else:
                display_name = f"Cage {cage_id}"

            cage_item = QTableWidgetItem(display_name)
            cage_item.setTextAlignment(Qt.AlignLeft | Qt.AlignVCenter)
            cage_item.setToolTip(f"Cage {cage_id} - Relay {relay_id}")
            self.calibration_table.setItem(row, 0, cage_item)

            stale = bool(cal) and calibration_is_stale(cal, self.settings)
            invalid = bool(cal) and not calibration_is_usable(cal)
            # What Run does about it: only solenoid pulse delivery plans from
            # a valve calibration (see utils.calibration_gate).
            consequence = (
                "A schedule watering this cage will not start until it is recalibrated."
                if gate_applies(self.settings)
                else "The current delivery mode does not use it, but pulse delivery would "
                "refuse it until it is recalibrated."
            )
            if cal:
                # Calibrated - show data. A calibration measured under the
                # other valve topology, or one without a usable volume or
                # pulse width, is flagged, not hidden: a schedule watering
                # this cage will not start until it is recalibrated.
                if invalid:
                    status_item = QTableWidgetItem("Invalid")
                    status_item.setForeground(QColor(200, 0, 0))
                    status_item.setToolTip(
                        "The stored volume per pulse or pulse width is missing, zero or "
                        f"invalid. {consequence}"
                    )
                elif stale:
                    device = topology_from(self.settings)
                    status_item = QTableWidgetItem("Stale")
                    status_item.setForeground(QColor(200, 150, 0))
                    status_item.setToolTip(
                        f"Measured on {calibration_label(cal)}: "
                        f"{describe(calibration_topology(cal))}. "
                        f"This device runs {device}: {describe(device)}. "
                        f"{consequence}"
                    )
                else:
                    status_item = QTableWidgetItem("[OK]")
                    status_item.setForeground(QColor(0, 150, 0))
                    status_item.setToolTip(f"Calibrated on {calibration_label(cal)}")
                status_item.setTextAlignment(Qt.AlignCenter)

                volume_item = QTableWidgetItem(
                    _format_number(cal.get('volume_per_pulse_ml'), "{:.6f}")
                )
                volume_item.setTextAlignment(Qt.AlignCenter)

                # The CV may be missing (a row written without it): shown
                # as a dash rather than taking the whole table down.
                cv_pct = _as_number(cal.get('coefficient_of_variation_pct'))
                cv_item = QTableWidgetItem(_format_number(cv_pct, "{:.2f}%"))
                cv_item.setTextAlignment(Qt.AlignCenter)

                # Color code quality
                if cv_pct is None:
                    cv_item.setForeground(QColor(150, 150, 150))
                elif cv_pct < 1.0:
                    cv_item.setForeground(QColor(0, 150, 0))  # Excellent - green
                elif cv_pct < 3.0:
                    cv_item.setForeground(QColor(50, 150, 50))  # Good - lighter green
                elif cv_pct < 5.0:
                    cv_item.setForeground(QColor(200, 150, 0))  # Acceptable - yellow
                else:
                    cv_item.setForeground(QColor(200, 0, 0))  # Poor - red

                # Format date
                raw_date = str(cal.get('calibration_date') or '')
                try:
                    date_obj = datetime.fromisoformat(raw_date)
                    date_str = date_obj.strftime('%Y-%m-%d')
                except ValueError:
                    date_str = raw_date[:10] or "—"

                date_item = QTableWidgetItem(date_str)
                date_item.setTextAlignment(Qt.AlignCenter)

                self.calibration_table.setItem(row, 1, status_item)
                self.calibration_table.setItem(row, 2, volume_item)
                self.calibration_table.setItem(row, 3, cv_item)
                self.calibration_table.setItem(row, 4, date_item)

                # Action button - Recalibrate (compact for table); a stale or
                # invalid row's button stands out like an uncalibrated row's.
                btn = QPushButton("Recalibrate")
                if stale or invalid:
                    btn.setProperty("variant", "primary")
                btn.setStyleSheet(self._ACTION_BUTTON_STYLE)
                btn.setMinimumWidth(90)
                btn.setToolTip(f"Recalibrate cage {cage_id}")
                btn.clicked.connect(lambda checked, c=cage_id: self._launch_calibration_wizard(c))
                self.calibration_table.setCellWidget(row, 5, btn)
                self._calibrate_buttons.append(btn)

            else:
                # Not calibrated - show warning
                status_item = QTableWidgetItem("Not Calibrated")
                status_item.setForeground(QColor(200, 0, 0))
                status_item.setTextAlignment(Qt.AlignCenter)
                status_item.setToolTip("Not calibrated")

                volume_item = QTableWidgetItem("—")
                volume_item.setTextAlignment(Qt.AlignCenter)
                volume_item.setForeground(QColor(150, 150, 150))

                cv_item = QTableWidgetItem("—")
                cv_item.setTextAlignment(Qt.AlignCenter)
                cv_item.setForeground(QColor(150, 150, 150))

                date_item = QTableWidgetItem("—")
                date_item.setTextAlignment(Qt.AlignCenter)
                date_item.setForeground(QColor(150, 150, 150))

                self.calibration_table.setItem(row, 1, status_item)
                self.calibration_table.setItem(row, 2, volume_item)
                self.calibration_table.setItem(row, 3, cv_item)
                self.calibration_table.setItem(row, 4, date_item)

                # Action button - Calibrate (compact for table)
                btn = QPushButton("Calibrate")
                btn.setProperty("variant", "primary")
                btn.setStyleSheet(self._ACTION_BUTTON_STYLE)
                btn.setMinimumWidth(90)
                btn.setToolTip(f"Calibrate cage {cage_id} (250 pulses)")
                btn.clicked.connect(lambda checked, c=cage_id: self._launch_calibration_wizard(c))
                self.calibration_table.setCellWidget(row, 5, btn)
                self._calibrate_buttons.append(btn)

        # Reflect the current operation-lock state on the freshly-built buttons.
        self._apply_calibration_lock_state()

    def _apply_calibration_lock_state(self):
        """Grey out the calibration launch buttons while another hardware
        operation (a schedule run / priming) holds the operation lock. Purely
        visual — _launch_calibration_wizard also refuses. Tolerates being called
        before the table is first populated."""
        lock = get_operation_lock()
        busy = lock.is_busy() and not lock.held_by(CALIBRATION)
        tip = f"Unavailable while {lock.active_label()} is in progress" if busy else ""
        buttons = list(getattr(self, "_calibrate_buttons", []))
        all_btn = getattr(self, "_calibrate_all_btn", None)
        if all_btn is not None:
            buttons.append(all_btn)
        for btn in buttons:
            btn.setEnabled(not busy)
            if busy:
                btn.setToolTip(tip)

    # Size-only stylesheet for the calibration-table action buttons. Cell-widget
    # buttons do not match the `QTableWidget QPushButton` compact rule in the
    # theme QSS, so they fall back to the base `QPushButton { min-height: 40px }`
    # and render ~42px tall — taller than the 40px row, which made them overflow
    # and straddle the boundary between two rows. An inline stylesheet (highest
    # priority) caps the height; the variant/theme colours still apply. Verified
    # on a real Pi display.
    _ACTION_BUTTON_STYLE = "QPushButton { min-height: 26px; max-height: 26px; padding: 2px 12px; }"

    def _launch_calibration_wizard(self, cage_id, announce=True):
        """
        Launch calibration wizard for specific cage.

        All users can calibrate - action is logged to database with trainer_id.

        Returns True when the wizard finished and saved (Accepted), False
        when it was refused, cancelled or crashed, so Calibrate All knows
        whether to open the next cage. ``announce=False`` skips the
        per-cage success box (the batch shows one summary instead).

        CRITICAL: Don't use print() to sys.stderr in this method - it's redirected
        through Qt signals which can corrupt during dialog operations.
        """
        # Check if logged in
        if not self.login_system or not self.login_system.is_logged_in():
            QMessageBox.warning(
                self, "Access Denied", "You must be logged in to calibrate valves."
            )
            return False

        # Hardware mutual-exclusion: no calibration while another hardware
        # operation (schedule run / priming) holds the lock. Authoritative check
        # (the per-cage / Calibrate-All buttons are also greyed out in Phase 2).
        _lock = get_operation_lock()
        if _lock.is_busy() and not _lock.held_by(CALIBRATION):
            QMessageBox.warning(
                self,
                "Hardware busy",
                f"Cannot calibrate while {_lock.active_label()} is in progress.",
            )
            return False

        # Import and create wizard dialog
        from ui.CalibrationWizard import CalibrationWizard

        try:
            wizard = CalibrationWizard(
                cage_id=cage_id,
                database_handler=self.database_handler,
                system_controller=self.system_controller,
                parent=self,
            )
        except Exception as e:
            import traceback

            traceback.print_exc()
            self.print_to_terminal(f"CRITICAL: Failed to create calibration wizard: {e}")
            raise

        # Execute wizard and check result
        # CRITICAL: Don't use print() to sys.stderr around dialog.exec_() -
        # it's redirected through Qt signals which can corrupt during dialog close!
        try:
            self.print_to_terminal(f"Opening calibration wizard for Cage {cage_id}...")
            # File log (safe) before exec_
            try:
                import os
                from datetime import datetime

                path = os.path.expanduser('~/rrr_app_debug.log')
                ts = datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]
                with open(path, 'a', encoding='utf-8') as f:
                    f.write(f"{ts} [RRR] SettingsTab: calling wizard.exec_() for cage {cage_id}\n")
            except Exception:
                pass
            result = wizard.exec_()
            self.print_to_terminal(f"Wizard completed with result: {result}")
            # File log (safe) after exec_
            try:
                import os
                from datetime import datetime

                path = os.path.expanduser('~/rrr_app_debug.log')
                ts = datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]
                with open(path, 'a', encoding='utf-8') as f:
                    f.write(f"{ts} [RRR] SettingsTab: wizard.exec_() returned {result}\n")
            except Exception:
                pass
        except Exception as e:
            import traceback

            traceback.print_exc()
            self.print_to_terminal(f"CRITICAL: Calibration wizard crashed during exec_(): {e}")
            import traceback

            error_trace = traceback.format_exc()
            self.print_to_terminal(f"Traceback:\n{error_trace}")

            # Even if wizard crashed, calibration might have been saved
            # Refresh table to show any saved data
            try:
                self.print_to_terminal("Attempting to refresh table despite error...")
                self._populate_calibration_table()
                self.print_to_terminal("Table refreshed - calibration may have been saved")
            except Exception as refresh_error:
                self.print_to_terminal(f"Failed to refresh table: {refresh_error}")
            return False

        if result == QDialog.Accepted:
            # Calibration completed successfully
            self.print_to_terminal(f"[OK] Cage {cage_id} calibration completed successfully")

            # Use QTimer to do ALL post-close operations
            # This ensures wizard is fully closed and event loop is stable
            def handle_successful_calibration():
                try:
                    # Refresh table to show new calibration
                    self.print_to_terminal("Refreshing calibration table...")
                    try:
                        self._populate_calibration_table()
                        self.print_to_terminal("Table refreshed successfully")
                    except Exception as refresh_error:
                        self.print_to_terminal(
                            f"Warning: Failed to refresh table: {refresh_error}"
                        )
                        import traceback

                        self.print_to_terminal(traceback.format_exc())

                    # Show success message (one summary instead, in a batch)
                    if not announce:
                        self.print_to_terminal("Post-calibration handling complete")
                        return
                    try:
                        self.print_to_terminal("Retrieving calibration data...")
                        cal = self.database_handler.get_valve_calibration(cage_id)

                        if cal:
                            self.print_to_terminal("Showing success message...")
                            QMessageBox.information(
                                self,
                                "Calibration Complete",
                                f"Cage {cage_id} calibration saved successfully!\n\n"
                                "Volume per pulse: "
                                f"{_format_number(cal.get('volume_per_pulse_ml'), '{:.6f}')} mL\n"
                                "Quality (CV): "
                                f"{_format_number(cal.get('coefficient_of_variation_pct'), '{:.2f}%')}"
                                "\n\n"
                                "This calibration is now active for all deliveries.",
                            )
                            self.print_to_terminal("Success message shown and dismissed")
                        else:
                            self.print_to_terminal("Warning: Calibration not found in database")
                            QMessageBox.information(
                                self,
                                "Calibration Complete",
                                f"Cage {cage_id} has been successfully calibrated!\n\n"
                                "The new calibration is now active.",
                            )
                    except Exception as msg_error:
                        self.print_to_terminal(
                            f"Warning: Failed to show success message: {msg_error}"
                        )
                        import traceback

                        self.print_to_terminal(traceback.format_exc())
                        # Don't crash - calibration is already saved

                    self.print_to_terminal("Post-calibration handling complete")

                except Exception as e:
                    self.print_to_terminal(f"Error in post-calibration handler: {e}")
                    import traceback

                    self.print_to_terminal(traceback.format_exc())

            # Schedule ALL operations for next event loop iteration
            # Give wizard 200ms to fully close and clean up
            from PyQt5.QtCore import QTimer

            self.print_to_terminal("Scheduling post-calibration operations...")
            QTimer.singleShot(200, handle_successful_calibration)
            return True

        elif result == QDialog.Rejected:
            # User cancelled/discarded calibration
            self.print_to_terminal(f"Cage {cage_id} calibration cancelled by user")
            return False

        else:
            # Unexpected result
            self.print_to_terminal(f"Warning: Unexpected dialog result: {result}")
            return False

    def _calibrate_all_uncalibrated(self):
        """
        Sequentially calibrate all uncalibrated valves.

        All users can calibrate - actions are logged to database with trainer_id.
        """
        # Check if logged in
        if not self.login_system or not self.login_system.is_logged_in():
            QMessageBox.warning(self, "Access Denied", "You must be logged in.")
            return

        # Cages with no calibration, then cages whose calibration has no
        # usable volume or pulse width (Invalid), then cages whose calibration
        # was measured under the other valve topology (Stale). Schedules
        # watering any of them will not start.
        calibrations = self.database_handler.get_all_valve_calibrations()
        cages = sorted(self._cage_map())
        uncalibrated = [c for c in cages if c not in calibrations]
        invalid = [
            c for c in cages if c in calibrations and not calibration_is_usable(calibrations[c])
        ]
        stale = [
            c
            for c in cages
            if c in calibrations
            and c not in invalid
            and calibration_is_stale(calibrations[c], self.settings)
        ]
        batch = uncalibrated + invalid + stale

        if not batch:
            QMessageBox.information(self, "All Calibrated", "All valves are already calibrated!")
            return

        parts = []
        if uncalibrated:
            parts.append(f"{len(uncalibrated)} uncalibrated valves:\n{uncalibrated}")
        if invalid:
            parts.append(f"{len(invalid)} with an unusable calibration (Invalid):\n{invalid}")
        if stale:
            parts.append(
                f"{len(stale)} calibrated under the other valve topology (Stale):\n{stale}"
            )
        found = "Found " + "\nand ".join(parts)
        reply = QMessageBox.question(
            self,
            "Calibrate All",
            f"{found}\n\n"
            f"This will take approximately {len(batch) * 10} minutes.\n\n"
            "Continue?",
            QMessageBox.Yes | QMessageBox.No,
        )

        if reply == QMessageBox.Yes:
            done = 0
            for cage_id in batch:
                # Stop at the first wizard the operator cancels (or that
                # cannot run) rather than open the next cage's. This used to
                # stop after the first wizard every time: the flag it tested
                # was never set anywhere.
                if not self._launch_calibration_wizard(cage_id, announce=False):
                    break
                done += 1
            summary = f"Calibrated {done} of {len(batch)} valves."
            if done < len(batch):
                summary += f" Not done: {batch[done:]}"
            self.print_to_terminal(summary)
            QMessageBox.information(self, "Calibrate All", summary)

    def _export_calibration_report(self):
        """Export calibration data to CSV"""
        try:
            from datetime import datetime

            file_path, _ = QFileDialog.getSaveFileName(
                self,
                "Export Calibration Report",
                f"calibration_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                "CSV Files (*.csv)",
            )

            if not file_path:
                return

            calibrations = self.database_handler.get_all_valve_calibrations()

            # csv.writer quotes a field only when it needs it, so a comma or a
            # quote in the notes cannot shift the columns.
            with open(file_path, 'w', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                writer.writerow(
                    [
                        "Cage",
                        "Status",
                        "Volume_per_Pulse_mL",
                        "CV_Percent",
                        "Num_Samples",
                        "Pulse_Width_ms",
                        "Inter_Pulse_Interval_ms",
                        "Calibration_Date",
                        "Notes",
                        "Topology",
                    ]
                )

                for cage_id in sorted(self._cage_map()):
                    if cage_id in calibrations:
                        cal = calibrations[cage_id]
                        # Pre-timing-profile rows have no interval: report the
                        # legacy cadence rather than an empty column.
                        interval = cal.get('inter_pulse_interval_ms')
                        interval_text = "100 (legacy)" if interval is None else str(interval)
                        if not calibration_is_usable(cal):
                            status = "Invalid"
                        elif calibration_is_stale(cal, self.settings):
                            status = "Stale"
                        else:
                            status = "Calibrated"
                        writer.writerow(
                            [
                                cage_id,
                                status,
                                _format_number(cal.get('volume_per_pulse_ml'), '{:.6f}'),
                                _format_number(cal.get('coefficient_of_variation_pct'), '{:.2f}'),
                                cal.get('num_samples'),
                                cal.get('pulse_width_ms'),
                                interval_text,
                                cal.get('calibration_date') or '',
                                cal.get('notes') or '',
                                calibration_label(cal),
                            ]
                        )
                    else:
                        writer.writerow([cage_id, "Not Calibrated"] + ["—"] * 8)

            self.print_to_terminal(f"Calibration report exported to {file_path}")
            QMessageBox.information(self, "Export Complete", f"Report saved to:\n{file_path}")

        except Exception as e:
            QMessageBox.critical(self, "Export Error", f"Failed to export: {str(e)}")

    def _stop_running_schedule(self) -> bool:
        """Stop a running schedule the way the Stop button does.

        True if one was running. Priming's CLOSE ALL RELAYS calls this: a
        schedule left running would open its valves again at its next pulse.
        """
        section = self.run_stop_section
        if section is None or not getattr(section, 'job_in_progress', False):
            return False
        section.stop_program()
        return True

    def _create_priming_control(self):
        """
        Create priming control tab using modular PrimingControlWidget.

        Best Practices:
        - Composition over inheritance
        - Single Responsibility Principle
        - Dependency Injection (passing settings and callback)
        - Separation of Concerns (priming logic isolated in dedicated widget)
        """
        from PyQt5.QtWidgets import QFrame, QScrollArea

        # Instantiate the modular priming control widget
        priming_widget = PrimingControlWidget(
            settings=self.settings,
            print_callback=self.print_to_terminal,
            stop_schedule=self._stop_running_schedule,
        )

        # Connect widget signals to parent if needed
        priming_widget.status_message.connect(self.print_to_terminal)
        # Kept so a valve topology change can lock its Open buttons.
        self.priming_widget = priming_widget

        # Wrap in scroll area for proper overflow handling
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setWidget(priming_widget)
        scroll.setFrameShape(QFrame.NoFrame)

        return scroll

    def _create_system_settings(self):
        """Create system settings tab with proper type handling"""
        system_group = QGroupBox("System Settings")
        layout = QFormLayout()
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(8)

        # Log Level Spinner with proper type handling
        self.log_level = SafeSpinBox()
        self.log_level.setRange(0, 4)  # 0=DEBUG to 4=CRITICAL
        self.log_level.setValue(int(self.settings.get('log_level', 2)))
        self.log_level.valueChanged.connect(self._log_level_changed)

        # Add tooltip to explain log levels
        self.log_level.setToolTip("0=DEBUG, 1=INFO, 2=WARNING, 3=ERROR, 4=CRITICAL")

        layout.addRow("Log Level:", self.log_level)

        system_group.setLayout(layout)
        return system_group

    def _log_level_changed(self, value):
        """Handle log level changes"""
        self.settings['log_level'] = value
        # Auto-save the log level change
        self._auto_save_settings()

    def _theme_changed(self, theme: str):
        """Apply theme immediately and persist in settings."""
        self.settings['theme'] = theme
        try:
            style_mgr = QApplication.instance().property('style_manager')
            if style_mgr:
                style_mgr.apply(theme)
        except Exception:
            pass
        # Re-render themed HTML content that QSS can't reach (Help tab).
        try:
            help_tab = getattr(self.window(), 'help_tab', None)
            if help_tab is not None and hasattr(help_tab, 'refresh_theme'):
                help_tab.refresh_theme()
        except Exception:
            pass
        # Auto-save the theme change
        self._auto_save_settings()

    def _create_notifications(self):
        slack_group = QGroupBox("Slack Integration")
        slack_layout = QFormLayout()
        slack_layout.setContentsMargins(12, 12, 12, 12)
        slack_layout.setSpacing(8)

        self.slack_token = QLineEdit()
        self.slack_token.setText(self.settings.get('slack_token', ''))
        self.slack_token.setEchoMode(QLineEdit.Password)
        slack_layout.addRow("Slack Bot Token:", self.slack_token)

        self.slack_channel = QLineEdit()
        self.slack_channel.setText(self.settings.get('channel_id', ''))
        slack_layout.addRow("Channel ID:", self.slack_channel)

        # Phase 3 offline-resilience: status indicator + troubleshooting.
        # The label is refreshed once a second by self._slack_status_timer
        # (started below) reading NotificationHandler.last_status.
        self.slack_status_label = QLabel()
        self.slack_status_label.setWordWrap(True)
        self.slack_status_label.setMinimumHeight(48)
        self.slack_status_label.setTextInteractionFlags(Qt.TextSelectableByMouse)
        slack_layout.addRow("Status:", self.slack_status_label)
        self._refresh_slack_status()

        # Re-render once a second so the indicator catches up shortly after
        # the relay worker calls send_slack_notification(). Cheap — the
        # formatter is pure-Python and reads one attribute.
        self._slack_status_timer = QTimer(self)
        self._slack_status_timer.timeout.connect(self._refresh_slack_status)
        self._slack_status_timer.start(1000)

        slack_group.setLayout(slack_layout)
        return slack_group

    def _refresh_slack_status(self):
        """Render the Slack indicator from NotificationHandler.last_status."""
        # Imported lazily so a missing utils.slack_status (e.g. on a partial
        # checkout) cannot stop the settings tab from opening.
        try:
            from utils.slack_status import format_status
        except Exception:
            return

        handler = getattr(self, "notification_handler", None)
        status = getattr(handler, "last_status", None) if handler else None
        icon, message = format_status(status)

        glyph = {"ok": "✓", "warn": "⚠", "unknown": "•"}.get(icon, "•")
        # Conservative palette — readable on both light and dark themes.
        color = {"ok": "#0a7d28", "warn": "#9c4a00", "unknown": "#666666"}.get(icon, "#666666")
        self.slack_status_label.setText(f"{glyph}  {message}")
        self.slack_status_label.setStyleSheet(f"color: {color}; padding: 6px; border-radius: 4px;")

    def _create_backup_restore(self):
        backup_group = QGroupBox("Backup and Restore")
        backup_layout = QVBoxLayout()
        backup_layout.setContentsMargins(12, 12, 12, 12)
        backup_layout.setSpacing(8)

        backup_button = QPushButton("Create Backup")
        backup_button.clicked.connect(self.create_backup)
        backup_layout.addWidget(backup_button)

        restore_button = QPushButton("Restore from Backup")
        restore_button.clicked.connect(self.restore_from_backup)
        backup_layout.addWidget(restore_button)

        backup_group.setLayout(backup_layout)
        return backup_group

    def _create_data_import_export(self):
        import_export_group = QGroupBox("Data Import/Export")
        layout = QGridLayout()
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(8)

        export_btn = QPushButton("Export Animals to CSV")
        export_btn.clicked.connect(self.export_animals)
        import_btn = QPushButton("Import Animals from CSV")
        import_btn.clicked.connect(self.import_animals)

        layout.addWidget(export_btn, 0, 0)
        layout.addWidget(import_btn, 0, 1)

        import_export_group.setLayout(layout)
        return import_export_group

    def _create_general_tab(self):
        """
        Merge Notifications, Import/Export, and Theme selection into one tab.
        """
        widget = QWidget()
        v = QVBoxLayout()
        v.setContentsMargins(12, 12, 12, 12)
        v.setSpacing(12)

        # Appearance group (Theme)
        appearance = QGroupBox("Appearance")
        appearance_form = QFormLayout()
        appearance_form.setContentsMargins(12, 12, 12, 12)
        appearance_form.setSpacing(8)
        self.theme_combo = QComboBox()
        self.theme_combo.addItems(["light", "dark"])
        try:
            self.theme_combo.setCurrentText(self.settings.get('theme', 'light'))
        except Exception:
            self.theme_combo.setCurrentText("light")
        self.theme_combo.currentTextChanged.connect(self._theme_changed)
        appearance_form.addRow("Theme:", self.theme_combo)
        appearance.setLayout(appearance_form)
        v.addWidget(appearance)

        # Notifications (Slack)
        v.addWidget(self._create_notifications())

        # Backup/Restore and Import/Export
        v.addWidget(self._create_backup_restore())
        v.addWidget(self._create_data_import_export())

        # System settings (e.g., log level) merged here for clarity
        v.addWidget(self._create_system_settings())

        # User Mode Toggle (Normal/Super)
        v.addWidget(self._create_mode_toggle())

        v.addStretch()
        widget.setLayout(v)

        # Wrap in scroll area for proper overflow handling
        from PyQt5.QtWidgets import QFrame, QScrollArea

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setWidget(widget)
        scroll.setFrameShape(QFrame.NoFrame)

        return scroll

    def _create_mode_toggle(self):
        """
        Create User Mode toggle (Normal/Super) section.

        Moved from main GUI to Settings for cleaner layout.
        """
        mode_group = QGroupBox("User Mode")
        mode_layout = QVBoxLayout()
        mode_layout.setContentsMargins(12, 12, 12, 12)
        mode_layout.setSpacing(8)

        # Description
        desc_label = QLabel(
            "Switch between Normal and Super mode to access all animals/schedules."
        )
        desc_label.setWordWrap(True)
        desc_label.setStyleSheet("color: #666; font-size: 11px;")
        mode_layout.addWidget(desc_label)

        # Mode toggle button
        self.mode_toggle_button = QPushButton("Switch to Super Mode")
        self.mode_toggle_button.setMinimumHeight(36)
        self.mode_toggle_button.clicked.connect(self._toggle_mode)
        mode_layout.addWidget(self.mode_toggle_button)

        # Current mode status
        self.mode_status_label = QLabel("Current Mode: Normal")
        self.mode_status_label.setStyleSheet("font-weight: bold;")
        mode_layout.addWidget(self.mode_status_label)

        # Update button text based on current mode
        self._update_mode_button_state()

        mode_group.setLayout(mode_layout)
        return mode_group

    def _toggle_mode(self):
        """Handle mode toggle from Settings tab."""
        if not self.login_system:
            QMessageBox.warning(self, "Not Logged In", "You must be logged in to switch modes.")
            return

        if not self.login_system.is_logged_in():
            QMessageBox.warning(self, "Not Logged In", "You must be logged in to switch modes.")
            return

        try:
            self.login_system.switch_mode()
            self._update_mode_button_state()

            new_role = self.login_system.get_current_trainer()['role']
            self.print_to_terminal(f"Switched to {new_role.capitalize()} Mode.")

            # Refresh animals and schedules if parent GUI is available
            parent = self.window()
            if hasattr(parent, 'projects_section'):
                parent.projects_section.schedules_tab.load_animals()
                parent.projects_section.animals_tab.load_animals()
        except Exception as e:
            QMessageBox.critical(self, "Mode Toggle Error", f"An error occurred: {e}")

    def _update_mode_button_state(self):
        """Update mode toggle button text based on current state."""
        if not hasattr(self, 'mode_toggle_button'):
            return

        if self.login_system and self.login_system.is_logged_in():
            try:
                current_role = self.login_system.get_current_trainer()['role']
                if current_role == 'super':
                    self.mode_toggle_button.setText("Switch to Normal Mode")
                    self.mode_status_label.setText("Current Mode: Super")
                else:
                    self.mode_toggle_button.setText("Switch to Super Mode")
                    self.mode_status_label.setText("Current Mode: Normal")
                self.mode_toggle_button.setEnabled(True)
            except Exception:
                self.mode_toggle_button.setEnabled(False)
                self.mode_status_label.setText("Current Mode: Unknown")
        else:
            self.mode_toggle_button.setEnabled(False)
            self.mode_status_label.setText("Current Mode: Guest (login required)")

    def create_backup(self):
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename, _ = QFileDialog.getSaveFileName(
                self, "Save Backup", f"rrr_backup_{timestamp}.json", "JSON files (*.json)"
            )

            if filename:
                with open(filename, 'w') as f:
                    json.dump(self.settings, f, indent=4)
                QMessageBox.information(self, "Success", "Backup created successfully")

        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to create backup: {str(e)}")

    def restore_from_backup(self):
        try:
            filename, _ = QFileDialog.getOpenFileName(
                self, "Load Backup", "", "JSON files (*.json)"
            )

            if filename:
                with open(filename, 'r') as f:
                    backup_settings = json.load(f)

                # Validate backup data
                required_keys = ['pump_volume_ul', 'calibration_factor']
                if not all(key in backup_settings for key in required_keys):
                    raise ValueError("Invalid backup file format")

                # The valve topology and the hardware mode change only through
                # their guarded controls in the Delivery tab, never from a
                # backup file: those refuse while anything drives the hardware.
                backup_topology = backup_settings.pop(SETTING_KEY, None)
                backup_mode = backup_settings.pop('hardware_mode', None)
                # The relay layout is this device's wiring. Its HAT count
                # changes only through Change Relay Hats, which re-initialises
                # the relay handlers and is greyed out while anything holds the
                # hardware; restored from a file, it would leave them (and a
                # priming session's valves) on the old layout.
                layout_keys = ('num_hats', 'global_master_relay_id', 'relay_pairs', 'cage_relays')
                backup_layout = {
                    key: backup_settings.pop(key) for key in layout_keys if key in backup_settings
                }
                self.settings.update(backup_settings)
                self.load_settings()
                message = "Settings restored successfully"
                current = topology_from(self.settings)
                if backup_topology is not None and normalize(backup_topology) != current:
                    message += (
                        f"\n\nThe backup's valve topology ({backup_topology}) was not applied: "
                        f"this device stays on {current}. Change it in Settings > Delivery > "
                        "Valve Topology if the rig was re-plumbed."
                    )
                mode = self.settings.get('hardware_mode', 'solenoid')
                if backup_mode is not None and str(backup_mode).strip().lower() != mode:
                    message += (
                        f"\n\nThe backup's hardware mode ({backup_mode}) was not applied: "
                        f"this device stays in {mode} mode. Change it in Settings > Delivery > "
                        "Delivery Hardware Mode if needed."
                    )
                hats = self.settings.get('num_hats', 1)
                if 'num_hats' in backup_layout and str(backup_layout['num_hats']) != str(hats):
                    message += (
                        f"\n\nThe backup's relay layout ({backup_layout['num_hats']} relay "
                        f"HAT(s)) was not applied: this device keeps its {hats}. Change the "
                        "number with Change Relay Hats if the hardware changed."
                    )
                QMessageBox.information(self, "Success", message)

        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to restore backup: {str(e)}")

    def load_settings(self):
        """Reload all settings into UI elements"""
        self.pump_volume.setValue(self.settings.get('pump_volume_ul', 50))
        self.calibration_factor.setValue(self.settings.get('calibration_factor', 1.0))
        self.slack_token.setText(self.settings.get('slack_token', ''))
        self.slack_channel.setText(self.settings.get('channel_id', ''))
        self.log_level.setValue(self.settings.get('log_level', 2))

    def export_animals(self):
        if not self.login_system.is_logged_in():
            QMessageBox.warning(self, "Access Denied", "You must be logged in to export animals.")
            return

        if not self.database_handler:
            QMessageBox.critical(self, "Export Error", "Database handler not initialized")
            return

        try:
            file_path, file_type = QFileDialog.getSaveFileName(
                self,
                "Export Animals",
                "",
                "Excel Files (*.xlsx);;CSV Files (*.csv)",  # Make Excel default
            )
            if not file_path:
                return

            animals = self.database_handler.get_all_animals()
            if not animals:
                QMessageBox.information(self, "Export Info", "No animals found to export")
                return

            data = []
            for animal in animals:
                # Format dates in Excel-friendly format
                last_weighted = (
                    datetime.fromisoformat(animal.last_weighted).strftime('%Y-%m-%d %H:%M:%S')
                    if animal.last_weighted
                    else ''
                )
                last_watering = (
                    datetime.fromisoformat(animal.last_watering).strftime('%Y-%m-%d %H:%M:%S')
                    if animal.last_watering
                    else ''
                )

                data.append(
                    {
                        'Lab Animal ID': animal.lab_animal_id,
                        'Name': animal.name,
                        'Sex': animal.sex or '',
                        'Initial Weight (g)': f"{animal.initial_weight:.1f}"
                        if animal.initial_weight
                        else '',
                        'Last Weight (g)': f"{animal.last_weight:.1f}"
                        if animal.last_weight
                        else '',
                        'Last Weighted': last_weighted,
                        'Last Watering': last_watering,
                    }
                )

            df = pd.DataFrame(data)

            # Ensure file has correct extension
            if not file_path.endswith(('.xlsx', '.csv')):
                file_path += '.xlsx' if 'Excel' in file_type else '.csv'

            if file_path.endswith('.xlsx'):
                # Excel-specific export settings for Mac compatibility
                writer = pd.ExcelWriter(file_path, engine='openpyxl')
                df.to_excel(writer, sheet_name='Animals', index=False)

                # Auto-adjust column widths
                worksheet = writer.sheets['Animals']
                for idx, col in enumerate(df.columns):
                    max_length = max(df[col].astype(str).apply(len).max(), len(col)) + 2
                    worksheet.column_dimensions[chr(65 + idx)].width = max_length

                writer.close()
            else:
                # Mac-friendly CSV settings
                df.to_csv(
                    file_path,
                    index=False,
                    encoding='utf-8-sig',  # BOM for Excel Mac
                    sep=',',
                    date_format='%Y-%m-%d %H:%M:%S',
                )

            self.print_to_terminal(f"Successfully exported {len(animals)} animals to {file_path}")
            QMessageBox.information(
                self, "Success", f"Successfully exported {len(animals)} animals"
            )

        except AttributeError as e:
            QMessageBox.critical(
                self,
                "Export Error",
                "Database connection error. Please check system configuration.",
            )
            self.print_to_terminal(f"Database error during export: {str(e)}")
        except Exception as e:
            QMessageBox.critical(self, "Export Error", f"Error exporting animals: {str(e)}")
            self.print_to_terminal(f"Unexpected error during export: {str(e)}")

    def import_animals(self):
        if not self.login_system.is_logged_in():
            QMessageBox.warning(self, "Access Denied", "You must be logged in to import animals.")
            return

        try:
            file_path, _ = QFileDialog.getOpenFileName(
                self, "Import Animals", "", "CSV Files (*.csv)"
            )
            if file_path:
                df = pd.read_csv(file_path)
                current_trainer = self.login_system.get_current_trainer()
                trainer_id = current_trainer['trainer_id'] if current_trainer else None

                imported = 0
                errors = []

                for _, row in df.iterrows():
                    try:
                        # Map lab document format to our database format
                        sex = (
                            'female'
                            if row['# Females'] == 1
                            else 'male'
                            if row['# Males'] == 1
                            else None
                        )

                        # Validate the birthdate format (raises on bad data,
                        # skipping the row). NOTE: the parsed value is not
                        # stored — Animal has no birthdate field yet; this is
                        # known debt, kept as a validation gate only.
                        datetime.strptime(str(row['Birthdate']), '%y%m%d')

                        animal = Animal(
                            animal_id=None,
                            lab_animal_id=str(row['Ear tag ID#'])
                            if pd.notna(row['Ear tag ID#'])
                            else row['Cage Number #'],
                            name=row['Nickname'] if pd.notna(row['Nickname']) else '',
                            initial_weight=None,  # No weight in lab format
                            last_weight=None,
                            last_weighted=None,
                            last_watering=None,
                            sex=sex,
                        )

                        if self.database_handler.add_animal(animal, trainer_id):
                            imported += 1

                    except Exception as e:
                        errors.append(f"Row {_+2}: {str(e)}")

                msg = f"Successfully imported {imported} animals."
                if errors:
                    msg += f"\n\nErrors ({len(errors)}):\n" + "\n".join(errors)

                QMessageBox.information(self, "Import Results", msg)
                self.print_to_terminal(f"Imported {imported} animals from {file_path}")

        except Exception as e:
            QMessageBox.critical(self, "Import Error", f"Error importing animals: {e}")
