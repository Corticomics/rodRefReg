"""
Calibration Wizard - Integrated UI for Per-Valve Calibration
============================================================

Best Practices:
- Wizard pattern for step-by-step user guidance
- Real-time progress feedback
- Input validation at each step
- Safe error handling
- Persistent storage of results
"""

import threading
from datetime import datetime

from PyQt5.QtCore import QObject, Qt, QThread, QTimer, pyqtSignal
from PyQt5.QtWidgets import (
    QDialog,
    QDoubleSpinBox,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QSpinBox,
    QTextEdit,
    QVBoxLayout,
)
from utils.operation_lock import CALIBRATION, get_operation_lock


class _CalibrationPulseWorker(QObject):
    """
    Executes the calibration pulse sequence on a worker thread.

    Owns ONLY the hardware pulse loop: open master / settle / loop
    [open cage relay, sleep(pulse width), close cage relay, sleep(rest)] /
    close master. The timing code is intentionally identical to the old
    inline GUI-thread loop (same time.sleep calls, same order, same
    hardware calls) so calibration timing characteristics are unchanged —
    time.sleep on a dedicated thread is correct here; QTimer scheduling
    would add event-loop jitter to the pulse width.

    Threading rules (see the project threading checklist / RelayWorker):
    - No widget access from this class — results reach the dialog only
      through the queued signals below.
    - Hardware imports stay inside run() so this module imports cheaply
      without hardware deps.
    - Cancellation is cooperative: the dialog sets ``stop_event`` and the
      loop checks it once per pulse. The inter-pulse rest waits on the
      same event, so a cancel interrupts a long rest immediately instead
      of running it out (identical behaviour at the legacy 100 ms rest).
    - Whatever the exit path (completion, cancel, exception), the cage
      relay and the master valve are closed before ``finished`` is emitted.
    """

    progress = pyqtSignal(int)  # pulses completed so far
    log = pyqtSignal(str)  # human-readable status line for the wizard log
    finished = pyqtSignal(bool, object)  # success, error message (str) or None

    # Rest between pulses, milliseconds — the legacy inline-loop value, used
    # when a caller does not supply a timing profile.
    DEFAULT_INTER_PULSE_INTERVAL_MS = 100

    def __init__(
        self,
        cage_id,
        num_pulses,
        pulse_width_ms,
        system_settings,
        stop_event,
        inter_pulse_interval_ms=DEFAULT_INTER_PULSE_INTERVAL_MS,
    ):
        super().__init__()
        self._cage_id = cage_id
        self._num_pulses = num_pulses
        self._pulse_width_ms = pulse_width_ms
        self._system_settings = system_settings
        self._stop_event = stop_event
        self._inter_pulse_interval_ms = inter_pulse_interval_ms

    def run(self):
        """Execute the pulse sequence. Runs on the worker thread."""
        import time

        success = False
        error = None
        solenoid = None
        valves_closed = False
        try:
            from drivers.solenoid_controller import SolenoidController
            from gpio.gpio_handler import RelayHandler
            from models.relay_unit_manager import RelayUnitManager

            system_settings = self._system_settings
            cage_map = {str(i): i for i in range(1, 16)}
            master_id = int(system_settings.get('global_master_relay_id', 16))

            # Create relay unit manager and handler.
            # NOTE: this is the wizard's OWN RelayHandler instance (not shared
            # with a RelayWorker); the OperationLock serializes hardware
            # operations app-wide, so no other operation drives relays now.
            relay_unit_manager = RelayUnitManager(system_settings)
            relay_handler = RelayHandler(relay_unit_manager, system_settings['num_hats'])

            # Create solenoid controller
            solenoid = SolenoidController(relay_handler, master_id, cage_map)

            self.log.emit(" Hardware initialized")

            # Open master valve
            solenoid.open_master()
            time.sleep(0.5)
            self.log.emit(" Master valve opened")

            # Execute pulses
            pulse_count = 0
            pulse_duration_s = self._pulse_width_ms / 1000.0
            rest_duration_s = self._inter_pulse_interval_ms / 1000.0
            stopped = False

            for _ in range(self._num_pulses):
                # Cooperative cancel: checked once per pulse.
                if self._stop_event.is_set():
                    stopped = True
                    break

                # Open valve
                solenoid.open_cage(self._cage_id)
                time.sleep(pulse_duration_s)

                # Close valve
                solenoid.close_cage(self._cage_id)
                pulse_count += 1

                # Update progress
                self.progress.emit(pulse_count)

                # Log every 50 pulses
                if pulse_count % 50 == 0:
                    self.log.emit(
                        f"Progress: {pulse_count}/{self._num_pulses} pulses "
                        f"({pulse_count / self._num_pulses * 100:.0f}%)"
                    )

                # Valve-closed rest between pulses. Waiting on the stop event
                # (rather than sleeping) means a cancel is honoured at once,
                # which matters once the rest runs to hundreds of ms.
                if self._stop_event.wait(rest_duration_s):
                    stopped = True
                    break

            # Close master valve (same order as the old inline loop)
            solenoid.close_cage(self._cage_id)
            solenoid.close_master()
            valves_closed = True

            if stopped:
                self.log.emit(f"Calibration cancelled after {pulse_count} pulses")
                self.log.emit(" All valves closed")
            else:
                success = True
                self.log.emit(f" Completed {pulse_count} pulses")
                self.log.emit(" All valves closed")

        except Exception as e:
            error = str(e)
        finally:
            # Fail-safe: never leave valves open, whatever the exit path.
            # (The old inline loop did NOT close valves on exception — this
            # backstop is a deliberate safety improvement.)
            if solenoid is not None and not valves_closed:
                try:
                    solenoid.close_cage(self._cage_id)
                except Exception as close_error:
                    self.log.emit(f"WARNING: failed to close cage valve: {close_error}")
                try:
                    solenoid.close_master()
                except Exception as close_error:
                    self.log.emit(f"WARNING: failed to close master valve: {close_error}")
            self.finished.emit(success, error)


