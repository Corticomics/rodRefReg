from PyQt5.QtCore import QObject, pyqtSignal, pyqtSlot, QMutex, QMutexLocker, QTimer
from datetime import datetime, timedelta
import time
from utils.volume_calculator import VolumeCalculator
import math
import traceback
"""
RelayWorker is a QObject-based class that manages the triggering of relays based on a schedule.

Attributes:
    finished (pyqtSignal): Signal emitted when the worker has finished its task.
    progress (pyqtSignal): Signal emitted to report progress messages.

Methods:
    __init__(settings, relay_handler, notification_handler):
        Initializes the RelayWorker with the given settings, relay handler, and notification handler.
    
    run_cycle():
        Main method to run the relay triggering cycle. It schedules relay triggers based on the provided settings.
    
    trigger_relay(relay_unit_id, water_volume, triggers=None):
        Triggers the specified relay pair and sends a notification.
    
    stop():
        Stops the relay worker, including all scheduled timers, and emits the finished signal.
"""


class RelayWorker(QObject):
    finished = pyqtSignal()
    progress = pyqtSignal(str)

    def __init__(self, settings, relay_handler, notification_handler):
        super().__init__()
        self.settings = settings
        self.relay_handler = relay_handler
        self.notification_handler = notification_handler
        self.mutex = QMutex()
        self._is_running = True
        self.timers = []
        
        # Initialize main timer
        self.main_timer = QTimer()
        self.main_timer.setSingleShot(True)
        
        # Create volume calculator instance
        self.volume_calculator = VolumeCalculator(settings)
        
        # Initialize delivered volumes tracking
        self.settings['delivered_volumes'] = self.settings.get('delivered_volumes', {})
        
        self.delivery_instants = settings.get('delivery_instants', [])
        self.mode = settings.get('mode', 'instant').lower()
        
        # Add debug logging
        self.progress.emit(f"Initialized RelayWorker with settings: {settings}")
        
    @pyqtSlot()
    def run_cycle(self):
        """Main entry point for starting the worker"""
        self._is_running = True  # Set to True when we actually start
        self.progress.emit(f"Starting {self.mode} cycle")
        
        if self.mode == 'instant':
            self.run_instant_cycle()
        else:
            self.run_staggered_cycle()

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
        
        # Group deliveries by relay unit to ensure proper timing
        deliveries_by_unit = {}
        for instant in self.delivery_instants:
            unit_id = instant['relay_unit_id']
            if unit_id not in deliveries_by_unit:
                deliveries_by_unit[unit_id] = []
            deliveries_by_unit[unit_id].append(instant)
        
        # Process each relay unit's deliveries with proper timing
        for unit_id, unit_deliveries in deliveries_by_unit.items():
            for idx, instant in enumerate(unit_deliveries):
                try:
                    delivery_time = datetime.fromisoformat(instant['delivery_time'])
                    self.progress.emit(f"Processing delivery time: {delivery_time}")
                    
                    if delivery_time > current_time:
                        # Calculate delay including stagger between triggers
                        base_delay = (delivery_time - current_time).total_seconds() * 1000
                        trigger_delay = idx * self.settings.get('min_trigger_interval_ms', 500)
                        total_delay = base_delay + trigger_delay
                        
                        self.progress.emit(f"Scheduling delivery in {total_delay/1000:.2f} seconds")
                        
                        timer = QTimer(self)
                        timer.setSingleShot(True)
                        timer.timeout.connect(
                            lambda i=instant: self.trigger_relay(
                                i['relay_unit_id'],
                                i['water_volume']
                            )
                        )
                        timer.start(int(total_delay))
                        self.timers.append(timer)
                        scheduled_count += 1
                    else:
                        self.progress.emit(f"Skipping past delivery time: {delivery_time}")
                except Exception as e:
                    self.progress.emit(f"Error scheduling delivery: {str(e)}")

        if scheduled_count == 0:
            self.progress.emit("No future deliveries to schedule")
            self.finished.emit()
        else:
            self.progress.emit(f"Scheduled {scheduled_count} deliveries")
            self.check_completion()

    def run_staggered_cycle(self):
        try:
            with QMutexLocker(self.mutex):
                if not self._is_running:
                    self.progress.emit("[DEBUG] Worker not running")
                    return

            current_time = datetime.now()
            window_start = datetime.fromtimestamp(self.settings['window_start'])
            window_end = datetime.fromtimestamp(self.settings['window_end'])
            
            self.progress.emit(f"[DEBUG] Processing window: {window_start} - {window_end}")
            
            # Verify we have required settings
            if not all(key in self.settings for key in ['target_volumes', 'relay_unit_assignments']):
                self.progress.emit("[DEBUG] Missing required settings")
                self.finished.emit()
                return
            
            deliveries_by_unit = {}
            for animal_id, target_volume in self.settings['target_volumes'].items():
                relay_unit_id = self.settings['relay_unit_assignments'].get(str(animal_id))
                
                if not relay_unit_id:
                    self.progress.emit(f"[DEBUG] No relay unit for animal {animal_id}")
                    continue
                
                if relay_unit_id not in deliveries_by_unit:
                    deliveries_by_unit[relay_unit_id] = []
                
                instant = {
                    'relay_unit_id': relay_unit_id,
                    'animal_id': animal_id,
                    'water_volume': target_volume,
                    'triggers': self.volume_calculator.calculate_triggers(target_volume)
                }
                deliveries_by_unit[relay_unit_id].append(instant)
            
            self.progress.emit(f"[DEBUG] Prepared deliveries: {deliveries_by_unit}")
            
            # Rest of the method remains the same...
        except Exception as e:
            self.progress.emit(f"Error in run_staggered_cycle: {str(e)}")
            self.finished.emit()

    def check_completion(self):
        """Check if all deliveries are complete"""
        active_timers = [t for t in self.timers if t.isActive()]
        if not active_timers:
            self._is_running = False
            self.finished.emit()
        else:
            self.main_timer.singleShot(1000, self.check_completion)

    def trigger_relay(self, relay_unit_id, water_volume, triggers=None):
        """
        Triggers a relay unit with proper error handling and verification
        """
        with QMutexLocker(self.mutex):
            if not self._is_running:
                return
            
            try:
                relay_unit_id = int(relay_unit_id)
                
                # Use provided triggers or calculate them
                required_triggers = triggers if triggers is not None else \
                                  self.volume_calculator.calculate_triggers(water_volume)
                
                triggers_dict = {str(relay_unit_id): required_triggers}
                
                self.progress.emit(
                    f"Triggering relay unit {relay_unit_id} for {water_volume}ml "
                    f"({required_triggers} triggers)"
                )
                
                # Execute the relay trigger
                success = self.relay_handler.trigger_relays(triggers_dict)
                if success:
                    self.progress.emit(f"Successfully triggered relay {relay_unit_id}")
                else:
                    self.progress.emit(f"Failed to trigger relay {relay_unit_id}")
                    
                return success
                
            except Exception as e:
                self.progress.emit(f"Error in trigger_relay: {str(e)}")
                return False

    def stop(self):
        with QMutexLocker(self.mutex):
            self._is_running = False
        self.main_timer.stop()
        for timer in self.timers:
            timer.stop()
            timer.deleteLater()
        self.timers.clear()
        self.finished.emit()
