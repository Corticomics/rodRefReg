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
        
        # Add schedule_id to instance variables
        self.schedule_id = settings.get('schedule_id')
        if not self.schedule_id:
            raise ValueError("schedule_id is required in settings")

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
                    # Convert delivery_time string to datetime if needed
                    delivery_time = instant['delivery_time']
                    if isinstance(delivery_time, str):
                        delivery_time = datetime.fromisoformat(delivery_time.replace('Z', '+00:00'))
                    
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

    def run_staggered_cycle(self):
        """Handle staggered deliveries with individual time windows"""
        try:
            current_time = datetime.now()
            
            # Debug print settings
            print("\nStaggered Cycle Debug Info:")
            print(f"Current time: {current_time}")
            
            # Calculate optimal cycle interval based on window duration and volumes
            window_duration = (self.window_end - self.window_start).total_seconds()
            
            # Get the animal with the largest volume to determine minimum cycles needed
            max_volume = max(
                float(vol) for vol in self.settings.get('desired_water_outputs', {}).values()
            )
            
            # Calculate minimum number of cycles needed based on max volume and max per cycle
            max_volume_per_cycle = self.settings.get('max_cycle_volume', 0.2)  # 0.2ml max per cycle
            min_cycles_needed = max_volume / max_volume_per_cycle
            
            # Calculate cycle interval (ensure at least 2 cycles in the window)
            cycle_interval = min(
                window_duration / max(min_cycles_needed, 2),  # At least 2 cycles
                window_duration / 2  # Maximum interval is half the window
            )
            
            # Check feasibility when initializing windows
            if not hasattr(self, 'animal_windows') or not self.animal_windows:
                print("Initializing animal windows")
                self.animal_windows = {}
                
                # Get relay assignments and target volumes
                relay_assignments = self.settings.get('relay_unit_assignments', {})
                desired_outputs = self.settings.get('desired_water_outputs', {})
                
                # Get individual animal windows from settings
                animal_windows = self.settings.get('animal_windows', {})
                
                for animal_id in relay_assignments:
                    target_volume = float(desired_outputs.get(str(animal_id), 0.0))
                    
                    # Get individual window times for this animal
                    animal_window = animal_windows.get(str(animal_id), {})
                    window_start = datetime.fromisoformat(animal_window.get('start', self.window_start.isoformat()))
                    window_end = datetime.fromisoformat(animal_window.get('end', self.window_end.isoformat()))
                    
                    # Calculate volume per cycle for this animal
                    window_duration = (window_end - window_start).total_seconds()
                    cycles_in_window = window_duration / cycle_interval
                    volume_per_cycle = min(
                        target_volume / cycles_in_window,
                        max_volume_per_cycle
                    )
                    
                    self.animal_windows[animal_id] = {
                        'start': window_start,
                        'end': window_end,
                        'last_delivery': None,
                        'relay_unit': relay_assignments.get(str(animal_id)),
                        'target_volume': target_volume,
                        'volume_per_cycle': volume_per_cycle
                    }
                    print(f"Created window for animal {animal_id}: {self.animal_windows[animal_id]}")
                    print(f"Volume per cycle: {volume_per_cycle}ml")
            
            # Get active animals for current time
            active_animals = {}
            print(f"Checking active animals at {current_time}")
            print(f"Window start: {self.window_start}, Window end: {self.window_end}")
            print(f"Animal windows: {self.animal_windows.items()}")
            
            # Check if current time is within the overall window
            if current_time < self.window_start:
                print(f"Current time ({current_time}) is before window start ({self.window_start})")
                # Schedule next check at window start
                delay_ms = int((self.window_start - current_time).total_seconds() * 1000)
                self.main_timer.singleShot(delay_ms, self.run_staggered_cycle)
                return
            
            if current_time > self.window_end:
                print(f"Current time ({current_time}) is after window end ({self.window_end})")
                self.check_window_completion()
                return
            
            for animal_id, window in self.animal_windows.items():
                if window['start'] <= current_time <= window['end']:
                    delivered = self.delivered_volumes.get(animal_id, 0)
                    target = window['target_volume']
                    print(f"Animal {animal_id}: delivered={delivered}, target={target}")
                    
                    if delivered < target:
                        active_animals[animal_id] = {
                            'remaining': target - delivered,
                            'last_delivery': window['last_delivery'],
                            'relay_unit': window['relay_unit']
                        }
                        print(f"Animal {animal_id} is active with {target-delivered}mL remaining")

            print(f"Active animals: {active_animals.items()}")
            if not active_animals:
                self.progress.emit("No active animals in current time window")
                logging.warning("No active animals found")
                logging.debug(f"Delivered volumes: {self.delivered_volumes}")
                self.check_window_completion()
                return

            # Schedule deliveries with proper queuing
            success = self.schedule_deliveries(active_animals)
            if not success:
                self.progress.emit("Failed to schedule deliveries")
                return
                
            # Schedule next cycle
            next_cycle = int(cycle_interval * 1000)
            self.main_timer.singleShot(next_cycle, self.run_staggered_cycle)

        except Exception as e:
            self.progress.emit(f"Error in staggered cycle: {str(e)}")
            logging.error(f"Staggered cycle error: {str(e)}", exc_info=True)
            self.check_window_completion()

    async def execute_delivery(self, delivery_data):
        """Execute delivery with volume tracking and compensation"""
        try:
            animal_id = delivery_data['animal_id']
            current_delivered = self.delivered_volumes.get(animal_id, 0)
            
            # Get target volume from animal windows instead of settings
            target_volume = self.animal_windows[animal_id]['target_volume']
            
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
            
            if self.settings['mode'].lower() == 'instant':
                # For instant mode, just track completion of scheduled deliveries
                total_deliveries = len(self.delivery_instants)
                completed_deliveries = sum(1 for d in self.delivery_instants 
                                        if datetime.fromisoformat(d['delivery_time'].replace('Z', '+00:00')) <= current_time)
                
                progress_info = {
                    'window_progress': (completed_deliveries / total_deliveries * 100) if total_deliveries > 0 else 100,
                    'time_remaining': 0,  # Not applicable for instant mode
                    'volume_progress': {},  # No target volumes in instant mode
                    'failed_deliveries': self.failed_deliveries.copy()
                }
                
            else:  # Staggered mode
                window_duration = (self.window_end - self.window_start).total_seconds()
                elapsed_time = (current_time - self.window_start).total_seconds()
                progress_percent = min(100, (elapsed_time / window_duration) * 100)

                # Calculate volume progress for each animal
                volume_progress = {}
                for animal_id, target in self.settings.get('target_volumes', {}).items():
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
            print(f"Progress update error details: {e}")  # Additional debug info

    def check_window_completion(self):
        """Check if window is complete or needs to continue"""
        try:
            current_time = datetime.now()
            
            if self.settings['mode'].lower() == 'instant':
                # For instant mode, check if all scheduled deliveries are past their time
                all_deliveries_complete = all(
                    datetime.fromisoformat(d['delivery_time'].replace('Z', '+00:00')) <= current_time
                    for d in self.delivery_instants
                )
                
                if all_deliveries_complete:
                    self.progress.emit("All instant deliveries completed")
                    self.stop()
                else:
                    # Continue monitoring
                    self.main_timer.singleShot(10000, self.check_window_completion)
                    
            else:  # Staggered mode
                # First check if target_volumes exists in settings
                target_volumes = self.settings.get('target_volumes', {})
                
                if not target_volumes:
                    # If no target volumes, just check time
                    if current_time >= self.window_end:
                        self.progress.emit("Window time completed")
                        self.stop()
                    else:
                        self.main_timer.singleShot(10000, self.check_window_completion)
                    return

                # If we have target volumes, check them
                all_volumes_delivered = all(
                    self.delivered_volumes.get(aid, 0) >= target
                    for aid, target in target_volumes.items()
                )

                if all_volumes_delivered or current_time >= self.window_end:
                    # Log final status
                    for animal_id, target in target_volumes.items():
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
            print(f"Completion check error details: {e}")  # Additional debug info
            print(f"Current settings: {self.settings}")  # Print settings for debugging
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

    def setup_schedule(self, schedule):
        """Setup delivery windows for each animal"""
        try:
            self.animal_windows = {}
            self.delivered_volumes = {}
            
            # Get animal assignments and volumes
            animal_ids = schedule.get('animal_ids', [])
            relay_assignments = schedule.get('relay_unit_assignments', {})
            desired_outputs = schedule.get('desired_water_outputs', {})
            base_volume = schedule.get('water_volume', 0.0)
            
            # Get staggered windows data
            window_data = schedule.get('window_data', {})
            
            print(f"Setting up schedule with {len(animal_ids)} animals")
            
            # Setup windows for each animal
            for animal_id in animal_ids:
                str_animal_id = str(animal_id)
                relay_unit = relay_assignments.get(str_animal_id)
                
                if relay_unit is None:
                    logging.warning(f"No relay unit assigned for animal {animal_id}")
                    continue
                
                # Get animal-specific windows or use default
                if str_animal_id in window_data and window_data[str_animal_id]:
                    # Use first window for now (can be extended to handle multiple windows)
                    window = window_data[str_animal_id][0]
                    window_start = datetime.fromisoformat(window['start_time'])
                    window_end = datetime.fromisoformat(window['end_time'])
                    target_volume = window['volume']
                else:
                    # Fallback to default schedule window
                    window_start = datetime.fromisoformat(schedule['start_time'])
                    window_end = datetime.fromisoformat(schedule['end_time'])
                    target_volume = desired_outputs.get(str_animal_id, base_volume)
                
                self.animal_windows[animal_id] = {
                    'start': window_start,
                    'end': window_end,
                    'relay_unit': relay_unit,
                    'target_volume': target_volume,
                    'last_delivery': 0
                }
                self.delivered_volumes[animal_id] = 0
                
                print(f"Added window for animal {animal_id}: "
                      f"start={window_start}, end={window_end}, "
                      f"target={target_volume}mL, relay={relay_unit}")
            
            return len(self.animal_windows) > 0
            
        except Exception as e:
            logging.error(f"Error setting up schedule: {str(e)}")
            return False

    def check_active_animals(self):
        """Check which animals are active in the current time window"""
        if not self.animal_windows:
            logging.warning("No animal windows configured")
            return {}
            
        current_time = time.time()
        active_animals = {}
        
        for animal_id, window in self.animal_windows.items():
            if window['start'] <= current_time <= window['end']:
                delivered = self.delivered_volumes.get(animal_id, 0)
                target = window['target_volume']
                
                if delivered < target:
                    active_animals[animal_id] = {
                        'remaining': target - delivered,
                        'last_delivery': window['last_delivery'],
                        'relay_unit': window['relay_unit']
                    }
                    
        if not active_animals:
            logging.debug(f"No active animals at {datetime.fromtimestamp(current_time)}")
            logging.debug(f"Windows: {self.animal_windows}")
            
        return active_animals
    
    def update_delivery(self, animal_id, volume):
        """Update delivered volume for an animal"""
        if animal_id in self.delivered_volumes:
            self.delivered_volumes[animal_id] += volume
            self.animal_windows[animal_id]['last_delivery'] = time.time()
            logging.debug(f"Updated delivery for animal {animal_id}: {self.delivered_volumes[animal_id]}mL")
            
    def is_schedule_complete(self):
        """Check if all animals have received their target volumes"""
        for animal_id, window in self.animal_windows.items():
            delivered = self.delivered_volumes.get(animal_id, 0)
            if delivered < window['target_volume']:
                return False
        return True

    def calculate_schedule_feasibility(self):
        """
        Calculate if all deliveries can be completed within their time windows.
        Returns (is_feasible, details)
        """
        try:
            total_triggers = 0
            time_per_trigger = 0.5  # Base time for each trigger in seconds
            setup_time = 0.1  # Setup time for each delivery in seconds
            
            # Calculate total triggers needed for all animals
            for animal_id, window in self.animal_windows.items():
                volume = window['target_volume']
                triggers = self.volume_calculator.calculate_triggers(volume)
                total_triggers += triggers
            
            # Calculate total time needed
            total_time_needed = (
                (total_triggers * time_per_trigger) +  # Time for all triggers
                (len(self.animal_windows) * setup_time)  # Setup time for each animal
            )
            
            # Get shortest window duration
            window_durations = []
            for window in self.animal_windows.values():
                duration = (window['end'] - window['start']).total_seconds()
                window_durations.append(duration)
            
            shortest_window = min(window_durations) if window_durations else 0
            
            is_feasible = total_time_needed <= shortest_window
            details = {
                'total_triggers': total_triggers,
                'time_needed': total_time_needed,
                'shortest_window': shortest_window,
                'is_feasible': is_feasible
            }
            
            return is_feasible, details
            
        except Exception as e:
            logging.error(f"Error calculating feasibility: {str(e)}")
            return False, {'error': str(e)}

    def schedule_deliveries(self, active_animals):
        """Schedule deliveries with proper queuing for overlapping windows"""
        try:
            # Sort animals by remaining volume (descending) to prioritize larger volumes
            sorted_animals = sorted(
                active_animals.items(),
                key=lambda x: x[1]['remaining'],
                reverse=True
            )
            
            base_time = datetime.now()
            cumulative_delay = 0
            
            for animal_id, data in sorted_animals:
                volume_per_cycle = self.animal_windows[animal_id]['volume_per_cycle']
                cycle_volume = min(data['remaining'], volume_per_cycle)
                
                if cycle_volume <= 0:
                    continue
                    
                # Calculate triggers needed
                triggers = self.volume_calculator.calculate_triggers(cycle_volume)
                trigger_time = triggers * 0.5  # 0.5 seconds per trigger
                
                delivery_data = {
                    'schedule_id': self.schedule_id,  # Use instance variable
                    'animal_id': animal_id,
                    'relay_unit_id': data['relay_unit'],
                    'water_volume': cycle_volume,
                    'instant_time': base_time + timedelta(seconds=cumulative_delay),
                    'triggers': triggers
                }
                
                # Schedule with cumulative delay
                timer = QTimer()
                timer.setSingleShot(True)
                timer.timeout.connect(
                    lambda d=delivery_data: self._handle_delivery(d)
                )
                timer.start(int(cumulative_delay * 1000))
                self.timers.append(timer)
                
                print(f"Scheduled delivery for animal {animal_id}: "
                      f"{cycle_volume}mL in {cumulative_delay}s")
                
                # Update cumulative delay for next delivery
                cumulative_delay += trigger_time + 0.1  # Add 0.1s setup time between deliveries
                
            return True
            
        except Exception as e:
            logging.error(f"Error scheduling deliveries: {str(e)}")
            return False

    def _handle_delivery(self, delivery_data):
        """Synchronously handle a delivery"""
        try:
            # Ensure schedule_id is present
            if 'schedule_id' not in delivery_data:
                delivery_data['schedule_id'] = self.schedule_id
                
            animal_id = delivery_data['animal_id']
            current_delivered = self.delivered_volumes.get(animal_id, 0)
            
            # Get target volume from animal windows
            target_volume = self.animal_windows[animal_id]['target_volume']
            
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

            # Trigger the relay directly
            success = self.trigger_relay(
                delivery_data['relay_unit_id'],
                delivery_data['water_volume']
            )

            if success:
                with QMutexLocker(self.mutex):
                    # Update delivered volume
                    actual_volume = delivery_data['water_volume']
                    self.delivered_volumes[animal_id] = current_delivered + actual_volume
                    self.failed_deliveries[animal_id] = 0  # Reset failures

                    # Ensure all required fields are present
                    delivery_log = {
                        'schedule_id': self.schedule_id,  # Use instance variable
                        'animal_id': animal_id,
                        'relay_unit_id': delivery_data['relay_unit_id'],
                        'volume_delivered': actual_volume,
                        'timestamp': delivery_data['instant_time'].isoformat(),
                        'status': 'completed'
                    }
                    
                    # Log success
                    if self.database_handler:
                        self.database_handler.log_delivery(delivery_log)

                self.volume_updated.emit(str(animal_id), self.delivered_volumes[animal_id])
                self.progress.emit(
                    f"Delivered {actual_volume:.3f}mL to animal {animal_id} "
                    f"(Total: {self.delivered_volumes[animal_id]:.3f}mL)"
                )

            else:
                # Handle failure
                with QMutexLocker(self.mutex):
                    self.failed_deliveries[animal_id] = failed_count + 1
                    
                    if self.database_handler:
                        delivery_log = {
                            'schedule_id': self.schedule_id,  # Use instance variable
                            'animal_id': animal_id,
                            'relay_unit_id': delivery_data['relay_unit_id'],
                            'volume_delivered': 0,
                            'timestamp': delivery_data['instant_time'].isoformat(),
                            'status': 'failed'
                        }
                        self.database_handler.log_delivery(delivery_log)

                self.schedule_retry(delivery_data)

            return success

        except Exception as e:
            self.progress.emit(f"Delivery error: {str(e)}")
            return False
