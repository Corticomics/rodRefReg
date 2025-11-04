from PyQt5.QtCore import QObject, pyqtSignal, pyqtSlot, QMutex, QMutexLocker, QTimer
from datetime import datetime, timedelta
import time
from utils.volume_calculator import VolumeCalculator
import asyncio
import logging
from functools import partial
from strategies.factory import StrategyFactory
from drivers.flow_sensor import SLF3S0600FDriver
from drivers.solenoid_controller import SolenoidController
from utils.calibration import CalibrationStore

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
        # Track per-animal retry timers to avoid duplicate scheduling
        self.retry_timers = {}
        
        # Initialize main_timer
        self.main_timer = QTimer(self)
        
        # Retrieve mode and delivery instants from worker settings
        self.mode = settings.get('mode', 'instant').lower()
        self.delivery_instants = settings.get('delivery_instants', [])

        # Window end behavior: allow continuing after window end until targets are met (best-practice for robustness)
        self.enforce_window_end = settings.get('enforce_window_end', False)
        # Effective target volumes for staggered mode
        self.target_volumes = settings.get('target_volumes', settings.get('desired_water_outputs', {}))
        
        # Initialize tracking variables
        self.delivered_volumes = {}
        self.failed_deliveries = {}
        self.window_start = datetime.fromtimestamp(settings['window_start'])
        self.window_end = datetime.fromtimestamp(settings['window_end'])
        
        # --- FIX: Pass the SystemController instance to VolumeCalculator ---
        self.volume_calculator = VolumeCalculator(self.system_controller)
        # --------------------------------------------------------------------
        
        # Resolve hardware mode and strategy
        system_settings = self.system_controller.settings
        
        # DEBUG: Print actual settings to diagnose hardware_mode issue (use print for immediate output)
        print(f"\n[DEBUG] ========== HARDWARE MODE DETECTION ==========")
        print(f"[DEBUG] system_settings type: {type(system_settings)}")
        print(f"[DEBUG] system_settings.get('hardware_mode'): {system_settings.get('hardware_mode') if isinstance(system_settings, dict) else 'NOT A DICT'}")
        print(f"[DEBUG] system_settings.get('flow_sensor_type'): {system_settings.get('flow_sensor_type') if isinstance(system_settings, dict) else 'NOT A DICT'}")
        print(f"[DEBUG] system_settings.get('uart_port'): {system_settings.get('uart_port') if isinstance(system_settings, dict) else 'NOT A DICT'}")
        
        self.hardware_mode = (system_settings.get('hardware_mode') or 'pump') if isinstance(system_settings, dict) else 'pump'
        print(f"[DEBUG] Resolved hardware_mode: '{self.hardware_mode}'")
        print(f"[DEBUG] Type of hardware_mode: {type(self.hardware_mode)}")
        print(f"[DEBUG] hardware_mode == 'solenoid': {self.hardware_mode == 'solenoid'}")
        print(f"[DEBUG] hardware_mode.strip() == 'solenoid': {self.hardware_mode.strip() == 'solenoid' if isinstance(self.hardware_mode, str) else 'NOT STRING'}")
        print(f"[DEBUG] ===============================================\n")
        
        # Here we added a check for the hardware mode to be solenoid
        print(f"[DEBUG] About to check: if self.hardware_mode == 'solenoid':")
        if self.hardware_mode == 'solenoid':
            print(f"[DEBUG] ✅ ENTERED solenoid mode block!")
            print(f"[DEBUG] Entering solenoid mode initialization...")
            
            # Build solenoid components using factory pattern
            print(f"[DEBUG] Step 1: Importing flow sensor factory...")
            from drivers.flow_sensor_factory import create_flow_sensor
            from drivers.uart_flow_sensor import TeensyUnavailableError
            print(f"[DEBUG] Step 1:  Imports successful")
            
            print(f"[DEBUG] Step 2: Creating flow sensor...")
            try:
                flow_sensor = create_flow_sensor(system_settings)
                print(f"[DEBUG] Step 2:  Flow sensor created: {type(flow_sensor)}")
            except TeensyUnavailableError as e:
                print(f"[DEBUG] Step 2:  TeensyUnavailableError: {e}")
                self.progress.emit(f"Flow sensor unavailable: {e}")
                self.progress.emit("Cannot run solenoid schedule without flow sensor. Please check Teensy connection.")
                raise RuntimeError("Flow sensor required for solenoid mode")
            except Exception as e:
                print(f"[DEBUG] Step 2:  Exception: {type(e).__name__}: {e}")
                import traceback
                print(f"[DEBUG] Stack trace:\n{traceback.format_exc()}")
                raise

            # Build cage map and solenoid controller
            print(f"[DEBUG] Step 3: Building cage map and solenoid controller...")
            cage_map = system_settings.get('cage_relays', {})
            print(f"[DEBUG] Step 3a: cage_map from settings: {cage_map}")
            if not cage_map:
                # Fallback: build sequential single-relay map across all relays, excluding master (16)
                # NOTE: We do NOT save here - ensure_solenoid_defaults() handles persistence
                # Saving here was causing pulse mode keys to be deleted during schedule execution
                try:
                    num_hats = int(system_settings.get('num_hats', 1))
                    total_relays = 16 * num_hats
                    master_id = int(system_settings.get('global_master_relay_id', 16))
                    seq_map = {}
                    cage_id = 1
                    for relay_id in range(1, total_relays + 1):
                        if relay_id == master_id:
                            continue
                        seq_map[str(cage_id)] = relay_id
                        cage_id += 1
                    cage_map = seq_map
                    print(f"[DEBUG] Built fallback cage_map with {len(cage_map)} cages (not persisting - ensure_solenoid_defaults handles that)")
                except Exception as e:
                    print(f"Failed to build sequential cage_relays: {e}")
            print(f"[DEBUG] Step 3b: Building SolenoidController...")
            master_id = int(system_settings.get('global_master_relay_id', 16))
            print(f"[DEBUG] Step 3b: master_id={master_id}, cage_map={cage_map}")
            solenoid = SolenoidController(self.relay_handler, master_id, cage_map)
            print(f"[DEBUG] Step 3b:  SolenoidController created")
            
            print(f"[DEBUG] Step 4: Creating strategy...")
            cal_store = CalibrationStore()
            self.strategy = StrategyFactory.create(
                self.hardware_mode,
                solenoid_controller=solenoid,
                flow_sensor=flow_sensor,
                calibration_store=cal_store,
                settings=system_settings,
                pump_controller=self.pump_controller,
                volume_calculator=self.volume_calculator,
            )
            print(f"[DEBUG] Step 4:  Strategy created: {type(self.strategy)}")
            
            # Start flow sensor in continuous mode
            print(f"[DEBUG] Step 5: Starting flow sensor...")
            try:
                print(f"[DEBUG] Step 5a: Checking if flow_sensor has start() method...")
                if hasattr(flow_sensor, 'start'):
                    print(f"[DEBUG] Step 5a:  Has start() method, calling it...")
                    flow_sensor.start()
                    print(f"[DEBUG] Step 5a:  start() completed successfully!")
                    
                    # CRITICAL: Verify stream health immediately after start (fail-fast principle)
                    # Best Practices:
                    # - Contract programming: Establish preconditions before execution
                    # - Fail-fast: Report sensor issues during initialization, not mid-delivery
                    print(f"[DEBUG] Step 5b: Verifying stream health...")
                    if hasattr(flow_sensor, 'wait_for_frames'):
                        if not flow_sensor.wait_for_frames(min_frames=5, timeout_s=5.0):
                            error_msg = (
                                "Flow sensor started but not streaming measurements. "
                                "Cannot proceed with solenoid schedule. "
                                "Check: 1) Teensy USB connection, 2) I²C wiring (SDA/SCL/GND), "
                                "3) Pullup resistors (2kΩ), 4) Teensy firmware loaded"
                            )
                            print(f"[DEBUG] Step 5b:  {error_msg}")
                            self.progress.emit(f"ERROR: {error_msg}")
                            raise RuntimeError(error_msg)
                        print(f"[DEBUG] Step 5b:  Stream health verified")
                    
                    # Get sensor info for logging
                    if hasattr(flow_sensor, 'port'):
                        sensor_info = f"uart on {flow_sensor.port}"
                    elif hasattr(flow_sensor, 'bus_id'):
                        sensor_info = f"i2c on bus {flow_sensor.bus_id()}"
                    else:
                        sensor_info = f"unknown interface"
                    print(f"[DEBUG] Step 5c:  Flow sensor fully operational ({sensor_info})")
                    self.progress.emit(f"Flow sensor operational: {sensor_info}")
                else:
                    print(f"[DEBUG] Step 5a:  Flow sensor has no start() method!")
                    raise RuntimeError("Flow sensor missing start() method")
            except TeensyUnavailableError as e:
                print(f"[DEBUG] Step 5:  TeensyUnavailableError: {e}")
                self.progress.emit(f"Flow sensor unavailable: {e}")
                raise RuntimeError("Flow sensor required for solenoid mode")
            except Exception as e:
                # CRITICAL: Don't silently ignore startup failures in production!
                print(f"[DEBUG] Step 5a:  CRITICAL: Flow sensor start failed: {type(e).__name__}: {e}")
                import traceback
                print(f"[DEBUG] Stack trace:\n{traceback.format_exc()}")
                raise RuntimeError(f"Flow sensor startup failed: {e}")
            
            print(f"[DEBUG] ========== SOLENOID INITIALIZATION COMPLETE ==========\n")
        else:
            # NOT solenoid mode - using pump or other strategy
            print(f"[DEBUG] ❌ ENTERED else block (NOT solenoid mode)!")
            print(f"[DEBUG] hardware_mode value: '{self.hardware_mode}'")
            self.progress.emit(f"[DEBUG] NOT in solenoid mode (hardware_mode={self.hardware_mode}), using generic strategy")
            self.strategy = StrategyFactory.create(
                self.hardware_mode,
                pump_controller=self.pump_controller,
                volume_calculator=self.volume_calculator,
            )

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
            outputs = [float(vol) for vol in self.settings.get('desired_water_outputs', {}).values()]
            max_volume = max(outputs) if outputs else 0.0
            max_volume_per_cycle = self.settings.get('max_cycle_volume', 0.2)
            min_cycles_needed = (max_volume / max_volume_per_cycle) if max_volume_per_cycle > 0 else 0
            
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
                    cycles_in_window = (window_duration / cycle_interval) if cycle_interval > 0 else 0
                    if target_volume <= 0 or cycles_in_window <= 0:
                        volume_per_cycle = 0.0
                    else:
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
            print(f"Window start: {self.window_start}, Window end: {self.window_end}")
            print(f"Animal windows: {self.animal_windows.items()}")
            
            if current_time < self.window_start:
                print(f"Current time ({current_time}) is before window start ({self.window_start})")
                delay_ms = int((self.window_start - current_time).total_seconds() * 1000)
                self.main_timer.singleShot(delay_ms, self.run_staggered_cycle)
                return
            
            if current_time > self.window_end and self.enforce_window_end:
                print(f"Current time ({current_time}) is after window end ({self.window_end}) and enforce_window_end=True")
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
                # Check if we need to continue beyond window end to complete deliveries
                self.check_final_completion()
                return
            
            success = self.schedule_deliveries(active_animals)
            if not success:
                self.progress.emit("Failed to schedule deliveries")
                return
                
            next_cycle = int(cycle_interval * 1000)
            self.main_timer.singleShot(next_cycle, self.run_staggered_cycle)
            
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

            success = await self.strategy.deliver(
                relay_unit_id=delivery_data['relay_unit_id'],
                target_volume_ml=delivery_data['water_volume'],
                triggers_hint=delivery_data.get('triggers'),
            )

            if success:
                with QMutexLocker(self.mutex):
                    actual_volume = delivery_data['water_volume']
                    self.delivered_volumes[animal_id] = current_delivered + actual_volume
                    self.failed_deliveries[animal_id] = 0
                    self.database_handler.log_delivery({
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
                    self.database_handler.log_delivery({
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
        window_end = datetime.fromtimestamp(self.settings['window_end'])
        if retry_time >= window_end:
            self.progress.emit("Cannot retry delivery - outside window")
            return
        # Prevent duplicate retries per animal
        animal_id = delivery_data.get('animal_id')
        if animal_id in self.retry_timers:
            existing_timer = self.retry_timers.get(animal_id)
            if existing_timer and existing_timer.isActive():
                self.progress.emit(f"Retry already scheduled for animal {animal_id}; skipping duplicate")
                return
            # Clean up stale mapping
            self.retry_timers.pop(animal_id, None)
        delivery_data['instant_time'] = retry_time
        timer = QTimer(self)
        timer.setSingleShot(True)
        # Wrap coroutine execution in a thread-local event loop
        def _run_retry(d=delivery_data):
            try:
                loop = asyncio.new_event_loop()
                try:
                    asyncio.set_event_loop(loop)
                    loop.run_until_complete(self.execute_delivery(d))
                finally:
                    loop.close()
                    asyncio.set_event_loop(None)
            except Exception as e:
                self.progress.emit(f"Retry error: {str(e)}")
            finally:
                # Remove timer mapping once it fires
                try:
                    self.retry_timers.pop(animal_id, None)
                except Exception:
                    pass
        timer.timeout.connect(_run_retry)
        timer.start(retry_delay * 1000)
        self.timers.append(timer)
        # Track this retry timer
        self.retry_timers[animal_id] = timer
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
                effective_targets = self.settings.get('target_volumes', self.settings.get('desired_water_outputs', {}))
                for animal_id, target in effective_targets.items():
                    delivered = self.delivered_volumes.get(animal_id, 0)
                    volume_progress[animal_id] = {
                        'delivered': delivered,
                        'target': target,
                        'percent': (delivered / target) * 100 if (target is not None and target > 0) else 100
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

    def check_final_completion(self):
        """
        Check if schedule should complete, prioritizing volume delivery over time windows.
        
        Best Practices:
        - User requirement: "MUST have delivered the user.desired volume even if that means going over the time window a bit"
        - Fail-safe: Always complete deliveries before stopping
        - Observable: Log final delivery status for each animal
        - Graceful: Clean up all resources (timers, sensors, valves)
        """
        try:
            current_time = datetime.now()
            target_volumes = self.settings.get('target_volumes', self.settings.get('desired_water_outputs', {}))
            
            if not target_volumes:
                self.progress.emit("No target volumes configured, stopping schedule")
                self.stop()
                return
            
            # Check which animals still need deliveries
            incomplete_animals = {}
            for animal_id, target in target_volumes.items():
                delivered = self.delivered_volumes.get(animal_id, 0)
                remaining = target - delivered
                
                if remaining > 0.01:  # Allow 0.01 mL tolerance for floating point precision
                    incomplete_animals[animal_id] = {
                        'delivered': delivered,
                        'target': target,
                        'remaining': remaining
                    }
            
            if incomplete_animals:
                # We need to continue delivering even though time window ended
                self.progress.emit(
                    f"⚠️ Time window ended but {len(incomplete_animals)} animal(s) incomplete. "
                    f"Continuing deliveries to meet target volumes..."
                )
                
                for animal_id, info in incomplete_animals.items():
                    self.progress.emit(
                        f"  Animal {animal_id}: {info['delivered']:.3f}/{info['target']:.3f}mL "
                        f"({info['remaining']:.3f}mL remaining)"
                    )
                
                # Schedule final deliveries for incomplete animals
                active_animals = {}
                for animal_id, info in incomplete_animals.items():
                    relay_unit = self.animal_windows[animal_id]['relay_unit']
                    active_animals[animal_id] = {
                        'remaining': info['remaining'],
                        'last_delivery': self.animal_windows[animal_id]['last_delivery'],
                        'relay_unit': relay_unit
                    }
                
                # Schedule the final deliveries
                success = self.schedule_deliveries(active_animals)
                if success:
                    # Check again after deliveries complete (give time for execution)
                    self.main_timer.singleShot(5000, self.check_final_completion)
                else:
                    self.progress.emit("Failed to schedule final deliveries, stopping")
                    self.stop()
            else:
                # All animals have received their target volumes
                self.progress.emit("✅ All target volumes delivered successfully!")
                for animal_id, target in target_volumes.items():
                    delivered = self.delivered_volumes.get(animal_id, 0)
                    precision = abs(delivered - target) / target * 100.0 if target > 0 else 0.0
                    self.progress.emit(
                        f"  Animal {animal_id}: {delivered:.3f}mL delivered "
                        f"(target: {target:.3f}mL, precision: {precision:.1f}%)"
                    )
                self.stop()
                
        except Exception as e:
            self.progress.emit(f"Error in final completion check: {str(e)}")
            print(f"Final completion check error details: {e}")
            import traceback
            print(traceback.format_exc())
            self.stop()
    
    def check_window_completion(self):
        """
        Legacy completion check - now redirects to check_final_completion.
        Kept for backward compatibility.
        """
        self.check_final_completion()

    def stop(self):
        """
        Gracefully stop the schedule and clean up all resources.
        
        Best Practices:
        - Idempotent: Safe to call multiple times
        - Comprehensive: Stop all timers, sensors, and valdves
        - Observable: Log each cleanup step
        - Fail-safe: Continue cleanup even if individual steps fail
        """
        print("\n[STOP] ========== SCHEDULE STOP SEQUENCE INITIATED ==========")
        
        with QMutexLocker(self.mutex):
            if not self._is_running:
                print("[STOP] Already stopped, skipping")
                return
            self._is_running = False
            print("[STOP]  Set _is_running = False")
        
        # Stop all timers
        try:
            self.monitor_timer.stop()
            print("[STOP]  Monitor timer stopped")
        except Exception as e:
            print(f"[STOP]  Monitor timer stop failed: {e}")
        
        try:
            self.main_timer.stop()
            print("[STOP]  Main timer stopped")
        except Exception as e:
            print(f"[STOP]  Main timer stop failed: {e}")
        
        # Stop and clear all delivery timers
        timer_count = len(self.timers)
        if timer_count > 0:
            print(f"[STOP] Stopping {timer_count} delivery timer(s)...")
            for i, timer in enumerate(self.timers):
                try:
                    if timer.isActive():
                        timer.stop()
                        print(f"[STOP]    Timer {i+1}/{timer_count} stopped")
                except RuntimeError as ex:
                    print(f"[STOP]    Timer {i+1}/{timer_count} already deleted: {ex}")
                except Exception as e:
                    print(f"[STOP]    Timer {i+1}/{timer_count} error: {e}")
            self.timers.clear()
            print(f"[STOP]  All {timer_count} timer(s) cleared")
        else:
            print("[STOP] No active delivery timers to stop")
        
        # Clear retry timers
        if hasattr(self, 'retry_timers') and self.retry_timers:
            retry_count = len(self.retry_timers)
            print(f"[STOP] Clearing {retry_count} retry timer(s)...")
            for animal_id, timer in self.retry_timers.items():
                try:
                    if timer and timer.isActive():
                        timer.stop()
                        print(f"[STOP]    Retry timer for animal {animal_id} stopped")
                except Exception as e:
                    print(f"[STOP]    Retry timer for animal {animal_id} error: {e}")
            self.retry_timers.clear()
            print(f"[STOP]  All {retry_count} retry timer(s) cleared")
        
        # Stop flow sensor if running in solenoid mode
        if self.hardware_mode == 'solenoid' and hasattr(self, 'strategy'):
            print("[STOP] Attempting to stop flow sensor...")
            try:
                # Access flow sensor through strategy if available
                if hasattr(self.strategy, '_sensor') and hasattr(self.strategy._sensor, 'stop'):
                    print("[STOP]   Calling sensor.stop()...")
                    self.strategy._sensor.stop()
                    print("[STOP]    Flow sensor stop() completed")
                    
                    # Wait briefly to ensure sensor stops cleanly
                    import time
                    time.sleep(0.5)
                    
                    # Verify sensor stopped
                    if hasattr(self.strategy._sensor, '_running'):
                        if not self.strategy._sensor._running:
                            print("[STOP]    Flow sensor confirmed stopped (_running=False)")
                        else:
                            print("[STOP]   ⚠️ Warning: sensor._running still True after stop()")
                    
                    print("[STOP]  Flow sensor stopped successfully")
                else:
                    print("[STOP]   ⚠️ Flow sensor not accessible or no stop() method")
            except Exception as e:
                print(f"[STOP]    Flow sensor stop failed: {e}")
                import traceback
                print(f"[STOP]   Stack trace:\n{traceback.format_exc()}")
        else:
            print(f"[STOP] Flow sensor stop not needed (hardware_mode={self.hardware_mode})")
        
        # Final status report
        print("[STOP] ========== CLEANUP COMPLETE ==========")
        self.progress.emit("✅ Schedule stopped - All resources cleaned up")
        print("[STOP] Emitting finished signal...")
        self.finished.emit()
        print("[STOP] ========== STOP SEQUENCE COMPLETE ==========\n")
    def setup_schedule(self, schedule):
        """Setup delivery windows for each animal"""
        try:
            self.animal_windows = {}
            self.delivered_volumes = {}
            window_start = datetime.fromisoformat(schedule['start_time']).timestamp()
            window_end = datetime.fromisoformat(schedule['end_time']).timestamp()
            print(f"Setting up schedule with {len(schedule.get('animal_ids', []))} animals")
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
            for animal_id, data in sorted_animals:
                volume_per_cycle = self.animal_windows[animal_id]['volume_per_cycle']
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
                # Use partial with a copy to avoid closure over loop variable and later mutation
                timer.timeout.connect(partial(self._handle_delivery, delivery_data.copy()))
                timer.start(int(cumulative_delay * 1000))
                self.timers.append(timer)
                print(f"Scheduled delivery for animal {animal_id}: {cycle_volume}mL in {cumulative_delay}s")
                cumulative_delay += trigger_time + 0.1
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
            # In pump mode, keep legacy synchronous path via trigger_relay to avoid behavior change.
            # For other modes, delivery is handled asynchronously by strategy at schedule time.
            if self.hardware_mode == 'pump':
                success = self.trigger_relay(
                    delivery_data['relay_unit_id'],
                    delivery_data['water_volume']
                )
            else:
                # Non-pump modes should not use trigger_relay; run coroutine in a private loop
                try:
                    # CRITICAL DEBUG: Log delivery attempt
                    self.progress.emit(
                        f"[DEBUG] Attempting delivery: animal={animal_id}, "
                        f"cage={delivery_data['relay_unit_id']}, "
                        f"volume={delivery_data['water_volume']:.3f}mL"
                    )
                    
                    loop = asyncio.new_event_loop()
                    try:
                        asyncio.set_event_loop(loop)
                        success = loop.run_until_complete(
                            self.strategy.deliver(
                                relay_unit_id=delivery_data['relay_unit_id'],
                                target_volume_ml=delivery_data['water_volume'],
                                triggers_hint=delivery_data.get('triggers'),
                            )
                        )
                        
                        # CRITICAL DEBUG: Log delivery result
                        self.progress.emit(
                            f"[DEBUG] Delivery completed: animal={animal_id}, success={success}"
                        )
                    finally:
                        loop.close()
                        asyncio.set_event_loop(None)
                except Exception as e:
                    # CRITICAL DEBUG: Log full exception details
                    import traceback
                    error_details = traceback.format_exc()
                    self.progress.emit(f"Delivery error for animal {animal_id}: {str(e)}")
                    self.progress.emit(f"[DEBUG] Exception traceback:\n{error_details}")
                    success = False
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