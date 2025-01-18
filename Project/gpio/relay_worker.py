from PyQt5.QtCore import QObject, pyqtSignal, pyqtSlot, QMutex, QMutexLocker, QTimer
from datetime import datetime
import time
from utils.volume_calculator import VolumeCalculator
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
    
    trigger_relay(relay_pair):
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
        self._is_running = False
        self.mutex = QMutex()
        self.main_timer = QTimer(self)
        self.timers = []  # Keep track of active timers
        self.delivery_instants = settings.get('delivery_instants', [])
        self.mode = settings.get('mode', 'instant').lower()
        
        # Initialize VolumeCalculator
        self.volume_calculator = VolumeCalculator(settings)
        
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
        """Handle staggered deliveries within time window"""
        with QMutexLocker(self.mutex):
            if not self._is_running:
                return

        current_time = int(time.time())
        window_start = self.settings['window_start']
        window_end = self.settings['window_end']
        
        if window_start <= current_time <= window_end:
            cycle_interval = self.settings.get('cycle_interval')
            stagger_interval = self.settings.get('stagger_interval')
            
            # Track delivered volumes per animal
            delivered_volumes = self.settings.get('delivered_volumes', {})
            target_volumes = self.settings.get('target_volumes', {})
            
            for relay_unit_id, triggers_per_cycle in self.settings['num_triggers'].items():
                animal_id = str(relay_unit_id)  # Assuming 1:1 mapping
                delivered = delivered_volumes.get(animal_id, 0)
                target = target_volumes.get(animal_id, 0)
                
                if delivered < target:
                    # Calculate remaining volume and triggers
                    remaining_volume = target - delivered
                    remaining_triggers = self.volume_calculator.calculate_triggers(remaining_volume)
                    triggers_this_cycle = min(triggers_per_cycle, remaining_triggers)
                    
                    for i in range(triggers_this_cycle):
                        delay = i * stagger_interval * 1000
                        timer = QTimer(self)
                        timer.setSingleShot(True)
                        timer.timeout.connect(
                            lambda r=relay_unit_id, v=remaining_volume: self.trigger_relay(r, v)
                        )
                        timer.start(int(delay))
                        self.timers.append(timer)
                    
                    # Update delivered volume
                    volume_this_cycle = (triggers_this_cycle * self.pump_volume_ul) / 1000
                    delivered_volumes[animal_id] = delivered + volume_this_cycle
            
            # Update settings with new volumes
            self.settings['delivered_volumes'] = delivered_volumes
            
            # Check if all volumes are complete
            all_complete = all(
                delivered_volumes.get(aid, 0) >= target_volumes.get(aid, 0)
                for aid in target_volumes
            )
            
            if not all_complete:
                self.main_timer.singleShot(int(cycle_interval * 1000), self.run_staggered_cycle)
            else:
                self._is_running = False
                self.finished.emit()
        else:
            self._is_running = False
            self.finished.emit()

    def check_completion(self):
        """Check if all deliveries are complete"""
        active_timers = [t for t in self.timers if t.isActive()]
        if not active_timers:
            self._is_running = False
            self.finished.emit()
        else:
            self.main_timer.singleShot(1000, self.check_completion)

    def trigger_relay(self, relay_unit_id, water_volume):
        """
        Triggers a relay unit with proper error handling and verification
        """
        with QMutexLocker(self.mutex):
            if not self._is_running:
                return
            
            try:
                # Ensure relay_unit_id is properly typed
                relay_unit_id = int(relay_unit_id)
                
                # Calculate required triggers based on water volume
                required_triggers = self.volume_calculator.calculate_triggers(water_volume)
                
                # Create triggers dictionary with proper string keys
                triggers_dict = {str(relay_unit_id): required_triggers}
                
                # Log attempt
                self.progress.emit(
                    f"Triggering relay unit {relay_unit_id} for {water_volume}ml "
                    f"({required_triggers} triggers)"
                )
                
                # Execute triggers with verification
                relay_info = self.relay_handler.trigger_relays(
                    [relay_unit_id],  # Pass as list of integers
                    triggers_dict,
                    self.settings.get('stagger', 0.5)
                )
                
                if relay_info:
                    success_msg = (
                        f"Successfully triggered relay unit {relay_unit_id} "
                        f"{required_triggers} times"
                    )
                    self.progress.emit(success_msg)
                    if self.notification_handler:
                        self.notification_handler.send_slack_notification(success_msg)
                        self.notification_handler.log_pump_trigger(success_msg)
                return relay_info
                
            except Exception as e:
                error_msg = f"Error triggering relay {relay_unit_id}: {str(e)}"
                self.progress.emit(error_msg)
                if self.notification_handler:
                    self.notification_handler.log_pump_trigger(error_msg)
                return None

    def stop(self):
        with QMutexLocker(self.mutex):
            self._is_running = False
        self.main_timer.stop()
        for timer in self.timers:
            timer.stop()
            timer.deleteLater()
        self.timers.clear()
        self.finished.emit()
