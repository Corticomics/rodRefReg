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

    def run_staggered_cycle(self):
        """Handle staggered deliveries with individual time windows"""
        try:
            current_time = datetime.now()
            
            print("\nStaggered Cycle Debug Info:")
            print(f"Current time: {current_time}")
            
            window_duration = (self.window_end - self.window_start).total_seconds()
            max_volume = max(
                float(vol) for vol in self.settings.get('desired_water_outputs', {}).values()
            )
            max_volume_per_cycle = self.settings.get('max_cycle_volume', 0.2)
            min_cycles_needed = max_volume / max_volume_per_cycle
            
            cycle_interval = min(
                window_duration / max(min_cycles_needed, 2),
                window_duration / 2
            )
            
            if not hasattr(self, 'animal_windows') or not self.animal_windows:
                print("Initializing animal windows")
                self.animal_windows = {}
                relay_assignments = self.settings.get('relay_unit_assignments', {})
                desired_outputs = self.settings.get('desired_water_outputs', {})
                animal_windows = self.settings.get('animal_windows', {})
                
                for animal_id in relay_assignments:
                    target_volume = float(desired_outputs.get(str(animal_id), 0.0))
                    animal_window = animal_windows.get(str(animal_id), {})
                    window_start = datetime.fromisoformat(animal_window.get('start', self.window_start.isoformat()))
                    window_end = datetime.fromisoformat(animal_window.get('end', self.window_end.isoformat()))
                    
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
            
            active_animals = {}
            print(f"Checking active animals at {current_time}")
            print(f"GLOBAL Window start: {self.window_start}, Window end: {self.window_end}")
            print(f"Animal windows: {self.animal_windows.items()}")
            
            # Global window check - entire system is inactive outside this window
            if current_time < self.window_start:
                print(f"Current time ({current_time}) is before GLOBAL window start ({self.window_start})")
                self.progress.emit("System inactive: Before global schedule window")
                delay_ms = int((self.window_start - current_time).total_seconds() * 1000)
                self.main_timer.singleShot(delay_ms, self.run_staggered_cycle)
                return
            
            # Global window check - entire system is inactive outside this window
            if current_time > self.window_end:
                print(f"Current time ({current_time}) is after GLOBAL window end ({self.window_end})")
                self.progress.emit("System inactive: After global schedule window")
                self.check_window_completion()
                return
            
            for animal_id, window in self.animal_windows.items():
                # Individual animal window check
                if window['start'] <= current_time <= window['end']:
                    delivered = self.delivered_volumes.get(animal_id, 0)
                    target = window['target_volume']
                    print(f"Animal {animal_id}: IN WINDOW, delivered={delivered}, target={target}")
                    
                    if delivered < target:
                        active_animals[animal_id] = {
                            'remaining': target - delivered,
                            'last_delivery': window['last_delivery'],
                            'relay_unit': window['relay_unit']
                        }
                        print(f"Animal {animal_id} is ACTIVE with {target-delivered}mL remaining")
                else:
                    print(f"Animal {animal_id}: OUTSIDE WINDOW ({window['start']} to {window['end']})")
            
            print(f"Active animals for this cycle: {active_animals.items()}")
            if not active_animals:
                self.progress.emit("No active animals in current time window")
                self.check_window_completion()
                return
            
            success = self.schedule_deliveries(active_animals)
            if not success:
                self.progress.emit("Failed to schedule deliveries")
                return
                
            next_cycle = int(cycle_interval * 1000)
            next_cycle_time = datetime.now() + timedelta(milliseconds=next_cycle)
            self.progress.emit(f"Next staggered cycle scheduled at {next_cycle_time.strftime('%H:%M:%S')}")
            self.main_timer.singleShot(next_cycle, self.run_staggered_cycle)
            
            # Log summary of this cycle
            self.progress.emit(f"Cycle complete. Scheduled {len(active_animals)} animals for water delivery")
            
        except Exception as e:
            self.progress.emit(f"Error in staggered cycle: {str(e)}")
            self.check_window_completion()

    async def execute_delivery(self, delivery_data):
        """Execute delivery with volume tracking and compensation"""
        try:
            animal_id = delivery_data['animal_id']
            current_delivered = self.delivered_volumes.get(animal_id, 0)
            target_volume = self.animal_windows[animal_id]['target_volume']
            
            if current_delivered >= target_volume:
                return True

            failed_count = self.failed_deliveries.get(animal_id, 0)
            if failed_count > 0:
                volume_increase = min(failed_count * 0.05, 0.2)
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
                    actual_volume = delivery_data['water_volume']
                    self.delivered_volumes[animal_id] = current_delivered + actual_volume
                    self.failed_deliveries[animal_id] = 0
                    await self.database_handler.log_delivery({
                        'schedule_id': delivery_data['schedule_id'],
                        'animal_id': animal_id,
                        'relay_unit_id': delivery_data['relay_unit_id'],
                        'volume_delivered': actual_volume,
                        'timestamp': delivery_data['instant_time'].isoformat(),
                        'status': 'completed'
                    })

                self.volume_updated.emit(str(animal_id), self.delivered_volumes[animal_id])
                self.progress.emit(
                    f"Delivered {actual_volume:.3f}mL to animal {animal_id} "
                    f"(Total: {self.delivered_volumes[animal_id]:.3f}mL)"
                )
            else:
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
        animal_id = delivery_data['animal_id']
        
        # Use the animal's specific window end time
        animal_window_end = self.animal_windows.get(animal_id, {}).get('end')
        if not animal_window_end:
            self.progress.emit(f"Cannot retry delivery - no valid window for animal {animal_id}")
            return
            
        retry_delay = 30  # seconds
        retry_time = datetime.now() + timedelta(seconds=retry_delay)
        
        # Check against animal's window end, not global window
        if retry_time >= animal_window_end:
            self.progress.emit(f"Cannot retry delivery for animal {animal_id} - outside its window")
            return
            
        delivery_data['instant_time'] = retry_time
        timer = QTimer(self)
        timer.setSingleShot(True)
        timer.timeout.connect(lambda d=delivery_data: self._handle_delivery(d))
        timer.start(retry_delay * 1000)
        self.timers.append(timer)
        self.progress.emit(f"Scheduled retry for animal {delivery_data['animal_id']} in {retry_delay} seconds")

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
            if self.settings['mode'].lower() == 'instant':
                total_deliveries = len(self.delivery_instants)
                completed_deliveries = sum(
                    1 for d in self.delivery_instants 
                    if datetime.fromisoformat(d['delivery_time'].replace('Z', '+00:00')) <= current_time
                )
                progress_info = {
                    'window_progress': (completed_deliveries / total_deliveries * 100) if total_deliveries > 0 else 100,
                    'time_remaining': 0,
                    'volume_progress': {},
                    'failed_deliveries': self.failed_deliveries.copy()
                }
            else:
                window_duration = (self.window_end - self.window_start).total_seconds()
                elapsed_time = (current_time - self.window_start).total_seconds()
                progress_percent = min(100, (elapsed_time / window_duration) * 100)
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
            print(f"Progress update error details: {e}")

    def check_window_completion(self):
        """Check if window is complete or needs to continue"""
        try:
            current_time = datetime.now()
            if self.settings['mode'].lower() == 'instant':
                all_deliveries_complete = all(
                    datetime.fromisoformat(d['delivery_time'].replace('Z', '+00:00')) <= current_time
                    for d in self.delivery_instants
                )
                if all_deliveries_complete:
                    self.progress.emit("All instant deliveries completed")
                    self.stop()
                else:
                    self.main_timer.singleShot(10000, self.check_window_completion)
            else:
                target_volumes = self.settings.get('target_volumes', {})
                if not target_volumes:
                    if current_time >= self.window_end:
                        self.progress.emit("Window time completed")
                        self.stop()
                    else:
                        self.main_timer.singleShot(10000, self.check_window_completion)
                    return
                all_volumes_delivered = all(
                    self.delivered_volumes.get(aid, 0) >= target
                    for aid, target in target_volumes.items()
                )
                if all_volumes_delivered or current_time >= self.window_end:
                    for animal_id, target in target_volumes.items():
                        delivered = self.delivered_volumes.get(animal_id, 0)
                        self.progress.emit(
                            f"Final delivery for animal {animal_id}: {delivered:.3f}mL of {target:.3f}mL ({(delivered/target)*100:.1f}%)"
                        )
                    self.stop()
                else:
                    self.main_timer.singleShot(10000, self.check_window_completion)
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

    def setup_schedule(self, schedule):
        """Setup delivery windows for each animal"""
        try:
            self.animal_windows = {}
            self.delivered_volumes = {}
            window_start = datetime.fromisoformat(schedule['start_time']).timestamp()
            window_end = datetime.fromisoformat(schedule['end_time']).timestamp()
            prinat(f"Setting up schedule with {len(schedule.get('animal_ids', []))} animals")
            print(f"Window period: {datetime.fromtimestamp(window_start)} to {datetime.fromtimestamp(window_end)}")
            animal_ids = schedule.get('animal_ids', [])
            relay_assignments = schedule.get('relay_unit_assignments', {})
            desired_outputs = schedule.get('desired_water_outputs', {})
            base_volume = schedule.get('water_volume', 0.0)
            for animal_id in animal_ids:
                str_animal_id = str(animal_id)
                target_volume = desired_outputs.get(str_animal_id, base_volume)
                relay_unit = relay_assignments.get(str_animal_id)
                if relay_unit is None:
                    logging.warning(f"No relay unit assigned for animal {animal_id}")
                    continue
                self.animal_windows[animal_id] = {
                    'start': window_start,
                    'end': window_end,
                    'relay_unit': relay_unit,
                    'target_volume': target_volume,
                    'last_delivery': 0
                }
                self.delivered_volumes[animal_id] = 0
                print(f"Added window for animal {animal_id}: target={target_volume}mL, relay={relay_unit}")
            if not self.animal_windows:
                logging.warning("No valid animal windows were created")
            else:
                print(f"Successfully setup {len(self.animal_windows)} animal windows")
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
            time_per_trigger = 0.5
            setup_time = 0.1
            for animal_id, window in self.animal_windows.items():
                volume = window['target_volume']
                triggers = self.volume_calculator.calculate_triggers(volume)
                total_triggers += triggers
            total_time_needed = (total_triggers * time_per_trigger) + (len(self.animal_windows) * setup_time)
            window_durations = [ (window['end'] - window['start']) for window in self.animal_windows.values() ]
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
            sorted_animals = sorted(
                active_animals.items(),
                key=lambda x: x[1]['remaining'],
                reverse=True
            )
            base_time = datetime.now()
            cumulative_delay = 0
            scheduled_count = 0
            
            # Only schedule animals that are currently within their time window
            for animal_id, data in sorted_animals:
                # Double-check that the animal is within its time window
                window = self.animal_windows[animal_id]
                if not (window['start'] <= base_time <= window['end']):
                    print(f"Animal {animal_id} is not within its time window, skipping")
                    continue
                    
                volume_per_cycle = window['volume_per_cycle']
                cycle_volume = min(data['remaining'], volume_per_cycle)
                if cycle_volume <= 0:
                    continue
                    
                triggers = self.volume_calculator.calculate_triggers(cycle_volume)
                trigger_time = triggers * 0.5
                delivery_data = {
                    'schedule_id': self.schedule_id,
                    'animal_id': animal_id,
                    'relay_unit_id': data['relay_unit'],
                    'water_volume': cycle_volume,
                    'instant_time': base_time + timedelta(seconds=cumulative_delay),
                    'triggers': triggers
                }
                timer = QTimer()
                timer.setSingleShot(True)
                timer.timeout.connect(lambda d=delivery_data: self._handle_delivery(d))
                timer.start(int(cumulative_delay * 1000))
                self.timers.append(timer)
                print(f"Scheduled delivery for animal {animal_id}: {cycle_volume}mL in {cumulative_delay}s")
                cumulative_delay += trigger_time + 0.1
                scheduled_count += 1
                
            if scheduled_count == 0:
                self.progress.emit("No deliveries scheduled in this cycle")
                
            return True
        except Exception as e:
            logging.error(f"Error scheduling deliveries: {str(e)}")
            return False

    def _handle_delivery(self, delivery_data):
        """Synchronously handle a delivery"""
        try:
            if 'schedule_id' not in delivery_data:
                delivery_data['schedule_id'] = self.schedule_id
            
            animal_id = delivery_data['animal_id']
            
            # Check if animal is still within its time window
            current_time = datetime.now()
            animal_window = self.animal_windows.get(animal_id, {})
            if not (animal_window.get('start') <= current_time <= animal_window.get('end')):
                self.progress.emit(f"Animal {animal_id} is now outside its time window, skipping delivery")
                return True
            
            current_delivered = self.delivered_volumes.get(animal_id, 0)
            target_volume = self.animal_windows[animal_id]['target_volume']
            if current_delivered >= target_volume:
                return True
                
            failed_count = self.failed_deliveries.get(animal_id, 0)
            if failed_count > 0:
                volume_increase = min(failed_count * 0.05, 0.2)
                adjusted_volume = delivery_data['water_volume'] * (1 + volume_increase)
                delivery_data['water_volume'] = min(
                    adjusted_volume,
                    target_volume - current_delivered
                )
                
            success = self.trigger_relay(
                delivery_data['relay_unit_id'],
                delivery_data['water_volume']
            )
            
            if success:
                with QMutexLocker(self.mutex):
                    actual_volume = delivery_data['water_volume']
                    self.delivered_volumes[animal_id] = current_delivered + actual_volume
                    self.failed_deliveries[animal_id] = 0
                    delivery_log = {
                        'schedule_id': self.schedule_id,
                        'animal_id': animal_id,
                        'relay_unit_id': delivery_data['relay_unit_id'],
                        'volume_delivered': actual_volume,
                        'timestamp': delivery_data['instant_time'].isoformat(),
                        'status': 'completed'
                    }
                    if self.database_handler:
                        self.database_handler.log_delivery(delivery_log)
                self.volume_updated.emit(str(animal_id), self.delivered_volumes[animal_id])
                self.progress.emit(
                    f"Delivered {actual_volume:.3f}mL to animal {animal_id} (Total: {self.delivered_volumes[animal_id]:.3f}mL)"
                )
            else:
                with QMutexLocker(self.mutex):
                    self.failed_deliveries[animal_id] = failed_count + 1
                    if self.database_handler:
                        delivery_log = {
                            'schedule_id': self.schedule_id,
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

    def update_system_settings(self, settings):
        """Update worker settings when system settings change"""
        self.min_trigger_interval = settings.get('min_trigger_interval_ms', self.min_trigger_interval)
        self.cycle_interval = settings.get('cycle_interval', self.cycle_interval)
        self.stagger_interval = settings.get('stagger_interval', self.stagger_interval)