class CalibrationWizard(QDialog):
    """
    Integrated calibration wizard with step-by-step UI.

    Workflow:
    1. Introduction & Pre-flight checks
    2. Configure calibration parameters
    3. Execute pulse sequence (with progress)
    4. Measure & input volume
    5. Calculate & save results
    """

    calibration_complete = pyqtSignal(dict)  # Emits calibration results

    # Default valve-closed rest offered in the wizard. Longer than the legacy
    # 100 ms so a calibration run does not heat the coil the way a tight duty
    # cycle does; the delivery path replays whatever is stored per cage.
    DEFAULT_INTER_PULSE_INTERVAL_MS = 500

    # Above this duty cycle the config page shows a (non-blocking) advisory.
    DUTY_CYCLE_ADVISORY_PCT = 15.0

    def __init__(self, cage_id, database_handler, system_controller, parent=None):
        """
        Initialize calibration wizard.

        CRITICAL: Avoid print() to sys.stderr during __init__ and close operations
        as sys.stderr is redirected through Qt signals which can corrupt during
        dialog destruction. Use self.log() instead for user-visible output.
        """
        super().__init__(parent)

        # CRITICAL: Use default QDialog behavior — don't modify window flags.
        # Default QDialog is already a proper child dialog with a close
        # button, won't trigger app quit when closed, and doesn't need
        # WA_DeleteOnClose. Setting custom flags here previously caused
        # the wizard to crash the parent app on close; the simpler default
        # is correct.

        # Set modal to block interaction with parent while wizard is open
        self.setModal(True)

        # Store references
        self.cage_id = cage_id
        self.db = database_handler
        self.system_controller = system_controller

        # Calibration parameters
        self.num_pulses = 250  # Default
        self.pulse_width_ms = 20  # Default
        self.inter_pulse_interval_ms = self.DEFAULT_INTER_PULSE_INTERVAL_MS
        self.measured_volume_ml = 0.0
        self.calibration_result = None

        # Pulse-worker state (populated by _execute_calibration).
        self._worker = None
        self._worker_thread = None
        self._worker_stop = None
        # True whenever no run holds the operation lock; set to False for
        # exactly the duration of a pulse run so the lock is released once
        # per run, on whichever termination path fires first.
        self._run_finalized = True
        self._user_cancelled = False

        # Window properties
        self.setWindowTitle(f"Valve Calibration Wizard - Cage {cage_id}")
        self.setMinimumWidth(600)
        self.setMinimumHeight(500)

        # Initialize UI
        self.init_ui()

    def init_ui(self):
        """Initialize multi-step wizard UI"""
        layout = QVBoxLayout(self)

        # Header
        header = QLabel(f"<h2>Calibrate Cage {self.cage_id}</h2>")
        header.setAlignment(Qt.AlignCenter)
        layout.addWidget(header)

        # Current step indicator
        self.step_label = QLabel()
        self.step_label.setAlignment(Qt.AlignCenter)
        self.step_label.setObjectName("Subheader")
        layout.addWidget(self.step_label)

        # Content area (changes per step)
        self.content_widget = QGroupBox()
        self.content_layout = QVBoxLayout()
        self.content_widget.setLayout(self.content_layout)
        layout.addWidget(self.content_widget)

        # Progress bar (hidden initially)
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        layout.addWidget(self.progress_bar)

        # Log output
        self.log_output = QTextEdit()
        self.log_output.setReadOnly(True)
        self.log_output.setMaximumHeight(150)
        self.log_output.setObjectName("WizardLog")
        layout.addWidget(self.log_output)

        # Button bar
        button_layout = QHBoxLayout()

        self.back_btn = QPushButton("← Back")
        self.back_btn.clicked.connect(self.go_back)
        self.back_btn.setVisible(False)
        button_layout.addWidget(self.back_btn)

        button_layout.addStretch()

        self.cancel_btn = QPushButton("Cancel")
        self.cancel_btn.clicked.connect(self._safe_cancel)
        button_layout.addWidget(self.cancel_btn)

        self.next_btn = QPushButton("Next")
        self.next_btn.clicked.connect(self.go_next)
        button_layout.addWidget(self.next_btn)

        layout.addLayout(button_layout)

        # Start with step 1
        self.current_step = 0
        self.show_step(0)

    def log(self, message):
        """Add message to log output (visible in wizard dialog)"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        formatted = f"[{timestamp}] {message}"
        self.log_output.append(formatted)
        self.log_output.verticalScrollBar().setValue(self.log_output.verticalScrollBar().maximum())

    def show_step(self, step):
        """Display specific wizard step"""
        # Clear current content
        while self.content_layout.count():
            child = self.content_layout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()

        self.current_step = step

        if step == 0:
            self._show_introduction()
        elif step == 1:
            self._show_configuration()
        elif step == 2:
            self._show_execution()
        elif step == 3:
            self._show_measurement()
        elif step == 4:
            self._show_results()

    def _show_introduction(self):
        """Step 1: Introduction & Pre-flight checks"""
        self.step_label.setText("Step 1 of 5: Pre-Flight Checklist")

        intro_text = QLabel(
            f"<b>Welcome to the Calibration Wizard for Cage {self.cage_id}</b><br><br>"
            "This process will empirically measure the valve's delivery volume by:<br>"
            "1. Executing 200-300 calibrated pulses<br>"
            "2. Measuring the total output with a lab scale<br>"
            "3. Calculating volume per pulse<br><br>"
            "<b style='color: #d32f2f;'>Before proceeding, ensure:</b>"
        )
        intro_text.setWordWrap(True)
        self.content_layout.addWidget(intro_text)

        checklist_group = QGroupBox("Pre-Flight Checklist")
        checklist_layout = QVBoxLayout()

        checks = [
            " Lab scale available (±0.001g precision minimum)",
            " Empty collection beaker ready",
            " Beaker tared on scale",
            " Fluid reservoir is FULL",
            " System has been running >30 minutes (stable temperature)",
            " No other schedules are running",
            f" Cage {self.cage_id} output tube is positioned over beaker",
        ]

        for check in checks:
            label = QLabel(check)
            label.setObjectName("ChecklistItem")
            checklist_layout.addWidget(label)

        checklist_group.setLayout(checklist_layout)
        self.content_layout.addWidget(checklist_group)

        warning = QLabel(
            "The run takes several minutes — the next step estimates it from your "
            "settings — and cannot be paused once started."
        )
        warning.setWordWrap(True)
        warning.setProperty("variant", "warning")
        self.content_layout.addWidget(warning)

        self.content_layout.addStretch()

        self.back_btn.setVisible(False)
        self.next_btn.setText("Next: Configure →")
        self.next_btn.setEnabled(True)

    def _show_configuration(self):
        """Step 2: Configure calibration parameters"""
        self.step_label.setText("Step 2 of 5: Configuration")

        config_group = QGroupBox("Calibration Parameters")
        config_layout = QFormLayout()

        # Number of pulses
        self.num_pulses_spin = QSpinBox()
        # Low counts are allowed for sampling and diagnostic runs; the
        # trade-off is precision, since scale resolution is a larger share
        # of a smaller total volume.
        self.num_pulses_spin.setRange(10, 1000)
        self.num_pulses_spin.setValue(250)
        self.num_pulses_spin.setSuffix(" pulses")
        self.num_pulses_spin.setToolTip(
            "More pulses = higher precision (recommended: 250). Short runs "
            "are useful for sampling a timing profile, but weigh a smaller "
            "total volume, so scale error counts for more."
        )
        config_layout.addRow("Number of Pulses:", self.num_pulses_spin)

        # Pulse width
        self.pulse_width_spin = QSpinBox()
        self.pulse_width_spin.setRange(10, 500)
        self.pulse_width_spin.setValue(20)
        self.pulse_width_spin.setSuffix(" ms")
        self.pulse_width_spin.setToolTip("How long the valve is held open for each pulse")
        config_layout.addRow("Pulse Width:", self.pulse_width_spin)

        # Inter-pulse interval — the valve-closed rest between pulses. Stored
        # with the calibration so deliveries replay the same timing profile.
        self.interval_spin = QSpinBox()
        self.interval_spin.setRange(100, 2000)
        self.interval_spin.setValue(self.DEFAULT_INTER_PULSE_INTERVAL_MS)
        self.interval_spin.setSingleStep(50)
        self.interval_spin.setSuffix(" ms")
        self.interval_spin.setToolTip(
            "Rest between pulses, with the valve closed. A longer rest keeps "
            "the coil cooler, which keeps the volume per pulse steady over a "
            "long run. Deliveries reuse the interval you calibrate with."
        )
        config_layout.addRow("Inter-Pulse Interval:", self.interval_spin)

        # Estimated time
        self.time_estimate = QLabel()
        config_layout.addRow("Estimated Time:", self.time_estimate)

        for spin in (self.num_pulses_spin, self.pulse_width_spin, self.interval_spin):
            spin.valueChanged.connect(self._update_time_estimate)

        config_group.setLayout(config_layout)
        self.content_layout.addWidget(config_group)

        # Duty-cycle advisory. Never blocks — the long-standing 20 ms / 100 ms
        # profile is itself 16.7%, so this only tells the operator that a hot
        # duty cycle can make the volume per pulse drift during the run.
        self.duty_warning = QLabel()
        self.duty_warning.setWordWrap(True)
        self.duty_warning.setProperty("variant", "warning")
        self.content_layout.addWidget(self.duty_warning)

        info = QLabel(
            "Calibrate with the pulse width and interval you intend to run. "
            "Deliveries replay this cage's stored timing profile."
        )
        info.setWordWrap(True)
        self.content_layout.addWidget(info)

        self._update_time_estimate()

        self.content_layout.addStretch()

        self.back_btn.setVisible(True)
        self.next_btn.setText("Next: Start Calibration →")
        self.next_btn.setEnabled(True)

    def _update_time_estimate(self):
        """Refresh the run-time estimate and the duty-cycle advisory."""
        if not hasattr(self, 'num_pulses_spin'):
            return
        num_pulses = self.num_pulses_spin.value()
        pulse_width_ms = self.pulse_width_spin.value()
        interval_ms = self.interval_spin.value()

        # Master-valve settle (0.5 s) plus one period per pulse.
        est_seconds = 0.5 + num_pulses * (pulse_width_ms + interval_ms) / 1000.0
        if est_seconds < 90:
            self.time_estimate.setText(f"~{est_seconds:.0f} seconds")
        else:
            self.time_estimate.setText(f"~{est_seconds / 60:.1f} minutes")

        duty_pct = 100.0 * pulse_width_ms / (pulse_width_ms + interval_ms)
        if duty_pct > self.DUTY_CYCLE_ADVISORY_PCT:
            self.duty_warning.setText(
                f"Duty cycle {duty_pct:.0f}% — the valve is energised for a large "
                "share of the run, so the coil heats up and the volume per pulse "
                "can drift downward. Lengthen the interval to reduce it."
            )
            self.duty_warning.setVisible(True)
        else:
            self.duty_warning.clear()
            self.duty_warning.setVisible(False)

    def _show_execution(self):
        """Step 3: Execute pulse sequence"""
        self.step_label.setText("Step 3 of 5: Executing Pulses")

        # Save parameters
        self.num_pulses = self.num_pulses_spin.value()
        self.pulse_width_ms = self.pulse_width_spin.value()
        self.inter_pulse_interval_ms = self.interval_spin.value()

        status = QLabel(
            f"<b>Executing {self.num_pulses} pulses on Cage {self.cage_id}...</b><br><br>"
            "The system is now delivering water to the collection beaker.<br>"
            "<b>Do not disturb</b> the setup during this process."
        )
        status.setWordWrap(True)
        self.content_layout.addWidget(status)

        self.progress_bar.setVisible(True)
        self.progress_bar.setRange(0, self.num_pulses)
        self.progress_bar.setValue(0)

        self.content_layout.addStretch()

        self.back_btn.setVisible(False)
        self.next_btn.setEnabled(False)
        self.next_btn.setText("Executing...")
        self.cancel_btn.setEnabled(False)

        self.log(
            f"Starting calibration: {self.num_pulses} pulses @ {self.pulse_width_ms}ms "
            f"+ {self.inter_pulse_interval_ms}ms rest"
        )

        # Start execution in background
        QTimer.singleShot(500, self._execute_calibration)

    def _execute_calibration(self):
        """
        Start the calibration pulse sequence on a worker thread.

        The pulse loop (open/sleep/close/sleep) runs in
        _CalibrationPulseWorker on a dedicated QThread so the GUI thread
        stays free — the progress bar and log now update live instead of
        freezing for the whole run. Results come back through queued
        signals; the operation lock is released in _finalize_run() on
        whichever termination path fires first (finish, error, cancel,
        dialog close).
        """
        # Hardware mutual-exclusion: calibration drives the master valve + flow
        # sensor shared with schedules/priming. Hold the lock for exactly the
        # pulse run (the later measure/results steps use no hardware).
        lock = get_operation_lock()
        if not lock.try_acquire(CALIBRATION):
            QMessageBox.warning(
                self,
                "Hardware busy",
                f"Cannot calibrate while {lock.active_label()} is in progress.",
            )
            self._safe_cancel()
            return

        # The lock is now held; _finalize_run() must release it exactly once.
        self._run_finalized = False
        self._user_cancelled = False

        self._worker_stop = threading.Event()
        self._worker = _CalibrationPulseWorker(
            cage_id=self.cage_id,
            num_pulses=self.num_pulses,
            pulse_width_ms=self.pulse_width_ms,
            system_settings=self.system_controller.settings,
            stop_event=self._worker_stop,
            inter_pulse_interval_ms=self.inter_pulse_interval_ms,
        )
        # NOT parented to the dialog (a QObject moved to a thread must be
        # parentless); lifetime is managed in _on_worker_finished.
        self._worker_thread = QThread()
        self._worker.moveToThread(self._worker_thread)
        self._worker_thread.started.connect(self._worker.run)
        # Cross-thread signals back into the dialog MUST be queued so the
        # slots (widget updates, message boxes) run on the GUI thread.
        self._worker.progress.connect(self._on_worker_progress, Qt.QueuedConnection)
        self._worker.log.connect(self.log, Qt.QueuedConnection)
        self._worker.finished.connect(self._on_worker_finished, Qt.QueuedConnection)
        self._worker_thread.start()

    def _on_worker_progress(self, pulse_count):
        """Update the progress bar (GUI thread, queued from the worker)."""
        self.progress_bar.setValue(pulse_count)

    def _on_worker_finished(self, success, error):
        """
        Worker run ended (GUI thread, queued from the worker).

        The worker has already closed the cage + master valves on every
        exit path, so all that is left here is thread teardown, the lock
        release, and the step transition / error report.
        """
        thread = self._worker_thread
        worker = self._worker
        self._worker_thread = None
        self._worker = None
        self._worker_stop = None
        if thread is not None:
            thread.quit()
            thread.wait(2000)
            thread.deleteLater()
        if worker is not None:
            worker.deleteLater()

        # Hardware work is over on every path — release the lock so
        # schedule/priming can run during the manual measure/results steps.
        self._finalize_run()

        if self._user_cancelled:
            # Cancel/close already handled dialog teardown; nothing to show.
            return

        if success:
            # Move to next step (same 1 s pause as the old inline flow)
            QTimer.singleShot(1000, self._advance_to_measurement)
        else:
            message = error if error else "Calibration stopped before completion"
            self.log(f"ERROR: {message}")
            QMessageBox.critical(
                self,
                "Calibration Failed",
                f"An error occurred during pulse execution:\n\n{message}\n\n"
                "Please ensure:\n"
                "• Relay hardware is connected\n"
                "• No other processes are using the hardware\n"
                "• System permissions are correct",
            )
            # Use safe cancel instead of direct reject()
            self._safe_cancel()

    def _advance_to_measurement(self):
        """Deferred transition to the measurement step (skip if closed)."""
        if self._user_cancelled:
            return
        self.show_step(3)

    def _finalize_run(self):
        """Release the operation lock for this wizard's run (exactly once)."""
        if self._run_finalized:
            return
        self._run_finalized = True
        get_operation_lock().release(CALIBRATION)

    def _shutdown_worker(self, wait_ms=5000):
        """
        Ask a running pulse worker to stop and wait (bounded) for its thread.

        The worker checks the stop event once per pulse and closes the cage
        relay + master valve before finishing, so when the wait returns the
        hardware is safe. No-op when no worker is running.
        """
        if self._worker_stop is not None:
            self._worker_stop.set()
        thread = self._worker_thread
        if thread is not None and thread.isRunning():
            thread.quit()
            if not thread.wait(wait_ms):
                self.log(
                    f"WARNING: calibration worker did not stop within {wait_ms} ms — "
                    "verify that all valves are closed"
                )

    def _show_measurement(self):
        """Step 4: User measures output"""
        self.step_label.setText("Step 4 of 5: Measure Output")

        self.progress_bar.setVisible(False)

        instruction = QLabel(
            f"<b>Pulse execution complete!</b><br><br>"
            f"<span style='font-size: 12pt;'>Please measure the collected water:</span>"
        )
        instruction.setWordWrap(True)
        self.content_layout.addWidget(instruction)

        steps = QLabel(
            "1. Remove the collection beaker from under Cage "
            + str(self.cage_id)
            + "\n2. Place beaker on lab scale"
            + "\n3. Read the weight in grams"
            + "\n4. For water: 1 gram ≈ 1 mL (at room temperature)"
            + "\n5. Enter the measured volume below"
        )
        steps.setWordWrap(True)
        self.content_layout.addWidget(steps)

        # Input group
        input_group = QGroupBox("Measurement Input")
        input_layout = QFormLayout()

        self.volume_input = QDoubleSpinBox()
        self.volume_input.setRange(0.1, 100.0)
        self.volume_input.setDecimals(3)
        self.volume_input.setSuffix(" mL")
        self.volume_input.setValue(0.0)
        input_layout.addRow("Measured Volume:", self.volume_input)

        input_group.setLayout(input_layout)
        self.content_layout.addWidget(input_group)

        self.content_layout.addStretch()

        self.back_btn.setVisible(False)  # Can't go back after execution
        self.next_btn.setEnabled(True)
        self.next_btn.setText("Calculate Results →")
        self.cancel_btn.setEnabled(True)

    def _show_results(self):
        """Step 5: Display and save results"""
        self.step_label.setText("Step 5 of 5: Calibration Results")

        # Calculate calibration
        self.measured_volume_ml = self.volume_input.value()

        if self.measured_volume_ml <= 0:
            QMessageBox.warning(self, "Invalid Input", "Please enter a valid measured volume > 0")
            self.show_step(3)  # Go back to measurement
            return

        volume_per_pulse = self.measured_volume_ml / self.num_pulses

        # Estimate uncertainty
        scale_precision = 0.001  # ±0.001g
        stddev = scale_precision / (self.num_pulses**0.5)
        cv_pct = (stddev / volume_per_pulse) * 100 if volume_per_pulse > 0 else 999

        self.calibration_result = {
            'cage_id': self.cage_id,
            'volume_per_pulse_ml': volume_per_pulse,
            'stddev_ml': stddev,
            'cv_pct': cv_pct,
            'num_samples': self.num_pulses,
            'measured_volume_ml': self.measured_volume_ml,
        }

        # Display results
        results_group = QGroupBox("Calibration Results")
        results_layout = QFormLayout()

        results_layout.addRow("Total Volume:", QLabel(f"<b>{self.measured_volume_ml:.4f} mL</b>"))
        results_layout.addRow("Number of Pulses:", QLabel(f"<b>{self.num_pulses}</b>"))
        results_layout.addRow(
            "Pulse Timing:",
            QLabel(
                f"<b>{self.pulse_width_ms} ms open + "
                f"{self.inter_pulse_interval_ms} ms rest</b>"
            ),
        )
        vpp = QLabel(f"Volume per Pulse: {volume_per_pulse:.6f} mL")
        vpp.setProperty("variant", "success")
        results_layout.addRow("", vpp)
        results_layout.addRow("Estimated CV:", QLabel(f"<b>{cv_pct:.2f}%</b>"))

        results_group.setLayout(results_layout)
        self.content_layout.addWidget(results_group)

        # Quality assessment. NOTE: a per-quality color was previously
        # computed here but never applied to any widget — removed as dead
        # code. If quality coloring is wanted, wire it into quality_label.
        if cv_pct < 1.0:
            quality = "EXCELLENT"
        elif cv_pct < 3.0:
            quality = "GOOD"
        elif cv_pct < 5.0:
            quality = "ACCEPTABLE"
        else:
            quality = "POOR"

        quality_label = QLabel(f"Quality: {quality}")
        quality_label.setAlignment(Qt.AlignCenter)
        self.content_layout.addWidget(quality_label)

        if cv_pct >= 5.0:
            warning = QLabel(
                "Poor quality detected. Consider recalibrating with more pulses (300+)"
            )
            warning.setWordWrap(True)
            warning.setProperty("variant", "warning")
            self.content_layout.addWidget(warning)

        self.content_layout.addStretch()

        self.log(f" Calibration calculated: {volume_per_pulse:.6f} mL/pulse (CV: {cv_pct:.2f}%)")

        self.back_btn.setVisible(False)
        self.next_btn.setText("Save & Finish")
        self.next_btn.setEnabled(True)
        self.cancel_btn.setText("Discard")

    def go_next(self):
        """Handle next button click"""
        if self.current_step == 0:
            self.show_step(1)
        elif self.current_step == 1:
            self.show_step(2)
        elif self.current_step == 2:
            pass  # Handled by async execution
        elif self.current_step == 3:
            self.show_step(4)
        elif self.current_step == 4:
            self._save_and_finish()

    def go_back(self):
        """Handle back button click"""
        if self.current_step > 0:
            self.show_step(self.current_step - 1)

    def closeEvent(self, event):
        """
        Override close event to handle X button properly.

        CRITICAL: Accept the event and let Qt handle dialog cleanup.
        Don't call reject() here - it causes recursion!
        Don't print to stderr here - sys.stderr is redirected through Qt signals
        which can corrupt during dialog destruction.
        """
        # Log to file (safe, not through Qt signals)
        try:
            import os
            from datetime import datetime

            path = os.path.expanduser('~/rrr_app_debug.log')
            ts = datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]
            with open(path, 'a', encoding='utf-8') as f:
                f.write(f"{ts} [RRR] Wizard closeEvent (X button)\n")
        except Exception:
            pass
        # Stop a running pulse worker first (bounded wait; the worker closes
        # the cage + master valves before finishing), then make sure the
        # operation lock isn't left held if the dialog is closed mid-run.
        self._user_cancelled = True
        self._shutdown_worker()
        self._finalize_run()
        # Just accept the close - dialog will be marked as rejected automatically
        # by Qt when closed via X button (not accept() or reject())
        event.accept()

    def _safe_cancel(self):
        """
        Safely cancel the calibration wizard.

        CRITICAL: Don't use print() to sys.stderr here - it goes through Qt signals
        which can corrupt during dialog close. Use self.log() for user-visible output.
        """
        # Log to file (safe)
        try:
            import os
            from datetime import datetime

            path = os.path.expanduser('~/rrr_app_debug.log')
            ts = datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]
            with open(path, 'a', encoding='utf-8') as f:
                f.write(f"{ts} [RRR] Wizard _safe_cancel invoked\n")
        except Exception:
            pass
        # Log state for user (visible in dialog log)
        if self.calibration_result:
            self.log("User cancelled - calibration data will NOT be saved")
        else:
            self.log("User cancelled calibration wizard")

        # Stop a running pulse worker first (bounded wait; the worker closes
        # the cage + master valves before finishing), then release the
        # operation lock for this run.
        self._user_cancelled = True
        self._shutdown_worker()
        self._finalize_run()

        # Close dialog immediately - user pressed cancel, they mean it
        # Use simple reject() - Qt will handle cleanup
        self.reject()

    def _save_and_finish(self):
        """
        Save calibration to database and close wizard.

        CRITICAL: Don't use print() to sys.stderr - it's redirected through Qt signals
        which can corrupt during dialog close. Use self.log() for user-visible output.

        Best Practices:
        - Defensive checks for all external references
        - Comprehensive error logging via self.log()
        - Safe dialog closing
        - Database transaction safety
        """
        self.log("=" * 50)
        self.log("SAVE & FINISH - Starting")
        self.log("=" * 50)

        try:
            # Step 1: Get current trainer ID with defensive checks
            self.log("Getting trainer info...")
            trainer_id = None
            trainer_name = 'Unknown'

            try:
                parent = self.parent()
                parent_name = type(parent).__name__ if parent else 'None'
                self.log(f"  Parent: {parent_name}")
                if parent and hasattr(parent, 'login_system'):
                    login_system = parent.login_system
                    if login_system and hasattr(login_system, 'get_current_trainer'):
                        current_trainer = login_system.get_current_trainer()
                        if current_trainer:
                            trainer_id = current_trainer.get('trainer_id')
                            trainer_name = current_trainer.get('username', 'Unknown')
                            self.log(f"  Trainer: {trainer_name} (ID: {trainer_id})")
                else:
                    self.log("  No login system found")
            except Exception as e:
                self.log(f"Warning: Could not get trainer info: {e}")
                # Continue with None trainer_id - this is acceptable

            # Step 2: Validate calibration result exists
            self.log("Validating calibration result...")
            if not self.calibration_result:
                raise ValueError("Calibration result is missing")

            # Validate required fields
            required_fields = ['volume_per_pulse_ml', 'stddev_ml', 'cv_pct']
            for field in required_fields:
                if field not in self.calibration_result:
                    raise ValueError(f"Missing required field: {field}")
            self.log("  All required fields present")

            # Step 3: Save to database
            self.log("Saving to database...")
            relay_id = self.cage_id  # Assuming cage_id == relay_id
            notes = (
                f"Wizard calibration: {self.num_pulses} pulses @ "
                f"{self.pulse_width_ms}ms + {self.inter_pulse_interval_ms}ms rest"
            )

            cal_id = self.db.save_valve_calibration(
                cage_id=self.cage_id,
                relay_id=relay_id,
                pulse_width_ms=self.pulse_width_ms,
                volume_per_pulse_ml=float(self.calibration_result['volume_per_pulse_ml']),
                stddev_ml=float(self.calibration_result['stddev_ml']),
                cv_pct=float(self.calibration_result['cv_pct']),
                num_samples=int(self.num_pulses),
                calibrated_by=trainer_id,
                notes=notes,
                # Always written: the row is replaced per cage, so omitting the
                # interval here would silently reset a stored profile to legacy.
                inter_pulse_interval_ms=int(self.inter_pulse_interval_ms),
            )

            if not cal_id:
                raise Exception("Database returned None - save may have failed")

            self.log(f"  SUCCESS: Saved to database (ID: {cal_id})")

            # Step 4: Log calibration action (separate try block - non-critical)
            self.log("Logging action...")
            try:
                log_details = (
                    f"Cage {self.cage_id}: {self.calibration_result['volume_per_pulse_ml']:.6f} mL/pulse, "
                    f"CV: {self.calibration_result['cv_pct']:.2f}%, "
                    f"Samples: {self.num_pulses}"
                )
                self.db.log_action(
                    super_user_id=trainer_id if trainer_id else 0,
                    action='valve_calibration',
                    details=log_details,
                )
                self.log("  Action logged successfully")
            except Exception as log_error:
                self.log(f"Warning: Failed to log action: {log_error}")

            # Step 5: Show success
            self.log("Finalizing...")
            self.log("[OK] Calibration saved successfully!")
            self.log(f"  Volume/pulse: {self.calibration_result['volume_per_pulse_ml']:.6f} mL")
            self.log(f"  Quality (CV): {self.calibration_result['cv_pct']:.2f}%")

            # Store cage_id for parent to access
            self.success_cage_id = self.cage_id

            # Step 6: Close dialog
            self.log("Closing dialog...")
            # Log to file (safe)
            try:
                import os
                from datetime import datetime

                path = os.path.expanduser('~/rrr_app_debug.log')
                ts = datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]
                with open(path, 'a', encoding='utf-8') as f:
                    f.write(f"{ts} [RRR] Wizard calling accept() from _save_and_finish\n")
            except Exception:
                pass
            self.accept()  # Close immediately, Qt handles cleanup

        except Exception as e:
            import traceback

            error_details = traceback.format_exc()

            self.log(f"CRITICAL ERROR during save: {str(e)}")
            self.log(f"Traceback:\n{error_details}")

            QMessageBox.critical(
                self,
                "Save Failed",
                f"Failed to save calibration:\n\n{str(e)}\n\n"
                "Check the log output for details.\n"
                "The calibration data was not saved.",
            )
