from PyQt5.QtCore import QObject, pyqtSignal, pyqtSlot, QMutex, QMutexLocker, QTimer
from datetime import datetime, timedelta
import time
from utils.volume_calculator import VolumeCalculator
import asyncio
"""
RelayWorker is a QObject-based class that manages the triggering of relays based on a schedule.

Attributes:
    finished (pyqtSignal): Signal emitted when the worker has finished its task.
    progress (pyqtSignal): Signal emitted to report progress messages.
    volume_updated (pyqtSignal): Signal emitted when the volume for an animal is updated.
    window_progress (pyqtSignal): Signal emitted to report window progress information.

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
    volume_updated = pyqtSignal(str, float)  # animal_id, total_volume
    window_progress = pyqtSignal(dict)  # window progress info

    def __init__(self, settings, relay_handler, notification_handler):
        super().__init__()
        self.settings = settings
        self.relay_handler = relay_handler
        self.notification_handler = notification_handler
        self.database_handler = settings.get('database_handler')
        self.pump_controller = settings.get('pump_controller')
        self.timing_calculator = settings.get('timing_calculator')
        self.mutex = QMutex()
        self._is_running = False
        self.timers = []
        
        # Add main_timer initialization
        self.main_timer = QTimer(self)
        
        # Store mode and delivery instants from settings
        self.mode = settings.get('mode', 'instant').lower()
        self.delivery_instants = settings.get('delivery_instants', [])
        
        # Initialize tracking
        self.delivered_volumes = {}
        self.failed_deliveries = {}
        self.window_start = datetime.fromtimestamp(settings['window_start'])
        self.window_end = datetime.fromtimestamp(settings['window_end'])
        
        # Initialize volume calculator
        self.volume_calculator = VolumeCalculator(settings)
        
        # Progress monitoring
        self.monitor_timer = QTimer()
        self.monitor_timer.timeout.connect(self.update_window_progress)
        self.monitor_timer.start(10000)  # Update every 10 seconds
        
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
                    delivery_time = instant['datetime']
                    if delivery_time > current_time:
                        base_delay = (delivery_time - current_time).total_seconds() * 1000
                        trigger_delay = idx * self.settings.get('min_trigger_interval_ms', 500)
                        total_delay = base_delay + trigger_delay
                        
                        self.progress.emit(f"Scheduling delivery in {total_delay/1000:.2f} seconds")
                        
                        timer = QTimer(self)
                        timer.setSingleShot(True)
                        timer.timeout.connect(
                            lambda i=instant: self.trigger_relay(
                                i['relay_unit_id'],
                                i['volume']
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
        """Handle staggered deliveries with volume tracking"""
        try:
            current_time = datetime.now()
            if not (self.window_start <= current_time <= self.window_end):
                self.progress.emit("Outside delivery window")
                self.check_window_completion()
                return

            # Initialize target volumes if not present
            if 'target_volumes' not in self.settings:
                self.settings['target_volumes'] = {}
                for animal_id in self.settings.get('relay_unit_assignments', {}):
                    self.settings['target_volumes'][animal_id] = self.settings.get('water_volume', 0)

            # Get remaining volumes
            remaining_volumes = {}
            for animal_id, target in self.settings['target_volumes'].items():
                delivered = self.delivered_volumes.get(animal_id, 0)
                if delivered < target:
                    remaining_volumes[animal_id] = target - delivered

            if not remaining_volumes:
                self.progress.emit("All volumes delivered")
                self.check_window_completion()
                return

            # Schedule deliveries for each animal
            for animal_id, remaining_volume in remaining_volumes.items():
                relay_unit_id = self.settings['relay_unit_assignments'].get(str(animal_id))
                if not relay_unit_id:
                    self.progress.emit(f"No relay unit for animal {animal_id}")
                    continue

                # Calculate triggers needed
                required_triggers = self.volume_calculator.calculate_triggers(remaining_volume)
                
                delivery_data = {
                    'schedule_id': self.settings.get('schedule_id'),
                    'animal_id': animal_id,
                    'relay_unit_id': relay_unit_id,
                    'water_volume': remaining_volume,
                    'instant_time': current_time,
                    'triggers': required_triggers
                }

                timer = QTimer()
                timer.setSingleShot(True)
                timer.timeout.connect(
                    lambda d=delivery_data: self.execute_delivery(d)
                )
                timer.start(1000)  # Start after 1 second
                self.timers.append(timer)

            # Schedule next cycle
            if self._is_running:
                self.main_timer.singleShot(
                    self.settings.get('cycle_interval', 3600) * 1000,
                    self.run_staggered_cycle
                )

        except Exception as e:
            self.progress.emit(f"Error in staggered cycle: {str(e)}")
            self.check_window_completion()

    async def execute_delivery(self, delivery_data):
        """Execute delivery with volume tracking and compensation"""
        try:
            animal_id = delivery_data['animal_id']
            current_delivered = self.delivered_volumes.get(animal_id, 0)
            target_volume = self.settings['target_volumes'][animal_id]
            
            if current_delivered >= target_volume:
                return True

            # Check for failed deliveries and adjust volume
            failed_count = self.failed_deliveries.get(animal_id, 0)
            if failed_count > 0:
                # Increase volume by up to 20% based on failures
                volume_increase = min(failed_count * 0.05, 0.2)  # 5% per failure, max 20%
                adjusted_volume = delivery_data['water_volume'] * (1 + volume_increase)
                delivery_data['water_volume'] = min(
                    adjusted_volume,
                    target_volume - current_delivered
                )

            success = await self.pump_controller.dispense_water(
                delivery_data['relay_unit_id'],
                delivery_data['water_volume'],
                delivery_data['triggers']
            )

            if success:
                with QMutexLocker(self.mutex):
                    # Update delivered volume
                    actual_volume = delivery_data['water_volume']
                    self.delivered_volumes[animal_id] = current_delivered + actual_volume
                    self.failed_deliveries[animal_id] = 0  # Reset failures

                    # Log success
                    await self.database_handler.log_delivery({
                        'schedule_id': delivery_data['schedule_id'],
                        'animal_id': animal_id,
                        'relay_unit_id': delivery_data['relay_unit_id'],
                        'volume_delivered': actual_volume,
                        'timestamp': delivery_data['instant_time'].isoformat(),
                        'status': 'completed'
                    })

                # Emit progress
                self.volume_updated.emit(str(animal_id), self.delivered_volumes[animal_id])
                self.progress.emit(
                    f"Delivered {actual_volume:.3f}mL to animal {animal_id} "
                    f"(Total: {self.delivered_volumes[animal_id]:.3f}mL)"
                )

            else:
                # Handle failure
                with QMutexLocker(self.mutex):
                    self.failed_deliveries[animal_id] = failed_count + 1
                    
                    await self.database_handler.log_delivery({
                        'schedule_id': delivery_data['schedule_id'],
                        'animal_id': animal_id,
                        'relay_unit_id': delivery_data['relay_unit_id'],
                        'volume_delivered': 0,
                        'timestamp': delivery_data['instant_time'].isoformat(),
                        'status': 'failed'
                    })

                self.schedule_retry(delivery_data)

            return success

        except Exception as e:
            self.progress.emit(f"Delivery error: {str(e)}")
            return False

    def schedule_retry(self, delivery_data):
        """Schedule a retry for failed delivery"""
        retry_delay = 30  # seconds
        retry_time = datetime.now() + timedelta(seconds=retry_delay)
        
        # Don't retry if outside window
        window_end = datetime.fromtimestamp(self.settings['window_end'])
        if retry_time >= window_end:
            self.progress.emit(f"Cannot retry delivery - outside window")
            return
        
        delivery_data['instant_time'] = retry_time
        
        timer = QTimer(self)
        timer.setSingleShot(True)
        timer.timeout.connect(
            lambda d=delivery_data: self.execute_delivery(d)
        )
        timer.start(retry_delay * 1000)
        self.timers.append(timer)
        
        self.progress.emit(
            f"Scheduled retry for animal {delivery_data['animal_id']} "
            f"in {retry_delay} seconds"
        )

    def check_completion(self):
        """Check if all deliveries are complete"""
        active_timers = [t for t in self.timers if t.isActive()]
        if not active_timers:
            self._is_running = False
            self.finished.emit()
        else:
            self.main_timer.singleShot(1000, self.check_completion)

    def trigger_relay(self, relay_unit_id, water_volume):
        with QMutexLocker(self.mutex):
            if not self._is_running:
                return
            
            try:
                relay_unit_id = int(relay_unit_id)
                required_triggers = self.volume_calculator.calculate_triggers(water_volume)
                triggers_dict = {str(relay_unit_id): required_triggers}
                
                self.progress.emit(
                    f"Triggering relay unit {relay_unit_id} for {water_volume}ml "
                    f"({required_triggers} triggers)"
                )
                
                relay_info = self.relay_handler.trigger_relays(
                    [relay_unit_id],
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
                return relay_info
                
            except Exception as e:
                error_msg = f"Error triggering relay {relay_unit_id}: {str(e)}"
                self.progress.emit(error_msg)
                return None

    def update_window_progress(self):
        """Update window progress information"""
        try:
            current_time = datetime.now()
            window_duration = (self.window_end - self.window_start).total_seconds()
            elapsed_time = (current_time - self.window_start).total_seconds()
            progress_percent = min(100, (elapsed_time / window_duration) * 100)

            # Calculate volume progress for each animal
            volume_progress = {}
            for animal_id, target in self.settings['target_volumes'].items():
                delivered = self.delivered_volumes.get(animal_id, 0)
                volume_progress[animal_id] = {
                    'delivered': delivered,
                    'target': target,
                    'percent': (delivered / target) * 100 if target > 0 else 0
                }

            progress_info = {
                'window_progress': progress_percent,
                'time_remaining': max(0, (self.window_end - current_time).total_seconds()),
                'volume_progress': volume_progress,
                'failed_deliveries': self.failed_deliveries.copy()
            }

            self.window_progress.emit(progress_info)

        except Exception as e:
            self.progress.emit(f"Error updating progress: {str(e)}")

    def check_window_completion(self):
        """Check if window is complete or needs to continue"""
        try:
            current_time = datetime.now()
            all_volumes_delivered = all(
                self.delivered_volumes.get(aid, 0) >= target
                for aid, target in self.settings['target_volumes'].items()
            )

            if all_volumes_delivered or current_time >= self.window_end:
                # Log final status
                for animal_id, target in self.settings['target_volumes'].items():
                    delivered = self.delivered_volumes.get(animal_id, 0)
                    self.progress.emit(
                        f"Final delivery for animal {animal_id}: "
                        f"{delivered:.3f}mL of {target:.3f}mL "
                        f"({(delivered/target)*100:.1f}%)"
                    )

                self.stop()
            else:
                # Continue monitoring
                self.main_timer.singleShot(10000, self.check_window_completion)

        except Exception as e:
            self.progress.emit(f"Error checking completion: {str(e)}")
            self.stop()

    def stop(self):
        """Stop all timers and clean up"""
        with QMutexLocker(self.mutex):
            self._is_running = False
            
        self.monitor_timer.stop()
        self.main_timer.stop()
        
        for timer in self.timers:
            timer.stop()
            timer.deleteLater()
        self.timers.clear()
        
        self.progress.emit("RelayWorker stopped")
        self.finished.emit()
