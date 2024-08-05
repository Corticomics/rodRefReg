import sys
import time
from threading import Thread
from PyQt5.QtWidgets import QApplication
from RunStop import RunStop
from settings import load_settings, save_settings

class RodentRefreshmentApp:
    def __init__(self):
        self.settings = load_settings()
        self.gui = RunStop(self.run_program, self.stop_program, self.update_all_settings, self.change_relay_hats, self.settings)

    def run_program(self):
        # Run the pump control logic in a new thread
        Thread(target=self.run_logic).start()

    def run_logic(self):
        interval = self.gui.get_interval()
        stagger = self.gui.get_stagger()
        start_time = self.gui.get_start_time()
        end_time = self.gui.get_end_time()

        offline_duration = self.gui.get_offline_duration()
        if offline_duration > 0:
            end_time = time.time() + (offline_duration * 60)

        current_time = time.time()
        while current_time < end_time:
            if start_time.timestamp() <= current_time <= end_time.timestamp():
                self.activate_relay()
                time.sleep(interval)  # Wait for the interval
            current_time = time.time()

    def activate_relay(self):
        # Logic to activate relay for dispensing water
        print("Relay activated")

    def stop_program(self):
        # Placeholder for stopping the program logic
        print("Program stopped")
        # You may want to include logic to safely stop the running thread

    def update_all_settings(self):
        settings = {
            'interval': self.gui.get_interval(),
            'stagger': self.gui.get_stagger(),
            'start_time': self.gui.get_start_time().timestamp(),
            'end_time': self.gui.get_end_time().timestamp(),
            'offline_duration': self.gui.get_offline_duration()
        }
        save_settings(settings)
        print("Settings updated")

    def change_relay_hats(self):
        # Placeholder for changing relay hats logic
        print("Relay hats changed")

if __name__ == "__main__":
    app = QApplication(sys.argv)
    rodent_app = RodentRefreshmentApp()
    rodent_app.gui.show()
    sys.exit(app.exec_())
