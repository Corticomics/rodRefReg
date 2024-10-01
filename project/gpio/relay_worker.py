from PyQt5.QtCore import QObject, pyqtSignal, pyqtSlot, QMutex, QMutexLocker, QTimer
import time

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
            max_trigger_time = 0  # To track the maximum time a trigger will take
            for relay_pair_str, triggers in self.settings['num_triggers'].items():
                relay_pair = eval(relay_pair_str)
                for i in range(triggers):
                    delay = i * self.settings['stagger']  # delay in seconds
                    total_delay = delay + self.estimate_trigger_duration()
                    max_trigger_time = max(max_trigger_time, total_delay)

                    timer = QTimer(self)
                    timer.setSingleShot(True)
                    timer.timeout.connect(lambda rp=relay_pair: self.trigger_relay(rp))
                    timer.start(delay * 1000)
                    self.timers.append(timer)

            # Calculate total cycle duration
            cycle_duration = max_trigger_time

            # Schedule the next run after cycle_duration + interval
            total_wait_time = cycle_duration + self.settings['interval']
            self.progress.emit(f"Cycle completed, waiting for {total_wait_time} seconds for next cycle.")
            self.main_timer.singleShot(total_wait_time * 1000, self.run_cycle)
        else:
            self._is_running = False  # Stop if the time window is over
            self.finished.emit()

def estimate_trigger_duration(self):
    # Approximate time it takes to execute a trigger
    # Adjust this value based on actual execution time
    return self.settings['stagger']  # Assuming stagger time represents trigger execution time


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
