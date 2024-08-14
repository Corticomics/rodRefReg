# In relay_worker.py

from PyQt5.QtCore import QObject, pyqtSignal, pyqtSlot, QMutex, QMutexLocker

class RelayWorker(QObject):
    finished = pyqtSignal()
    progress = pyqtSignal(str)

    def __init__(self, settings, relay_handler):
        super().__init__()
        self.settings = settings
        self.relay_handler = relay_handler
        self._is_running = True
        self.mutex = QMutex()

    @pyqtSlot()
    def run(self):
        while self._is_running:
            try:
                current_time = int(time.time())
                if self.settings['window_start'] <= current_time <= self.settings['window_end']:
                    for relay_pair_str, triggers in self.settings['num_triggers'].items():
                        relay_pair = eval(relay_pair_str)
                        relay_info = self.relay_handler.trigger_relays([relay_pair], {relay_pair_str: triggers}, self.settings['stagger'])
                        self.progress.emit(f"Triggered {relay_pair} {triggers} times. Relay info: {relay_info}")
                else:
                    break
            except Exception as e:
                self.progress.emit(f"An error occurred: {e}")
                break
        self.finished.emit()

    def stop(self):
        with QMutexLocker(self.mutex):
            self._is_running = False
