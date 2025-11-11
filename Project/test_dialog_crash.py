#!/usr/bin/env python3
"""
Isolated test to reproduce the CalibrationWizard crash.

This minimal reproducer will help identify the exact point of failure.
Run with: python3 test_dialog_crash.py
"""

import sys
import traceback
from PyQt5.QtWidgets import (
    QApplication, QDialog, QMainWindow, QWidget, QVBoxLayout, 
    QHBoxLayout, QPushButton, QLabel, QTextEdit, QMessageBox,
    QDoubleSpinBox, QFormLayout
)
from PyQt5.QtCore import QTimer, pyqtSignal

# Import database handler
sys.path.insert(0, 'Project')
from models.database_handler import DatabaseHandler


class TestCalibrationDialog(QDialog):
    """Minimal dialog that mimics CalibrationWizard behavior"""
    
    calibration_complete = pyqtSignal(dict)
    
    def __init__(self, cage_id, db_handler, parent=None):
        super().__init__(parent)
        self.cage_id = cage_id
        self.db = db_handler
        self.calibration_result = None
        
        self.setWindowTitle(f"Test Calibration Dialog - Cage {cage_id}")
        self.setModal(True)
        self.resize(500, 400)
        
        self.init_ui()
    
    def init_ui(self):
        layout = QVBoxLayout(self)
        
        # Title
        title = QLabel(f"<h2>Test Calibration for Cage {self.cage_id}</h2>")
        layout.addWidget(title)
        
        # Log output
        self.log_output = QTextEdit()
        self.log_output.setReadOnly(True)
        layout.addWidget(self.log_output)
        
        # Input
        input_layout = QFormLayout()
        self.volume_input = QDoubleSpinBox()
        self.volume_input.setRange(0.1, 100.0)
        self.volume_input.setDecimals(6)
        self.volume_input.setValue(3.756)
        input_layout.addRow("Test Volume (mL):", self.volume_input)
        layout.addLayout(input_layout)
        
        # Buttons
        button_layout = QHBoxLayout()
        
        self.cancel_btn = QPushButton("Cancel")
        self.cancel_btn.clicked.connect(self._safe_cancel)
        button_layout.addWidget(self.cancel_btn)
        
        button_layout.addStretch()
        
        self.save_btn = QPushButton("Save & Finish")
        self.save_btn.clicked.connect(self._save_and_finish)
        button_layout.addWidget(self.save_btn)
        
        layout.addLayout(button_layout)
        
        self.log("Test dialog initialized")
        self.log(f"Database handler: {type(self.db).__name__}")
    
    def log(self, message):
        """Log a message to the output"""
        self.log_output.append(message)
        print(f"[DIALOG] {message}")  # Also print to console
    
    def _safe_cancel(self):
        """Safely cancel the dialog"""
        try:
            self.log("User clicked Cancel")
            self.log("Calling reject()...")
            self.reject()
            self.log("Dialog closed via reject()")
        except Exception as e:
            self.log(f"ERROR during cancel: {e}")
            traceback.print_exc()
    
    def _save_and_finish(self):
        """
        Save calibration to database and close dialog.
        This mimics the exact behavior of CalibrationWizard._save_and_finish()
        """
        try:
            self.log("=" * 50)
            self.log("SAVE & FINISH clicked")
            self.log("=" * 50)
            
            # Step 1: Prepare calibration data
            self.log("Step 1: Preparing calibration data...")
            measured_volume = self.volume_input.value()
            num_pulses = 250
            volume_per_pulse = measured_volume / num_pulses
            
            self.calibration_result = {
                'cage_id': self.cage_id,
                'volume_per_pulse_ml': volume_per_pulse,
                'stddev_ml': 0.000128,
                'cv_pct': 0.85,
                'num_samples': num_pulses,
                'measured_volume_ml': measured_volume
            }
            
            self.log(f"  Volume per pulse: {volume_per_pulse:.6f} mL")
            self.log("Step 1: COMPLETE")
            
            # Step 2: Save to database
            self.log("Step 2: Saving to database...")
            
            cal_id = self.db.save_valve_calibration(
                cage_id=self.cage_id,
                relay_id=self.cage_id,
                pulse_width_ms=50,
                volume_per_pulse_ml=volume_per_pulse,
                stddev_ml=0.000128,
                coefficient_of_variation_pct=0.85,
                num_samples=num_pulses,
                calibrated_by=None,
                notes=f"Test calibration from test_dialog_crash.py"
            )
            
            if not cal_id:
                raise Exception("Database returned None - save may have failed")
            
            self.log(f"  Saved with ID: {cal_id}")
            self.log("Step 2: COMPLETE")
            
            # Step 3: Log action
            self.log("Step 3: Logging action...")
            try:
                self.db.log_action(
                    trainer_id=None,
                    action_type='test_calibration',
                    details=f"Test calibration for Cage {self.cage_id}"
                )
                self.log("  Action logged")
            except Exception as log_error:
                self.log(f"  WARNING: Failed to log action: {log_error}")
            self.log("Step 3: COMPLETE")
            
            # Step 4: Log success
            self.log("Step 4: Finalizing...")
            self.log("  Calibration saved successfully!")
            self.log(f"  Volume/pulse: {volume_per_pulse:.6f} mL")
            self.log(f"  Quality (CV): 0.85%")
            self.log("Step 4: COMPLETE")
            
            # Step 5: Close dialog
            self.log("=" * 50)
            self.log("Step 5: CLOSING DIALOG")
            self.log("=" * 50)
            self.log("About to call self.accept()...")
            
            # TEST 1: Direct close (current approach)
            self.accept()
            
            self.log("After self.accept() returned")
            self.log("=" * 50)
            
        except Exception as e:
            self.log("=" * 50)
            self.log(f"EXCEPTION in _save_and_finish: {e}")
            self.log("=" * 50)
            import traceback
            error_details = traceback.format_exc()
            self.log(error_details)
            
            QMessageBox.critical(
                self,
                "Save Failed",
                f"Failed to save calibration:\n\n{str(e)}\n\n"
                "Check the log output for details."
            )


