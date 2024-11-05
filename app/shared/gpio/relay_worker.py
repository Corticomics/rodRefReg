# shared/gpio/relay_worker.py

from PyQt5.QtCore import QObject, pyqtSignal, QMutex, QMutexLocker, QTimer, pyqtSlot
import time

class RelayWorker(QObject):
    finished = pyqtSignal()
    progress = pyqtSignal(str)

    def __init__(self, settings, relay_handler, notification_handler, db_manager):
        super().__init__()
        self.settings = settings
        self.relay_handler = relay_handler
        self.notification_handler = notification_handler
        self.db_manager = db_manager
        self._is_running = True
        self.mutex = QMutex()
        self.main_timer = QTimer(self)
        self.main_timer.setSingleShot(True)
        self.main_timer.timeout.connect(self.run_cycle)
        self.timers = []  # Keep track of active timers

    @pyqtSlot()
    def start(self):
        self.run_cycle()

    @pyqtSlot()
    def run_cycle(self):
        with QMutexLocker(self.mutex):
            if not self._is_running:
                return

        current_time = int(time.time())
        if current_time < self.settings['window_start']:
            delay = self.settings['window_start'] - current_time
            self.progress.emit(f"Waiting {delay} seconds until the start of the window.")
            self.main_timer.start(delay * 1000)
            return

        if self.settings['window_start'] <= current_time <= self.settings['window_end']:
            for relay_pair_str, triggers in self.settings['num_triggers'].items():
                relay_pair = eval(relay_pair_str)
                mouse = self.db_manager.get_mouse_by_relay(relay_pair)
                if not mouse:
                    self.progress.emit(f"No mouse assigned to Relay Pair {relay_pair}. Skipping.")
                    continue

                min_water = mouse.calculate_min_water()
                max_water = mouse.calculate_max_water()
                suggested_volume = self.settings['relay_volumes'].get(relay_pair, 0.0)

                # Ensure suggested_volume is within min and max
                if suggested_volume < min_water:
                    self.progress.emit(f"Warning: Suggested volume {suggested_volume}ml for Relay Pair {relay_pair} is below the minimum {min_water}ml.")
                    suggested_volume = min_water
                elif suggested_volume > max_water:
                    self.progress.emit(f"Warning: Suggested volume {suggested_volume}ml for Relay Pair {relay_pair} exceeds the maximum {max_water}ml.")
                    suggested_volume = max_water

                # Calculate the number of triggers based on suggested_volume
                triggers = int(suggested_volume / self.relay_handler.volume_per_trigger)

                for i in range(triggers):
                    delay = i * self.settings['stagger'] * 1000  # delay in milliseconds
                    timer = QTimer(self)
                    timer.setSingleShot(True)
                    timer.timeout.connect(lambda rp=relay_pair: self.trigger_relay(rp))
                    timer.start(delay)
                    self.timers.append(timer)

            # Schedule the next run
            self.progress.emit(f"Cycle completed, waiting for {self.settings['interval']} seconds for next cycle.")
            self.main_timer.start(self.settings['interval'] * 1000)
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