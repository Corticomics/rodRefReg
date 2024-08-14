# In relay_worker.py

from PyQt5.QtCore import QObject, pyqtSignal, pyqtSlot, QMutex, QMutexLocker
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

    @pyqtSlot()
    def run_cycle(self):
        with QMutexLocker(self.mutex):
            if not self._is_running:
                return
            
            try:
                current_time = int(time.time())
                if self.settings['window_start'] <= current_time <= self.settings['window_end']:
                    for relay_pair_str, triggers in self.settings['num_triggers'].items():
                        relay_pair = eval(relay_pair_str)
                        for _ in range(triggers):
                            relay_info = self.relay_handler.trigger_relays([relay_pair], {relay_pair_str: triggers}, self.settings['stagger'])
                            self.progress.emit(f"Triggered {relay_pair} {triggers} times. Relay info: {relay_info}")
                            # Send a notification after each relay trigger
                            self.notification_handler.send_notification(f"Triggered {relay_pair} {triggers} times.")
                            time.sleep(self.settings['stagger'])  # Stagger between individual relay activations within a cycle
                else:
                    self._is_running = False  # Stop if the time window is over
                    self.finished.emit()
            except Exception as e:
                self.progress.emit(f"An error occurred: {e}")

    def stop(self):
        with QMutexLocker(self.mutex):
            self._is_running = False
