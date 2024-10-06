from PyQt5.QtCore import QObject, pyqtSignal, pyqtSlot, QMutex, QMutexLocker, QTimer
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

    @pyqtSlot()
    def run_cycle(self):
        with QMutexLocker(self.mutex):
            if not self._is_running:
                return

        current_time = int(time.time())
        if current_time < self.settings['window_start']:
            delay = self.settings['window_start'] - current_time
            self.progress.emit(f"Waiting {delay} seconds until the start of the window.")
            self.main_timer.singleShot(delay * 1000, self.run_cycle)
            return

        if self.settings['window_start'] <= current_time <= self.settings['window_end']:
            for relay_pair_str, triggers in self.settings['num_triggers'].items():
                relay_pair = eval(relay_pair_str)
                for i in range(triggers):
                    delay = i * self.settings['stagger'] * 1000  # delay in milliseconds
                    timer = QTimer(self)
                    timer.setSingleShot(True)
                    timer.timeout.connect(lambda rp=relay_pair: self.trigger_relay(rp))
                    timer.start(delay)
                    self.timers.append(timer)

            # Schedule the next run
            self.progress.emit(f"Cycle completed, waiting for {self.settings['interval']} seconds for next cycle.")
            self.main_timer.singleShot(self.settings['interval'] * 1000, self.run_cycle)
        else:
            self._is_running = False  # Stop if the time window is over
            self.finished.emit()

    def trigger_relay(self, relay_pair):
        with QMutexLocker(self.mutex):
            if not self._is_running:
                return
        relay_info = self.relay_handler.trigger_relays(
            [relay_pair],
            {str(relay_pair): 1},
            self.settings['stagger']
        )
        self.progress.emit(f"Triggered {relay_pair}. Relay info: {relay_info}")
        self.notification_handler.send_slack_notification(f"Triggered {relay_pair}.")

    def stop(self):
        with QMutexLocker(self.mutex):
            self._is_running = False
        self.main_timer.stop()  # Stop the main timer
        # Stop and delete all scheduled timers
        for timer in self.timers:
            timer.stop()
            timer.deleteLater()
        self.timers.clear()
        self.finished.emit()  # Ensure that any waiting threads know we're done
