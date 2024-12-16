from PyQt5.QtCore import QObject, pyqtSignal, pyqtSlot, QMutex, QMutexLocker, QTimer
from datetime import datetime
import time
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
        
        if current_time < window_start:
            delay = window_start - current_time
            self.progress.emit(f"Waiting {delay} seconds until window start")
            self.main_timer.singleShot(delay * 1000, self.run_staggered_cycle)
            return

        if window_start <= current_time <= window_end:
            cycle_interval = self.settings.get('cycle_interval')
            stagger_interval = self.settings.get('stagger_interval')
            
            water_volumes = self.settings.get('water_volumes', {})
            
            for relay_unit_id, triggers_per_cycle in self.settings['num_triggers'].items():
                water_volume = water_volumes.get(str(relay_unit_id), self.settings.get('water_volume', 0))
                volume_per_trigger = water_volume / triggers_per_cycle
                
                for i in range(triggers_per_cycle):
                    delay = i * stagger_interval * 1000  # Convert to milliseconds
                    timer = QTimer(self)
                    timer.setSingleShot(True)
                    timer.timeout.connect(
                        lambda r=relay_unit_id, v=volume_per_trigger: self.trigger_relay(r, v)
                    )
                    timer.start(int(delay))
                    self.timers.append(timer)

            # Schedule next cycle
            self.main_timer.singleShot(int(cycle_interval * 1000), self.run_staggered_cycle)
            self.progress.emit(f"Staggered cycle scheduled, next in {cycle_interval} seconds")
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
        with QMutexLocker(self.mutex):
            if not self._is_running:
                return
                
            num_triggers = self.settings.get('num_triggers', {}).get(
                str(relay_unit_id), 
                self.settings['base_triggers']
            )
            
            relay_info = self.relay_handler.trigger_relays(
                [relay_unit_id],
                {str(relay_unit_id): num_triggers},
                self.settings.get('stagger', 5)
            )
            return relay_info

    def stop(self):
        with QMutexLocker(self.mutex):
            self._is_running = False
        self.main_timer.stop()
        for timer in self.timers:
            timer.stop()
            timer.deleteLater()
        self.timers.clear()
        self.finished.emit()
