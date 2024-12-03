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
        self._is_running = True
        self.mutex = QMutex()
        self.main_timer = QTimer(self)
        self.timers = []  # Keep track of active timers
        self.delivery_instants = settings.get('delivery_instants', [])
        self.mode = settings.get('mode', 'instant')  # 'instant' or 'staggered'
        
    @pyqtSlot()
    def run_cycle(self):
        if self.mode == 'instant':
            self.run_instant_cycle()
        else:
            self.run_staggered_cycle()

    def run_instant_cycle(self):
        """Handle precise time-based deliveries"""
        with QMutexLocker(self.mutex):
            if not self._is_running or not self.delivery_instants:
                self.finished.emit()
                return

        current_time = datetime.now()
        for instant in self.delivery_instants:
            delivery_time = datetime.fromisoformat(instant['delivery_time'])
            if delivery_time > current_time:
                delay = (delivery_time - current_time).total_seconds() * 1000
                timer = QTimer(self)
                timer.setSingleShot(True)
                timer.timeout.connect(
                    lambda i=instant: self.trigger_relay(
                        i['relay_unit_id'],
                        i['water_volume']
                    )
                )
                timer.start(int(delay))
                self.timers.append(timer)
                self.progress.emit(
                    f"Scheduled instant delivery for relay unit {instant['relay_unit_id']} "
                    f"at {delivery_time.strftime('%Y-%m-%d %H:%M:%S')}"
                )
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
            stagger = self.settings.get('stagger', 5)
            water_volumes = self.settings.get('water_volumes', {})
            
            for relay_unit_id, triggers in self.settings['num_triggers'].items():
                water_volume = water_volumes.get(str(relay_unit_id), self.settings.get('water_volume', 0))
                for i in range(triggers):
                    delay = i * stagger * 1000
                    timer = QTimer(self)
                    timer.setSingleShot(True)
                    timer.timeout.connect(
                        lambda r=relay_unit_id, v=water_volume: self.trigger_relay(r, v)
                    )
                    timer.start(delay)
                    self.timers.append(timer)

            interval = self.settings.get('interval', 3600)
            self.main_timer.singleShot(interval * 1000, self.run_staggered_cycle)
            self.progress.emit(f"Staggered cycle scheduled, next in {interval} seconds")
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
                
        relay_info = self.relay_handler.trigger_relays(
            [relay_unit_id],
            {str(relay_unit_id): 1},
            self.settings.get('stagger', 5)
        )
        
        msg = f"Delivered {water_volume}mL using relay unit {relay_unit_id}"
        self.progress.emit(msg)
        self.notification_handler.send_slack_notification(msg)

    def stop(self):
        with QMutexLocker(self.mutex):
            self._is_running = False
        self.main_timer.stop()
        for timer in self.timers:
            timer.stop()
            timer.deleteLater()
        self.timers.clear()
        self.finished.emit()
