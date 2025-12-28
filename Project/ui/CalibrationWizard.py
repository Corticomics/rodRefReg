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

from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QSpinBox, QDoubleSpinBox, QTextEdit, QProgressBar,
    QGroupBox, QFormLayout, QMessageBox, QWizard, QWizardPage
)
from PyQt5.QtCore import Qt, QTimer, pyqtSignal, QEvent
from PyQt5.QtGui import QFont
import asyncio
from datetime import datetime


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
    
    def __init__(self, cage_id, database_handler, system_controller, parent=None):
        """
        Initialize calibration wizard.
        
        CRITICAL: Avoid print() to sys.stderr during __init__ and close operations
        as sys.stderr is redirected through Qt signals which can corrupt during 
        dialog destruction. Use self.log() instead for user-visible output.
        """
        super().__init__(parent)
        
        # CRITICAL: Use default QDialog behavior - don't modify window flags!
        # The working test_dialog_crash.py proves this is all we need:
        # - Default QDialog is already a proper child dialog
        # - Has close button by default
        # - Won't trigger app quit when closed
        # - Doesn't need WA_DeleteOnClose flag
        
        # Set modal to block interaction with parent while wizard is open
        self.setModal(True)
            
        # Store references
        self.cage_id = cage_id
        self.db = database_handler
        self.system_controller = system_controller
            
        # Calibration parameters
        self.num_pulses = 250  # Default
        self.pulse_width_ms = 20  # Default
        self.measured_volume_ml = 0.0
        self.calibration_result = None
            
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
        self.log_output.verticalScrollBar().setValue(
            self.log_output.verticalScrollBar().maximum()
        )
    
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
            f" Cage {self.cage_id} output tube is positioned over beaker"
        ]
        
        for check in checks:
            label = QLabel(check)
            label.setObjectName("ChecklistItem")
            checklist_layout.addWidget(label)
        
        checklist_group.setLayout(checklist_layout)
        self.content_layout.addWidget(checklist_group)
        
        warning = QLabel("This process will take ~8-10 minutes and cannot be paused once started.")
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
        self.num_pulses_spin.setRange(100, 500)
        self.num_pulses_spin.setValue(250)
        self.num_pulses_spin.setSuffix(" pulses")
        self.num_pulses_spin.setToolTip("More pulses = higher precision (recommended: 250)")
        config_layout.addRow("Number of Pulses:", self.num_pulses_spin)
        
        # Pulse width
        self.pulse_width_spin = QSpinBox()
        self.pulse_width_spin.setRange(10, 500)
        self.pulse_width_spin.setValue(20)
        self.pulse_width_spin.setSuffix(" ms")
        self.pulse_width_spin.setToolTip("Pulse duration (default: 20ms for Parker Series 3)")
        config_layout.addRow("Pulse Width:", self.pulse_width_spin)
        
        # Estimated time
        self.time_estimate = QLabel()
        self._update_time_estimate()
        self.num_pulses_spin.valueChanged.connect(self._update_time_estimate)
        config_layout.addRow("Estimated Time:", self.time_estimate)
        
        config_group.setLayout(config_layout)
        self.content_layout.addWidget(config_group)
        
        info = QLabel("Recommended: Use default values (250 pulses @ 20ms) for best accuracy.")
        info.setWordWrap(True)
        self.content_layout.addWidget(info)
        
        self.content_layout.addStretch()
        
        self.back_btn.setVisible(True)
        self.next_btn.setText("Next: Start Calibration →")
        self.next_btn.setEnabled(True)
    
    def _update_time_estimate(self):
        """Update estimated time based on pulse count"""
        num_pulses = self.num_pulses_spin.value() if hasattr(self, 'num_pulses_spin') else 250
        est_minutes = (num_pulses * 0.12) / 60  # ~0.12s per pulse
        self.time_estimate.setText(f"~{est_minutes:.1f} minutes")
    
    def _show_execution(self):
        """Step 3: Execute pulse sequence"""
        self.step_label.setText("Step 3 of 5: Executing Pulses")
        
        # Save parameters
        self.num_pulses = self.num_pulses_spin.value()
        self.pulse_width_ms = self.pulse_width_spin.value()
        
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
        
        self.log(f"Starting calibration: {self.num_pulses} pulses @ {self.pulse_width_ms}ms")
        
        # Start execution in background
        QTimer.singleShot(500, self._execute_calibration)
    
    def _execute_calibration(self):
        """
        Execute the calibration pulse sequence.
        
        Best Practices:
        - Use system controller's hardware interfaces
        - Progress feedback every 10 pulses
        - Robust error handling
        - Safe cleanup on failure
        """
        try:
            # Import required modules
            from drivers.solenoid_controller import SolenoidController
            from gpio.gpio_handler import RelayHandler
            from models.relay_unit_manager import RelayUnitManager
            import time
            
            # Get cage map from settings
            system_settings = self.system_controller.settings
            cage_map = {str(i): i for i in range(1, 16)}
            master_id = int(system_settings.get('global_master_relay_id', 16))
            
            # Create relay unit manager and handler
            relay_unit_manager = RelayUnitManager(system_settings)
            relay_handler = RelayHandler(relay_unit_manager, system_settings['num_hats'])
            
            # Create solenoid controller
            solenoid = SolenoidController(relay_handler, master_id, cage_map)
            
            self.log(" Hardware initialized")
            
            # Open master valve
            solenoid.open_master()
            time.sleep(0.5)
            self.log(" Master valve opened")
            
            # Execute pulses
            pulse_count = 0
            pulse_duration_s = self.pulse_width_ms / 1000.0
            
            for i in range(self.num_pulses):
                # Open valve
                solenoid.open_cage(self.cage_id)
                time.sleep(pulse_duration_s)
                
                # Close valve
                solenoid.close_cage(self.cage_id)
                pulse_count += 1
                
                # Update progress
                self.progress_bar.setValue(pulse_count)
                
                # Log every 50 pulses
                if pulse_count % 50 == 0:
                    self.log(f"Progress: {pulse_count}/{self.num_pulses} pulses ({pulse_count/self.num_pulses*100:.0f}%)")
                
                # Small delay between pulses
                time.sleep(0.1)
            
            # Close master valve
            solenoid.close_cage(self.cage_id)
            solenoid.close_master()
            
            self.log(f" Completed {pulse_count} pulses")
            self.log(" All valves closed")
            
            # Move to next step
            QTimer.singleShot(1000, lambda: self.show_step(3))
            
        except Exception as e:
            self.log(f"ERROR: {str(e)}")
            QMessageBox.critical(
                self,
                "Calibration Failed",
                f"An error occurred during pulse execution:\n\n{str(e)}\n\n"
                "Please ensure:\n"
                "• Relay hardware is connected\n"
                "• No other processes are using the hardware\n"
                "• System permissions are correct"
            )
            # Use safe cancel instead of direct reject()
            self._safe_cancel()
    
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
        stddev = scale_precision / (self.num_pulses ** 0.5)
        cv_pct = (stddev / volume_per_pulse) * 100 if volume_per_pulse > 0 else 999
        
        self.calibration_result = {
            'cage_id': self.cage_id,
            'volume_per_pulse_ml': volume_per_pulse,
            'stddev_ml': stddev,
            'cv_pct': cv_pct,
            'num_samples': self.num_pulses,
            'measured_volume_ml': self.measured_volume_ml
        }
        
        # Display results
        results_group = QGroupBox("Calibration Results")
        results_layout = QFormLayout()
        
        results_layout.addRow("Total Volume:", QLabel(f"<b>{self.measured_volume_ml:.4f} mL</b>"))
        results_layout.addRow("Number of Pulses:", QLabel(f"<b>{self.num_pulses}</b>"))
        vpp = QLabel(f"Volume per Pulse: {volume_per_pulse:.6f} mL")
        vpp.setProperty("variant", "success")
        results_layout.addRow("", vpp)
        results_layout.addRow("Estimated CV:", QLabel(f"<b>{cv_pct:.2f}%</b>"))
        
        results_group.setLayout(results_layout)
        self.content_layout.addWidget(results_group)
        
        # Quality assessment
        if cv_pct < 1.0:
            quality = "EXCELLENT"
            color = "#4CAF50"
        elif cv_pct < 3.0:
            quality = "GOOD"
            color = "#8BC34A"
        elif cv_pct < 5.0:
            quality = "ACCEPTABLE"
            color = "#FFC107"
        else:
            quality = "POOR"
            color = "#F44336"
        
        quality_label = QLabel(f"Quality: {quality}")
        quality_label.setAlignment(Qt.AlignCenter)
        self.content_layout.addWidget(quality_label)
        
        if cv_pct >= 5.0:
            warning = QLabel("Poor quality detected. Consider recalibrating with more pulses (300+)")
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
            notes = f"Wizard calibration: {self.num_pulses} pulses @ {self.pulse_width_ms}ms"
            
            cal_id = self.db.save_valve_calibration(
                cage_id=self.cage_id,
                relay_id=relay_id,
                pulse_width_ms=self.pulse_width_ms,
                volume_per_pulse_ml=float(self.calibration_result['volume_per_pulse_ml']),
                stddev_ml=float(self.calibration_result['stddev_ml']),
                cv_pct=float(self.calibration_result['cv_pct']),
                num_samples=int(self.num_pulses),
                calibrated_by=trainer_id,
                notes=notes
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
                    details=log_details
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
                "The calibration data was not saved."
            )

