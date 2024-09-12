from PyQt5.QtCore import QObject, pyqtSignal, pyqtSlot, QMutex, QMutexLocker, QTimer
import time

class RelayWorker(QObject):
    finished = pyqtSignal()
    progress = pyqtSignal(str)

    def __init__(self, settings, relay_handler, notification_handler):
        super().__init__()
        self.settings = settings
        self.relay_handler = relay_handler
        self.notification_handler = notification_handler  # Store the notification handler
        self._is_running = True
        self.mutex = QMutex()
        self.timer = QTimer(self)

    @pyqtSlot()
    def run_cycle(self):
        with QMutexLocker(self.mutex):
            if not self._is_running:
                return

            try:
                current_time = int(time.time())
                if current_time < self.settings['window_start']:
                    delay = self.settings['window_start'] - current_time
                    self.progress.emit(f"Waiting {delay} seconds until the start of the window.")
                    QTimer.singleShot(delay * 1000, self.run_cycle)
                    return

                if self.settings['window_start'] <= current_time <= self.settings['window_end']:
                    for relay_pair_str, triggers in self.settings['num_triggers'].items():
                        relay_pair = eval(relay_pair_str)
                        for _ in range(triggers):
                            relay_info = self.relay_handler.trigger_relays([relay_pair], {relay_pair_str: triggers}, self.settings['stagger'])
                            self.progress.emit(f"Triggered {relay_pair} {triggers} times. Relay info: {relay_info}")
                            # Send a notification after each relay trigger
                            self.notification_handler.send_slack_notification(f"Triggered {relay_pair} {triggers} times.")
                            time.sleep(self.settings['stagger'])  # Stagger between individual relay activations within a cycle

                    # Schedule the next run
                    self.progress.emit(f"Cycle completed, waiting for {self.settings['interval']} seconds for next cycle.")
                    self.timer.singleShot(self.settings['interval'] * 1000, self.run_cycle)
                else:
                    self._is_running = False  # Stop if the time window is over
                    self.stop_timer()  # Ensure the timer is stopped
                    self.finished.emit()
            except Exception as e:
                self.progress.emit(f"An error occurred in run_cycle: {e}")
                self.stop_timer()  # Stop timer on exception too

    def stop_timer(self):
        if self.timer.isActive():
            self.timer.stop()

    def stop(self):
        with QMutexLocker(self.mutex):
            self._is_running = False
        self.stop_timer()  # Stop the timer when stopping the worker
