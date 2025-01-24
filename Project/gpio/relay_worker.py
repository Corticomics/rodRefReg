from PyQt5.QtCore import QObject, pyqtSignal, pyqtSlot, QMutex, QMutexLocker, QTimer
from datetime import datetime, timedelta
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
        """Handle staggered deliveries within time window"""
        try:
            with QMutexLocker(self.mutex):
                if not self._is_running:
                    return

            current_time = datetime.now()
            window_start = datetime.fromtimestamp(self.settings['window_start'])
            window_end = datetime.fromtimestamp(self.settings['window_end'])
            
            if window_start <= current_time <= window_end:
                # Get delivery settings
                target_volumes = self.settings.get('target_volumes', {})
                relay_assignments = self.settings.get('relay_unit_assignments', {})
                delivered_volumes = self.settings.get('delivered_volumes', {})

                # Prepare animals data for timing calculator
                animals_data = [
                    {
                        'animal_id': animal_id,
                        'volume_ml': target_volumes[animal_id] - delivered_volumes.get(animal_id, 0)
                    }
                    for animal_id in target_volumes
                    if delivered_volumes.get(animal_id, 0) < target_volumes[animal_id]
                ]

                if not animals_data:
                    self.progress.emit("All volumes delivered")
                    self.finished.emit()
                    return

                # Calculate timing plan for remaining volumes
                timing_plan = self.timing_calculator.calculate_staggered_timing(
                    window_start, window_end, animals_data
                )

                # Schedule deliveries based on timing plan
                for animal_id, schedule in timing_plan['schedule'].items():
                    relay_unit_id = relay_assignments.get(str(animal_id))
                    if not relay_unit_id:
                        self.progress.emit(f"No relay unit assigned for animal {animal_id}")
                        continue

                    # Calculate volume per cycle
                    total_volume = target_volumes[animal_id]
                    volume_per_cycle = total_volume / schedule['total_cycles']

                    # Schedule triggers for this cycle
                    for trigger in range(schedule['triggers_per_cycle']):
                        delay_ms = (schedule['cycle_start_offset'] * 1000 + 
                                  trigger * schedule['trigger_interval_ms'])
                        
                        instant = {
                            'relay_unit_id': relay_unit_id,
                            'water_volume': volume_per_cycle,
                            'animal_id': animal_id,
                            'triggers': 1  # Single trigger per timer
                        }

                        timer = QTimer(self)
                        timer.setSingleShot(True)
                        timer.timeout.connect(
                            lambda i=instant: self.execute_delivery(i)
                        )
                        timer.start(int(delay_ms))
                        self.timers.append(timer)
                        
                        self.progress.emit(
                            f"Scheduled {volume_per_cycle:.3f}mL for animal {animal_id} "
                            f"on relay {relay_unit_id} at {delay_ms/1000:.1f}s"
                        )

                # Schedule next cycle if needed
                next_cycle_time = current_time + timedelta(seconds=timing_plan['cycle_interval'])
                if next_cycle_time <= window_end:
                    self.main_timer.singleShot(
                        int(timing_plan['cycle_interval'] * 1000),
                        self.run_staggered_cycle
                    )
                else:
                    self.check_completion()

        except Exception as e:
            self.progress.emit(f"Error in staggered cycle: {str(e)}")
            self.finished.emit()

    def execute_delivery(self, instant):
        """Execute a single delivery with proper tracking"""
        try:
            # Calculate required triggers for this volume
            triggers_needed = self.volume_calculator.calculate_triggers(instant['water_volume'])
            
            # Get relay unit from relay handler
            relay_unit = self.relay_handler.get_relay_unit(instant['relay_unit_id'])
            if not relay_unit:
                self.progress.emit(f"Error: Could not find relay unit {instant['relay_unit_id']}")
                return False
            
            # Execute triggers with minimum interval for reliable pump operation
            success = self._execute_triggers(
                relay_unit,
                triggers_needed
            )
            
            if success:
                # Update delivered volume
                animal_id = instant['animal_id']
                with QMutexLocker(self.mutex):
                    # Calculate actual delivered volume based on triggers
                    actual_volume = (triggers_needed * self.settings.get('pump_volume_ul', 50)) / 1000
                    self.settings['delivered_volumes'][animal_id] = (
                        self.settings['delivered_volumes'].get(animal_id, 0) + 
                        actual_volume
                    )
                
                self.progress.emit(
                    f"Delivered {actual_volume:.3f}mL to animal {animal_id} "
                    f"using {triggers_needed} triggers"
                )
                
            return success
            
        except Exception as e:
            self.progress.emit(f"Delivery error: {str(e)}")
            return False

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
