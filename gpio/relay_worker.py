# relay_worker.py
from PyQt5.QtCore import QObject, pyqtSignal, pyqtSlot
import time

class RelayWorker(QObject):
    finished = pyqtSignal()
    progress = pyqtSignal(str)

    def __init__(self, settings, relay_handler):
        super().__init__()
        self.settings = settings
        self.relay_handler = relay_handler

        # Debugging output to ensure initialization
        print(f"RelayWorker initialized with settings: {settings}")
        print(f"RelayWorker initialized with relay_handler: {relay_handler}")

    @pyqtSlot()
    def run(self):
        try:
            current_time = int(time.time())
            print("Worker started")
            if self.settings['window_start'] <= current_time <= self.settings['window_end']:
                for relay_pair_str, triggers in self.settings['num_triggers'].items():
                    relay_pair = eval(relay_pair_str)
                    relay_info = self.relay_handler.trigger_relays([relay_pair], {relay_pair_str: triggers}, self.settings['stagger'])
                    self.progress.emit(f"Triggered {relay_pair} {triggers} times. Relay info: {relay_info}")
            else:
                print("Worker not in time window")
        except Exception as e:
            self.progress.emit(f"An error occurred: {e}")
        finally:
            self.finished.emit()

