from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QPushButton, QLabel, QLineEdit, 
                             QDateTimeEdit, QTabWidget, QFormLayout, QSizePolicy, 
                             QHBoxLayout, QMessageBox, QComboBox, QDialog, QListWidget)
from PyQt5.QtCore import QDateTime, QTimer, Qt, pyqtSignal
from .schedule_drop_area import ScheduleDropArea
from .edit_schedule_dialog import EditScheduleDialog
from gpio.relay_worker import RelayWorker
from datetime import datetime
from PyQt5.QtWidgets import QApplication

class RunStopSection(QWidget):
    schedule_updated = pyqtSignal(int)

    def __init__(self, run_program_callback, stop_program_callback, change_relay_hats_callback, 
                 system_controller=None, database_handler=None, relay_handler=None, notification_handler=None, parent=None):
        super().__init__(parent)
        self.run_program_callback = run_program_callback
        self.stop_program_callback = stop_program_callback
        self.change_relay_hats_callback = change_relay_hats_callback
        self.system_controller = system_controller
        
        if database_handler is None:
            raise ValueError("database_handler cannot be None")
        self.database_handler = database_handler
        
        self.relay_handler = relay_handler
        self.notification_handler = notification_handler
        self.current_schedule = None

        self.job_in_progress = False

        self.init_ui()

        if system_controller:
            self.load_settings(system_controller.settings)

        self.setAcceptDrops(True)

    def init_ui(self):
        self.layout = QVBoxLayout()
        self.layout.setContentsMargins(0, 0, 0, 0)
        self.layout.setSpacing(12)

        self.run_button = QPushButton("Run", self)
        self.stop_button = QPushButton("Stop", self)
        self.relay_hats_button = QPushButton("Change Relay Hats", self)
        self.edit_button = QPushButton("Edit Schedule")
        
        self.edit_button.setObjectName("edit_button")
        self.edit_button.setEnabled(False)
        self.edit_button.clicked.connect(self.edit_current_schedule)
        self.edit_button.setStyleSheet("""
            QPushButton {
                background-color: #17a2b8;
                color: white;
                border: none;
                border-radius: 4px;
                padding: 4px 8px;
                font-size: 12px;
                min-width: 80px;
                max-height: 24px;
            }
            QPushButton:hover {
                background-color: #138496;
            }
            QPushButton:disabled {
                background-color: #87c4cb;
            }
        """)

        self.run_button.clicked.connect(self.run_program)
        self.stop_button.clicked.connect(self.stop_program)
        self.relay_hats_button.clicked.connect(self.change_relay_hats)

        self.button_layout = QHBoxLayout()
        self.button_layout.setSpacing(5)
        self.button_layout.addWidget(self.edit_button)
        self.button_layout.addWidget(self.run_button)
        self.button_layout.addWidget(self.stop_button)
        self.button_layout.addWidget(self.relay_hats_button)

        self.schedule_drop_area = ScheduleDropArea()
        self.schedule_drop_area.schedule_dropped.connect(self.on_schedule_dropped)
        
        self.layout.addLayout(self.button_layout)
        self.layout.addWidget(self.schedule_drop_area)
        self.layout.addStretch()
        
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        self.run_button.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.stop_button.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.relay_hats_button.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        
        self.setLayout(self.layout)
        self.update_button_states()
        
        self.schedule_drop_area.mode_changed.connect(self._on_mode_changed)

    def load_settings(self, settings):
        # No calendar settings needed anymore
        pass

    def update_button_states(self):
        self.run_button.setEnabled(not self.job_in_progress)
        self.stop_button.setEnabled(self.job_in_progress)
        self.relay_hats_button.setEnabled(not self.job_in_progress)
        if self.job_in_progress:
            self.run_button.setStyleSheet("""
                QPushButton {
                    background-color: #cccccc;
                    color: #666666;
                }
            """)
            self.run_button.setToolTip("Job in progress")
            self.relay_hats_button.setToolTip("Cannot change relay hats during a job")
        else:
            self.run_button.setStyleSheet("")
            self.run_button.setToolTip("")
            self.relay_hats_button.setToolTip("")

        if not self.job_in_progress:
            self.stop_button.setStyleSheet("""
                QPushButton {
                    background-color: #cccccc;
                    color: #666666;
                }
            """)
            self.stop_button.setToolTip("No job in progress to stop")
        else:
            self.stop_button.setStyleSheet("")
            self.stop_button.setToolTip("")

    def run_program(self):
        try:
            print("\nDEBUG - RunStopSection run_program:")
            print(f"self.system_controller type: {type(self.system_controller)}")
            if self.job_in_progress:
                return
            
            if not self.schedule_drop_area.current_schedule:
                QMessageBox.warning(self, "No Schedule", "Please drop a schedule to run")
                return
            
            schedule = self.schedule_drop_area.current_schedule
            mode = self.schedule_drop_area.get_mode()
            
            # Get settings from system_controller; note we do not alter system_controller.settings here
            worker_settings = self.system_controller.settings.copy()
            worker_settings.update({
                'schedule_id': schedule.schedule_id,
                'mode': mode,
                'window_start': schedule.start_time,
                'window_end': schedule.end_time,
                'water_volume': schedule.water_volume,
                'relay_unit_assignments': schedule.relay_unit_assignments,
                'desired_water_outputs': schedule.desired_water_outputs
            })
            
            schedule_details = self.database_handler.get_schedule_details(schedule.schedule_id)[0]
            schedule.animals = schedule_details['animal_ids']
            schedule.relay_unit_assignments = schedule_details.get('relay_unit_assignments', {})
            schedule.desired_water_outputs = schedule_details.get('desired_water_outputs', {})
            
            if not schedule.animals:
                QMessageBox.warning(self, "Invalid Schedule", "No animals assigned to this schedule")
                return
            
            print("\nDEBUG INFO:")
            print(f"Schedule: {schedule.__dict__}")
            print(f"Mode: {mode}")
            
            print("\nSchedule Debug Info:")
            print(f"Desired water outputs: {schedule.desired_water_outputs}")
            print(f"Relay assignments: {schedule.relay_unit_assignments}")
            
            if mode == "Staggered":
                if not schedule.start_time or not schedule.end_time:
                    QMessageBox.warning(self, "Invalid Schedule", 
                        "Schedule must have start and end times for staggered mode")
                    return
                
                if not schedule.desired_water_outputs:
                    QMessageBox.warning(self, "Invalid Schedule", 
                        "No water outputs configured for staggered mode")
                    return
                
                windows = self.database_handler.get_schedule_staggered_windows(schedule.schedule_id)
                if not windows:
                    QMessageBox.warning(self, "Invalid Schedule", 
                        "No delivery windows configured for staggered mode")
                    return
                
                schedule.window_data = windows
                window_start = datetime.fromisoformat(schedule.start_time).timestamp()
                window_end = datetime.fromisoformat(schedule.end_time).timestamp()
                
            else:  # Instant mode
                deliveries = self.database_handler.get_schedule_instant_deliveries(schedule.schedule_id)
                if not deliveries:
                    QMessageBox.warning(self, "Invalid Schedule", 
                        "This schedule has no instant delivery times configured")
                    return
                
                schedule.instant_deliveries = []
                for delivery in deliveries:
                    animal_id, _, _, datetime_str, volume, _, relay_unit_id = delivery
                    delivery_time = datetime.fromisoformat(datetime_str)
                    schedule.add_instant_delivery(animal_id, delivery_time, volume, relay_unit_id)
                
                delivery_times = [d['datetime'] for d in schedule.instant_deliveries]
                window_start = min(delivery_times).timestamp()
                window_end = max(delivery_times).timestamp()
            
            if not schedule.relay_unit_assignments:
                QMessageBox.warning(self, "Invalid Schedule", 
                    "No relay unit assignments configured")
                return
            
            self.job_in_progress = True
            self.update_button_states()
            
            QTimer.singleShot(0, lambda: self._execute_program(
                schedule, mode, window_start, window_end
            ))
            
        except Exception as e:
            self.job_in_progress = False
            self.update_button_states()
            QMessageBox.critical(self, "Error", f"Failed to run program: {str(e)}")

    def _execute_program(self, schedule, mode, window_start, window_end):
        try:
            self.run_program_callback(schedule, mode, window_start, window_end)
        except Exception as e:
            self.job_in_progress = False
            self.update_button_states()
            QMessageBox.critical(self, "Error", f"Failed to run program: {str(e)}")

    def stop_program(self):
        try:
            if not self.job_in_progress:
                return
            
            self.progress_dialog = QMessageBox(self)
            self.progress_dialog.setIcon(QMessageBox.Information)
            self.progress_dialog.setText("Stopping schedule...")
            self.progress_dialog.setStandardButtons(QMessageBox.NoButton)
            
            self.stop_button.setEnabled(False)
            self.stop_button.setText("Stopping...")
            
            self._execute_stop()
            
        except Exception as e:
            self.job_in_progress = False
            self.update_button_states()
            QMessageBox.critical(self, "Error", f"Failed to stop schedule: {str(e)}")

    def _execute_stop(self):
        try:
            self.progress_dialog.show()
            QApplication.processEvents()
            
            success = self.stop_program_callback()
            
            QApplication.processEvents()
            
            if hasattr(self, 'progress_dialog') and self.progress_dialog:
                self.progress_dialog.close()
                self.progress_dialog.deleteLater()
                self.progress_dialog = None
            
            self.job_in_progress = False
            self.update_button_states()
            self.reset_ui()
            
            if not success:
                QMessageBox.warning(self, "Warning", "Failed to stop schedule completely")
                
        except Exception as e:
            if hasattr(self, 'progress_dialog') and self.progress_dialog:
                self.progress_dialog.close()
                self.progress_dialog.deleteLater()
                self.progress_dialog = None
            QMessageBox.critical(self, "Error", f"Failed to stop schedule: {str(e)}")
            self.job_in_progress = False
            self.update_button_states()

    def reset_ui(self):
        self.job_in_progress = False
        self.update_button_states()
        self.stop_button.setText("Stop")

    def change_relay_hats(self):
        try:
            self.change_relay_hats_callback()
            self.reset_ui()
            self.update_button_states()
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to change relay hats: {str(e)}")

    def _on_mode_changed(self, mode):
        pass

    def edit_current_schedule(self):
        if not self.current_schedule:
            return
        
        try:
            dialog = EditScheduleDialog(self.current_schedule, self.database_handler, self)
            if dialog.exec_() == QDialog.Accepted:
                self.schedule_drop_area.update_table(self.current_schedule)
                self.schedule_updated.emit(self.current_schedule.schedule_id)
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to edit schedule: {str(e)}")

    def on_schedule_dropped(self, schedule):
        self.current_schedule = schedule
        self.edit_button.setEnabled(True)
        self.edit_button.setStyleSheet("""
            QPushButton {
                background-color: #17a2b8;
                color: white;
                border: none;
                border-radius: 4px;
                padding: 4px 8px;
                font-size: 12px;
                min-width: 80px;
                max-height: 24px;
            }
            QPushButton:hover {
                background-color: #138496;
            }
        """)
        self.schedule_drop_area.schedule_dropped.connect(self.on_schedule_dropped)

    def on_schedule_updated(self, updated_schedule):
        self.current_schedule = updated_schedule
        self.schedule_drop_area.update_table(updated_schedule)
        self.schedule_updated.emit(updated_schedule.schedule_id)