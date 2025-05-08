from PyQt5.QtCore import QObject, pyqtSignal, pyqtSlot, QMutex, QMutexLocker, QTimer
from datetime import datetime, timedelta
import time
from utils.volume_calculator import VolumeCalculator
import asyncio
import logging

"""
RelayWorker is a QObject-based class that manages the triggering of relays based on a schedule.

Attributes:
    finished (pyqtSignal): Signal emitted when the worker has finished its task.
    progress (pyqtSignal): Signal emitted to report progress messages.
    volume_updated (pyqtSignal): Signal emitted when the volume for an animal is updated.
    window_progress (pyqtSignal): Signal emitted to report window progress information.

Methods:
    __init__(settings, relay_handler, notification_handler, system_controller):
        Initializes the RelayWorker with the given settings, relay handler, and notification handler.
    
    run_cycle():
        Main method to run the relay triggering cycle. It schedules relay triggers based on the provided settings.
    
    trigger_relay(relay_unit_id, water_volume):
        Triggers the specified relay unit and sends a notification.
    
    stop():
        Stops the relay worker, including all scheduled timers, and emits the finished signal.

    update_system_settings(self, settings):
        Updates the worker's settings when the system's settings change.
"""

class RelayWorker(QObject):
    finished = pyqtSignal()
    progress = pyqtSignal(str)
    volume_updated = pyqtSignal(str, float)  # animal_id, total_volume
    window_progress = pyqtSignal(dict)        # window progress info

    def __init__(self, settings, relay_handler, notification_handler, system_controller):
        super().__init__()
        print("\nDEBUG - RelayWorker Initialization:")
        print(f"system_controller type: {type(system_controller)}")
        print(f"settings type: {type(settings)}")
        
        # Verify that system_controller is indeed an instance (not a dict)
        if isinstance(system_controller, dict):
            raise TypeError("Expected system_controller to be a SystemController instance, got dict.")
        
        self.system_controller = system_controller
        print(f"self.system_controller type after assignment: {type(self.system_controller)}")
        self.settings = settings  # Worker settings (a dict)
        self.relay_handler = relay_handler
        self.notification_handler = notification_handler
        self.database_handler = settings.get('database_handler')
        self.pump_controller = settings.get('pump_controller')
        self.timing_calculator = settings.get('timing_calculator')
        self.mutex = QMutex()
        self._is_running = False
        self.timers = []
        
        # Initialize main_timer
        self.main_timer = QTimer(self)
        
        # Retrieve mode and delivery instants from worker settings
        self.mode = settings.get('mode', 'instant').lower()
        self.delivery_instants = settings.get('delivery_instants', [])
        
        # Initialize tracking variables
        self.delivered_volumes = {}
        self.failed_deliveries = {}
        self.window_start = datetime.fromtimestamp(settings['window_start'])
        self.window_end = datetime.fromtimestamp(settings['window_end'])
        
        # --- FIX: Pass the SystemController instance to VolumeCalculator ---
        self.volume_calculator = VolumeCalculator(self.system_controller)
        # --------------------------------------------------------------------
        
        # Start progress monitoring timer
        self.monitor_timer = QTimer()
        self.monitor_timer.timeout.connect(self.update_window_progress)
        self.monitor_timer.start(10000)  # Update every 10 seconds
        
        self.progress.emit(f"Initialized RelayWorker with settings: {settings}")
        
        # Ensure a schedule_id is provided in the settings
        self.schedule_id = settings.get('schedule_id')
        if not self.schedule_id:
            raise ValueError("schedule_id is required in settings")
        
        # Get system-wide settings from system_controller (which is expected to have a .settings attribute)
        system_settings = self.system_controller.settings
        self.min_trigger_interval = system_settings.get('min_trigger_interval_ms', 500)
        self.cycle_interval = system_settings.get('cycle_interval', 3600)
        self.stagger_interval = system_settings.get('stagger_interval', 0.5)

    @pyqtSlot()
    def run_cycle(self):
        """Main entry point for starting the worker"""
        self._is_running = True  # Set to True when we actually start
        
        # --- Simplified logic: Only run instant cycle --- 
        if self.mode == 'instant':
            self.progress.emit(f"Starting instant cycle")
            self.run_instant_cycle()
        else:
            self.progress.emit(f"Warning: RelayWorker received non-instant mode '{self.mode}'. Staggered logic is handled elsewhere.")
            # Optionally emit finished or handle error
            self.finished.emit()
        # --- End simplification ---

    def run_instant_cycle(self):
        """Handle precise time-based deliveries"""
        with QMutexLocker(self.mutex):
            if not self.delivery_instants:
                self.progress.emit("No delivery instants configured")
                self.finished.emit()
                return

        current_time = datetime.now()
        scheduled_count = 0
        
        self.progress.emit(f"Processing {len(self.delivery_instants)} deliveries")
        
        # Group deliveries by relay unit
        deliveries_by_unit = {}
        for instant in self.delivery_instants:
            unit_id = instant['relay_unit_id']
            if unit_id not in deliveries_by_unit:
                deliveries_by_unit[unit_id] = []
            deliveries_by_unit[unit_id].append(instant)
        
        # Process each unit's deliveries
        for unit_id, unit_deliveries in deliveries_by_unit.items():
            for idx, instant in enumerate(unit_deliveries):
                try:
                    # Convert delivery_time string to datetime if needed
                    delivery_time = instant['delivery_time']
                    if isinstance(delivery_time, str):
                        delivery_time = datetime.fromisoformat(delivery_time.replace('Z', '+00:00'))
                    
                    if delivery_time > current_time:
                        base_delay = (delivery_time - current_time).total_seconds() * 1000
                        trigger_delay = idx * self.min_trigger_interval
                        total_delay = base_delay + trigger_delay
                        
                        self.progress.emit(f"Scheduling delivery in {total_delay/1000:.2f} seconds")
                        
                        timer = QTimer(self)
                        timer.setSingleShot(True)
                        timer.timeout.connect(
                            lambda i=instant: self.trigger_relay(
                                i['relay_unit_id'],
                                i['water_volume']  # Changed from 'volume' to 'water_volume'
                            )
                        )
                        timer.start(int(total_delay))
                        self.timers.append(timer)
                        scheduled_count += 1
                    else:
                        self.progress.emit(f"Skipping past delivery time: {delivery_time}")
                except Exception as e:
                    self.progress.emit(f"Error scheduling delivery: {str(e)}")
                    print(f"Instant delivery data: {instant}")  # Debug print

        if scheduled_count == 0:
            self.progress.emit("No future deliveries to schedule")
            self.finished.emit()
        else:
            self.progress.emit(f"Scheduled {scheduled_count} deliveries")
            self.check_completion()

    def check_completion(self):
        """Check if all deliveries are complete"""
        # --- Simplified: Only check for instant mode --- 
        if self.mode != 'instant':
            return # Should not be called for other modes now
        
        active_timers = [t for t in self.timers if t.isActive()]
        if not active_timers:
            self._is_running = False
            self.progress.emit("Instant delivery cycle complete.")
            self.finished.emit()
        else:
            # Check again later if timers are still running
            self.main_timer.singleShot(1000, self.check_completion)
        # --- End simplification --- 

    def trigger_relay(self, relay_unit_id, water_volume):
        with QMutexLocker(self.mutex):
            if not self._is_running:
                return
            try:
                relay_unit_id = int(relay_unit_id)
                required_triggers = self.volume_calculator.calculate_triggers(water_volume)
                triggers_dict = {str(relay_unit_id): required_triggers}
                self.progress.emit(
                    f"Triggering relay unit {relay_unit_id} for {water_volume}ml ({required_triggers} triggers)"
                )
                relay_info = self.relay_handler.trigger_relays(
                    [relay_unit_id],
                    triggers_dict,
                    self.stagger_interval
                )
                if relay_info:
                    success_msg = (
                        f"Successfully triggered relay unit {relay_unit_id} {required_triggers} times"
                    )
                    self.progress.emit(success_msg)
                    if self.notification_handler:
                        self.notification_handler.send_slack_notification(success_msg)
                return relay_info
            except Exception as e:
                self.progress.emit(f"Error triggering relay {relay_unit_id}: {str(e)}")
                return None

    def update_window_progress(self):
        """Update window progress information"""
        try:
            current_time = datetime.now()
            # --- Simplified: Only handle instant mode --- 
            if self.settings['mode'].lower() == 'instant':
                # Check if delivery_instants exists and is not empty
                if not hasattr(self, 'delivery_instants') or not self.delivery_instants:
                    progress_info = {
                        'window_progress': 100,
                        'time_remaining': 0,
                        'volume_progress': {},
                        'failed_deliveries': self.failed_deliveries.copy()
                    }
                else:
                    total_deliveries = len(self.delivery_instants)
                    completed_deliveries = sum(
                        1 for d in self.delivery_instants 
                        if isinstance(d, dict) and 'delivery_time' in d and 
                        datetime.fromisoformat(d['delivery_time'].replace('Z', '+00:00')) <= current_time
                    )
                    progress_info = {
                        'window_progress': (completed_deliveries / total_deliveries * 100) if total_deliveries > 0 else 100,
                        'time_remaining': 0, # Instant mode doesn't have a duration in the same way
                        'volume_progress': {}, # Volume tracking is complex here, maybe handle elsewhere
                        'failed_deliveries': self.failed_deliveries.copy()
                    }
            else:
                # Staggered mode progress is handled elsewhere (e.g., ScheduleController)
                # Return empty or default info if needed by UI
                progress_info = {
                    'window_progress': 0,
                    'time_remaining': 0,
                    'volume_progress': {},
                    'failed_deliveries': {}
                }
            # --- End simplification --- 
            self.window_progress.emit(progress_info)
        except Exception as e:
            self.progress.emit(f"Error updating progress: {str(e)}")
            print(f"Progress update error details: {e}")

    def check_window_completion(self):
        """Check if window is complete or needs to continue"""
        try:
            current_time = datetime.now()
            # --- Simplified: Only handle instant mode completion --- 
            if self.settings['mode'].lower() == 'instant':
                # Check if delivery_instants exists and is not empty
                if not hasattr(self, 'delivery_instants') or not self.delivery_instants:
                     all_deliveries_complete = True
                else:
                    all_deliveries_complete = all(
                        isinstance(d, dict) and 'delivery_time' in d and
                        datetime.fromisoformat(d['delivery_time'].replace('Z', '+00:00')) <= current_time
                        for d in self.delivery_instants
                    )
                
                if all_deliveries_complete:
                    self.progress.emit("All instant deliveries completed")
                    self.stop()
                else:
                    # Schedule next check if not complete
                    self.main_timer.singleShot(10000, self.check_window_completion)
            else:
                # Staggered mode completion handled elsewhere
                self.progress.emit("RelayWorker received non-instant mode for completion check.")
                # Stop worker if it was somehow started for non-instant mode
                self.stop() 
            # --- End simplification ---
        except Exception as e:
            self.progress.emit(f"Error checking completion: {str(e)}")
            print(f"Completion check error details: {e}")
            self.stop()

    def stop(self):
        with QMutexLocker(self.mutex):
            self._is_running = False
        self.monitor_timer.stop()
        self.main_timer.stop()
        for timer in self.timers:
            try:
                timer.stop()  # No need to call deleteLater() since timers are parented.
            except RuntimeError as ex:
                self.progress.emit(f"Timer already deleted: {ex}")
        self.timers.clear()
        self.progress.emit("RelayWorker stopped")
        self.finished.emit()

    def update_system_settings(self, settings):
        """Update worker settings when system settings change"""
        self.min_trigger_interval = settings.get('min_trigger_interval_ms', self.min_trigger_interval)