class TestMainWindow(QMainWindow):
    """Main window that opens the test dialog"""
    
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Dialog Crash Test - Main Window")
        self.resize(600, 500)
        
        # Initialize database
        print("[MAIN] Initializing database...")
        self.db = DatabaseHandler()
        print(f"[MAIN] Database handler created: {type(self.db).__name__}")
        
        self.init_ui()
    
    def init_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)
        
        # Title
        title = QLabel("<h1>Dialog Crash Test</h1>")
        layout.addWidget(title)
        
        # Instructions
        instructions = QLabel(
            "This test will help identify the exact crash point.\n\n"
            "Instructions:\n"
            "1. Click 'Open Test Dialog'\n"
            "2. Click 'Save & Finish' in the dialog\n"
            "3. Watch the console output\n"
            "4. Report the last message you see before crash"
        )
        instructions.setWordWrap(True)
        layout.addWidget(instructions)
        
        # Terminal output
        self.terminal = QTextEdit()
        self.terminal.setReadOnly(True)
        layout.addWidget(self.terminal)
        
        # Buttons
        button_layout = QHBoxLayout()
        
        self.open_dialog_btn = QPushButton("Open Test Dialog")
        self.open_dialog_btn.clicked.connect(self.open_test_dialog)
        button_layout.addWidget(self.open_dialog_btn)
        
        self.clear_btn = QPushButton("Clear Log")
        self.clear_btn.clicked.connect(self.terminal.clear)
        button_layout.addWidget(self.clear_btn)
        
        layout.addLayout(button_layout)
        
        self.print_to_terminal("[MAIN] Test application initialized")
        self.print_to_terminal("[MAIN] Database ready")
        self.print_to_terminal("[MAIN] Click 'Open Test Dialog' to begin test")
    
    def print_to_terminal(self, message):
        """Print message to terminal"""
        self.terminal.append(message)
        print(message)
    
    def open_test_dialog(self):
        """Open the test calibration dialog"""
        cage_id = 1
        
        self.print_to_terminal("")
        self.print_to_terminal("=" * 60)
        self.print_to_terminal(f"[MAIN] Opening test dialog for Cage {cage_id}...")
        self.print_to_terminal("=" * 60)
        
        # Create dialog
        dialog = TestCalibrationDialog(
            cage_id=cage_id,
            db_handler=self.db,
            parent=self
        )
        
        # Execute dialog and check result
        try:
            self.print_to_terminal("[MAIN] Calling dialog.exec_()...")
            
            result = dialog.exec_()
            
            self.print_to_terminal(f"[MAIN] dialog.exec_() returned: {result}")
            self.print_to_terminal(f"[MAIN] QDialog.Accepted = {QDialog.Accepted}")
            self.print_to_terminal(f"[MAIN] QDialog.Rejected = {QDialog.Rejected}")
            
        except Exception as e:
            self.print_to_terminal("=" * 60)
            self.print_to_terminal(f"[MAIN] CRASH during dialog.exec_(): {e}")
            self.print_to_terminal("=" * 60)
            import traceback
            error_trace = traceback.format_exc()
            self.print_to_terminal(error_trace)
            return
        
        # Handle result
        if result == QDialog.Accepted:
            self.print_to_terminal("[MAIN] Dialog accepted - calibration saved")
            
            # Delay post-close operations
            def handle_success():
                try:
                    self.print_to_terminal("[MAIN] Showing success message...")
                    
                    # Get calibration from DB
                    cal = self.db.get_valve_calibration(cage_id)
                    
                    if cal:
                        QMessageBox.information(
                            self,
                            "Test Complete",
                            f"Test calibration saved!\n\n"
                            f"Volume per pulse: {cal['volume_per_pulse_ml']:.6f} mL\n\n"
                            "Check console output for detailed log."
                        )
                        self.print_to_terminal("[MAIN] Success message shown and dismissed")
                    else:
                        self.print_to_terminal("[MAIN] WARNING: Calibration not found in DB")
                    
                    self.print_to_terminal("[MAIN] Test complete!")
                    self.print_to_terminal("=" * 60)
                    
                except Exception as e:
                    self.print_to_terminal(f"[MAIN] Error in success handler: {e}")
                    traceback.print_exc()
            
            # Schedule with delay
            self.print_to_terminal("[MAIN] Scheduling success handler (200ms)...")
            QTimer.singleShot(200, handle_success)
            
        elif result == QDialog.Rejected:
            self.print_to_terminal("[MAIN] Dialog cancelled by user")
            self.print_to_terminal("=" * 60)
        else:
            self.print_to_terminal(f"[MAIN] Unexpected result: {result}")
            self.print_to_terminal("=" * 60)


def main():
    """Run the test application"""
    print("=" * 60)
    print("DIALOG CRASH TEST - ISOLATED REPRODUCER")
    print("=" * 60)
    print()
    print("This test mimics the CalibrationWizard behavior.")
    print("Watch the console output to identify the exact crash point.")
    print()
    
    app = QApplication(sys.argv)
    
    # Install exception hook
    def exception_hook(exctype, value, tb):
        print("=" * 60)
        print("UNHANDLED EXCEPTION CAUGHT:")
        print("=" * 60)
        traceback.print_exception(exctype, value, tb)
        print("=" * 60)
    
    sys.excepthook = exception_hook
    
    # Create and show main window
    window = TestMainWindow()
    window.show()
    
    print()
    print("Application started. Main window displayed.")
    print("Click 'Open Test Dialog' to begin test.")
    print()
    
    sys.exit(app.exec_())


if __name__ == '__main__':
    main()

